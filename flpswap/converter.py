"""Byte-preserving FLP version metadata patcher.

This deliberately does not claim to translate version-specific project features.
It rewrites only the FLVersion event (and FLBuild when a target build is supplied),
preserving all other event bytes exactly. This avoids PyFLP re-serialization losses,
but metadata patching alone cannot make unsupported project features compatible.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import tempfile
from typing import Any

from flpswap.flp_parser import FlpFormatError, parse_flp_metadata
from flpswap.flp_diagnostics import inventory_flp, compare_inventories


class ConversionError(RuntimeError):
    """Conversion could not be completed safely."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(data) and shift <= 28:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
    raise ConversionError("FLP contiene una longitud variable truncada o inválida.")


def _encode_varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("Variable length cannot be negative")
    result = bytearray()
    while value >= 0x80:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)


def _rewrite_version_event(raw: bytes, target_version: str) -> tuple[bytes, int, bool]:
    """Rewrite event 199 and optional fixed-size FLBuild event 159, preserving other bytes."""
    if len(raw) < 22 or raw[:4] != b"FLhd":
        raise ConversionError("No es un contenedor FLP reconocido.")
    header_len = struct.unpack_from("<I", raw, 4)[0]
    if header_len != 6 or raw[14:18] != b"FLdt":
        raise ConversionError("La cabecera FLP no tiene el formato esperado.")
    event_size = struct.unpack_from("<I", raw, 18)[0]
    if 22 + event_size != len(raw):
        raise ConversionError("El tamaño del bloque FLdt no coincide con el archivo.")
    events = raw[22:]
    out = bytearray()
    offset = 0
    version_count = 0
    build_count = 0
    parts = target_version.split(".")
    build_value = int(parts[3]) if len(parts) == 4 else None

    while offset < len(events):
        event_start = offset
        event_id = events[offset]
        offset += 1
        if event_id <= 63:
            size = 1
        elif event_id <= 127:
            size = 2
        elif event_id <= 191:
            size = 4
        else:
            size, offset = _read_varint(events, offset)
        payload_start = offset
        payload_end = payload_start + size
        if payload_end > len(events):
            raise ConversionError(f"Evento FLP {event_id} truncado.")
        payload = events[payload_start:payload_end]

        if event_id == 199:
            version_count += 1
            if version_count > 1:
                raise ConversionError("El FLP contiene varios eventos de versión; no se modificará ambiguamente.")
            encoded = target_version.encode("ascii") + b"\x00"
            out.append(event_id)
            out.extend(_encode_varint(len(encoded)))
            out.extend(encoded)
        elif event_id == 159 and build_value is not None:
            # ProjectID.FLBuild in PyFLP: DWORD + 31 = event ID 159.
            build_count += 1
            out.append(event_id)
            out.extend(struct.pack("<I", build_value))
        else:
            # Preserve every non-target event, including unknown plugin data, byte-for-byte.
            out.extend(events[event_start:payload_end])
        offset = payload_end

    if version_count != 1:
        raise ConversionError("No se encontró exactamente un evento FLVersion (ID 199).")
    if build_value is not None and build_count > 1:
        raise ConversionError("El FLP contiene varios eventos FLBuild; no se modificará ambiguamente.")

    rebuilt = bytearray(raw[:22])
    rebuilt[18:22] = len(out).to_bytes(4, "little")
    rebuilt.extend(out)
    return bytes(rebuilt), version_count, bool(build_count and build_value is not None)


def convert_flp(
    source_path: str | Path,
    output_path: str | Path,
    target_version: str,
    declared_source_version: str | None = None,
) -> dict[str, Any]:
    """Create a byte-preserving copy with the requested FL Studio version metadata.

    This is not a full semantic downgrade/upgrade. Only the version string and,
    when provided, the FLBuild event are changed. All other event bytes are preserved.
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
    if not before.saved_version:
        raise ConversionError("No se pudo detectar la versión guardada; no se ha creado ningún archivo.")

    original_hash = _sha256(source)
    raw = source.read_bytes()
    try:
        rewritten, version_count, build_updated = _rewrite_version_event(raw, target_version)
    except (ValueError, struct.error) as exc:
        raise ConversionError(f"No se pudo reescribir la versión del FLP: {exc}") from exc

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
        if not after.valid_container or after.saved_version != target_version:
            raise ConversionError("La comprobación posterior no coincide con la versión solicitada.")
        if not event_comparison["event_id_counts_match_except_version_event"]:
            raise ConversionError("Cambió el inventario de eventos; se cancela la conversión.")
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

    return {
        "status": "version_metadata_rewritten_unverified",
        "source_path": str(source),
        "output_path": str(output),
        "detected_source_version": before.saved_version,
        "declared_source_version": declared_source_version,
        "target_version": target_version,
        "source_sha256_before": original_hash,
        "source_sha256_after": _sha256(source),
        "source_preserved": _sha256(source) == original_hash,
        "input_event_count": before.event_count,
        "output_event_count": after.event_count,
        "event_inventory_before": before_inventory.to_dict(),
        "event_inventory_after": after_inventory.to_dict(),
        "event_inventory_comparison": event_comparison,
        "input_size_bytes": source.stat().st_size,
        "output_size_bytes": output.stat().st_size,
        "version_events_rewritten": version_count,
        "build_event_updated": build_updated,
        "compatibility_verified": False,
        "warnings": [
            "Se ha cambiado la versión declarada del proyecto, no se han traducido automáticamente todas las funciones del FLP.",
            "Todos los bytes de los eventos distintos de FLVersion y el FLBuild opcional se han preservado sin reserializarlos.",
            "Los plugins VST/VST3, plugins nativos, automatizaciones y eventos introducidos después de la versión destino pueden seguir siendo incompatibles.",
            "Abre la copia en la versión destino y comprueba patrones, automatizaciones, mezclador, plugins, muestras y reproducción.",
        ],
    }
