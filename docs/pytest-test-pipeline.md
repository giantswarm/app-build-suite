# Pytest test pipeline

This testing pipeline is implemented using the well established [`pytest`](https://docs.pytest.org/en/stable/)
testing framework. It can be used for testing any apps, no matter if the application was originally written
in python or not. To make testing easier, we are also providing
[`pytest-helm-charts`](https://github.com/giantswarm/pytest-helm-charts) plugin, which makes writing
tests for kubernetes deployed apps easier. See [examples/apps/hello-world-app/tests/abs](examples/apps/hello-world-app/tests/abs) for a complete
usage example.

To make your tests automatically invocable from `abs`, you must adhere to the following rules:

- you must put all the test code in `[CHART_TOP_DIR]/tests/abs/` directory,
- dependencies must be managed with `pipenv` (`abs` first launches pipenv to create a virtual
  environment for your tests, then launches your tests in that virtual environment passing Kubernetes
  required options, like `kube.config` file, as command line arguments).

The `pytest` pipeline invokes following series of steps:

1. TestInfoProvider: gathers some additional info required for running the tests.
1. PytestSmokeTestRunner: invokes `pytest` with `smoke` tag to run smoke tests only.
1. PytestFunctionalTestRunner: invokes `pytest` with `functional` tag to run functional tests only.

## Configuring test scenarios

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

### Test scenario example

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
