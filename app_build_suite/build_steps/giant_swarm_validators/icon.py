import argparse
import os
import urllib.request
import urllib.error
import tempfile
import logging
from typing import Final, Tuple

from PIL import Image
from cairosvg import svg2png
from app_build_suite.build_steps.giant_swarm_validators.errors import (
    GiantSwarmValidatorError,
)
from app_build_suite.build_steps.giant_swarm_validators.mixins import UseChartYaml

from app_build_suite.build_steps.helm_consts import (
    CHART_YAML,
)

logger = logging.getLogger(__name__)


class IconExists(UseChartYaml):
    def get_check_code(self) -> str:
        return "C0002"

    def validate(self, config: argparse.Namespace) -> bool:
        chart_yaml = self.get_chart_yaml(config)

        if "icon" not in chart_yaml:
            logger.info(f"'icon' not found in '{CHART_YAML}'.")
            return False

        if not chart_yaml["icon"]:
            logger.info(f"'icon' is present in '{CHART_YAML}', but it's empty.")
            return False

        return True


class IconIsAlmostSquare(UseChartYaml):
    MAX_ALLOWED_DEVIATION: Final[float] = 0.33

    def get_check_code(self) -> str:
        return "C0003"

    def validate(self, config: argparse.Namespace) -> bool:
        chart_yaml = self.get_chart_yaml(config)

        icon_path = chart_yaml.get("icon")
        if icon_path is None:
            logger.info(f"Icon not found in '{CHART_YAML}'. Skipping icon validation.")
            return True

        img_path = self.fetch_icon_to_tmp(icon_path)

        if not self.is_image(img_path):
            try:
                png_path = self.convert_svg_to_png(img_path)
                os.remove(img_path)
                img_path = png_path
            except Exception:
                logger.warning("Icon is not a valid image or SVG.")
                return False

        try:
            width, height = self.get_width_height_from_image(img_path)
        except GiantSwarmValidatorError as e:
            logger.warn(f"Icon validation failed: {e.msg}")
            return False
        finally:
            os.remove(img_path)

        deviation = self.get_deviation(width, height)
        valid = self.is_almost_square(deviation)
        if not valid:
            logger.info(
                "The icon should be close to a square shape, but it is not.\n "
                + f"width: {width}, height: {height}, normalized deviation: {deviation}, "
                + f"max allowed deviation: {self.MAX_ALLOWED_DEVIATION}."
            )

        return valid

    def is_image(self, path: str) -> bool:
        try:
            with Image.open(path) as img:
                img.verify()
                return True
        except (IOError, SyntaxError):
            return False

    def convert_svg_to_png(self, svg_path: str) -> str:
        _, tmp_file_path = tempfile.mkstemp()
        svg2png(url=svg_path, write_to=tmp_file_path)
        return tmp_file_path

    def fetch_icon_to_tmp(self, icon_path: str) -> str:
        _, tmp_file_path = tempfile.mkstemp()
        try:
            return urllib.request.urlretrieve(icon_path, tmp_file_path)[0]  # nosec
        except urllib.error.URLError as exc:
            raise GiantSwarmValidatorError(
                f"Error fetching icon from '{icon_path}'. Error: {exc}."
            )

    def get_width_height_from_image(self, path: str) -> Tuple[int, int]:
        img = Image.open(path)
        return img.width, img.height

    def parse_svg_size(self, size: str) -> int:
        if size.endswith("px"):
            size = size[:-2]
        return int(float(size))

    def get_deviation(self, width: int, height: int) -> float:
        return abs(width - height) / max(width, height)

    def is_almost_square(self, deviation: float) -> bool:
        return deviation < self.MAX_ALLOWED_DEVIATION
