"""Module with file utils"""
import hashlib


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
