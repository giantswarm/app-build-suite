import argparse
import logging
from typing import Optional, List, Dict

import configargparse

from app_build_suite.cluster_providers.cluster_provider import ClusterInfo, ClusterType, ClusterProvider

logger = logging.getLogger(__name__)


class ClusterManager:
    """
    This class manages creation and destruction of clusters required to execute tests.
    Cluster are re-used, so when a cluster of specific 'provider' type and 'version' already exists,
    we return the existing (saved internally) cluster. If it doesn't exist, it is created and saved.
    Each cluster is given an ID taken (if only possible) from the underlying provider, to be able
    to correlate clusters created here with what's really running in the infrastructure.
    """

    def __init__(self):
        # config is necessary for cluster providers to configure clusters; we'll set it once config is loaded
        self._config: Optional[argparse.Namespace] = None
        # list to track created clusters
        self._clusters: List[ClusterInfo] = []
        # dictionary to keep cluster providers
        self._cluster_providers: Dict[ClusterType, ClusterProvider] = {}
        # find and create cluster providers
        for cls in ClusterProvider.__subclasses__():
            instance = cls()
            self._cluster_providers[instance.provided_cluster_type] = instance

    def get_registered_cluster_types(self) -> List[ClusterType]:
        return [k for k in self._cluster_providers.keys()]

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        for cluster_type, provider in self._cluster_providers.items():
            logger.debug(f"Initializing configuration of cluster provider for clusters of type {cluster_type}")
            provider.initialize_config(config_parser)

    def pre_run(self, config: argparse.Namespace) -> None:
        for cluster_type, provider in self._cluster_providers.items():
            logger.debug(f"Executing pre-run of cluster provider for clusters of type {cluster_type}")
            provider.pre_run(config)

    def get_cluster_for_test_type(
        self, cluster_type: ClusterType, cluster_config_file: str, config: argparse.Namespace
    ) -> ClusterInfo:
        """ clusters can be requested in parallel - creation mus be non-blocking!"""
        if cluster_type not in self._cluster_providers.keys():
            raise ValueError(f"Unknown cluster type '{cluster_type}'.")
        cluster_info = self._cluster_providers[cluster_type].get_cluster(
            cluster_type, config, config_file=cluster_config_file
        )
        self._clusters.append(cluster_info)
        return cluster_info

    def release_cluster(self, cluster_info: ClusterInfo) -> None:
        if cluster_info not in self._clusters:
            raise ValueError(f"Cluster {cluster_info} is not registered as managed here.")
        cluster_info.managing_provider.delete_cluster(cluster_info)
        self._clusters.remove(cluster_info)

    def cleanup(self) -> None:
        """
        A finalizer of ClusterManager - requests destruction of any cluster previously created,
        saved and not yet destroyed.
        :return:
        """
        for cluster_info in self._clusters:
            self.release_cluster(cluster_info)
