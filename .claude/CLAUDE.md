# CLAUDE.md

## Project Overview

**app-build-suite** is a Python-based Helm chart build automation tool for the Giant Swarm App Platform. It
orchestrates Helm chart building with linting, validation, versioning, and metadata generation.

## Project logic workflow

Always read the root directory README.md file and the docs/helm-build-pipeline.md files. Make sure any new
logic is structured the same as in the helm-build-pipeline.md file. Update the file whenever you introduce a
new pipeline step.

## Commands

### Development Setup

```bash
uv venv                    # Create virtual environment
uv sync                    # Install dependencies
source .venv/bin/activate  # Activate venv
```

### Running the Tool

```bash
python -m app_build_suite --help                           # View CLI help
python -m app_build_suite --step validate -c <chart_dir>   # Run specific step
```

### Running tests with makefile

```bash
make test                  # Run pytest locally (requires uv)
make test-ci               # Run pytest with coverage
make docker-test           # Run tests in Docker container
make docker-test-ci        # Run CI tests in Docker
```

### Docker

```bash
make docker-build          # Build Docker image
make docker-push           # Push to registry
make docker-build-test     # Build test runner image
```

### Code Quality

```bash
pre-commit run --all-files # Run all pre-commit hooks
```

## Architecture

### Package Structure

```text
app_build_suite/
├── __main__.py              # Entry point (main())
├── build_steps/
│   ├── helm.py              # Main build pipeline logic
│   ├── helm_consts.py       # Constants and defaults
│   ├── steps.py             # Step definitions (ALL_STEPS)
│   └── giant_swarm_validators/
│       ├── helm.py          # Chart validators
│       └── icon.py          # Icon validation
└── utils/
    └── git.py               # Git operations
```

### Key Concepts

- **Step-based pipeline**: Uses `step-exec-lib` for modular build steps
- **HelmBuildFilteringPipeline**: Main orchestrator in `build_steps/helm.py`
- **3-tier config hierarchy**: CLI args > env vars (ABS\_\*) > config files (.abs/main.yaml)

### Configuration Files

- `.abs/main.yaml` in chart directory (highest priority config file)
- `.abs/main.yaml` in current directory
- `.abs.main.yaml` (fallback)

### Entry Points

- CLI: `python -m app_build_suite` or `abs` console script
- Docker wrapper: `dabs.sh`

## Conventions

### Code Style

- Python 3.13+
- Type hints enforced (mypy)
- ruff for linting
- Pre-commit hooks for consistency

### Testing

- pytest with pytest-mock
- E2E tests in `tests/e2e/`
- Coverage tracked via codecov

### Dependencies

- Managed via `uv` (modern Python package manager)
- Lock file: `uv.lock`
- Renovate for automated updates

## Change validation

- if any python code was changed, run all the unit tests with uv and pytest
- always run pre-commit to make sure your edits pass project quality rules

## Commit Rules

**IMPORTANT:** Before completing any task, run `/commit` to commit your changes.

- Use conventional commit format: `type(scope): description`
- Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`
- Only commit files YOU modified - never commit unrelated changes
- Do not push unless explicitly asked
