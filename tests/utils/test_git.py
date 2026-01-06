import os
import tempfile
from typing import Dict, List

import git
from pytest_mock import MockFixture
import pytest

from app_build_suite.utils.git import GitRepoVersionInfo


@pytest.mark.parametrize(
    "tags, last_commit_hash, expected_version_string",
    [
        ([], "123", "0.0.0-123"),
        ([{"name": "v0.0.1", "sha": "123"}], "123", "0.0.1"),
        ([{"name": "0.0.1", "sha": "012"}], "123", "0.0.1-123"),
        ([{"name": "v0.0.1", "sha": "012"}], "123", "0.0.1-123"),
        ([{"name": "v-0.0.1", "sha": "012"}], "123", "0.0.1-123"),
        ([{"name": "v_0.0.1", "sha": "012"}], "123", "0.0.1-123"),
        ([{"name": "v.0.0.1", "sha": "012"}], "123", "0.0.1-123"),
        ([{"name": "v0.0.1", "sha": "abc"}], "def", "0.0.1-def"),
        ([{"name": "v0.1.1-gs1", "sha": "abc"}], "abc", "0.1.1-gs1"),
        ([{"name": "v0.1.1-gs1", "sha": "abc"}], "def", "0.1.1-gs1-def"),
    ],
)
def test_git_version(
    tags: List[Dict[str, str]],
    last_commit_hash: str,
    expected_version_string: str,
    mocker: MockFixture,
) -> None:
    path = "bogus/path"
    mocker.patch("git.Repo")
    repo_mock = mocker.MagicMock()
    git_obj = mocker.MagicMock()
    git_obj.describe = mocker.Mock(
        return_value=(
            ""
            if not tags
            else (
                tags[0]["name"]
                if tags[0]["sha"] == last_commit_hash
                else f"{tags[0]['name']}-1-{last_commit_hash}"
            )
        )
    )
    repo_mock.git = git_obj
    repo_mock.head.commit.hexsha = last_commit_hash
    git.Repo.return_value = repo_mock

    git_info = GitRepoVersionInfo(path)
    assert git_info.is_git_repo
    ver = git_info.get_git_version()
    assert ver == expected_version_string


def test_gets_latest_tag_available_on_the_current_branch(mocker: MockFixture) -> None:
    with tempfile.TemporaryDirectory() as repo_dir:
        # init new git repo
        file_name = os.path.join(repo_dir, "new-file")
        repo = git.Repo.init(repo_dir)
        repo.git.config("user.email", "test@none.com")
        repo.git.config("user.name", "test")
        # create a new file and commit it
        open(file_name, "wb").close()
        repo.index.add([file_name])
        repo.index.commit("initial commit")
        first_commit = repo.head.commit
        # create new commit and a tag on main
        with open(file_name, "a") as f:
            f.write("branch main")
        repo.index.add([file_name])
        repo.index.commit("on main")
        repo.create_tag(
            "0.1.0",
            ref=repo.head.reference,
            message="This is a tag-object pointing to main",
        )
        # create a new branch, a commit and a tag there
        lower_tag = "0.0.1"
        new_branch = repo.create_head("feature", commit=first_commit.hexsha)
        repo.head.reference = new_branch
        with open(file_name, "a") as f:
            f.write("topic branch")
        repo.index.add([file_name])
        repo.index.commit("on topic")
        repo.create_tag(
            lower_tag,
            ref=repo.head.reference,
            message="This is a tag-object pointing to topic",
        )

        # check if we discover correct version
        git_info = GitRepoVersionInfo(repo_dir)
        assert git_info.is_git_repo
        ver = git_info.get_git_version()
        assert ver == lower_tag


def test_gets_latest_tag_available_when_no_tag(mocker: MockFixture) -> None:
    with tempfile.TemporaryDirectory() as repo_dir:
        # init new git repo
        file_name = os.path.join(repo_dir, "new-file")
        repo = git.Repo.init(repo_dir)
        repo.git.config("user.email", "test@none.com")
        repo.git.config("user.name", "test")
        # create a new file and commit it
        open(file_name, "wb").close()
        repo.index.add([file_name])
        repo.index.commit("initial commit")

        # check if we discover correct version
        git_info = GitRepoVersionInfo(repo_dir)
        assert git_info.is_git_repo
        ver = git_info.get_git_version()
        assert ver.startswith("0.0.0-")
