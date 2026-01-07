# Giant Swarm Validators

App Build Suite includes a set of Giant Swarm specific validators that ensure Helm charts comply with company standards and best practices. These validators run during the `validate` step of the build pipeline.

## Overview

Giant Swarm validators check for:
- Required files and directory structure
- Proper `Chart.yaml` configuration
- Team ownership labels
- Icon requirements

## Validator Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--disable-giantswarm-helm-validator` | flag | `false` | Disable all Giant Swarm validators |
| `--disable-strict-giantswarm-validator` | flag | `false` | Make validation failures non-fatal (warnings only) |
| `--giantswarm-validator-ignored-checks` | string | `""` | Comma-separated list of check codes to ignore |

### Ignoring Specific Checks

To ignore specific checks, use the check code:

```bash
python -m app_build_suite --giantswarm-validator-ignored-checks F0001,C0001 -c ./helm/my-app
```

Or in your `.abs/main.yaml`:

```yaml
giantswarm-validator-ignored-checks: F0001,C0001
```

## Available Validators

### F0001: HasValuesSchema

**Category:** File System Layout

**Description:** Checks if the chart contains a `values.schema.json` file.

**Why it matters:** A JSON schema for values ensures that users provide correct configuration and helps with IDE autocompletion.

**How to fix:**
1. Create a `values.schema.json` file in your chart root directory
2. Define the schema for all values in your `values.yaml`

**Example `values.schema.json`:**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 1,
      "description": "Number of replicas"
    },
    "image": {
      "type": "object",
      "properties": {
        "repository": {
          "type": "string"
        },
        "tag": {
          "type": "string"
        }
      },
      "required": ["repository"]
    }
  }
}
```

---

### C0001: HasTeamLabel

**Category:** Chart.yaml

**Description:** Validates that:
1. The `application.giantswarm.io/team` (or `io.giantswarm.application.team`) annotation is present in `Chart.yaml`
2. The annotation value is not empty
3. The team label is properly referenced in the chart's `_helpers.tpl` or `_helpers.yaml`

**Why it matters:** Team labels enable proper ownership tracking and help with routing alerts and issues to the responsible team.

**How to fix:**

1. Add the annotation to `Chart.yaml`:

```yaml
annotations:
  application.giantswarm.io/team: "my-team-name"
```

Or using the OCI format:

```yaml
annotations:
  io.giantswarm.application.team: "my-team-name"
```

2. Reference the annotation in your `_helpers.tpl`:

```gotemplate
{{- define "labels.common" -}}
app: {{ include "name" . | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service | quote }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
application.giantswarm.io/team: {{ index .Chart.Annotations "application.giantswarm.io/team" | quote }}
{{- end -}}
```

Or with a default fallback:

```gotemplate
application.giantswarm.io/team: {{ index .Chart.Annotations "application.giantswarm.io/team" | default "my-team" | quote }}
```

---

### C0002: IconExists

**Category:** Chart.yaml

**Description:** Checks if the `icon` field is present and not empty in `Chart.yaml`.

**Why it matters:** Icons are displayed in the Giant Swarm App Platform UI and help users identify applications.

**How to fix:**

Add an icon URL to your `Chart.yaml`:

```yaml
icon: https://s.giantswarm.io/app-icons/giantswarm/1/dark.svg
```

Icons can be added to the [giantswarm/web-assets](https://github.com/giantswarm/web-assets) repository.

---

### C0003: IconIsAlmostSquare

**Category:** Chart.yaml

**Description:** Validates that the icon has an approximately square aspect ratio (maximum 33% deviation from 1:1).

**Why it matters:** Non-square icons may be cropped or stretched when displayed in the UI.

**How to fix:**

1. Use an icon with dimensions close to square (e.g., 128x128, 256x256)
2. SVG icons are recommended as they scale better
3. Maximum allowed deviation: 33% (e.g., 100x75 would fail, 100x80 would pass)

## Check Code Format

Check codes follow the pattern `X0000`:
- **F** prefix: File system layout and structure checks
- **C** prefix: `Chart.yaml` related checks

## Example: Configuring All Validators

```yaml
# .abs/main.yaml

# Enable metadata generation (required for some validators)
generate-metadata: true
catalog-base-url: https://giantswarm.github.io/my-catalog/

# Validator configuration
# disable-giantswarm-helm-validator: false  # Keep validators enabled
# disable-strict-giantswarm-validator: false  # Keep strict mode

# Ignore specific checks if needed (during migration)
# giantswarm-validator-ignored-checks: F0001
```

## Troubleshooting

### "Team annotation not found"

Ensure your `Chart.yaml` contains:

```yaml
annotations:
  application.giantswarm.io/team: "your-team"
```

### "Expected team label not found in _helpers.tpl"

The validator expects a specific format in your helpers file. Make sure you have:

```gotemplate
application.giantswarm.io/team: {{ index .Chart.Annotations "application.giantswarm.io/team" | quote }}
```

### "Icon validation failed"

1. Ensure the icon URL is accessible
2. Check that the icon is a valid image format (PNG, SVG, etc.)
3. Verify the aspect ratio is close to square

### Temporarily Bypassing Validators

During migration or development, you can:

1. Disable strict mode to get warnings instead of errors:
   ```bash
   python -m app_build_suite --disable-strict-giantswarm-validator -c ./helm/my-app
   ```

2. Ignore specific checks:
   ```bash
   python -m app_build_suite --giantswarm-validator-ignored-checks C0002,C0003 -c ./helm/my-app
   ```

3. Disable all Giant Swarm validators:
   ```bash
   python -m app_build_suite --disable-giantswarm-helm-validator -c ./helm/my-app
   ```

