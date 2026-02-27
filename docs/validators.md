# Giant Swarm Validators

App Build Suite includes Giant Swarm specific validators that ensure Helm charts comply with company standards. These validators run during the `validate` step.

## Configuration

| Option | Description |
|--------|-------------|
| `--disable-giantswarm-helm-validator` | Disable all Giant Swarm validators |
| `--disable-strict-giantswarm-validator` | Make validation failures non-fatal (warnings only) |
| `--giantswarm-validator-ignored-checks` | Comma-separated list of check codes to ignore |

### Ignoring Specific Checks

```bash
dabs.sh --giantswarm-validator-ignored-checks F0001,C0001 -c ./helm/my-app
```

Or in `.abs/main.yaml`:

```yaml
giantswarm-validator-ignored-checks: F0001,C0001
```

## Available Validators

### F0001: HasValuesSchema

Checks if the chart contains a `values.schema.json` file.

**How to fix:** Create a `values.schema.json` file in your chart root directory.

### C0001: HasTeamLabel

Validates that:
1. The `application.giantswarm.io/team` annotation is present in `Chart.yaml`
2. The annotation value is not empty
3. The team label is properly referenced in `_helpers.tpl` or `_helpers.yaml`

**How to fix:**

1. Add the annotation to `Chart.yaml`:

```yaml
annotations:
  application.giantswarm.io/team: "your-team"
```

2. Reference it in your `_helpers.tpl`:

```gotemplate
application.giantswarm.io/team: {{ index .Chart.Annotations "application.giantswarm.io/team" | quote }}
```

### C0002: IconExists

Checks if the `icon` field is present and not empty in `Chart.yaml`.

**How to fix:** Add an icon URL to your `Chart.yaml`:

```yaml
icon: https://s.giantswarm.io/app-icons/my-app/1/dark.svg
```

### C0003: IconIsAlmostSquare

Validates that the icon has an approximately square aspect ratio (maximum 33% deviation).

**How to fix:** Use an icon with dimensions close to square.

## Check Code Format

- **F** prefix: File system layout checks
- **C** prefix: `Chart.yaml` related checks
