"""Build step: validates the chart directory contains a valid Helm chart."""

import argparse
import logging
import os
from typing import Set

import configargparse
import yaml
from step_exec_lib.errors import ValidationError
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType

from app_build_suite.build_steps.helm_consts import CHART_YAML, VALUES_YAML
from app_build_suite.build_steps.steps import STEP_BUILD

logger = logging.getLogger(__name__)


class HelmBuilderValidator(BuildStep):
    """
    Very simple validator that checks if the folder looks like Helm chart at all.
    Also validates that the chart name is RFC 1123 compliant.
    """

    _RFC1123_MAX_LENGTH = 63

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_BUILD}

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "-c",
            "--chart-dir",
            required=False,
            default=".",
            help="Path to the Helm Chart to build.",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        """Validates if basic chart files are present in the configured directory."""
        if not (
            os.path.exists(os.path.join(config.chart_dir, CHART_YAML))
            and os.path.exists(os.path.join(config.chart_dir, VALUES_YAML))
        ):
            raise ValidationError(self.name, f"Can't find '{CHART_YAML}' or '{VALUES_YAML}' files.")

        # Validate chart name is RFC 1123 compliant
        self._validate_chart_name_rfc1123(config)

    def _validate_chart_name_rfc1123(self, config: argparse.Namespace) -> None:
        """Validates that Chart.yaml 'name' field complies with RFC 1123 DNS label rules.

        RFC 1123 DNS label rules:
        - Max 63 characters
        - Must start with lowercase alphanumeric
        - Must end with lowercase alphanumeric
        - Only lowercase alphanumeric and hyphens allowed
        - Cannot be empty
        """
        chart_yaml_path = os.path.join(config.chart_dir, CHART_YAML)
        with open(chart_yaml_path, "r") as file:
            chart_yaml = yaml.safe_load(file)

        # Check if 'name' field exists
        if "name" not in chart_yaml:
            raise ValidationError(self.name, f"'{CHART_YAML}' is missing required field 'name'.")

        name = chart_yaml["name"]

        # Check if name is empty
        if name is None or name == "":
            raise ValidationError(self.name, f"'{CHART_YAML}' field 'name' is empty.")

        name = str(name)
        errors = []

        # Check length
        if len(name) > self._RFC1123_MAX_LENGTH:
            errors.append(
                f"Name exceeds maximum length of {self._RFC1123_MAX_LENGTH} characters (actual length: {len(name)})."
            )

        # Check first character
        if name and not (name[0].islower() or name[0].isdigit()):
            errors.append(
                f"Name must start with a lowercase alphanumeric character, but starts with '{name[0]}' at position 0."
            )

        # Check last character
        if name and not (name[-1].islower() or name[-1].isdigit()):
            errors.append(
                f"Name must end with a lowercase alphanumeric character, "
                f"but ends with '{name[-1]}' at position {len(name) - 1}."
            )

        # Find all invalid characters with positions
        invalid_chars = []
        for pos, char in enumerate(name):
            if char == "-" or char.isdigit() or char.islower():
                continue
            invalid_chars.append((pos, char))

        if invalid_chars:
            char_list = ", ".join(f"'{c}' at position {p}" for p, c in invalid_chars)
            errors.append(
                f"Name contains invalid characters. Only lowercase alphanumeric "
                f"and hyphens are allowed. Invalid characters found: {char_list}."
            )

        if errors:
            error_msg = f"Chart name '{name}' violates RFC 1123 DNS label rules:\n"
            for error in errors:
                error_msg += f"  - {error}\n"
            raise ValidationError(self.name, error_msg)

    def run(self, config: argparse.Namespace, context: Context) -> None:
        pass
