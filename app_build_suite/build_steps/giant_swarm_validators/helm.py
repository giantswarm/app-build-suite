"""
General idea for naming validation checks:
- comply to 1 letter + 4 digits pattern
- check types and first letters:
  - file system layout and structure: "F"
  - Chart.yaml related problems "C"
"""
import argparse
import logging
import os
import re
import urllib.request
import urllib.error
from typing import Final, Tuple

from PIL import Image, UnidentifiedImageError
import defusedxml.ElementTree as ET
import yaml
from step_exec_lib.errors import Error

from app_build_suite.build_steps.helm_consts import (
    VALUES_SCHEMA_JSON,
    CHART_YAML,
    TEMPLATES_DIR,
    HELPERS_YAML,
    HELPERS_TPL,
)

logger = logging.getLogger(__name__)


ANNOTATIONS_KEY = "annotations"
GS_TEAM_LABEL_KEY = "application.giantswarm.io/team"


class GiantSwarmValidatorError(Error):
    pass


class HasValuesSchema:
    def get_check_code(self) -> str:
        return "F0001"

    def validate(self, config: argparse.Namespace) -> bool:
        return os.path.exists(os.path.join(config.chart_dir, VALUES_SCHEMA_JSON))


class HasTeamLabel:

    escaped_label = re.escape(GS_TEAM_LABEL_KEY)
    _label_regexp = (
        r"[ \t]*"
        + escaped_label
        + r':[ \t]+{{[ \t]*index[ \t]+\.Chart\.Annotations[ \t]+"'
        + escaped_label
        + r'"[ \t]*(\|[ \t]*default[ \t]+\"[a-zA-Z0-9]+\"[ \t]+){0,1}\|[ \t]*quote[ \t]*}}[ \t]*'
    )

    def get_check_code(self) -> str:
        return "C0001"

    def validate(self, config: argparse.Namespace) -> bool:
        chart_yaml_path = os.path.join(config.chart_dir, CHART_YAML)

        chart_yaml = get_chart_yaml(chart_yaml_path)
        if ANNOTATIONS_KEY not in chart_yaml or GS_TEAM_LABEL_KEY not in chart_yaml[ANNOTATIONS_KEY]:
            logger.info(f"'{GS_TEAM_LABEL_KEY}' annotation not found in '{CHART_YAML}'.")
            return False

        # check if team label is not empty
        if chart_yaml[ANNOTATIONS_KEY][GS_TEAM_LABEL_KEY] is None:
            logger.info(f"'{GS_TEAM_LABEL_KEY}' is present in '{CHART_YAML}', but it's empty.")
            return False

        # Check if _helpers.yaml or _helpers.tpl exists and uses team label
        helpers_file_path = self.get_helpers_file_path(config)
        with open(helpers_file_path, "r") as stream:
            try:
                helpers_yaml_lines = stream.readlines()
            except OSError as exc:
                logger.warning(f"Error reading file '{helpers_file_path}'. Error: {exc}.")
                return False
        label_regexp = re.compile(self._label_regexp)
        if any(label_regexp.match(line) for line in helpers_yaml_lines):
            return True
        logger.info(f"The expected team label not found in '{helpers_file_path}'.")
        logger.info(f"'{helpers_file_path}' must contain a line that matches the regexp '{label_regexp}'.")
        return False

    def get_helpers_file_path(self, config: argparse.Namespace) -> str:
        helpers_file_path = os.path.join(config.chart_dir, TEMPLATES_DIR, HELPERS_YAML)
        if not os.path.exists(helpers_file_path):
            helpers_file_path = os.path.join(config.chart_dir, TEMPLATES_DIR, HELPERS_TPL)
            if not os.path.exists(helpers_file_path):
                raise GiantSwarmValidatorError(
                    f"Template file '{HELPERS_YAML}' or '{HELPERS_TPL}' not found in " f"'{TEMPLATES_DIR}' directory."
                )
        return helpers_file_path


class IconIsAlmostSquare:
    MAX_ALLOWED_DEVIATION: Final[float] = 0.33

    def get_check_code(self) -> str:
        return "C0002"

    def validate(self, config: argparse.Namespace) -> bool:
        chart_yaml_path = os.path.join(config.chart_dir, CHART_YAML)

        chart_yaml = get_chart_yaml(chart_yaml_path)

        icon_path = chart_yaml.get("icon")
        if icon_path is None:
            logger.info(f"Icon not found in '{CHART_YAML}'. Skipping icon validation.")
            return True

        try:
            width, height = self.get_width_height_from_url(icon_path)
        except GiantSwarmValidatorError as e:
            logger.warn(f"Icon validation failed: {e.msg}")
            return False

        deviation = self.get_deviation(width, height)
        valid = self.is_almost_square(deviation)
        if not valid:
            logger.warn(
                "The icon should be close to a square shape, but it is not.\n "
                + f"width: {width}, height: {height}, normalized deviation: {deviation}, "
                + f"max allowed deviation: {self.MAX_ALLOWED_DEVIATION}."
            )

        return valid

    def get_width_height_from_url(self, url: str) -> Tuple[int, int]:
        tmp_icon_path = self.fetch_icon_to_tmp(url)

        try:
            width, height = self.get_width_height_from_image(tmp_icon_path)
            return width, height
        except UnidentifiedImageError:
            pass

        try:
            width, height = self.get_width_height_from_svg(tmp_icon_path)
            return width, height
        except ET.ParseError:
            pass

        raise GiantSwarmValidatorError(f"Icon file '{url}' is not a valid image or svg.")

    def fetch_icon_to_tmp(self, icon_path: str) -> str:
        try:
            return urllib.request.urlretrieve(icon_path)[0]  # nosec
        except urllib.error.URLError as exc:
            raise GiantSwarmValidatorError(f"Error fetching icon from '{icon_path}'. Error: {exc}.")

    def get_width_height_from_image(self, path: str) -> Tuple[int, int]:
        img = Image.open(path)
        return img.width, img.height

    def get_width_height_from_svg(self, path: str) -> Tuple[int, int]:
        tree = ET.parse(path)
        root = tree.getroot()
        width, height = root.attrib.get("width"), root.attrib.get("height")
        if width is not None and height is not None:
            return self.parse_svg_size(width), self.parse_svg_size(height)

        viewbox = root.attrib.get("viewBox")
        if viewbox is not None:
            width, height = viewbox.split(" ")[2:]
            return self.parse_svg_size(width), self.parse_svg_size(height)

        raise GiantSwarmValidatorError("Cannot parse aspect ratio from svg. Missing width & height or viewBox.")

    def parse_svg_size(self, size: str) -> int:
        if size.endswith("px"):
            size = size[:-2]
        return int(float(size))

    def get_deviation(self, width: int, height: int) -> float:
        return abs(width - height) / max(width, height)

    def is_almost_square(self, deviation: float) -> bool:
        return deviation < self.MAX_ALLOWED_DEVIATION


def get_chart_yaml(chart_yaml_path: str) -> dict:
    if not os.path.exists(chart_yaml_path):
        raise GiantSwarmValidatorError(f"Can't find file '{chart_yaml_path}'.")
    with open(chart_yaml_path, "r") as stream:
        try:
            chart_yaml = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise GiantSwarmValidatorError(f"Error parsing YAML file '{chart_yaml_path}'. Error: {exc}.")
    return chart_yaml
