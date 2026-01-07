# Configuration Reference

This document provides a comprehensive reference for all configuration options available in App Build Suite (ABS).

## Configuration Methods

ABS supports three configuration methods, listed in order of priority (highest to lowest):

1. **Command line arguments** - Highest priority, overrides all other methods
2. **Environment variables** - All options can be set via environment variables with `ABS_` prefix
3. **Config file** - Located at `.abs/main.yaml` in your chart directory or project root

### Environment Variables

All configuration options can be set via environment variables by:
1. Converting the option name to uppercase
2. Replacing dashes with underscores
3. Adding the `ABS_` prefix

For example:
- `--replace-chart-version-with-git` → `ABS_REPLACE_CHART_VERSION_WITH_GIT=true`
- `--catalog-base-url` → `ABS_CATALOG_BASE_URL=https://example.com/catalog/`

### Config File Location

ABS looks for configuration files in this order:
1. `<chart-dir>/.abs/main.yaml`
2. `<chart-dir>/.abs/main.yml`
3. `<current-dir>/.abs/main.yaml`
4. `<current-dir>/.abs/main.yml`

## Global Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-d`, `--debug` | flag | `false` | Enable debug messages for verbose output |
| `--version` | flag | - | Show version information and exit |
| `-b`, `--build-engine` | string | `helm3` | Select the build engine (currently only `helm3` is supported) |
| `--steps` | list | `['all']` | List of steps to execute. Available: `all`, `build`, `validate`, `static_check`, `metadata` |
| `--skip-steps` | list | `[]` | List of steps to skip. Cannot be used with `--steps` |

## Chart Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-c`, `--chart-dir` | string | `.` | Path to the Helm Chart to build |
| `--destination` | string | `.` | Path to the directory where the packaged chart `.tgz` will be stored |

## Version Management

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--replace-chart-version-with-git` | flag | `false` | Replace `version` in `Chart.yaml` with git-derived version |
| `--replace-app-version-with-git` | flag | `false` | Replace `appVersion` in `Chart.yaml` with git-derived version |
| `--keep-chart-changes` | flag | `false` | Keep the changes made to `Chart.yaml` (normally restored after build) |

### Git Version Format

When git version replacement is enabled, the version is formatted as:
- For tagged commits: `<tag>` (e.g., `1.2.3`)
- For untagged commits: `<last-tag>-<commit-hash>` (e.g., `1.2.3-abc123def456`)

## Metadata Generation

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--generate-metadata` | flag | `false` | Enable generation of metadata for Giant Swarm App Platform |
| `--catalog-base-url` | string | - | Base URL of the app catalog (required when `generate-metadata` is enabled). Must end with `/` |

### Generated Metadata

When metadata generation is enabled, ABS creates a `<chart-name>-<version>.tgz-meta/` directory containing:
- `main.yaml` - Primary metadata file with chart information
- `README.md` - Copied from the chart if present
- `values.schema.json` - Copied from the chart if present

## Linting and Validation

### Chart Testing (`ct`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--ct-config` | string | - | Path to `ct` (chart-testing) configuration file |
| `--ct-schema` | string | - | Path to custom `ct` schema file for `Chart.yaml` validation |

When metadata generation is enabled, ABS automatically uses a custom schema that validates Giant Swarm specific fields.

#### Example `ct` Config File

```yaml
---
chart-repos:
  - bitnami=https://charts.bitnami.com/bitnami
  - giantswarm-catalog=https://giantswarm.github.io/giantswarm-catalog/
```

### KubeLinter

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--kubelinter-config` | string | - | Path to `kube-linter` configuration file. If not set, looks for `.kube-linter.yaml` in chart directory |

#### Example KubeLinter Config

```yaml
checks:
  exclude:
    - run-as-non-root
    - no-read-only-root-fs
```

See [KubeLinter documentation](https://docs.kubelinter.io/) for more options.

## Giant Swarm Validators

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-g`, `--disable-giantswarm-helm-validator` | flag | `false` | Disable Giant Swarm specific validation |
| `-s`, `--disable-strict-giantswarm-validator` | flag | `false` | If set, validation failures produce warnings instead of errors |
| `--giantswarm-validator-ignored-checks` | string | `""` | Comma-separated list of check codes to ignore (e.g., `F0001,C0001`) |

See [Giant Swarm Validators](validators.md) for detailed information about each check.

## Example Configurations

### Minimal Configuration

```yaml
# .abs/main.yaml
chart-dir: ./helm/my-app
```

### Full Configuration for Giant Swarm App Platform

```yaml
# .abs/main.yaml
replace-chart-version-with-git: true
replace-app-version-with-git: true
generate-metadata: true
catalog-base-url: https://giantswarm.github.io/my-catalog/
destination: ./build
ct-config: .circleci/ct-config.yaml
kubelinter-config: .kube-linter.yaml
```

### Local Development Configuration

```yaml
# .abs/main.yaml
chart-dir: ./helm/my-app
destination: ./build
# Disable strict validation during development
disable-strict-giantswarm-validator: true
```

## Running Specific Steps

### Run Only Validation

```bash
python -m app_build_suite --steps validate -c ./helm/my-app
```

### Skip Static Checks

```bash
python -m app_build_suite --skip-steps static_check -c ./helm/my-app
```

### Available Steps

| Step | Description |
|------|-------------|
| `all` | Run all steps (default) |
| `build` | Build the Helm chart package |
| `validate` | Run chart-testing (`ct`) linting |
| `static_check` | Run KubeLinter static analysis |
| `metadata` | Generate App Platform metadata |

