"""Build step: loads Chart.yaml into context."""

import argparse
import logging
import os
from typing import Set

import yaml
from step_exec_lib.errors import ValidationError
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType

from app_build_suite.build_steps.helm_consts import (
    CHART_YAML,
    context_key_changes_made,
    context_key_chart_yaml,
)
from app_build_suite.build_steps.steps import STEP_BUILD, STEP_METADATA

logger = logging.getLogger(__name__)


class ChartYamlLoader(BuildStep):
    """Loads Chart.yaml into context as a parsed dict."""

    @property
    def steps_provided(self) -> Set[StepType]:
        # Tag with both BUILD and METADATA so it runs when either is requested
        return {STEP_BUILD, STEP_METADATA}

    def pre_run(self, config: argparse.Namespace) -> None:
        """Validates that the Chart.yaml file is readable and parseable."""
        chart_yaml_path = os.path.join(config.chart_dir, CHART_YAML)
        try:
            with open(chart_yaml_path, "r") as f:
                yaml.safe_load(f)
        except (OSError, yaml.YAMLError) as e:
            raise ValidationError(self.name, f"Cannot read/parse {CHART_YAML}: {e}")

    def run(self, config: argparse.Namespace, context: Context) -> None:
        """Loads Chart.yaml from disk and stores it in context."""
        chart_yaml_path = os.path.join(config.chart_dir, CHART_YAML)
        with open(chart_yaml_path, "r") as f:
            context[context_key_chart_yaml] = yaml.safe_load(f)
        # Initialize changes_made flag (moved from HelmGitVersionSetter)
        context[context_key_changes_made] = False
        logger.debug(f"Loaded {CHART_YAML} into context.")
