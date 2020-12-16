# App build suite contribution guidelines

`app-build-suite` is built using Python >= 3.8 and pipenv.

## Development setup (without docker)

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

## Development setup (with docker)

It is possible to skip installing Python locally and utilize docker by mounting the repository into a running container.

Directory `examples/apps/hello-world-app` contains an example app to run app-build-suite against.

```bash
# do this once (and every time you change something in Dockerfile)
docker build -t app-build-suite:dev .
# in the root of this repository
docker run --rm -it -v $(pwd)/app_build_suite:/abs/app_build_suite -v $(pwd):/abs/workdir --entrypoint /bin/bash app-build-suite:dev
```

Once inside the container, just execute `python -m app_build_suite`.

## Tests

We encourage adding tests. Execute them with `make docker-test`
