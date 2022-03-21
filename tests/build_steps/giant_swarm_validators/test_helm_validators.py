import os.path

import pytest
from configargparse import Namespace
from pytest_mock import MockerFixture

from app_build_suite.build_steps.giant_swarm_validators.helm import HasValuesSchema, HasTeamLabel
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
    ],
    ids=["both valid", "team label value missing", "team label name typo", "not used in _templates.yaml"],
)
def test_has_team_label_validator(
    chart_yaml_input: str, templates_input: str, expected_result: bool, mocker: MockerFixture, config: Namespace
) -> None:
    mock_exists = mocker.patch("os.path.exists")
    mock_open_chart_yaml = mocker.mock_open(read_data=chart_yaml_input)
    mock_open_templates = mocker.mock_open(read_data=templates_input)
    mock_opens = mocker.patch("app_build_suite.build_steps.giant_swarm_validators.helm.open")
    mock_opens.side_effect = (mock_open_chart_yaml.return_value, mock_open_templates.return_value)

    val = HasTeamLabel()
    assert val.validate(config) == expected_result
    assert mock_exists.call_args_list[0].args[0] == os.path.join(config.chart_dir, CHART_YAML)
    assert mock_opens.call_args_list[0].args[0] == os.path.join(config.chart_dir, CHART_YAML)
    if mock_exists.call_count > 1:
        assert mock_exists.call_args_list[1].args[0] == os.path.join(config.chart_dir, TEMPLATES_DIR, HELPERS_YAML)
        assert mock_opens.call_args_list[1].args[0] == os.path.join(config.chart_dir, TEMPLATES_DIR, HELPERS_YAML)
