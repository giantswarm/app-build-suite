"""Build steps implementing helm3 based builds."""
import argparse
import logging
import os
import pathlib
import shutil
from datetime import datetime
from typing import List, Optional, Set
from urllib.parse import urlsplit

import configargparse
import validators
import yaml

from app_build_suite.build_steps.steps import STEP_BUILD, STEP_VALIDATE, STEP_STATIC_CHECK, STEP_METADATA
from app_build_suite.errors import BuildError
from step_exec_lib.errors import ValidationError
from step_exec_lib.steps import BuildStep, BuildStepsFilteringPipeline
from step_exec_lib.types import Context, StepType
from step_exec_lib.utils.files import get_file_sha256
from step_exec_lib.utils.git import GitRepoVersionInfo
from step_exec_lib.utils.processes import run_and_log

logger = logging.getLogger(__name__)

context_key_chart_full_path: str = "chart_full_path"
context_key_chart_file_name: str = "chart_file_name"
context_key_git_version: str = "git_version"
context_key_changes_made: str = "changes_made"
context_key_meta_dir_path: str = "meta_dir_path"
context_key_chart_lock_files_to_restore: str = "chart_lock_files_to_restore"

_chart_yaml_app_version_key = "appVersion"
_chart_yaml_chart_version_key = "version"
_chart_yaml = "Chart.yaml"
_values_yaml = "values.yaml"
_chart_lock = "Chart.lock"
_requirements_lock = "requirements.lock"


class HelmBuilderValidator(BuildStep):
    """
    Very simple validator that checks if the folder looks like Helm chart at all.
    """

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_BUILD}

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

    def run(self, config: argparse.Namespace, context: Context) -> None:
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
            help=f"Should the {_chart_yaml_app_version_key} in {_chart_yaml} be replaced by a tag and hash from git",
        )
        config_parser.add_argument(
            "--replace-chart-version-with-git",
            required=False,
            action="store_true",
            help=f"Should the {_chart_yaml_chart_version_key} in {_chart_yaml} be replaced by a tag and hash from git",
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
        Gets the git-version, then replaces keys in Chart.yaml
        :param config: the config object
        :param context: the context object
        :return: None
        """
        context[context_key_changes_made] = False
        if not self._is_enabled(config):
            logger.debug("No version override options requested, ending step.")
            return

        if self.repo_info is not None:
            git_version = self.repo_info.get_git_version()
        else:
            raise ValidationError(self.name, f"Can't find valid git repository in {config.chart_dir}")
        # add the version info to context, so other BuildSteps can use it
        context[context_key_git_version] = git_version

        new_lines: List[str] = []
        chart_yaml_path = os.path.join(config.chart_dir, _chart_yaml)
        with open(chart_yaml_path, "r") as file:
            lines = file.readlines()
            for line in lines:
                fields = line.split(":")
                if (config.replace_chart_version_with_git and fields[0] == _chart_yaml_chart_version_key) or (
                    config.replace_app_version_with_git and fields[0] == _chart_yaml_app_version_key
                ):
                    logger.info(f"Replacing '{fields[0]}' with git version '{git_version}' in {_chart_yaml}.")
                    context[context_key_changes_made] = True
                    new_lines.append(f"{fields[0]}: {git_version}\n")
                else:
                    new_lines.append(line)
        if context[context_key_changes_made]:
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
        return {STEP_VALIDATE}

    _ct_bin = "ct"
    _min_ct_version = "3.3.1"
    _max_ct_version = "4.0.0"
    _metadata_schema = "gs_metadata_chart_schema.yaml"

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

    def pre_run(self, config: argparse.Namespace) -> None:
        """
        Verifies if the required version of `ct` is installed and config options are sane.
        :param config: the config object
        :return: None
        """
        # verify if binary present
        self._assert_binary_present_in_path(self._ct_bin)
        # verify version
        run_res = run_and_log([self._ct_bin, "version"], capture_output=True)  # nosec
        version_line = run_res.stdout.splitlines()[0]
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

    def run(self, config: argparse.Namespace, _: Context) -> None:
        args = [
            self._ct_bin,
            "lint",
            "--validate-maintainers=false",
            f"--charts={config.chart_dir}",
        ]
        if config.debug:
            args.append("--debug")
        if config.ct_config is not None:
            args.append(f"--config={config.ct_config}")
        if config.ct_schema is not None:
            args.append(f"--chart-yaml-schema={config.ct_schema}")
        logger.info("Running chart tool linting")
        run_res = run_and_log(args, capture_output=True)  # nosec, input params checked above in pre_run
        for line in run_res.stdout.splitlines():
            logger.info(line)
        if run_res.returncode != 0:
            logger.error(f"{self._ct_bin} run failed with exit code {run_res.returncode}")
            raise BuildError(self.name, "Linting failed")


class KubeLinter(BuildStep):
    """
    Runs kube-linter against the chart.
    """

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_STATIC_CHECK}

    _kubelinter_bin = "kube-linter"
    _min_kubelinter_version = "0.1.6"
    _max_kubelinter_version = "0.3.0"
    _default_kubelinter_cfg_file = ".kube-linter.yaml"

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--kubelinter-config",
            required=False,
            help=f"Path to optional 'kube-linter' config file. If empty, tries to load "
            f"'{self._default_kubelinter_cfg_file}'.",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        """
        Verifies if the required version of `kube-linter` is installed and config options are sane.
        :param config: the config object
        :return: None
        """
        # verify if binary present
        self._assert_binary_present_in_path(self._kubelinter_bin)
        # verify version
        run_res = run_and_log([self._kubelinter_bin, "version"], capture_output=True)  # nosec
        version = run_res.stdout.splitlines()[0]
        self._assert_version_in_range(
            self._kubelinter_bin, version, self._min_kubelinter_version, self._max_kubelinter_version
        )
        # validate config options
        if config.kubelinter_config is not None and not os.path.isabs(config.kubelinter_config):
            config.kubelinter_config = os.path.join(os.getcwd(), config.kubelinter_config)
        if config.kubelinter_config is not None and not os.path.isfile(config.kubelinter_config):
            raise ValidationError(
                self.name,
                f"Kube-linter config file {config.kubelinter_config} doesn't exist.",
            )
        _default_cfg_path = os.path.join(config.chart_dir, self._default_kubelinter_cfg_file)
        if not config.kubelinter_config and os.path.isfile(_default_cfg_path):
            config.kubelinter_config = _default_cfg_path

    def run(self, config: argparse.Namespace, _: Context) -> None:
        args = [
            self._kubelinter_bin,
            "lint",
            config.chart_dir,
            "--verbose",
        ]

        # adding `--verbose` to the default args due to the kube-linter hiding
        # some problems and thus skipping linting some of the resources.

        if config.kubelinter_config is not None:
            args.append(f"--config={config.kubelinter_config}")
        logger.info("Running kube-linter tool")
        run_res = run_and_log(args, capture_output=True)  # nosec, input params checked above in pre_run
        for line in run_res.stdout.splitlines():
            logger.info(line)
        if run_res.returncode != 0:
            logger.error(f"{self._kubelinter_bin} run failed with exit code {run_res.returncode}")
            for line in run_res.stderr.splitlines():
                logger.error(line)
            raise BuildError(self.name, "kube-linter failed")


class HelmRequirementsUpdater(BuildStep):
    """
    Executes helm dependency update.
    """

    _helm_bin = "helm"
    _min_helm_version = "3.5.2"
    _max_helm_version = "4.0.0"

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_BUILD}

    # noinspection PyMethodMayBeStatic
    def _should_run(self, config: argparse.Namespace) -> bool:
        return config.replace_chart_version_with_git

    # noinspection PyMethodMayBeStatic
    def _detect_chart_lock_files(self, config: argparse.Namespace) -> List[str]:
        lock_files = []
        if os.path.isfile(os.path.join(config.chart_dir, _chart_lock)):
            lock_files.append(_chart_lock)
        if os.path.isfile(os.path.join(config.chart_dir, _requirements_lock)):
            lock_files.append(_requirements_lock)
        return lock_files

    def pre_run(self, config: argparse.Namespace) -> None:
        """
        Checks if the required version of helm is installed and if a lock file is present.
        :param config: the config object
        :return: None
        """
        if not self._should_run(config):
            logger.debug("No chart version override requested, skipping dependency update.")
            return
        if len(self._detect_chart_lock_files(config)) == 0:
            logger.debug(f"No {_chart_lock} or {_requirements_lock} file exists, skipping dependency update.")
            return
        self._assert_binary_present_in_path(self._helm_bin)
        run_res = run_and_log([self._helm_bin, "version"], capture_output=True)  # nosec
        version_line = run_res.stdout.splitlines()[0]
        prefix = "version.BuildInfo"
        if version_line.startswith(prefix):
            version_line = version_line[len(prefix) :].strip("{}")
        else:
            raise ValidationError(self.name, f"Can't parse '{self._helm_bin}' version number.")
        version_entries = version_line.split(",")[0]
        version = version_entries.split(":")[1].strip('"')
        self._assert_version_in_range(self._helm_bin, version, self._min_helm_version, self._max_helm_version)

    def run(self, config: argparse.Namespace, context: Context) -> None:
        """
        Runs 'helm dependencies update' to update or generate a Chart.lock file.
        :param config: the config object
        :param context: the context object
        :return: None
        """
        context[context_key_chart_lock_files_to_restore] = []
        present_lock_files = self._detect_chart_lock_files(config)
        if not self._should_run(config):
            logger.debug("No chart version override requested. Dependency update not required, ending step.")
            return
        if len(present_lock_files) == 0:
            logger.debug(f"No {_chart_lock} or {_requirements_lock} file exists, skipping dependency update.")
            return
        args = []
        for lock_file in present_lock_files:
            logger.debug(f"Saving backup of {lock_file} in {lock_file}.back")
            lock_path = os.path.join(config.chart_dir, lock_file)
            shutil.copy2(lock_path, lock_path + ".back")
            args = [
                self._helm_bin,
                "dependencies",
                "update",
                config.chart_dir,
            ]
            context[context_key_chart_lock_files_to_restore].append(lock_file)
        logger.info(f"Updating lockfile(s) with 'helm dependencies update {config.chart_dir}'")
        run_res = run_and_log(args, capture_output=True)  # nosec, input params checked above in pre_run
        if run_res.returncode != 0:
            logger.error(f"{self._helm_bin} run failed with exit code {run_res.returncode}")
            raise BuildError(self.name, "Chart dependency update failed")


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

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--destination",
            required=False,
            default=".",
            help="Path of a directory to store the packaged tgz.",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        """
        Checks if the required version of helm is installed.
        :param config: the config object
        :return: None
        """
        self._assert_binary_present_in_path(self._helm_bin)
        run_res = run_and_log([self._helm_bin, "version"], capture_output=True)  # nosec
        version_line = run_res.stdout.splitlines()[0]
        prefix = "version.BuildInfo"
        if version_line.startswith(prefix):
            version_line = version_line[len(prefix) :].strip("{}")
        else:
            raise ValidationError(self.name, f"Can't parse '{self._helm_bin}' version number.")
        version_entries = version_line.split(",")[0]
        version = version_entries.split(":")[1].strip('"')
        self._assert_version_in_range(self._helm_bin, version, self._min_helm_version, self._max_helm_version)

    def run(self, config: argparse.Namespace, context: Context) -> None:
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
            "--destination",
            config.destination,
        ]
        logger.info("Building chart with 'helm package'")
        run_res = run_and_log(args, capture_output=True)  # nosec, input params checked above in pre_run
        for line in run_res.stdout.splitlines():
            logger.info(line)
            if line.startswith("Successfully packaged chart and saved it to"):
                full_chart_path = line.split(":")[1].strip()
                full_chart_path = os.path.abspath(full_chart_path)
                # compare our expected chart_file_name with the one returned from helm and fail if differs
                helm_chart_file_name = os.path.basename(full_chart_path)
                if (
                    context_key_chart_file_name in context
                    and helm_chart_file_name != context[context_key_chart_file_name]
                ):
                    raise BuildError(
                        self.name,
                        f"unexpected chart path '{helm_chart_file_name}' != '{context[context_key_chart_file_name]}'",
                    )
                if context_key_chart_full_path in context and full_chart_path != context[context_key_chart_full_path]:
                    raise BuildError(
                        self.name,
                        f"unexpected helm build result: path reported in output '{full_chart_path}' "
                        f"is not equal to '{context[context_key_chart_full_path]}'",
                    )
        if run_res.returncode != 0:
            logger.error(f"{self._helm_bin} run failed with exit code {run_res.returncode}")
            raise BuildError(self.name, "Chart build failed")


class HelmChartMetadataPreparer(BuildStep):
    """
    HelmChartMetadataPreparer prepares metadata generation based on additional info in Chart.yaml file.
    Should run before HelmChartBuilder
    """

    _key_upstream_chart_url = "upstreamChartURL"
    _key_upstream_chart_version = "upstreamChartVersion"
    _key_restrictions = "restrictions"
    _key_cluster_singleton = "clusterSingleton"
    _key_namespace_singleton = "namespaceSingleton"
    _key_gpu_instances = "gpuInstances"
    _key_fixed_namespace = "fixedNamespace"
    _key_annotations = "annotations"
    _key_annotation_metadata_url = "application.giantswarm.io/metadata"

    _annotation_files_map = {
        "./values.schema.json": "application.giantswarm.io/values-schema",
        "../../README.md": "application.giantswarm.io/readme",
    }

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
        if config.generate_metadata and not config.catalog_base_url:
            raise ValidationError(
                self.name, "config option --generate-metadata requires non-empty option --catalog-base-url"
            )
        if not config.catalog_base_url.endswith("/"):
            raise ValidationError(self.name, "config option --catalog-base-url value should end with a /")
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
    def write_chart_yaml(chart_yaml_file_name: str, data: Context) -> None:
        with open(chart_yaml_file_name, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def build_file_annotations(
        self, catalog_base_url: str, chart_file_name: str, chart_dir: str, meta_dir_path: str
    ) -> Context:
        """
        Based upon the _annotations_files_map:
          - check if the file is available
          - include it in the annotations
          - copy it into the metadata directory
        """
        catalog_url = f"{catalog_base_url}{chart_file_name}-meta/"
        annotations = {self._key_annotation_metadata_url: urlsplit(f"{catalog_url}main.yaml").geturl()}
        for additional_file, annotation_key in self._annotation_files_map.items():
            source_file_path = os.path.join(os.path.abspath(chart_dir), additional_file)
            if os.path.isfile(source_file_path):
                annotations[annotation_key] = urlsplit(f"{catalog_url}{os.path.basename(additional_file)}").geturl()
                target_file_path = os.path.join(meta_dir_path, os.path.basename(additional_file))
                shutil.copy2(source_file_path, target_file_path)

        return annotations

    def run(self, config: argparse.Namespace, context: Context) -> None:
        if not config.generate_metadata:
            logger.info("Metadata generation is disabled using 'generate-metadata' option.")
            return
        # read current Chart.yaml
        chart_yaml_path = os.path.join(config.chart_dir, _chart_yaml)
        with open(chart_yaml_path, "r") as file:
            chart_yaml = yaml.safe_load(file)
        original_annotations = chart_yaml.get(self._key_annotations, None)
        # try to guess the package file name. we need it for url generation in annotations
        chart_name = chart_yaml["name"]
        chart_version = chart_yaml["version"]
        context[context_key_chart_file_name] = f"{chart_name}-{chart_version}.tgz"
        context[context_key_chart_full_path] = os.path.abspath(
            os.path.join(config.destination, context[context_key_chart_file_name])
        )
        # create metadata directory
        context[context_key_meta_dir_path] = f"{context[context_key_chart_full_path]}-meta"
        pathlib.Path(context[context_key_meta_dir_path]).mkdir(parents=True, exist_ok=True)
        # put in generated annotations
        chart_yaml[self._key_annotations] = {
            **chart_yaml.get(self._key_annotations, {}),
            **self.build_file_annotations(
                config.catalog_base_url,
                context[context_key_chart_file_name],
                config.chart_dir,
                context[context_key_meta_dir_path],
            ),
        }
        # save Chart.yaml
        if (
            not context.get(context_key_changes_made, False)
            and original_annotations != chart_yaml[self._key_annotations]
        ):
            logger.debug(f"Saving backup of {_chart_yaml} in {_chart_yaml}.back")
            shutil.copy2(chart_yaml_path, chart_yaml_path + ".back")
            context[context_key_changes_made] = True
        self.write_chart_yaml(chart_yaml_path, chart_yaml)


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
        chart_yaml_path = os.path.join(config.chart_dir, _chart_yaml)
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
        return datetime.utcnow().isoformat(timespec="microseconds")

    @staticmethod
    def write_meta_file(meta_file_name: str, meta: Context) -> None:
        with open(meta_file_name, "w") as f:
            yaml.dump(meta, f, default_flow_style=False)

    def run(self, config: argparse.Namespace, context: Context) -> None:
        if not config.generate_metadata:
            logger.info("Metadata generation is disabled using 'generate-metadata' option.")
            return
        meta = {}
        chart_yaml_path = os.path.join(config.chart_dir, _chart_yaml)
        with open(chart_yaml_path, "r") as file:
            chart_yaml = yaml.safe_load(file)
        # mandatory metadata
        meta[self._key_chart_file] = context[context_key_chart_file_name]
        meta[self._key_digest] = get_file_sha256(context[context_key_chart_full_path])
        meta[self._key_date_created] = self.get_build_timestamp()
        meta[self._key_chart_api_version] = chart_yaml[self._key_api_version]
        # optional metadata
        for key in [
            self._key_upstream_chart_url,
            self._key_upstream_chart_version,
            self._key_restrictions,
            self._key_annotations,
            self._key_icon,
            self._key_home,
        ]:
            if key in chart_yaml:
                meta[key] = chart_yaml[key]
        # save metadata file
        pathlib.Path(context[context_key_meta_dir_path]).mkdir(exist_ok=True)
        meta_file_name = os.path.join(context[context_key_meta_dir_path], "main.yaml")
        self.write_meta_file(meta_file_name, meta)
        logger.info(f"Metadata file saved to '{meta_file_name}'")


class HelmChartYAMLRestorer(BuildStep):
    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_BUILD}

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--keep-chart-changes",
            required=False,
            action="store_true",
            help=f"Should the changes made in {_chart_yaml} be kept",
        )

    def run(self, config: argparse.Namespace, context: Context) -> None:
        # nothing to do here, we run in cleanup
        pass

    def cleanup(
        self,
        config: argparse.Namespace,
        context: Context,
        has_build_failed: bool,
    ) -> None:
        if config.keep_chart_changes:
            logger.info(f"Skipping restore of {_chart_yaml}.")
            return
        if context_key_changes_made in context and context[context_key_changes_made]:
            logger.info(f"Restoring backup {_chart_yaml}.back to {_chart_yaml}")
            chart_yaml_path = os.path.join(config.chart_dir, _chart_yaml)
            shutil.move(chart_yaml_path + ".back", chart_yaml_path)
        if context_key_chart_lock_files_to_restore in context and context[context_key_chart_lock_files_to_restore]:
            for file_name in context[context_key_chart_lock_files_to_restore]:
                logger.info(f"Restoring backup {file_name}.back to {file_name}")
                lock_file_path = os.path.join(config.chart_dir, file_name)
                shutil.move(lock_file_path + ".back", lock_file_path)


class HelmBuildFilteringPipeline(BuildStepsFilteringPipeline):
    """
    Pipeline that combines all the steps required to use helm3 as a chart builder.
    """

    def __init__(self) -> None:
        super().__init__(
            [
                HelmBuilderValidator(),
                HelmGitVersionSetter(),
                HelmRequirementsUpdater(),
                HelmChartToolLinter(),
                KubeLinter(),
                HelmChartMetadataPreparer(),
                HelmChartBuilder(),
                HelmChartMetadataFinalizer(),
                HelmChartYAMLRestorer(),
            ],
            "Helm 3 build engine options",
        )
