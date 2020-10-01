import argparse
import shutil
from abc import ABC, abstractmethod
from typing import List, NewType

import configargparse
import semver

from app_build_suite.build_steps.errors import ValidationError

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
