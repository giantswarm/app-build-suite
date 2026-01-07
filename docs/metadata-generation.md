# App Platform Metadata Generation

When `--generate-metadata` is enabled, ABS generates metadata files for the Giant Swarm App Platform.

## Enabling Metadata Generation

Add to your `.abs/main.yaml`:

```yaml
generate-metadata: true
catalog-base-url: https://giantswarm.github.io/my-catalog/
```

**Note:** `catalog-base-url` must end with `/`.

## Generated Files

When you build a chart, ABS creates a metadata directory alongside the chart package:

```
build/
├── my-app-1.2.3.tgz              # The chart package
└── my-app-1.2.3.tgz-meta/        # Metadata directory
    ├── main.yaml                  # Primary metadata file
    ├── README.md                  # Copied from chart (if exists)
    └── values.schema.json         # Copied from chart (if exists)
```

## Chart.yaml Extensions

ABS recognizes special fields in `Chart.yaml` for metadata:

### Upstream Chart Information

For charts based on upstream Helm charts:

```yaml
upstreamChartURL: https://charts.bitnami.com/bitnami/nginx
upstreamChartVersion: "15.3.0"
```

**Note:** If `upstreamChartURL` is provided, `upstreamChartVersion` is required.

### App Restrictions

```yaml
restrictions:
  clusterSingleton: true      # Only one instance per cluster
  namespaceSingleton: false   # Only one instance per namespace
  fixedNamespace: kube-system # Must be installed in specific namespace
  gpuInstances: false         # Requires GPU instances
  compatibleProviders:        # Compatible cloud providers
    - aws
    - azure
```

## Validation

When metadata generation is enabled, ABS uses a custom schema for `Chart.yaml` validation that includes Giant Swarm specific fields like `upstreamChartURL`, `upstreamChartVersion`, and `restrictions`.
