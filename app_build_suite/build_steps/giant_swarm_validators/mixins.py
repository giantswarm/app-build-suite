import argparse
import os

import yaml
from app_build_suite.build_steps.giant_swarm_validators.errors import (
    GiantSwarmValidatorError,
)

from app_build_suite.build_steps.helm_consts import CHART_YAML


class UseChartYaml:
    def get_chart_yaml(self, config: argparse.Namespace) -> dict:
        chart_yaml_path = os.path.join(config.chart_dir, CHART_YAML)

        if not os.path.exists(chart_yaml_path):
            raise GiantSwarmValidatorError(f"Can't find file '{chart_yaml_path}'.")
        with open(chart_yaml_path, "r") as stream:
            try:
                chart_yaml = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                raise GiantSwarmValidatorError(f"Error parsing YAML file '{chart_yaml_path}'. Error: {exc}.")
        return chart_yaml
