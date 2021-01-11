[![build](https://circleci.com/gh/giantswarm/app-build-suite.svg?style=svg)](https://circleci.com/gh/giantswarm/app-build-suite)
[![codecov](https://codecov.io/gh/giantswarm/app-build-suite/branch/master/graph/badge.svg)](https://codecov.io/gh/giantswarm/app-build-suite)
[![Apache License](https://img.shields.io/badge/license-apache-blue.svg)](https://pypi.org/project/pytest-helm-charts/)

# app-build-suite
A tool to build and test apps for Giant Swarm App Platform.

This tool is development and CI/CD tool that allows you to:

- build your helm chart
  - do some simple variable replacements before building the chart
  - linting chart's source code
  - generating actual chart archive
  - generating App Platform specific metadata
- test your chart after building
  - run your tests of different kind using [`pytest`](https://docs.pytest.org/en/stable/) and
    [`pytest-helm-charts`](https://github.com/giantswarm/pytest-helm-charts)

---
*Big fat warning* This tool is available as a development version!
---

## How to use app-build-suite

### Installation

`abs` is distributed as a docker image, so the easiest way to install and use it is to get our `dabs.sh`
script, which is a wrapper script to make launching the docker image easier.

Alternatively, you can just checkout this repository and build the docker image yourself by running:

```bash
make docker-build
```

### Getting started

Executing `dabs.sh` is the most straight forward way to run `app-build-suite`.
For example, for our sample chart present in this repository in `examples/apps/hello-world-app`, run:

```bash
dabs.sh -c examples/apps/hello-world-app --skip-steps test_all
```

Please note that this command skips all the test steps and runs only the actual chart build steps. If you want
to run tests as well, you need to provide a cluster to run them on. For example, you can use a cluster
of type `external`, which is a cluster you provide externally to the `abs` tool. If you have `kind`, you can do it
like this:

```bash
kind create cluster
kind get kubeconfig > ./kube.config
```

Then you can configure `abs` to run `functional` tests on top of that kind cluster:

```bash
dabs.sh -c examples/apps/hello-world-app \
  --smoke-tests-cluster-type external \
  --functional-tests-cluster-type external \
  --external-cluster-kubeconfig-path kube.config \
  --external-cluster-type kind \
  --external-cluster-version "1.19.0" \
  --destination build
```

### Usage

Please run:

```bash
dabs.sh -h
```

to get help about all the available config options.

## How does it work

This tool works by executing a series of so called `Build Steps`. Each build step is configurable
(run `./dabs.sh -h` to check), but also you can skip any step provided or just run only a subset of all steps.
This idea is fundamental for integrating `abs` with other workflows, like in the CI/CD system or
on your local machine. Check `dabs.sh -h` output for step names available to `--steps` and `--skip-steps`
flags.

To skip or include multiple step names, separate them with space, like in this example:

```bash
dabs.sh -c examples/apps/hello-world-app --skip-steps test_unit test_performance
```

## Detailed execution steps

`abs` is composed of two main pipelines: *build* and *test*. Each of them is composed of steps.
When `abs` runs, it executes all the steps from the *build* pipeline and then from the *test* pipeline.
Config options can be used to disable/enable any specific build steps.

Please check below for available build pipelines and steps. Each step offers some config options,
you can check them by running `dabs.sh -h`.

### Build pipelines

Currently, only one build pipeline is supported. It is based on `helm 3`.

#### Helm 3 build engine steps

Helm 3 build pipeline executes in sequence the following set of steps:

1. HelmBuilderValidator: a simple step that checks if the build folder contains a Helm chart
1. HelmGitVersionSetter: when enabled, this step will set `version` and/or `appVersion` in the `Chart.yaml`
   of your helm chart to a version value based of your last commit hash and tag in a git repo. For this
   step to work, the chart or chart's parent directory must contain valid git repo (`.git/`).
1. HelmChartToolLinter: this step runs the [`ct`](https://github.com/helm/chart-testing) (aka. `chart-testing`)
   This tool runs validation and linting of YAML files included in your chart.
1. HelmChartMetadataPreparer: this step is required to gather some data required for chart metadata
   generation.
1. HelmChartBuilder: this step does the actual chart build using Helm.
1. HelmChartMetadataFinalizer: completes and writes the data gather partially by HelmChartMetadataPreparer.
1. HelmChartYAMLRestorer: restores chart files, which were changed as part of the build process (ie. by
   HelmGitVersionSetter).

### Test pipelines

After your app artifact is built (your chart when using Helm build engine pipeline), `abs` can run
tests for it for you. There are a few assumptions related to how testing invoked by `abs` works.

First, we assume that each test framework that you can use for developing tests for your app can
label the tests and run only the set of tests labelled. `abs` expects all tests to have at least one
of the following labels: `smoke`, `functional`.

The idea is that `abs` invokes first the testing framework with `smoke` filter, so that only smoke tests
are invoked. Smoke tests are expected to be very basic and short-lived, so they provide an immediate
feedback if something is wrong and there's no point in running more advanced (and time and resource
consuming tests). Only if `smoke` tests are OK, `functional` tests are invoked to check if the application
works as expected. In the future, we want to introduce `performance` tests for checking for expected
performance results in a well-defined environment and `compatibility` tests for checking strict
compatibility of your app with a specific platform release.

Another important concept is that each type of tests can be run on a different type of Kubernetes cluster.
That way, we want to make a test flow that uses "fail fast" principle: if your tests are going to fail,
make them fail as soon as possible, without creating "heavy" clusters or running "heavy" tests. As an example,
our default config should be something like this:

1. Run `smoke` tests on `kind` cluster. Fail if any test fails.
2. Run `functional` tests on `kind` cluster. We might reuse the `kind` cluster from the step above. But
   we might also need a more powerful setup to be able to test all the `functional` scenarios, so we might
   request a real AWS cluster for that kind of tests. It's for the test developer to choose.

Currently, we only support `pytest` test pipeline.

#### Pytest test pipeline

This testing pipeline is implemented using the well established [`pytest`](https://docs.pytest.org/en/stable/)
testing framework. It can be used for testing any apps, no matter if the application was originally written
in python or not. To make testing easier, we are also providing
[`pytest-helm-charts`](https://github.com/giantswarm/pytest-helm-charts) plugin, which makes writing
tests for kubernetes deployed apps easier. See [examples/apps/hello-world-app/tests/abs](examples/apps/hello-world-app/tests/abs) for a complete
usage example.

To make your tests automatically invokable from `abs`, you must adhere to the following rules:

- you must put all the test code in `[CHART_TOP_DIR]/tests/abs/` directory,
- dependencies must be managed with `pipenv` (`abs` first launches pipenv to create a virtual
  environment for your tests, then launches your tests in that virtual environment passing Kubernetes
  required options, like `kube.config` file, as command line arguments).

The `pytest` pipeline invokes following series of steps:

1. TestInfoProvider: gathers some additional info required for running the tests.
1. PytestSmokeTestRunner: invokes `pytest` with `smoke` tag to run smoke tests only.
1. PytestFunctionalTestRunner: invokes `pytest` with `functional` tag to run functional tests only.

### Configuration

Every configuration option in `abs` can be configured in 3 ways. Starting from the highest to the lowest
priority, these are:

- command line arguments,
- environment variables,
- config file (default config file is `.abs/main.yaml` and it's searched in the running directory or the
  directory specified with `-c` option).

When you run `./dabs.sh -h` it shows you command line options and the relevant environment variables names. Options
for a config file are the same as for command line, just with truncated leading `--`. You can check
[this example](examples/apps/hello-world-app/.abs/main.yaml).

The configuration is made this way so you can put your defaults into the config file, yet override them with
env variables or command line when needed. This way you can easily override configs for stuff like CI/CD builds.

## How to contribute

Check out the [contribution guidelines](docs/CONTRIBUTING.md).
