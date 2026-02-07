# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

App Build Suite (ABS) is a Python-based CI/CD tool for building Helm charts for the Giant Swarm App Platform. It orchestrates well-known tools (helm, ct, kube-linter) into an opinionated build pipeline and adds Giant Swarm-specific metadata generation.

## Development Commands

```bash
# Setup (requires Python 3.13+ and uv)
uv venv && source .venv/bin/activate && uv sync
pre-commit install

# Run tests
make test                    # Local pytest with coverage
make docker-test             # Docker-based tests (interactive)
make docker-test-ci          # Docker-based tests with XML coverage

# Build Docker image
make docker-build

# Run ABS locally
python -m app_build_suite --help
python -m app_build_suite --step validate -c PATH_TO_CHART

# Release (manual process)
make release TAG=vX.Y.Z
git push origin vX.Y.Z
```

## Architecture

### Build Step Pipeline

The core framework uses `step_exec_lib` to execute a configurable pipeline of build steps. Entry point is `app_build_suite/__main__.py`.

**Pipeline flow:**
1. `HelmBuilderValidator` - Validates Chart.yaml/values.yaml exist, RFC 1123 name validation
2. `HelmGitVersionSetter` - Extracts version from git tags (optional)
3. `HelmChartToolLinter` - Runs `ct lint` for YAML validation
4. `KubeLinter` - Static K8s manifest analysis
5. `HelmChartMetadataPreparer` - Gathers metadata for Giant Swarm App Platform
6. `HelmChartBuilder` - Runs `helm package`
7. `HelmChartMetadataFinalizer` - Completes metadata generation
8. `HelmChartYAMLRestorer` - Restores original Chart.yaml if modified

Core build step logic is in [app_build_suite/build_steps/helm.py](app_build_suite/build_steps/helm.py).

### Giant Swarm Validators

Located in `app_build_suite/build_steps/giant_swarm_validators/`, these run during `static_check` step:
- **F0001** `HasValuesSchema` - Checks for values.schema.json
- **C0001** `HasTeamLabel` - Validates team annotation
- **C0002** `IconExists` - Validates icon field
- **C0003** `IconIsAlmostSquare` - Icon aspect ratio validation

### Configuration Priority

ABS configuration (highest to lowest priority):
1. Command line arguments
2. Environment variables (ABS_ prefix)
3. Config file: `.abs/main.yaml` in chart directory

### Step Execution Control

Run specific steps: `--steps validate static_check build`
Skip steps: `--skip-steps validate static_check`

## Key Dependencies

- `step-exec-lib` - Core build step framework (from Giant Swarm)
- `configargparse` - Config file + CLI + env var parsing
- `gitpython` - Git integration for version extraction
- `pillow`, `cairosvg` - Icon validation

## Code Style

- Uses `ruff` for linting/formatting (line length: 120)
- Uses `mypy` for type checking
- Pre-commit hooks enforced via `.pre-commit-config.yaml`
- Follow Giant Swarm coding guidelines: https://github.com/giantswarm/fmt/
- Update CHANGELOG.md for changes
- Keep `docs/` folder and README.md up-to-date when changing code
