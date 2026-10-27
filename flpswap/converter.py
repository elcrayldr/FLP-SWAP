"""Version-aware FLP converter using conservative, documented event migrations."""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
from typing import Any

from flpswap.flp_parser import FlpFormatError, parse_flp_metadata
from flpswap.flp_diagnostics import inventory_flp, compare_inventories
from flpswap.flp_migration import MigrationError, migrate_event_stream


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
    """Write a new FLP using version-aware rules; never overwrite the source.

    Implemented migration rules cover FL25.2+ framing (0xAC / UTF-16 version
    banner) and playlist record sizes when targeting FL24 or earlier. Unknown
    plugin/event semantics are preserved, not guessed; compatibility still
    needs opening and playback validation in the target FL Studio version.
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
        before_inventory = inventory_flp(source)
    except (OSError, ValueError, FlpFormatError) as exc:
        raise ConversionError(f"El archivo de origen no supera la validación FLP: {exc}") from exc
    if not before.saved_version and not declared_source_version:
        raise ConversionError("Este FLP no contiene un evento de versión detectable. Selecciona manualmente la versión de origen y vuelve a intentarlo.")

    original_hash = _sha256(source)
    raw = source.read_bytes()
    try:
        rewritten, migration_report = migrate_event_stream(raw, target_version)
    except (ValueError, MigrationError) as exc:
        raise ConversionError(f"No se pudo migrar el proyecto: {exc}") from exc

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ConversionError(f"El destino ya existe: {output}. Elige otro nombre para evitar sobrescribir archivos.")

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="flpswap_", suffix=".flp", dir=str(output.parent), delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(rewritten)
            handle.flush()

        after = parse_flp_metadata(temp_path)
        after_inventory = inventory_flp(temp_path)
        event_comparison = compare_inventories(before_inventory, after_inventory)
        target_parts = [int(part) for part in target_version.split(".")]
        target_supports_version_event = target_parts[0] > 1 or (target_parts[0] == 1 and (target_parts[1] > 3 or (target_parts[1] == 3 and target_parts[2] >= 9)))
        expected_saved_version = target_version if target_supports_version_event else None
        if not after.valid_container or after.saved_version != expected_saved_version:
            raise ConversionError(
                f"La validación posterior esperaba {expected_saved_version!r}, pero detectó {after.saved_version!r}."
            )
        if _sha256(source) != original_hash:
            raise ConversionError("El archivo original cambió durante el proceso.")
        temp_path.replace(output)
        temp_path = None
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"No se pudo validar la copia resultante: {exc}") from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    source_hash_after = _sha256(source)
    warnings = [
        "La conversión aplica reglas conocidas de estructura FLP; no reconstruye automáticamente parámetros privados de todos los plugins.",
        "Los eventos desconocidos se conservan salvo los marcadores FL25.2+ documentados como incompatibles con destinos anteriores a FL25.2.",
        "Los proyectos que contienen funciones exclusivas de una versión posterior pueden abrirse con funciones omitidas o no reproducir exactamente igual.",
        "Para validar compatibilidad real, abre la copia en la versión destino y comprueba patrones, playlist, automatizaciones, mezclador, plugins, muestras y reproducción.",
    ]
    if migration_report["removed_known_fl25_events"]:
        warnings.append("Se eliminaron marcadores estructurales de FL25.2+ incompatibles con la versión destino.")
    if migration_report["playlist_records_resized"]:
        warnings.append("Los clips de playlist se adaptaron al tamaño de registro documentado para la versión de destino; verifica posición, duración y offsets.")

    return {
        "status": "version_aware_migration_created_unverified",
        "source_path": str(source),
        "output_path": str(output),
        "detected_source_version": before.saved_version or declared_source_version,
        "declared_source_version": declared_source_version,
        "target_version": target_version,
        "source_sha256_before": original_hash,
        "source_sha256_after": source_hash_after,
        "source_preserved": source_hash_after == original_hash,
        "input_event_count": before.event_count,
        "output_event_count": after.event_count,
        "event_inventory_before": before_inventory.to_dict(),
        "event_inventory_after": after_inventory.to_dict(),
        "event_inventory_comparison": event_comparison,
        "migration": migration_report,
        "input_size_bytes": source.stat().st_size,
        "output_size_bytes": output.stat().st_size,
        "compatibility_verified": False,
        "warnings": warnings,
    }
