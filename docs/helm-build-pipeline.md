# Helm build engine steps

Helm build pipeline executes in sequence the following set of steps:

1. HelmBuilderValidator: validates that the build folder contains a Helm chart and that the chart name
   is valid.
   - Checks for presence of `Chart.yaml` and `values.yaml` files
   - Validates that the `name` field in `Chart.yaml` complies with
     [RFC 1123](https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-label-names) DNS label rules,
     which is required for Kubernetes compatibility. The name must:
     - be at most 63 characters long,
     - start with a lowercase alphanumeric character,
     - end with a lowercase alphanumeric character,
     - contain only lowercase alphanumeric characters and hyphens (`-`).

     This validator detects Unicode look-alike characters (e.g., en-dash `–`, em-dash `—`, minus sign `−`)
     that visually resemble ASCII hyphen but are invalid. Error messages include exact character positions
     to help locate issues.
   - config options: none
2. HelmGitVersionSetter: when enabled, this step will set `version` and/or `appVersion` in the `Chart.yaml`
   of your helm chart to a version value based of your last commit hash and tag in a git repo. For this
   step to work, the chart or chart's parent directory must contain valid git repo (`.git/`).
   - config options:
     - `--replace-app-version-with-git`:
                        should the `appVersion` in `Chart.yaml` be replaced by a tag and hash from git
     - `--replace-chart-version-with-git`:
                        should the `version` in `Chart.yaml  be replaced by a tag and hash from git
3. HelmHomeUrlSetter: automatically sets the `home` field in `Chart.yaml` to the git remote URL.
   This ensures the home URL always points to the correct GitHub repository. Enabled by default.
   - Converts SSH URLs (e.g., `git@github.com:org/repo.git`) to HTTPS format
   - GitHub repositories only (non-GitHub remotes are silently skipped)
   - Uses the 'origin' remote
   - Adds `home` field if missing, updates if present
   - config options:
     - `--disable-home-url-auto-update`: disable automatic setting of home URL from git remote
4. GiantSwarmHelmValidator: runs simple validation rules against the chart source files. Checks for rules we want
   to enforce as company policy.
   Currently, supports the following checks
   ([have a look at the code for details](../app_build_suite/build_steps/giant_swarm_validators/)):
   - `F0001` `HasValuesSchema` - checks if the `values.schema.json` file is present.
   - `C0001` `HasTeamLabel` - a bit naive check if the team annotation is present (it only checks for the correct definition
     in `Chart.yaml` and then if the `_templates.yaml` is present and the recommended label is there) or is not empty. Check
     [the example](../examples/apps/hello-world-app/templates/_helpers.yaml) here.
   - `C0002` `IconExists` - checks if the `icon` field is present in `Chart.yaml` and is not empty.
   - `C0003` `IconIsAlmostSquare` - validates that the icon image is close to a square shape (max 33% aspect ratio deviation).
   - `C0004` `HomeUrlMatchesGitRemote` - validates that the `home` field in `Chart.yaml` matches the git remote URL.

   Available config options:
     - `--disable-giantswarm-helm-validator` - enabled by default, can disable the whole module,
     - `--disable-strict-giantswarm-validator` - enabled by default, it means the build will fail if any validation
     rule fails; if disabled, build won't fail even if rules will,
     - `--giantswarm-validator-ignored-checks` - each check has its own ID which is printed during build; if you
     want to ignore a subset of checks, put a comma separated list here.
5. HelmChartToolLinter: this step runs the [`ct`](https://github.com/helm/chart-testing) (aka. `chart-testing`)
   This tool runs validation and linting of YAML files included in your chart. The tool is configurable on its own:
   [config reference](https://github.com/helm/chart-testing#configuration).
   - config options:
     - `--ct-config`:
                        path to optional `ct`'s tool config file.
     - `--ct-schema`:
                        path to optional `ct` schema file.
   If your chart is using external chart repositories for stuff like subcharts or dependencies, you might need
   to configure `ct` to point to them: set `ct-config` to something like `./ct-config.yaml`, then create this
   file and set content to (example for external "bitnami" chart repo):

   ```yaml
   ---
   chart-repos:
     - bitnami=https://charts.bitnami.com/bitnami
   ```

6. KubeLinter: this step runs [kube-linter](https://docs.kubelinter.io/) static chart verification tool.
   Make sure to check [kube-linter configuration docs](https://docs.kubelinter.io/#/configuring-kubelinter)
   to learn how to tune the verification to your taste or even
   [disable it completely](https://docs.kubelinter.io/#/configuring-kubelinter?id=disable-all-default-checks).
   If you don't pass an explicit path to `kube-linter`'s config file with option `--kubelinter-config`,
   `abs` will check if the file `.kube-linter.yaml` file exists in the
   chart's main directory. If it does, it will be passed as a command line option to `kube-linter`. If it doesn't,
   `kube-linter` will run with default configuration.
   - config options:
     - `--kubelinter-config`: path to optional 'kube-linter' config file.
7. HelmChartMetadataPreparer: this step is required to gather some data required for chart metadata
   generation.
   - config options:
     - `--generate-metadata`: enable generation of the metadata file for Giant Swarm App Platform.
     - `--catalog-base-url`: Base URL of the catalog in which the app package will be stored in. Should end with a /.
   When metadata generation is enabled, the annotations for `application.giantswarm.io/readme` and
   `application.giantswarm.io/values-schema` are automatically rewritten to point directly to the
   files in the chart's GitHub repository using the chart version tag so that published annotations
   always reference the exact release content.

8. HelmChartBuilder: this step does the actual chart build using Helm.
   - config options:
     - `--destination`: path of a directory to store the packaged Helm chart tgz.
9. HelmChartMetadataFinalizer: completes and writes the data gather partially by HelmChartMetadataPreparer.
   - config options: none
10. HelmChartYAMLRestorer: restores chart files, which were changed as part of the build process (ie. by
    HelmGitVersionSetter or HelmHomeUrlSetter).

    - config options:
      - `--keep-chart-changes` should the changes made in Chart.yaml be kept
