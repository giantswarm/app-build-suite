"""Build step: runs helm dependency update."""

import argparse
import logging
import os
import shutil
from typing import List, Set

from step_exec_lib.errors import ValidationError
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType
from step_exec_lib.utils.processes import run_and_log

from app_build_suite.build_steps.helm_consts import (
    CHART_LOCK,
    REQUIREMENTS_LOCK,
    context_key_chart_lock_files_to_restore,
)
from app_build_suite.build_steps.steps import STEP_BUILD
from app_build_suite.errors import BuildError

logger = logging.getLogger(__name__)


class HelmRequirementsUpdater(BuildStep):
    """
    Executes helm dependency update.
    """

    _helm_bin = "helm"
    _min_helm_version = "3.8.1"
    _max_helm_version = "4.0.0"

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_BUILD}

    # noinspection PyMethodMayBeStatic
    def _should_run(self, config: argparse.Namespace) -> bool:
        return config.replace_chart_version_with_git

    # noinspection PyMethodMayBeStatic
    def _detect_chart_lock_files(self, config: argparse.Namespace) -> List[str]:
        lock_files = []
        if os.path.isfile(os.path.join(config.chart_dir, CHART_LOCK)):
            lock_files.append(CHART_LOCK)
        if os.path.isfile(os.path.join(config.chart_dir, REQUIREMENTS_LOCK)):
            lock_files.append(REQUIREMENTS_LOCK)
        return lock_files

    def pre_run(self, config: argparse.Namespace) -> None:
        """
        Checks if the required version of helm is installed and if a lock file is present.
        :param config: the config object
        :return: None
        """
        if not self._should_run(config):
            logger.debug("No chart version override requested, skipping dependency update.")
            return
        if len(self._detect_chart_lock_files(config)) == 0:
            logger.debug(f"No {CHART_LOCK} or {REQUIREMENTS_LOCK} file exists, skipping dependency update.")
            return
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
        Runs 'helm dependencies update' to update or generate a Chart.lock file.
        :param config: the config object
        :param context: the context object
        :return: None
        """
        context[context_key_chart_lock_files_to_restore] = []
        present_lock_files = self._detect_chart_lock_files(config)
        if not self._should_run(config):
            logger.debug("No chart version override requested. Dependency update not required, ending step.")
            return
        if len(present_lock_files) == 0:
            logger.debug(f"No {CHART_LOCK} or {REQUIREMENTS_LOCK} file exists, skipping dependency update.")
            return
        args = [
            self._helm_bin,
            "dependencies",
            "update",
            config.chart_dir,
        ]
        for lock_file in present_lock_files:
            logger.debug(f"Saving backup of {lock_file} in {lock_file}.back")
            lock_path = os.path.join(config.chart_dir, lock_file)
            shutil.copy2(lock_path, lock_path + ".back")
            context[context_key_chart_lock_files_to_restore].append(lock_file)
        logger.info(f"Updating lockfile(s) with 'helm dependencies update {config.chart_dir}'")
        run_res = run_and_log(args, capture_output=True)  # nosec, input params checked above in pre_run
        if run_res.returncode != 0:
            logger.error(f"{self._helm_bin} run failed with exit code {run_res.returncode}")
            raise BuildError(self.name, "Chart dependency update failed")
