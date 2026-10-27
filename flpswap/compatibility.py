"""Conservative compatibility assessment; this module does not rewrite FLP files."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass


_VERSION_RE = re.compile(r"^(\d+(?:\.\d+){1,3})(?:[.-]?([0-9]+))?(?:[a-zA-Z].*)?$")


@dataclass(frozen=True)
class CompatibilityAssessment:
    source_version: str | None
    target_version: str
    relation: str
    conversion_supported: bool
    status: str
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        result = asdict(self)
        result["warnings"] = list(self.warnings)
        return result


def _version_key(value: str) -> tuple[int, ...] | None:
    """Parse a dotted FL Studio version, ignoring a trailing build number for ordering."""
    match = _VERSION_RE.fullmatch(value.strip())
    if not match:
        return None
    try:
        return tuple(int(part) for part in match.group(1).split("."))
    except ValueError:
        return None


def assess_compatibility(source_version: str | None, target_version: str) -> CompatibilityAssessment:
    """Compare version labels only; never imply that a project has been converted."""
    target_key = _version_key(target_version)
    if target_key is None:
        raise ValueError(f"Unrecognized target version format: {target_version!r}")

    warnings = [
        "Esta evaluación compara etiquetas de versión; no analiza todos los eventos ni estados de plugins.",
        "No se ha modificado ni convertido el archivo FLP.",
        "Un proyecto de una versión posterior puede contener datos que la versión de destino no entienda.",
    ]
    source_key = _version_key(source_version) if source_version else None
    if not source_version or source_key is None:
        relation = "unknown"
        warnings.insert(0, "No se pudo identificar con seguridad la versión de origen.")
    elif source_key == target_key:
        relation = "same_version"
    elif source_key < target_key:
        relation = "source_older_than_target"
    else:
        relation = "source_newer_than_target"
        warnings.insert(0, "La versión de origen parece más reciente que la de destino; se requiere análisis y conversión verificada.")

    return CompatibilityAssessment(
        source_version=source_version,
        target_version=target_version,
        relation=relation,
        conversion_supported=False,
        status="assessment_only",
        warnings=tuple(warnings),
    )
