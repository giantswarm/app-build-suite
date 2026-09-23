import http.client
import json
import urllib.error
import urllib.request
from typing import Any, List, Optional, Union

import pytest
from pytest_mock import MockerFixture

from app_build_suite.build_steps import helm_image_reference_validator
from app_build_suite.build_steps.helm_consts import context_key_rendered_chart
from app_build_suite.build_steps.helm_image_reference_validator import (
    HelmImageReferenceValidator,
    ImageReference,
    RegistryClient,
    RegistryError,
    extract_image_references,
    parse_image_reference,
)
from app_build_suite.errors import BuildError
from tests.build_steps.helpers import init_config_for_step

DIGEST = "sha256:" + "ab" * 32

RENDERED = """---
# Source: my-app/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    spec:
      initContainers:
        - name: init
          image: gsoci.azurecr.io/giantswarm/init:1.2.3
      containers:
        - name: app
          image: gsoci.azurecr.io/giantswarm/my-app:0.1.0
        - name: metrics
          image: gsoci.azurecr.io/giantswarm/redis_exporter:v1.92.0
---
# Source: my-app/templates/policy.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
spec:
  rules:
    - name: any-image
      match:
        image: "*"
---
# Source: my-app/templates/cronjob.yaml
apiVersion: batch/v1
kind: CronJob
spec:
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: job
              image: gsoci.azurecr.io/giantswarm/my-app:0.1.0
            - name: upstream
              image: quay.io/prometheus/busybox:latest
---
# Source: my-app/templates/configmap.yaml
apiVersion: v1
kind: ConfigMap
data:
  other: gsoci.azurecr.io/giantswarm/not-under-an-image-key:1.0.0
"""

GSOCI_REFERENCES = [
    "gsoci.azurecr.io/giantswarm/init:1.2.3",
    "gsoci.azurecr.io/giantswarm/my-app:0.1.0",
    "gsoci.azurecr.io/giantswarm/redis_exporter:v1.92.0",
]


class FakeRegistryClient:
    """Answers from a fixed set of existing references and records what was asked."""

    def __init__(self, existing: List[str], failing: Optional[List[str]] = None) -> None:
        self.existing = existing
        self.failing = failing or []
        self.asked: List[str] = []

    def manifest_exists(self, image: ImageReference) -> bool:
        self.asked.append(image.reference)
        if image.reference in self.failing:
            raise RegistryError("registry unreachable")
        return image.reference in self.existing


def _run_step(client: FakeRegistryClient, rendered: Optional[str] = RENDERED, disabled: bool = False) -> None:
    step = HelmImageReferenceValidator(registry_client=client)  # type: ignore[arg-type]
    config = init_config_for_step(step)
    config.disable_helm_image_reference_validator = disabled
    context = {} if rendered is None else {context_key_rendered_chart: rendered}
    step.run(config, context)


@pytest.mark.parametrize(
    "value, registry, repository, tag, digest",
    [
        ("gsoci.azurecr.io/giantswarm/my-app:0.1.0", "gsoci.azurecr.io", "giantswarm/my-app", "0.1.0", None),
        (
            "gsoci.azurecr.io/giantswarm/redis_exporter:v1.92.0",
            "gsoci.azurecr.io",
            "giantswarm/redis_exporter",
            "v1.92.0",
            None,
        ),
        ("gsoci.azurecr.io/giantswarm/my-app", "gsoci.azurecr.io", "giantswarm/my-app", "latest", None),
        (f"gsoci.azurecr.io/giantswarm/my-app@{DIGEST}", "gsoci.azurecr.io", "giantswarm/my-app", "latest", DIGEST),
        (
            f"gsoci.azurecr.io/giantswarm/my-app:0.1.0@{DIGEST}",
            "gsoci.azurecr.io",
            "giantswarm/my-app",
            "0.1.0",
            DIGEST,
        ),
        ("localhost:5000/my-app:dev", "localhost:5000", "my-app", "dev", None),
        ("nginx:1.25", "docker.io", "nginx", "1.25", None),
        ("giantswarm/my-app:0.1.0", "docker.io", "giantswarm/my-app", "0.1.0", None),
        ("quay.io/prometheus/busybox:latest", "quay.io", "prometheus/busybox", "latest", None),
    ],
)
def test_parse_image_reference(value: str, registry: str, repository: str, tag: str, digest: Optional[str]) -> None:
    image = parse_image_reference(value)
    assert image is not None
    assert (image.registry, image.repository, image.tag, image.digest) == (registry, repository, tag, digest)
    assert image.reference == value


def test_digest_wins_over_tag_for_the_manifest_reference() -> None:
    image = parse_image_reference(f"gsoci.azurecr.io/giantswarm/my-app:0.1.0@{DIGEST}")
    assert image is not None
    assert image.manifest_reference == DIGEST
    tagged = parse_image_reference("gsoci.azurecr.io/giantswarm/my-app:0.1.0")
    assert tagged is not None
    assert tagged.manifest_reference == "0.1.0"


@pytest.mark.parametrize(
    "value",
    ["*", "", "gsoci.azurecr.io/giantswarm/*", "{{ .Values.image }}", "an image", "gsoci.azurecr.io/GiantSwarm/App:1"],
)
def test_values_that_are_no_image_reference(value: str) -> None:
    assert parse_image_reference(value) is None


def test_extracts_image_values_with_the_templates_they_render_from() -> None:
    found = extract_image_references(RENDERED)
    assert set(found) == set(GSOCI_REFERENCES) | {"*", "quay.io/prometheus/busybox:latest"}
    assert found["gsoci.azurecr.io/giantswarm/init:1.2.3"] == {"my-app/templates/deployment.yaml"}
    assert found["gsoci.azurecr.io/giantswarm/my-app:0.1.0"] == {
        "my-app/templates/deployment.yaml",
        "my-app/templates/cronjob.yaml",
    }
    assert found["*"] == {"my-app/templates/policy.yaml"}
    assert "gsoci.azurecr.io/giantswarm/not-under-an-image-key:1.0.0" not in found


def test_every_checked_registry_reference_is_resolved_once_and_others_are_not(mocker: MockerFixture) -> None:
    info = mocker.patch.object(helm_image_reference_validator.logger, "info")
    client = FakeRegistryClient(existing=GSOCI_REFERENCES)
    _run_step(client)
    assert sorted(client.asked) == GSOCI_REFERENCES
    assert any("3 image reference(s) resolved" in str(call.args[0]) for call in info.call_args_list)


def test_a_missing_tag_fails_the_build_naming_the_reference_and_its_template() -> None:
    client = FakeRegistryClient(existing=[r for r in GSOCI_REFERENCES if "redis_exporter" not in r])
    with pytest.raises(BuildError) as excinfo:
        _run_step(client)
    assert "1 image reference(s) cannot be pulled" in excinfo.value.msg
    assert (
        "'gsoci.azurecr.io/giantswarm/redis_exporter:v1.92.0' does not exist in gsoci.azurecr.io" in excinfo.value.msg
    )
    assert "my-app/templates/deployment.yaml" in excinfo.value.msg
    assert "init:1.2.3" not in excinfo.value.msg


def test_every_problem_is_reported_at_once(mocker: MockerFixture) -> None:
    error = mocker.patch.object(helm_image_reference_validator.logger, "error")
    client = FakeRegistryClient(existing=[], failing=["gsoci.azurecr.io/giantswarm/init:1.2.3"])
    with pytest.raises(BuildError) as excinfo:
        _run_step(client)
    assert "3 image reference(s) cannot be pulled" in excinfo.value.msg
    assert "'gsoci.azurecr.io/giantswarm/init:1.2.3' could not be resolved: registry unreachable" in excinfo.value.msg
    logged = [str(call.args[0]) for call in error.call_args_list]
    assert any("'require' the image job" in line for line in logged)
    assert any("--disable-helm-image-reference-validator" in line for line in logged)


def test_disabled_validator_asks_nothing() -> None:
    client = FakeRegistryClient(existing=[])
    _run_step(client, disabled=True)
    assert client.asked == []


def test_without_a_render_in_the_context_nothing_is_checked_and_it_is_said(mocker: MockerFixture) -> None:
    warning = mocker.patch.object(helm_image_reference_validator.logger, "warning")
    client = FakeRegistryClient(existing=[])
    _run_step(client, rendered=None)
    assert client.asked == []
    assert "image references are not checked" in str(warning.call_args.args[0])


def test_the_pipeline_runs_the_validator_right_after_the_render() -> None:
    from app_build_suite.build_steps.helm import HelmBuildFilteringPipeline
    from app_build_suite.build_steps.helm_template_validator import HelmTemplateValidator

    steps = HelmBuildFilteringPipeline()._pipeline
    names = [type(step).__name__ for step in steps]
    assert names.index(HelmImageReferenceValidator.__name__) == names.index(HelmTemplateValidator.__name__) + 1


# --- RegistryClient against a scripted HTTP opener --------------------------------------------------------

CHALLENGE = (
    'Bearer realm="https://gsoci.azurecr.io/oauth2/token",service="gsoci.azurecr.io",'
    'scope="repository:giantswarm/redis_exporter:pull"'
)


class _Response:
    def __init__(self, status: int, body: bytes = b"") -> None:
        self.status = status
        self._body = body

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _http_error(url: str, code: int, challenge: Optional[str] = None) -> urllib.error.HTTPError:
    headers = http.client.HTTPMessage()
    if challenge:
        headers["WWW-Authenticate"] = challenge
    return urllib.error.HTTPError(url, code, "error", headers, None)


class ScriptedOpener:
    """Plays back one answer per request, in order, and keeps the requests for assertions."""

    def __init__(self, answers: List[Union[_Response, Exception]]) -> None:
        self.answers = list(answers)
        self.requests: List[urllib.request.Request] = []

    def __call__(self, request: urllib.request.Request, timeout: float) -> _Response:
        self.requests.append(request)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def _reference(value: str) -> ImageReference:
    image = parse_image_reference(value)
    assert image is not None
    return image


EXPORTER = _reference("gsoci.azurecr.io/giantswarm/redis_exporter:v1.92.0")
MANIFEST_URL = "https://gsoci.azurecr.io/v2/giantswarm/redis_exporter/manifests/v1.92.0"
TOKEN_BODY = json.dumps({"access_token": "t0k3n"}).encode()


def test_client_answers_the_bearer_challenge_and_finds_the_manifest() -> None:
    opener = ScriptedOpener([_http_error(MANIFEST_URL, 401, CHALLENGE), _Response(200, TOKEN_BODY), _Response(200)])
    assert RegistryClient(opener=opener).manifest_exists(EXPORTER) is True
    head, token, retry = opener.requests
    assert head.get_method() == "HEAD" and head.full_url == MANIFEST_URL
    assert head.get_header("Accept", "").startswith("application/vnd.oci.image.index.v1+json")
    assert token.full_url == (
        "https://gsoci.azurecr.io/oauth2/token?service=gsoci.azurecr.io"
        "&scope=repository%3Agiantswarm%2Fredis_exporter%3Apull"
    )
    assert retry.get_method() == "HEAD" and retry.get_header("Authorization") == "Bearer t0k3n"


def test_client_reuses_the_token_for_the_same_repository() -> None:
    opener = ScriptedOpener(
        [_http_error(MANIFEST_URL, 401, CHALLENGE), _Response(200, TOKEN_BODY), _Response(200), _Response(404)]
    )
    client = RegistryClient(opener=opener)
    assert client.manifest_exists(EXPORTER) is True
    older = parse_image_reference("gsoci.azurecr.io/giantswarm/redis_exporter:v1.91.1")
    assert older is not None
    assert client.manifest_exists(older) is False
    assert len(opener.requests) == 4
    assert opener.requests[3].get_header("Authorization") == "Bearer t0k3n"


def test_client_reports_a_missing_manifest_as_absent() -> None:
    opener = ScriptedOpener(
        [_http_error(MANIFEST_URL, 401, CHALLENGE), _Response(200, TOKEN_BODY), _http_error(MANIFEST_URL, 404)]
    )
    assert RegistryClient(opener=opener).manifest_exists(EXPORTER) is False


def test_client_treats_a_digest_reference_like_a_tag() -> None:
    by_digest = parse_image_reference(f"gsoci.azurecr.io/giantswarm/redis_exporter@{DIGEST}")
    assert by_digest is not None
    opener = ScriptedOpener([_Response(200)])
    assert RegistryClient(opener=opener).manifest_exists(by_digest) is True
    assert opener.requests[0].full_url.endswith(f"/manifests/{DIGEST}")


@pytest.mark.parametrize(
    "answers, message",
    [
        ([_http_error(MANIFEST_URL, 500)], "answered HTTP 500"),
        ([_http_error(MANIFEST_URL, 401)], "without a bearer challenge"),
        (
            [_http_error(MANIFEST_URL, 401, CHALLENGE), _http_error("https://gsoci.azurecr.io/oauth2/token", 401)],
            "refused an anonymous token",
        ),
        ([_http_error(MANIFEST_URL, 401, CHALLENGE), _Response(200, b"{}")], "answered without a token"),
        (
            [_http_error(MANIFEST_URL, 401, CHALLENGE), _Response(200, TOKEN_BODY), _http_error(MANIFEST_URL, 401)],
            "be read anonymously",
        ),
        ([urllib.error.URLError("connection refused")], "connection refused"),
    ],
)
def test_client_raises_when_the_registry_cannot_answer(
    answers: List[Union[_Response, Exception]], message: str
) -> None:
    with pytest.raises(RegistryError) as excinfo:
        RegistryClient(opener=ScriptedOpener(answers)).manifest_exists(EXPORTER)
    assert message in str(excinfo.value)
