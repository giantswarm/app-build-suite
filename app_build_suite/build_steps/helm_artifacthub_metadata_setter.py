"""Build step: injects missing Artifact Hub metadata into Chart.yaml at package time."""

import argparse
import logging
import os
import shutil
from typing import Dict, List, Optional, Set

import configargparse
import yaml
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType

from app_build_suite.build_steps.helm_consts import (
    CHART_YAML,
    README_MD,
    context_key_artifacthub_readme_copied,
    context_key_changes_made,
    context_key_chart_yaml,
)
from app_build_suite.build_steps.steps import STEP_BUILD
from app_build_suite.utils.git import GitRepoVersionInfo
from app_build_suite.utils.git_url import GitUrlConverter

logger = logging.getLogger(__name__)


class HelmArtifactHubMetadataSetter(BuildStep):
    """
    Injects Artifact Hub metadata into the in-memory Chart.yaml if it's missing.

    - 'artifacthub.io/license': set to 'Apache-2.0' if the repository root contains a LICENSE file
      that is recognizably Apache License 2.0
    - 'artifacthub.io/links': set to a 'Support' link (GitHub issues page of the chart's repository)
      and, if available, a single 'Upstream project' link taken from the first entry in the chart's
      'sources' that doesn't point to the Giant Swarm GitHub organization
    - copies the repository root README.md into the chart directory if the chart has none, so it gets
      packaged; the copy is removed again in cleanup, leaving the working tree clean
    - Explicit values already present in Chart.yaml always win - only missing data is injected
    - Enabled by default, can be disabled with --disable-artifacthub-metadata
    """

    _key_annotations = "annotations"
    _key_ah_license = "artifacthub.io/license"
    _key_ah_links = "artifacthub.io/links"
    _apache_2_license = "Apache-2.0"
    _license_file_names = ["LICENSE", "LICENSE.md", "LICENSE.txt"]
    _license_detection_lines = 20
    _giantswarm_github_url_prefix = "https://github.com/giantswarm"

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_BUILD}

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--disable-artifacthub-metadata",
            required=False,
            action="store_true",
            help=f"Disable automatic injection of missing Artifact Hub metadata into {CHART_YAML}",
        )

    def _is_enabled(self, config: argparse.Namespace) -> bool:
        return not config.disable_artifacthub_metadata

    def _find_repo_root(self, chart_dir: str) -> Optional[str]:
        current = os.path.abspath(chart_dir)
        while True:
            if os.path.isdir(os.path.join(current, ".git")):
                return current
            parent = os.path.dirname(current)
            if parent == current:
                return None
            current = parent

    def _detect_apache_2_license(self, repo_root: str) -> bool:
        """
        Check if the repository root contains a LICENSE file that is recognizably Apache License 2.0.

        Only the first few lines of the file are inspected; if the license can't be confidently
        detected, False is returned.
        """
        for file_name in self._license_file_names:
            license_path = os.path.join(repo_root, file_name)
            if not os.path.isfile(license_path):
                continue
            try:
                with open(license_path, "r", errors="replace") as f:
                    head = "".join(f.readline() for _ in range(self._license_detection_lines)).lower()
            except OSError as e:
                logger.debug(f"Can't read license file '{license_path}': {e}.")
                continue
            if "apache license" in head and "version 2.0" in head:
                logger.debug(f"Detected Apache License 2.0 in '{license_path}'.")
                return True
            logger.debug(f"License file '{license_path}' doesn't look like Apache License 2.0.")
        return False

    def _get_github_repo_url(self, config: argparse.Namespace, chart_yaml: Context) -> Optional[str]:
        """
        Get the normalized GitHub HTTPS URL of the chart's repository, or None if it can't be derived.

        The 'home' field in Chart.yaml is preferred (it's set from the git remote by HelmHomeUrlSetter,
        which runs before this step); the 'origin' git remote is used as a fallback.
        """
        home = chart_yaml.get("home")
        if isinstance(home, str) and GitUrlConverter.is_github_url(home):
            return GitUrlConverter.normalize_to_https(home)

        repo_info = GitRepoVersionInfo(config.chart_dir)
        if repo_info.is_git_repo:
            remote_url = repo_info.get_remote_url("origin")
            if remote_url and GitUrlConverter.is_github_url(remote_url):
                return GitUrlConverter.normalize_to_https(remote_url)

        logger.debug("Can't derive a GitHub repository URL from 'home' field or git remote.")
        return None

    def _build_links_annotation(self, config: argparse.Namespace, chart_yaml: Context) -> Optional[str]:
        """
        Build the value for the 'artifacthub.io/links' annotation: a YAML list serialized as a string
        (that's the Artifact Hub convention).
        """
        links: List[Dict[str, str]] = []

        repo_url = self._get_github_repo_url(config, chart_yaml)
        if repo_url:
            links.append({"name": "Support", "url": f"{repo_url}/issues"})
        else:
            logger.info("Can't derive a reliable GitHub repository URL, skipping the 'Support' link.")

        sources = chart_yaml.get("sources", [])
        if isinstance(sources, list):
            for source in sources:
                if isinstance(source, str) and not source.startswith(self._giantswarm_github_url_prefix):
                    links.append({"name": "Upstream project", "url": source})
                    break

        if not links:
            return None
        return yaml.safe_dump(links, default_flow_style=False, sort_keys=False)

    def _ensure_chart_readme(self, config: argparse.Namespace, context: Context, repo_root: Optional[str]) -> None:
        """
        If the chart directory has no README.md but the repository root does, copy it into the chart
        directory so it gets packaged. The copy is removed again in cleanup.
        """
        chart_readme_path = os.path.abspath(os.path.join(config.chart_dir, README_MD))
        if os.path.isfile(chart_readme_path):
            logger.debug(f"{README_MD} already present in the chart directory, nothing to copy.")
            return
        if repo_root is None:
            logger.debug(f"Can't find the repository root, skipping {README_MD} copy.")
            return
        root_readme_path = os.path.abspath(os.path.join(repo_root, README_MD))
        if root_readme_path == chart_readme_path or not os.path.isfile(root_readme_path):
            logger.debug(f"No {README_MD} found in the repository root, skipping copy.")
            return
        logger.info(f"Copying repository root {README_MD} into the chart directory for packaging.")
        shutil.copy2(root_readme_path, chart_readme_path)
        context[context_key_artifacthub_readme_copied] = chart_readme_path

    def run(self, config: argparse.Namespace, context: Context) -> None:
        """
        Injects missing Artifact Hub annotations into the in-memory Chart.yaml and copies the
        repository root README.md into the chart directory if the chart has none.
        """
        if not self._is_enabled(config):
            logger.debug("Artifact Hub metadata injection is disabled, ending step.")
            return

        chart_yaml = context[context_key_chart_yaml]
        annotations = chart_yaml.get(self._key_annotations) or {}
        repo_root = self._find_repo_root(config.chart_dir)
        changes_made = False

        if self._key_ah_license in annotations:
            logger.debug(f"'{self._key_ah_license}' already set in {CHART_YAML}, keeping the existing value.")
        elif repo_root is not None and self._detect_apache_2_license(repo_root):
            logger.info(f"Adding '{self._key_ah_license}: {self._apache_2_license}' annotation to {CHART_YAML}.")
            annotations[self._key_ah_license] = self._apache_2_license
            changes_made = True
        else:
            logger.info(f"No Apache License 2.0 detected in the repository root, skipping '{self._key_ah_license}'.")

        if self._key_ah_links in annotations:
            logger.debug(f"'{self._key_ah_links}' already set in {CHART_YAML}, keeping the existing value.")
        else:
            links = self._build_links_annotation(config, chart_yaml)
            if links:
                logger.info(f"Adding '{self._key_ah_links}' annotation to {CHART_YAML}.")
                annotations[self._key_ah_links] = links
                changes_made = True
            else:
                logger.info(f"No links could be derived, skipping '{self._key_ah_links}'.")

        if changes_made:
            chart_yaml[self._key_annotations] = annotations
            context[context_key_changes_made] = True

        self._ensure_chart_readme(config, context, repo_root)

    def cleanup(
        self,
        config: argparse.Namespace,
        context: Context,
        has_build_failed: bool,
    ) -> None:
        if context_key_artifacthub_readme_copied in context and context[context_key_artifacthub_readme_copied]:
            copied_readme_path = context[context_key_artifacthub_readme_copied]
            if os.path.isfile(copied_readme_path):
                logger.info(f"Removing {README_MD} copied into the chart directory during the build.")
                os.remove(copied_readme_path)
