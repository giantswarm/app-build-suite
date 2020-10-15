"""Main module. Loads configuration and executes main control loops."""
import logging
import sys
from typing import List, NewType

import configargparse

from app_build_suite.build_steps import (
    BuildStep,
    BuildStepsFilteringPipeline,
    ALL_STEPS,
)
from app_build_suite.build_steps.errors import ConfigError
from .components import ComponentsContainer, Runner

version = "0.0.1"
app_name = "app_build_suite"
logger = logging.getLogger(__name__)

BuildEngineType = NewType("BuildEngineType", str)
BUILD_ENGINE_HELM3 = BuildEngineType("helm3")
ALL_BUILD_ENGINES = [BUILD_ENGINE_HELM3]


def get_pipeline(container: ComponentsContainer) -> List[BuildStepsFilteringPipeline]:
    return [
        container.builder(),
    ]


def configure_global_options(config_parser: configargparse.ArgParser):
    config_parser.add_argument(
        "-d",
        "--debug",
        required=False,
        default=False,
        action="store_true",
        help="Enable debug messages.",
    )
    config_parser.add_argument(
        "--version", action="version", version=f"{app_name} v{version}"
    )
    config_parser.add_argument(
        "-b",
        "--build-engine",
        required=False,
        default="helm3",
        type=BuildEngineType,
        help="Select the build engine used for building your chart.",
    )
    config_parser.add_argument(
        "--steps",
        nargs="+",
        help=f"List of steps to execute. Available steps: {ALL_STEPS}",
        required=False,
        default=["all"],
    )


def get_global_config_parser(add_help: bool = True) -> configargparse.ArgParser:
    config_parser = configargparse.ArgParser(
        prog=app_name,
        add_config_file_help=True,
        default_config_files=[".abs.yaml"],
        description="Build and test Giant Swarm App Platform app.",
        add_env_var_help=True,
        auto_env_var_prefix="ABS_",
        formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
        add_help=add_help,
    )
    configure_global_options(config_parser)
    return config_parser


def validate_global_config(config: configargparse.Namespace):
    # validate build engine
    if config.build_engine not in ALL_BUILD_ENGINES:
        raise ConfigError(
            "build_engine",
            f"Unknown build engine '{config.build_engine}'. Valid engines are: {ALL_BUILD_ENGINES}.",
        )
    # validate steps
    for step in config.steps:
        if step not in ALL_STEPS:
            raise ConfigError(
                "steps", f"Unknown step '{step}'. Valid steps are: {ALL_STEPS}."
            )


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


def main():
    log_format = "%(asctime)s %(name)s %(levelname)s: %(message)s"
    logging.basicConfig(format=log_format)
    logging.getLogger().setLevel(logging.INFO)

    global_only_config_parser = get_global_config_parser(add_help=False)
    global_only_config = global_only_config_parser.parse_known_args()[0]
    if global_only_config.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    container = ComponentsContainer()
    container.config.from_dict({"build_engine": global_only_config.build_engine},)

    steps = get_pipeline(container)
    config = get_config(steps)
    runner = Runner(config, steps)
    runner.run()


if __name__ == "__main__":
    main()
