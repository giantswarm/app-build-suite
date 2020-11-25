import argparse
import os
from abc import ABC
from typing import Set

import configargparse

from app_build_suite.build_steps.base_test_runner import (
    BaseTestRunnersFilteringPipeline,
    TestInfoProvider,
    BaseTestRunner,
    ClusterManager,
    TestType,
    TEST_FUNCTIONAL,
)
from app_build_suite.build_steps.build_step import StepType, STEP_TEST_FUNCTIONAL


class PytestTestFilteringPipeline(BaseTestRunnersFilteringPipeline):
    key_config_option_pytest_dir = "--app-tests-pytest-tests-dir"

    def __init__(self):
        cluster_manager = ClusterManager()
        super().__init__(
            [
                TestInfoProvider(),
                PytestFunctionalTestRunner(cluster_manager),
            ],
            "Pytest test options",
            cluster_manager,
        )

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        super().initialize_config(config_parser)
        config_parser.add_argument(
            self.key_config_option_pytest_dir,
            required=False,
            default=os.path.join("tests", "abs"),
            help="Directory, where pytest tests source code can be found.",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        super(PytestTestFilteringPipeline, self).pre_run(config)
        # TODO: validate test dir
        raise NotImplementedError()


class PytestTestRunner(BaseTestRunner, ABC):
    def __init__(self, cluster_manager: ClusterManager):
        super().__init__(cluster_manager)

    def run_tests(self):
        pass


class PytestFunctionalTestRunner(PytestTestRunner):
    def __init__(self, cluster_manager: ClusterManager):
        super().__init__(cluster_manager)

    @property
    def _test_type_executed(self) -> TestType:
        return TEST_FUNCTIONAL

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_TEST_FUNCTIONAL}
