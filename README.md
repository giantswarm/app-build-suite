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
  - define different test scenarios for your release

---
*Big fat warning* This tool is available as a development version!
---

## How to use app-build-suite

### Installation

`abs` is distributed as a docker image, so the easiest way to install and use it is to get our `dabs.sh`
script from [releases](https://github.com/giantswarm/app-build-suite/releases). `dabs.sh` is a wrapper script
that launches for you `abs` inside a docker container and provides all the necessary docker options required
to make it work.

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
of the following labels: `smoke`, `functional`. It uses the labels to run only certain tests, so `abs`
runs all `smoke` tests first, then all `functional` tests. As concrete example, this mechanism is implemented
as [marks in pytest](https://docs.pytest.org/en/stable/mark.html) or
[tags in go test](https://golang.org/pkg/go/build/#hdr-Build_Constraints).

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

#### Configuring test scenarios

Each test type ("smoke", "functional") can have its own type and configuration of a Kubernetes cluster it
runs on. That way you can create test scenarios like: "please run my 'smoke' tests on a `kind` cluster; if they
succeed, run 'functional' tests on an external cluster I give you `kube.config` for".

The type of cluster used for each type of tests is selected using the `--[TEST_TYPE]-tests-cluster-type`
config option. Additionally, if the cluster provider of given type supports some config files that allow you
to tune how the cluster is created, you can pass a path to that config file using the
`--[TEST_TYPE]-tests-cluster-config-file`.

Currently, the supported cluster types are:

1. `external` - it means the cluster is created out of the scope of control of `abs`. The user must pass
   a path to the `kube.config` file and cluster type and Kubernetes version as command line arguments.
1. `kind` - `abs` automatically create a [`kind`](https://kind.sigs.k8s.io/docs/user/quick-start/)
   cluster for that type of tests. You can additionally pass
   [kind config file](https://kind.sigs.k8s.io/docs/user/quick-start/#configuring-your-kind-cluster)
   to configure the cluster that will be created by `abs`.

##### Test scenario example

**Info:** Please remember you can save any command line option you use constantly in the `.abs/main.yaml`
file and skip it from command line.

1. I want to run 'smoke' tests on a kind cluster and 'functional' tests on an external K8s 1.19.0 cluster
   created on EKS:

   ```bash
   # command-line version
   dabs.sh -c my-chart --smoke-tests-cluster-type kind \
     --functional-tests-cluster-type external \
     --external-cluster-kubeconfig-path kube.config \
     --external-cluster-type EKS \
     --external-cluster-version "1.19.0"
   ```

2. I want to run both `smoke` and `functional` tests on the same `kind` cluster. I want the `kind` cluster
   to be created according to my config file:

   ```yaml
   # config file version - content of `.abs/main.yaml`
   functional-tests-cluster-type: kind
   smoke-tests-cluster-type: kind
   smoke-tests-cluster-config-file: my-chart/kind_config.yaml
   functional-tests-cluster-config-file: my-chart/kind_config.yaml
   ```

### Configuration

Every configuration option in `abs` can be configured in 3 ways. Starting from the highest to the lowest
priority, these are:

- command line arguments,
- environment variables,
- config file (`abs` tries first to load the config file from the chart's directory `.abs/main.yaml` file; if
  it doesn't exist, then it tries to load the default config file from the current working directory's
  `.abs.main.yaml`).

When you run `./dabs.sh -h` it shows you command line options and the relevant environment variables names. Options
for a config file are the same as for command line, just with truncated leading `--`. You can check
[this example](examples/apps/hello-world-app/.abs/main.yaml).

The configuration is made this way so you can put your defaults into the config file, yet override them with
env variables or command line when needed. This way you can easily override configs for stuff like CI/CD builds.

## How to contribute

Check out the [contribution guidelines](docs/CONTRIBUTING.md).
