# Configuration Reference

For the most up-to-date and complete list of configuration options, run:

```bash
dabs.sh --help
```

Or if running locally with Python:

```bash
python -m app_build_suite --help
```

## Configuration Methods

ABS supports three configuration methods, listed in order of priority (highest to lowest):

1. **Command line arguments** - Highest priority, overrides all other methods
2. **Environment variables** - All options can be set via environment variables with `ABS_` prefix
3. **Config file** - Located at `.abs/main.yaml` in your chart directory

### Config File Location

ABS looks for configuration files in this order:
1. `<chart-dir>/.abs/main.yaml` (or `.yml`)
2. `<current-dir>/.abs/main.yaml` (or `.yml`)

### Config File Format

Options in the config file use the same names as command line arguments, without the leading `--`:

```yaml
# .abs/main.yaml
replace-chart-version-with-git: true
generate-metadata: true
catalog-base-url: https://giantswarm.github.io/my-catalog/
```

### Environment Variables

All options can be set via environment variables by:
1. Converting the option name to uppercase
2. Replacing dashes with underscores
3. Adding the `ABS_` prefix

Example: `--replace-chart-version-with-git` → `ABS_REPLACE_CHART_VERSION_WITH_GIT=true`

## Common Configuration Examples

### Basic Build

```yaml
# .abs/main.yaml
chart-dir: ./helm/my-app
destination: ./build
```

### Build with Git Versioning

```yaml
# .abs/main.yaml
replace-chart-version-with-git: true
```

### Full Giant Swarm App Platform Configuration

```yaml
# .abs/main.yaml
replace-chart-version-with-git: true
generate-metadata: true
catalog-base-url: https://giantswarm.github.io/giantswarm-catalog/
destination: ./build
```

## Running Specific Steps

You can run a subset of the build pipeline using `--steps` or `--skip-steps`:

```bash
# Run only validation
dabs.sh --steps validate -c ./helm/my-app

# Skip static checks
dabs.sh --skip-steps static_check -c ./helm/my-app
```

Available steps: `all`, `build`, `validate`, `static_check`, `metadata`
