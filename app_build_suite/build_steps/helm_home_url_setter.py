"""Build step: sets the 'home' field in Chart.yaml from git remote URL."""

import argparse
import logging
from typing import Optional, Set

import configargparse
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType

from app_build_suite.build_steps.helm_consts import (
    CHART_YAML,
    context_key_changes_made,
    context_key_chart_yaml,
)
from app_build_suite.build_steps.steps import STEP_BUILD
from app_build_suite.utils.git import GitRepoVersionInfo
from app_build_suite.utils.git_url import GitUrlConverter

logger = logging.getLogger(__name__)


class HelmHomeUrlSetter(BuildStep):
    """
    Sets chart 'home' field to the git remote URL in HTTPS format.

    - Converts SSH URLs (git@github.com:org/repo) to HTTPS format
    - GitHub repositories only (non-GitHub remotes are skipped)
    - Uses 'origin' remote
    - Enabled by default, can be disabled with --disable-home-url-auto-update
    - Adds 'home' field if missing, updates if present
    """

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_BUILD}

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--disable-home-url-auto-update",
            required=False,
            action="store_true",
            help="Disable automatic setting of 'home' field in Chart.yaml from git remote URL",
        )

    def _is_enabled(self, config: argparse.Namespace) -> bool:
        return not config.disable_home_url_auto_update

    def _get_github_home_url(self, config: argparse.Namespace) -> Optional[str]:
        """
        Get normalized GitHub HTTPS URL from git remote, or None if not available.
        """
        repo_info = GitRepoVersionInfo(config.chart_dir)
        if not repo_info.is_git_repo:
            logger.debug(f"Can't find valid git repository in {config.chart_dir}. Skipping home URL auto-update.")
            return None

        remote_url = repo_info.get_remote_url("origin")
        if not remote_url:
            logger.debug("No 'origin' remote found in git repository. Skipping home URL auto-update.")
            return None

        if not GitUrlConverter.is_github_url(remote_url):
            logger.debug(
                f"Remote URL '{remote_url}' is not a GitHub repository. "
                "Only GitHub repositories are supported for home URL auto-update."
            )
            return None

        return GitUrlConverter.normalize_to_https(remote_url)

    def run(self, config: argparse.Namespace, context: Context) -> None:
        """
        Gets the git remote URL and updates the 'home' field in Chart.yaml.
        Uses line-by-line parsing to preserve formatting and comments.
        """
        if not self._is_enabled(config):
            logger.debug("Home URL auto-update is disabled, ending step.")
            return

        home_url = self._get_github_home_url(config)
        if home_url is None:
            return

        # Read from context dict instead of disk
        chart_yaml = context[context_key_chart_yaml]
        current_home = chart_yaml.get("home", "")

        # Check if update is needed
        if GitUrlConverter.urls_match(current_home, home_url):
            logger.debug(f"'home' field already set to '{home_url}', no changes needed.")
            return

        # Modify context dict
        if current_home:
            logger.info(f"Replacing 'home' with git remote URL '{home_url}' in {CHART_YAML}.")
        else:
            logger.info(f"Adding 'home' field with git remote URL '{home_url}' to {CHART_YAML}.")

        chart_yaml["home"] = home_url
        context[context_key_changes_made] = True
