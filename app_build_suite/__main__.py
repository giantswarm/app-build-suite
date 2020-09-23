"""Main module."""
import logging
from typing import List

import configargparse

from app_build_suite.build_steps import (
    BuildStep,
    HelmBuilderValidator,
    GitVersionSetter,
    Error,
)

version = "0.0.1"
app_name = "app_build_suite"
logger = logging.getLogger(app_name)


def get_pipeline() -> List[BuildStep]:
    return [HelmBuilderValidator(), GitVersionSetter()]


def configure_global_options(config_parser: configargparse.ArgParser):
    config_parser.add_argument(
        "-d",
        "--debug",
        required=False,
        action="store_false",
        help="Enable debug messages.",
    )
    config_parser.add_argument(
        "--version", action="version", version=f"{app_name} v{version}"
    )


def main():
    steps = get_pipeline()

    # initialize config, setup arg parsers
    config_parser = configargparse.ArgParser(
        prog=app_name,
        add_config_file_help=True,
        default_config_files=[".abs.yaml"],
        description="Build and test Giant Swarm App Platform app.",
        add_env_var_help=True,
        auto_env_var_prefix="ABS_",
    )
    configure_global_options(config_parser)
    for step in steps:
        step.initialize_config(config_parser)
    config = config_parser.parse_args()

    # configure logging
    if config.debug:
        logger.setLevel(logging.DEBUG)

    logger.debug(config_parser.format_values())

    # run pre-run steps: validation
    for step in steps:
        logger.debug(f"Running pre-run step for {step.name}")
        try:
            step.pre_run(config)
        except Error as e:
            logger.error(f"Error when running pre-run step for {step.name}: {e.msg}")


if __name__ == "__main__":
    main()
