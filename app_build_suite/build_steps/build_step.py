import argparse
from abc import ABC, abstractmethod
from typing import List, NewType

import configargparse

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
