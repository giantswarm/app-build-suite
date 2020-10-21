"""Build steps implementing helm3 based builds."""
import argparse
import logging
import os
import pathlib
import shutil
import subprocess  # nosec
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict, Set

import configargparse
import validators
import yaml

from app_build_suite.build_steps import BuildStep
from app_build_suite.build_steps.build_step import (
    StepType,
    STEP_BUILD,
    ALL_STEPS,
    STEP_TEST_UNIT,
    BuildStepsFilteringPipeline,
    STEP_METADATA,
)
from app_build_suite.build_steps.errors import ValidationError, BuildError
from app_build_suite.utils.files import get_file_sha256
from app_build_suite.utils.git import GitRepoVersionInfo

logger = logging.getLogger(__name__)

context_key_chart_full_path: str = "chart_full_path"
context_key_chart_file_name: str = "chart_file_name"
context_key_git_version: str = "git_version"

_chart_yaml_app_version_key = "appVersion"
_chart_yaml_chart_version_key = "version"
_chart_yaml = "Chart.yaml"
_values_yaml = "values.yaml"


class HelmBuilderValidator(BuildStep):
    """
    Very simple validator that checks if the folder looks like Helm chart at all.
    """

    @property
    def steps_provided(self) -> Set[StepType]:
        return ALL_STEPS

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "-c",
            "--chart-dir",
            required=False,
            default=".",
            help="Path to the Helm Chart to build.",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        """Validates if basic chart files are present in the configured directory."""
        if os.path.exists(os.path.join(config.chart_dir, _chart_yaml)) and os.path.exists(
            os.path.join(config.chart_dir, _values_yaml)
        ):
            return
        raise ValidationError(self.name, f"Can't find '{_chart_yaml}' or '{_values_yaml}' files.")

    def run(self, config: argparse.Namespace, context: Dict[str, Any]) -> None:
        pass


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
            help=f"Should the {_chart_yaml_app_version_key}  in {_chart_yaml} be replaced by a tag and hash from git",
        )
        config_parser.add_argument(
            "--replace-chart-version-with-git",
            required=False,
            action="store_true",
            help=f"Should the {_chart_yaml_chart_version_key} in {_chart_yaml} be replaced by a tag and hash from git",
        )

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

    def run(self, config: argparse.Namespace, context: Dict[str, Any]) -> None:
        """
        Gets the git-version, then replaces keys in Chart.yaml
        :param config: the config object
        :param context: the context object
        :return: None
        """
        if not self._is_enabled(config):
            logger.debug("No version override options requested, ending step.")
            return

        if self.repo_info is not None:
            git_version = self.repo_info.get_git_version
        else:
            raise ValidationError(self.name, f"Can't find valid git repository in {config.chart_dir}")
        # add the version info to context, so other BuildSteps can use it
        context[context_key_git_version] = git_version

        new_lines: List[str] = []
        changes_made = False
        chart_yaml_path = os.path.join(config.chart_dir, _chart_yaml)
        with open(chart_yaml_path, "r") as file:
            lines = file.readlines()
            for line in lines:
                fields = line.split(":")
                if (config.replace_chart_version_with_git and fields[0] == _chart_yaml_chart_version_key) or (
                    config.replace_app_version_with_git and fields[0] == _chart_yaml_app_version_key
                ):
                    logger.info(f"Replacing '{fields[0]}' with git version '{git_version}' in {_chart_yaml}.")
                    changes_made = True
                    new_lines.append(f"{fields[0]}: {git_version}\n")
                else:
                    new_lines.append(line)
        if changes_made:
            logger.debug(f"Saving backup of {_chart_yaml} in {_chart_yaml}.back")
            shutil.copy2(chart_yaml_path, chart_yaml_path + ".back")
            with open(chart_yaml_path, "w") as file:
                logger.info(f"Saving {_chart_yaml} with version set from git.")
                file.writelines(new_lines)


class HelmChartToolLinter(BuildStep):
    """
    Runs helm ct linter against the chart.
    """

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_TEST_UNIT}

    _ct_bin = "ct"
    _min_ct_version = "3.1.0"
    _max_ct_version = "4.0.0"
    _metadata_schema = "gs_metadata_chart_schema.yaml"

    def __init__(self):
        self._additional_helm_repos = ["stable=https://kubernetes-charts.storage.googleapis.com/"]

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--ct-config",
            required=False,
            help="Path to optional 'ct' lint config file.",
        )
        config_parser.add_argument(
            "--ct-schema",
            required=False,
            help="Path to optional 'ct' schema file.",
        )
        config_parser.add_argument(
            "--ct-chart-repos",
            required=False,
            help="Additional helm chart repositories for use with 'ct' validation."
            " Additional chart repositories for dependency resolutions."
            " Repositories should be formatted as 'name=url' (ex:"
            " local=http://127.0.0.1:8879/charts). Multiple entries must"
            " be separated with ','.",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        """
        Verifies if the required version of `ct` is installed and config options are sane.
        :param config: the config object
        :return: None
        """
        # verify if binary present
        self._assert_binary_present_in_path(self._ct_bin)
        # verify version
        run_res = subprocess.run([self._ct_bin, "version"], capture_output=True)  # nosec
        version_line = str(run_res.stdout.splitlines()[0], "utf-8")
        version = version_line.split(":")[1].strip()
        self._assert_version_in_range(self._ct_bin, version, self._min_ct_version, self._max_ct_version)
        # validate config options
        if config.ct_config is not None and not os.path.isabs(config.ct_config):
            config.ct_config = os.path.join(os.getcwd(), config.ct_config)
        if config.ct_config is not None and not os.path.isfile(config.ct_config):
            raise ValidationError(
                self.name,
                f"Chart tool config file {config.ct_config} doesn't exist.",
            )
        # if we're validating a metadata enabled project (for Giant Swarm App Platform),
        # we have to use the modified schema
        if config.generate_metadata:
            full_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "resources",
                "ct_schemas",
                self._metadata_schema,
            )
            logger.info(
                f"Metadata generation was requested, changing default validation schema to '{self._metadata_schema}'"
            )
            config.ct_schema = full_path
        # validate schema path
        if config.ct_schema is not None and not os.path.isabs(config.ct_schema):
            config.ct_schema = os.path.join(os.getcwd(), config.ct_schema)
        if config.ct_schema is not None and not os.path.isfile(config.ct_schema):
            raise ValidationError(
                self.name,
                f"Chart tool schema file {config.ct_schema} doesn't exist.",
            )
        if config.ct_chart_repos is not None:
            repos_entries = config.ct_chart_repos.split(",")
            for entry in repos_entries:
                entry = entry.strip("\"'")
                name, url = entry.split("=")
                if not validators.slug(name):
                    raise ValidationError(
                        self.name,
                        f"{name} is not a correct helm repo name.",
                    )
                if not validators.url(url):
                    raise ValidationError(
                        self.name,
                        f"{url} is not a correct helm repo url.",
                    )
                self._additional_helm_repos.append(entry)

    def run(self, config: argparse.Namespace, _: Dict[str, Any]) -> None:
        args = [
            self._ct_bin,
            "lint",
            "--validate-maintainers=false",
            f"--charts={config.chart_dir}",
            f"--chart-repos={','.join(self._additional_helm_repos)}",
        ]
        if config.debug:
            args.append("--debug")
        if config.ct_config is not None:
            args.append(f"--config={config.ct_config}")
        if config.ct_schema is not None:
            args.append(f"--chart-yaml-schema={config.ct_schema}")
        logger.info("Running chart tool linting")
        run_res = subprocess.run(args, capture_output=True)  # nosec, input params checked above in pre_run
        for line in run_res.stdout.splitlines():
            logger.info(str(line, "utf-8"))
        if run_res.returncode != 0:
            logger.error(f"{self._ct_bin} run failed with exit code {run_res.returncode}")
            raise BuildError(self.name, "Linting failed")


class HelmChartBuilder(BuildStep):
    """
    Builds a helm chart using helm3.
    """

    _helm_bin = "helm"
    _min_helm_version = "3.2.0"
    _max_helm_version = "4.0.0"

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_BUILD}

    def pre_run(self, config: argparse.Namespace) -> None:
        """
        Checks if the required version of helm is installed.
        :param config: the config object
        :return: None
        """
        self._assert_binary_present_in_path(self._helm_bin)
        run_res = subprocess.run([self._helm_bin, "version"], capture_output=True)  # nosec
        version_line = str(run_res.stdout.splitlines()[0], "utf-8")
        prefix = "version.BuildInfo"
        if version_line.startswith(prefix):
            version_line = version_line[len(prefix) :].strip("{}")
        else:
            raise ValidationError(self.name, f"Can't parse '{self._helm_bin}' version number.")
        version_entries = version_line.split(",")[0]
        version = version_entries.split(":")[1].strip('"')
        self._assert_version_in_range(self._helm_bin, version, self._min_helm_version, self._max_helm_version)

    def run(self, config: argparse.Namespace, context: Dict[str, Any]) -> None:
        """
        Runs 'helm package' to build the chart.
        :param config: the config object
        :param context: the context object
        :return: None
        """
        args = [
            self._helm_bin,
            "package",
            config.chart_dir,
        ]
        logger.info("Building chart with 'helm package'")
        run_res = subprocess.run(args, capture_output=True)  # nosec, input params checked above in pre_run
        for line in run_res.stdout.splitlines():
            logger.info(str(line, "utf-8"))
            if line.startswith(b"Successfully packaged chart and saved it to"):
                full_chart_path = str(line.split(b":")[1].strip(), "utf-8")
                context[context_key_chart_full_path] = full_chart_path
                context[context_key_chart_file_name] = os.path.basename(full_chart_path)
        if run_res.returncode != 0:
            logger.error(f"{self._helm_bin} run failed with exit code {run_res.returncode}")
            raise BuildError(self.name, "Chart build failed")


class HelmChartMetadataGenerator(BuildStep):
    """
    HelmChartMetadataGenerator generates metadata files based on additional info in Chart.yaml file
    """

    _key_upstream_chart_url = "upstreamChartURL"
    _key_restrictions = "restrictions"
    _key_cluster_singleton = "clusterSingleton"
    _key_namespace_singleton = "namespaceSingleton"
    _key_gpu_instances = "gpuInstances"
    _key_fixed_namespace = "fixedNamespace"
    _key_chart_file = "chartFile"
    _key_digest = "digest"
    _key_date_created = "dateCreated"

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

    def pre_run(self, config: argparse.Namespace) -> None:
        if not config.generate_metadata:
            logger.info("Metadata generation is disabled using 'generate-metadata' option.")
            return
        # first step of validation should be done already by 'ct' with correct schema (unless explicitly disabled)
        chart_yaml_path = os.path.join(config.chart_dir, _chart_yaml)
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
    def get_build_timestamp() -> str:
        return datetime.utcnow().replace(tzinfo=timezone.utc, microsecond=0).isoformat()

    @staticmethod
    def write_meta_file(meta_file_name: str, meta: Dict[str, Any]) -> None:
        with open(meta_file_name, "w") as f:
            yaml.dump(meta, f, default_flow_style=False)

    def run(self, config: argparse.Namespace, context: Dict[str, Any]) -> None:
        if not config.generate_metadata:
            logger.info("Metadata generation is disabled using 'generate-metadata' option.")
            return
        meta = {}
        chart_yaml_path = os.path.join(config.chart_dir, _chart_yaml)
        with open(chart_yaml_path, "r") as file:
            chart_yaml = yaml.safe_load(file)
        meta[self._key_chart_file] = context[context_key_chart_file_name]
        meta[self._key_digest] = get_file_sha256(context[context_key_chart_file_name])
        if self._key_upstream_chart_url in chart_yaml:
            meta[self._key_upstream_chart_url] = chart_yaml[self._key_upstream_chart_url]
        meta[self._key_date_created] = self.get_build_timestamp()
        if self._key_restrictions in chart_yaml:
            meta[self._key_restrictions] = {}
            for key in [
                self._key_cluster_singleton,
                self._key_namespace_singleton,
                self._key_fixed_namespace,
                self._key_gpu_instances,
            ]:
                if key in chart_yaml[self._key_restrictions]:
                    meta[self._key_restrictions][key] = chart_yaml[self._key_restrictions][key]
        meta_dir_name = f"{context[context_key_chart_file_name]}-meta"
        pathlib.Path(meta_dir_name).mkdir(exist_ok=True)
        meta_file_name = os.path.join(meta_dir_name, "main.yaml")
        self.write_meta_file(meta_file_name, meta)
        logger.info(f"Metadata file saved to '{meta_file_name}'")


class HelmBuildFilteringPipeline(BuildStepsFilteringPipeline):
    """
    Pipeline that combines all the steps required to use helm3 as a chart builder.
    """

    def __init__(self):
        super().__init__(
            [
                HelmBuilderValidator(),
                HelmGitVersionSetter(),
                HelmChartToolLinter(),
                HelmChartBuilder(),
                HelmChartMetadataGenerator(),
            ],
            "Helm 3 build engine options",
        )
