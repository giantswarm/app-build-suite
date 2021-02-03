import argparse
import logging
import os
import uuid

import configargparse

from app_build_suite.cluster_providers import cluster_provider
from app_build_suite.errors import TestError
from app_build_suite.utils import files, config as config_abs
from app_build_suite.utils.processes import run_and_log

logger = logging.getLogger(__name__)

ClusterTypeKind = cluster_provider.ClusterType("kind")


class KindClusterProvider(cluster_provider.ClusterProvider):
    key_config_option_kind_config_path = "--kind-cluster-config-path"
    _kind_bin = "kind"
    _kind_min_version = "0.9.0"
    _kind_max_version = "1.0.0"

    @property
    def provided_cluster_type(self) -> cluster_provider.ClusterType:
        return ClusterTypeKind

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        pass

    def pre_run(self, config: argparse.Namespace) -> None:
        # verify if binary present
        files.assert_binary_present_in_path(self.__class__.__name__, self._kind_bin)
        # verify version
        run_res = run_and_log([self._kind_bin, "version"], capture_output=True)  # nosec
        version_line = run_res.stdout.splitlines()[0]
        version = version_line.split(" ")[1].strip()
        config_abs.assert_version_in_range(
            self.__class__.__name__, self._kind_bin, version, self._kind_min_version, self._kind_max_version
        )

    @staticmethod
    def __get_kube_config_from_name(name: str) -> str:
        return f"{name}.kube.config"

    def get_cluster(
        self, cluster_type: cluster_provider.ClusterType, config: argparse.Namespace, **kwargs
    ) -> cluster_provider.ClusterInfo:
        cluster_name = str(uuid.uuid4())
        kube_config_path = self.__get_kube_config_from_name(cluster_name)
        kind_args = [self._kind_bin, "create", "cluster", "--name", cluster_name, "--kubeconfig", kube_config_path]
        logger.info(f"Creating KinD cluster with ID '{cluster_name}'...")
        config_file = ""
        if "config_file" in kwargs and kwargs["config_file"]:
            config_file = kwargs["config_file"]
            kind_args.extend(["--config", config_file])
        run_res = run_and_log(kind_args, capture_output=True)  # nosec
        logger.debug(run_res.stderr)
        if run_res.returncode != 0:
            raise TestError(f"Error when creating KinD cluster. Exit code is: {run_res.returncode}")
        cluster_version_line = run_res.stderr.splitlines()[1]
        cluster_version = cluster_version_line.split(":")[1].split(")")[0].strip()
        logger.info("KinD cluster started successfully")
        return cluster_provider.ClusterInfo(
            cluster_type=self.provided_cluster_type,
            overridden_cluster_type=None,
            version=cluster_version,
            cluster_id=cluster_name,
            kube_config_path=kube_config_path,
            managing_provider=self,
            config_file=config_file,
        )

    def delete_cluster(self, cluster_info: cluster_provider.ClusterInfo):
        logger.info(f"Deleting KinD cluster with ID '{cluster_info.cluster_id}'...")
        kube_config_path = self.__get_kube_config_from_name(cluster_info.cluster_id)
        kind_args = [self._kind_bin, "delete", "cluster", "--name", cluster_info.cluster_id]
        run_res = run_and_log(kind_args, capture_output=True)  # nosec
        logger.debug(run_res.stderr)
        if run_res.returncode != 0:
            raise TestError(f"Error when deleting KinD cluster. Exit code is: {run_res.returncode}")
        os.remove(kube_config_path)
        logger.info("KinD cluster deleted successfully")
