import configargparse
from step_exec_lib.steps import BuildStep


def get_test_config_parser() -> configargparse.ArgParser:
    config_parser = configargparse.ArgParser(
        prog="test session",
        description="test session",
        formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
        add_help=True,
    )
    steps_group = config_parser.add_mutually_exclusive_group()
    steps_group.add_argument(
        "--steps",
        nargs="+",
        help="List of steps to execute.",
        required=False,
        default=["all"],
    )
    steps_group.add_argument(
        "--skip-steps",
        nargs="+",
        help="List of steps to skip.",
        required=False,
        default=[],
    )
    return config_parser


def init_config_for_step(step: BuildStep) -> configargparse.Namespace:
    config_parser = get_test_config_parser()
    step.initialize_config(config_parser)
    config = config_parser.parse_known_args()[0]
    config.chart_dir = "res_test_helm"
    return config
