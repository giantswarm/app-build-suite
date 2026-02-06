# CI/CD Integration

App Build Suite (ABS) integrates with CircleCI through the `architect-orb`. This is the supported and recommended way to use ABS in CI/CD pipelines.

## CircleCI with architect-orb

### Basic Setup

Use the `architect/push-to-app-catalog` job with the `app-build-suite` executor:

```yaml
# .circleci/config.yml
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

### Configuration File

Create `.abs/main.yaml` in your repository:

```yaml
generate-metadata: true
chart-dir: ./helm/my-app
destination: ./build
catalog-base-url: https://giantswarm.github.io/my-catalog/
replace-chart-version-with-git: true
```

### Chart Testing Configuration

For charts with external dependencies, create a chart-testing config file:

```yaml
# .circleci/ct-config.yaml
---
chart-repos:
  - giantswarm-catalog=https://giantswarm.github.io/giantswarm-catalog/
```

Reference it in `.abs/main.yaml`:

```yaml
ct-config: .circleci/ct-config.yaml
```

## Local Development

For local development, use the `dabs.sh` wrapper script:

```bash
# Download from releases
curl -LO https://github.com/giantswarm/app-build-suite/releases/latest/download/dabs.sh
chmod +x dabs.sh

# Run ABS
./dabs.sh -c helm/my-app
```

### Using a Specific Version

```bash
DABS_TAG=v1.5.1 ./dabs.sh -c helm/my-app
```

## GitHub Action

A reusable GitHub Action workflow is available for publishing apps to GitHub Pages-based app catalogs. See the [push-to-app-catalog workflow](.github/workflows/push-to-app-catalog.yaml) for details.

## Troubleshooting

### Git Version Detection Fails

Ensure full git history is available. In CircleCI this is done by default, but other CI systems may require explicit configuration.

### Chart Dependencies Not Found

Create a `ct-config.yaml` with the required Helm repositories and reference it in your ABS configuration.

### Metadata URL Issues

Ensure `catalog-base-url` ends with a trailing `/`:

```yaml
# Correct
catalog-base-url: https://example.com/catalog/

# Wrong
catalog-base-url: https://example.com/catalog
```
