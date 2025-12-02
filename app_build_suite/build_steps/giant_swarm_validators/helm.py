"""
General idea for naming validation checks:
- comply to 1 letter + 4 digits pattern
- check types and first letters:
  - file system layout and structure: "F"
  - Chart.yaml related problems "C"
"""

import argparse
import logging
import os
import re
from app_build_suite.build_steps.giant_swarm_validators.errors import GiantSwarmValidatorError

from app_build_suite.build_steps.giant_swarm_validators.mixins import UseChartYaml

from app_build_suite.build_steps.helm_consts import (
    VALUES_SCHEMA_JSON,
    CHART_YAML,
    TEMPLATES_DIR,
    HELPERS_YAML,
    HELPERS_TPL,
)

logger = logging.getLogger(__name__)


ANNOTATIONS_KEY = "annotations"
GS_TEAM_LABEL_KEY = "application.giantswarm.io/team"
GS_TEAM_LABEL_KEY_OCI = "io.giantswarm.application.team"


class HasValuesSchema:
    def get_check_code(self) -> str:
        return "F0001"

    def validate(self, config: argparse.Namespace) -> bool:
        return os.path.exists(os.path.join(config.chart_dir, VALUES_SCHEMA_JSON))


class HasTeamLabel(UseChartYaml):
    escaped_label = re.escape(GS_TEAM_LABEL_KEY)
    _label_regexp = (
        r"[ \t]*"
        + escaped_label
        + r':[ \t]+{{[ \t]*index[ \t]+\.Chart\.Annotations[ \t]+"'
        + escaped_label
        + r'"[ \t]*(\|[ \t]*default[ \t]+\"[a-zA-Z0-9]+\"[ \t]+){0,1}\|[ \t]*quote[ \t]*}}[ \t]*'
    )

    def get_check_code(self) -> str:
        return "C0001"

    def validate(self, config: argparse.Namespace) -> bool:
        chart_yaml = self.get_chart_yaml(config)

        if ANNOTATIONS_KEY not in chart_yaml or (
            GS_TEAM_LABEL_KEY not in chart_yaml[ANNOTATIONS_KEY]
            and GS_TEAM_LABEL_KEY_OCI not in chart_yaml[ANNOTATIONS_KEY]
        ):
            logger.info(f"'{GS_TEAM_LABEL_KEY}' or '{GS_TEAM_LABEL_KEY_OCI}' annotation not found in '{CHART_YAML}'.")
            return False

        team_label = (
            chart_yaml[ANNOTATIONS_KEY][GS_TEAM_LABEL_KEY]
            if GS_TEAM_LABEL_KEY in chart_yaml[ANNOTATIONS_KEY]
            else chart_yaml[ANNOTATIONS_KEY][GS_TEAM_LABEL_KEY_OCI]
        )
        # check if team label is not empty
        if team_label is None:
            logger.info(
                f"'{GS_TEAM_LABEL_KEY}' or '{GS_TEAM_LABEL_KEY_OCI}' is present in '{CHART_YAML}', but it's empty."
            )
            return False

        # Check if _helpers.yaml or _helpers.tpl exists and uses team label
        helpers_file_path = self.get_helpers_file_path(config)
        with open(helpers_file_path, "r") as stream:
            try:
                helpers_yaml_lines = stream.readlines()
            except OSError as exc:
                logger.warning(f"Error reading file '{helpers_file_path}'. Error: {exc}.")
                return False
        label_regexp = re.compile(self._label_regexp)
        if any(label_regexp.match(line) for line in helpers_yaml_lines):
            return True
        logger.info(f"The expected team label not found in '{helpers_file_path}'.")
        logger.info(f"'{helpers_file_path}' must contain a line that matches the regexp '{label_regexp}'.")
        return False

    def get_helpers_file_path(self, config: argparse.Namespace) -> str:
        helpers_file_path = os.path.join(config.chart_dir, TEMPLATES_DIR, HELPERS_YAML)
        if not os.path.exists(helpers_file_path):
            helpers_file_path = os.path.join(config.chart_dir, TEMPLATES_DIR, HELPERS_TPL)
            if not os.path.exists(helpers_file_path):
                raise GiantSwarmValidatorError(
                    f"Template file '{HELPERS_YAML}' or '{HELPERS_TPL}' not found in '{TEMPLATES_DIR}' directory."
                )
        return helpers_file_path
