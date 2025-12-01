import argparse
import os.path
import re
from typing import Dict, Any, List
from unittest.mock import mock_open, patch

import yaml
import pytest
from pytest_mock import MockerFixture
from step_exec_lib.errors import ValidationError

import app_build_suite
from app_build_suite.build_steps.helm import (
    HelmChartMetadataFinalizer,
    HelmChartMetadataBuilder,
    context_key_chart_file_name,
    context_key_chart_full_path,
    context_key_meta_dir_path,
    context_key_git_version,
    context_key_changes_made,
    context_key_original_chart_yaml,
    GiantSwarmHelmValidator,
)
from tests.build_steps.helpers import init_config_for_step


def test_prepare_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    input_chart_path = os.path.join(os.path.dirname(__file__), "res_test_helm/Chart.yaml")
    step = HelmChartMetadataBuilder()
    config = init_config_for_step(step)
    config.generate_metadata = True
    config.catalog_base_url = "https://some-bogus-catalog/"
    config.chart_dir = os.path.dirname(input_chart_path)
    config.destination = "."

    with open(input_chart_path) as f:
        input_chart_yaml = f.read()
    chart_yaml_data = yaml.safe_load(input_chart_yaml)

    # run pre_run
    with patch("app_build_suite.build_steps.helm.open", mock_open(read_data=input_chart_yaml)) as m:
        step.pre_run(config)
        m.assert_called_once_with(input_chart_path, "r")

    # run run
    git_version = "v0.0.1"
    chart_file_name = f"hello-world-app-{git_version}.tgz"
    chart_full_path = f"./{chart_file_name}"
    meta_dir_path = f"{chart_full_path}-meta"
    with patch("app_build_suite.build_steps.helm.open", mock_open(read_data=input_chart_yaml)) as m:
        context = {
            context_key_chart_file_name: chart_file_name,
            context_key_chart_full_path: chart_full_path,
            context_key_meta_dir_path: meta_dir_path,
            context_key_git_version: git_version,
            context_key_changes_made: True,
        }

        repo_root = step._find_git_repo_root(config.chart_dir)
        assert repo_root is not None
        github_repo = step._discover_github_repo(chart_yaml_data)
        assert github_repo is not None
        version_tag = step._normalize_version_tag(chart_yaml_data["version"])
        assert version_tag is not None

        def expected_github_url(additional_path: str) -> str:
            source_file_path = os.path.join(os.path.abspath(config.chart_dir), additional_path)
            relative_to_root = os.path.relpath(source_file_path, repo_root).replace(os.sep, "/")
            return f"{step._github_raw_host}/{github_repo}/refs/tags/{version_tag}/{relative_to_root}"

        def monkey_write_chart_yaml(_: str, chart_yaml_file_name: str, data: Dict[str, Any]) -> None:
            annotation_base_url = f"{config.catalog_base_url}hello-world-app-{git_version}.tgz-meta/"
            annotations = data["annotations"]
            assert annotations["io.giantswarm.application.metadata"] == f"{annotation_base_url}main.yaml"
            assert annotations["io.giantswarm.application.values-schema"] == expected_github_url("./values.schema.json")
            assert annotations["io.giantswarm.application.readme"] == expected_github_url("../../README.md")

            restrictions = chart_yaml_data["restrictions"]
            for key, value in restrictions.items():
                kebab_key = step._oci_translated_keys[key]
                expected_value = step._format_restriction_value(value)  # type: ignore[attr-defined]
                assert annotations[f"io.giantswarm.application.restrictions.{kebab_key}"] == expected_value

            assert annotations["io.giantswarm.application.upstream-chart-url"] == chart_yaml_data["upstreamChartURL"]
            assert (
                annotations["io.giantswarm.application.upstream-chart-version"]
                == chart_yaml_data["upstreamChartVersion"]
            )

        monkeypatch.setattr("app_build_suite.build_steps.helm.os.path.isfile", lambda _: True)
        monkeypatch.setattr("app_build_suite.build_steps.helm.shutil.copy2", lambda _, __: True)
        monkeypatch.setattr(
            app_build_suite.build_steps.helm.HelmChartMetadataBuilder, "write_chart_yaml", monkey_write_chart_yaml
        )

        step.run(config, context)
        m.assert_called_once_with(input_chart_path, "r")


def test_generate_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    input_chart_path = os.path.join(os.path.dirname(__file__), "res_test_helm/Chart.yaml")
    step = HelmChartMetadataFinalizer()
    config = init_config_for_step(step)
    config.generate_metadata = True
    config.chart_dir = os.path.dirname(input_chart_path)

    with open(input_chart_path) as f:
        # input_chart_yaml = f.read()
        chart_yaml_data = yaml.safe_load(f)

    # run run
    chart_file_name = "hello-world-app-v0.0.1.tgz"
    chart_full_path = f"./{chart_file_name}"
    meta_dir_path = f"{chart_full_path}-meta"
    # with patch("app_build_suite.build_steps.helm.open", mock_open(read_data=input_chart_yaml)) as m:
    # chart_yaml_path = os.path.join(config.chart_dir, CHART_YAML)
    # with open(chart_yaml_path, "r") as file:
    # chart_yaml = yaml.safe_load(file)

    context = {
        context_key_chart_file_name: chart_file_name,
        context_key_chart_full_path: chart_full_path,
        context_key_meta_dir_path: meta_dir_path,
        context_key_original_chart_yaml: chart_yaml_data,
    }

    def monkey_sha256(path: str) -> str:
        assert path == chart_full_path
        return "123"

    def monkey_meta_write(_: str, meta_file_name: str, meta: Dict[str, Any]) -> None:
        assert meta_file_name == os.path.join(f"{chart_full_path}-meta", "main.yaml")
        input_meta_path = os.path.join(os.path.dirname(__file__), "res_test_helm/main.yaml")
        with open(input_meta_path) as t:
            expected_meta = yaml.safe_load(t)
        assert meta == expected_meta

    monkeypatch.setattr("app_build_suite.build_steps.helm.get_file_sha256", monkey_sha256)
    monkeypatch.setattr(
        app_build_suite.build_steps.helm.HelmChartMetadataFinalizer, "write_meta_file", monkey_meta_write
    )
    monkeypatch.setattr(
        app_build_suite.build_steps.helm.HelmChartMetadataFinalizer,
        "get_build_timestamp",
        lambda _: "1020-10-20T10:20:10.000000",
    )
    step.pre_run(config)
    step.run(config, context)
    # m.assert_called_with(input_chart_path, "r")


def test_format_timestamp_to_match_helms() -> None:
    ts_str = HelmChartMetadataFinalizer.get_build_timestamp()
    ts_regex = re.compile("^[0-9]{4}-(1[0-2]|0[1-9])-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9](.[0-9]+)?Z?$")
    assert ts_regex.fullmatch(ts_str)


class GiantSwarmTestValidator:
    def __init__(self, valid: bool, check_code: str) -> None:
        self.check_code = check_code
        self.valid = valid
        self.validate_called = False

    def validate(self, config: argparse.Namespace) -> bool:
        self.validate_called = True
        return self.valid

    def get_check_code(self) -> str:
        return self.check_code


@pytest.mark.parametrize(
    "validators,expected_exception,strict_mode,ignore_list",
    [
        ([GiantSwarmTestValidator(True, "W1")], False, True, ""),
        ([GiantSwarmTestValidator(False, "W1")], True, True, ""),
        ([GiantSwarmTestValidator(False, "W1")], False, True, "W1"),
        ([GiantSwarmTestValidator(False, "W1")], False, False, ""),
        (
            [
                GiantSwarmTestValidator(True, "W1"),
                GiantSwarmTestValidator(True, "W2"),
                GiantSwarmTestValidator(False, "W3"),
            ],
            True,
            True,
            "",
        ),
    ],
    ids=[
        "single valid",
        "single invalid",
        "failed in ignored",
        "failed in non-strict mode",
        "multiple with one invalid",
    ],
)
def test_giant_swarm_validator(
    validators: List[GiantSwarmTestValidator],
    expected_exception: bool,
    strict_mode: bool,
    ignore_list: str,
    mocker: MockerFixture,
) -> None:
    step = GiantSwarmHelmValidator()
    config = init_config_for_step(step)
    config.disable_strict_giantswarm_validator = not strict_mode
    config.giantswarm_validator_ignored_checks = ignore_list

    loader_mock = mocker.Mock(name="loader", return_value=validators)
    mocker.patch.object(step, "_load_giant_swarm_validators", loader_mock)

    try:
        step.pre_run(config)
    except ValidationError as ve:
        if not expected_exception:
            raise
        assert ve.source == "GiantSwarmHelmValidator"
        failed_regex = re.match(r"Giant Swarm validator '(\w+): GiantSwarmTestValidator' failed its checks\.", ve.msg)
        if not failed_regex:
            raise ValueError("Failed to find expected text in the raised exception")
        expected_to_fail = set(v.check_code for v in validators if not v.valid)
        assert failed_regex.group(1) in expected_to_fail

    assert all(v.validate_called for v in validators)
