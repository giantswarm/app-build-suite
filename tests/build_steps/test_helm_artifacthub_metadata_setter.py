"""Tests for HelmArtifactHubMetadataSetter build step."""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import configargparse
import yaml

from app_build_suite.build_steps.chart_yaml_writer import ChartYamlWriter
from app_build_suite.build_steps.helm_artifacthub_metadata_setter import HelmArtifactHubMetadataSetter
from app_build_suite.build_steps.helm_chart_yaml_restorer import HelmChartYAMLRestorer
from app_build_suite.build_steps.helm_consts import (
    BlockLiteralStr,
    context_key_artifacthub_readme_copied,
    context_key_changes_made,
    context_key_chart_yaml,
)
from tests.build_steps.helpers import init_config_for_step

APACHE_2_LICENSE_TEXT = """
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION
"""

MIT_LICENSE_TEXT = """
MIT License

Copyright (c) 2026 Giant Swarm

Permission is hereby granted, free of charge, to any person obtaining a copy...
"""

KEY_LICENSE = "artifacthub.io/license"
KEY_LINKS = "artifacthub.io/links"


def _make_repo(
    tmp_path: Path,
    license_text: Optional[str] = None,
    root_readme: Optional[str] = None,
    chart_readme: Optional[str] = None,
) -> Path:
    """Create a fake repo (a '.git' dir marks the root) with a chart dir inside; return the chart dir."""
    (tmp_path / ".git").mkdir()
    chart_dir = tmp_path / "helm" / "test-app"
    chart_dir.mkdir(parents=True)
    if license_text is not None:
        (tmp_path / "LICENSE").write_text(license_text)
    if root_readme is not None:
        (tmp_path / "README.md").write_text(root_readme)
    if chart_readme is not None:
        (chart_dir / "README.md").write_text(chart_readme)
    return chart_dir


def _init_step_for_chart_dir(
    chart_dir: Path, chart_yaml: Dict[str, Any]
) -> Tuple[HelmArtifactHubMetadataSetter, configargparse.Namespace, Dict[str, Any]]:
    step = HelmArtifactHubMetadataSetter()
    config = init_config_for_step(step)
    config.chart_dir = str(chart_dir)
    context = {
        context_key_chart_yaml: chart_yaml,
        context_key_changes_made: False,
    }
    return step, config, context


def test_injects_license_when_apache2_detected(tmp_path: Path) -> None:
    chart_dir = _make_repo(tmp_path, license_text=APACHE_2_LICENSE_TEXT, chart_readme="# chart")
    chart_yaml: Dict[str, Any] = {"name": "test-app", "version": "0.0.1"}
    step, config, context = _init_step_for_chart_dir(chart_dir, chart_yaml)

    step.run(config, context)

    assert chart_yaml["annotations"][KEY_LICENSE] == "Apache-2.0"
    assert context[context_key_changes_made] is True


def test_keeps_existing_license_annotation(tmp_path: Path) -> None:
    chart_dir = _make_repo(tmp_path, license_text=APACHE_2_LICENSE_TEXT, chart_readme="# chart")
    chart_yaml: Dict[str, Any] = {
        "name": "test-app",
        "version": "0.0.1",
        "annotations": {KEY_LICENSE: "MIT", KEY_LINKS: "- name: custom\n  url: https://example.com\n"},
    }
    step, config, context = _init_step_for_chart_dir(chart_dir, chart_yaml)

    step.run(config, context)

    assert chart_yaml["annotations"][KEY_LICENSE] == "MIT"
    assert chart_yaml["annotations"][KEY_LINKS] == "- name: custom\n  url: https://example.com\n"
    assert context[context_key_changes_made] is False


def test_skips_license_when_not_apache2(tmp_path: Path) -> None:
    chart_dir = _make_repo(tmp_path, license_text=MIT_LICENSE_TEXT, chart_readme="# chart")
    chart_yaml: Dict[str, Any] = {"name": "test-app", "version": "0.0.1"}
    step, config, context = _init_step_for_chart_dir(chart_dir, chart_yaml)

    step.run(config, context)

    assert KEY_LICENSE not in chart_yaml.get("annotations", {})


def test_skips_license_when_no_license_file(tmp_path: Path) -> None:
    chart_dir = _make_repo(tmp_path, chart_readme="# chart")
    chart_yaml: Dict[str, Any] = {"name": "test-app", "version": "0.0.1"}
    step, config, context = _init_step_for_chart_dir(chart_dir, chart_yaml)

    step.run(config, context)

    assert KEY_LICENSE not in chart_yaml.get("annotations", {})
    assert context[context_key_changes_made] is False


def test_injects_links_from_home_and_upstream_source(tmp_path: Path) -> None:
    chart_dir = _make_repo(tmp_path, chart_readme="# chart")
    chart_yaml: Dict[str, Any] = {
        "name": "test-app",
        "version": "0.0.1",
        "home": "https://github.com/giantswarm/test-app",
        "sources": [
            "https://github.com/giantswarm/test-app",
            "https://github.com/upstream-org/upstream-project",
            "https://github.com/other-org/other-project",
        ],
    }
    step, config, context = _init_step_for_chart_dir(chart_dir, chart_yaml)

    step.run(config, context)

    links_value = chart_yaml["annotations"][KEY_LINKS]
    assert isinstance(links_value, str)
    links = yaml.safe_load(links_value)
    assert links == [
        {"name": "Support", "url": "https://github.com/giantswarm/test-app/issues"},
        {"name": "Upstream project", "url": "https://github.com/upstream-org/upstream-project"},
    ]
    assert context[context_key_changes_made] is True


def test_injects_links_without_upstream_when_all_sources_are_giantswarm(tmp_path: Path) -> None:
    chart_dir = _make_repo(tmp_path, chart_readme="# chart")
    chart_yaml: Dict[str, Any] = {
        "name": "test-app",
        "version": "0.0.1",
        "home": "https://github.com/giantswarm/test-app",
        "sources": ["https://github.com/giantswarm/test-app"],
    }
    step, config, context = _init_step_for_chart_dir(chart_dir, chart_yaml)

    step.run(config, context)

    links = yaml.safe_load(chart_yaml["annotations"][KEY_LINKS])
    assert links == [{"name": "Support", "url": "https://github.com/giantswarm/test-app/issues"}]


def test_injects_upstream_link_only_when_no_repo_url_derivable(tmp_path: Path) -> None:
    # no 'home' field and no usable git remote - only the 'Upstream project' link can be derived
    chart_dir = _make_repo(tmp_path, chart_readme="# chart")
    chart_yaml: Dict[str, Any] = {
        "name": "test-app",
        "version": "0.0.1",
        "sources": ["https://github.com/upstream-org/upstream-project"],
    }
    step, config, context = _init_step_for_chart_dir(chart_dir, chart_yaml)

    step.run(config, context)

    links = yaml.safe_load(chart_yaml["annotations"][KEY_LINKS])
    assert links == [{"name": "Upstream project", "url": "https://github.com/upstream-org/upstream-project"}]


def test_skips_links_when_nothing_derivable(tmp_path: Path) -> None:
    chart_dir = _make_repo(tmp_path, chart_readme="# chart")
    chart_yaml: Dict[str, Any] = {"name": "test-app", "version": "0.0.1"}
    step, config, context = _init_step_for_chart_dir(chart_dir, chart_yaml)

    step.run(config, context)

    assert KEY_LINKS not in chart_yaml.get("annotations", {})
    assert context[context_key_changes_made] is False


def test_copies_root_readme_and_removes_it_in_cleanup(tmp_path: Path) -> None:
    chart_dir = _make_repo(tmp_path, root_readme="# root readme")
    chart_yaml: Dict[str, Any] = {"name": "test-app", "version": "0.0.1"}
    step, config, context = _init_step_for_chart_dir(chart_dir, chart_yaml)

    step.run(config, context)

    chart_readme = chart_dir / "README.md"
    assert chart_readme.is_file()
    assert chart_readme.read_text() == "# root readme"
    assert context[context_key_artifacthub_readme_copied] == str(chart_readme)

    step.cleanup(config, context, has_build_failed=False)
    assert not chart_readme.exists()


def test_keeps_existing_chart_readme(tmp_path: Path) -> None:
    chart_dir = _make_repo(tmp_path, root_readme="# root readme", chart_readme="# chart readme")
    chart_yaml: Dict[str, Any] = {"name": "test-app", "version": "0.0.1"}
    step, config, context = _init_step_for_chart_dir(chart_dir, chart_yaml)

    step.run(config, context)

    chart_readme = chart_dir / "README.md"
    assert chart_readme.read_text() == "# chart readme"
    assert context_key_artifacthub_readme_copied not in context

    step.cleanup(config, context, has_build_failed=False)
    assert chart_readme.read_text() == "# chart readme"


def test_disabled_flag_makes_step_a_noop(tmp_path: Path) -> None:
    chart_dir = _make_repo(tmp_path, license_text=APACHE_2_LICENSE_TEXT, root_readme="# root readme")
    chart_yaml: Dict[str, Any] = {
        "name": "test-app",
        "version": "0.0.1",
        "home": "https://github.com/giantswarm/test-app",
    }
    step, config, context = _init_step_for_chart_dir(chart_dir, chart_yaml)
    config.disable_artifacthub_metadata = True

    step.run(config, context)

    assert "annotations" not in chart_yaml
    assert not (chart_dir / "README.md").exists()
    assert context[context_key_changes_made] is False


def test_injected_annotations_are_restored_after_build(tmp_path: Path) -> None:
    """The injected annotations are part of the regular Chart.yaml write/backup/restore cycle."""
    chart_dir = _make_repo(tmp_path, license_text=APACHE_2_LICENSE_TEXT, chart_readme="# chart")
    original_chart_yaml_text = 'name: test-app\nversion: 0.0.1\nhome: "https://github.com/giantswarm/test-app"\n'
    chart_yaml_path = chart_dir / "Chart.yaml"
    chart_yaml_path.write_text(original_chart_yaml_text)
    chart_yaml: Dict[str, Any] = yaml.safe_load(original_chart_yaml_text)
    step, config, context = _init_step_for_chart_dir(chart_dir, chart_yaml)
    config.keep_chart_changes = False

    step.run(config, context)
    ChartYamlWriter().run(config, context)

    written = yaml.safe_load(chart_yaml_path.read_text())
    assert written["annotations"][KEY_LICENSE] == "Apache-2.0"
    assert "Support" in written["annotations"][KEY_LINKS]
    assert (chart_dir / "Chart.yaml.back").is_file()

    HelmChartYAMLRestorer().cleanup(config, context, has_build_failed=False)

    assert chart_yaml_path.read_text() == original_chart_yaml_text
    assert not (chart_dir / "Chart.yaml.back").exists()


def test_giantswarm_prefixed_org_is_treated_as_upstream(tmp_path: Path) -> None:
    """A source in a different org whose name merely starts with 'giantswarm' is upstream, not ours."""
    chart_dir = _make_repo(tmp_path, chart_readme="# chart")
    chart_yaml: Dict[str, Any] = {
        "name": "test-app",
        "version": "0.0.1",
        "home": "https://github.com/giantswarm/test-app",
        "sources": ["https://github.com/giantswarm-community/upstream-project"],
    }
    step, config, context = _init_step_for_chart_dir(chart_dir, chart_yaml)

    step.run(config, context)

    links = yaml.safe_load(chart_yaml["annotations"][KEY_LINKS])
    assert {"name": "Upstream project", "url": "https://github.com/giantswarm-community/upstream-project"} in links


def test_detects_repo_root_when_git_is_a_file(tmp_path: Path) -> None:
    """In worktrees/submodules '.git' is a file (a 'gitdir:' pointer), not a directory."""
    (tmp_path / ".git").write_text("gitdir: /elsewhere/.git/worktrees/wt\n")
    (tmp_path / "LICENSE").write_text(APACHE_2_LICENSE_TEXT)
    chart_dir = tmp_path / "helm" / "test-app"
    chart_dir.mkdir(parents=True)
    (chart_dir / "README.md").write_text("# chart")
    chart_yaml: Dict[str, Any] = {"name": "test-app", "version": "0.0.1"}
    step, config, context = _init_step_for_chart_dir(chart_dir, chart_yaml)

    step.run(config, context)

    assert chart_yaml["annotations"][KEY_LICENSE] == "Apache-2.0"


def test_keeps_copied_readme_with_keep_chart_changes(tmp_path: Path) -> None:
    """With --keep-chart-changes the copied README stays, matching the retained annotations."""
    chart_dir = _make_repo(tmp_path, root_readme="# root readme")
    chart_yaml: Dict[str, Any] = {"name": "test-app", "version": "0.0.1"}
    step, config, context = _init_step_for_chart_dir(chart_dir, chart_yaml)
    config.keep_chart_changes = True

    step.run(config, context)
    chart_readme = chart_dir / "README.md"
    assert chart_readme.is_file()

    step.cleanup(config, context, has_build_failed=False)
    assert chart_readme.read_text() == "# root readme"


def test_writer_block_scalars_only_the_links_annotation(tmp_path: Path) -> None:
    """The links value is a BlockLiteralStr rendered as a block scalar; other multi-line strings
    (e.g. a multi-line description) keep their default rendering and are not reformatted."""
    chart_dir = _make_repo(tmp_path, chart_readme="# chart")
    chart_yaml_path = chart_dir / "Chart.yaml"
    chart_yaml_path.write_text("name: test-app\nversion: 0.0.1\n")
    chart_yaml: Dict[str, Any] = {
        "name": "test-app",
        "version": "0.0.1",
        "description": "line one\nline two",
        "home": "https://github.com/giantswarm/test-app",
    }
    step, config, context = _init_step_for_chart_dir(chart_dir, chart_yaml)

    step.run(config, context)
    assert isinstance(chart_yaml["annotations"][KEY_LINKS], BlockLiteralStr)

    ChartYamlWriter().run(config, context)
    raw = chart_yaml_path.read_text()

    assert "artifacthub.io/links: |" in raw
    assert "description: |" not in raw
    assert yaml.safe_load(raw)["description"] == "line one\nline two"
