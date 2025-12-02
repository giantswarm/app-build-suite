import os.path
import pathlib

import pytest
from configargparse import Namespace
from pytest_mock import MockerFixture

from app_build_suite.build_steps.giant_swarm_validators.helm import HasValuesSchema, HasTeamLabel
from app_build_suite.build_steps.giant_swarm_validators.icon import IconExists, IconIsAlmostSquare
from app_build_suite.build_steps.helm import GiantSwarmHelmValidator
from app_build_suite.build_steps.helm_consts import VALUES_SCHEMA_JSON, CHART_YAML, TEMPLATES_DIR, HELPERS_YAML
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
    chart_yaml_input: str, templates_input: str, expected_result: bool, mocker: MockerFixture, config: Namespace
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


@pytest.mark.parametrize(
    "logo_filename,expected_result",
    [
        (
            "",
            True,
        ),
        (
            "./test_files/test_logo.svg",
            False,
        ),
        (
            "./test_files/test_icon.svg",
            True,
        ),
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
    logo_filename: str, expected_result: bool, mocker: MockerFixture, config: Namespace
) -> None:
    current_folder = pathlib.Path(__file__).parent.absolute()
    logo_path = os.path.join(current_folder, logo_filename)

    chart_yaml_input = (
        f"""
icon: file://{logo_path}"""
        if logo_filename
        else "no: icon"
    )

    mocker.patch("os.path.exists")
    mock_open_chart_yaml = mocker.mock_open(read_data=chart_yaml_input)
    mock_opens = mocker.patch("app_build_suite.build_steps.giant_swarm_validators.mixins.open")
    mock_opens.return_value = mock_open_chart_yaml.return_value

    val = IconIsAlmostSquare()

    assert val.validate(config) == expected_result


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
