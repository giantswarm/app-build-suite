import git


def is_git_repo(path: str) -> bool:
    try:
        _ = git.Repo(path, search_parent_directories=True)
    except git.exc.InvalidGitRepositoryError:
        return False
    return True


def get_git_version(path: str) -> str:
    repo = git.Repo(path, search_parent_directories=True)
    tags = sorted(repo.tags, key=lambda t: t.tag.tagged_date)
    ver = "0.0.0" if len(tags) == 0 else tags[-1]
    sha = repo.head.object.hexsha
    return f"{ver}-{sha}"
