import argparse
import logging
import os
import subprocess  # nosec - we need it to execute apptestctl and test framework
import time
from abc import ABC, abstractmethod
from typing import NewType, Set, Optional, List, cast, Callable

import configargparse
import pykube
import yaml
from pykube import KubeConfig, HTTPClient, ConfigMap
from pytest_helm_charts.giantswarm_app_platform.custom_resources import AppCR
from pytest_helm_charts.utils import YamlDict

from app_build_suite.build_steps import BuildStepsFilteringPipeline, BuildStep
from app_build_suite.build_steps.build_step import StepType, STEP_TEST_ALL
from app_build_suite.build_steps.cluster_manager import ClusterManager
from app_build_suite.build_steps.repositories import ChartMuseumAppRepository
from app_build_suite.cluster_providers.cluster_provider import ClusterInfo, ClusterType
from app_build_suite.errors import ConfigError, TestError
from app_build_suite.types import Context
from app_build_suite.utils.config import get_config_value_by_cmd_line_option

TestType = NewType("TestType", str)
TEST_UNIT = TestType("unit")
TEST_FUNCTIONAL = TestType("functional")
TEST_PERFORMANCE = TestType("performance")
TEST_COMPATIBILITY = TestType("compatibility")

context_key_chart_yaml: str = "chart_yaml"
context_key_app_cr: str = "app_cr"
context_key_app_cm_cr: str = "app_cm_cr"

_chart_yaml = "Chart.yaml"
logger = logging.getLogger(__name__)


class BaseTestRunnersFilteringPipeline(BuildStepsFilteringPipeline):
    """
    Pipeline that combines all the steps required to run application tests.
    """

    key_config_group_name = "App testing options"
    key_config_option_deploy_app = "--app-tests-deploy"
    key_config_option_deploy_namespace = "--app-tests-deploy-namespace"
    key_config_option_deploy_config_file = "--app-tests-app-config-file"

    def __init__(self, pipeline: List[BuildStep], cluster_manager: ClusterManager):
        super().__init__(pipeline, self.key_config_group_name)
        self._cluster_manager = cluster_manager

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        super().initialize_config(config_parser)
        if self._config_parser_group is None:
            raise ValueError("'_config_parser_group' can't be None")
        self._config_parser_group.add_argument(
            self.key_config_option_deploy_app,
            required=False,
            default=True,
            action="store_true",
            help="If 'True', then the chart built in the build step will be deployed to the test target cluster"
            " using an App CR before tests are started",
        )
        self._config_parser_group.add_argument(
            self.key_config_option_deploy_namespace,
            required=False,
            default="default",
            help="The namespace your app under test should be deployed to for running tests.",
        )
        self._config_parser_group.add_argument(
            self.key_config_option_deploy_config_file,
            required=False,
            help="Path for a configuration file (values file) for your app when it's deployed for testing.",
        )
        self._cluster_manager.initialize_config(self._config_parser_group)

    def pre_run(self, config: argparse.Namespace) -> None:
        super().pre_run(config)
        self._cluster_manager.pre_run(config)
        app_config_file = get_config_value_by_cmd_line_option(config, self.key_config_option_deploy_config_file)
        if app_config_file:
            if not os.path.isfile(app_config_file):
                raise TestError(
                    f"Application test run was configured to use '{app_config_file}' as app"
                    f" config file, but it doesn't exist."
                )
            try:
                with open(app_config_file, "r") as file:
                    yaml.safe_load(file)
            except Exception:
                raise TestError(
                    f"Application config file '{app_config_file}' found, but can't be loaded"
                    f"as a correct YAML document."
                )

    def cleanup(
        self,
        config: argparse.Namespace,
        context: Context,
        has_build_failed: bool,
    ) -> None:
        self._cluster_manager.cleanup()


class TestInfoProvider(BuildStep):
    """
    Since the whole build pipeline can change Chart.yaml file multiple times, this
    class loads the Chart.yaml as dict into context at the beginning of testing
    pipeline.
    """

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_TEST_ALL}

    def run(self, config: argparse.Namespace, context: Context) -> None:
        chart_yaml_path = os.path.join(config.chart_dir, _chart_yaml)
        with open(chart_yaml_path, "r") as file:
            chart_yaml = yaml.safe_load(file)
            context[context_key_chart_yaml] = chart_yaml


class BaseTestRunner(BuildStep, ABC):
    _apptestctl_bin = "apptestctl"
    _apptestctl_bootstrap_timeout_sec = 180
    _app_deployment_timeout_sec = 1800
    _app_deletion_timeout_sec = 600

    def __init__(self, cluster_manager: ClusterManager):
        self._cluster_manager = cluster_manager
        self._configured_cluster_type: ClusterType = ClusterType("")
        self._configured_cluster_config_file = ""
        self._kube_client: Optional[HTTPClient] = None
        self._cluster_info: Optional[ClusterInfo] = None

    @property
    @abstractmethod
    def _test_type_executed(self) -> TestType:
        raise NotImplementedError

    @abstractmethod
    def run_tests(self, config: argparse.Namespace, context: Context):
        raise NotImplementedError

    @property
    def _config_enabled_attribute_name(self) -> str:
        return f"--enable-{self._test_type_executed}-tests"

    @property
    def _config_cluster_type_attribute_name(self) -> str:
        return f"--{self._test_type_executed}-tests-cluster-type"

    @property
    def _config_cluster_config_file_attribute_name(self) -> str:
        return f"--{self._test_type_executed}-tests-cluster-config-file"

    def is_enabled(self, config: argparse.Namespace) -> bool:
        return get_config_value_by_cmd_line_option(config, self._config_enabled_attribute_name)

    def _ensure_app_platform_ready(self, kube_config_path: str) -> None:
        """
        Ensures that app platform components are already running in the requested cluster.
        This means:
        - app-operator
        - chart-operator
        - some chart repository (chart-museum)
        - AppCatalog CR is created in the API for the chart repository
        :return:

        Args:
            config:
            kubeconfig_path:
        """

        # run the tool
        args = [self._apptestctl_bin, "bootstrap", f"--kubeconfig-path={kube_config_path}", "--wait"]
        logger.info(f"Running {self._apptestctl_bin} tool to ensure app platform components on the target cluster")
        run_res = subprocess.run(args)  # nosec, file is either autogenerated or in user's responsibility
        if run_res.returncode != 0:
            raise TestError("Bootstrapping app platform on the target cluster failed")
        logger.info("App platform components bootstrapped and ready to use.")

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            self._config_enabled_attribute_name,
            required=False,
            default=True,
            action="store_true",
            help=f"If 'True', then {self._test_type_executed} tests will be executed.",
        )
        config_parser.add_argument(
            self._config_cluster_type_attribute_name,
            required=False,
            help=f"Cluster type to use for {self._test_type_executed} tests.",
        )
        config_parser.add_argument(
            self._config_cluster_config_file_attribute_name,
            required=False,
            help=f"Additional configuration file for the cluster used for {self._test_type_executed} tests.",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        if not self.is_enabled(config):
            logger.info(f"Skipping tests of type {self._test_type_executed} as configured (pre-run step).")
            return
        # TODO: verify version of apptestctl when possible
        cluster_type = ClusterType(
            get_config_value_by_cmd_line_option(config, self._config_cluster_type_attribute_name)
        )
        cluster_config_file: str = get_config_value_by_cmd_line_option(
            config, self._config_cluster_config_file_attribute_name
        )
        known_cluster_types = self._cluster_manager.get_registered_cluster_types()
        if cluster_type not in known_cluster_types:
            raise ConfigError(
                f"--{self._test_type_executed}-tests-cluster-type",
                f"Unknown cluster type '{cluster_type}' requested for tests of type"
                f" '{self._test_type_executed}'. Known cluster types are: '{known_cluster_types}'.",
            )
        if cluster_config_file and not os.path.isfile(cluster_config_file):
            raise ConfigError(
                f"--{self._test_type_executed}-tests-cluster-config-file",
                f"Cluster config file '{cluster_config_file}' for cluster type"
                f" '{cluster_type}' requested for tests of type"
                f" '{self._test_type_executed}' doesn't exist.",
            )
        self._configured_cluster_type = cluster_type
        self._configured_cluster_config_file = cluster_config_file

    def run(self, config: argparse.Namespace, context: Context) -> None:
        if not self.is_enabled(config):
            logger.info(f"Skipping tests of type {self._test_type_executed} as configured (run step).")
            return
        # this API might need a change if we need to pass some more information than just type and config file
        logger.info(
            f"Requesting new cluster of type '{self._configured_cluster_type}' using config file"
            f" '{self._configured_cluster_config_file}'."
        )
        self._cluster_info = self._cluster_manager.get_cluster_for_test_type(
            self._configured_cluster_type, self._configured_cluster_config_file, config
        )

        logger.info("Establishing connection to the new cluster.")
        try:
            kube_config = KubeConfig.from_file(self._cluster_info.kube_config_path)
            self._kube_client = HTTPClient(kube_config)
        except Exception:
            raise TestError("Can't establish connection to the new test cluster")

        # prepare app platform and upload artifacts
        self._ensure_app_platform_ready(self._cluster_info.kube_config_path)
        self._upload_chart_to_app_catalog(context)

        try:
            if get_config_value_by_cmd_line_option(
                config, BaseTestRunnersFilteringPipeline.key_config_option_deploy_app
            ):
                self._deploy_chart_as_app(config, context)
            self.run_tests(config, context)
        except Exception as e:
            raise TestError(f"Application deployment failed: {e}")
        finally:
            self._delete_app(config, context)
            self._cluster_manager.release_cluster(self._cluster_info)

    def _deploy_chart_as_app(self, config: argparse.Namespace, context: Context) -> None:
        namespace = get_config_value_by_cmd_line_option(
            config, BaseTestRunnersFilteringPipeline.key_config_option_deploy_namespace
        )
        app_name = context[context_key_chart_yaml]["name"]
        app_version = context[context_key_chart_yaml]["version"]
        app: YamlDict = {
            "apiVersion": "application.giantswarm.io/v1alpha1",
            "kind": "App",
            "metadata": {
                "name": app_name,
                "namespace": namespace,
                "labels": {"app": app_name, "app-operator.giantswarm.io/version": "0.0.0"},
            },
            "spec": {
                "catalog": "chartmuseum",
                "version": app_version,
                "kubeConfig": {"inCluster": True},
                "name": app_name,
                "namespace": namespace,
            },
        }
        app_config_file_path = get_config_value_by_cmd_line_option(
            config, BaseTestRunnersFilteringPipeline.key_config_option_deploy_config_file
        )
        if app_config_file_path:
            app_cm_name = f"{app_name}-cm"
            self._deploy_app_config_map(namespace, app_cm_name, app_config_file_path)
            cm = app["spec"]["config"] = {"configMap": {"name": app_cm_name, "namespace": namespace}}
            context[context_key_app_cm_cr] = cm

        app_obj = AppCR(self._kube_client, app)
        logger.info(f"Creating App CR to deploy application '{app_name}' in namespace '{namespace}'.")
        app_obj.create()
        self._wait_for_app_to_be_deployed(app_obj)
        context[context_key_app_cr] = app_obj

    # this is on purpose not taken from `utils` in pytest-helm-chart, as it will have to be
    # rewritten into an async version
    def _wait_for_app_condition(
        self,
        app_obj: AppCR,
        timeout_sec: int,
        condition_name: str,
        condition_fun: Callable[[AppCR], bool] = None,
        expected_exception: pykube.exceptions.HTTPError = None,
    ):
        if condition_fun is None and expected_exception is None:
            raise ValueError("Either 'condition_fun' or 'expected_exception' has to be not None")
        success = False
        while timeout_sec > 0:
            try:
                app_obj.reload()
            except pykube.exceptions.KubernetesError as e:
                if expected_exception is not None and type(e) is pykube.exceptions.HTTPError:
                    he = cast(pykube.exceptions.HTTPError, e)
                    if he.code == expected_exception.code:
                        success = True
                        break
                raise
            if condition_fun is not None and condition_fun(app_obj):
                success = True
                break
            logger.debug(f"Waiting for app '{app_obj.name}' to be {condition_name}.")
            time.sleep(1)
            timeout_sec -= 1
        if not success:
            raise TestError(
                f"Application not ready: '{app_obj.name}' failed to be {condition_name} in "
                f"'{app_obj.namespace} within {self._app_deployment_timeout_sec} minutes."
            )

    def _wait_for_app_to_be_deployed(self, app_obj: AppCR):
        self._wait_for_app_condition(
            app_obj,
            self._app_deployment_timeout_sec,
            "deployed",
            condition_fun=lambda a: "status" in a.obj
            and "release" in a.obj["status"]
            and "status" in a.obj["status"]["release"]
            and a.obj["status"]["release"]["status"].lower() == "deployed",
        )

    def _wait_for_app_to_be_deleted(self, app_obj: AppCR):
        self._wait_for_app_condition(
            app_obj,
            self._app_deletion_timeout_sec,
            "deleted",
            expected_exception=pykube.exceptions.HTTPError(code=404, message=""),
        )

    def _deploy_app_config_map(self, namespace: str, name: str, app_config_file_path: str) -> ConfigMap:
        with open(app_config_file_path) as f:
            config_values = f.read()
        app_cm: YamlDict = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": name, "namespace": namespace},
            "data": {"values": config_values},
        }
        app_cm_obj = ConfigMap(self._kube_client, app_cm)
        logger.info(f"Creating ConfigMap '{name}' with options in namespace '{namespace}'.")
        app_cm_obj.create()
        return app_cm_obj

    def _upload_chart_to_app_catalog(self, context: Context):
        # in future, if we want to support multiple chart repositories, we need to make this configurable
        # right now, static dependency will do
        ChartMuseumAppRepository(self._kube_client).upload_artifacts(context)

    # noinspection PyMethodMayBeStatic
    def _delete_app(self, config: argparse.Namespace, context: Context):
        app_obj = cast(AppCR, context[context_key_app_cr])
        app_obj.delete()
        app_config_file_path = get_config_value_by_cmd_line_option(
            config, BaseTestRunnersFilteringPipeline.key_config_option_deploy_config_file
        )
        if app_config_file_path:
            cast(ConfigMap, context[context_key_app_cm_cr]).delete()

        self._wait_for_app_to_be_deleted(app_obj)
