from typing import List, Optional

import pytest
import yaml

from app_build_suite.utils.yaml_strict import DuplicateKeyError, UniqueKeyLoader, find_nearest_source

VALID_MULTI_DOC = """---
# Source: my-app/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
---
# Source: my-app/templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app
"""

DUPLICATE_TOP_LEVEL = """apiVersion: v1
kind: ConfigMap
kind: Secret
"""

DUPLICATE_NESTED = """apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: my-app
  labels:
    team: my-team
"""

DUPLICATE_IN_LIST_ITEM = """spec:
  containers:
    - name: main
      image: img:1
      name: sidecar
"""

SAME_KEY_DIFFERENT_DOCS = """---
kind: ConfigMap
---
kind: Secret
"""

EMPTY_DOCS = "---\n---\n"

SYNTAX_ERROR = "key: [unclosed\nother: 1\n  bad indent: {{\n"


def _load_all(document: str) -> List[object]:
    return list(yaml.load_all(document, Loader=UniqueKeyLoader))


def test_valid_multi_doc_loads() -> None:
    docs = _load_all(VALID_MULTI_DOC)
    assert len(docs) == 2
    assert docs[0]["kind"] == "Deployment"  # type: ignore[index]


@pytest.mark.parametrize(
    "document,duplicate_key,dup_line,first_line",
    [
        (DUPLICATE_TOP_LEVEL, "kind", 3, 2),
        (DUPLICATE_NESTED, "labels", 6, 4),
        (DUPLICATE_IN_LIST_ITEM, "name", 5, 3),
    ],
    ids=["top-level", "nested", "in-list-item"],
)
def test_duplicate_keys_raise(document: str, duplicate_key: str, dup_line: int, first_line: int) -> None:
    with pytest.raises(DuplicateKeyError) as excinfo:
        _load_all(document)
    assert f"duplicate key '{duplicate_key}'" in str(excinfo.value)
    assert f"line {dup_line}" in str(excinfo.value)
    assert f"first defined at line {first_line}" in str(excinfo.value)
    assert excinfo.value.line == dup_line


def test_same_key_in_different_documents_is_fine() -> None:
    assert len(_load_all(SAME_KEY_DIFFERENT_DOCS)) == 2


@pytest.mark.parametrize(
    "document,expected_docs", [(EMPTY_DOCS, [None, None]), ("", [])], ids=["empty-docs", "empty-stream"]
)
def test_empty_documents_are_fine(document: str, expected_docs: List[object]) -> None:
    assert _load_all(document) == expected_docs


def test_syntax_error_raises_marked_yaml_error() -> None:
    with pytest.raises(yaml.MarkedYAMLError):
        _load_all(SYNTAX_ERROR)


@pytest.mark.parametrize(
    "line_no,expected_source",
    [
        (5, "my-app/templates/deployment.yaml"),
        (10, "my-app/templates/service.yaml"),
        (1, None),
    ],
    ids=["first-doc", "second-doc", "before-any-source"],
)
def test_find_nearest_source(line_no: int, expected_source: Optional[str]) -> None:
    assert find_nearest_source(VALID_MULTI_DOC, line_no) == expected_source
