import argparse
from typing import Any


def get_config_attribute_from_cmd_line_option(cmd_line_opt: str) -> str:
    return cmd_line_opt.lstrip("-").replace("-", "_")


def get_config_value_by_cmd_line_option(config: argparse.Namespace, cmd_line_opt: str) -> Any:
    return getattr(config, get_config_attribute_from_cmd_line_option(cmd_line_opt))
