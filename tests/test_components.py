from typing import cast

import configargparse
import pytest

from app_build_suite.components import Runner
from tests.build_steps.dummy_build_step import DummyBuildStep


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
