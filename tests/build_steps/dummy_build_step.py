import argparse
from typing import Dict, Any, Set

import configargparse
import pytest

from app_build_suite.__main__ import get_global_config_parser
from app_build_suite.build_steps import BuildStep, BuildStepsFilteringPipeline
from app_build_suite.build_steps.build_step import (
    StepType,
    STEP_ALL,
    STEP_BUILD,
    STEP_TEST_ALL,
    STEP_METADATA,
)
from app_build_suite.errors import Error, ValidationError


def init_config_for_step(step: BuildStep) -> configargparse.Namespace:
    config_parser = get_global_config_parser()
    step.initialize_config(config_parser)
    config = config_parser.parse_known_args()[0]
    config.chart_dir = "."
    return config


class DummyBuildStep(BuildStep):
    def __init__(
        self,
        dummy_name: str,
        steps_provided: Set[StepType] = None,
        fail_in_config: bool = False,
        fail_in_pre: bool = False,
        fail_in_run: bool = False,
        fail_in_cleanup: bool = False,
    ):
        self.fail_in_config = fail_in_config
        self.my_steps = {STEP_ALL} if steps_provided is None else steps_provided
        self.fail_in_cleanup = fail_in_cleanup
        self.dummy_name = dummy_name
        self.config_counter = 0
        self.pre_run_counter = 0
        self.run_counter = 0
        self.cleanup_counter = 0
        self.fail_in_pre = fail_in_pre
        self.fail_in_run = fail_in_run
        self.cleanup_informed_about_failure = False

    @property
    def steps_provided(self) -> Set[StepType]:
        return self.my_steps

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        """
        Run configuration phase
        :param config_parser: Any config parser.
        :return: None
        """
        self.config_counter += 1
        if self.fail_in_config:
            raise ValidationError(self.name, "configuration error was requested")

    def pre_run(self, config: argparse.Namespace) -> None:
        """
        Execute any pre-run validation or assertion logic.
        :param config: Ready (parsed) configuration Namespace object.
        :return: None
        """
        self.pre_run_counter += 1
        if self.fail_in_pre:
            raise Error("failure was requested")

    def run(self, config: argparse.Namespace, context: Dict[str, Any]) -> None:
        """
        Execute actual build action of the BuildStep.
        :param context: A context where different components can save data to share with other components.
        :param config: Ready (parsed) configuration Namespace object.
        :return: None
        """
        self.run_counter += 1
        context["test"] = 0
        if self.fail_in_run:
            raise Error("failure was requested")

    def cleanup(
        self,
        config: argparse.Namespace,
        context: Dict[str, Any],
        has_build_failed: bool,
    ) -> None:
        self.cleanup_counter += 1
        context["test"] += 1
        self.cleanup_informed_about_failure = has_build_failed
        if self.fail_in_cleanup:
            raise Error("failure was requested")

    def assert_run_counters(
        self,
        expected_config_counter: int,
        expected_pre_run_counter: int,
        expected_run_counter: int,
        expected_cleanup_counter: int,
    ):
        __tracebackhide__ = True
        if self.config_counter != expected_config_counter:
            pytest.fail(f"expected config run counter is {expected_config_counter}, but was {self.config_counter}")
        if self.pre_run_counter != expected_pre_run_counter:
            pytest.fail(f"expected pre_run run counter is {expected_pre_run_counter}, but was {self.pre_run_counter}")
        if self.run_counter != expected_run_counter:
            pytest.fail(f"expected run counter is {expected_run_counter}, but was {self.run_counter}")
        if self.cleanup_counter != expected_cleanup_counter:
            pytest.fail(f"expected cleanup run counter is {expected_cleanup_counter}, but was {self.cleanup_counter}")


class DummyOneStepBuildFilteringPipeline(BuildStepsFilteringPipeline):
    def __init__(self):
        self.step = DummyBuildStep("t1")
        super().__init__([self.step], "Dummy one step pipeline")


class DummyTwoStepBuildFilteringPipeline(BuildStepsFilteringPipeline):
    def __init__(self, fail_in_pre: bool = False):
        self.step1 = DummyBuildStep("bs1", {STEP_BUILD, STEP_METADATA}, fail_in_pre=fail_in_pre)
        self.step2 = DummyBuildStep("bs2", {STEP_TEST_ALL}, fail_in_pre=fail_in_pre)
        super().__init__([self.step1, self.step2], "Dummy two steps pipeline")
