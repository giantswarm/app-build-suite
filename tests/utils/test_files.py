import os.path
from step_exec_lib.utils.files import get_file_sha256


def test_get_sha256() -> None:
    filename = os.path.join(os.path.dirname(__file__), "..", "build_steps", "res_test_helm", "Chart.yaml")
    assert get_file_sha256(filename) == "d7d772229b6187fd20906bf4c457b2077a630eacdaa193ac11482096e505c1bc"
