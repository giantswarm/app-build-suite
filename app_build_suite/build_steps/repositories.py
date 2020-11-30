from abc import ABC, abstractmethod
from typing import cast

import requests
from pykube import HTTPClient, Service

from app_build_suite.build_steps import helm
from app_build_suite.types import Context
from app_build_suite.errors import TestError


class AppRepository(ABC):
    @abstractmethod
    def upload_artifacts(self, context: Context) -> None:
        raise NotImplementedError()


class ChartMuseumAppRepository(AppRepository):
    _cm_service_name = "chartmuseum-chartmuseum"
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
        chart_filename = context[helm.context_key_chart_file_name]
        with open(chart_filename, "rb") as f:
            files = {chart_filename: f}
            headers = {"Content-Type": "application/octet-stream", "Expect": "100-continue", "Connection": "keep-alive"}
            resp = requests.post("http://localhost:8080/api/charts", stream=True, data=f, headers=headers)
            resp = requests.post("http://localhost:8080/api/charts", files=files)
            resp = cm_srv.proxy_http_post("/api/charts/", files=files)
            if not resp.ok:
                raise TestError("Error uploading chart to chartmuseum")
        # with open(chart_filename, "rb") as f:
        #    # resp = cm_srv.proxy_http_post("/api/charts", data=chart_file_data, headers={'Content-Type':
        #    'application/octet-stream'})
        #    resp = cm_srv.proxy_http_post(f"/api/charts/", data=f.read())
        #    if not resp.ok:
        #        raise TestError("Error uploading chart to chartmuseum")
