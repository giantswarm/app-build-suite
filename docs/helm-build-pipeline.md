# Helm build engine steps

Helm build pipeline executes in sequence the following set of steps:

1. HelmBuilderValidator: a simple step that checks if the build folder contains a Helm chart.
   - config options: none
2. HelmGitVersionSetter: when enabled, this step will set `version` and/or `appVersion` in the `Chart.yaml`
   of your helm chart to a version value based of your last commit hash and tag in a git repo. For this
   step to work, the chart or chart's parent directory must contain valid git repo (`.git/`).
   - config options:
     - `--replace-app-version-with-git`:
                        should the `appVersion` in `Chart.yaml` be replaced by a tag and hash from git
     - `--replace-chart-version-with-git`:
                        should the `version` in `Chart.yaml  be replaced by a tag and hash from git
3. HelmChartToolLinter: this step runs the [`ct`](https://github.com/helm/chart-testing) (aka. `chart-testing`)
   This tool runs validation and linting of YAML files included in your chart. The tool is configurable on its own:
   [config reference](https://github.com/helm/chart-testing#configuration).
   - config options:
     - `--ct-config`:
                        path to optional `ct`'s tool config file.
     - `--ct-schema`:
                        path to optional `ct` schema file.
4. KubeLinter: this step runs [kube-linter](https://docs.kubelinter.io/) static chart verification tool.
   Make sure to check [kube-linter configuration docs](https://docs.kubelinter.io/#/configuring-kubelinter)
   to learn how to tune the verification to your taste or even
   [disable it completely](https://docs.kubelinter.io/#/configuring-kubelinter?id=disable-all-default-checks).
   If you don't pass an explicit path to `kube-linter`'s config file with option `--kubelinter-config`,
   `abs` will check if the file `.kube-linter.yaml` file exists in the
   chart's main directory. If it does, it will be passed as a command line option to `kube-linter`. If it doesn't,
   `kube-linter` will run with default configuration.
   - config options:
     - `--kubelinter-config`: path to optional 'kube-linter' config file.
5. HelmChartMetadataPreparer: this step is required to gather some data required for chart metadata
   generation.
   - config options:
     - `--generate-metadata`: enable generation of the metadata file for Giant Swarm App Platform.
     - `--catalog-base-url`: Base URL of the catalog in which the app package will be stored in. Should end with a /.

6. HelmChartBuilder: this step does the actual chart build using Helm.
   - config options:
     - `--destination`: path of a directory to store the packaged Helm chart tgz.
7. HelmChartMetadataFinalizer: completes and writes the data gather partially by HelmChartMetadataPreparer.
   - config options: none
8. HelmChartYAMLRestorer: restores chart files, which were changed as part of the build process (ie. by
   HelmGitVersionSetter).
   - config options:
     - `--keep-chart-changes` should the changes made in Chart.yaml be kept
9. GiantSwarmHelmValidator: runs simple validation rules against the chart source files. Checks for rules we want
   to enforce as company policy.
   Currently, supports the following checks
   ([have a look at the code for details](../app_build_suite/build_steps/giant_swarm_validators/helm.py):
   - `HasValuesSchema` - checks if the `values.schema.json` file is present,
   - `HasTeamLabel` - a bit naive check if the team annotation is present (it only checks for the correct definition
     in `Chart.yaml` and then if the `_templates.yaml` is present and the recommended label is there). Check
     [the example](../examples/apps/hello-world-app/templates/_helpers.yaml) here.

   Available config options:
     - `--enable-giantswarm-helm-validator` - enabled by default, can disable the whole module,
     - `--enable-strict-giantswarm-validator` - true by default, it means the build will fail if any validation
     rule fails,
     - `--giantswarm-validator-ignored-checks` - each check has its own ID which is printed during build; if you
     want to ignore a subset of checks, put a comma separated list here.
