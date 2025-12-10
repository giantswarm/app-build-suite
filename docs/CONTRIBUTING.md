# App build suite contribution guidelines

`app-build-suite` is built using Python >= 3.8 and uv.

## Development setup

### Without docker

This setup is recommended for IDE and running interactively with debuggers. Check below for a version
that runs inside a docker container.

A good method of handling Python installations is to use [uv](https://github.com/astral-sh/uv).
Please refer to the [uv installation documentation](https://astral.sh/docs/uv/install) for instructions on how to
install it.

```bash
# to create venv
uv venv
# activate the venv
source .venv/bin/activate
# install dependencies
uv sync
# to configure quality check triggers
pre-commit install
```

Directory `examples/apps/hello-world-app` contains an example app to run `app-build-suite` against.

You also need a bunch of binary tools, which normally are present in the docker image, but for developing
locally (outside of a docker container, so you can easily debug your code), you need to install
them on your own. You can list all the required tools and versions currently used
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

The most important basic class is [BuildStep] that comes from the
[step_exec_lib](https://github.com/giantswarm/step-exec-lib/) library. Please check docs there for documentation
about classes provided.

## Tests

We encourage adding tests. Execute them with `make docker-test`

## Releases

At this point, this repository does not make use of the release automation implemented in GitHub actions.

To create a release, switch to the `master` branch, make sure everything you want to have in your release is committed
and documented in the CHANGELOG.md file and your git stage is clean. For MacOS users make sure to use GNU Sed.

Now execute:

```bash
    make release TAG=vX.Y.Z
```

This will prepare the files in the repository, commit them and create a new git tag. Review the created commits. When
satisfied, publish the new release with:

```bash
    git push origin vX.Y.Z
```
