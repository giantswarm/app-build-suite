[![build](https://circleci.com/gh/giantswarm/app-build-suite.svg?style=svg)](https://circleci.com/gh/giantswarm/app-build-suite)
[![codecov](https://codecov.io/gh/giantswarm/app-build-suite/branch/master/graph/badge.svg)](https://codecov.io/gh/giantswarm/app-build-suite)
[![Apache License](https://img.shields.io/badge/license-apache-blue.svg)](https://pypi.org/project/pytest-helm-charts/)

# app-build-suite
A tool to build and release apps for app platform

---
*Big fat warning* This is development version!
---

## How to use app-build-suite

Executing `dabs.sh` is the most straight forward way to run app-build-suite.
For example, for a chart present in `helm/giantswarm-todo-app`, run:

```bash
./dabs.sh -c helm/giantswarm-todo-app
```

To build a container image with local changes:

```bash
make docker-build
```


## How to contribute

Check out the [contribution guidelines](docs/CONTRIBUTION.md).
