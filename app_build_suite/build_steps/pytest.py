import argparse
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, NewType, Set

import configargparse

from app_build_suite.build_steps import BuildStepsFilteringPipeline, BuildStep
from app_build_suite.build_steps.build_step import StepType, STEP_TEST_FUNCTIONAL

TestType = NewType("TestType", str)
TEST_UNIT = TestType("unit")
TEST_FUNCTIONAL = TestType("functional")
TEST_PERFORMANCE = TestType("performance")
TEST_COMPATIBILITY = TestType("compatibility")


class PytestTestFilteringPipeline(BuildStepsFilteringPipeline):
    """
    Pipeline that combines all the steps required to use pytest as a testing framework.
    """

    def __init__(self):
        super().__init__(
            [
                FunctionalTestRunner(),
            ],
            "Pytest test options",
        )


@dataclass
class ClusterType:
    # TODO: implement, below is just a stub/idea
    provider: str
    version: str


@dataclass
class ClusterInfo:
    cluster_type: ClusterType
    # from the real cluster provider
    cluster_id: str
    # path to the kubeconfig file to connect to the cluster
    kube_config_path: str


class BaseTestRunner(BuildStep, ABC):
    # TODO: implement, below is just a stub/idea

    @property
    @abstractmethod
    def _cluster_type_required(self) -> ClusterType:
        raise NotImplementedError

    @property
    @abstractmethod
    def _test_type_executed(self) -> TestType:
        raise NotImplementedError

    def _ensure_app_platform_ready(self, cluster) -> None:
        """
        Ensures that app platform components are already running in the requested cluster.
        This means:
        - app-operator
        - chart-operator
        - some chart repository (chart-museum)
        - AppCatalog CR is created in the API for the chart repository
        :return:
        """
        raise NotImplementedError

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        raise NotImplementedError

    def run(self, config: argparse.Namespace, context: Dict[str, Any]) -> None:
        # TODO:
        # - request a cluster of _cluster_type_required() from ClusterManager; this can be overriden by a config option
        #   `--use-external-cluster=path_to_kubeconfig`
        # - _ensure_app_platform_ready()
        # - start pytest test, using TestType as a filtering parameter and passing chart name
        #   and kubeconfig as parameters
        # - let ClusterManager know we're not using that cluster anymore
        raise NotImplementedError


class FunctionalTestRunner(BaseTestRunner):
    """
    FunctionalTestRunner executes functional tests on top of the configured version of kind cluster
    """

    @property
    def _cluster_type_required(self) -> ClusterType:
        # TODO: load version from config
        return ClusterType("kind", "1.17.3")

    @property
    def _test_type_executed(self) -> TestType:
        return TEST_FUNCTIONAL

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_TEST_FUNCTIONAL}


class ClusterManager:
    """
    This class manages creation and destruction of clusters required to execute tests.
    Cluster are re-used, so when a cluster of specific 'provider' type and 'version' already exists,
    we return the existing (saved internally) cluster. If it doesn't exist, it is created and saved.
    Each cluster is given an ID taken (if only possible) from the underlying provider, to be able
    to correlate clusters created here with what's really running in the infrastructure.
    """

    def __init__(self):
        # dictionary to track created clusters
        self._clusters: Dict[ClusterType, ClusterInfo]
        # dictionary to keep cluster providers
        self._cluster_providers: Dict[ClusterType, ClusterProvider] = {}

    async def get_cluster(self, cluster_type: ClusterType) -> ClusterInfo:
        """ clusters can be requested in parallel - creation mus be non-blocking!"""
        raise NotImplementedError

    async def destroy_all(self):
        """
        A finalizer of ClusterManager - requests destruction of any cluster previously created and saved.
        :return:
        """
        raise NotImplementedError


class ClusterProvider(ABC):
    @property
    @abstractmethod
    def cluster_type(self) -> ClusterType:
        raise NotImplementedError

    async def get_cluster(self, cluster_type: ClusterType) -> ClusterInfo:
        raise NotImplementedError

    async def delete_cluster(self, cluster_info: ClusterInfo):
        raise NotImplementedError
