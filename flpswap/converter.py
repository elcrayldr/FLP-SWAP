"""Best-effort semantic FLP rewrite engine.

This is NOT a universal compatibility translator. PyFLP parses and serializes the
project model; the engine changes the saved FL Studio version, round-trips the
project, validates the output, and preserves the source file. Version tagging
alone cannot make unsupported events/plugins compatible with the target DAW.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
from typing import Any

from flpswap.flp_parser import FlpFormatError, parse_flp_metadata


class ConversionError(RuntimeError):
    """Conversion could not be completed safely."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def convert_flp(
    source_path: str | Path,
    output_path: str | Path,
    target_version: str,
    declared_source_version: str | None = None,
) -> dict[str, Any]:
    """Re-serialize an FLP via PyFLP and set its saved version in an output copy.

    Returns a report that explicitly labels this as best-effort and unverified
    compatibility. The original is never modified; output must be a different path.
    """
    source = Path(source_path).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    target_version = target_version.strip()
    if not source.is_file():
        raise ConversionError(f"No existe el archivo de origen: {source}")
    if source.suffix.casefold() != ".flp" or output.suffix.casefold() != ".flp":
        raise ConversionError("El archivo de origen y el de destino deben tener extensión .flp.")
    if source == output:
        raise ConversionError("El archivo de salida debe ser una copia distinta del original.")
    if not target_version or any(ch not in "0123456789." for ch in target_version):
        raise ConversionError("La versión de destino debe tener formato numérico, por ejemplo 26.1.7.")
    parts = target_version.split(".")
    if len(parts) not in (3, 4) or any(not part.isdigit() for part in parts):
        raise ConversionError("Formato de versión no válido. Usa major.minor.patch o major.minor.patch.build.")

    try:
        before = parse_flp_metadata(source)
    except (OSError, ValueError, FlpFormatError) as exc:
        raise ConversionError(f"El archivo de origen no supera la validación FLP: {exc}") from exc
    original_hash = _sha256(source)
    actual_source_version = before.saved_version
    if not actual_source_version:
        raise ConversionError(
            "No se ha podido detectar la versión guardada en el FLP. "
            "No se convertirá a ciegas; prueba con un proyecto que contenga el evento de versión."
        )

    try:
        import pyflp
    except ImportError as exc:
        raise ConversionError(
            "Falta PyFLP. Instala las dependencias de FLP-SWAP y vuelve a intentarlo."
        ) from exc

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="flpswap_", suffix=".flp", dir=str(output.parent), delete=False
        ) as handle:
            temp_path = Path(handle.name)

        project = pyflp.parse(str(source))
        # A selected source version is an assertion from the user, not a substitute
        # for the version read from the file. Do not silently rewrite source metadata.
        project.version = target_version
        pyflp.save(project, str(temp_path))

        # Validate the serialized output before promoting it to the requested path.
        after = parse_flp_metadata(temp_path)
        if not after.valid_container or after.saved_version != target_version:
            raise ConversionError(
                "La comprobación posterior no coincide con la versión solicitada. "
                "Se ha cancelado el guardado del resultado."
            )
        if after.event_count < 1:
            raise ConversionError("El archivo resultante no contiene eventos FLP.")
        if _sha256(source) != original_hash:
            raise ConversionError("El archivo original cambió durante el proceso; se cancela la conversión.")
        if output.exists():
            raise ConversionError(
                f"El destino ya existe: {output}. Elige otro nombre para evitar sobrescribir archivos."
            )
        temp_path.replace(output)
        temp_path = None
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(
            "PyFLP no ha podido leer o reescribir el proyecto con seguridad. "
            "No se ha creado un resultado final. Detalle: " + str(exc)
        ) from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    return {
        "status": "best_effort_rewrite_unverified",
        "source_path": str(source),
        "output_path": str(output),
        "detected_source_version": actual_source_version,
        "declared_source_version": declared_source_version,
        "target_version": target_version,
        "source_sha256_before": original_hash,
        "source_sha256_after": _sha256(source),
        "source_preserved": _sha256(source) == original_hash,
        "input_event_count": before.event_count,
        "output_event_count": after.event_count,
        "input_size_bytes": source.stat().st_size,
        "output_size_bytes": output.stat().st_size,
        "compatibility_verified": False,
        "warnings": [
            "El proyecto se ha reserializado mediante un modelo semántico; esto no garantiza compatibilidad funcional con la versión destino.",
            "No se ha comprobado el estado de todos los plugins ni sus parámetros frente a la versión de destino.",
            "Abre el resultado en la versión de destino y comprueba patrones, automatizaciones, mezclador, instrumentos y efectos antes de usarlo.",
            "PyFLP es una biblioteca de terceros no oficial y su cobertura de formatos puede ser incompleta.",
        ],
    }
