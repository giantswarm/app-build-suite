import os
import unittest.mock
from typing import cast

import pytest
from pytest_mock import MockerFixture
from step_exec_lib.errors import ValidationError

from app_build_suite.build_steps.helm_template_validator import HelmTemplateValidator
from app_build_suite.errors import BuildError
from tests.build_steps.helpers import init_config_for_step

RENDERED_OK = """---
# Source: my-app/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
---
# Source: my-app/templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app
"""

RENDERED_DUPLICATE_KEY = """---
# Source: my-app/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: my-app
  labels:
    team: my-team
"""

RENDERED_SYNTAX_ERROR = """---
# Source: my-app/templates/broken.yaml
key: [unclosed
"""


def _run_validator(mocker: MockerFixture, stdout: str, returncode: int = 0) -> unittest.mock.Mock:
    run_res = mocker.Mock(name="RunResult")
    run_res.returncode = returncode
    run_res.stdout = stdout
    run_res.stderr = "some helm error" if returncode != 0 else ""
    run_and_log = mocker.patch(
        "app_build_suite.build_steps.helm_template_validator.run_and_log",
        return_value=run_res,
    )
    step = HelmTemplateValidator()
    config = init_config_for_step(step)
    step.run(config, {})
    return run_and_log


def test_valid_rendered_chart_passes(mocker: MockerFixture) -> None:
    run_and_log = _run_validator(mocker, RENDERED_OK)
    args = run_and_log.call_args.args[0]
    assert args[:3] == ["helm", "template", "abs-validation"]
    assert "--include-crds" in args


def test_duplicate_key_in_rendered_chart_fails(mocker: MockerFixture) -> None:
    with pytest.raises(BuildError) as excinfo:
        _run_validator(mocker, RENDERED_DUPLICATE_KEY)
    assert "Duplicate YAML key" in excinfo.value.msg
    assert "my-app/templates/deployment.yaml" in excinfo.value.msg
    assert "duplicate key 'labels'" in excinfo.value.msg


def test_syntax_error_in_rendered_chart_fails(mocker: MockerFixture) -> None:
    with pytest.raises(BuildError) as excinfo:
        _run_validator(mocker, RENDERED_SYNTAX_ERROR)
    assert "Invalid YAML" in excinfo.value.msg
    assert "my-app/templates/broken.yaml" in excinfo.value.msg


def test_failed_helm_template_run_fails(mocker: MockerFixture) -> None:
    with pytest.raises(BuildError) as excinfo:
        _run_validator(mocker, "", returncode=1)
    assert "'helm template' rendering failed" in excinfo.value.msg


def test_disabled_validator_skips_run(mocker: MockerFixture) -> None:
    run_and_log = mocker.patch("app_build_suite.build_steps.helm_template_validator.run_and_log")
    step = HelmTemplateValidator()
    config = init_config_for_step(step)
    config.disable_helm_template_validator = True
    step.pre_run(config)
    step.run(config, {})
    run_and_log.assert_not_called()


def test_extra_values_files_are_passed_to_helm(mocker: MockerFixture) -> None:
    run_res = mocker.Mock(name="RunResult")
    run_res.returncode = 0
    run_res.stdout = RENDERED_OK
    run_and_log = mocker.patch(
        "app_build_suite.build_steps.helm_template_validator.run_and_log",
        return_value=run_res,
    )
    mocker.patch("os.path.isfile", return_value=True)
    step = HelmTemplateValidator()
    mocker.patch.object(step, "_assert_binary_present_in_path")
    mocker.patch.object(step, "_assert_version_in_range")
    config = init_config_for_step(step)
    config.helm_template_extra_values = ["extra-values.yaml"]
    run_res.stdout = 'version.BuildInfo{Version:"v3.21.2"}'
    step.pre_run(config)
    run_res.stdout = RENDERED_OK
    step.run(config, {})

    expected_path = os.path.join(os.getcwd(), "extra-values.yaml")
    assert config.helm_template_extra_values == [expected_path]
    args = run_and_log.call_args.args[0]
    values_idx = args.index("--values")
    assert args[values_idx + 1] == expected_path


def test_missing_extra_values_file_fails_pre_run(mocker: MockerFixture) -> None:
    run_res = mocker.Mock(name="RunResult")
    run_res.returncode = 0
    run_res.stdout = 'version.BuildInfo{Version:"v3.21.2"}'
    mocker.patch(
        "app_build_suite.build_steps.helm_template_validator.run_and_log",
        return_value=run_res,
    )
    step = HelmTemplateValidator()
    mocker.patch.object(step, "_assert_binary_present_in_path")
    mocker.patch.object(step, "_assert_version_in_range")
    config = init_config_for_step(step)
    config.helm_template_extra_values = ["/nonexisting-fhtagn42/values.yaml"]
    with pytest.raises(ValidationError):
        step.pre_run(config)


def test_step_is_registered_in_helm_pipeline() -> None:
    from app_build_suite.build_steps.helm import HelmBuildFilteringPipeline
    from app_build_suite.build_steps.helm_chart_builder import HelmChartBuilder

    pipeline = HelmBuildFilteringPipeline()
    steps = cast(list, pipeline._pipeline)
    step_types = [type(s) for s in steps]
    assert HelmTemplateValidator in step_types
    # must render before packaging
    assert step_types.index(HelmTemplateValidator) < step_types.index(HelmChartBuilder)
