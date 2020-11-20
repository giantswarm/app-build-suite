from typing import Any, Dict, List, Tuple

import pytest

from app_build_suite.__main__ import get_global_config_parser
from app_build_suite.build_steps import BuildStep
from app_build_suite.build_steps.build_step import (
    STEP_BUILD,
    STEP_METADATA,
    STEP_TEST_ALL,
    StepType,
    STEP_ALL,
)
from app_build_suite.errors import ValidationError, Error
from tests.build_steps.dummy_build_step import (
    DummyBuildStep,
    DummyTwoStepBuildFilteringPipeline,
)


class TestBuildStep:
    def test_build_step_is_abstract(self):
        with pytest.raises(TypeError):
            BuildStep()

    def test_build_step_name(self):
        bs = DummyBuildStep("bs1")
        assert bs.name == "DummyBuildStep"

    def test_build_step_raises_own_exception_when_binary_not_found(self, monkeypatch):
        fake_bin = "fake.bin"

        def check_bin(name):
            assert name == fake_bin
            return None

        monkeypatch.setattr("shutil.which", check_bin)
        bs = DummyBuildStep("s1")
        with pytest.raises(ValidationError):
            bs._assert_binary_present_in_path(fake_bin)

    def test_build_step_validates_version_ok(self):
        bs = DummyBuildStep("bs1")
        bs._assert_version_in_range("test", "v0.2.0", "0.2.0", "0.3.0")
        bs._assert_version_in_range("test", "0.2.0", "0.2.0", "0.3.0")
        bs._assert_version_in_range("test", "v0.2.100", "0.2.0", "0.3.0")
        with pytest.raises(ValidationError):
            bs._assert_version_in_range("test", "v0.3.0", "0.2.0", "0.3.0")
        with pytest.raises(ValidationError):
            bs._assert_version_in_range("test", "v0.1.0", "0.2.0", "0.3.0")


class TestBuildStepSuite:
    def test_build_step_suite_combines_step_types_ok(self):
        bsp = DummyTwoStepBuildFilteringPipeline()
        assert bsp.steps_provided == {STEP_BUILD, STEP_METADATA, STEP_TEST_ALL}

    @pytest.mark.parametrize(
        "requested_tags,requested_skips,expected_run_counters",
        [
            # STEPS_ALL should run all build steps
            ([STEP_ALL], [], ([1, 1, 1, 1], [1, 1, 1, 1])),
            # STEPS_BUILD should run only 1st BuildStep, but 'configure' needs to run for both still
            ([STEP_BUILD], [], ([1, 1, 1, 1], [1, 0, 0, 0])),
            # STEPS_TEST_ALL should run only 2nd BuildStep, but 'configure' needs to run for both still
            ([STEP_TEST_ALL], [], ([1, 0, 0, 0], [1, 1, 1, 1])),
            # this should run all except the ones including STEP_BUILD (1st one)
            ([STEP_ALL], [STEP_BUILD], ([1, 0, 0, 0], [1, 1, 1, 1])),
            # this should run all except the ones including STEP_TEST_ALL (2nd one)
            ([STEP_ALL], [STEP_TEST_ALL], ([1, 1, 1, 1], [1, 0, 0, 0])),
        ],
    )
    def test_build_step_suite_runs_steps_ok(
        self,
        requested_tags: List[StepType],
        requested_skips: List[StepType],
        expected_run_counters: Tuple[List[int], List[int]],
    ):
        bsp = DummyTwoStepBuildFilteringPipeline()
        config_parser = get_global_config_parser()
        bsp.initialize_config(config_parser)
        config = config_parser.parse_known_args()[0]
        config.steps = list(requested_tags)
        config.skip_steps = list(requested_skips)
        context: Dict[str, Any] = {}
        bsp.pre_run(config)
        bsp.run(config, context)
        bsp.cleanup(config, context, False)

        bsp.step1.assert_run_counters(*expected_run_counters[0])
        bsp.step2.assert_run_counters(*expected_run_counters[1])

    def test_build_step_suite_runs_with_exception(self):
        bsp = DummyTwoStepBuildFilteringPipeline(fail_in_pre=True)
        config_parser = get_global_config_parser()
        bsp.initialize_config(config_parser)
        config = config_parser.parse_known_args()[0]
        with pytest.raises(Error):
            bsp.pre_run(config)

        # this fails in pre_run
        bsp.step1.assert_run_counters(1, 1, 0, 0)
        # since step above fails, this won't have even pre_run ran
        bsp.step2.assert_run_counters(1, 0, 0, 0)
