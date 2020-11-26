import argparse
import logging
import os
import shutil
import subprocess  # nosec, needed to invoke pytest as external process
from abc import ABC
from typing import Set, cast

import configargparse

from app_build_suite.build_steps.base_test_runner import (
    BaseTestRunnersFilteringPipeline,
    TestInfoProvider,
    BaseTestRunner,
    ClusterManager,
    TestType,
    TEST_FUNCTIONAL,
    context_key_chart_yaml,
)
from app_build_suite.build_steps.build_step import StepType, STEP_TEST_FUNCTIONAL
from app_build_suite.errors import ValidationError, TestError
from app_build_suite.types import Context
from app_build_suite.utils.config import get_config_value_by_cmd_line_option

logger = logging.getLogger(__name__)


class PytestTestFilteringPipeline(BaseTestRunnersFilteringPipeline):
    key_config_option_pytest_dir = "--app-tests-pytest-tests-dir"

    def __init__(self):
        cluster_manager = ClusterManager()
        super().__init__(
            [
                TestInfoProvider(),
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

    def pre_run(self, config: argparse.Namespace) -> None:
        super().pre_run(config)

        pytest_dir = get_config_value_by_cmd_line_option(
            config, PytestTestFilteringPipeline.key_config_option_pytest_dir
        )
        if not os.path.isdir(pytest_dir):
            logger.warning(
                f"Pytest tests were requested, but the configured test source code directory '{pytest_dir}'"
                f" doesn't exist. Skipping pytest run."
            )
            self._skip_tests = True
        if not any(f.endswith(".py") for f in os.listdir(pytest_dir)):
            logger.warning(
                f"Pytest tests were requested, but no python source code file was found in"
                f" directory '{pytest_dir}'. Skipping pytest run."
            )
            self._skip_tests = True
        if shutil.which(self._pipenv_bin) is None:
            raise ValidationError(
                self.name,
                f"In order to install pytest virtual env, you need to have " f"'{self._pipenv_bin}' installed.",
            )

    def run(self, config: argparse.Namespace, context: Context) -> None:
        if not self._skip_tests:
            super().run(config, context)
        else:
            logger.warning("Not running any pytest tests, as validation failed in pre_run step.")

    def run_tests(self, config: argparse.Namespace, context: Context) -> None:
        if not self._cluster_info:
            raise TestError("Cluster info is missing, can't run tests.")

        pytest_dir = get_config_value_by_cmd_line_option(
            config, PytestTestFilteringPipeline.key_config_option_pytest_dir
        )

        args = [self._pipenv_bin, "install", "--deploy"]
        logger.info(
            f"Running {self._pipenv_bin} tool in '{pytest_dir}' directory to install virtual env " f"for running tests."
        )
        run_res = subprocess.run(args, cwd=pytest_dir)  # nosec, no user input here
        if run_res.returncode != 0:
            raise TestError(f"Running '{args}' in directory '{pytest_dir}' failed.")

        app_config_file_path = get_config_value_by_cmd_line_option(
            config, BaseTestRunnersFilteringPipeline.key_config_option_deploy_config_file
        )
        cluster_type = (
            self._cluster_info.overridden_cluster_type
            if self._cluster_info.overridden_cluster_type
            else self._cluster_info.cluster_type
        )
        cluster_version = self._cluster_info.version
        args = [
            self._pytest_bin,
            "-m",
            self._test_type_executed,
            "-cluster-type",
            self._configured_cluster_type,
            "-kube-config",
            self._cluster_info.kube_config_path,
            "-values-file",
            app_config_file_path,
            "--chart-version",
            context[context_key_chart_yaml]["version"],
            "--chart-extra-info",
            f"external_cluster_type={cluster_type}," f"external_cluster_version={cluster_version}",
            "--log-cli-level",
            "info",
            "--junitxml=test_results",
        ]
        logger.info(f"Running {self._pytest_bin} tool in '{pytest_dir}' directory.")
        run_res = subprocess.run(args, cwd=pytest_dir)  # nosec, no user input here
        if run_res.returncode != 0:
            raise TestError(f"Pytest tests failed: running '{args}' in directory '{pytest_dir}' failed.")


class PytestFunctionalTestRunner(PytestTestRunner):
    def __init__(self, cluster_manager: ClusterManager):
        super().__init__(cluster_manager)

    @property
    def _test_type_executed(self) -> TestType:
        return TEST_FUNCTIONAL

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_TEST_FUNCTIONAL}
