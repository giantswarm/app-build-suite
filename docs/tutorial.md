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
