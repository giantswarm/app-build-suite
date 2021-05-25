import argparse
from typing import Any

import semver

from step_exec_lib.errors import ValidationError


def get_config_attribute_from_cmd_line_option(cmd_line_opt: str) -> str:
    return cmd_line_opt.lstrip("-").replace("-", "_")


def get_config_value_by_cmd_line_option(config: argparse.Namespace, cmd_line_opt: str) -> Any:
    return getattr(config, get_config_attribute_from_cmd_line_option(cmd_line_opt))


def assert_version_in_range(
    check_source_name: str, app_name: str, version: str, min_version: str, max_version_exc: str
) -> None:
    """
    Checks if the given app_name with a string version falls in between specified min and max
    versions (min_version <= version < max_version). Raises ValidationError.
    :param check_source_name: The name of the component making the check (for clear exception source).
    :param app_name: The name of the app (used just for logging purposes).
    :param version: The version string (semver, might start with optional 'v' prefix).
    :param min_version: proper semver version string to check for (includes this version)
    :param max_version_exc: proper semver version string to check for (excludes this version)
    :return:
    """
    if version.startswith("v"):
        version = version[1:]
    parsed_ver = semver.VersionInfo.parse(version)
    parsed_min_version = semver.VersionInfo.parse(min_version)
    parsed_max_version = semver.VersionInfo.parse(max_version_exc)
    if parsed_ver < parsed_min_version:
        raise ValidationError(
            check_source_name,
            f"Min version '{min_version}' of '{app_name}' is required, '{parsed_ver}' found.",
        )
    if parsed_ver >= parsed_max_version:
        raise ValidationError(
            check_source_name,
            f"Version '{parsed_ver}' of '{app_name}' is detected, but lower than {max_version_exc} is required.",
        )
