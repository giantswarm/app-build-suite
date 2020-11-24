import argparse
import logging
import os

import configargparse

from app_build_suite.cluster_providers import cluster_provider
from app_build_suite.errors import ConfigError

logger = logging.getLogger(__name__)

ClusterTypeExternal = cluster_provider.ClusterType("external")


class ExternalClusterProvider(cluster_provider.ClusterProvider):
    __config_option_kubeconfig_path = "--external-cluster-kubeconfig-path"

    def __init__(self):
        self.__kubeconfig_path = ""

    @property
    def provided_cluster_type(self) -> cluster_provider.ClusterType:
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

    def get_cluster(self, cluster_type: cluster_provider.ClusterType, **kwargs) -> cluster_provider.ClusterInfo:
        logger.debug("External cluster manager returning kubeconfig path as configured.")
        return cluster_provider.ClusterInfo(
            self.provided_cluster_type, "unknown", "unavailable", self.__kubeconfig_path, self
        )

    def delete_cluster(self, cluster_info: cluster_provider.ClusterInfo):
        logger.debug("External cluster manager ignoring cluster deletion request (as expected).")
