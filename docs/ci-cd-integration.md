# CI/CD Integration

App Build Suite (ABS) is designed to integrate seamlessly with CI/CD pipelines. This document covers integration with GitHub Actions and CircleCI.

## Docker Image

ABS is distributed as a Docker image available at:

```
gsoci.azurecr.io/giantswarm/app-build-suite:latest
```

For a specific version:
```
gsoci.azurecr.io/giantswarm/app-build-suite:v1.5.1
```

### Image Variants

| Image Tag | Description |
|-----------|-------------|
| `latest` | Latest stable release |
| `vX.Y.Z` | Specific version |
| `vX.Y.Z-circleci` | CircleCI-optimized variant with additional tools |

The CircleCI variant includes additional tools:
- GitHub CLI (`gh`)
- `gh-token` for GitHub App authentication
- `curl` and `jq`

## GitHub Actions

### Using the Reusable Workflow

ABS provides a reusable workflow for publishing apps to GitHub Pages-based app catalogs.

**In your repository's workflow file:**

```yaml
name: Build and Publish

on:
  push:
    tags:
      - 'v*'

jobs:
  push-to-catalog:
    uses: giantswarm/app-build-suite/.github/workflows/push-to-app-catalog.yaml@main
    with:
      app_catalog: my-app-catalog
      chart: my-app
      organization: my-org
    secrets:
      envPAT: ${{ secrets.PAT_TOKEN }}
```

### Workflow Inputs

| Input | Required | Description |
|-------|----------|-------------|
| `app_catalog` | Yes | Name of the app catalog repository |
| `chart` | Yes | Name of the chart in the `helm/` directory |
| `organization` | Yes | GitHub organization name |

### Workflow Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `envPAT` | Yes | GitHub Personal Access Token with write access to the catalog repository |

### Custom GitHub Actions Workflow

For more control, use the Docker image directly:

```yaml
name: Build Chart

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Required for git version detection

      - name: Build with ABS
        uses: docker://gsoci.azurecr.io/giantswarm/app-build-suite:latest
        with:
          args: >-
            --chart-dir helm/my-app
            --destination ./build
            --replace-chart-version-with-git
            --generate-metadata
            --catalog-base-url https://my-org.github.io/my-catalog/

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: chart
          path: build/
```

## CircleCI

### Using architect-orb

The recommended way to use ABS in CircleCI is through the `architect-orb`:

```yaml
version: 2.1

orbs:
  architect: giantswarm/architect@6.8.0

workflows:
  build:
    jobs:
      - architect/push-to-app-catalog:
          name: push-to-catalog
          context: architect
          executor: app-build-suite
          app_catalog: my-catalog
          app_catalog_test: my-catalog-test
          chart: my-app
          filters:
            branches:
              ignore:
                - main
            tags:
              only: /^v.*/
```

### Executor Options

| Executor | Description |
|----------|-------------|
| `app-build-suite` | Standard ABS executor |
| `architect` | Legacy architect executor |

### Configuration File

Create `.abs/main.yaml` in your repository:

```yaml
generate-metadata: true
chart-dir: ./helm/my-app
destination: ./build
catalog-base-url: https://giantswarm.github.io/my-catalog/
replace-chart-version-with-git: true
```

### Custom CircleCI Job

For custom pipelines:

```yaml
version: 2.1

jobs:
  build-chart:
    docker:
      - image: gsoci.azurecr.io/giantswarm/app-build-suite:v1.5.1-circleci
    steps:
      - checkout
      - run:
          name: Build chart
          command: |
            python -m app_build_suite \
              --chart-dir helm/my-app \
              --destination ./build \
              --replace-chart-version-with-git \
              --generate-metadata \
              --catalog-base-url https://example.com/catalog/
      - persist_to_workspace:
          root: .
          paths:
            - build/

workflows:
  build:
    jobs:
      - build-chart
```

### Chart Testing Configuration

For charts with dependencies, create `.circleci/ct-config.yaml`:

```yaml
---
chart-repos:
  - kubernetes-charts=https://charts.helm.sh/stable
  - giantswarm-catalog=https://giantswarm.github.io/giantswarm-catalog/
```

Reference it in `.abs/main.yaml`:

```yaml
ct-config: .circleci/ct-config.yaml
```

## Local Development with dabs.sh

For local development, use the `dabs.sh` wrapper script:

```bash
# Download from releases
curl -LO https://github.com/giantswarm/app-build-suite/releases/latest/download/dabs.sh
chmod +x dabs.sh

# Run ABS
./dabs.sh -c helm/my-app
```

### Custom Docker Tag

```bash
DABS_TAG=v1.5.1 ./dabs.sh -c helm/my-app
```

## Running Without Docker

For CI environments with Python available:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/giantswarm/app-build-suite.git
cd app-build-suite
uv venv
source .venv/bin/activate
uv sync

# Run ABS
python -m app_build_suite -c /path/to/your/chart
```

**Note:** This requires `helm`, `ct`, and `kube-linter` binaries to be installed.

## Environment Variables in CI

All configuration options can be set via environment variables:

```yaml
# CircleCI example
jobs:
  build:
    docker:
      - image: gsoci.azurecr.io/giantswarm/app-build-suite:latest
    environment:
      ABS_CHART_DIR: ./helm/my-app
      ABS_GENERATE_METADATA: "true"
      ABS_CATALOG_BASE_URL: "https://example.com/catalog/"
      ABS_REPLACE_CHART_VERSION_WITH_GIT: "true"
```

## Best Practices

### 1. Always Fetch Full Git History

```yaml
# GitHub Actions
- uses: actions/checkout@v4
  with:
    fetch-depth: 0

# CircleCI - done by default
```

### 2. Use Specific Image Versions

Avoid using `latest` in production pipelines:

```yaml
# Good
image: gsoci.azurecr.io/giantswarm/app-build-suite:v1.5.1

# Avoid in production
image: gsoci.azurecr.io/giantswarm/app-build-suite:latest
```

### 3. Cache Dependencies

For charts with dependencies:

```yaml
# CircleCI
- restore_cache:
    keys:
      - helm-deps-v1-{{ checksum "helm/my-app/Chart.lock" }}
```

### 4. Separate Build and Test Pipelines

Use ABS for building, [app-test-suite](https://github.com/giantswarm/app-test-suite) for testing:

```yaml
workflows:
  build-and-test:
    jobs:
      - build-with-abs
      - integration-tests:
          requires:
            - build-with-abs
```

## Troubleshooting CI/CD

### Git Version Detection Fails

Ensure full git history is available:
```yaml
fetch-depth: 0
```

### Permission Denied Errors

The container runs as root by default but respects `USE_UID` and `USE_GID` environment variables:

```yaml
environment:
  USE_UID: "1000"
  USE_GID: "1000"
```

### Chart Dependencies Not Found

Create a `ct-config.yaml` with the required Helm repositories:

```yaml
chart-repos:
  - repo-name=https://repo-url
```

### Metadata URL Generation Issues

Ensure `catalog-base-url` ends with a `/`:

```yaml
# Correct
catalog-base-url: https://example.com/catalog/

# Wrong
catalog-base-url: https://example.com/catalog
```

