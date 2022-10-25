import pytest

from app_build_suite.__main__ import main


def test_build_example_app(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["bogus", "-c", "examples/apps/hello-world-app", "--destination", "build/"],
    )
    main()


def test_disable_chart_linter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["bogus", "-c", "examples/apps/hello-world-app", "--disable-chart-linter", "--destination", "build/"],
    )
    main()


def test_only_validate_example_app(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["bogus", "-c", "examples/apps/hello-world-app", "-p", "helm-validate-giantswarm"],
    )
    main()
