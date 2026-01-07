# Migration Guide

This guide helps you migrate existing Helm chart repositories to use App Build Suite (ABS).

## Migration Steps

### 1. Update CircleCI Configuration

Set the executor to `app-build-suite` in your workflow:

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

Create `.abs/main.yaml`:

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

Remove project placeholders:

```yaml
# Remove this
project:
  branch: "[[ .Branch ]]"
  commit: "[[ .SHA ]]"
```

### 4. Add Required Chart.yaml Fields

#### Team Annotation

```yaml
annotations:
  application.giantswarm.io/team: "your-team-name"
```

Reference it in `_helpers.tpl`:

```gotemplate
application.giantswarm.io/team: {{ index .Chart.Annotations "application.giantswarm.io/team" | quote }}
```

#### Icon

```yaml
icon: https://s.giantswarm.io/app-icons/your-app/1/dark.svg
```

### 5. Create values.schema.json

ABS validates that a `values.schema.json` exists. Create one if missing.

### 6. Address KubeLinter Issues

KubeLinter checks for Kubernetes best practices. For exceptions, use annotations:

```yaml
metadata:
  annotations:
    ignore-check.kube-linter.io/run-as-non-root: "Requires root for X functionality"
```

### 7. Configure Chart Testing (if needed)

For charts with external dependencies:

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

## Testing Your Migration

### Local Testing

```bash
./dabs.sh -c ./helm/your-app
```

### Validation Only

```bash
./dabs.sh --steps validate -c ./helm/your-app
```

## Example Migrations

- [app-operator#1310](https://github.com/giantswarm/app-operator/pull/1310)
- [chart-operator#1183](https://github.com/giantswarm/chart-operator/pull/1183)
- [app-admission-controller#557](https://github.com/giantswarm/app-admission-controller/pull/557)

## Migration Checklist

- [ ] Updated `.circleci/config.yml` to use `app-build-suite` executor
- [ ] Created `.abs/main.yaml` configuration
- [ ] Removed `[[ .Version ]]` placeholders from Chart.yaml
- [ ] Removed `project.branch` and `project.commit` from values.yaml
- [ ] Added `application.giantswarm.io/team` annotation to Chart.yaml
- [ ] Added team label reference to `_helpers.tpl`
- [ ] Added `icon` field to Chart.yaml
- [ ] Created `values.schema.json`
- [ ] Created `ct-config.yaml` if chart has external dependencies
- [ ] Tested build locally with `dabs.sh`
