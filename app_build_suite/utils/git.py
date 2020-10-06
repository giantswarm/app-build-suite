"""Module with git related utilities."""
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

    @property
    def get_git_version(self) -> str:
        """
        Gets application version in the format [last-tag]-[last-commit-sha].
        :return: The version string
        """
        if not self._is_repo:
            raise git.exc.InvalidGitRepositoryError()
        tags = sorted(self._repo.tags, key=lambda t: t.tag.tagged_date)
        ver = "0.0.0" if len(tags) == 0 else tags[-1]
        sha = self._repo.head.object.hexsha
        return f"{ver}-{sha}"
