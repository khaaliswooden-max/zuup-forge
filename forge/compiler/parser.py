"""
Platform Specification Parser

Loads YAML platform specs, validates against the DSL schema,
and produces typed PlatformSpec objects for the compiler.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from forge.compiler.spec_schema import PlatformSpec


class SpecParseError(Exception):
    """Raised when a platform spec fails to parse or validate."""

    def __init__(self, spec_path: str, errors: list[dict[str, Any]]):
        self.spec_path = spec_path
        self.errors = errors
        msg = f"Failed to parse {spec_path}:\n"
        for err in errors:
            loc = " → ".join(str(part) for part in err.get("loc", []))
            msg += f"  [{loc}] {err['msg']}\n"
        super().__init__(msg)


def load_spec(path: str | Path) -> PlatformSpec:
    """
    Load and validate a platform specification from a YAML file.

    Args:
        path: Path to the .platform.yaml file

    Returns:
        Validated PlatformSpec object

    Raises:
        SpecParseError: If the spec is invalid
        FileNotFoundError: If the file doesn't exist
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Spec file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise SpecParseError(str(path), [{"loc": [], "msg": "Empty spec file"}])

    try:
        spec = PlatformSpec(**raw)
    except ValidationError as e:
        raise SpecParseError(str(path), e.errors()) from e

    # Post-validation: check entity relation targets exist
    entity_names = {entity.name for entity in spec.entities}
    for entity in spec.entities:
        for rel in entity.relations:
            if rel.target not in entity_names:
                raise SpecParseError(str(path), [{
                    "loc": ["entities", entity.name, "relations", rel.target],
                    "msg": f"Relation target '{rel.target}' not found in entities",
                }])

    # Post-validation: check AI guardrail references
    guardrail_names = {g.name for g in spec.ai.guardrails}
    for model in spec.ai.models:
        for guard_ref in model.guardrails:
            if guard_ref not in guardrail_names:
                raise SpecParseError(str(path), [{
                    "loc": ["ai", "models", model.name, "guardrails", guard_ref],
                    "msg": f"Guardrail '{guard_ref}' not found in ai.guardrails",
                }])

    return spec


def load_all_specs(specs_dir: str | Path) -> dict[str, PlatformSpec]:
    """
    Load all platform specs from a directory.

    Returns:
        Dict mapping platform name to PlatformSpec
    """
    specs_dir = Path(specs_dir)
    specs = {}

    for spec_file in sorted(specs_dir.glob("*.platform.yaml")):
        spec = load_spec(spec_file)
        specs[spec.platform.name] = spec

    return specs
