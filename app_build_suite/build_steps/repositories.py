from abc import ABC, abstractmethod
from typing import cast

from pykube import HTTPClient, Service

from app_build_suite.build_steps import helm
from app_build_suite.components import Context
from app_build_suite.errors import TestError


class AppRepository(ABC):
    @abstractmethod
    def upload_artifacts(self, context: Context) -> None:
        raise NotImplementedError()


class ChartMuseumAppRepository(AppRepository):
    _cm_service_name = "chartmuseum"
    _cm_service_namespace = "giantswarm"

    def __init__(self, kube_client: HTTPClient):
        self._kube_client = kube_client

    def upload_artifacts(self, context: Context) -> None:
        cm_srv = cast(
            Service,
            Service.objects(self._kube_client)
            .filter(namespace=self._cm_service_namespace)
            .get_or_none(name=self._cm_service_name),
        )
        if cm_srv is None:
            raise TestError(
                f"Repository service '{self._cm_service_name}' not found in namespace"
                f" '{self._cm_service_namespace}'. Can't upload chart."
            )
        with open(context[helm.context_key_chart_file_name], "rb") as f:
            chart_file_data = bytearray(f.read())
        cm_srv.proxy_http_get("/api/charts", data=chart_file_data)
