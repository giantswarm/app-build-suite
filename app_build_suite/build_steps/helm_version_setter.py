"""Build step: sets chart version/appVersion from command line arguments."""

import argparse
import logging
from typing import Set

import configargparse
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType

from app_build_suite.build_steps.helm_consts import (
    CHART_YAML,
    CHART_YAML_APP_VERSION_KEY,
    CHART_YAML_CHART_VERSION_KEY,
    context_key_changes_made,
    context_key_chart_yaml,
)
from app_build_suite.build_steps.steps import STEP_BUILD

logger = logging.getLogger(__name__)


class HelmVersionSetter(BuildStep):
    """
    Sets chart `version` and/or `appVersion` from explicit command line arguments.

    `--keep-app-version` opts `appVersion` out of being set at all. It is meant to be set in the config
    file, so the repository owning the chart decides: the caller computes a version, but only the
    repository knows whether `appVersion` means something other than that version. Passing both is a
    caller bug and warns; taking precedence over `--override-app-version` is a backstop, not the
    mechanism, so a caller that reads the config should simply not pass the flag.
    """

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_BUILD}

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--override-chart-version",
            required=False,
            default=None,
            help=f"Override the {CHART_YAML_CHART_VERSION_KEY} in {CHART_YAML} with this value.",
        )
        config_parser.add_argument(
            "--override-app-version",
            required=False,
            default=None,
            help=f"Override the {CHART_YAML_APP_VERSION_KEY} in {CHART_YAML} with this value.",
        )
        config_parser.add_argument(
            "--keep-app-version",
            required=False,
            action="store_true",
            help=f"Keep the {CHART_YAML_APP_VERSION_KEY} declared in {CHART_YAML} and ignore "
            f"--override-app-version. For a chart that vendors an upstream release and declares that "
            f"release as its {CHART_YAML_APP_VERSION_KEY}, where the caller's computed version belongs "
            f"in the chart's own version only. Settable from the config file, so the repository that "
            f"owns the chart decides rather than the calling pipeline.",
        )
        # Deprecated options kept for backward compatibility — they have no effect.
        config_parser.add_argument(
            "--replace-chart-version-with-git",
            required=False,
            action="store_true",
            help="DEPRECATED: Has no effect. Use --override-chart-version instead.",
        )
        config_parser.add_argument(
            "--replace-app-version-with-git",
            required=False,
            action="store_true",
            help="DEPRECATED: Has no effect. Use --override-app-version instead.",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        if config.replace_chart_version_with_git:
            logger.warning(
                "DEPRECATED: --replace-chart-version-with-git is no longer used and has no effect. "
                "Use --override-chart-version instead."
            )
        if config.replace_app_version_with_git:
            logger.warning(
                "DEPRECATED: --replace-app-version-with-git is no longer used and has no effect. "
                "Use --override-app-version instead."
            )

    def run(self, config: argparse.Namespace, context: Context) -> None:
        if config.override_chart_version is not None:
            logger.info(f"Overriding 'version' with '{config.override_chart_version}' in {CHART_YAML}.")
            context[context_key_chart_yaml][CHART_YAML_CHART_VERSION_KEY] = config.override_chart_version
            context[context_key_changes_made] = True

        if config.keep_app_version:
            if config.override_app_version is not None:
                # A caller that knows about --keep-app-version should not pass a value it
                # cannot apply, so warn rather than discard it quietly.
                logger.warning(
                    f"Keeping the '{CHART_YAML_APP_VERSION_KEY}' declared in {CHART_YAML}; "
                    f"ignoring --override-app-version '{config.override_app_version}' "
                    f"because --keep-app-version is set. Prefer not passing "
                    f"--override-app-version at all when the chart keeps its own "
                    f"{CHART_YAML_APP_VERSION_KEY}."
                )
        elif config.override_app_version is not None:
            logger.info(f"Overriding 'appVersion' with '{config.override_app_version}' in {CHART_YAML}.")
            context[context_key_chart_yaml][CHART_YAML_APP_VERSION_KEY] = config.override_app_version
            context[context_key_changes_made] = True
