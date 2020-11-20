import argparse
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import NewType

import configargparse

from app_build_suite.errors import ConfigError

logger = logging.getLogger(__name__)

ClusterType = NewType("ClusterType", str)
ClusterTypeExternal = ClusterType("external")


@dataclass
class ClusterInfo:
    cluster_type: ClusterType
    # as defined by cluster provider
    version: str
    # from the real cluster provider
    cluster_id: str
    # path to the kubeconfig file to connect to the cluster
    kube_config_path: str
    # cluster provider instance responsible for managing this cluster
    managing_provider: "ClusterProvider"


class ClusterProvider(ABC):
    @property
    @abstractmethod
    def provided_cluster_type(self) -> ClusterType:
        raise NotImplementedError

    @abstractmethod
    def get_cluster(self, cluster_type: ClusterType, **kwargs) -> ClusterInfo:
        raise NotImplementedError

    @abstractmethod
    def delete_cluster(self, cluster_info: ClusterInfo) -> None:
        raise NotImplementedError

    @abstractmethod
    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        raise NotImplementedError

    def pre_run(self, config: argparse.Namespace) -> None:
        pass


class ExternalClusterProvider(ClusterProvider):
    __config_option_kubeconfig_path = "--external-cluster-kubeconfig-path"

    def __init__(self):
        self.__kubeconfig_path = ""

    @property
    def provided_cluster_type(self) -> ClusterType:
        return ClusterTypeExternal

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            self.__config_option_kubeconfig_path,
            required=False,
            help="A path to the 'kubeconfig' file that provides connection details for external cluster",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        if not config.external_cluster_kubeconfig_path:
            raise ConfigError(self.__config_option_kubeconfig_path, "Kubeconfig file path must be configured")

        if not os.path.isfile(config.external_cluster_kubeconfig_path):
            raise ConfigError(
                self.__config_option_kubeconfig_path,
                f"Kubeconfig file {config.external_cluster_kubeconfig_path} not found.",
            )
        self.__kubeconfig_path = config.external_cluster_kubeconfig_path

    def get_cluster(self, cluster_type: ClusterType, **kwargs) -> ClusterInfo:
        logger.debug("External cluster manager returning kubeconfig path as configured.")
        return ClusterInfo(self.provided_cluster_type, "unknown", "unavailable", self.__kubeconfig_path, self)

    def delete_cluster(self, cluster_info: ClusterInfo):
        logger.debug("External cluster manager ignoring cluster deletion request (as expected).")
