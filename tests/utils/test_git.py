import git
from pytest_mock import MockFixture

from app_build_suite.utils.git import GitRepoVersionInfo


def test_get_remote_url(mocker: MockFixture) -> None:
    """Test that get_remote_url returns the URL of the specified remote."""
    path = "bogus/path"
    mocker.patch("git.Repo")
    repo_mock = mocker.MagicMock()

    # Mock remote
    origin_remote = mocker.MagicMock()
    origin_remote.url = "git@github.com:org/repo.git"
    repo_mock.remote.return_value = origin_remote

    git.Repo.return_value = repo_mock

    git_info = GitRepoVersionInfo(path)
    assert git_info.get_remote_url("origin") == "git@github.com:org/repo.git"
    repo_mock.remote.assert_called_with("origin")


def test_get_remote_url_missing_remote(mocker: MockFixture) -> None:
    """Test that get_remote_url returns None when remote doesn't exist."""
    path = "bogus/path"
    mocker.patch("git.Repo")
    repo_mock = mocker.MagicMock()

    # Simulate remote not found
    repo_mock.remote.side_effect = ValueError("Remote not found")

    git.Repo.return_value = repo_mock

    git_info = GitRepoVersionInfo(path)
    assert git_info.get_remote_url("upstream") is None


def test_get_remote_url_not_a_repo(mocker: MockFixture) -> None:
    """Test that get_remote_url returns None when not a git repo."""
    path = "bogus/path"
    mocker.patch("git.Repo", side_effect=git.exc.InvalidGitRepositoryError())

    git_info = GitRepoVersionInfo(path)
    assert git_info.is_git_repo is False
    assert git_info.get_remote_url("origin") is None
