"""Build step: runs helm ct linter against the chart."""

import argparse
import logging
import os
from typing import Set

import configargparse
from step_exec_lib.errors import ValidationError
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType
from step_exec_lib.utils.processes import run_and_log

from app_build_suite.build_steps.steps import STEP_VALIDATE
from app_build_suite.errors import BuildError

logger = logging.getLogger(__name__)


class HelmChartToolLinter(BuildStep):
    """
    Runs helm ct linter against the chart.
    """

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_VALIDATE}

    _ct_bin = "ct"
    _min_ct_version = "3.5.1"
    _max_ct_version = "4.0.0"
    _metadata_schema = "gs_metadata_chart_schema.yaml"

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--ct-config",
            required=False,
            help="Path to optional 'ct' lint config file.",
        )
        config_parser.add_argument(
            "--ct-schema",
            required=False,
            help="Path to optional 'ct' schema file.",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        """
        Verifies if the required version of `ct` is installed and config options are sane.
        :param config: the config object
        :return: None
        """
        # verify if binary present
        self._assert_binary_present_in_path(self._ct_bin)
        # verify version
        run_res = run_and_log([self._ct_bin, "version"], capture_output=True)  # nosec
        version_line = run_res.stdout.splitlines()[0]
        version = version_line.split(":")[1].strip()
        self._assert_version_in_range(self._ct_bin, version, self._min_ct_version, self._max_ct_version)
        # validate config options
        if config.ct_config is not None and not os.path.isabs(config.ct_config):
            config.ct_config = os.path.join(os.getcwd(), config.ct_config)
        if config.ct_config is not None and not os.path.isfile(config.ct_config):
            raise ValidationError(
                self.name,
                f"Chart tool config file {config.ct_config} doesn't exist.",
            )
        # if we're validating a metadata enabled project (for Giant Swarm App Platform),
        # we have to use the modified schema
        if config.generate_metadata:
            full_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "resources",
                "ct_schemas",
                self._metadata_schema,
            )
            logger.info(
                f"Metadata generation was requested, changing default validation schema to '{self._metadata_schema}'"
            )
            config.ct_schema = full_path
        # validate schema path
        if config.ct_schema is not None and not os.path.isabs(config.ct_schema):
            config.ct_schema = os.path.join(os.getcwd(), config.ct_schema)
        if config.ct_schema is not None and not os.path.isfile(config.ct_schema):
            raise ValidationError(
                self.name,
                f"Chart tool schema file {config.ct_schema} doesn't exist.",
            )

    def run(self, config: argparse.Namespace, _: Context) -> None:
        args = [
            self._ct_bin,
            "lint",
            "--validate-maintainers=false",
            f"--charts={config.chart_dir}",
        ]
        if config.debug:
            args.append("--debug")
        if config.ct_config is not None:
            args.append(f"--config={config.ct_config}")
        if config.ct_schema is not None:
            args.append(f"--chart-yaml-schema={config.ct_schema}")
        logger.info("Running chart tool linting")
        run_res = run_and_log(args, capture_output=True)  # nosec, input params checked above in pre_run
        for line in run_res.stdout.splitlines():
            logger.info(line)
        if run_res.returncode != 0:
            logger.error(f"{self._ct_bin} run failed with exit code {run_res.returncode}")
            raise BuildError(self.name, "Linting failed")
