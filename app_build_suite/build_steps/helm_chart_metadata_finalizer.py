"""Build step: finalizes metadata generation after chart build."""

import argparse
import copy
import logging
import os
import pathlib
import shutil
from datetime import datetime, timezone
from typing import Any, Set

import yaml
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType

from app_build_suite.build_steps.helm_consts import (
    CHART_YAML,
    annotation_files_map,
    context_key_chart_file_name,
    context_key_chart_full_path,
    context_key_meta_dir_path,
    context_key_original_chart_yaml,
    key_annotation_prefix,
    key_oci_annotation_prefix,
)
from app_build_suite.build_steps.steps import STEP_METADATA
from step_exec_lib.errors import ValidationError
from step_exec_lib.utils.files import get_file_sha256

logger = logging.getLogger(__name__)


class HelmChartMetadataFinalizer(BuildStep):
    """
    HelmChartMetadataFinalizer finalizes metadata generation based on additional info in Chart.yaml file
    Should run after HelmChartBuilder
    """

    _key_upstream_chart_url = "upstreamChartURL"
    _key_upstream_chart_version = "upstreamChartVersion"
    _key_restrictions = "restrictions"
    _key_cluster_singleton = "clusterSingleton"
    _key_namespace_singleton = "namespaceSingleton"
    _key_gpu_instances = "gpuInstances"
    _key_fixed_namespace = "fixedNamespace"
    _key_chart_file = "chartFile"
    _key_digest = "digest"
    _key_date_created = "dateCreated"
    _key_chart_api_version = "chartApiVersion"
    _key_api_version = "apiVersion"
    _key_annotations = "annotations"
    _key_icon = "icon"
    _key_home = "home"

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_METADATA}

    def pre_run(self, config: argparse.Namespace) -> None:
        chart_yaml_path = os.path.join(config.chart_dir, CHART_YAML)
        with open(chart_yaml_path, "r") as file:
            chart_yaml = yaml.safe_load(file)
        if self._key_upstream_chart_url in chart_yaml and self._key_upstream_chart_version not in chart_yaml:
            raise ValidationError(
                self.name,
                f"'{self._key_upstream_chart_url}' is found in Chart.yaml, but"
                f" '{self._key_upstream_chart_version}' is not. When you provide upstream"
                f" chart URL, please also include the version.",
            )

    @staticmethod
    def get_build_timestamp() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds").split("+")[0] + "Z"

    @staticmethod
    def write_meta_file(meta_file_name: str, meta: Context) -> None:
        with open(meta_file_name, "w") as f:
            yaml.dump(meta, f, default_flow_style=False)

    @staticmethod
    def _kebab_to_camel(kebab_str: str) -> str:
        """Convert kebab-case string to camelCase."""
        parts = kebab_str.split("-")
        if not parts:
            return kebab_str
        return parts[0] + "".join(word.capitalize() for word in parts[1:])

    def _convert_annotations(self, original_annotations: dict[str, Any]) -> dict[str, Any]:
        """Convert annotations from old format to new format."""
        new_style_annotations = copy.deepcopy(original_annotations)
        to_remove = []
        to_add = {}
        slashed_oci_annotation_prefix = key_oci_annotation_prefix.replace(".", "/")

        for key, value in new_style_annotations.items():
            if key.startswith(key_oci_annotation_prefix):
                # leave application.giantswarm.io/... as is but replace dots with slashes
                new_key = key.replace(".", "/")
                new_key = new_key.replace(slashed_oci_annotation_prefix, key_annotation_prefix)
                to_remove.append(key)
                # if key part after prefix is kebab case, convert to camel case
                key_parts = new_key.split("/")
                if len(key_parts) > 1:
                    converted_parts = [key_parts[0]]  # Keep prefix as-is
                    for part in key_parts[1:]:
                        if "-" in part:
                            converted_parts.append(self._kebab_to_camel(part))
                        else:
                            converted_parts.append(part)
                    new_key = "/".join(converted_parts)
                to_add[new_key] = value

        for key in to_remove:
            new_style_annotations.pop(key)
        for key, value in to_add.items():
            new_style_annotations[key] = value

        return new_style_annotations

    def run(self, config: argparse.Namespace, context: Context) -> None:
        if not config.generate_metadata:
            logger.info("Metadata generation is disabled using 'generate-metadata' option.")
            return
        meta = {}
        # mandatory metadata
        meta[self._key_chart_file] = context[context_key_chart_file_name]
        meta[self._key_digest] = get_file_sha256(context[context_key_chart_full_path])
        meta[self._key_date_created] = self.get_build_timestamp()
        meta[self._key_chart_api_version] = context[context_key_original_chart_yaml][self._key_api_version]
        # optional metadata
        for key in [
            self._key_upstream_chart_url,
            self._key_upstream_chart_version,
            self._key_restrictions,
            self._key_icon,
            self._key_home,
        ]:
            if key in context[context_key_original_chart_yaml]:
                meta[key] = context[context_key_original_chart_yaml][key]
        # convert existing annotations in the format io.giantswarm.application...to application.giantswarm.io/...
        # Handle case where annotations don't exist
        original_annotations = context[context_key_original_chart_yaml].get(self._key_annotations, {})
        meta[self._key_annotations] = self._convert_annotations(original_annotations)
        # create metadata directory
        context[context_key_meta_dir_path] = f"{context[context_key_chart_full_path]}-meta"
        pathlib.Path(context[context_key_meta_dir_path]).mkdir(parents=True, exist_ok=True)
        # save metadata file
        meta_dir_path = context[context_key_meta_dir_path]
        meta_file_name = os.path.join(context[context_key_meta_dir_path], "main.yaml")
        self.write_meta_file(meta_file_name, meta)
        logger.info(f"Metadata file saved to '{meta_file_name}'")
        # copy additional files to metadata directory
        chart_dir = config.chart_dir
        for additional_file in annotation_files_map.keys():
            source_file_path = os.path.join(os.path.abspath(chart_dir), additional_file)
            if os.path.isfile(source_file_path):
                target_file_path = os.path.join(meta_dir_path, os.path.basename(additional_file))
                shutil.copy2(source_file_path, target_file_path)
