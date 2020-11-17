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

    def get_git_version(self, strip_v_in_version: bool = True) -> str:
        """
        Gets application version in the format [last-tag]-[last-commit-sha].
        :param strip_v_in_version: If the version tag starts with 'v' (like 'v1.2.3),
        this chooses if the 'v' should be stripped, so the resulting tag is '1.2.3'
        :return: The version string
        """
        if not self._is_repo:
            raise git.exc.InvalidGitRepositoryError()
        tags = sorted(self._repo.tags, key=lambda t: t.commit.committed_date)
        ver = "0.0.0" if len(tags) == 0 else tags[-1]
        if strip_v_in_version and ver.name.startswith("v"):
            txt_ver = ver.name.lstrip("v-_")
        else:
            txt_ver = ver.name
        sha = self._repo.head.object.hexsha
        return f"{txt_ver}-{sha}"
