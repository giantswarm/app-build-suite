# How to use app-build-suite to build and optionally test an app

## Preparing tools

To be able to complete this tutorial, you need a few tools:

- `app-build-suite` itself; if you haven't done so already, we're recommending getting the latest version of the `dabs.sh` helper from [releases](https://github.com/giantswarm/app-build-suite/releases)
- for building part
  - [docker](https://docs.docker.com/get-docker/)
- for the testing part
  - a working python environment that you can use to install [pipenv](https://pypi.org/project/pipenv/)
    - if you already have python, it should be enough to run `pip install -U pipenv`
  - to be able to use the shortest path, you also need a working python 3.8 environment
    - to avoid problems like missing the specific python version, we highly recommend
      [`pyenv`](https://github.com/pyenv/pyenv#installation) for managing python environments; once `pyenv` is installed, it's enough to run `pyenv install 3.8.6` to get the python environment you need

## Building your app

The project we'll be working on is in the `examples/tutorial` directory of this
repository. It's content is a ready helm chart that we want to build with `abs`.
To get started, let's switch to that directory and create a `.abs` subdirectory:

```bash
cd examples/tutorial
mkdir .abs

```

Now, we need to prepare a config file for `abs`. In the `.abs` directory we've just
created, we need to create a `main.yaml` file with the following content:

```yaml
replace-chart-version-with-git: true
generate-metadata: true
catalog-base-url: http://localhost/
```

The first line of the config file will set versions in our chart according to ones
detected from the git repository. The other two are needed only if you want to generate
metadata required for advanced features of the Giant Swarm App Platform. If you want
to learn more, check the [more detailed description](pytest-test-pipeline.md).

We're almost ready to go. One technical detail: when running `abs` using
`dabs.sh`, your current working directory is mapped to inside the docker container.
We have configured `abs` to set our chart version using commit information
from `git`, but our current directory doesn't contain any `git` repository - only
the parent directory does. So, the simplest thing we can do is to move up in our
directory structure and invoke `dabs.sh` from a directory where also `git`'s `.git`
directory is. Since we haven't prepared any tests for our app yet, we're also
requesting `abs` to skip any tests:

```bash
$ cd ../../..
$ dabs.sh -c examples/tutorial --skip-steps test_all
2021-04-28 14:48:03,554 __main__ INFO: Starting build with the following options
2021-04-28 14:48:03,554 __main__ INFO:
Command Line Args:   -c examples/tutorial --skip-steps test_all
Config File (/abs/workdir/examples/tutorial/.abs/main.yaml):
  replace-chart-version-with-git:true
  generate-metadata: true
  catalog-base-url:  http://localhost/
Defaults:
  --build-engine:    helm3
  --steps:           ['all']
  --destination:     .
  --app-tests-deploy-namespace:default
  --app-tests-pytest-tests-dir:tests/abs

2021-04-28 14:48:03,554 app_build_suite.build_steps.build_step INFO: Running pre-run step for HelmBuilderValidator
2021-04-28 14:48:03,554 app_build_suite.build_steps.build_step INFO: Running pre-run step for HelmGitVersionSetter
2021-04-28 14:48:03,555 app_build_suite.build_steps.build_step INFO: Running pre-run step for HelmRequirementsUpdater
2021-04-28 14:48:03,555 app_build_suite.build_steps.build_step INFO: Running pre-run step for HelmChartToolLinter
2021-04-28 14:48:03,555 app_build_suite.utils.processes INFO: Running command:
2021-04-28 14:48:03,555 app_build_suite.utils.processes INFO: ct version
2021-04-28 14:48:03,563 app_build_suite.utils.processes INFO: Command executed, exit code: 0.
2021-04-28 14:48:03,563 app_build_suite.build_steps.helm INFO: Metadata generation was requested, changing default validation schema to 'gs_metadata_chart_schema.yaml'
2021-04-28 14:48:03,563 app_build_suite.build_steps.build_step INFO: Running pre-run step for KubeLinter
2021-04-28 14:48:03,563 app_build_suite.utils.processes INFO: Running command:
2021-04-28 14:48:03,563 app_build_suite.utils.processes INFO: kube-linter version
2021-04-28 14:48:03,610 app_build_suite.utils.processes INFO: Command executed, exit code: 0.
2021-04-28 14:48:03,610 app_build_suite.build_steps.build_step INFO: Running pre-run step for HelmChartMetadataPreparer
2021-04-28 14:48:03,620 app_build_suite.build_steps.build_step INFO: Running pre-run step for HelmChartBuilder
2021-04-28 14:48:03,621 app_build_suite.utils.processes INFO: Running command:
2021-04-28 14:48:03,621 app_build_suite.utils.processes INFO: helm version
2021-04-28 14:48:03,667 app_build_suite.utils.processes INFO: Command executed, exit code: 0.
2021-04-28 14:48:03,668 app_build_suite.build_steps.build_step INFO: Running pre-run step for HelmChartMetadataFinalizer
2021-04-28 14:48:03,668 app_build_suite.build_steps.build_step INFO: Running pre-run step for HelmChartYAMLRestorer
2021-04-28 14:48:03,668 app_build_suite.build_steps.build_step INFO: Skipping pre-run step for TestInfoProvider as it was not configured to run.
2021-04-28 14:48:03,668 app_build_suite.build_steps.build_step INFO: Skipping pre-run step for PytestSmokeTestRunner as it was not configured to run.
2021-04-28 14:48:03,668 app_build_suite.build_steps.build_step INFO: Skipping pre-run step for PytestFunctionalTestRunner as it was not configured to run.
2021-04-28 14:48:03,668 app_build_suite.build_steps.build_step INFO: Running build step for HelmBuilderValidator
2021-04-28 14:48:03,668 app_build_suite.build_steps.build_step INFO: Running build step for HelmGitVersionSetter
2021-04-28 14:48:03,681 app_build_suite.build_steps.helm INFO: Replacing 'version' with git version '0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a' in Chart.yaml.
2021-04-28 14:48:03,682 app_build_suite.build_steps.helm INFO: Saving Chart.yaml with version set from git.
2021-04-28 14:48:03,682 app_build_suite.build_steps.build_step INFO: Running build step for HelmRequirementsUpdater
2021-04-28 14:48:03,682 app_build_suite.build_steps.build_step INFO: Running build step for HelmChartToolLinter
2021-04-28 14:48:03,682 app_build_suite.build_steps.helm INFO: Running chart tool linting
2021-04-28 14:48:03,682 app_build_suite.utils.processes INFO: Running command:
2021-04-28 14:48:03,682 app_build_suite.utils.processes INFO: ct lint --validate-maintainers=false --charts=examples/tutorial --chart-yaml-schema=/abs/workdir/app_build_suite/build_steps/../../resources/ct_schemas/gs_metadata_chart_schema.yaml
2021-04-28 14:48:04,718 app_build_suite.utils.processes INFO: Command executed, exit code: 0.
2021-04-28 14:48:04,719 app_build_suite.build_steps.helm INFO: Linting charts...
2021-04-28 14:48:04,719 app_build_suite.build_steps.helm INFO:
2021-04-28 14:48:04,719 app_build_suite.build_steps.helm INFO: ------------------------------------------------------------------------------------------------------------------------
2021-04-28 14:48:04,719 app_build_suite.build_steps.helm INFO:  Charts to be processed:
2021-04-28 14:48:04,719 app_build_suite.build_steps.helm INFO: ------------------------------------------------------------------------------------------------------------------------
2021-04-28 14:48:04,719 app_build_suite.build_steps.helm INFO:  hello-world-app => (version: "0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a", path: "examples/tutorial")
2021-04-28 14:48:04,719 app_build_suite.build_steps.helm INFO: ------------------------------------------------------------------------------------------------------------------------
2021-04-28 14:48:04,720 app_build_suite.build_steps.helm INFO:
2021-04-28 14:48:04,720 app_build_suite.build_steps.helm INFO: Linting chart 'hello-world-app => (version: "0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a", path: "examples/tutorial")'
2021-04-28 14:48:04,720 app_build_suite.build_steps.helm INFO: Validating /abs/workdir/examples/tutorial/Chart.yaml...
2021-04-28 14:48:04,720 app_build_suite.build_steps.helm INFO: Validation success! 👍
2021-04-28 14:48:04,720 app_build_suite.build_steps.helm INFO: ==> Linting examples/tutorial
2021-04-28 14:48:04,720 app_build_suite.build_steps.helm INFO:
2021-04-28 14:48:04,720 app_build_suite.build_steps.helm INFO: 1 chart(s) linted, 0 chart(s) failed
2021-04-28 14:48:04,720 app_build_suite.build_steps.helm INFO: ------------------------------------------------------------------------------------------------------------------------
2021-04-28 14:48:04,721 app_build_suite.build_steps.helm INFO:  ✔︎ hello-world-app => (version: "0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a", path: "examples/tutorial")
2021-04-28 14:48:04,721 app_build_suite.build_steps.helm INFO: ------------------------------------------------------------------------------------------------------------------------
2021-04-28 14:48:04,721 app_build_suite.build_steps.helm INFO: All charts linted successfully
2021-04-28 14:48:04,721 app_build_suite.build_steps.build_step INFO: Running build step for KubeLinter
2021-04-28 14:48:04,721 app_build_suite.build_steps.helm INFO: Running kube-linter tool
2021-04-28 14:48:04,721 app_build_suite.utils.processes INFO: Running command:
2021-04-28 14:48:04,721 app_build_suite.utils.processes INFO: kube-linter lint examples/tutorial --config=examples/tutorial/.kube-linter.yaml
2021-04-28 14:48:04,794 app_build_suite.utils.processes INFO: Command executed, exit code: 0.
2021-04-28 14:48:04,794 app_build_suite.build_steps.build_step INFO: Running build step for HelmChartMetadataPreparer
2021-04-28 14:48:04,803 app_build_suite.build_steps.build_step INFO: Running build step for HelmChartBuilder
2021-04-28 14:48:04,803 app_build_suite.build_steps.helm INFO: Building chart with 'helm package'
2021-04-28 14:48:04,803 app_build_suite.utils.processes INFO: Running command:
2021-04-28 14:48:04,803 app_build_suite.utils.processes INFO: helm package examples/tutorial --destination .
2021-04-28 14:48:04,853 app_build_suite.utils.processes INFO: Command executed, exit code: 0.
2021-04-28 14:48:04,853 app_build_suite.build_steps.helm INFO: Successfully packaged chart and saved it to: /abs/workdir/hello-world-app-0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a.tgz
2021-04-28 14:48:04,853 app_build_suite.build_steps.build_step INFO: Running build step for HelmChartMetadataFinalizer
2021-04-28 14:48:04,865 app_build_suite.build_steps.helm INFO: Metadata file saved to '/abs/workdir/hello-world-app-0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a.tgz-meta/main.yaml'
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Running build step for HelmChartYAMLRestorer
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Skipping build step for TestInfoProvider as it was not configured to run.
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Skipping build step for PytestSmokeTestRunner as it was not configured to run.
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Skipping build step for PytestFunctionalTestRunner as it was not configured to run.
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Running cleanup step for HelmBuilderValidator
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Running cleanup step for HelmGitVersionSetter
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Running cleanup step for HelmRequirementsUpdater
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Running cleanup step for HelmChartToolLinter
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Running cleanup step for KubeLinter
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Running cleanup step for HelmChartMetadataPreparer
2021-04-28 14:48:04,866 app_build_suite.build_steps.build_step INFO: Running cleanup step for HelmChartBuilder
2021-04-28 14:48:04,866 app_build_suite.build_steps.build_step INFO: Running cleanup step for HelmChartMetadataFinalizer
2021-04-28 14:48:04,866 app_build_suite.build_steps.build_step INFO: Running cleanup step for HelmChartYAMLRestorer
2021-04-28 14:48:04,866 app_build_suite.build_steps.helm INFO: Restoring backup Chart.yaml.back to Chart.yaml
```

What happened here? A few things:

- our chart was validated using `ct` and `kube-linter` tools
- version information in our chart was set to `0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a`
- finally our chart was built with Helm

As a result, we have a new helm chart file and metadata files generated for the
App Platform:

```bash
ls -la hello-world-app-0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a.*
-rw-r--r-- 1 piontec piontec 1993 kwi 28 16:48 hello-world-app-0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a.tgz

hello-world-app-0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a.tgz-meta:
total 20
drwxr-xr-x 1 piontec piontec    72 kwi 28 16:48 .
drwxrwxr-x 1 piontec piontec  1168 kwi 28 16:51 ..
-rw-r--r-- 1 piontec piontec  1011 kwi 28 16:48 main.yaml
-rw-rw-r-- 1 piontec piontec 11664 mar  2 14:41 README.md
-rw-rw-r-- 1 piontec piontec   300 paź 21  2020 values.schema.json
```
