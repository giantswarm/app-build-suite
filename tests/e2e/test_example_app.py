from app_build_suite.__main__ import main


def test_build_example_app(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["bogus", "-c", "../../examples/apps/hello-world-app", "--destination", "build/", "--skip-steps", "test_all"],
    )
    main()
