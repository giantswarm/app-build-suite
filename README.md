[![build](https://circleci.com/gh/giantswarm/app-build-suite.svg?style=svg)](https://circleci.com/gh/giantswarm/app-build-suite)
[![codecov](https://codecov.io/gh/giantswarm/app-build-suite/branch/master/graph/badge.svg)](https://codecov.io/gh/giantswarm/app-build-suite)
[![Apache License](https://img.shields.io/badge/license-apache-blue.svg)](https://pypi.org/project/pytest-helm-charts/)

# app-build-suite
A tool to build and release apps for app platform

---
*Big fat warning* This is development version!
---

## How to use

The easiest way is to make a docker image:

```bash
make docker-build
```

Then run using the easy docker run script `dabs`. For example,
for a chart present in `helm/giantswarm-todo-app`, run:

```bash
./dabs.sh -c helm/giantswarm-todo-app
```


## How to contribute

Setup dev environment:

- python >= 3.8
- pipenv

Then, checkout the repo and run:

```bash
# to create venv
pipenv install --dev
# to configure quality check triggers
pipenv run pre-commit install
```
