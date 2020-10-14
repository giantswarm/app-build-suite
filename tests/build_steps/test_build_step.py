import pytest

from app_build_suite.build_steps import BuildStep
from app_build_suite.build_steps.build_step import (
    STEP_BUILD,
    STEP_METADATA,
    STEP_TEST_ALL,
)
from app_build_suite.build_steps.errors import ValidationError
from tests.build_steps.dummy_build_step import DummyBuildStep, DummyTwoStepBuildPipeline


def test_build_step_is_abstract():
    with pytest.raises(TypeError):
        BuildStep()


def test_build_step_name():
    bs = DummyBuildStep("bs1")
    assert bs.name == "DummyBuildStep"


def test_build_step_raises_own_exception_when_binary_not_found(monkeypatch):
    fake_bin = "fake.bin"

    def check_bin(name):
        assert name == fake_bin
        return None

    monkeypatch.setattr("shutil.which", check_bin)
    bs = DummyBuildStep("s1")
    with pytest.raises(ValidationError):
        bs._assert_binary_present_in_path(fake_bin)


def test_build_step_validates_version_ok():
    bs = DummyBuildStep("bs1")
    bs._assert_version_in_range("test", "v0.2.0", "0.2.0", "0.3.0")
    bs._assert_version_in_range("test", "0.2.0", "0.2.0", "0.3.0")
    bs._assert_version_in_range("test", "v0.2.100", "0.2.0", "0.3.0")
    with pytest.raises(ValidationError):
        bs._assert_version_in_range("test", "v0.3.0", "0.2.0", "0.3.0")
    with pytest.raises(ValidationError):
        bs._assert_version_in_range("test", "v0.1.0", "0.2.0", "0.3.0")


def test_build_step_suite_combines_step_types_ok():
    bsp = DummyTwoStepBuildPipeline()
    assert bsp.steps_provided == {STEP_BUILD, STEP_METADATA, STEP_TEST_ALL}
