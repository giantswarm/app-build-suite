import pytest
from configargparse import Namespace
from pytest_mock import MockerFixture

from app_build_suite.build_steps.giant_swarm_validators.home_url import HomeUrlMatchesGitRemote
from app_build_suite.build_steps.helm import GiantSwarmHelmValidator
from tests.build_steps.helpers import init_config_for_step


@pytest.fixture
def config() -> Namespace:
    step = GiantSwarmHelmValidator()
    cfg = init_config_for_step(step)
    return cfg


@pytest.mark.parametrize(
    "chart_yaml_input,remote_url,is_git_repo,expected_result",
    [
        # Valid: home matches git remote (HTTPS)
        (
            "home: https://github.com/org/repo",
            "https://github.com/org/repo.git",
            True,
            True,
        ),
        # Valid: home matches git remote (SSH converted)
        (
            "home: https://github.com/org/repo",
            "git@github.com:org/repo.git",
            True,
            True,
        ),
        # Valid: home matches with trailing slash
        (
            "home: https://github.com/org/repo/",
            "https://github.com/org/repo",
            True,
            True,
        ),
        # Invalid: home doesn't match
        (
            "home: https://github.com/wrong/repo",
            "git@github.com:org/repo.git",
            True,
            False,
        ),
        # Valid: no home field (skip validation)
        (
            "name: test-chart",
            "git@github.com:org/repo.git",
            True,
            True,
        ),
        # Valid: not a git repo (skip validation)
        (
            "home: https://github.com/org/repo",
            None,
            False,
            True,
        ),
        # Valid: non-GitHub remote (skip validation)
        (
            "home: https://gitlab.com/org/repo",
            "git@gitlab.com:org/repo.git",
            True,
            True,
        ),
    ],
    ids=[
        "home matches https remote",
        "home matches ssh remote",
        "trailing slash ok",
        "home mismatch",
        "no home field",
        "not git repo",
        "non-github remote",
    ],
)
def test_home_url_matches_git_remote_validator(
    chart_yaml_input: str,
    remote_url: str,
    is_git_repo: bool,
    expected_result: bool,
    mocker: MockerFixture,
    config: Namespace,
) -> None:
    # Mock os.path.exists
    mocker.patch("os.path.exists", return_value=True)

    # Mock Chart.yaml reading
    mock_open_chart = mocker.mock_open(read_data=chart_yaml_input)
    mocker.patch(
        "app_build_suite.build_steps.giant_swarm_validators.mixins.open",
        return_value=mock_open_chart(),
    )

    # Mock GitRepoVersionInfo
    mock_git_repo_info = mocker.MagicMock()
    mock_git_repo_info.is_git_repo = is_git_repo
    mock_git_repo_info.get_remote_url.return_value = remote_url

    mocker.patch(
        "app_build_suite.build_steps.giant_swarm_validators.home_url.GitRepoVersionInfo",
        return_value=mock_git_repo_info,
    )

    val = HomeUrlMatchesGitRemote()
    assert val.validate(config) == expected_result


def test_home_url_validator_check_code() -> None:
    """Verify the validator returns the correct check code."""
    val = HomeUrlMatchesGitRemote()
    assert val.get_check_code() == "C0004"


def test_home_url_validator_with_no_origin_remote(
    mocker: MockerFixture,
    config: Namespace,
) -> None:
    """Validation should pass when there's no origin remote."""
    mocker.patch("os.path.exists", return_value=True)

    mock_open_chart = mocker.mock_open(read_data="home: https://github.com/org/repo")
    mocker.patch(
        "app_build_suite.build_steps.giant_swarm_validators.mixins.open",
        return_value=mock_open_chart(),
    )

    mock_git_repo_info = mocker.MagicMock()
    mock_git_repo_info.is_git_repo = True
    mock_git_repo_info.get_remote_url.return_value = None  # No origin remote

    mocker.patch(
        "app_build_suite.build_steps.giant_swarm_validators.home_url.GitRepoVersionInfo",
        return_value=mock_git_repo_info,
    )

    val = HomeUrlMatchesGitRemote()
    assert val.validate(config) is True


def test_home_url_validator_with_non_string_home(
    mocker: MockerFixture,
    config: Namespace,
) -> None:
    """Validation should fail when home field is not a string."""
    mocker.patch("os.path.exists", return_value=True)

    # home is a number, not a string
    mock_open_chart = mocker.mock_open(read_data="home: 12345")
    mocker.patch(
        "app_build_suite.build_steps.giant_swarm_validators.mixins.open",
        return_value=mock_open_chart(),
    )

    val = HomeUrlMatchesGitRemote()
    assert val.validate(config) is False
