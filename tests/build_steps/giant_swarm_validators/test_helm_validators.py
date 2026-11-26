import errno
import gzip
import http.client
import http.server
import io
import itertools
import os.path
import pathlib
import ssl
import tempfile
import threading
import urllib.error
from collections.abc import Iterator
from email.message import Message

import pytest
from PIL import Image
from configargparse import Namespace
from pytest_mock import MockerFixture
from step_exec_lib.errors import ValidationError

from app_build_suite.build_steps.giant_swarm_validators.helm import (
    HasValuesSchema,
    HasTeamLabel,
)
from app_build_suite.build_steps.giant_swarm_validators.icon import (
    IconDomainIsValid,
    IconExists,
    IconIsAlmostSquare,
)
from app_build_suite.build_steps.giant_swarm_validators import icon as icon_module
from app_build_suite.build_steps.giantswarm_helm_validator import GiantSwarmHelmValidator
from app_build_suite.build_steps.helm_consts import (
    VALUES_SCHEMA_JSON,
    CHART_YAML,
    TEMPLATES_DIR,
    HELPERS_YAML,
)
from tests.build_steps.helpers import init_config_for_step


@pytest.fixture
def config() -> Namespace:
    step = GiantSwarmHelmValidator()
    cfg = init_config_for_step(step)
    return cfg


def test_has_values_schema_validator(mocker: MockerFixture, config: Namespace) -> None:
    mock_exists = mocker.patch("os.path.exists")

    val = HasValuesSchema()

    assert val.validate(config)
    assert mock_exists.call_args.args[0] == os.path.join(config.chart_dir, VALUES_SCHEMA_JSON)


@pytest.mark.parametrize(
    "chart_yaml_input,templates_input,expected_result",
    [
        # case: both files valid, validation should pass
        (
            # Chart.yaml
            """
annotations:
  application.giantswarm.io/team: 'honeybadger'""",
            # _helpers.yaml
            """
   {{- define "hello-world-app.labels" -}}
   application.giantswarm.io/team: {{ index .Chart.Annotations "application.giantswarm.io/team" | quote }}
   {{- end }}""",
            True,
        ),
        # case: both files valid, helpers has default team, validation should pass
        (
            # Chart.yaml
            """
annotations:
  application.giantswarm.io/team: 'honeybadger'""",
            # _helpers.yaml
            """
   {{- define "hello-world-app.labels" -}}
   application.giantswarm.io/team: """
            + """{{ index .Chart.Annotations "application.giantswarm.io/team" | default "honeybadger" | quote }}
   {{- end }}""",
            True,
        ),
        # case: team annotation present, but has no value; should fail
        (
            # Chart.yaml
            """
annotations:
  application.giantswarm.io/team: """,
            # _helpers.yaml
            """application.giantswarm.io/team: {{ index .Chart.Annotations "application.giantswarm.io/team" | quote }}""",  # noqa: E501
            False,
        ),
        # case: team annotation has typo; should fail
        (
            # Chart.yaml
            """
annotations:
  application.giantwarm.io/team: 'broccoli'""",
            # _helpers.yaml
            """application.giantswarm.io/team: {{ index .Chart.Annotations "application.giantswarm.io/team" | quote }}""",  # noqa: E501
            False,
        ),
        # case: team annotation is OK, but not present in _helpers.py; should fail
        (
            # Chart.yaml
            """
annotations:
  application.giantswarm.io/team: 'broccoli'""",
            # _helpers.yaml
            """bogus line""",
            False,
        ),
        # case: OCI format annotation, validation should pass
        (
            # Chart.yaml
            """
annotations:
  io.giantswarm.application.team: 'honeybadger'""",
            # _helpers.yaml
            """
   {{- define "hello-world-app.labels" -}}
   application.giantswarm.io/team: {{ index .Chart.Annotations "io.giantswarm.application.team" | quote }}
   {{- end }}""",
            True,
        ),
        # case: OCI format annotation in helpers, validation should pass
        (
            # Chart.yaml
            """
annotations:
  io.giantswarm.application.team: 'honeybadger'""",
            # _helpers.yaml
            """
   {{- define "hello-world-app.labels" -}}
   io.giantswarm.application.team: {{ index .Chart.Annotations "io.giantswarm.application.team" | quote }}
   {{- end }}""",
            True,
        ),
    ],
    ids=[
        "both valid",
        "valid with default team",
        "team label value missing",
        "team label name typo",
        "not used in _templates.yaml",
        "OCI format annotation with new format in helpers",
        "OCI format annotation with OCI format in helpers",
    ],
)
def test_has_team_label_validator(
    chart_yaml_input: str,
    templates_input: str,
    expected_result: bool,
    mocker: MockerFixture,
    config: Namespace,
) -> None:
    mock_exists = mocker.patch("os.path.exists")
    mock_open_chart_yaml = mocker.mock_open(read_data=chart_yaml_input)
    mock_open_templates = mocker.mock_open(read_data=templates_input)
    mock_opens_chart_yaml = mocker.patch("app_build_suite.build_steps.giant_swarm_validators.mixins.open")
    mock_opens_template_yaml = mocker.patch("app_build_suite.build_steps.giant_swarm_validators.helm.open")

    mock_opens_chart_yaml.return_value = mock_open_chart_yaml()
    mock_opens_template_yaml.return_value = mock_open_templates()

    val = HasTeamLabel()
    assert val.validate(config) == expected_result
    assert mock_exists.call_args_list[0].args[0] == os.path.join(config.chart_dir, CHART_YAML)
    assert mock_opens_chart_yaml.call_args_list[0].args[0] == os.path.join(config.chart_dir, CHART_YAML)

    if mock_exists.call_count > 1:
        assert mock_exists.call_args_list[1].args[0] == os.path.join(config.chart_dir, TEMPLATES_DIR, HELPERS_YAML)
        assert mock_opens_template_yaml.call_args_list[0].args[0] == os.path.join(
            config.chart_dir, TEMPLATES_DIR, HELPERS_YAML
        )


ICON_URL = "https://s.giantswarm.io/x.svg"
ICON_MODULE = "app_build_suite.build_steps.giant_swarm_validators.icon"
# A valid gzip header followed by deflate data zlib rejects.
_SVGZ = gzip.compress(b"<svg/>" * 100)
CORRUPT_GZIP = _SVGZ[:10] + b"\xff" * 20 + _SVGZ[30:]
needs_cairo = pytest.mark.skipif(
    icon_module.svg2png is None, reason="checking an SVG icon's shape needs the cairo C library"
)


def mock_chart_yaml(mocker: MockerFixture, chart_yaml_input: str) -> None:
    mocker.patch("os.path.exists")
    mock_open_chart_yaml = mocker.mock_open(read_data=chart_yaml_input)
    mock_opens = mocker.patch("app_build_suite.build_steps.giant_swarm_validators.mixins.open")
    mock_opens.return_value = mock_open_chart_yaml.return_value


@pytest.fixture
def tmp_files(mocker: MockerFixture) -> list[str]:
    """Records every temp file the icon check creates, to assert they're all removed."""
    paths: list[str] = []
    real_mkstemp = tempfile.mkstemp

    def recording_mkstemp() -> tuple[int, str]:
        fd, path = real_mkstemp()
        paths.append(path)
        return fd, path

    mocker.patch(f"{ICON_MODULE}.tempfile.mkstemp", side_effect=recording_mkstemp)
    return paths


def assert_removed(paths: list[str]) -> None:
    # os.stat, not os.path.exists or Path.exists: mock_chart_yaml patches os.path.exists, and since
    # Python 3.14 Path.exists goes through it too.
    for path in paths:
        try:
            os.stat(path)
        except FileNotFoundError:
            continue
        pytest.fail(f"temp file {path} was left behind")


@pytest.mark.parametrize(
    "logo_filename,expected_result",
    [
        (
            "",
            True,
        ),
        pytest.param("./test_files/test_logo.svg", False, marks=needs_cairo),
        pytest.param("./test_files/test_icon.svg", True, marks=needs_cairo),
        (
            "./test_files/test_logo.png",
            False,
        ),
        (
            "./test_files/test_icon.png",
            True,
        ),
    ],
    ids=[
        "no icon",
        "svg icon is not a square",
        "svg icon is a square",
        "png icon is not a square",
        "png icon is a square",
    ],
)
def test_icon_is_almost_square_validator(
    logo_filename: str, expected_result: bool, mocker: MockerFixture, config: Namespace, tmp_files: list[str]
) -> None:
    mock_chart_yaml(mocker, f"icon: {ICON_URL}" if logo_filename else "no: icon")
    if logo_filename:
        logo_path = pathlib.Path(__file__).parent.absolute() / logo_filename
        mocker.patch(f"{ICON_MODULE}.urllib.request.urlopen", return_value=io.BytesIO(logo_path.read_bytes()))

    val = IconIsAlmostSquare()

    assert val.validate(config) == expected_result
    assert_removed(tmp_files)


@pytest.mark.parametrize(
    "logo_filename,expected_result",
    [("test_logo.svg", True), ("test_icon.svg", True), ("test_icon.svgz", True)],
    ids=["svg icon that isn't a square", "square svg icon", "compressed svg icon"],
)
def test_icon_is_almost_square_validator_svg_without_cairo_is_skipped(
    logo_filename: str,
    expected_result: bool,
    mocker: MockerFixture,
    config: Namespace,
    tmp_files: list[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_chart_yaml(mocker, f"icon: {ICON_URL}")
    test_files = pathlib.Path(__file__).parent.absolute() / "test_files"
    if logo_filename.endswith(".svgz"):
        body = gzip.compress((test_files / logo_filename.removesuffix("z")).read_bytes())
    else:
        body = (test_files / logo_filename).read_bytes()
    mocker.patch(f"{ICON_MODULE}.urllib.request.urlopen", return_value=io.BytesIO(body))
    # What icon.py is left with when importing cairosvg fails because cairo can't be loaded.
    mocker.patch(f"{ICON_MODULE}.svg2png", None)
    mocker.patch(f"{ICON_MODULE}._cairo_import_error", OSError('no library called "cairo-2" was found'))

    val = IconIsAlmostSquare()

    assert val.validate(config) is expected_result
    assert "needs the cairo library" in caplog.text
    assert_removed(tmp_files)


@pytest.mark.parametrize(
    "body",
    [
        b"<html>not an image</html>",
        b"\x00\x01garbage",
        b"<?xml version='1.0'?><svg",
        b"<?xml version='1.0' encoding='shift_jis'?><svg/>",
        b"<?xml version='1.0' encoding='x-bogus'?><svg/>",
        b"\x1f\x8bnot really gzip",
        CORRUPT_GZIP,
        gzip.compress(b"<!--" + b"a" * (6 * 1024 * 1024) + b"--><svg/>"),
    ],
    ids=[
        "html page",
        "binary garbage",
        "truncated svg",
        "encoding expat can't decode",
        "unknown encoding",
        "broken gzip",
        "corrupt gzip data",
        "svgz that decompresses past the size limit",
    ],
)
def test_icon_is_almost_square_validator_non_svg_without_cairo_fails(
    body: bytes, mocker: MockerFixture, config: Namespace, tmp_files: list[str]
) -> None:
    mock_chart_yaml(mocker, f"icon: {ICON_URL}")
    mocker.patch(f"{ICON_MODULE}.urllib.request.urlopen", return_value=io.BytesIO(body))
    mocker.patch(f"{ICON_MODULE}.svg2png", None)
    mocker.patch(f"{ICON_MODULE}._cairo_import_error", OSError('no library called "cairo-2" was found'))

    val = IconIsAlmostSquare()

    assert val.validate(config) is False
    assert_removed(tmp_files)


@pytest.mark.parametrize(
    "fetch_error,expected_result",
    [
        (urllib.error.HTTPError(ICON_URL, 404, "Not Found", Message(), None), True),
        (urllib.error.HTTPError(ICON_URL, 429, "Too Many Requests", Message(), None), True),
        (urllib.error.HTTPError(ICON_URL, 403, "Forbidden", Message(), None), False),
        (urllib.error.HTTPError(ICON_URL, 503, "Service Unavailable", Message(), None), True),
        (urllib.error.URLError("Name or service not known"), True),
        (TimeoutError("timed out"), True),
        (ConnectionResetError("Connection reset by peer"), True),
        (http.client.RemoteDisconnected("Remote end closed connection"), True),
        (ssl.SSLEOFError("EOF occurred in violation of protocol"), True),
        (http.client.InvalidURL("URL can't contain control characters"), False),
    ],
    ids=[
        "unpublished icon is skipped",
        "rate limited is an unreachable icon host",
        "other http error fails",
        "5xx is an unreachable icon host",
        "dns error is an unreachable icon host",
        "timeout is an unreachable icon host",
        "connection error is an unreachable icon host",
        "garbled response is an unreachable icon host",
        "tls error is an unreachable icon host",
        "url urllib can't use fails",
    ],
)
def test_icon_is_almost_square_validator_fetch_errors(
    fetch_error: Exception, expected_result: bool, mocker: MockerFixture, config: Namespace, tmp_files: list[str]
) -> None:
    mock_chart_yaml(mocker, f"icon: {ICON_URL}")
    mock_urlopen = mocker.patch(f"{ICON_MODULE}.urllib.request.urlopen", side_effect=fetch_error)

    val = IconIsAlmostSquare()

    assert val.validate(config) == expected_result
    mock_urlopen.assert_called_once_with(ICON_URL, timeout=10)
    assert_removed(tmp_files)


@pytest.mark.parametrize(
    "read_error",
    [
        OSError(errno.EHOSTUNREACH, "No route to host"),
        http.client.IncompleteRead(b"partial"),
        ssl.SSLEOFError("EOF occurred in violation of protocol"),
    ],
    ids=["route lost mid-download", "truncated response", "tls error mid-download"],
)
def test_icon_is_almost_square_validator_read_errors_are_unavailable(
    read_error: Exception, mocker: MockerFixture, config: Namespace, tmp_files: list[str]
) -> None:
    mock_chart_yaml(mocker, f"icon: {ICON_URL}")
    response = mocker.MagicMock()
    response.__enter__.return_value = response
    response.read1.side_effect = read_error
    mocker.patch(f"{ICON_MODULE}.urllib.request.urlopen", return_value=response)

    val = IconIsAlmostSquare()

    assert val.validate(config)
    assert_removed(tmp_files)


def test_icon_is_almost_square_validator_local_write_error_is_not_hidden(
    mocker: MockerFixture, config: Namespace, tmp_files: list[str]
) -> None:
    mock_chart_yaml(mocker, f"icon: {ICON_URL}")
    mocker.patch(f"{ICON_MODULE}.urllib.request.urlopen", return_value=io.BytesIO(b"<svg/>"))
    disk_full = OSError(errno.ENOSPC, "No space left on device")
    mock_tmp_file = mocker.mock_open()
    mock_tmp_file.return_value.write.side_effect = disk_full
    mocker.patch(f"{ICON_MODULE}.open", mock_tmp_file, create=True)

    val = IconIsAlmostSquare()

    with pytest.raises(OSError) as exc_info:
        val.validate(config)
    assert exc_info.value is disk_full
    assert_removed(tmp_files)


def test_icon_is_almost_square_validator_oversized_icon_fails(
    mocker: MockerFixture, config: Namespace, tmp_files: list[str]
) -> None:
    mock_chart_yaml(mocker, f"icon: {ICON_URL}")
    mocker.patch.object(IconIsAlmostSquare, "MAX_ICON_BYTES", 10)
    mocker.patch.object(IconIsAlmostSquare, "READ_CHUNK_BYTES", 4)
    mocker.patch(f"{ICON_MODULE}.urllib.request.urlopen", return_value=io.BytesIO(b"x" * 100))

    val = IconIsAlmostSquare()

    assert not val.validate(config)
    assert_removed(tmp_files)


def test_icon_is_almost_square_validator_slow_download_is_unavailable(
    mocker: MockerFixture, config: Namespace, tmp_files: list[str]
) -> None:
    mock_chart_yaml(mocker, f"icon: {ICON_URL}")
    mocker.patch.object(IconIsAlmostSquare, "READ_CHUNK_BYTES", 1)
    mocker.patch(f"{ICON_MODULE}.urllib.request.urlopen", return_value=io.BytesIO(b"<svg/>"))
    mocker.patch(f"{ICON_MODULE}.monotonic", side_effect=itertools.count(0, 20))

    val = IconIsAlmostSquare()

    assert val.validate(config)
    assert_removed(tmp_files)


@pytest.mark.parametrize(
    "icon_value",
    ["not a url", "''", "123", "true", "[a]", "file:///etc/passwd", "ftp://s.giantswarm.io/x.svg", "https://"],
    ids=["malformed url", "empty url", "number", "boolean", "list", "local file", "ftp", "no host"],
)
def test_icon_is_almost_square_validator_bad_url_fails_without_fetching(
    icon_value: str, mocker: MockerFixture, config: Namespace, tmp_files: list[str]
) -> None:
    mock_chart_yaml(mocker, f"icon: {icon_value}")
    mock_urlopen = mocker.patch(f"{ICON_MODULE}.urllib.request.urlopen")

    val = IconIsAlmostSquare()

    assert not val.validate(config)
    mock_urlopen.assert_not_called()
    assert tmp_files == []


@pytest.mark.parametrize(
    "require_published,expected_result",
    [(False, True), (True, False)],
    ids=["unpublished icon is skipped by default", "unpublished icon fails when required"],
)
def test_icon_is_almost_square_validator_require_published_icon(
    require_published: bool, expected_result: bool, mocker: MockerFixture, config: Namespace, tmp_files: list[str]
) -> None:
    mock_chart_yaml(mocker, f"icon: {ICON_URL}")
    mocker.patch(
        f"{ICON_MODULE}.urllib.request.urlopen",
        side_effect=urllib.error.HTTPError(ICON_URL, 404, "Not Found", Message(), None),
    )
    config.giantswarm_validator_require_published_icon = require_published

    val = IconIsAlmostSquare()

    assert val.validate(config) == expected_result
    assert_removed(tmp_files)


@pytest.fixture
def cut_short_icon_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """A real local HTTP server that announces 1000 bytes, sends 100 and closes the connection."""
    # urllib honours proxy settings from the environment, which must not catch the local server.
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")

    class CutShortHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", "1000")
            self.end_headers()
            self.wfile.write(b"<" * 100)
            self.wfile.flush()
            self.close_connection = True

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), CutShortHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/x.svg"
    finally:
        server.shutdown()
        server.server_close()


def test_icon_is_almost_square_validator_cut_short_response_is_unavailable(
    cut_short_icon_url: str, mocker: MockerFixture, config: Namespace, tmp_files: list[str]
) -> None:
    mock_chart_yaml(mocker, f"icon: {cut_short_icon_url}")
    mock_warning = mocker.patch(f"{ICON_MODULE}.logger.warning")

    val = IconIsAlmostSquare()

    assert val.validate(config)
    assert "cut short" in mock_warning.call_args.args[0]
    assert_removed(tmp_files)


@pytest.fixture
def chunked_icon_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """A real local HTTP server that sends a complete square SVG chunked, with a Content-Length it must ignore."""
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    body = (pathlib.Path(__file__).parent / "test_files" / "test_icon.svg").read_bytes()

    class ChunkedHandler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("Content-Length", str(len(body) * 10))
            self.send_header("Connection", "close")
            self.end_headers()
            for start in range(0, len(body), 100):
                part = body[start : start + 100]
                self.wfile.write(f"{len(part):x}\r\n".encode() + part + b"\r\n")
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
            self.close_connection = True

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), ChunkedHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/x.svg"
    finally:
        server.shutdown()
        server.server_close()


@needs_cairo
def test_icon_is_almost_square_validator_chunked_response_is_not_cut_short(
    chunked_icon_url: str, mocker: MockerFixture, config: Namespace, tmp_files: list[str]
) -> None:
    mock_chart_yaml(mocker, f"icon: {chunked_icon_url}")
    mock_warning = mocker.patch(f"{ICON_MODULE}.logger.warning")

    val = IconIsAlmostSquare()

    assert val.validate(config)
    mock_warning.assert_not_called()
    assert_removed(tmp_files)


def test_icon_is_almost_square_validator_decompression_bomb_fails(
    mocker: MockerFixture, config: Namespace, tmp_files: list[str]
) -> None:
    mock_chart_yaml(mocker, f"icon: {ICON_URL}")
    mocker.patch(f"{ICON_MODULE}.urllib.request.urlopen", return_value=io.BytesIO(b"png"))
    mocker.patch.object(IconIsAlmostSquare, "is_image", side_effect=Image.DecompressionBombError("too many pixels"))

    val = IconIsAlmostSquare()

    assert not val.validate(config)
    assert_removed(tmp_files)


def test_icon_is_almost_square_validator_unreadable_image_fails(
    mocker: MockerFixture, config: Namespace, tmp_files: list[str]
) -> None:
    mock_chart_yaml(mocker, f"icon: {ICON_URL}")
    mocker.patch(f"{ICON_MODULE}.urllib.request.urlopen", return_value=io.BytesIO(b"<html>not an image</html>"))

    val = IconIsAlmostSquare()

    assert not val.validate(config)
    assert_removed(tmp_files)


@pytest.mark.parametrize(
    "chart_yaml_input,expected_result",
    [
        (
            "empty: yaml",
            False,
        ),
        (
            """
icon: file://./test_files/test_logo.svg""",
            True,
        ),
    ],
    ids=[
        "no icon",
        "icon in yaml and exists",
    ],
)
def test_icon_exists(
    chart_yaml_input: str,
    expected_result: str,
    mocker: MockerFixture,
    config: Namespace,
) -> None:
    mocker.patch("os.path.exists")
    mock_open_chart_yaml = mocker.mock_open(read_data=chart_yaml_input)
    mock_opens = mocker.patch("app_build_suite.build_steps.giant_swarm_validators.mixins.open")
    mock_opens.return_value = mock_open_chart_yaml.return_value

    val = IconExists()

    assert val.validate(config) == expected_result


@pytest.mark.parametrize(
    "chart_yaml_input,expected_result",
    [
        (
            "no: icon",
            True,
        ),
        (
            """
icon: https://s.giantswarm.io/app-icons/1/png/hello-world-app-light.png""",
            True,
        ),
        (
            """
icon: https://raw.githubusercontent.com/giantswarm/hello-world-app/v0.0.1/app-icon.png""",
            False,
        ),
        (
            """
icon: https://example.com/icon.png""",
            False,
        ),
        (
            """
icon: http://s.giantswarm.io/app-icons/1/png/hello-world-app-light.png""",
            True,
        ),
        (
            """
icon: not a url""",
            False,
        ),
        (
            """
icon: 123""",
            False,
        ),
        (
            """
icon: [a]""",
            False,
        ),
    ],
    ids=[
        "no icon - skip validation",
        "valid s.giantswarm.io domain",
        "invalid github domain",
        "invalid arbitrary domain",
        "plain http on the allowed domain passes",
        "malformed url is rejected",
        "number is rejected",
        "list is rejected",
    ],
)
def test_icon_domain_is_valid(
    chart_yaml_input: str,
    expected_result: bool,
    mocker: MockerFixture,
    config: Namespace,
) -> None:
    mocker.patch("os.path.exists")
    mock_open_chart_yaml = mocker.mock_open(read_data=chart_yaml_input)
    mock_opens = mocker.patch("app_build_suite.build_steps.giant_swarm_validators.mixins.open")
    mock_opens.return_value = mock_open_chart_yaml.return_value

    val = IconDomainIsValid()

    assert val.validate(config) == expected_result


@pytest.mark.parametrize(
    "ignored_checks,expect_failure",
    [("", True), ("C9999", False)],
    ids=["crashing check fails the build", "crashing check on the ignore list only warns"],
)
def test_crashing_validator_counts_as_failed_check(
    ignored_checks: str, expect_failure: bool, mocker: MockerFixture, config: Namespace
) -> None:
    crashing = mocker.MagicMock()
    crashing.get_check_code.return_value = "C9999"
    crashing.validate.side_effect = AttributeError("boom")
    step = GiantSwarmHelmValidator()
    mocker.patch.object(step, "_load_giant_swarm_validators", return_value=[crashing])
    config.disable_giantswarm_helm_validator = False
    config.disable_strict_giantswarm_validator = False
    config.giantswarm_validator_ignored_checks = ignored_checks

    if expect_failure:
        with pytest.raises(ValidationError, match="C9999"):
            step.pre_run(config)
    else:
        step.pre_run(config)
