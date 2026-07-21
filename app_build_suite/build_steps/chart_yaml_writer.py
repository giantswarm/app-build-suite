"""Build step: writes the in-context Chart.yaml dict to disk."""

import argparse
import logging
import os
import shutil
from typing import Set

import yaml
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType

from app_build_suite.build_steps.helm_consts import (
    CHART_YAML,
    BlockLiteralStr,
    context_key_changes_made,
    context_key_chart_yaml,
)
from app_build_suite.build_steps.steps import STEP_BUILD, STEP_METADATA

logger = logging.getLogger(__name__)


def _represent_block_literal(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style="|")


class ChartYamlDumper(yaml.SafeDumper):
    """YAML dumper that renders BlockLiteralStr values as block scalars.

    Only values explicitly wrapped in BlockLiteralStr (e.g. the 'artifacthub.io/links' annotation)
    are forced to block-scalar style; all other strings keep PyYAML's default rendering.
    """


ChartYamlDumper.add_representer(BlockLiteralStr, _represent_block_literal)


class ChartYamlWriter(BuildStep):
    """Writes the in-context Chart.yaml dict to disk, creating a backup."""

    @property
    def steps_provided(self) -> Set[StepType]:
        # Tag with both BUILD and METADATA so it runs when either is requested
        return {STEP_BUILD, STEP_METADATA}

    def run(self, config: argparse.Namespace, context: Context) -> None:
        """Writes the Chart.yaml dict from context to disk if changes were made."""
        if not context.get(context_key_changes_made, False):
            logger.debug("No changes were made to Chart.yaml, skipping write.")
            return

        chart_yaml_path = os.path.join(config.chart_dir, CHART_YAML)

        # Create backup from original on-disk file
        backup_path = chart_yaml_path + ".back"
        logger.debug(f"Saving backup of {CHART_YAML} in {CHART_YAML}.back")
        shutil.copy2(chart_yaml_path, backup_path)

        # Write context dict to disk
        with open(chart_yaml_path, "w") as f:
            yaml.dump(context[context_key_chart_yaml], f, Dumper=ChartYamlDumper, default_flow_style=False)
        logger.info(f"Saved modified {CHART_YAML} to disk.")
