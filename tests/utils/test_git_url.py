import pytest

from app_build_suite.utils.git_url import GitUrlConverter


class TestGitUrlConverter:
    """Tests for GitUrlConverter utility class."""

    @pytest.mark.parametrize(
        "url,expected",
        [
            # SSH format URLs
            ("git@github.com:org/repo.git", True),
            ("git@github.com:org/repo", True),
            ("git@github.com:giantswarm/hello-world-app.git", True),
            # HTTPS format URLs
            ("https://github.com/org/repo.git", True),
            ("https://github.com/org/repo", True),
            ("https://github.com/giantswarm/hello-world-app", True),
            # Non-GitHub URLs
            ("git@gitlab.com:org/repo.git", False),
            ("https://gitlab.com/org/repo.git", False),
            ("git@bitbucket.org:org/repo.git", False),
            ("https://bitbucket.org/org/repo.git", False),
            ("https://example.com/org/repo", False),
            # Invalid URLs
            ("", False),
            ("not-a-url", False),
            ("http://github.com/org/repo", False),  # http not https
        ],
        ids=[
            "ssh with .git",
            "ssh without .git",
            "ssh giantswarm example",
            "https with .git",
            "https without .git",
            "https giantswarm example",
            "gitlab ssh",
            "gitlab https",
            "bitbucket ssh",
            "bitbucket https",
            "other domain",
            "empty string",
            "not a url",
            "http not https",
        ],
    )
    def test_is_github_url(self, url: str, expected: bool) -> None:
        assert GitUrlConverter.is_github_url(url) == expected

    @pytest.mark.parametrize(
        "url,expected",
        [
            # SSH to HTTPS conversion
            ("git@github.com:org/repo.git", "https://github.com/org/repo"),
            ("git@github.com:org/repo", "https://github.com/org/repo"),
            ("git@github.com:giantswarm/hello-world-app.git", "https://github.com/giantswarm/hello-world-app"),
            # HTTPS normalization
            ("https://github.com/org/repo.git", "https://github.com/org/repo"),
            ("https://github.com/org/repo", "https://github.com/org/repo"),
            ("https://github.com/giantswarm/hello-world-app.git", "https://github.com/giantswarm/hello-world-app"),
            # Non-GitHub returns None
            ("git@gitlab.com:org/repo.git", None),
            ("https://gitlab.com/org/repo.git", None),
            # Invalid returns None
            ("", None),
            ("not-a-url", None),
        ],
        ids=[
            "ssh with .git to https",
            "ssh without .git to https",
            "ssh giantswarm to https",
            "https strips .git",
            "https unchanged",
            "https giantswarm strips .git",
            "gitlab ssh returns none",
            "gitlab https returns none",
            "empty returns none",
            "invalid returns none",
        ],
    )
    def test_normalize_to_https(self, url: str, expected: str) -> None:
        assert GitUrlConverter.normalize_to_https(url) == expected

    @pytest.mark.parametrize(
        "url1,url2,expected",
        [
            # Same URLs
            ("https://github.com/org/repo", "https://github.com/org/repo", True),
            # SSH and HTTPS match
            ("git@github.com:org/repo.git", "https://github.com/org/repo", True),
            ("https://github.com/org/repo.git", "git@github.com:org/repo", True),
            # With trailing slashes
            ("https://github.com/org/repo/", "https://github.com/org/repo", True),
            ("https://github.com/org/repo", "https://github.com/org/repo/", True),
            # Different repos
            ("https://github.com/org/repo1", "https://github.com/org/repo2", False),
            ("git@github.com:org1/repo.git", "git@github.com:org2/repo.git", False),
            # Non-GitHub URLs (simple comparison)
            ("https://gitlab.com/org/repo", "https://gitlab.com/org/repo", True),
            ("https://gitlab.com/org/repo1", "https://gitlab.com/org/repo2", False),
        ],
        ids=[
            "same https urls",
            "ssh matches https",
            "https with .git matches ssh",
            "trailing slash match 1",
            "trailing slash match 2",
            "different repos",
            "different orgs",
            "non-github same",
            "non-github different",
        ],
    )
    def test_urls_match(self, url1: str, url2: str, expected: bool) -> None:
        assert GitUrlConverter.urls_match(url1, url2) == expected
