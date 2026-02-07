"""Module with git related utilities."""

from typing import Optional

import git


class GitRepoVersionInfo:
    """
    Provides application versions information based on the tags and commits in the repo
    """

    def __init__(self, path: str):
        """
        Create an instance of GitRepoVersionInfo
        :param path: The path to search for git information. It searches for '.git' in this folder or any parent
        folder.
        """
        self._is_repo = False
        try:
            self._repo = git.Repo(path, search_parent_directories=True)
            self._is_repo = True
        except git.exc.InvalidGitRepositoryError:
            self._repo = None

    @property
    def is_git_repo(self) -> bool:
        """
        Checks if the path given in constructor is a sub-path of a valid git repo.
        :return: Boolean true, if repo was found.
        """
        return self._is_repo

    def get_git_version(self, strip_v_in_version: bool = True) -> str:
        """
        Gets application version in the format [last-tag]-[last-commit-sha].
        :param strip_v_in_version: If the version tag starts with 'v' (like 'v1.2.3),
        this chooses if the 'v' should be stripped, so the resulting tag is '1.2.3'.
        If there's a "-", "." or "_" separator after "v", it is removed as well.
        :return: The version string
        """
        if not self._is_repo:
            raise git.exc.InvalidGitRepositoryError()
        sha = self._repo.head.commit.hexsha
        try:
            latest_tag = self._repo.git.describe("--tags")
        except git.exc.GitCommandError:
            return f"0.0.0-{sha}"
        if strip_v_in_version and latest_tag.startswith("v"):
            latest_tag = latest_tag.lstrip("v")
            latest_tag = latest_tag.lstrip("-_.")
        latest_tag_parts = latest_tag.rsplit("-", maxsplit=2)
        if not latest_tag_parts[0]:
            return f"0.0.0-{sha}"
        if len(latest_tag_parts) < 3:
            return latest_tag
        return f"{latest_tag_parts[0]}-{sha}"

    def get_remote_url(self, remote_name: str = "origin") -> Optional[str]:
        """
        Get the URL of the specified git remote.

        :param remote_name: Name of the remote (default: 'origin')
        :return: Remote URL string, or None if remote doesn't exist or not a git repo
        """
        if not self._is_repo or self._repo is None:
            return None
        try:
            return self._repo.remote(remote_name).url
        except (ValueError, git.exc.GitCommandError):
            return None
