import argparse
import logging
import os
import shutil
from typing import List, Optional

import configargparse

from app_build_suite.build_steps import BuildStep
from app_build_suite.build_steps.errors import ValidationError
from app_build_suite.utils.git import GitRepoVersionInfo

logger = logging.getLogger(__name__)

_chart_yaml_app_version_key = "appVersion"
_chart_yaml_chart_version_key = "version"
_chart_yaml = "Chart.yaml"
_values_yaml = "values.yaml"


class HelmGitVersionSetter(BuildStep):
    repo_info: Optional[GitRepoVersionInfo] = None

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--replace-app-version-with-git",
            required=False,
            action="store_false",
            help=f"Should the {_chart_yaml_app_version_key}  in {_chart_yaml} be replaced by a tag and hash from git",
        )
        config_parser.add_argument(
            "--replace-chart-version-with-git",
            required=False,
            action="store_false",
            help=f"Should the {_chart_yaml_chart_version_key} in {_chart_yaml} be replaced by a tag and hash from git",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        self.repo_info = GitRepoVersionInfo(config.chart_dir)
        if not self.repo_info.is_git_repo:
            raise ValidationError(
                self.name, f"Can't find valid git repository in {config.chart_dir}"
            )

    def run(self, config: argparse.Namespace) -> None:
        """
        Gets the git-version, then replaces keys in Chart.yaml
        :param config: the config object
        :return: None
        """
        if self.repo_info is not None:
            git_version = self.repo_info.get_git_version
        else:
            raise ValidationError(
                self.name, f"Can't find valid git repository in {config.chart_dir}"
            )
        new_lines: List[str] = []
        changes_made = False
        chart_yaml_path = os.path.join(config.chart_dir, _chart_yaml)
        with open(chart_yaml_path, "r") as file:
            lines = file.readlines()
            for line in lines:
                fields = line.split(":")
                if (
                    config.replace_chart_version_with_git
                    and fields[0] == _chart_yaml_chart_version_key
                ) or (
                    config.replace_app_version_with_git
                    and fields[0] == _chart_yaml_app_version_key
                ):
                    logger.info(
                        f"Replacing '{fields[0]}' with get version '{git_version}' in {_chart_yaml}."
                    )
                    changes_made = True
                    new_lines.append(f"{fields[0]}: {git_version}")
                else:
                    new_lines.append(line)
        if changes_made:
            logger.debug(f"Saving backup of {_chart_yaml} in {_chart_yaml}.back")
            shutil.copy2(chart_yaml_path, chart_yaml_path + ".back")
            with open(chart_yaml_path, "w") as file:
                logger.info(f"Saving {_chart_yaml} with version set from git.")
                file.writelines(new_lines)

    def cleanup(self, config: argparse.Namespace) -> None:
        pass


class HelmBuilderValidator(BuildStep):
    """Very simple validator that checks of the folder looks like Helm chart at all.
    """

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "-c",
            "--chart-dir",
            required=False,
            default=".",
            help="Path to the Helm Chart to build. Default is local dir.",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        """Validates if basic chart files are present in the configured directory."""
        if os.path.exists(
            os.path.join(config.chart_dir, _chart_yaml)
        ) and os.path.exists(os.path.join(config.chart_dir, _values_yaml)):
            return
        raise ValidationError(
            self.name, f"Can't find '{_chart_yaml}' or '{_values_yaml}' files."
        )

    def run(self, config: argparse.Namespace) -> None:
        pass

    def cleanup(self, config: argparse.Namespace) -> None:
        pass
