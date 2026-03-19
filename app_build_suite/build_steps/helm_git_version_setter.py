"""Build step: sets chart version/appVersion from git."""

import argparse
import logging
from typing import Optional, Set

import configargparse
from step_exec_lib.errors import ValidationError
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType

from app_build_suite.build_steps.helm_consts import (
    CHART_YAML,
    CHART_YAML_APP_VERSION_KEY,
    CHART_YAML_CHART_VERSION_KEY,
    context_key_changes_made,
    context_key_chart_yaml,
    context_key_git_version,
)
from app_build_suite.build_steps.steps import STEP_BUILD
from app_build_suite.utils.git import GitRepoVersionInfo

logger = logging.getLogger(__name__)


class HelmGitVersionSetter(BuildStep):
    """
    Sets chart `version` and `appVersion` to a version discovered from `git`. Both options are configurable.
    """

    repo_info: Optional[GitRepoVersionInfo] = None

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_BUILD}

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--replace-app-version-with-git",
            required=False,
            action="store_true",
            help=f"Should the {CHART_YAML_APP_VERSION_KEY} in {CHART_YAML} be replaced by a tag and hash from git",
        )
        config_parser.add_argument(
            "--replace-chart-version-with-git",
            required=False,
            action="store_true",
            help=f"Should the {CHART_YAML_CHART_VERSION_KEY} in {CHART_YAML} be replaced by a tag and hash from git",
        )

    # noinspection PyMethodMayBeStatic
    def _is_enabled(self, config: argparse.Namespace) -> bool:
        return config.replace_chart_version_with_git or config.replace_app_version_with_git

    def pre_run(self, config: argparse.Namespace) -> None:
        """
        Checks if we can find a git directory in the chart's dir or that dir's parent.
        :param config: Configuration Namespace object.
        :return: None
        """
        if not self._is_enabled(config):
            logger.debug("No version override options requested, skipping pre-run.")
            return
        self.repo_info = GitRepoVersionInfo(config.chart_dir)
        if not self.repo_info.is_git_repo:
            raise ValidationError(self.name, f"Can't find valid git repository in {config.chart_dir}")

    def run(self, config: argparse.Namespace, context: Context) -> None:
        """
        Gets the git-version, then modifies version/appVersion in the context dict.
        :param config: the config object
        :param context: the context object
        :return: None
        """
        if not self._is_enabled(config):
            logger.debug("No version override options requested, ending step.")
            return

        if self.repo_info is not None:
            git_version = self.repo_info.get_git_version()
        else:
            raise ValidationError(self.name, f"Can't find valid git repository in {config.chart_dir}")
        # add the version info to context, so other BuildSteps can use it
        context[context_key_git_version] = git_version

        # Modify context dict instead of line-by-line manipulation
        if config.replace_chart_version_with_git:
            logger.info(f"Replacing 'version' with git version '{git_version}' in {CHART_YAML}.")
            context[context_key_chart_yaml][CHART_YAML_CHART_VERSION_KEY] = git_version
            context[context_key_changes_made] = True

        if config.replace_app_version_with_git:
            logger.info(f"Replacing 'appVersion' with git version '{git_version}' in {CHART_YAML}.")
            context[context_key_chart_yaml][CHART_YAML_APP_VERSION_KEY] = git_version
            context[context_key_changes_made] = True
