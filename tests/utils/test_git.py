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
    ],
)
def test_git_version(
    tags: List[Dict[str, str]], last_commit_hash: str, expected_version_string: str, mocker: MockFixture
) -> None:
    path = "bogus/path"
    mocker.patch("git.Repo")
    repo_mock = mocker.MagicMock()
    tag_objs = []
    for tag in tags:
        tag_obj = mocker.Mock()
        type(tag_obj).name = mocker.PropertyMock(return_value=tag["name"])
        commit = mocker.Mock()
        type(commit).hexsha = mocker.PropertyMock(return_value=tag["sha"])
        type(tag_obj).commit = mocker.PropertyMock(return_value=commit)
        tag_objs.append(tag_obj)
    type(repo_mock).tags = mocker.PropertyMock(return_value=tag_objs)
    repo_mock.head.commit.hexsha = last_commit_hash
    git.Repo.return_value = repo_mock

    git_info = GitRepoVersionInfo(path)
    assert git_info.is_git_repo
    ver = git_info.get_git_version()
    assert ver == expected_version_string
