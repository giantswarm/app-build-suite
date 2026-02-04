"""
Home URL validation checks:
- C0004: Validates that Chart.yaml 'home' field matches the git remote URL
"""

import argparse
import logging

from app_build_suite.build_steps.giant_swarm_validators.mixins import UseChartYaml
from app_build_suite.utils.git import GitRepoVersionInfo
from app_build_suite.utils.git_url import GitUrlConverter

logger = logging.getLogger(__name__)


class HomeUrlMatchesGitRemote(UseChartYaml):
    """
    Validates that Chart.yaml 'home' field matches the git remote URL.

    This validator checks that the 'home' field in Chart.yaml points to the
    same GitHub repository as the git 'origin' remote.

    Validation passes if:
    - 'home' field matches the normalized git remote URL
    - 'home' field is missing (it's optional, auto-update step can add it)
    - Not a git repository (validation not applicable)
    - Git remote is not GitHub (validation not applicable)

    Validation fails if:
    - 'home' field exists but doesn't match the GitHub remote URL
    """

    def get_check_code(self) -> str:
        return "C0004"

    def validate(self, config: argparse.Namespace) -> bool:
        chart_yaml = self.get_chart_yaml(config)

        # Check if home field exists
        home_url = chart_yaml.get("home")
        if not home_url:
            logger.debug("'home' field not found in Chart.yaml. Skipping validation.")
            return True  # Missing home is OK, not a failure

        if not isinstance(home_url, str):
            logger.info("'home' field is not a string in Chart.yaml.")
            return False

        # Get git repository info
        repo_info = GitRepoVersionInfo(config.chart_dir)
        if not repo_info.is_git_repo:
            logger.debug("Not a git repository. Cannot validate 'home' field against git remote.")
            return True  # Not a git repo, skip validation

        # Get origin remote URL
        remote_url = repo_info.get_remote_url("origin")
        if not remote_url:
            logger.debug("No 'origin' remote found. Cannot validate 'home' field.")
            return True  # No remote, skip validation

        # Check if it's a GitHub URL
        if not GitUrlConverter.is_github_url(remote_url):
            logger.debug(f"Remote URL '{remote_url}' is not a GitHub repository. Skipping 'home' field validation.")
            return True  # Only validate GitHub repos

        # Normalize and compare URLs
        expected_url = GitUrlConverter.normalize_to_https(remote_url)
        if expected_url is None:
            logger.debug("Could not normalize remote URL. Skipping validation.")
            return True

        if GitUrlConverter.urls_match(home_url, expected_url):
            return True

        # URLs don't match
        logger.info(
            f"'home' field mismatch in Chart.yaml: expected '{expected_url}' (from git remote), but found '{home_url}'."
        )
        return False
