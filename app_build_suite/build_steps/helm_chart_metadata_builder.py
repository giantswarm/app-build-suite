"""Build step: prepares metadata and annotations for Giant Swarm App Platform."""

import argparse
import copy
import logging
import os
from typing import Any, List, Optional, Set
from urllib.parse import urlsplit

import configargparse
import validators
import yaml
from step_exec_lib.errors import ValidationError
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType

from app_build_suite.build_steps.helm_consts import (
    CHART_YAML,
    annotation_files_map,
    context_key_changes_made,
    context_key_chart_file_name,
    context_key_chart_full_path,
    context_key_chart_yaml,
    context_key_original_chart_yaml,
    key_annotation_prefix,
    key_oci_annotation_prefix,
)
from app_build_suite.build_steps.steps import STEP_METADATA

logger = logging.getLogger(__name__)


class HelmChartMetadataBuilder(BuildStep):
    """
    HelmChartMetadataBuilder builds metadata generation based on additional info in Chart.yaml file.
    Should run before HelmChartBuilder
    """

    _key_upstream_chart_url = "upstreamChartURL"
    _key_upstream_chart_version = "upstreamChartVersion"
    _key_restrictions = "restrictions"
    _key_cluster_singleton = "clusterSingleton"
    _key_namespace_singleton = "namespaceSingleton"
    _key_gpu_instances = "gpuInstances"
    _key_compatible_providers = "compatibleProviders"
    _key_fixed_namespace = "fixedNamespace"
    _key_annotations = "annotations"
    _key_annotation_metadata_url = f"{key_annotation_prefix}/metadata"
    _key_annotation_restrictions_prefix = f"{key_annotation_prefix}/restrictions"
    _key_oci_annotation_metadata_url = f"{key_oci_annotation_prefix}.metadata"
    _key_oci_annotation_restrictions_prefix = f"{key_oci_annotation_prefix}.restrictions"
    _oci_translated_keys = {
        _key_upstream_chart_url: "upstream-chart-url",
        _key_upstream_chart_version: "upstream-chart-version",
        _key_cluster_singleton: "cluster-singleton",
        _key_namespace_singleton: "namespace-singleton",
        _key_gpu_instances: "gpu-instances",
        _key_fixed_namespace: "fixed-namespace",
        _key_compatible_providers: "compatible-providers",
    }

    _github_host = "github.com"
    _github_raw_host = "https://raw.githubusercontent.com"

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_METADATA}

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--generate-metadata",
            required=False,
            action="store_true",
            help="Generate the metadata file for Giant Swarm App Platform.",
        )
        config_parser.add_argument(
            "--catalog-base-url",
            required=False,
            help="Base URL of the catalog in which the app package will be stored in. Should end with a /",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        if not config.generate_metadata:
            logger.info("Metadata generation is disabled using 'generate-metadata' option.")
            return
        if not config.catalog_base_url:
            raise ValidationError(
                self.name,
                "config option --generate-metadata requires non-empty option --catalog-base-url",
            )
        if not config.catalog_base_url.endswith("/"):
            raise ValidationError(self.name, "config option --catalog-base-url value should end with a /")
        # first step of validation should be done already by 'ct' with correct schema (unless explicitly disabled)
        chart_yaml_path = os.path.join(config.chart_dir, CHART_YAML)
        with open(chart_yaml_path, "r") as file:
            chart_yaml = yaml.safe_load(file)
        if self._key_upstream_chart_url in chart_yaml and not validators.url(chart_yaml[self._key_upstream_chart_url]):
            raise ValidationError(
                self.name,
                f"Config option '{self._key_upstream_chart_url}' is not a correct URL.",
            )
        if self._key_restrictions in chart_yaml:
            for option in [
                self._key_cluster_singleton,
                self._key_namespace_singleton,
                self._key_gpu_instances,
            ]:
                if (
                    option in chart_yaml[self._key_restrictions]
                    and type(chart_yaml[self._key_restrictions][option]) is not bool
                ):
                    raise ValidationError(self.name, f"Value of '{option}' is not a correct boolean.")

    @staticmethod
    def write_chart_yaml(chart_yaml_file_name: str, data: Context) -> None:
        with open(chart_yaml_file_name, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def _normalize_version_tag(self, chart_version: str) -> str:
        if not chart_version:
            raise ValidationError(self.name, "Chart version is not set")
        if chart_version.startswith("v"):
            return chart_version
        return f"v{chart_version}"

    def _extract_commit_hash_from_version(self, version: str) -> Optional[str]:
        """
        Extracts commit hash from version string if it's in commit-based format.
        Commit-based format: {tag}-{commit_hash} where commit_hash is 7-40 hex characters.
        :param version: Version string (e.g., "1.0.1-e0fc1f818b9f3d2c816c3ddf94e814ba6e3e1aae")
        :return: Commit hash if found, None otherwise
        """
        if not version:
            return None
        # Split on last dash to separate tag from potential commit hash
        parts = version.rsplit("-", 1)
        if len(parts) != 2:
            return None
        potential_hash = parts[1]
        # Commit hash should be 7-40 hex characters
        if len(potential_hash) >= 7 and len(potential_hash) <= 40:
            try:
                # Validate it's hexadecimal
                int(potential_hash, 16)
                return potential_hash
            except ValueError:
                return None
        return None

    def _format_restriction_value(self, value: Any) -> Any:
        if isinstance(value, list):
            return ",".join(str(v) for v in value)
        return value

    def _find_git_repo_root(self, chart_dir: str) -> Optional[str]:
        current = os.path.abspath(chart_dir)
        while True:
            if os.path.isdir(os.path.join(current, ".git")):
                return current
            parent = os.path.dirname(current)
            if parent == current:
                return None
            current = parent

    def _extract_github_repo_from_url(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        parsed = urlsplit(url)
        netloc = parsed.netloc.lower()
        path_parts = [part for part in parsed.path.strip("/").split("/") if part]
        if netloc.endswith(self._github_host) and len(path_parts) >= 2:
            owner = path_parts[0]
            repo = path_parts[1]
            if repo.endswith(".git"):
                repo = repo[:-4]
            return f"{owner}/{repo}"
        if netloc == "raw.githubusercontent.com" and len(path_parts) >= 2:
            return f"{path_parts[0]}/{path_parts[1]}"
        return None

    def _discover_github_repo(self, chart_yaml: Context) -> Optional[str]:
        candidates: List[str] = []
        home = chart_yaml.get("home")
        if isinstance(home, str):
            candidates.append(home)
        sources = chart_yaml.get("sources", [])
        if isinstance(sources, list):
            candidates.extend([src for src in sources if isinstance(src, str)])
        for candidate in candidates:
            repo = self._extract_github_repo_from_url(candidate)
            if repo:
                return repo
        return None

    def _build_github_annotation_url(
        self,
        github_repo: Optional[str],
        repo_root: Optional[str],
        source_file_path: str,
        version: Optional[str],
    ) -> str:
        if not github_repo or not repo_root or not version:
            return "unknown"
        abs_repo_root = os.path.abspath(repo_root)
        abs_file = os.path.abspath(source_file_path)
        try:
            relative_path = os.path.relpath(abs_file, abs_repo_root)
        except ValueError:
            return "unknown"
        if relative_path.startswith(".."):
            return "unknown"
        normalized_relative_path = relative_path.replace(os.sep, "/")
        # Check if version contains a commit hash
        commit_hash = self._extract_commit_hash_from_version(version)
        if commit_hash:
            # Use commit hash directly for commit-based versions
            return urlsplit(f"{self._github_raw_host}/{github_repo}/{commit_hash}/{normalized_relative_path}").geturl()
        else:
            # Use tag format for tag-based versions
            normalized_tag = self._normalize_version_tag(version)
            return urlsplit(
                f"{self._github_raw_host}/{github_repo}/refs/tags/{normalized_tag}/{normalized_relative_path}"
            ).geturl()

    def build_chart_yaml_annotations(
        self,
        chart_yaml: Context,
        catalog_base_url: str,
        chart_file_name: str,
        chart_dir: str,
    ) -> Context:
        """
        Based upon the _annotations_files_map:
          - check if the file is available
          - include it in the annotations
          - copy it into the metadata directory
        """
        catalog_url = f"{catalog_base_url}{chart_file_name}-meta/"
        annotations = {self._key_oci_annotation_metadata_url: urlsplit(f"{catalog_url}main.yaml").geturl()}
        github_repo = self._discover_github_repo(chart_yaml)
        chart_version = chart_yaml.get("version")
        repo_root = self._find_git_repo_root(chart_dir)
        for additional_file, annotation_key in annotation_files_map.items():
            source_file_path = os.path.join(os.path.abspath(chart_dir), additional_file)
            if os.path.isfile(source_file_path):
                github_url = self._build_github_annotation_url(github_repo, repo_root, source_file_path, chart_version)
                annotations[annotation_key] = github_url
        if self._key_restrictions in chart_yaml:
            restrictions = chart_yaml[self._key_restrictions]
            if isinstance(restrictions, dict):
                for key, value in restrictions.items():
                    kebab_key = self._oci_translated_keys[key]
                    formatted_value = self._format_restriction_value(value)
                    chart_yaml[self._key_annotations][f"{self._key_oci_annotation_restrictions_prefix}.{kebab_key}"] = (
                        formatted_value
                    )
        if self._key_upstream_chart_url in chart_yaml:
            annotation_key = f"{key_oci_annotation_prefix}.{self._oci_translated_keys[self._key_upstream_chart_url]}"
            chart_yaml[self._key_annotations][annotation_key] = chart_yaml[self._key_upstream_chart_url]
        if self._key_upstream_chart_version in chart_yaml:
            annotation_key = (
                f"{key_oci_annotation_prefix}.{self._oci_translated_keys[self._key_upstream_chart_version]}"
            )
            chart_yaml[self._key_annotations][annotation_key] = chart_yaml[self._key_upstream_chart_version]

        return annotations

    def run(self, config: argparse.Namespace, context: Context) -> None:
        if not config.generate_metadata:
            logger.info("Metadata generation is disabled using 'generate-metadata' option.")
            return
        # Read from context dict instead of disk
        chart_yaml = context[context_key_chart_yaml]
        original_annotations = chart_yaml.get(self._key_annotations, None)
        # Save original chart yaml BEFORE annotation modifications (preserves version/home changes)
        context[context_key_original_chart_yaml] = copy.deepcopy(chart_yaml)
        # try to guess the package file name. we need it for url generation in annotations
        chart_name = chart_yaml["name"]
        chart_version = chart_yaml["version"]
        context[context_key_chart_file_name] = f"{chart_name}-{chart_version}.tgz"
        context[context_key_chart_full_path] = os.path.abspath(
            os.path.join(config.destination, context[context_key_chart_file_name])
        )
        # Initialize annotations if they don't exist
        if self._key_annotations not in chart_yaml:
            chart_yaml[self._key_annotations] = {}
        # convert existing annotations in the format application.giantswarm.io/... to io.giantswarm.application....
        to_remove = []
        to_add = {}
        for key, value in chart_yaml[self._key_annotations].items():
            if key.startswith(key_annotation_prefix):
                new_key = key.replace(key_annotation_prefix, key_oci_annotation_prefix)
                new_key = new_key.replace("/", ".")
                to_remove.append(key)
                to_add[new_key] = value
        for key in to_remove:
            chart_yaml[self._key_annotations].pop(key)
        for key, value in to_add.items():
            chart_yaml[self._key_annotations][key] = value
        # put in generated annotations
        annotations = self.build_chart_yaml_annotations(
            chart_yaml,
            config.catalog_base_url,
            context[context_key_chart_file_name],
            config.chart_dir,
        )
        chart_yaml[self._key_annotations].update(annotations)
        # Track changes if annotations were modified
        if original_annotations != chart_yaml[self._key_annotations]:
            context[context_key_changes_made] = True
