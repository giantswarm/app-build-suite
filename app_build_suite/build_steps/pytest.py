import argparse
import logging
import os
import subprocess  # nosec - we need it to execute apptestctl and test framework
from abc import ABC, abstractmethod
from typing import Dict, Any, NewType, Set, Optional, List

import configargparse
from pykube import KubeConfig, HTTPClient
from pytest_helm_charts import utils

from app_build_suite.build_steps import BuildStepsFilteringPipeline, BuildStep
from app_build_suite.build_steps.build_step import StepType, STEP_TEST_FUNCTIONAL
from app_build_suite.cluster_providers.cluster_provider import ClusterInfo, ClusterProvider, ClusterType
from app_build_suite.errors import ConfigError
from app_build_suite.utils.config import get_config_value_by_cmd_line_option

TestType = NewType("TestType", str)
TEST_UNIT = TestType("unit")
TEST_FUNCTIONAL = TestType("functional")
TEST_PERFORMANCE = TestType("performance")
TEST_COMPATIBILITY = TestType("compatibility")

logger = logging.getLogger(__name__)


class ClusterManager:
    """
    This class manages creation and destruction of clusters required to execute tests.
    Cluster are re-used, so when a cluster of specific 'provider' type and 'version' already exists,
    we return the existing (saved internally) cluster. If it doesn't exist, it is created and saved.
    Each cluster is given an ID taken (if only possible) from the underlying provider, to be able
    to correlate clusters created here with what's really running in the infrastructure.
    """

    def __init__(self):
        # config is necessary for cluster providers to configure clusters; we'll set it once config is loaded
        self._config: Optional[argparse.Namespace] = None
        # list to track created clusters
        self._clusters: List[ClusterInfo] = []
        # dictionary to keep cluster providers
        self._cluster_providers: Dict[ClusterType, ClusterProvider] = {}
        # find and create cluster providers
        for cls in ClusterProvider.__subclasses__():
            instance = cls()
            self._cluster_providers[instance.provided_cluster_type] = instance

    def get_registered_cluster_types(self) -> List[ClusterType]:
        return [k for k in self._cluster_providers.keys()]

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        for cluster_type, provider in self._cluster_providers.items():
            logger.debug(f"Initializing configuration of cluster provider for clusters of type {cluster_type}")
            provider.initialize_config(config_parser)

    def pre_run(self, config: argparse.Namespace) -> None:
        for cluster_type, provider in self._cluster_providers.items():
            logger.debug(f"Executing pre-run of cluster provider for clusters of type {cluster_type}")
            provider.pre_run(config)

    def get_cluster_for_test_type(self, cluster_type: ClusterType, cluster_config_file: str) -> ClusterInfo:
        """ clusters can be requested in parallel - creation mus be non-blocking!"""
        if cluster_type not in self._cluster_providers.keys():
            raise ValueError(f"Unknown cluster type '{cluster_type}'.")
        cluster_info = self._cluster_providers[cluster_type].get_cluster(cluster_type, config_file=cluster_config_file)
        self._clusters.append(cluster_info)
        return cluster_info

    def release_cluster(self, cluster_info: ClusterInfo) -> None:
        if cluster_info not in self._clusters:
            raise ValueError(f"Cluster {cluster_info} is not registered as managed here.")
        cluster_info.managing_provider.delete_cluster(cluster_info)
        self._clusters.remove(cluster_info)

    def cleanup(self) -> None:
        """
        A finalizer of ClusterManager - requests destruction of any cluster previously created,
        saved and not yet destroyed.
        :return:
        """
        for cluster_info in self._clusters:
            self.release_cluster(cluster_info)


class PytestTestFilteringPipeline(BuildStepsFilteringPipeline):
    """
    Pipeline that combines all the steps required to use pytest as a testing framework.
    """

    def __init__(self):
        self._cluster_manager = ClusterManager()
        super().__init__(
            [
                FunctionalTestRunner(self._cluster_manager),
            ],
            "Pytest test options",
        )

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        super().initialize_config(config_parser)
        if self._config_parser_group is None:
            raise ValueError("'_config_parser_group' can't be None")
        self._config_parser_group.add_argument(
            "--deploy-app-for-tests",
            required=False,
            default=True,
            action="store_true",
            help="If 'True', then the chart built in the build step will be deployed to the test target cluster"
            " using an App CR before tests are started",
        )
        self._cluster_manager.initialize_config(self._config_parser_group)

    def pre_run(self, config: argparse.Namespace) -> None:
        super().pre_run(config)
        self._cluster_manager.pre_run(config)

    def cleanup(
        self,
        config: argparse.Namespace,
        context: Dict[str, Any],
        has_build_failed: bool,
    ) -> None:
        self._cluster_manager.cleanup()


class BaseTestRunner(BuildStep, ABC):
    _apptestctl_bin = "apptestctl"
    _apptestctl_bootstrap_timeout_sec = 180

    def __init__(self, cluster_manager: ClusterManager):
        self._cluster_manager = cluster_manager
        self._configured_cluster_type: ClusterType = ClusterType("")
        self._configured_cluster_config_file = ""

    @property
    @abstractmethod
    def _test_type_executed(self) -> TestType:
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

        # currently apptestctl expects kubeconfig content to be passed as args
        with open(kube_config_path) as f:
            kube_config_txt = f.read()
        # run the tool
        args = [self._apptestctl_bin, "bootstrap", f"--kubeconfig={kube_config_txt}"]
        logger.info(f"Running {self._apptestctl_bin} tool to ensure app platform components on the target cluster")
        run_res = subprocess.run(args)  # nosec, file is either autogenerated or in user's responsibility
        if run_res.returncode != 0:
            logger.error("Bootstrapping app platform on the target cluster failed")
            raise
        # wait for everything to be up - currently apptestctl doesn't do that
        kube_config = KubeConfig.from_file(kube_config_path)
        kube_client = HTTPClient(kube_config)
        utils.wait_for_deployments_to_run(
            kube_client,
            ["app-operator-unique", "chart-operator-unique", "chartmuseum-chartmuseum"],
            "giantswarm",
            self._apptestctl_bootstrap_timeout_sec,
            missing_ok=False,
        )
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

    def run(self, config: argparse.Namespace, context: Dict[str, Any]) -> None:
        if not self.is_enabled(config):
            logger.info(f"Skipping tests of type {self._test_type_executed} as configured (run step).")
            return
        # this API might need a change if we need to pass some more information than just type and config file
        cluster_info = self._cluster_manager.get_cluster_for_test_type(
            self._configured_cluster_type, self._configured_cluster_config_file
        )
        self._ensure_app_platform_ready(cluster_info.kube_config_path)
        if config.deploy_app_for_tests:
            self._deploy_chart_as_app(context)
        self._run_pytest()
        self._cluster_manager.release_cluster(cluster_info)

    def _deploy_chart_as_app(self, context: Dict[str, Any]):
        pass

    def _run_pytest(self):
        pass


class FunctionalTestRunner(BaseTestRunner):
    """
    FunctionalTestRunner executes functional tests on top of the configured version of kind cluster
    """

    @property
    def _test_type_executed(self) -> TestType:
        return TEST_FUNCTIONAL

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_TEST_FUNCTIONAL}
