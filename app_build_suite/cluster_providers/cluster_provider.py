import argparse
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import NewType, Optional

import configargparse

logger = logging.getLogger(__name__)

ClusterType = NewType("ClusterType", str)


@dataclass
class ClusterInfo:
    # cluster type string like "kind" or "eks"
    cluster_type: ClusterType
    # some cluster providers are used as a proxy to other providers; then the real (end) cluster
    # type should be put here; example: cluster_type = "external", overridden_cluster_type = "kind"
    overridden_cluster_type: Optional[ClusterType]
    # as defined by cluster provider
    version: str
    # from the real cluster provider
    cluster_id: str
    # path to the kubeconfig file to connect to the cluster
    kube_config_path: str
    # cluster provider instance responsible for managing this cluster (needs forward type declaration)
    managing_provider: "ClusterProvider"


class ClusterProvider(ABC):
    @property
    @abstractmethod
    def provided_cluster_type(self) -> ClusterType:
        raise NotImplementedError

    @abstractmethod
    def get_cluster(self, cluster_type: ClusterType, config: argparse.Namespace, **kwargs) -> ClusterInfo:
        raise NotImplementedError

    @abstractmethod
    def delete_cluster(self, cluster_info: ClusterInfo) -> None:
        raise NotImplementedError

    @abstractmethod
    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        raise NotImplementedError

    def pre_run(self, config: argparse.Namespace) -> None:
        pass
