"""Tests for HelmVersionSetter build step."""

import logging
from typing import Any, Dict

import pytest

from app_build_suite.build_steps.helm_consts import (
    CHART_YAML_APP_VERSION_KEY,
    CHART_YAML_CHART_VERSION_KEY,
    context_key_changes_made,
    context_key_chart_yaml,
)
from app_build_suite.build_steps.helm_version_setter import HelmVersionSetter
from tests.build_steps.helpers import init_config_for_step


def _make_context() -> Dict[str, Any]:
    return {
        context_key_chart_yaml: {"version": "0.0.1", "appVersion": "0.0.1"},
        context_key_changes_made: False,
    }


def test_run_no_overrides_is_noop() -> None:
    step = HelmVersionSetter()
    config = init_config_for_step(step)
    context = _make_context()
    step.run(config, context)
    assert context[context_key_chart_yaml][CHART_YAML_CHART_VERSION_KEY] == "0.0.1"
    assert context[context_key_chart_yaml][CHART_YAML_APP_VERSION_KEY] == "0.0.1"
    assert context[context_key_changes_made] is False


def test_run_override_chart_version() -> None:
    step = HelmVersionSetter()
    config = init_config_for_step(step)
    config.override_chart_version = "1.2.3"
    context = _make_context()
    step.run(config, context)
    assert context[context_key_chart_yaml][CHART_YAML_CHART_VERSION_KEY] == "1.2.3"
    assert context[context_key_chart_yaml][CHART_YAML_APP_VERSION_KEY] == "0.0.1"
    assert context[context_key_changes_made] is True


def test_run_override_app_version() -> None:
    step = HelmVersionSetter()
    config = init_config_for_step(step)
    config.override_app_version = "2.3.4"
    context = _make_context()
    step.run(config, context)
    assert context[context_key_chart_yaml][CHART_YAML_APP_VERSION_KEY] == "2.3.4"
    assert context[context_key_chart_yaml][CHART_YAML_CHART_VERSION_KEY] == "0.0.1"
    assert context[context_key_changes_made] is True


def test_run_override_both_versions() -> None:
    step = HelmVersionSetter()
    config = init_config_for_step(step)
    config.override_chart_version = "1.2.3"
    config.override_app_version = "2.3.4"
    context = _make_context()
    step.run(config, context)
    assert context[context_key_chart_yaml][CHART_YAML_CHART_VERSION_KEY] == "1.2.3"
    assert context[context_key_chart_yaml][CHART_YAML_APP_VERSION_KEY] == "2.3.4"
    assert context[context_key_changes_made] is True


def test_pre_run_no_deprecated_flags_no_warning(caplog: pytest.LogCaptureFixture) -> None:
    step = HelmVersionSetter()
    config = init_config_for_step(step)
    with caplog.at_level(logging.WARNING):
        step.pre_run(config)
    assert caplog.text == ""


def test_pre_run_deprecated_chart_flag_warns(caplog: pytest.LogCaptureFixture) -> None:
    step = HelmVersionSetter()
    config = init_config_for_step(step)
    config.replace_chart_version_with_git = True
    with caplog.at_level(logging.WARNING):
        step.pre_run(config)
    assert "--replace-chart-version-with-git" in caplog.text
    assert "DEPRECATED" in caplog.text


def test_pre_run_deprecated_app_flag_warns(caplog: pytest.LogCaptureFixture) -> None:
    step = HelmVersionSetter()
    config = init_config_for_step(step)
    config.replace_app_version_with_git = True
    with caplog.at_level(logging.WARNING):
        step.pre_run(config)
    assert "--replace-app-version-with-git" in caplog.text
    assert "DEPRECATED" in caplog.text
