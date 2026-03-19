"""Build step: builds a helm chart using helm package."""

import argparse
import logging
import os
from typing import Set

import configargparse
from step_exec_lib.errors import ValidationError
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType
from step_exec_lib.utils.processes import run_and_log

from app_build_suite.build_steps.helm_consts import (
    context_key_chart_file_name,
    context_key_chart_full_path,
)
from app_build_suite.build_steps.steps import STEP_BUILD
from app_build_suite.errors import BuildError

logger = logging.getLogger(__name__)


class HelmChartBuilder(BuildStep):
    """
    Builds a helm chart using helm3.
    """

    _helm_bin = "helm"
    _min_helm_version = "3.2.0"
    _max_helm_version = "4.0.0"

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_BUILD}

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--destination",
            required=False,
            default=".",
            help="Path of a directory to store the packaged tgz.",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        """
        Checks if the required version of helm is installed.
        :param config: the config object
        :return: None
        """
        self._assert_binary_present_in_path(self._helm_bin)
        run_res = run_and_log([self._helm_bin, "version"], capture_output=True)  # nosec
        version_line = run_res.stdout.splitlines()[0]
        prefix = "version.BuildInfo"
        if version_line.startswith(prefix):
            version_line = version_line[len(prefix) :].strip("{}")
        else:
            raise ValidationError(self.name, f"Can't parse '{self._helm_bin}' version number.")
        version_entries = version_line.split(",")[0]
        version = version_entries.split(":")[1].strip('"')
        self._assert_version_in_range(self._helm_bin, version, self._min_helm_version, self._max_helm_version)

    def run(self, config: argparse.Namespace, context: Context) -> None:
        """
        Runs 'helm package' to build the chart.
        :param config: the config object
        :param context: the context object
        :return: None
        """
        args = [
            self._helm_bin,
            "package",
            config.chart_dir,
            "--destination",
            config.destination,
        ]
        logger.info("Building chart with 'helm package'")
        run_res = run_and_log(args, capture_output=True)  # nosec, input params checked above in pre_run
        for line in run_res.stdout.splitlines():
            logger.info(line)
            if line.startswith("Successfully packaged chart and saved it to"):
                full_chart_path = line.split(":")[1].strip()
                full_chart_path = os.path.abspath(full_chart_path)
                # compare our expected chart_file_name with the one returned from helm and fail if differs
                helm_chart_file_name = os.path.basename(full_chart_path)
                if (
                    context_key_chart_file_name in context
                    and helm_chart_file_name != context[context_key_chart_file_name]
                ):
                    raise BuildError(
                        self.name,
                        f"unexpected chart path '{helm_chart_file_name}' != '{context[context_key_chart_file_name]}'",
                    )
                if context_key_chart_full_path in context and full_chart_path != context[context_key_chart_full_path]:
                    raise BuildError(
                        self.name,
                        f"unexpected helm build result: path reported in output '{full_chart_path}' "
                        f"is not equal to '{context[context_key_chart_full_path]}'",
                    )
        if run_res.returncode != 0:
            logger.error(f"{self._helm_bin} run failed with exit code {run_res.returncode}")
            raise BuildError(self.name, "Chart build failed")
