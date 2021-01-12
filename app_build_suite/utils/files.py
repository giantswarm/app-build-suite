"""Module with file utils"""
import hashlib
import shutil

from app_build_suite.errors import ValidationError


def get_file_sha256(filename: str) -> str:
    """
    Get SHA256 has of a file
    :param filename: The path to the file.
    :return: Hexadecimal SHA256 hash as string.
    """
    with open(filename, "rb") as f:
        file_bytes = f.read()
        readable_hash = hashlib.sha256(file_bytes).hexdigest()
        return readable_hash


def assert_binary_present_in_path(check_source_name: str, bin_name: str) -> None:
    """
    Checks if binary is available in the system. Raises ValidationError if not found.
    :param check_source_name: The name of the component making the check (for clear exception source).
    :param bin_name: The name of the binary executable.
    :return: None.
    """
    if shutil.which(bin_name) is None:
        raise ValidationError(
            check_source_name,
            f"Can't find {bin_name} executable. Please make sure it's installed.",
        )
