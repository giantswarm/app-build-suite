# Migration Guide

This guide helps you migrate existing Helm chart repositories to use App Build Suite (ABS).

## Why Migrate to ABS?

ABS provides:
- Standardized build process across all Giant Swarm apps
- Automatic metadata generation for the App Platform
- Built-in linting with `ct` and `kube-linter`
- Git-based versioning
- Giant Swarm specific validations

## Migration Steps

### 1. Update CircleCI Configuration

For each `architect/push-to-app-catalog` workflow job, set the executor to `app-build-suite`:

```yaml
# .circleci/config.yml
workflows:
  build:
    jobs:
      - architect/push-to-app-catalog:
          name: push-to-catalog
          context: architect
          executor: app-build-suite  # Add this line
          # ... other options
```

### 2. Create ABS Configuration

Create `.abs/main.yaml` in your repository root:

```yaml
generate-metadata: true
chart-dir: ./helm/your-app-name
destination: ./build
catalog-base-url: https://giantswarm.github.io/your-catalog/
replace-chart-version-with-git: true
```

### 3. Remove Version Placeholders

ABS doesn't support template placeholders like `[[ .Version ]]`. Replace them with actual values.

#### Chart.yaml

**Before:**
```yaml
version: "[[ .Version ]]"
appVersion: "[[ .AppVersion ]]"
```

**After:**
```yaml
# Use a development version, e.g., next minor with -dev suffix
version: 1.3.0-dev
appVersion: 1.3.0-dev
```

Then enable git-based versioning in `.abs/main.yaml`:

```yaml
replace-chart-version-with-git: true
replace-app-version-with-git: true  # Only for Giant Swarm native apps
```

**Note:** For apps wrapping upstream projects, `appVersion` should reflect the upstream version and should NOT be replaced with git version.

#### values.yaml

**Before:**
```yaml
project:
  branch: "[[ .Branch ]]"
  commit: "[[ .SHA ]]"
```

**After:**
Remove these fields or replace with Chart.yaml references in templates:

```gotemplate
# In templates, use:
{{ .Chart.AppVersion }}
```

#### _helpers.tpl

**Before:**
```gotemplate
application.giantswarm.io/branch: {{ .Values.project.branch | quote }}
application.giantswarm.io/commit: {{ .Values.project.commit | quote }}
```

**After:**
```gotemplate
# Option 1: Use AppVersion
application.giantswarm.io/branch: {{ .Chart.AppVersion | replace "#" "-" | replace "/" "-" | replace "." "-" | trunc 63 | trimSuffix "-" | quote }}
application.giantswarm.io/commit: {{ .Chart.AppVersion | quote }}

# Option 2: Remove if not needed
```

#### Image Tags

**Before:**
```yaml
# values.yaml
image:
  tag: "[[ .Version ]]"
```

**After:**
```yaml
# values.yaml
image:
  tag: ""  # Empty, will default to Chart.AppVersion
```

```gotemplate
# _helpers.tpl
{{- define "image.tag" -}}
{{- if .Values.image.tag }}
{{- .Values.image.tag }}
{{- else }}
{{- .Chart.AppVersion }}
{{- end }}
{{- end }}
```

Then use `{{ include "image.tag" . }}` in your templates.

### 4. Add Required Chart.yaml Fields

#### Team Annotation

```yaml
# Chart.yaml
annotations:
  application.giantswarm.io/team: "your-team-name"
```

And reference it in `_helpers.tpl`:

```gotemplate
{{- define "labels.common" -}}
app: {{ include "name" . | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service | quote }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
application.giantswarm.io/team: {{ index .Chart.Annotations "application.giantswarm.io/team" | quote }}
{{- end -}}
```

#### Icon

```yaml
# Chart.yaml
icon: https://s.giantswarm.io/app-icons/your-app/1/dark.svg
```

Icons can be added via the [giantswarm/web-assets](https://github.com/giantswarm/web-assets) repository.

### 5. Create values.schema.json

ABS validates that a `values.schema.json` exists. Create one if missing:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 1
    }
  }
}
```

**Tip:** Use [helm-values-schema-json](https://github.com/losisin/helm-values-schema-json) to generate schemas from your values.yaml.

### 6. Address KubeLinter Issues

KubeLinter checks for Kubernetes best practices. Common issues:

#### Security Context

```yaml
# Before (missing security context)
containers:
  - name: app
    image: myapp:latest

# After
containers:
  - name: app
    image: myapp:latest
    securityContext:
      runAsNonRoot: true
      readOnlyRootFilesystem: true
      allowPrivilegeEscalation: false
```

For exceptions, use annotations:

```yaml
metadata:
  annotations:
    ignore-check.kube-linter.io/run-as-non-root: "Requires root for X functionality"
```

#### Resource Limits

```yaml
containers:
  - name: app
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 512Mi
```

#### Pod Anti-Affinity

For multi-replica deployments:

```yaml
spec:
  replicas: 3
  template:
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - podAffinityTerm:
                labelSelector:
                  matchLabels:
                    {{- include "labels.selector" . | nindent 20 }}
                topologyKey: kubernetes.io/hostname
              weight: 100
```

### 7. Configure Chart Testing (if needed)

For charts with external dependencies, create `.circleci/ct-config.yaml`:

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

### 8. Remove PSP Support (Kubernetes 1.25+)

If your chart includes PodSecurityPolicy resources:

1. Remove PSP resource files
2. Remove associated RBAC rules
3. Remove values:

```yaml
# Remove from values.yaml
global:
  podSecurityStandards:
    enforced: false
```

4. Update `values.schema.json` to remove PSP-related properties

## Testing Your Migration

### Local Testing

```bash
# Using Python directly
uv venv
source .venv/bin/activate
uv sync
python -m app_build_suite -c ./helm/your-app

# Using Docker
./dabs.sh -c ./helm/your-app
```

### Validation Only

```bash
python -m app_build_suite --steps validate -c ./helm/your-app
```

### Static Checks Only

```bash
python -m app_build_suite --steps static_check -c ./helm/your-app
```

## Example Migrations

Reference these PRs for real-world migration examples:

- [app-operator](https://github.com/giantswarm/app-operator/pull/1310)
- [chart-operator](https://github.com/giantswarm/chart-operator/pull/1183)
- [app-admission-controller](https://github.com/giantswarm/app-admission-controller/pull/557)
- [test-app](https://github.com/giantswarm/test-app/pull/10)

## Migration Checklist

- [ ] Updated `.circleci/config.yml` to use `app-build-suite` executor
- [ ] Created `.abs/main.yaml` configuration
- [ ] Removed `[[ .Version ]]` and similar placeholders from Chart.yaml
- [ ] Removed `project.branch` and `project.commit` from values.yaml
- [ ] Added `application.giantswarm.io/team` annotation to Chart.yaml
- [ ] Added team label reference to `_helpers.tpl`
- [ ] Added `icon` field to Chart.yaml
- [ ] Created or updated `values.schema.json`
- [ ] Fixed KubeLinter issues or added exceptions
- [ ] Created `ct-config.yaml` if chart has external dependencies
- [ ] Removed PSP resources (if targeting Kubernetes 1.25+)
- [ ] Tested build locally
- [ ] Verified CI pipeline passes

## Troubleshooting

### "Can't find valid git repository"

Ensure you're running ABS from within a git repository or a subdirectory of one.

### "Team annotation not found"

Add the team annotation to `Chart.yaml`:

```yaml
annotations:
  application.giantswarm.io/team: "your-team"
```

### "values.schema.json not found"

Create a basic schema file. At minimum:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object"
}
```

### KubeLinter Failures

Review the KubeLinter output and either:
1. Fix the issues in your templates
2. Add exceptions with `ignore-check.kube-linter.io/<check-name>` annotations
3. Configure `.kube-linter.yaml` to exclude specific checks globally

### Integration Tests Fail After Migration

If tests fail with newer Kubernetes versions:
1. Check for removed APIs (PSPs, etc.)
2. Update deprecated API versions
3. Review pod security contexts

Debug by re-running the failed CircleCI job with SSH and inspecting the kind cluster.

