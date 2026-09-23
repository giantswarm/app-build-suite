"""Build step: resolves the image references of the rendered chart against their registry."""

import argparse
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, Final, Iterator, List, Optional, Set, Tuple

import configargparse
import yaml
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType

from app_build_suite.build_steps.helm_consts import context_key_rendered_chart
from app_build_suite.build_steps.steps import STEP_VALIDATE
from app_build_suite.errors import BuildError
from app_build_suite.utils.yaml_strict import UniqueKeyLoader, find_nearest_source

logger = logging.getLogger(__name__)

# The registries whose references are resolved: Giant Swarm's public registry, where every chart built here
# pulls its images from, its own builds and the mirrored third-party images alike. It answers anonymously.
CHECKED_REGISTRIES: Final[Tuple[str, ...]] = ("gsoci.azurecr.io",)

IMAGE_KEY: Final[str] = "image"
DEFAULT_REGISTRY: Final[str] = "docker.io"
DEFAULT_TAG: Final[str] = "latest"
REQUEST_TIMEOUT_SECONDS: Final[int] = 30

# Every manifest media type a registry may serve for a reference: an image index for a multi-architecture
# image, a single manifest, and the Docker schema 2 forms of both.
MANIFEST_ACCEPT: Final[str] = ", ".join(
    [
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ]
)

# A plain image reference: [registry/]repository[:tag][@digest]. Whether the first path component is a
# registry follows Docker's rule (see parse_image_reference), the regex only splits the parts.
_IMAGE_REFERENCE_RE = re.compile(
    r"^(?:(?P<registry>[A-Za-z0-9.-]+(?::[0-9]+)?)/)?"
    r"(?P<repository>[a-z0-9]+(?:[._-]+[a-z0-9]+)*(?:/[a-z0-9]+(?:[._-]+[a-z0-9]+)*)*)"
    r"(?::(?P<tag>[A-Za-z0-9_][A-Za-z0-9._-]{0,127}))?"
    r"(?:@(?P<digest>sha256:[a-f0-9]{64}))?$"
)
_CHALLENGE_PARAM_RE = re.compile(r'(\w+)="([^"]*)"')


@dataclass(frozen=True)
class ImageReference:
    reference: str
    """The reference as the manifest states it."""
    registry: str
    repository: str
    tag: str
    digest: Optional[str]

    @property
    def manifest_reference(self) -> str:
        """What the kubelet pulls: the digest when there is one, the tag otherwise."""
        return self.digest or self.tag


def parse_image_reference(value: str) -> Optional[ImageReference]:
    """Splits an image reference into its parts; None when the value is not a plain image reference
    (a glob, a template left unrendered, prose)."""
    match = _IMAGE_REFERENCE_RE.match(value)
    if match is None:
        return None
    registry = match.group("registry")
    repository = match.group("repository")
    # Docker's rule: the first path component names a registry only when it looks like a host, otherwise
    # it is the first component of a Docker Hub repository ("giantswarm/app" pulls from docker.io).
    if registry is not None and "." not in registry and ":" not in registry and registry != "localhost":
        repository = f"{registry}/{repository}"
        registry = None
    return ImageReference(
        reference=value,
        registry=registry or DEFAULT_REGISTRY,
        repository=repository,
        tag=match.group("tag") or DEFAULT_TAG,
        digest=match.group("digest"),
    )


def _image_value_nodes(node: Optional[yaml.Node]) -> Iterator[yaml.ScalarNode]:
    if isinstance(node, yaml.MappingNode):
        for key_node, value_node in node.value:
            if (
                isinstance(key_node, yaml.ScalarNode)
                and key_node.value == IMAGE_KEY
                and isinstance(value_node, yaml.ScalarNode)
            ):
                yield value_node
            else:
                yield from _image_value_nodes(value_node)
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            yield from _image_value_nodes(item)


def extract_image_references(rendered: str) -> Dict[str, Set[str]]:
    """Every string value of an `image` key in the rendered manifests, wherever it sits (a pod's containers
    and init containers, a custom resource's own spec), mapped to the templates it renders from."""
    found: Dict[str, Set[str]] = {}
    for document in yaml.compose_all(rendered, Loader=UniqueKeyLoader):  # nosec, safe subclass
        for value_node in _image_value_nodes(document):
            source = find_nearest_source(rendered, value_node.start_mark.line + 1) or "unknown template"
            found.setdefault(value_node.value, set()).add(source)
    return found


class RegistryError(Exception):
    """The registry could not say whether a manifest exists."""


class RegistryClient:
    """Resolves manifests through the OCI distribution API, anonymously: a `HEAD` on the manifest, and
    when the registry challenges, the bearer token its challenge names."""

    def __init__(self, opener: Callable[..., Any] = urllib.request.urlopen) -> None:
        self._open = opener
        self._tokens: Dict[Tuple[str, str], str] = {}

    def manifest_exists(self, image: ImageReference) -> bool:
        url = f"https://{image.registry}/v2/{image.repository}/manifests/{image.manifest_reference}"
        headers = {"Accept": MANIFEST_ACCEPT}
        scope = (image.registry, image.repository)
        if scope in self._tokens:
            headers["Authorization"] = f"Bearer {self._tokens[scope]}"
        status, challenge = self._head(url, headers)
        if status == 401 and scope not in self._tokens:
            if not challenge:
                raise RegistryError(f"{image.registry} refused the request without a bearer challenge")
            self._tokens[scope] = self._token(challenge)
            headers["Authorization"] = f"Bearer {self._tokens[scope]}"
            status, _ = self._head(url, headers)
        if status == 200:
            return True
        if status == 404:
            return False
        if status == 401:
            raise RegistryError(f"{image.registry} does not let {image.repository} be read anonymously")
        raise RegistryError(f"{image.registry} answered HTTP {status} for {url}")

    def _head(self, url: str, headers: Dict[str, str]) -> Tuple[int, Optional[str]]:
        request = urllib.request.Request(url, headers=headers, method="HEAD")
        try:
            with self._open(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return response.status, None
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("WWW-Authenticate")
        except urllib.error.URLError as e:
            raise RegistryError(f"{url}: {e.reason}") from e

    def _token(self, challenge: str) -> str:
        params = dict(_CHALLENGE_PARAM_RE.findall(challenge))
        realm = params.get("realm")
        if not realm:
            raise RegistryError(f"cannot parse the bearer challenge '{challenge}'")
        query = urllib.parse.urlencode({key: params[key] for key in ("service", "scope") if key in params})
        request = urllib.request.Request(f"{realm}?{query}")
        try:
            with self._open(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                body = json.loads(response.read())
        except urllib.error.HTTPError as e:
            raise RegistryError(f"{realm} refused an anonymous token: HTTP {e.code}") from e
        except (urllib.error.URLError, ValueError) as e:
            raise RegistryError(f"{realm}: {e}") from e
        token = body.get("token") or body.get("access_token")
        if not token:
            raise RegistryError(f"{realm} answered without a token")
        return str(token)


class HelmImageReferenceValidator(BuildStep):
    """
    Resolves every image reference the rendered chart pulls from a checked registry and fails the build when
    the registry does not carry the tag or digest: a chart published like that cannot start its pods, and a
    bump of a mirrored third-party image tag that the mirror has not copied yet ships exactly that.
    """

    def __init__(self, registry_client: Optional[RegistryClient] = None) -> None:
        self._registry_client = registry_client or RegistryClient()

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_VALIDATE}

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "--disable-helm-image-reference-validator",
            required=False,
            default=False,
            action="store_true",
            help="Disable resolving the image references of the rendered chart against"
            f" {', '.join(CHECKED_REGISTRIES)}.",
        )

    def run(self, config: argparse.Namespace, context: Context) -> None:
        if config.disable_helm_image_reference_validator:
            logger.info("Image reference validation is disabled, skipping.")
            return
        rendered = context.get(context_key_rendered_chart)
        if rendered is None:
            logger.warning(
                "The build context holds no rendered chart (the helm template validator is disabled or did not"
                " run), so the image references are not checked."
            )
            return
        try:
            references = extract_image_references(rendered)
        except yaml.YAMLError as e:
            raise BuildError(self.name, f"Cannot parse the rendered chart: {e}")

        checked = 0
        problems: List[str] = []
        for value in sorted(references):
            templates = ", ".join(sorted(references[value]))
            image = parse_image_reference(value)
            if image is None:
                logger.debug(f"'{value}' is not an image reference, skipping (template: {templates}).")
                continue
            if image.registry not in CHECKED_REGISTRIES:
                logger.debug(f"'{value}' is on {image.registry}, which is not checked (template: {templates}).")
                continue
            try:
                exists = self._registry_client.manifest_exists(image)
            except RegistryError as e:
                problems.append(f"'{value}' could not be resolved: {e} (template: {templates})")
                continue
            checked += 1
            if exists:
                logger.info(f"'{value}' exists (template: {templates}).")
            else:
                problems.append(f"'{value}' does not exist in {image.registry} (template: {templates})")

        if problems:
            for line in problems:
                logger.error(line)
            for line in self._hints():
                logger.error(line)
            raise BuildError(self.name, f"{len(problems)} image reference(s) cannot be pulled: {'; '.join(problems)}")
        logger.info(f"{checked} image reference(s) resolved in {', '.join(CHECKED_REGISTRIES)}, all present.")

    @staticmethod
    def _hints() -> List[str]:
        return [
            "hint: a tag the registry does not carry is either not published yet (an image this pipeline"
            " builds: the chart job must 'require' the image job) or not mirrored yet (a third-party image:"
            " the mirror must carry the tag before the chart references it).",
            "hint: '--disable-helm-image-reference-validator' skips this check; use it only for a chart whose"
            " images are deliberately absent at build time.",
        ]
