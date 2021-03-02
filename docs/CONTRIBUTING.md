# App build suite contribution guidelines

`app-build-suite` is built using Python >= 3.8 and pipenv.

## Development setup

### Without docker

This setup is recommended for GUI and running interactively with debuggers. Check below for a version
that runs inside a docker container.

A good method of handling Python installations is to use [pyenv](https://github.com/pyenv/pyenv).


```bash
# Install pipenv
pip install pipenv
# to create venv
pipenv install --dev
# to configure quality check triggers
pipenv run pre-commit install
```

Directory `examples/apps/hello-world-app` contains an example app to run app-build-suite against.

You also need a bunch of binary tools, which normally are present in the docker image, but for developing
locally, you need to install them on your own. You can list all the required tools and versions currently used
by running:

```bash
dabs.sh versions
```

### With docker

It is possible to skip installing Python locally and utilize docker by mounting the repository into a running container.

Directory `examples/apps/hello-world-app` contains an example app to run app-build-suite against.

```bash
# do this once (and every time you change something in Dockerfile)
docker build -t app-build-suite:dev .
# in the root of this repository
docker run --rm -it -v $(pwd)/app_build_suite:/abs/app_build_suite -v $(pwd):/abs/workdir --entrypoint /bin/bash app-build-suite:dev
```

Once inside the container, just execute `python -m app_build_suite`.

## Extending `abs`

### How it's implemented

#### BuildStep

The most important basic class is [BuildStep](../app_build_suite/build_steps/build_step.py). The class is abstract
and you have to inherit it to provide any actual functionality.  The most important methods and properties of
this class are:

* Each `BuildStep` provides a set of step names it is associated with in the `steps_provided` property.
  These steps are used for filtering with `--steps`/`--skip-steps` command line options.
* `initialize_config` provides additional config options a specific class delivered from `BuildStep`
  wants to provide.
* `pre_run` is optional and should be used for validation and assertions. `pre_runs` of all `BuildSteps` are executed
  before any `run` method is executed. Its purpose is to allow the `abs`
  to quit with error even before any actual build or tests are done. The method can't be blocking and should run
  fast. If `pre_step` of any `BuildStep` fails, `run` methods of all `BuildSteps` are skipped.
* `run` is the method where actual long-running actions of the `BuildStep` are executed.
* `cleanup` is an optional method used to clean up resources that might have been needed by `run` but can't be cleaned
  up until all `runs` have executed. `cleanups` are called after any `run` failed or all of them are done.

#### BuildStepsFilteringPipeline

`BuildStep` class provides the `steps_provided` property, but is not in control of whether it should be executed or not
and when. `BuildSteps` have to be assembled into `pipelines`. The basic pipeline in `BuildStepsFilteringPipeline`, which
allows you to make a sequential pipeline out of your steps and filter and skip them according to `steps_provided` they
return and command line options `--steps`/`--skip-steps`. Each major part of `abs` execution is combined into a
pipeline, like `HelmBuildFilteringPipeline` used to execute build pipeline with Helm 3 or `PytestTestFilteringPipeline`
which is used to execute tests using `pytest` once the build pipeline is done.

#### Cluster provider

`abs` allows you to run different types of tests on clusters you have configured for them. To allow the user
to choose on which type of cluster the specific test type will run, there has to be a
[`ClusterProvider`](../app_build_suite/cluster_providers/cluster_provider.py) for that specific cluster.
Please make sure you register any new `ClusterProviders` in the package's
[`__init__.py`](../app_build_suite/cluster_providers/__init__.py), as they are auto-discovered from there.
When you're done with it, you don't have to write any additional code to make the new cluster type available.

As an example, please have a look at
[`ExternalClusterProvider`](../app_build_suite/cluster_providers/external_cluster_provider.py).

## Tests

We encourage adding tests. Execute them with `make docker-test`

## Releases

At this point, this repository does not make use of the release automation implemented in GitHub actions.

To create a release, switch to the `master` branch, make sure everything you want to have in your release is committed and documented in the CHANGELOG.md file and your git stage is clean. Now execute:

```bash
    make release TAG=vX.Y.Z
```

This will prepare the files in the repository, commit them and create a new git tag. Review the created commits. When satisfied, publish the new release with:

```bash
    git push origin vX.Y.Z
```
