import argparse
import logging
import shutil
import sys
from abc import ABC, abstractmethod
from typing import List, NewType, Callable, Set

import configargparse
import semver

from app_build_suite.build_steps.errors import ValidationError, Error

logger = logging.getLogger(__name__)

StepType = NewType("StepType", str)
STEP_ALL = StepType("all")
STEP_BUILD = StepType("build")
STEP_METADATA = StepType("metadata")
STEP_TEST_ALL = StepType("test_all")
STEP_TEST_UNIT = StepType("test_unit")
ALL_STEPS = [STEP_ALL, STEP_BUILD, STEP_METADATA, STEP_TEST_ALL, STEP_TEST_UNIT]


class BuildStep(ABC):
    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    @abstractmethod
    def steps_provided(self) -> List[StepType]:
        raise NotImplementedError

    @abstractmethod
    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        raise NotImplementedError

    @abstractmethod
    def pre_run(self, config: argparse.Namespace) -> None:
        raise NotImplementedError

    @abstractmethod
    def run(self, config: argparse.Namespace) -> None:
        raise NotImplementedError

    @abstractmethod
    def cleanup(self, config: argparse.Namespace) -> None:
        raise NotImplementedError

    def _assert_binary_present_in_path(self, bin_name: str) -> None:
        if shutil.which(bin_name) is None:
            raise ValidationError(
                self.name,
                f"Can't find {bin_name} executable. Please make sure it's installed.",
            )

    def _assert_version_in_range(
        self, app_name: str, version: str, min_version: str, max_version: str
    ) -> None:
        if version.startswith("v"):
            version = version[1:]
        parsed_ver = semver.VersionInfo.parse(version)
        parsed_min_version = semver.VersionInfo.parse(min_version)
        parsed_max_version = semver.VersionInfo.parse(max_version)
        if parsed_ver < parsed_min_version:
            raise ValidationError(
                self.name,
                f"Min version '{min_version}' of '{app_name}' is required, '{parsed_ver}' found.",
            )
        if parsed_ver >= parsed_max_version:
            raise ValidationError(
                self.name,
                f"Version '{parsed_ver}' of '{app_name}' is detected, but lower than {max_version} is required.",
            )


class BuildStepsPipeline(BuildStep):
    def __init__(self, pipeline: List[BuildStep]):
        self._pipeline = pipeline

    @property
    def steps_provided(self) -> List[StepType]:
        all_steps: Set[StepType] = set()
        for build_step in self._pipeline:
            all_steps.union(build_step.steps_provided)
        return list(all_steps)

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        group = config_parser.add_argument_group("helm3 build engine options")
        for build_step in self._pipeline:
            build_step.initialize_config(group)

    def pre_run(self, config: argparse.Namespace) -> None:
        self._iterate_steps(config, "pre-run", 2, lambda step: step.pre_run(config))

    def run(self, config: argparse.Namespace) -> None:
        self._iterate_steps(config, "build", 3, lambda step: step.run(config))

    def cleanup(self, config: argparse.Namespace) -> None:
        self._iterate_steps(config, "cleanup", 4, lambda step: step.cleanup(config))

    def _iterate_steps(
        self,
        config: configargparse.Namespace,
        stage: str,
        error_exit_code: int,
        step_function: Callable[[BuildStep], None],
    ) -> None:
        for step in self._pipeline:
            if STEP_ALL in config.steps or any(
                s in step.steps_provided for s in config.steps
            ):
                logger.info(f"Running {stage} step for {step.name}")
                try:
                    step_function(step)
                except Error as e:
                    logger.error(
                        f"Error when running {stage} step for {step.name}: {e.msg}"
                    )
                    sys.exit(error_exit_code)
            else:
                logger.info(
                    f"Skipping {stage} step for {step.name} as it was not configured to run."
                )
