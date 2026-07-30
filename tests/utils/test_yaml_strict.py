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

# The YAML 1.1 'value' tag: a plain '=' scalar. Taken from the upstream prometheus-operator
# AlertmanagerConfig CRD 'matchType' enum. Only the bare '=' resolves to the tag; '=~' is a
# plain string, and '!=' / '!~' have to be quoted because a leading '!' reads as a tag.
VALUE_TAG_ENUM = """enum:
- '!='
- =
- =~
- '!~'
"""

# The YAML 1.1 'merge' tag in key position. Plain yaml.safe_load handles this via
# SafeConstructor.flatten_mapping, so UniqueKeyLoader must not regress it.
MERGE_KEY = """base: &base
  a: 1
child:
  <<: *base
  c: 2
"""

# The same 'merge' tag reached from value position, where flatten_mapping never sees it.
MERGE_TAG_IN_LIST = """enum:
- <<
"""

# A duplicate alongside the tags above, guarding that the fix doesn't weaken detection.
DUPLICATE_WITH_VALUE_TAG = """enum:
- =
kind: ConfigMap
kind: Secret
"""


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
    "document,expected_docs",
    [
        (VALUE_TAG_ENUM, [{"enum": ["!=", "=", "=~", "!~"]}]),
        (MERGE_KEY, [{"base": {"a": 1}, "child": {"a": 1, "c": 2}}]),
        (MERGE_TAG_IN_LIST, [{"enum": ["<<"]}]),
    ],
    ids=["value-tag-enum", "merge-key", "merge-tag-in-list"],
)
def test_yaml_11_tags_load_without_error(document: str, expected_docs: List[object]) -> None:
    """PyYAML resolves the YAML 1.1 'value' ('=') and 'merge' ('<<') tags but SafeConstructor
    registers no constructor for either, so these used to raise ConstructorError."""
    assert _load_all(document) == expected_docs


def test_duplicate_detection_still_works_alongside_value_tag() -> None:
    with pytest.raises(DuplicateKeyError) as excinfo:
        _load_all(DUPLICATE_WITH_VALUE_TAG)
    assert "duplicate key 'kind'" in str(excinfo.value)


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
