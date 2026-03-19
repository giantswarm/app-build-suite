"""Build step: restores Chart.yaml from backup after the build."""

import argparse
import logging
import os
import shutil
from typing import Set

import configargparse
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType

from app_build_suite.build_steps.helm_consts import (
    CHART_YAML,
    context_key_changes_made,
    context_key_chart_lock_files_to_restore,
)
from app_build_suite.build_steps.steps import STEP_BUILD

logger = logging.getLogger(__name__)


class HelmChartYAMLRestorer(BuildStep):
    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_BUILD}

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--keep-chart-changes",
            required=False,
            action="store_true",
            help=f"Should the changes made in {CHART_YAML} be kept",
        )

    def run(self, config: argparse.Namespace, context: Context) -> None:
        # nothing to do here, we run in cleanup
        pass

    def cleanup(
        self,
        config: argparse.Namespace,
        context: Context,
        has_build_failed: bool,
    ) -> None:
        if config.keep_chart_changes:
            logger.info(f"Skipping restore of {CHART_YAML}.")
            return
        if context_key_changes_made in context and context[context_key_changes_made]:
            logger.info(f"Restoring backup {CHART_YAML}.back to {CHART_YAML}")
            chart_yaml_path = os.path.join(config.chart_dir, CHART_YAML)
            shutil.move(chart_yaml_path + ".back", chart_yaml_path)
        if context_key_chart_lock_files_to_restore in context and context[context_key_chart_lock_files_to_restore]:
            for file_name in context[context_key_chart_lock_files_to_restore]:
                logger.info(f"Restoring backup {file_name}.back to {file_name}")
                lock_file_path = os.path.join(config.chart_dir, file_name)
                shutil.move(lock_file_path + ".back", lock_file_path)
