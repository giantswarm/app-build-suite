import pytest

from app_build_suite.__main__ import main


def test_build_example_app(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["bogus", "-c", "examples/apps/hello-world-app", "--destination", "build/"],
    )
    main()
