import argparse
import logging
import os
import shutil
from abc import ABC
from typing import Set, cast, List

import configargparse

from app_test_suite.steps.base_test_runner import (
    BaseTestRunnersFilteringPipeline,
    TestInfoProvider,
    BaseTestRunner,
    context_key_chart_yaml,
)
from app_test_suite.steps.test_stage_helpers import TestType, TEST_SMOKE, TEST_FUNCTIONAL
from step_exec_lib.build_step import StepType, STEP_TEST_FUNCTIONAL, STEP_TEST_SMOKE
from app_test_suite.cluster_manager import ClusterManager
from app_build_suite.build_steps.helm import context_key_chart_file_name
from step_exec_lib.errors import ValidationError, TestError
from step_exec_lib.types import Context
from step_exec_lib.utils import get_config_value_by_cmd_line_option
from step_exec_lib.utils.processes import run_and_log

logger = logging.getLogger(__name__)


class PytestTestFilteringPipeline(BaseTestRunnersFilteringPipeline):
    key_config_option_pytest_dir = "--app-tests-pytest-tests-dir"

    def __init__(self):
        cluster_manager = ClusterManager()
        super().__init__(
            [
                TestInfoProvider(),
                PytestSmokeTestRunner(cluster_manager),
                PytestFunctionalTestRunner(cluster_manager),
            ],
            cluster_manager,
        )

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        super().initialize_config(config_parser)
        self._config_parser_group = cast(
            configargparse.ArgParser,
            config_parser.add_argument_group("App testing - pytest specific options"),
        )
        self._config_parser_group.add_argument(
            self.key_config_option_pytest_dir,
            required=False,
            default=os.path.join("tests", "abs"),
            help="Directory, where pytest tests source code can be found.",
        )


class PytestTestRunner(BaseTestRunner, ABC):
    _pipenv_bin = "pipenv"
    _pytest_bin = "pytest"

    def __init__(self, cluster_manager: ClusterManager):
        super().__init__(cluster_manager)
        self._skip_tests = False
        self._pytest_dir = ""

    def pre_run(self, config: argparse.Namespace) -> None:
        super().pre_run(config)

        pytest_dir = get_config_value_by_cmd_line_option(
            config, PytestTestFilteringPipeline.key_config_option_pytest_dir
        )
        pytest_dir = os.path.join(config.chart_dir, pytest_dir)
        if not os.path.isdir(pytest_dir):
            logger.warning(
                f"Pytest tests were requested, but the configured test source code directory '{pytest_dir}'"
                f" doesn't exist. Skipping pytest run."
            )
            self._skip_tests = True
            return
        if not any(f.endswith(".py") for f in cast(List[str], os.listdir(pytest_dir))):
            logger.warning(
                f"Pytest tests were requested, but no python source code file was found in"
                f" directory '{pytest_dir}'. Skipping pytest run."
            )
            self._skip_tests = True
            return
        if shutil.which(self._pipenv_bin) is None:
            raise ValidationError(
                self.name,
                f"In order to install pytest virtual env, you need to have " f"'{self._pipenv_bin}' installed.",
            )
        self._pytest_dir = pytest_dir

    def run_tests(self, config: argparse.Namespace, context: Context) -> None:
        if self._skip_tests:
            logger.warning("Not running any pytest tests, as validation failed in pre_run step.")
            return

        if not self._cluster_info:
            raise TestError("Cluster info is missing, can't run tests.")

        args = [self._pipenv_bin, "install", "--deploy"]
        logger.info(
            f"Running {self._pipenv_bin} tool in '{self._pytest_dir}' directory to install virtual env "
            f"for running tests."
        )
        run_res = run_and_log(args, cwd=self._pytest_dir)  # nosec, no user input here
        if run_res.returncode != 0:
            raise TestError(f"Running '{args}' in directory '{self._pytest_dir}' failed.")

        app_config_file_path = get_config_value_by_cmd_line_option(
            config, BaseTestRunnersFilteringPipeline.key_config_option_deploy_config_file
        )
        cluster_type = (
            self._cluster_info.overridden_cluster_type
            if self._cluster_info.overridden_cluster_type
            else self._cluster_info.cluster_type
        )
        kube_config = os.path.abspath(self._cluster_info.kube_config_path)
        cluster_version = self._cluster_info.version
        args = [
            self._pipenv_bin,
            "run",
            self._pytest_bin,
            "-m",
            self._test_type_executed,
            "--cluster-type",
            cluster_type,
            "--kube-config",
            kube_config,
            "--chart-path",
            context[context_key_chart_file_name],
            "--chart-version",
            context[context_key_chart_yaml]["version"],
            "--chart-extra-info",
            f"external_cluster_version={cluster_version}",
            "--log-cli-level",
            "info",
            f"--junitxml=test_results_{self._test_type_executed}.xml",
        ]
        if app_config_file_path:
            args += ["--values-file", app_config_file_path]
        logger.info(f"Running {self._pytest_bin} tool in '{self._pytest_dir}' directory.")
        run_res = run_and_log(args, cwd=self._pytest_dir)  # nosec, no user input here
        if run_res.returncode != 0:
            raise TestError(f"Pytest tests failed: running '{args}' in directory '{self._pytest_dir}' failed.")


class PytestFunctionalTestRunner(PytestTestRunner):
    def __init__(self, cluster_manager: ClusterManager):
        super().__init__(cluster_manager)

    @property
    def _test_type_executed(self) -> TestType:
        return TEST_FUNCTIONAL

    @property
    def specific_test_steps_provided(self) -> Set[StepType]:
        return {STEP_TEST_FUNCTIONAL}


class PytestSmokeTestRunner(PytestTestRunner):
    def __init__(self, cluster_manager: ClusterManager):
        super().__init__(cluster_manager)

    @property
    def _test_type_executed(self) -> TestType:
        return TEST_SMOKE

    @property
    def specific_test_steps_provided(self) -> Set[StepType]:
        return {STEP_TEST_SMOKE}
