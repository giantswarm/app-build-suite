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
