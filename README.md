# app-build-suite

[![build](https://circleci.com/gh/giantswarm/app-build-suite.svg?style=svg)](https://circleci.com/gh/giantswarm/app-build-suite)
[![codecov](https://codecov.io/gh/giantswarm/app-build-suite/branch/master/graph/badge.svg)](https://codecov.io/gh/giantswarm/app-build-suite)
[![Apache License](https://img.shields.io/badge/license-apache-blue.svg)](https://pypi.org/project/pytest-helm-charts/)

A tool to build apps (Helm Charts) for
[Giant Swarm App Platform](https://docs.giantswarm.io/app-platform/).

This tool is a Helm charts development and CI/CD tool that allows you to:

- do some simple variable replacements before building the chart
- lint chart's source code
- run Helm chart code analysis tools
- generate actual chart archive
- generate App Platform specific metadata

In short, it runs an opinionated Helm chart build process as a single configurable build step (one step
build`).

It has a companion tool called [app-test-suite](https://github.com/giantswarm/app-build-suite)
for running dynamic (run-time) tests on charts built.

---
*Big fat warning* This tool is available as a development version!

---

## Index

- [How to use app-build-suite](#how-to-use-app-build-suite)
  - [Installation](#installation)
  - [Tutorial](#tutorial)
  - [Quick start](#quick-start)
  - [A command wrapper on steroids](#a-command-wrapper-on-steroids)
  - [Full usage help](#full-usage-help)
- [Tuning app-build-suite execution and running parts of the build process](#tuning-app-build-suite-execution-and-running-parts-of-the-build-process)
  - [Configuring app-build-suite](#configuring-app-build-suite)
- [Execution steps details and configuration](#execution-steps-details-and-configuration)
  - [Build pipelines](#build-pipelines)
  - [Test pipelines](#test-pipelines)
- [How to contribute](#how-to-contribute)

## How to use app-build-suite

### Installation

`abs` is distributed as a docker image, so the easiest way to install and use it is to get our `dabs.sh`
script from [releases](https://github.com/giantswarm/app-build-suite/releases). `dabs.sh` is a wrapper script
that launches for you `abs` inside a docker container and provides all the necessary docker options required
to make it work (check te script for details, it's short).

Alternatively, you can just checkout this repository and build the docker image yourself by running:

```bash
make docker-build
```

### Tutorial

If you prefer to learn by example, building a simple project step-by-step,
please start with [tutorial](docs/tutorial.md).

### Quick start

Executing `dabs.sh` is the most straight forward way to run `app-build-suite`.
As an example, we have included a chart in this repository in
[`examples/apps/hello-world-app`](examples/apps/hello-world-app/). It's configuration file for
`abs` is in the [.abs/main.yaml](examples/apps/hello-world-app/.abs/main.yaml) file. To build the chart
using `dabs.sh` and the provided config file, run:

```bash
dabs.sh -c examples/apps/hello-world-app
```

### A command wrapper on steroids

`abs` is not much more than a wrapper around a set of well-known open source tools.
It orchestrates these tools into an opinionated build process and adds some additional
features, like generating metadata for the Giant Swarm App Platform.

To better explain it, see what really happens when you call

```bash
dabs.sh -c examples/apps/hello-world-app --destination build
```

The list bellow
is a set of commands executed for you by `abs`:

```bash
# app and chart versions in the Chart.yaml file are set using git changes (if configured)
ct lint --validate-maintainers=false --charts=examples/apps/hello-world-app --chart-yaml-schema=/abs/workdir/app_build_suite/build_steps/../../resources/ct_schemas/gs_metadata_chart_schema.yaml
kube-linter lint . --config .kube-linter.yaml
helm package examples/apps/hello-world-app --destination build
# now metadata is generated from the data collected during the build (if configured)
```

### Full usage help

To get an overview of available options, please run:

```bash
dabs.sh -h
```

To learn what the configuration options mean and how to use them, please follow to
[execution steps and their config options](#execution-steps-details-and-configuration).

## Tuning app-build-suite execution and running parts of the build process

This tool works by executing a series of so called `Build Steps`. In general, one `BuildSteps` is about
a single step in the build, like running a single external tool. Most of the build steps are configurable
(run `./dabs.sh -h` to check available options and go to
[steps details and configuration](#execution-steps-details-and-configuration) for detailed description).

The important property in `app-build-suite` is that you can only execute a subset of all the build steps.
This idea should be useful for integrating `abs` with other workflows, like CI/CD systems or for
running parts of the build process on your local machine during development. You can either run only a
selected set of steps using `--steps` option or you can run all if them excluding some
using `--skip-steps`. Check `dabs.sh -h` output for step names available to `--steps` and `--skip-steps`
flags.

To skip or include multiple step names, separate them with space, like in this example:

```bash
dabs.sh -c examples/apps/hello-world-app --skip-steps test_unit test_performance
```

### Configuring app-build-suite

Every configuration option in `abs` can be configured in 3 ways. Starting from the highest to the lowest
priority, these are:

- command line arguments,
- environment variables,
- config file (`abs` tries first to load the config file from the chart's directory `.abs/main.yaml` file; if
  it doesn't exist, then it tries to load the default config file from the current working directory's
  `.abs.main.yaml`).

When you run `dabs.sh -h` it shows you command line options and the relevant environment variables names. Options
for a config file are the same as for command line, just with truncated leading `--`. You can check
[this example](examples/apps/hello-world-app/.abs/main.yaml).

The configuration is made this way so you can put your defaults into the config file, yet override them with
env variables or command line when needed. This way you can easily override configs for stuff like CI/CD builds.

## Execution steps details and configuration

`abs` is composed of two main pipelines: *build* and *test*. Each of them is composed of steps.
When `abs` runs, it executes all the steps from the *build* pipeline and then from the *test* pipeline.
Config options can be used to disable/enable any specific build steps.

Please check below for available build pipelines and steps and their config options.

### Build pipelines

Currently, only one build pipeline is supported. It is based on `helm 3`. Please check
[this doc](../app-build-suite/docs/helm3-build-pipeline.md) for
detailed description of steps and available config options.

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

Currently, we only support [`pytest` test pipeline](docs/pytest-test-pipeline.md).

## How to contribute

Check out the [contribution guidelines](docs/CONTRIBUTING.md).
