import argparse
from typing import Dict, Any, List, cast

import configargparse
import pytest

from app_build_suite.build_steps import BuildStep
from app_build_suite.build_steps.build_step import (
    StepType,
    STEP_ALL,
    BuildStepsPipeline,
)
from app_build_suite.build_steps.errors import Error
from app_build_suite.components import Runner


class DummyBuildStep(BuildStep):
    def __init__(
        self,
        dummy_name: str,
        fail_in_pre: bool = False,
        fail_in_run: bool = False,
        fail_in_cleanup: bool = False,
    ):
        self.fail_in_cleanup = fail_in_cleanup
        self.dummy_name = dummy_name
        self.pre_run_counter = 0
        self.run_counter = 0
        self.cleanup_counter = 0
        self.fail_in_pre = fail_in_pre
        self.fail_in_run = fail_in_run
        self.cleanup_informed_about_failure = False

    @property
    def steps_provided(self) -> List[StepType]:
        return [STEP_ALL]

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


class DummyBuildPipeline(BuildStepsPipeline):
    def __init__(self):
        super().__init__([DummyBuildStep("t1")])


def test_runner_with_single_step():
    test_step = DummyBuildStep("t1")
    runner = Runner(cast(configargparse.Namespace, None), [test_step])
    runner.run()

    assert test_step.pre_run_counter == 1
    assert test_step.run_counter == 1
    assert test_step.cleanup_counter == 1
    assert runner.context["test"] == 1


def test_runner_exits_on_failed_pre_run():
    test_step = DummyBuildStep("t1", fail_in_pre=True)
    runner = Runner(cast(configargparse.Namespace, None), [test_step])
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        runner.run()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1
    assert test_step.pre_run_counter == 1
    assert test_step.run_counter == 0
    assert test_step.cleanup_counter == 0


def test_runner_breaks_build_on_failed_run():
    test_step1 = DummyBuildStep("t1", fail_in_run=True, fail_in_cleanup=True)
    test_step2 = DummyBuildStep("t2")
    runner = Runner(cast(configargparse.Namespace, None), [test_step1, test_step2])
    runner.run()

    assert test_step1.pre_run_counter == 1
    assert test_step2.pre_run_counter == 1
    assert test_step1.run_counter == 1
    # if the first build step failed, second one should be not executed
    assert test_step2.run_counter == 0
    # but cleanup should still run for both steps, even if cleanup in the 1st one fails
    assert test_step1.cleanup_informed_about_failure
    assert test_step1.cleanup_counter == 1
    assert test_step2.cleanup_informed_about_failure
    assert test_step2.cleanup_counter == 1
