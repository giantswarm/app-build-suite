VALUES_SCHEMA_JSON = "values.schema.json"
CHART_YAML_APP_VERSION_KEY = "appVersion"
CHART_YAML_CHART_VERSION_KEY = "version"
CHART_YAML = "Chart.yaml"
VALUES_YAML = "values.yaml"
CHART_LOCK = "Chart.lock"
REQUIREMENTS_LOCK = "requirements.lock"
TEMPLATES_DIR = "templates"
HELPERS_YAML = "_helpers.yaml"
HELPERS_TPL = "_helpers.tpl"

# Context keys shared across build steps
context_key_chart_yaml: str = "chart_yaml"
context_key_chart_full_path: str = "chart_full_path"
context_key_chart_file_name: str = "chart_file_name"
context_key_git_version: str = "git_version"
context_key_changes_made: str = "changes_made"
context_key_meta_dir_path: str = "meta_dir_path"
context_key_chart_lock_files_to_restore: str = "chart_lock_files_to_restore"
context_key_original_chart_yaml: str = "original_chart_yaml"

# OCI annotation constants shared across metadata build steps
key_oci_annotation_prefix = "io.giantswarm.application"
annotation_files_map = {
    "./values.schema.json": f"{key_oci_annotation_prefix}.values-schema",
    "../../README.md": f"{key_oci_annotation_prefix}.readme",
}
key_annotation_prefix = "application.giantswarm.io"
