"""Git repository version utilities."""

import git


class GitRepoVersionInfo:
    def __init__(self, path: str):
        self._is_repo = False
        try:
            self._repo = git.Repo(path, search_parent_directories=True)
            self._is_repo = True
        except git.exc.InvalidGitRepositoryError:
            self._repo = None

    @property
    def is_git_repo(self) -> bool:
        return self._is_repo

    def get_git_version(self, strip_v_in_version: bool = True) -> str:
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
        latest_tag_parts = latest_tag.split("-")
        if not latest_tag_parts[0]:
            return f"0.0.0-{sha}"
        if len(latest_tag_parts) == 3 and latest_tag_parts[2] != "":
            return f"{latest_tag_parts[0]}-{sha}"
        return latest_tag_parts[0]
