import pytest
import pykube
from pytest_helm_charts.fixtures import Cluster


@pytest.mark.functional
def test_dummy() -> None:
    assert True


@pytest.mark.functional
def test_api_working(kube_cluster: Cluster) -> None:
    assert kube_cluster.kube_client is not None
    assert len(pykube.Node.objects(kube_cluster.kube_client)) >= 1
