"""Basic building block for implementing BuildSteps and Pipelines"""
import argparse
import logging
from abc import ABC, abstractmethod
from typing import List, NewType, Callable, Set, cast, Optional

import configargparse

from app_build_suite.errors import Error
from app_build_suite.types import Context
from app_build_suite.utils import files, config as abs_config

logger = logging.getLogger(__name__)

StepType = NewType("StepType", str)
STEP_ALL = StepType("all")
STEP_BUILD = StepType("build")
STEP_METADATA = StepType("metadata")
STEP_TEST_ALL = StepType("test_all")
STEP_VALIDATE = StepType("test_validate")
STEP_TEST_SMOKE = StepType("test_smoke")
STEP_TEST_FUNCTIONAL = StepType("test_functional")
STEP_TEST_PERFORMANCE = StepType("test_performance")
STEP_TEST_COMPATIBILITY = StepType("test_compatibility")
ALL_STEPS = {
    STEP_ALL,
    STEP_BUILD,
    STEP_METADATA,
    STEP_TEST_ALL,
    STEP_VALIDATE,
    STEP_TEST_SMOKE,
    STEP_TEST_FUNCTIONAL,
    STEP_TEST_PERFORMANCE,
    STEP_TEST_COMPATIBILITY,
}


class BuildStep(ABC):
    """
    BuildStep is an abstract base class that defines interface for any real build steps.

    All the BuildSteps are executed by the main logic in such a way that first all initialize_config
    methods are called, then sequentially pre_run methods of all the BuildSteps, then all run calls
    and after that all cleanup steps. Therefore, you should use the methods as follows:
    - initialize_config must be used for adding BuildStep specific config options only
    - pre_run, if defined, is used for "fail fast" logic; check any assumptions and validations
      you can check *quickly* at this stage; failing here will fail the whole pipeline and not
      even get to the run step, providing immediate feedback that the build can't be done
    - run is the only method expected to run long lasting jobs and to execute actual build steps
      that can be later re-used by next steps
    - since results of executing run of one BuildStep can be later re-used by a subsequent BuildStep,
      yet you might want to do a proper cleanup after the build is done, the cleanup method is called
      only after the run method of all BuildSteps is executed.
    """

    @property
    def name(self) -> str:
        """
        The name of the step.
        :return: By default returns the name of the implementing class.
        """
        return self.__class__.__name__

    @property
    @abstractmethod
    def steps_provided(self) -> Set[StepType]:
        """
        This defines types of steps this BuildStep should be executed for. If a user filters the set of steps
        and the steps listed here don't match any of the steps selected by the user, the whole BuildStep
        won't be executed for this run.
        :return: Returns a list with elements from ALL_STEPS.
        """
        raise NotImplementedError

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        """
        Provide configuration options supported by this BuildStep. Needs to only act on ArgParser and can't
        run any blocking/long operations.
        :param config_parser: configargparse.ArgParser to add the configuration options to.
        :return: None
        """
        pass  # pragma: no cover

    def pre_run(self, config: argparse.Namespace) -> None:
        """
        Execute any pre-run validation or assertion logic.
        :param config: Ready (parsed) configuration Namespace object.
        :return: None
        """
        pass  # pragma: no cover

    @abstractmethod
    def run(self, config: argparse.Namespace, context: Context) -> None:
        """
        Execute actual build action of the BuildStep.
        :param context: A context where different components can save data to share with other components.
        :param config: Ready (parsed) configuration Namespace object.
        :return: None
        """
        raise NotImplementedError

    def cleanup(
        self,
        config: argparse.Namespace,
        context: Context,
        has_build_failed: bool,
    ) -> None:
        """
        Clean up any resources used during the BuildStep.
        :param context: A context where different components can save data to share with other components.
        :param has_build_failed: A boolean set to True if the cleanup is run after any of the BuildSteps
        failed their run step
        :param config: Ready (parsed) configuration Namespace object.
        :return: None
        """
        pass  # pragma: no cover

    def _assert_binary_present_in_path(self, bin_name: str) -> None:
        """
        Checks if binary is available in the system. Raises ValidationError if not found.
        :param bin_name: The name of the binary executable.
        :return: None.
        """
        files.assert_binary_present_in_path(self.name, bin_name)

    def _assert_version_in_range(self, app_name: str, version: str, min_version: str, max_version_exc: str) -> None:
        """
        Checks if the given app_name with a string version falls in between specified min and max
        versions (min_version <= version < max_version). Raises ValidationError.
        :param app_name: The name of the app (used just for logging purposes).
        :param version: The version string (semver, might start with optional 'v' prefix).
        :param min_version: proper semver version string to check for (includes this version)
        :param max_version_exc: proper semver version string to check for (excludes this version)
        :return:
        """
        abs_config.assert_version_in_range(self.name, app_name, version, min_version, max_version_exc)


class BuildStepsFilteringPipeline(BuildStep):
    """
    A base class to provide sets (pipelines) of BuildSteps that can be later executed as a single BuildStep.
    Implement your BuildStepsPipeline by inheriting from this class and overriding self._pipeline members.
    This class handles BuildSteps filtering based on configured "--steps" flags.
    """

    def __init__(self, pipeline: List[BuildStep], config_group_desc: str):
        """
        Create new instance using the BuildSteps passed.
        :param pipeline: The list of BuildSteps to be included in this pipeline.
        :param config_group_desc: All options provided by BuildSteps included in
        BuildStepsPipeline all included in the application's help message as
        a separate config options group. This sets its description.
        """
        self._config_group_desc = config_group_desc
        self._pipeline = pipeline
        self._config_parser_group: Optional[configargparse.ArgParser] = None
        self._all_pre_runs_skipped = False
        self._all_runs_skipped = False
        self._all_cleanups_skipped = False

    @property
    def steps_provided(self) -> Set[StepType]:
        all_steps: Set[StepType] = set()
        for build_step in self._pipeline:
            all_steps.update(build_step.steps_provided)
        return all_steps

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        self._config_parser_group = cast(
            configargparse.ArgParser,
            config_parser.add_argument_group(self._config_group_desc),
        )
        for build_step in self._pipeline:
            build_step.initialize_config(self._config_parser_group)

    def pre_run(self, config: argparse.Namespace) -> None:
        self._all_pre_runs_skipped = self._iterate_steps(config, "pre-run", lambda step: step.pre_run(config))

    def run(self, config: argparse.Namespace, context: Context) -> None:
        self._all_runs_skipped = self._iterate_steps(config, "build", lambda step: step.run(config, context))

    def cleanup(
        self,
        config: argparse.Namespace,
        context: Context,
        has_build_failed: bool,
    ) -> None:
        self._all_cleanups_skipped = self._iterate_steps(
            config,
            "cleanup",
            lambda step: step.cleanup(config, context, has_build_failed),
        )

    def _iterate_steps(
        self,
        config: configargparse.Namespace,
        stage: str,
        step_function: Callable[[BuildStep], None],
    ) -> bool:
        all_steps_skipped = True
        for step in self._pipeline:
            execute_all = STEP_ALL in config.steps
            is_requested_step = any(s in step.steps_provided for s in config.steps)
            is_requested_skip = any(s in step.steps_provided for s in config.skip_steps)
            if (execute_all or is_requested_step) and not is_requested_skip:
                logger.info(f"Running {stage} step for {step.name}")
                all_steps_skipped = False
                try:
                    step_function(step)
                except Error as e:
                    logger.error(f"Error when running {stage} step for {step.name}: {e.msg}")
                    raise
            else:
                logger.info(f"Skipping {stage} step for {step.name} as it was not configured to run.")
        return all_steps_skipped
