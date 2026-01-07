# App Platform Metadata Generation

App Build Suite can generate metadata files required by the Giant Swarm App Platform. This document explains what metadata is generated, how it's used, and how to configure it.

## Overview

When `--generate-metadata` is enabled, ABS generates additional files that provide rich information about your Helm chart to the App Platform. This metadata enables features like:

- App catalog browsing with detailed information
- Automatic detection of app restrictions
- Documentation links in the UI
- Version tracking and changelog display

## Enabling Metadata Generation

### Configuration

```yaml
# .abs/main.yaml
generate-metadata: true
catalog-base-url: https://giantswarm.github.io/my-catalog/
```

Or via command line:

```bash
python -m app_build_suite \
  --generate-metadata \
  --catalog-base-url https://giantswarm.github.io/my-catalog/ \
  -c ./helm/my-app
```

### Required Options

| Option | Description |
|--------|-------------|
| `--generate-metadata` | Enable metadata generation |
| `--catalog-base-url` | Base URL where the catalog is hosted. **Must end with `/`** |

## Generated Files

When you build a chart named `my-app` version `1.2.3`, ABS creates:

```
build/
├── my-app-1.2.3.tgz              # The chart package
└── my-app-1.2.3.tgz-meta/        # Metadata directory
    ├── main.yaml                  # Primary metadata file
    ├── README.md                  # Copied from chart (if exists)
    └── values.schema.json         # Copied from chart (if exists)
```

### main.yaml Structure

```yaml
chartFile: my-app-1.2.3.tgz
digest: sha256:abc123...
dateCreated: "2024-01-15T10:30:00.000000Z"
chartApiVersion: v2
icon: https://s.giantswarm.io/app-icons/my-app/1/dark.svg
home: https://github.com/giantswarm/my-app

# Optional fields (from Chart.yaml)
upstreamChartURL: https://charts.example.com/my-app
upstreamChartVersion: "1.2.0"
restrictions:
  clusterSingleton: true
  namespaceSingleton: false
  fixedNamespace: kube-system
  gpuInstances: false
  compatibleProviders:
    - aws
    - azure

annotations:
  application.giantswarm.io/readme: https://raw.githubusercontent.com/.../README.md
  application.giantswarm.io/values-schema: https://raw.githubusercontent.com/.../values.schema.json
```

## Chart.yaml Extensions

ABS recognizes special fields in `Chart.yaml` for metadata generation:

### Upstream Chart Information

For charts based on upstream Helm charts:

```yaml
# Chart.yaml
upstreamChartURL: https://charts.bitnami.com/bitnami/nginx
upstreamChartVersion: "15.3.0"
```

**Note:** If `upstreamChartURL` is provided, `upstreamChartVersion` is required.

### App Restrictions

Define deployment restrictions:

```yaml
# Chart.yaml
restrictions:
  # Only one instance per cluster
  clusterSingleton: true
  
  # Only one instance per namespace
  namespaceSingleton: false
  
  # Must be installed in a specific namespace
  fixedNamespace: kube-system
  
  # Requires GPU instances
  gpuInstances: false
  
  # Compatible cloud providers
  compatibleProviders:
    - aws
    - azure
    - gcp
```

## OCI Annotations

ABS automatically generates OCI-compliant annotations in `Chart.yaml`:

```yaml
annotations:
  io.giantswarm.application.metadata: https://catalog.example.com/my-app-1.2.3.tgz-meta/main.yaml
  io.giantswarm.application.readme: https://raw.githubusercontent.com/.../README.md
  io.giantswarm.application.values-schema: https://raw.githubusercontent.com/.../values.schema.json
  io.giantswarm.application.team: my-team
  
  # Restrictions as annotations (for OCI registries)
  io.giantswarm.application.restrictions.cluster-singleton: "true"
  io.giantswarm.application.restrictions.compatible-providers: "aws,azure"
```

### Annotation Format Conversion

ABS handles both annotation formats:

| Input Format | Output Format (OCI) |
|--------------|---------------------|
| `application.giantswarm.io/team` | `io.giantswarm.application.team` |
| `application.giantswarm.io/readme` | `io.giantswarm.application.readme` |

## GitHub URL Generation

When your chart is hosted on GitHub, ABS automatically generates raw content URLs pointing to the exact release version:

```yaml
# Input (Chart.yaml)
home: https://github.com/giantswarm/my-app
sources:
  - https://github.com/giantswarm/my-app

# Generated annotation
io.giantswarm.application.readme: https://raw.githubusercontent.com/giantswarm/my-app/refs/tags/v1.2.3/README.md
```

This ensures that documentation links always point to the correct version.

## Validation Schema

When metadata generation is enabled, ABS uses a custom schema for `Chart.yaml` validation that includes Giant Swarm specific fields:

```yaml
# Validated fields
name: str()
version: str()
apiVersion: str()
description: str()
icon: str(required=False)
home: str(required=False)
upstreamChartURL: str(required=False)
upstreamChartVersion: str(required=False)
restrictions:
  clusterSingleton: bool(required=False)
  namespaceSingleton: bool(required=False)
  fixedNamespace: str(required=False)
  gpuInstances: bool(required=False)
  compatibleProviders: list(str(), required=False)
annotations: map(str(), str(), required=False)
```

## Complete Example

### Chart.yaml

```yaml
apiVersion: v2
name: my-app
version: 1.2.3-dev
appVersion: "1.0.0"
description: My awesome application

home: https://github.com/giantswarm/my-app
icon: https://s.giantswarm.io/app-icons/my-app/1/dark.svg

sources:
  - https://github.com/giantswarm/my-app

maintainers:
  - name: My Team
    email: team@giantswarm.io

annotations:
  application.giantswarm.io/team: "my-team"

# Giant Swarm specific
upstreamChartURL: https://charts.example.com/upstream-app
upstreamChartVersion: "1.0.0"

restrictions:
  clusterSingleton: true
  fixedNamespace: my-app-system
  compatibleProviders:
    - aws
    - azure
```

### .abs/main.yaml

```yaml
generate-metadata: true
catalog-base-url: https://giantswarm.github.io/giantswarm-catalog/
replace-chart-version-with-git: true
replace-app-version-with-git: true
destination: ./build
```

### Build Command

```bash
python -m app_build_suite -c ./helm/my-app
```

### Generated Metadata (main.yaml)

```yaml
chartFile: my-app-1.2.3.tgz
digest: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
dateCreated: "2024-01-15T10:30:00.000000Z"
chartApiVersion: v2
icon: https://s.giantswarm.io/app-icons/my-app/1/dark.svg
home: https://github.com/giantswarm/my-app
upstreamChartURL: https://charts.example.com/upstream-app
upstreamChartVersion: "1.0.0"
restrictions:
  clusterSingleton: true
  fixedNamespace: my-app-system
  compatibleProviders:
    - aws
    - azure
annotations:
  application.giantswarm.io/team: my-team
  application.giantswarm.io/readme: https://raw.githubusercontent.com/giantswarm/my-app/refs/tags/v1.2.3/README.md
  application.giantswarm.io/valuesSchema: https://raw.githubusercontent.com/giantswarm/my-app/refs/tags/v1.2.3/helm/my-app/values.schema.json
```

## Troubleshooting

### "catalog-base-url value should end with a /"

Ensure your URL ends with a trailing slash:

```yaml
# Correct
catalog-base-url: https://example.com/catalog/

# Wrong
catalog-base-url: https://example.com/catalog
```

### "upstreamChartURL is found but upstreamChartVersion is not"

When specifying upstream chart URL, you must also specify the version:

```yaml
upstreamChartURL: https://charts.example.com/app
upstreamChartVersion: "1.0.0"  # Required!
```

### GitHub URLs Show "unknown"

This can happen when:
1. The chart is not in a git repository
2. The `home` or `sources` fields don't point to GitHub
3. The file paths can't be resolved relative to the git root

Ensure your `Chart.yaml` includes valid GitHub URLs in `home` or `sources`.

### Metadata Not Generated

Check that:
1. `--generate-metadata` is enabled
2. `--catalog-base-url` is provided
3. The `metadata` step is not skipped

