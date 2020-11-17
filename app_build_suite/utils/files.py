"""Module with file utils"""
import hashlib
import yaml

from typing import Any, Dict

# from shutil import copyfile


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


def save_yaml(filename: str, data: Dict[str, Any]) -> None:
    with open(filename, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


# def copy_file(source: str, destination: str) -> None:
#     try:
#         copyfile(source, destination)
#     except expression as identifier:
#         # logger
#         pass
