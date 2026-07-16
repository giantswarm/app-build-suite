"""Build step: renders the chart with 'helm template' and validates the output YAML."""

import argparse
import logging
import os
from typing import Set

import configargparse
import yaml
from step_exec_lib.errors import ValidationError
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType
from step_exec_lib.utils.processes import run_and_log

from app_build_suite.build_steps.steps import STEP_VALIDATE
from app_build_suite.errors import BuildError
from app_build_suite.utils.yaml_strict import DuplicateKeyError, UniqueKeyLoader, find_nearest_source

logger = logging.getLogger(__name__)


class HelmTemplateValidator(BuildStep):
    """
    Renders the chart with 'helm template' and validates that the rendered manifests
    are parseable YAML without duplicate mapping keys (which helm and Kubernetes
    silently resolve by keeping the last value, dropping configuration).
    """

    _helm_bin = "helm"
    _min_helm_version = "3.2.0"
    _max_helm_version = "4.0.0"
    _release_name = "abs-validation"

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_VALIDATE}

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--disable-helm-template-validator",
            required=False,
            default=False,
            action="store_true",
            help="Disable rendering the chart with 'helm template' and validating the output YAML.",
        )
        config_parser.add_argument(
            "--helm-template-extra-values",
            required=False,
            action="append",
            help="Path to an extra values file passed to 'helm template' as '--values'. Use for charts that"
            " don't render with default values only (e.g. templates using 'required'). Can be used multiple"
            " times.",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        """
        Checks if the required version of helm is installed and the configured values files exist.
        :param config: the config object
        :return: None
        """
        if config.disable_helm_template_validator:
            logger.debug("Helm template validation is disabled, skipping pre-run.")
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
        extra_values = config.helm_template_extra_values or []
        for i, values_file in enumerate(extra_values):
            if not os.path.isabs(values_file):
                extra_values[i] = values_file = os.path.join(os.getcwd(), values_file)
            if not os.path.isfile(values_file):
                raise ValidationError(
                    self.name,
                    f"Values file '{values_file}' configured with '--helm-template-extra-values' doesn't exist.",
                )

    def run(self, config: argparse.Namespace, _: Context) -> None:
        if config.disable_helm_template_validator:
            logger.info("Helm template validation is disabled, skipping.")
            return
        args = [
            self._helm_bin,
            "template",
            self._release_name,
            config.chart_dir,
            "--include-crds",
        ]
        for values_file in config.helm_template_extra_values or []:
            args += ["--values", values_file]
        logger.info("Rendering the chart with 'helm template' to validate the output.")
        run_res = run_and_log(args, capture_output=True)  # nosec, input params checked above in pre_run
        if run_res.returncode != 0:
            logger.error(f"{self._helm_bin} template run failed with exit code {run_res.returncode}")
            for line in run_res.stderr.splitlines():
                logger.error(line)
            raise BuildError(self.name, "'helm template' rendering failed")
        rendered = run_res.stdout
        try:
            doc_count = sum(1 for _ in yaml.load_all(rendered, Loader=UniqueKeyLoader))  # nosec, safe subclass
        except DuplicateKeyError as e:
            source = find_nearest_source(rendered, e.line)
            in_template = f" (template: '{source}')" if source else ""
            raise BuildError(self.name, f"Duplicate YAML key in the rendered chart{in_template}: {e}")
        except yaml.MarkedYAMLError as e:
            line = e.problem_mark.line + 1 if e.problem_mark else 0
            source = find_nearest_source(rendered, line) if line else None
            in_template = f" (template: '{source}')" if source else ""
            raise BuildError(self.name, f"Invalid YAML in the rendered chart{in_template}: {e}")
        except yaml.YAMLError as e:
            raise BuildError(self.name, f"Invalid YAML in the rendered chart: {e}")
        logger.info(f"Rendered chart is valid YAML ({doc_count} documents, no duplicate keys).")
