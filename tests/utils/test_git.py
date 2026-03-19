import os
import re
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

import git
from pytest_mock import MockFixture
import pytest

from app_build_suite.utils.git import GitRepoVersionInfo


def _make_repo_mock(mocker: MockFixture, tags: list, head_sha: str, branch: str = "main") -> None:
    """Helper: patch git.Repo with a mock that simulates the given tags and branch."""
    mocker.patch("git.Repo")
    repo_mock = mocker.MagicMock()

    # HEAD commit
    head_commit = mocker.MagicMock()
    head_commit.hexsha = head_sha
    repo_mock.head.commit = head_commit

    # Tags
    tag_objects = []
    for t in tags:
        tag_obj = mocker.MagicMock()
        tag_obj.name = t["name"]
        tag_commit = mocker.MagicMock()
        tag_commit.hexsha = t["sha"]
        tag_obj.commit = tag_commit
        tag_objects.append(tag_obj)
    repo_mock.tags = tag_objects

    # Active branch
    if branch == "detached":
        repo_mock.active_branch.__get__ = mocker.Mock(side_effect=TypeError)
        type(repo_mock).active_branch = property(lambda self: (_ for _ in ()).throw(TypeError()))
    else:
        active_branch_mock = mocker.MagicMock()
        active_branch_mock.name = branch
        repo_mock.active_branch = active_branch_mock

    git.Repo.return_value = repo_mock


@pytest.mark.parametrize(
    "tags, head_sha, branch, expected_version_string",
    [
        # HEAD directly on a stable tag → return tag
        ([{"name": "v0.0.1", "sha": "123"}], "123", "main", "0.0.1"),
        ([{"name": "0.0.1", "sha": "123"}], "123", "main", "0.0.1"),
        ([{"name": "v0.1.1-gs1", "sha": "abc"}], "abc", "main", "0.1.1-gs1"),
        # HEAD directly on an RC tag → return tag
        ([{"name": "1.2.3-rc.1", "sha": "abc"}], "abc", "feature", "1.2.3-rc.1"),
        # HEAD not on a tag → dev format
        # No tags at all: base becomes 0.0.1
        ([], "123", "main", "0.0.1-dev.main."),
        ([], "123", "feature-branch", "0.0.1-dev.feature-branch."),
        # Has a stable tag but HEAD is not on it: base = last stable + bump patch
        ([{"name": "1.2.3", "sha": "old"}], "new", "main", "1.2.4-dev.main."),
        ([{"name": "1.2.3", "sha": "old"}], "new", "my-feature", "1.2.4-dev.my-feature."),
        # Branch name sanitization: slashes → hyphens
        ([{"name": "1.0.0", "sha": "old"}], "new", "feature/my-thing", "1.0.1-dev.feature-my-thing."),
        # Branch name sanitization: underscores → hyphens
        ([{"name": "1.0.0", "sha": "old"}], "new", "feature_underscored", "1.0.1-dev.feature-underscored."),
    ],
)
def test_git_version(
    tags: list,
    head_sha: str,
    branch: str,
    expected_version_string: str,
    mocker: MockFixture,
) -> None:
    _make_repo_mock(mocker, tags, head_sha, branch)
    git_info = GitRepoVersionInfo("bogus/path")
    assert git_info.is_git_repo

    fixed_dt = datetime(2026, 1, 27, 9, 49, 59, tzinfo=timezone.utc)
    with patch("app_build_suite.utils.git.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_dt
        ver = git_info.get_git_version()

    assert ver.startswith(expected_version_string), f"Got: {ver!r}, expected prefix: {expected_version_string!r}"
    if "-dev." in expected_version_string or ver.count("-dev.") > 0:
        # Verify date/time suffix format
        assert re.search(r"-dev\.[^.]+\.\d{8}\.\d{6}$", ver), f"Dev format mismatch: {ver!r}"


def test_git_version_with_gs_git_tag_prefix(mocker: MockFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """GS_GIT_TAG_PREFIX filters which tags are considered stable."""
    monkeypatch.setenv("GS_GIT_TAG_PREFIX", "gs-")
    tags = [
        {"name": "1.9.0", "sha": "aaa"},  # no prefix → ignored
        {"name": "gs-1.8.0", "sha": "bbb"},  # matches prefix → stable base
    ]
    _make_repo_mock(mocker, tags, head_sha="new", branch="main")
    git_info = GitRepoVersionInfo("bogus/path")

    fixed_dt = datetime(2026, 1, 27, 9, 49, 59, tzinfo=timezone.utc)
    with patch("app_build_suite.utils.git.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_dt
        ver = git_info.get_git_version()

    assert ver.startswith("1.8.1-dev.main."), f"Got: {ver!r}"


@pytest.mark.parametrize(
    "branch, expected",
    [
        ("main", "main"),
        ("feature/my-thing", "feature-my-thing"),
        ("feature_underscored", "feature-underscored"),
        ("my--branch", "my-branch"),
        ("/leading-slash", "leading-slash"),
        ("trailing-slash/", "trailing-slash"),
        ("double//slash", "double-slash"),
        ("new-versioning", "new-versioning"),
    ],
)
def test_sanitize_branch_name(branch: str, expected: str) -> None:
    assert GitRepoVersionInfo._sanitize_branch_name(branch) == expected


def test_gets_latest_tag_available_on_the_current_branch(mocker: MockFixture) -> None:
    with tempfile.TemporaryDirectory() as repo_dir:
        file_name = os.path.join(repo_dir, "new-file")
        repo = git.Repo.init(repo_dir)
        repo.git.config("user.email", "test@none.com")
        repo.git.config("user.name", "test")
        open(file_name, "wb").close()
        repo.index.add([file_name])
        repo.index.commit("initial commit")
        first_commit = repo.head.commit
        # Commit and stable tag on main
        with open(file_name, "a") as f:
            f.write("branch main")
        repo.index.add([file_name])
        repo.index.commit("on main")
        repo.create_tag("0.1.0", ref=repo.head.reference, message="tag on main")
        # Create feature branch with a commit tagged 0.0.1
        lower_tag = "0.0.1"
        new_branch = repo.create_head("feature", commit=first_commit.hexsha)
        repo.head.reference = new_branch
        with open(file_name, "a") as f:
            f.write("topic branch")
        repo.index.add([file_name])
        repo.index.commit("on topic")
        repo.create_tag(lower_tag, ref=repo.head.reference, message="tag on feature")

        # HEAD is directly on tag 0.0.1 → returns tag without dev suffix
        git_info = GitRepoVersionInfo(repo_dir)
        assert git_info.is_git_repo
        ver = git_info.get_git_version()
        assert ver == lower_tag


def test_gets_dev_version_when_no_tag(mocker: MockFixture) -> None:
    with tempfile.TemporaryDirectory() as repo_dir:
        file_name = os.path.join(repo_dir, "new-file")
        repo = git.Repo.init(repo_dir)
        repo.git.config("user.email", "test@none.com")
        repo.git.config("user.name", "test")
        open(file_name, "wb").close()
        repo.index.add([file_name])
        repo.index.commit("initial commit")

        git_info = GitRepoVersionInfo(repo_dir)
        assert git_info.is_git_repo
        ver = git_info.get_git_version()
        # No tags → base 0.0.1 → dev format
        assert re.match(r"^0\.0\.1-dev\.[^.]+\.\d{8}\.\d{6}$", ver), f"Unexpected version: {ver!r}"


def test_get_remote_url(mocker: MockFixture) -> None:
    """Test that get_remote_url returns the URL of the specified remote."""
    path = "bogus/path"
    mocker.patch("git.Repo")
    repo_mock = mocker.MagicMock()
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
