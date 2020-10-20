import os.path
from app_build_suite.utils.files import get_file_sha256


def test_get_sha256() -> None:
    filename = os.path.join(os.path.dirname(__file__), "..", "build_steps", "res_test_helm", "Chart.yaml")
    assert get_file_sha256(filename) == "a8d675fa9d137613632782c05c2a68c1a6aa3ca463b612504d4be17dfa86325b"
