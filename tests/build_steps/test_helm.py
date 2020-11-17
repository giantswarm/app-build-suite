import os.path
from typing import Dict, Any
from unittest.mock import mock_open, patch

import yaml

import app_build_suite
from app_build_suite.build_steps.helm import (
    HelmChartMetadataFinalizer,
    context_key_chart_file_name,
    context_key_chart_full_path,
)
from tests.build_steps.dummy_build_step import init_config_for_step


def test_generate_metadata(monkeypatch):
    input_chart_path = os.path.join(os.path.dirname(__file__), "res_test_helm/Chart.yaml")
    step = HelmChartMetadataFinalizer()
    config = init_config_for_step(step)
    config.generate_metadata = True
    config.chart_dir = os.path.dirname(input_chart_path)

    with open(input_chart_path) as f:
        input_chart_yaml = f.read()

    # run pre_run
    with patch("app_build_suite.build_steps.helm.open", mock_open(read_data=input_chart_yaml)) as m:
        step.pre_run(config)
        m.assert_called_once_with(input_chart_path, "r")

    # run run
    chart_file_name = "hello-world-app-v0.0.1.tgz"
    chart_full_path = f"./{chart_file_name}"
    with patch("app_build_suite.build_steps.helm.open", mock_open(read_data=input_chart_yaml)) as m:
        context = {
            context_key_chart_file_name: chart_file_name,
            context_key_chart_full_path: chart_full_path,
        }

        def monkey_sha256(path: str) -> str:
            assert path == chart_full_path
            return "123"

        def monkey_meta_write(_, meta_file_name: str, meta: Dict[str, Any]):
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
            lambda _: "1020-10-20T10:20:10+00:00",
        )
        step.run(config, context)
        m.assert_called_with(input_chart_path, "r")
