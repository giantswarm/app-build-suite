"""Module with git related utilities."""

import os
import re
from datetime import datetime, timezone
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

    def _tag_on_head(self, strip_v: bool) -> Optional[str]:
        """Returns the tag name if HEAD commit is directly tagged, else None."""
        assert self._repo is not None
        head_sha = self._repo.head.commit.hexsha
        for tag in self._repo.tags:
            if tag.commit.hexsha == head_sha:
                name = tag.name
                if strip_v and name.startswith("v"):
                    name = name.lstrip("v").lstrip("-_.")
                return name
        return None

    def _find_next_dev_base_version(self) -> str:
        """
        Finds the last stable semver tag (X.Y.Z, no pre-release suffix) and returns
        the version with patch bumped by 1. Respects GS_GIT_TAG_PREFIX env var.
        Returns '0.0.1' if no stable tag is found.
        """
        assert self._repo is not None
        prefix = os.environ.get("GS_GIT_TAG_PREFIX", "")
        stable_re = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
        best: Optional[tuple[int, int, int]] = None
        for tag in self._repo.tags:
            name = tag.name
            if prefix and not name.startswith(prefix):
                continue
            name = name[len(prefix) :]
            m = stable_re.match(name)
            if not m:
                continue
            version = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if best is None or version > best:
                best = version
        if best is None:
            return "0.0.1"
        return f"{best[0]}.{best[1]}.{best[2] + 1}"

    @staticmethod
    def _sanitize_branch_name(branch: str) -> str:
        """Replaces non-alphanumeric chars (except hyphens) with hyphens, collapses runs, strips edges."""
        sanitized = re.sub(r"[^a-zA-Z0-9-]", "-", branch)
        sanitized = re.sub(r"-+", "-", sanitized)
        return sanitized.strip("-")

    def _current_branch(self) -> str:
        """Returns current branch name, or 'detached' if HEAD is detached."""
        assert self._repo is not None
        try:
            return self._repo.active_branch.name
        except TypeError:
            return "detached"

    def get_git_version(self, strip_v_in_version: bool = True) -> str:
        """
        Gets application version following the semVer tagging schema:
        - If HEAD is directly on a tag (stable X.Y.Z or RC X.Y.Z-rc.N): returns the tag.
        - Otherwise: returns X.Y.Z-dev.BRANCH.DATE.TIME where X.Y.Z is the next patch
          version after the last stable tag, BRANCH is the sanitized current branch name,
          and DATE/TIME are UTC timestamps.
        :param strip_v_in_version: Strip leading 'v' (and separator) from tag names.
        :return: The version string
        """
        if not self._is_repo:
            raise git.exc.InvalidGitRepositoryError()

        tag = self._tag_on_head(strip_v=strip_v_in_version)
        if tag is not None:
            return tag

        base_version = self._find_next_dev_base_version()
        branch = self._sanitize_branch_name(self._current_branch())
        now = datetime.now(tz=timezone.utc)
        date = now.strftime("%Y%m%d")
        time = now.strftime("%H%M%S")
        return f"{base_version}-dev.{branch}.{date}.{time}"

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
