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

```

### Usage

Please run:

```bash
dabs.sh -h
```

to get help about all the available config options.

## How to contribute

Check out the [contribution guidelines](docs/CONTRIBUTION.md).
