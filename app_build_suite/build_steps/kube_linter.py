"""Build step: runs kube-linter against the chart."""

import argparse
import logging
import os
from typing import Set

import configargparse
from step_exec_lib.errors import ValidationError
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType
from step_exec_lib.utils.processes import run_and_log

from app_build_suite.build_steps.steps import STEP_STATIC_CHECK
from app_build_suite.errors import BuildError

logger = logging.getLogger(__name__)


class KubeLinter(BuildStep):
    """
    Runs kube-linter against the chart.
    """

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_STATIC_CHECK}

    _kubelinter_bin = "kube-linter"
    _min_kubelinter_version = "0.2.5"
    _max_kubelinter_version = "1.0.0"
    _default_kubelinter_cfg_file = ".kube-linter.yaml"

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--kubelinter-config",
            required=False,
            help=f"Path to optional 'kube-linter' config file. If empty, tries to load "
            f"'{self._default_kubelinter_cfg_file}'.",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        """
        Verifies if the required version of `kube-linter` is installed and config options are sane.
        :param config: the config object
        :return: None
        """
        # verify if binary present
        self._assert_binary_present_in_path(self._kubelinter_bin)
        # verify version
        run_res = run_and_log([self._kubelinter_bin, "version"], capture_output=True)  # nosec
        version = run_res.stdout.splitlines()[0]
        self._assert_version_in_range(
            self._kubelinter_bin,
            version,
            self._min_kubelinter_version,
            self._max_kubelinter_version,
        )
        # validate config options
        if config.kubelinter_config is not None and not os.path.isabs(config.kubelinter_config):
            config.kubelinter_config = os.path.join(os.getcwd(), config.kubelinter_config)
        if config.kubelinter_config is not None and not os.path.isfile(config.kubelinter_config):
            raise ValidationError(
                self.name,
                f"Kube-linter config file {config.kubelinter_config} doesn't exist.",
            )
        _default_cfg_path = os.path.join(config.chart_dir, self._default_kubelinter_cfg_file)
        if not config.kubelinter_config and os.path.isfile(_default_cfg_path):
            config.kubelinter_config = _default_cfg_path

    def run(self, config: argparse.Namespace, _: Context) -> None:
        args = [
            self._kubelinter_bin,
            "lint",
            config.chart_dir,
            "--verbose",
        ]

        # adding `--verbose` to the default args due to the kube-linter hiding
        # some problems and thus skipping linting some of the resources.

        if config.kubelinter_config is not None:
            args.append(f"--config={config.kubelinter_config}")
        logger.info("Running kube-linter tool")
        run_res = run_and_log(args, capture_output=True)  # nosec, input params checked above in pre_run
        for line in run_res.stdout.splitlines():
            logger.info(line)
        if run_res.returncode != 0:
            logger.error(f"{self._kubelinter_bin} run failed with exit code {run_res.returncode}")
            for line in run_res.stderr.splitlines():
                logger.error(line)
            raise BuildError(self.name, "kube-linter failed")
