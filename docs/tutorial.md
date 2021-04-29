# How to use app-build-suite to build and optionally test an app

## Preparing tools

To be able to complete this tutorial, you need a few tools:

- `app-build-suite` itself; if you haven't done so already, we recommend getting the latest version of the `dabs.sh` helper from [releases](https://github.com/giantswarm/app-build-suite/releases)
- for the building part
  - [docker](https://docs.docker.com/get-docker/)
- for the testing part
  - a working python environment that you can use to install [pipenv](https://pypi.org/project/pipenv/)
    - if you already have python, it should be enough to run `pip install -U pipenv`
  - to be able to use the shortest path, you also need a working python 3.8 environment
    - to avoid problems like missing the specific python version, we highly recommend
      [`pyenv`](https://github.com/pyenv/pyenv#installation) for managing python environments; once `pyenv` is installed, it's enough to run `pyenv install 3.8.6` to get the python environment you need

## Building your app

The project we'll be working on is available in the `examples/tutorial` directory
of this repository. It's content is a ready helm chart that we want to build
with `abs`.
To get started, let's switch to that directory and create an `.abs` subdirectory:

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

The first line of the config file will make `abs` set versions in our chart according to ones
detected from the local git repository. The other two are needed only if you want to generate
metadata required for advanced features of the Giant Swarm App Platform. If you want
to learn more, check the [more detailed description](pytest-test-pipeline.md).

We're almost ready to go. One technical detail: when running `abs` using
`dabs.sh`, your current working directory is mapped to inside the docker container.
We have configured `abs` to set our chart version using commit information
from `git`, but our current directory doesn't contain any `git` repository - only
the parent directory does. So, the simplest thing we can do is to move up in our
directory structure and invoke `dabs.sh` from a directory where also `git`'s `.git`
directory is. Since we haven't prepared any tests for our app yet, we're also
requesting `abs` to skip any tests:

```bash
$ cd ../../..
$ dabs.sh -c examples/tutorial --skip-steps test_all
2021-04-28 14:48:03,554 __main__ INFO: Starting build with the following options
2021-04-28 14:48:03,554 __main__ INFO:
Command Line Args:   -c examples/tutorial --skip-steps test_all
Config File (/abs/workdir/examples/tutorial/.abs/main.yaml):
  replace-chart-version-with-git:true
  generate-metadata: true
  catalog-base-url:  http://localhost/
Defaults:
  --build-engine:    helm3
  --steps:           ['all']
  --destination:     .
  --app-tests-deploy-namespace:default
  --app-tests-pytest-tests-dir:tests/abs

2021-04-28 14:48:03,554 app_build_suite.build_steps.build_step INFO: Running pre-run step for HelmBuilderValidator
2021-04-28 14:48:03,554 app_build_suite.build_steps.build_step INFO: Running pre-run step for HelmGitVersionSetter
2021-04-28 14:48:03,555 app_build_suite.build_steps.build_step INFO: Running pre-run step for HelmRequirementsUpdater
2021-04-28 14:48:03,555 app_build_suite.build_steps.build_step INFO: Running pre-run step for HelmChartToolLinter
2021-04-28 14:48:03,555 app_build_suite.utils.processes INFO: Running command:
2021-04-28 14:48:03,555 app_build_suite.utils.processes INFO: ct version
2021-04-28 14:48:03,563 app_build_suite.utils.processes INFO: Command executed, exit code: 0.
2021-04-28 14:48:03,563 app_build_suite.build_steps.helm INFO: Metadata generation was requested, changing default validation schema to 'gs_metadata_chart_schema.yaml'
2021-04-28 14:48:03,563 app_build_suite.build_steps.build_step INFO: Running pre-run step for KubeLinter
2021-04-28 14:48:03,563 app_build_suite.utils.processes INFO: Running command:
2021-04-28 14:48:03,563 app_build_suite.utils.processes INFO: kube-linter version
2021-04-28 14:48:03,610 app_build_suite.utils.processes INFO: Command executed, exit code: 0.
2021-04-28 14:48:03,610 app_build_suite.build_steps.build_step INFO: Running pre-run step for HelmChartMetadataPreparer
2021-04-28 14:48:03,620 app_build_suite.build_steps.build_step INFO: Running pre-run step for HelmChartBuilder
2021-04-28 14:48:03,621 app_build_suite.utils.processes INFO: Running command:
2021-04-28 14:48:03,621 app_build_suite.utils.processes INFO: helm version
2021-04-28 14:48:03,667 app_build_suite.utils.processes INFO: Command executed, exit code: 0.
2021-04-28 14:48:03,668 app_build_suite.build_steps.build_step INFO: Running pre-run step for HelmChartMetadataFinalizer
2021-04-28 14:48:03,668 app_build_suite.build_steps.build_step INFO: Running pre-run step for HelmChartYAMLRestorer
2021-04-28 14:48:03,668 app_build_suite.build_steps.build_step INFO: Skipping pre-run step for TestInfoProvider as it was not configured to run.
2021-04-28 14:48:03,668 app_build_suite.build_steps.build_step INFO: Skipping pre-run step for PytestSmokeTestRunner as it was not configured to run.
2021-04-28 14:48:03,668 app_build_suite.build_steps.build_step INFO: Skipping pre-run step for PytestFunctionalTestRunner as it was not configured to run.
2021-04-28 14:48:03,668 app_build_suite.build_steps.build_step INFO: Running build step for HelmBuilderValidator
2021-04-28 14:48:03,668 app_build_suite.build_steps.build_step INFO: Running build step for HelmGitVersionSetter
2021-04-28 14:48:03,681 app_build_suite.build_steps.helm INFO: Replacing 'version' with git version '0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a' in Chart.yaml.
2021-04-28 14:48:03,682 app_build_suite.build_steps.helm INFO: Saving Chart.yaml with version set from git.
2021-04-28 14:48:03,682 app_build_suite.build_steps.build_step INFO: Running build step for HelmRequirementsUpdater
2021-04-28 14:48:03,682 app_build_suite.build_steps.build_step INFO: Running build step for HelmChartToolLinter
2021-04-28 14:48:03,682 app_build_suite.build_steps.helm INFO: Running chart tool linting
2021-04-28 14:48:03,682 app_build_suite.utils.processes INFO: Running command:
2021-04-28 14:48:03,682 app_build_suite.utils.processes INFO: ct lint --validate-maintainers=false --charts=examples/tutorial --chart-yaml-schema=/abs/workdir/app_build_suite/build_steps/../../resources/ct_schemas/gs_metadata_chart_schema.yaml
2021-04-28 14:48:04,718 app_build_suite.utils.processes INFO: Command executed, exit code: 0.
2021-04-28 14:48:04,719 app_build_suite.build_steps.helm INFO: Linting charts...
2021-04-28 14:48:04,719 app_build_suite.build_steps.helm INFO:
2021-04-28 14:48:04,719 app_build_suite.build_steps.helm INFO: ------------------------------------------------------------------------------------------------------------------------
2021-04-28 14:48:04,719 app_build_suite.build_steps.helm INFO:  Charts to be processed:
2021-04-28 14:48:04,719 app_build_suite.build_steps.helm INFO: ------------------------------------------------------------------------------------------------------------------------
2021-04-28 14:48:04,719 app_build_suite.build_steps.helm INFO:  hello-world-app => (version: "0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a", path: "examples/tutorial")
2021-04-28 14:48:04,719 app_build_suite.build_steps.helm INFO: ------------------------------------------------------------------------------------------------------------------------
2021-04-28 14:48:04,720 app_build_suite.build_steps.helm INFO:
2021-04-28 14:48:04,720 app_build_suite.build_steps.helm INFO: Linting chart 'hello-world-app => (version: "0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a", path: "examples/tutorial")'
2021-04-28 14:48:04,720 app_build_suite.build_steps.helm INFO: Validating /abs/workdir/examples/tutorial/Chart.yaml...
2021-04-28 14:48:04,720 app_build_suite.build_steps.helm INFO: Validation success! 👍
2021-04-28 14:48:04,720 app_build_suite.build_steps.helm INFO: ==> Linting examples/tutorial
2021-04-28 14:48:04,720 app_build_suite.build_steps.helm INFO:
2021-04-28 14:48:04,720 app_build_suite.build_steps.helm INFO: 1 chart(s) linted, 0 chart(s) failed
2021-04-28 14:48:04,720 app_build_suite.build_steps.helm INFO: ------------------------------------------------------------------------------------------------------------------------
2021-04-28 14:48:04,721 app_build_suite.build_steps.helm INFO:  ✔︎ hello-world-app => (version: "0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a", path: "examples/tutorial")
2021-04-28 14:48:04,721 app_build_suite.build_steps.helm INFO: ------------------------------------------------------------------------------------------------------------------------
2021-04-28 14:48:04,721 app_build_suite.build_steps.helm INFO: All charts linted successfully
2021-04-28 14:48:04,721 app_build_suite.build_steps.build_step INFO: Running build step for KubeLinter
2021-04-28 14:48:04,721 app_build_suite.build_steps.helm INFO: Running kube-linter tool
2021-04-28 14:48:04,721 app_build_suite.utils.processes INFO: Running command:
2021-04-28 14:48:04,721 app_build_suite.utils.processes INFO: kube-linter lint examples/tutorial --config=examples/tutorial/.kube-linter.yaml
2021-04-28 14:48:04,794 app_build_suite.utils.processes INFO: Command executed, exit code: 0.
2021-04-28 14:48:04,794 app_build_suite.build_steps.build_step INFO: Running build step for HelmChartMetadataPreparer
2021-04-28 14:48:04,803 app_build_suite.build_steps.build_step INFO: Running build step for HelmChartBuilder
2021-04-28 14:48:04,803 app_build_suite.build_steps.helm INFO: Building chart with 'helm package'
2021-04-28 14:48:04,803 app_build_suite.utils.processes INFO: Running command:
2021-04-28 14:48:04,803 app_build_suite.utils.processes INFO: helm package examples/tutorial --destination .
2021-04-28 14:48:04,853 app_build_suite.utils.processes INFO: Command executed, exit code: 0.
2021-04-28 14:48:04,853 app_build_suite.build_steps.helm INFO: Successfully packaged chart and saved it to: /abs/workdir/hello-world-app-0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a.tgz
2021-04-28 14:48:04,853 app_build_suite.build_steps.build_step INFO: Running build step for HelmChartMetadataFinalizer
2021-04-28 14:48:04,865 app_build_suite.build_steps.helm INFO: Metadata file saved to '/abs/workdir/hello-world-app-0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a.tgz-meta/main.yaml'
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Running build step for HelmChartYAMLRestorer
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Skipping build step for TestInfoProvider as it was not configured to run.
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Skipping build step for PytestSmokeTestRunner as it was not configured to run.
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Skipping build step for PytestFunctionalTestRunner as it was not configured to run.
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Running cleanup step for HelmBuilderValidator
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Running cleanup step for HelmGitVersionSetter
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Running cleanup step for HelmRequirementsUpdater
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Running cleanup step for HelmChartToolLinter
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Running cleanup step for KubeLinter
2021-04-28 14:48:04,865 app_build_suite.build_steps.build_step INFO: Running cleanup step for HelmChartMetadataPreparer
2021-04-28 14:48:04,866 app_build_suite.build_steps.build_step INFO: Running cleanup step for HelmChartBuilder
2021-04-28 14:48:04,866 app_build_suite.build_steps.build_step INFO: Running cleanup step for HelmChartMetadataFinalizer
2021-04-28 14:48:04,866 app_build_suite.build_steps.build_step INFO: Running cleanup step for HelmChartYAMLRestorer
2021-04-28 14:48:04,866 app_build_suite.build_steps.helm INFO: Restoring backup Chart.yaml.back to Chart.yaml
```

What happened here? A few things:

- our chart was validated using `ct` and `kube-linter` tools
- version information in our chart was set to `0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a`
- finally our chart was built with Helm

As a result, we have a new helm chart file and metadata files generated for the
App Platform:

```bash
$ ls -la hello-world-app-0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a.*
-rw-r--r-- 1 piontec piontec 1993 kwi 28 16:48 hello-world-app-0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a.tgz

hello-world-app-0.2.2-9e1d8665b328e957d8637e44674434aed8a3bf4a.tgz-meta:
total 20
drwxr-xr-x 1 piontec piontec    72 kwi 28 16:48 .
drwxrwxr-x 1 piontec piontec  1168 kwi 28 16:51 ..
-rw-r--r-- 1 piontec piontec  1011 kwi 28 16:48 main.yaml
-rw-rw-r-- 1 piontec piontec 11664 mar  2 14:41 README.md
-rw-rw-r-- 1 piontec piontec   300 paź 21  2020 values.schema.json
```

## Testing your app

### How does it work?

`abs` can run your tests as part of the app build process. Still, `abs` doesn't
implement any tests nor cares about how you implement them. The contract is just
that `abs` can invoke a specific `pytest` commands for you. If you implement your
tests using `pytest`, `abs` can start them automatically. More information is
available [here](pytest-test-pipeline.md). Still the recommended way to implement
tests for running with `abs` is using `pytest` and our plugin called
[`pytest-helm-charts`](https://github.com/giantswarm/pytest-helm-charts).

### Why I need specific python version?

In general, you can use any python version you want, unless you're using the
dockerized `dabs.sh` wrapper, which is also our recommended way of running `abs`.
Inside the docker image `dabs.sh` is using, there's only one python version available.
This python version is used by `abs` to invoke your tests implemented with `pytest`.
As a result, if you request any other python version than the one currently used
by `dabs.sh`, you'll get an error, as that version is not available inside the docker
image.

You can check the current python version (and versions of all the other software
projects `abs` is using) by running:

```bash
$ dabs.sh versions
-> python env:
Python 3.8.6
pip 20.3.1 from /abs/.venv/lib/python3.8/site-packages/pip (python 3.8)
pipenv, version 2020.11.15
...
```

### Writing the tests

We'll now write some basic tests for the HelloWorld app we've built above in
[building your app](#building-your-app).

#### Preparing environment

Let's create a directory for storing tests. `abs` looks for them in the `tests/abs`
directory, so let's start a fresh python virtual env there:

```bash
$ mkdir -p examples/tutorial/tests/abs
$ cd examples/tutorial/tests/abs
$ pipenv --python 3.8
Creating a virtualenv for this project...
Pipfile: /home/piontec/work/giantswarm/git/app-build-suite/examples/tutorial/tests/abs/Pipfile
Using /home/piontec/.virtualenvs/app-build-suite-pOZwqM8M/bin/python3.8 (3.8.6) to create virtualenv...
⠦ Creating virtual environment...created virtual environment CPython3.8.6.final.0-64 in 362ms
  creator CPython3Posix(dest=/home/piontec/.virtualenvs/abs-4WvsKJg-, clear=False, no_vcs_ignore=False, global=False)
  seeder FromAppData(download=False, pip=bundle, setuptools=bundle, wheel=bundle, via=copy, app_data_dir=/home/piontec/.local/share/virtualenv)
    added seed packages: pip==21.0.1, setuptools==56.0.0, wheel==0.36.2
  activators BashActivator,CShellActivator,FishActivator,PowerShellActivator,PythonActivator,XonshActivator

✔ Successfully created virtual environment!
Virtualenv location: /home/piontec/.virtualenvs/abs-4WvsKJg-
Creating a Pipfile for this project...
```

Now, we need to add our dependencies. If we're going to use `pytest-helm-chart`,
everything else will come as dependencies:

```bash
$ pipenv install "pytest-helm-charts>=0.3.1"
Installing pytest-helm-charts>=0.3.1...
Adding pytest-helm-charts to Pipfile's [packages]...
✔ Installation Succeeded
Pipfile.lock not found, creating...
Locking [dev-packages] dependencies...
Locking [packages] dependencies...
Building requirements...
Resolving dependencies...
✔ Success!
Updated Pipfile.lock (a62443)!
Installing dependencies from Pipfile.lock (a62443)...
  🐍   ▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉ 0/0 — 00:00:00
```

#### Implementing tests

Now we can start implementing actual tests. To get a full sample source code,
just copy the `test_example.py` [file](../examples/apps/hello-world-app/tests/abs/test_example.py) to our `tests/abs` directory, so it looks like this:

```bash
$ ls
Pipfile  Pipfile.lock  test_example.py
```

The simplest test case code in the `test_example.py` file looks like this:

```python
from typing import cast

import pytest
import pykube
from pytest_helm_charts.fixtures import Cluster


@pytest.mark.smoke
def test_we_have_environment(kube_cluster: Cluster) -> None:
    assert kube_cluster.kube_client is not None
    assert len(pykube.Node.objects(kube_cluster.kube_client)) >= 1
```

In this test, we're only checking if we can get a working connection object to
work with our cluster. This is done by requesting the `kube_cluster: Cluster` object
for our test (test method parameters are [pytest fixtures](https://docs.pytest.org/en/stable/fixture.html) and are injected for you by the test framework itself).
Additionally, we're marking our test as a "smoke" test. This information is provided
for `abs` itself: we want to include opinionated test scenarios in `abs` and that
way `abs` knows if it should run your test for specific scenario or not.

You can read more about [how `abs` executes tests](./pytest-test-pipeline.md) and
how to implement them with [pytest-helm-charts](https://pytest-helm-charts.readthedocs.io/en/latest/) and [pytest](https://docs.pytest.org/en/stable/index.html).

#### Running tests

We are now ready to build our test chart again, but this time running tests we've
implemented. To do that, we need to have a cluster where we can deploy our chart
and then execute our tests against a running application. Do make this time
efficient, we'll use [kind](https://kind.sigs.k8s.io/docs/user/quick-start/).
We're going to use embedded `abs` ability to create `kind` clusters, but remember
that you can use any existing cluster you like - you just need to pass a `kube.config`
file to `abs`. `abs` can run different types of tests on different clusters, so we have
to pass cluster type option twice, but our cluster will be reused for both kinds
of tests:

```bash
# log below is truncated to interesting parts only
dabs-stable.sh -c examples/tutorial --smoke-tests-cluster-type kind --functional-tests-cluster-type kind
2021-04-29 10:11:02,536 __main__ INFO: Starting build with the following options
2021-04-29 10:11:02,537 __main__ INFO:
Command Line Args:   -c examples/tutorial --smoke-tests-cluster-type kind --functional-tests-cluster-type kind
Config File (/abs/workdir/examples/tutorial/.abs/main.yaml):
  replace-chart-version-with-git:true
  generate-metadata: true
  catalog-base-url:  http://localhost/
Defaults:
  --build-engine:    helm3
  --steps:           ['all']
  --skip-steps:      []
  --destination:     .
  --app-tests-deploy-namespace:default
  --app-tests-pytest-tests-dir:tests/abs
...
2021-04-29 10:11:02,583 app_build_suite.build_steps.helm INFO: Metadata generation was requested, changing default validation schema to 'gs_metadata_chart_schema.yaml'
...
2021-04-29 10:11:03,212 app_build_suite.build_steps.helm INFO: Replacing 'version' with git version '0.2.2-d723856b0010dd5b236aa5dd7f26ea9ac6cff649' in Chart.yaml.
...
2021-04-29 10:11:03,213 app_build_suite.utils.processes INFO: Running command:
2021-04-29 10:11:03,213 app_build_suite.utils.processes INFO: ct lint --validate-maintainers=false --charts=examples/tutorial --chart-yaml-schema=/abs/workdir/app_build_suite/build_steps/../../resources/ct_schemas/gs_metadata_chart_schema.yaml
...
2021-04-29 10:11:04,292 app_build_suite.build_steps.helm INFO: Validation success! 👍
2021-04-29 10:11:04,293 app_build_suite.build_steps.helm INFO: ==> Linting examples/tutorial
2021-04-29 10:11:04,293 app_build_suite.build_steps.helm INFO:
2021-04-29 10:11:04,293 app_build_suite.build_steps.helm INFO: 1 chart(s) linted, 0 chart(s) failed
...
2021-04-29 10:11:04,294 app_build_suite.utils.processes INFO: Running command:
2021-04-29 10:11:04,294 app_build_suite.utils.processes INFO: kube-linter lint examples/tutorial --config=examples/tutorial/.kube-linter.yaml
...
2021-04-29 10:11:04,412 app_build_suite.build_steps.helm INFO: Building chart with 'helm package'
2021-04-29 10:11:04,412 app_build_suite.utils.processes INFO: Running command:
2021-04-29 10:11:04,412 app_build_suite.utils.processes INFO: helm package examples/tutorial --destination .
2021-04-29 10:11:04,489 app_build_suite.utils.processes INFO: Command executed, exit code: 0.
2021-04-29 10:11:04,489 app_build_suite.build_steps.helm INFO: Successfully packaged chart and saved it to: /abs/workdir/hello-world-app-0.2.2-d723856b0010dd5b236aa5dd7f26ea9ac6cff649.tgz
...
2021-04-29 10:11:04,505 app_build_suite.utils.processes INFO: Running command:
2021-04-29 10:11:04,505 app_build_suite.utils.processes INFO: kind create cluster --name 33b4c0eb-9342-4a25-b54f-e26589b44630 --kubeconfig 33b4c0eb-9342-4a25-b54f-e26589b44630.kube.config
...
2021-04-29 10:11:35,522 app_build_suite.build_steps.base_test_runner INFO: Running apptestctl tool to ensure app platform components on the target cluster
...
2021-04-29 10:13:19,506 app_build_suite.build_steps.base_test_runner INFO: App platform components bootstrapped and ready to use.
2021-04-29 10:13:19,528 app_build_suite.build_steps.repositories INFO: Uploading file '/abs/workdir/hello-world-app-0.2.2-d723856b0010dd5b236aa5dd7f26ea9ac6cff649.tgz' to chart-museum.
2021-04-29 10:13:19,540 app_build_suite.build_steps.base_test_runner INFO: Creating App CR for app 'hello-world-app' to be deployed in namespace 'default' in version '0.2.2-d723856b0010dd5b236aa5dd7f26ea9ac6cff649'.
2021-04-29 10:13:20,560 app_build_suite.build_steps.pytest INFO: Running pipenv tool in 'examples/tutorial/tests/abs' directory to install virtual env for running tests.
2021-04-29 10:13:20,560 app_build_suite.utils.processes INFO: Running command:
2021-04-29 10:13:20,560 app_build_suite.utils.processes INFO: pipenv install --deploy
Creating a virtualenv for this project...
Pipfile: /abs/workdir/examples/tutorial/tests/abs/Pipfile
Using /abs/.venv/bin/python3.8 (3.8.6) to create virtualenv...
⠏ Creating virtual environment...created virtual environment CPython3.8.6.final.0-64 in 1097ms
  creator CPython3Posix(dest=/abs/.local/share/virtualenvs/abs-DrHaOKLK, clear=False, no_vcs_ignore=False, global=False)
  seeder FromAppData(download=False, pip=bundle, setuptools=bundle, wheel=bundle, via=copy, app_data_dir=/abs/.local/share/virtualenv)
    added seed packages: pip==21.0.1, setuptools==54.1.2, wheel==0.36.2
  activators BashActivator,CShellActivator,FishActivator,PowerShellActivator,PythonActivator,XonshActivator

✔ Successfully created virtual environment!
Virtualenv location: /abs/.local/share/virtualenvs/abs-DrHaOKLK
Installing dependencies from Pipfile.lock (a62443)...
  🐍   ▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉ 16/16 — 00:00:09
2021-04-29 10:13:36,429 app_build_suite.utils.processes INFO: Command executed, exit code: 0.
2021-04-29 10:13:36,429 app_build_suite.build_steps.pytest INFO: Running pytest tool in 'examples/tutorial/tests/abs' directory.
2021-04-29 10:13:36,429 app_build_suite.utils.processes INFO: Running command:
2021-04-29 10:13:36,430 app_build_suite.utils.processes INFO: pipenv run pytest -m smoke --cluster-type kind --kube-config /abs/workdir/33b4c0eb-9342-4a25-b54f-e26589b44630.kube.config --chart-path hello-world-app-0.2.2-d723856b0010dd5b236aa5dd7f26ea9ac6cff649.tgz --chart-version 0.2.2-d723856b0010dd5b236aa5dd7f26ea9ac6cff649 --chart-extra-info external_cluster_version=v1.19.1 --log-cli-level info --junitxml=test_results_smoke.xml
...
=============================================== 1 passed, 1 deselected, 2 warnings in 0.07s ================================================
...
2021-04-29 10:14:43,995 app_build_suite.utils.processes INFO: Running command:
2021-04-29 10:14:43,995 app_build_suite.utils.processes INFO: kind delete cluster --name 33b4c0eb-9342-4a25-b54f-e26589b44630
2021-04-29 10:14:45,264 app_build_suite.utils.processes INFO: Command executed, exit code: 0.
2021-04-29 10:14:45,265 app_build_suite.cluster_providers.kind_cluster_provider INFO: KinD cluster deleted successfully
```

That's it. In a single step we have validated, linted, built and tested a new helm
chart. Additionally, the chart is ready to be used with Giant Swarm App Platform
and already has the optional metadata files generated. Now upload the chart to your
chart registry and start rolling it out to clusters!
