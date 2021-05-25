"""This is a module that includes main components of the app"""
import logging
import sys
from typing import List

import configargparse

from app_build_suite.build_steps import BuildStep
from step_exec_lib.errors import Error
from step_exec_lib.types import Context

logger = logging.getLogger(__name__)


class Runner:
    """
    A class used to run all the steps of a build pipeline. Expects to get a list of configured
    BuildSteps and a config. Provides context object.
    """

    def __init__(self, config: configargparse.Namespace, steps: List[BuildStep]):
        self._config = config
        self._steps = steps
        self._context: Context = {}
        self._failed_build = False

    @property
    def context(self):
        return self._context

    def run(self) -> None:
        self.run_pre_steps()
        self.run_build_steps()
        self.run_cleanup()
        if self._failed_build is True:
            logger.error("Exit 1 due to failed build step.")
            sys.exit(1)

    def run_pre_steps(self) -> None:
        try:
            for step in self._steps:
                step.pre_run(self._config)
        except Error as e:
            logger.error(f"Error when running pre-steps: {e}. Exiting.")
            sys.exit(1)

    def run_build_steps(self) -> None:
        try:
            for step in self._steps:
                step.run(self._config, self._context)
        except Error as e:
            logger.error(f"Error when running build: {e}. No further build steps will be performed, moving to cleanup.")
            self._failed_build = True

    def run_cleanup(self) -> None:
        for step in self._steps:
            try:
                step.cleanup(self._config, self._context, self._failed_build)
            except Error as e:
                logger.error(f"Last cleanup step failed: {e}. Moving to the next one.")
