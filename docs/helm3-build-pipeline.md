# Helm 3 build engine steps

Helm 3 build pipeline executes in sequence the following set of steps:

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
   This tool runs validation and linting of YAML files included in your chart.
   - config options:
     - `--ct-config`:
                        path to optional `ct`'s tool config file.
     - `--ct-schema`:
                        path to optional `ct` schema file.
4. HelmChartMetadataPreparer: this step is required to gather some data required for chart metadata
   generation.
   - config options:
     - `--generate-metadata`: enable generation of the metadata file for Giant Swarm App Platform.
     - `--catalog-base-url`: Base URL of the catalog in which the app package will be stored in. Should end with a /.

5. HelmChartBuilder: this step does the actual chart build using Helm.
   - config options:
     - `--destination`: path of a directory to store the packaged Helm chart tgz.
6. HelmChartMetadataFinalizer: completes and writes the data gather partially by HelmChartMetadataPreparer.
   - config options: none
7. HelmChartYAMLRestorer: restores chart files, which were changed as part of the build process (ie. by
   HelmGitVersionSetter).
   - config options:
     - `--keep-chart-changes` should the changes made in Chart.yaml be kept
