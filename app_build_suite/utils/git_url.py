"""Git URL utilities for remote URL manipulation."""

import re
from typing import Optional


class GitUrlConverter:
    """Handles conversion between git URL formats for GitHub repositories."""

    # SSH format: git@github.com:org/repo.git or git@github.com:org/repo
    _SSH_PATTERN = re.compile(r"^git@github\.com:([^/]+/[^/]+?)(?:\.git)?$")

    # HTTPS format: https://github.com/org/repo.git or https://github.com/org/repo
    _HTTPS_PATTERN = re.compile(r"^https://github\.com/([^/]+/[^/]+?)(?:\.git)?$")

    @classmethod
    def is_github_url(cls, url: str) -> bool:
        """
        Check if URL is a GitHub URL (SSH or HTTPS).

        :param url: Git remote URL to check
        :return: True if URL is a GitHub URL
        """
        if not url:
            return False
        return bool(cls._SSH_PATTERN.match(url) or cls._HTTPS_PATTERN.match(url))

    @classmethod
    def normalize_to_https(cls, url: str) -> Optional[str]:
        """
        Normalize a git remote URL to HTTPS format for GitHub repositories.

        Converts SSH URLs to HTTPS and strips .git suffix.

        Examples:
            git@github.com:org/repo.git → https://github.com/org/repo
            https://github.com/org/repo.git → https://github.com/org/repo
            https://github.com/org/repo → https://github.com/org/repo

        :param url: Git remote URL (SSH or HTTPS)
        :return: Normalized HTTPS URL without .git suffix, or None if not a GitHub URL
        """
        if not url:
            return None

        # Try SSH format first
        ssh_match = cls._SSH_PATTERN.match(url)
        if ssh_match:
            return f"https://github.com/{ssh_match.group(1)}"

        # Try HTTPS format
        https_match = cls._HTTPS_PATTERN.match(url)
        if https_match:
            return f"https://github.com/{https_match.group(1)}"

        # Not a recognized GitHub URL format
        return None

    @classmethod
    def urls_match(cls, url1: str, url2: str) -> bool:
        """
        Check if two URLs point to the same GitHub repository.

        Normalizes both URLs before comparison, handles trailing slashes.

        :param url1: First URL to compare
        :param url2: Second URL to compare
        :return: True if URLs point to same repository
        """
        normalized1 = cls.normalize_to_https(url1)
        normalized2 = cls.normalize_to_https(url2)

        if normalized1 is None or normalized2 is None:
            # If either can't be normalized, do a simple comparison
            return url1.rstrip("/") == url2.rstrip("/")

        return normalized1.rstrip("/") == normalized2.rstrip("/")
