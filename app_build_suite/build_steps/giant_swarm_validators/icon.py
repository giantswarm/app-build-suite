import argparse
import contextlib
import http.client
import os
import urllib.request
import urllib.error
import tempfile
import logging
from time import monotonic
from typing import Final, List, Optional, Tuple
from urllib.parse import urlparse

from PIL import Image
from cairosvg import svg2png
from app_build_suite.build_steps.giant_swarm_validators.errors import (
    GiantSwarmValidatorError,
    IconNotPublishedError,
    IconUnavailableError,
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


ICON_URL_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})


def parse_icon_url(icon: object) -> Tuple[Optional[str], Optional[str]]:
    """Returns the icon URL's hostname and None, or None and why the icon value isn't a usable web URL."""
    if not isinstance(icon, str):
        return None, f"Icon in '{CHART_YAML}' must be a URL string, but it is {icon!r}."
    try:
        parsed = urlparse(icon)
        hostname = parsed.hostname
    except ValueError as e:
        return None, f"Icon URL '{icon}' is malformed: {e}."
    if parsed.scheme not in ICON_URL_SCHEMES:
        return None, f"Icon URL '{icon}' must use http or https."
    if not hostname:
        return None, f"Icon URL '{icon}' has no host."
    return hostname, None


class IconDomainIsValid(UseChartYaml):
    ALLOWED_DOMAIN: Final[str] = "s.giantswarm.io"

    def get_check_code(self) -> str:
        return "C0004"

    def validate(self, config: argparse.Namespace) -> bool:
        chart_yaml = self.get_chart_yaml(config)

        icon_url = chart_yaml.get("icon")
        if icon_url is None:
            logger.info(f"Icon not found in '{CHART_YAML}'. Skipping icon domain validation.")
            return True

        hostname, problem = parse_icon_url(icon_url)
        if problem:
            logger.info(problem)
            return False

        if hostname != self.ALLOWED_DOMAIN:
            logger.info(f"Icon URL '{icon_url}' uses domain '{hostname}', but only '{self.ALLOWED_DOMAIN}' is allowed.")
            return False

        return True


class IconIsAlmostSquare(UseChartYaml):
    MAX_ALLOWED_DEVIATION: Final[float] = 0.33
    # Timeout for each network operation, and for reading the whole response body.
    FETCH_TIMEOUT_SECONDS: Final[int] = 10
    FETCH_DEADLINE_SECONDS: Final[int] = 30
    MAX_ICON_BYTES: Final[int] = 5 * 1024 * 1024
    READ_CHUNK_BYTES: Final[int] = 64 * 1024
    # Request timeout and rate limiting; any 5xx is unavailable too. 404 is handled on its own.
    UNAVAILABLE_HTTP_CODES: Final[frozenset[int]] = frozenset({408, 429})

    def get_check_code(self) -> str:
        return "C0003"

    def validate(self, config: argparse.Namespace) -> bool:
        chart_yaml = self.get_chart_yaml(config)

        icon_url = chart_yaml.get("icon")
        if icon_url is None:
            logger.info(f"Icon not found in '{CHART_YAML}'. Skipping icon validation.")
            return True

        # Only fetch well-formed web URLs, never local files or other schemes.
        _, problem = parse_icon_url(icon_url)
        if problem:
            logger.info(problem)
            return False

        # An outage of the icon host or an icon that isn't published yet must not block chart builds.
        try:
            img_path = self.fetch_icon_to_tmp(icon_url)
        except IconNotPublishedError as e:
            if getattr(config, "giantswarm_validator_require_published_icon", False):
                logger.warning(f"Icon validation failed, the icon isn't published: {e.msg}")
                return False
            logger.warning(f"Skipping icon shape validation, the icon isn't published yet: {e.msg}")
            return True
        except IconUnavailableError as e:
            logger.warning(f"Skipping icon shape validation, the icon can't be fetched: {e.msg}")
            return True
        except GiantSwarmValidatorError as e:
            logger.warning(f"Icon validation failed: {e.msg}")
            return False

        tmp_paths: List[str] = [img_path]
        try:
            try:
                is_image = self.is_image(img_path)
            except Image.DecompressionBombError as e:
                logger.warning(f"Icon validation failed, the image can't be read: {e}")
                return False
            if not is_image:
                try:
                    img_path = self.convert_svg_to_png(img_path)
                except Exception:
                    logger.warning("Icon is not a valid image or SVG.")
                    return False
                tmp_paths.append(img_path)

            try:
                width, height = self.get_width_height_from_image(img_path)
            except (OSError, Image.DecompressionBombError) as e:
                logger.warning(f"Icon validation failed, the image can't be read: {e}")
                return False
        finally:
            for path in tmp_paths:
                with contextlib.suppress(FileNotFoundError):
                    os.remove(path)

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
        fd, tmp_file_path = tempfile.mkstemp()
        os.close(fd)
        try:
            svg2png(url=svg_path, write_to=tmp_file_path)
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.remove(tmp_file_path)
            raise
        return tmp_file_path

    def fetch_icon_to_tmp(self, icon_url: str) -> str:
        fd, tmp_file_path = tempfile.mkstemp()
        os.close(fd)
        try:
            self._download(icon_url, tmp_file_path)
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.remove(tmp_file_path)
            raise
        return tmp_file_path

    def _download(self, icon_url: str, tmp_file_path: str) -> None:
        # Errors from the network side are told apart from local ones by where they're raised: urlopen and
        # response.read1 talk only to the icon host, while opening and writing the temp file is local. Local
        # errors, like a full temp dir, are not caught here, so they fail the check instead of being skipped.
        with open(tmp_file_path, "wb") as tmp_file:
            try:
                response = urllib.request.urlopen(icon_url, timeout=self.FETCH_TIMEOUT_SECONDS)  # nosec
            except urllib.error.HTTPError as exc:
                exc.close()
                if exc.code == 404:
                    raise IconNotPublishedError(f"Error fetching icon from '{icon_url}'. Error: {exc}.")
                if exc.code in self.UNAVAILABLE_HTTP_CODES or exc.code >= 500:
                    raise IconUnavailableError(f"Error fetching icon from '{icon_url}'. Error: {exc}.")
                raise GiantSwarmValidatorError(f"Error fetching icon from '{icon_url}'. Error: {exc}.")
            except (ValueError, http.client.InvalidURL) as exc:
                # A URL that urllib can't use, like one with a space, is the chart's fault.
                raise GiantSwarmValidatorError(f"Error fetching icon from '{icon_url}'. Error: {exc}.")
            except (OSError, http.client.HTTPException) as exc:
                # DNS, connection, TLS and timeout errors, or a garbled response: the host is at fault.
                raise IconUnavailableError(f"Error fetching icon from '{icon_url}'. Error: {exc}.")

            with response:
                deadline = monotonic() + self.FETCH_DEADLINE_SECONDS
                expected_size = self._content_length(response)
                size = 0
                while True:
                    try:
                        # read1 returns as soon as any data arrives, so a host that sends a trickle of bytes
                        # still hits the deadline below; read(n) would wait for all n bytes.
                        chunk = response.read1(self.READ_CHUNK_BYTES)
                    except (OSError, http.client.HTTPException) as exc:
                        raise IconUnavailableError(f"Error fetching icon from '{icon_url}'. Error: {exc}.")
                    if not chunk:
                        # http.client doesn't raise when the connection closes early, so check the length.
                        if expected_size is not None and size < expected_size:
                            raise IconUnavailableError(
                                f"Error fetching icon from '{icon_url}'. Error: got {size} of "
                                f"{expected_size} bytes, the response was cut short."
                            )
                        return
                    size += len(chunk)
                    if size > self.MAX_ICON_BYTES:
                        raise GiantSwarmValidatorError(
                            f"Icon at '{icon_url}' is larger than {self.MAX_ICON_BYTES} bytes."
                        )
                    if monotonic() > deadline:
                        raise IconUnavailableError(
                            f"Fetching icon from '{icon_url}' took longer than {self.FETCH_DEADLINE_SECONDS}s."
                        )
                    tmp_file.write(chunk)

    @staticmethod
    def _content_length(response: object) -> Optional[int]:
        # http.client sets length from Content-Length before the body is read, and leaves it None for a
        # chunked response, where Content-Length must be ignored.
        length = getattr(response, "length", None)
        return length if isinstance(length, int) else None

    def get_width_height_from_image(self, path: str) -> Tuple[int, int]:
        with Image.open(path) as img:
            return img.width, img.height

    def parse_svg_size(self, size: str) -> int:
        if size.endswith("px"):
            size = size[:-2]
        return int(float(size))

    def get_deviation(self, width: int, height: int) -> float:
        return abs(width - height) / max(width, height)

    def is_almost_square(self, deviation: float) -> bool:
        return deviation < self.MAX_ALLOWED_DEVIATION
