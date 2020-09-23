import argparse
import os
from abc import ABC, abstractmethod

import configargparse

from app_build_suite.build_steps.errors import ValidationError


class BuildStep(ABC):
    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        raise NotImplementedError

    @abstractmethod
    def pre_run(self, config: argparse.Namespace) -> None:
        raise NotImplementedError

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def cleanup(self) -> None:
        raise NotImplementedError


class HelmBuilderValidator(BuildStep):
    """Very simple validator that checks of the folder looks like Helm chart at all.
    """

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "-c",
            "--chart-dir",
            required=False,
            default=".",
            metavar="chart_dir",
            help="Path to the Helm Chart to build. Default is local dir.",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        """Validates if basic chart files are present in the configured directory."""
        _, _, files = next(os.walk(config.chart_dir))
        if "Chart.yaml" in files and "values.yaml" in files:
            return
        raise ValidationError(
            self.name, "Can't find 'Chart.yaml' or 'values.yaml' files."
        )

    def run(self) -> None:
        pass

    def cleanup(self) -> None:
        pass


class GitVersionSetter(BuildStep):
    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--replace-app-version-with-git",
            required=False,
            action="store_false",
            # metavar="replace_app_version_with_git",
            help="Should the appVersion in Chart.yaml be replaced by a tag and hash from git",
        )
        config_parser.add_argument(
            "--replace-chart-version-with-git",
            required=False,
            action="store_false",
            # metavar="replace_chart_version_with_git",
            help="Should the version in Chart.yaml be replaced by a tag and hash from git",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        pass

    def run(self) -> None:
        pass

    def cleanup(self) -> None:
        pass
