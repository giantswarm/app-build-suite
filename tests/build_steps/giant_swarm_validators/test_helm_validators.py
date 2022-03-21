import os.path

import configargparse
from pytest_mock import MockerFixture

from app_build_suite.build_steps.giant_swarm_validators.helm import HasValuesSchema
from app_build_suite.build_steps.helm import GiantSwarmHelmValidator
from app_build_suite.build_steps.helm_consts import VALUES_SCHEMA_JSON
from tests.build_steps.helpers import init_config_for_step


def get_validator_config() -> configargparse.Namespace:
    step = GiantSwarmHelmValidator()
    cfg = init_config_for_step(step)
    return cfg


def test_has_values_schema_validator(mocker: MockerFixture) -> None:
    mock_exists = mocker.patch("os.path.exists")

    cfg = get_validator_config()
    val = HasValuesSchema()

    assert val.validate(cfg)
    assert mock_exists.call_args.args[0] == os.path.join(cfg.chart_dir, VALUES_SCHEMA_JSON)
