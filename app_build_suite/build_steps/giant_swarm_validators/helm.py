import argparse
import logging
import os
import re

import yaml
from step_exec_lib.errors import Error

from app_build_suite.build_steps.helm_consts import VALUES_SCHEMA_JSON, CHART_YAML, TEMPLATES_DIR, HELPERS_YAML

logger = logging.getLogger(__name__)


ANNOTATIONS_KEY = "annotations"
GS_TEAM_LABEL_KEY = "application.giantswarm.io/team"


class GiantSwarmValidatorError(Error):
    pass


class HasValuesSchema:
    def validate(self, config: argparse.Namespace) -> bool:
        return os.path.exists(os.path.join(config.chart_dir, VALUES_SCHEMA_JSON))


class HasTeamLabel:

    escaped_label = re.escape(GS_TEAM_LABEL_KEY)
    _label_regexp = (
        escaped_label
        + r':[ \t]+{{[ \t]*index[ \t]+\.Chart\.Annotations[ \t]+"'
        + escaped_label
        + r'"[ \t]*\|[ \t]*quote[ \t]*}}[ \t]*'
    )

    def validate(self, config: argparse.Namespace) -> bool:
        chart_yaml_path = os.path.join(config.chart_dir, CHART_YAML)

        # check if team label is used in Chart.yaml
        if not os.path.exists(chart_yaml_path):
            raise GiantSwarmValidatorError(f"Can't find file '{chart_yaml_path}'.")
        with open(chart_yaml_path, "r") as stream:
            try:
                chart_yaml = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                raise GiantSwarmValidatorError(f"Error parsing YAML file '{chart_yaml}'. Error: {exc}.")
        if ANNOTATIONS_KEY not in chart_yaml or GS_TEAM_LABEL_KEY not in chart_yaml[ANNOTATIONS_KEY]:
            logger.info(f"'{GS_TEAM_LABEL_KEY}' annotation not found in '{CHART_YAML}'.")
            return False

        # check if team label is not empty
        if chart_yaml[ANNOTATIONS_KEY][GS_TEAM_LABEL_KEY] is None:
            logger.info(f"'{GS_TEAM_LABEL_KEY}' is present in '{CHART_YAML}', but it's empty.")
            return False

        # Check if _helpers.yaml exists and uses team label
        helpers_file_path = os.path.join(config.chart_dir, TEMPLATES_DIR, HELPERS_YAML)
        if not os.path.exists(helpers_file_path):
            raise GiantSwarmValidatorError(f"Can't find file '{helpers_file_path}'.")
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
