"""Strict YAML loading helpers that fail on duplicate mapping keys.

PyYAML's SafeLoader silently keeps the last value when a mapping key is duplicated,
which for rendered Helm manifests means silently dropped configuration.
"""

from typing import Any, Dict, Optional

import yaml


class DuplicateKeyError(yaml.YAMLError):
    def __init__(self, message: str, line: int):
        super().__init__(message)
        self.line = line
        """1-based line of the duplicate key, relative to the parsed stream."""


class UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> Dict[Any, Any]:
        seen: Dict[Any, yaml.nodes.Node] = {}
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=True)
            try:
                hash(key)
            except TypeError:
                # unhashable keys are reported by SafeLoader itself
                continue
            if key in seen:
                raise DuplicateKeyError(
                    f"duplicate key '{key}' at line {key_node.start_mark.line + 1},"
                    f" column {key_node.start_mark.column + 1}"
                    f" (first defined at line {seen[key].start_mark.line + 1})",
                    key_node.start_mark.line + 1,
                )
            seen[key] = key_node
        return super().construct_mapping(node, deep)


def find_nearest_source(rendered: str, line_no: int) -> Optional[str]:
    """Map a 1-based line in 'helm template' output back to the originating template file
    using the '# Source: <path>' comments helm emits at the start of each document."""
    lines = rendered.splitlines()
    for line in reversed(lines[: min(line_no, len(lines))]):
        if line.startswith("# Source: "):
            return line[len("# Source: ") :].strip()
    return None
