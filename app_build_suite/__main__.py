"""Main module. Loads configuration and executes main control loops."""
import logging
import os
import sys
from typing import List, NewType

import configargparse

from step_exec_lib.steps import (
    BuildStep,
    BuildStepsFilteringPipeline,
)
from step_exec_lib.types import STEP_ALL

from app_build_suite.build_steps.helm import HelmBuildFilteringPipeline
from step_exec_lib.errors import ConfigError
from step_exec_lib.steps import Runner

from app_build_suite.build_steps.steps import ALL_STEPS

ver = "v0.0.0-dev"
app_name = "app_build_suite"
logger = logging.getLogger(__name__)

BuildEngineType = NewType("BuildEngineType", str)
BUILD_ENGINE_HELM3 = BuildEngineType("helm3")
ALL_BUILD_ENGINES = [BUILD_ENGINE_HELM3]


def get_version() -> str:
    try:
        from .version import build_ver

        return build_ver
    except ImportError:
        return ver


def get_pipeline() -> List[BuildStepsFilteringPipeline]:
    return [
        # FIXME: once we have more than 1 build or test engine, this has to be configurable
        HelmBuildFilteringPipeline(),
    ]


def configure_global_options(config_parser: configargparse.ArgParser) -> None:
    config_parser.add_argument(
        "-d",
        "--debug",
        required=False,
        default=False,
        action="store_true",
        help="Enable debug messages.",
    )
    config_parser.add_argument("--version", action="version", version=f"{app_name} {get_version()}")
    config_parser.add_argument(
        "-b",
        "--build-engine",
        required=False,
        default="helm3",
        type=BuildEngineType,
        help="Select the build engine used for building your chart.",
    )
    steps_group = config_parser.add_mutually_exclusive_group()
    steps_group.add_argument(
        "--steps",
        nargs="+",
        help=f"List of steps to execute. Available steps: {ALL_STEPS}",
        required=False,
        default=["all"],
    )
    steps_group.add_argument(
        "--skip-steps",
        nargs="+",
        help=f"List of steps to skip. Available steps: {ALL_STEPS}",
        required=False,
        default=[],
    )


def get_default_config_file_path() -> str:
    # this is the only place where we check for command line option directly,
    # as that's the only way to change where we load the file from
    # FIXME: it's also hacky, as it relies on helm pipeline to provide the "-c" option
    short_opt = "-c"
    long_opt = "--chart-dir"
    base_dir = os.getcwd()
    charts_config_path = ""
    if short_opt in sys.argv or long_opt in sys.argv:
        opt = short_opt if short_opt in sys.argv else long_opt
        c_ind = sys.argv.index(opt)
        chart_dir = sys.argv[c_ind + 1]
        charts_config_path = os.path.join(base_dir, chart_dir, ".abs", "main.yaml")
    if os.path.isfile(charts_config_path):
        config_path = charts_config_path
    else:
        config_path = os.path.join(base_dir, ".abs", "main.yaml")
    logger.debug(f"Using {config_path} as configuration file path.")
    return config_path


def get_global_config_parser(add_help: bool = True) -> configargparse.ArgParser:
    config_file_path = get_default_config_file_path()
    config_parser = configargparse.ArgParser(
        prog=app_name,
        add_config_file_help=True,
        default_config_files=[config_file_path],
        description="Build and test Giant Swarm App Platform app.",
        add_env_var_help=True,
        auto_env_var_prefix="ABS_",
        formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
        add_help=add_help,
    )
    configure_global_options(config_parser)
    return config_parser


def validate_global_config(config: configargparse.Namespace) -> None:
    # validate build engine
    if config.build_engine not in ALL_BUILD_ENGINES:
        raise ConfigError(
            "build_engine",
            f"Unknown build engine '{config.build_engine}'. Valid engines are: {ALL_BUILD_ENGINES}.",
        )
    # validate steps; '--steps' and '--skip-steps' can't be used together, but that is already
    # enforced by the argparse library
    if STEP_ALL in config.skip_steps:
        raise ConfigError("skip-steps", f"'{STEP_ALL}' is not a reasonable step kind to skip.")
    for step in config.steps + config.skip_steps:
        if step not in ALL_STEPS:
            raise ConfigError("steps", f"Unknown step '{step}'. Valid steps are: {ALL_STEPS}.")


def get_config(steps: List[BuildStep]) -> configargparse.Namespace:
    # initialize config, setup arg parsers
    try:
        config_parser = get_global_config_parser()
        for step in steps:
            step.initialize_config(config_parser)
        config = config_parser.parse_args()
        validate_global_config(config)
    except ConfigError as e:
        logger.error(f"Error when checking config option '{e.config_option}': {e.msg}")
        sys.exit(1)

    logger.info("Starting build with the following options")
    logger.info(f"\n{config_parser.format_values()}")
    return config


def main() -> None:
    log_format = "%(asctime)s %(name)s %(levelname)s: %(message)s"
    logging.basicConfig(format=log_format)
    logging.getLogger().setLevel(logging.INFO)

    global_only_config_parser = get_global_config_parser(add_help=False)
    global_only_config = global_only_config_parser.parse_known_args()[0]
    if global_only_config.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    steps = get_pipeline()
    config = get_config(steps)
    runner = Runner(config, steps)
    runner.run()


if __name__ == "__main__":
    main()
