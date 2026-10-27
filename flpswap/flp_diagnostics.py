"""Low-level diagnostics for FL Studio project event streams.

This module intentionally reports structural facts only. Event IDs are not treated as
fully understood feature labels: undocumented IDs must not be guessed or rewritten.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import hashlib
import struct
from typing import Any


@dataclass(frozen=True)
class EventInventory:
    file_size_bytes: int
    sha256: str
    format_id: int
    channel_count: int
    ppq: int
    event_bytes: int
    event_count: int
    event_id_counts: dict[int, int]
    event_payload_bytes_by_id: dict[int, int]
    version_payloads: tuple[str, ...]
    event_ids_needing_mapping_review: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_size_bytes": self.file_size_bytes,
            "sha256": self.sha256,
            "format_id": self.format_id,
            "channel_count": self.channel_count,
            "ppq": self.ppq,
            "event_bytes": self.event_bytes,
            "event_count": self.event_count,
            "event_id_counts": {str(k): v for k, v in sorted(self.event_id_counts.items())},
            "event_payload_bytes_by_id": {
                str(k): v for k, v in sorted(self.event_payload_bytes_by_id.items())
            },
            "version_payloads": list(self.version_payloads),
            "event_ids_needing_mapping_review": list(self.event_ids_needing_mapping_review),
        }


def _varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(data) and shift <= 28:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
    raise ValueError("Tamaño de evento variable truncado o inválido.")


def inventory_flp(path: str | Path) -> EventInventory:
    """Read FLP container and count event IDs without mutating the project."""
    file_path = Path(path)
    raw = file_path.read_bytes()
    if len(raw) < 22 or raw[:4] != b"FLhd":
        raise ValueError("No es un contenedor FLP reconocido (falta FLhd).")
    header_size = struct.unpack_from("<I", raw, 4)[0]
    if header_size != 6:
        raise ValueError(f"Cabecera FLhd no compatible: {header_size}.")
    format_id, channel_count, ppq = struct.unpack_from("<HHH", raw, 8)
    if raw[14:18] != b"FLdt":
        raise ValueError("No se encuentra el bloque FLdt.")
    data_size = struct.unpack_from("<I", raw, 18)[0]
    start = 22
    end = start + data_size
    if end != len(raw):
        raise ValueError(
            f"El tamaño declarado de FLdt ({data_size}) no coincide con el archivo "
            f"({len(raw) - start} bytes de datos)."
        )

    events = raw[start:end]
    has_fl25_banner = "FL Studio 25.".encode("utf-16le") in raw or "FL Studio 26.".encode("utf-16le") in raw
    offset = 0
    counts: Counter[int] = Counter()
    payload_sizes: Counter[int] = Counter()
    versions: list[str] = []
    while offset < len(events):
        event_id = events[offset]
        offset += 1
        if event_id == 0xAC and has_fl25_banner:
            size = 3
        elif event_id <= 63:
            size = 1
        elif event_id <= 127:
            size = 2
        elif event_id <= 191:
            size = 4
        else:
            size, offset = _varint(events, offset)
        event_end = offset + size
        if event_end > len(events):
            raise ValueError(f"Evento {sum(counts.values()) + 1} (ID {event_id}) truncado.")
        payload = events[offset:event_end]
        counts[event_id] += 1
        payload_sizes[event_id] += len(payload)
        if event_id == 199:
            candidate = payload.rstrip(b"\x00").decode("ascii", errors="ignore").strip()
            if candidate and any(ch.isdigit() for ch in candidate):
                versions.append(candidate)
        offset = event_end

    # IDs >= 200 are surfaced for migration-rule review. They are not labelled
    # unsupported: many are legitimate FL Studio events, but this app has no
    # complete semantic mapping for all of them.
    needs_review = tuple(sorted(event_id for event_id in counts if event_id >= 200))
    return EventInventory(
        file_size_bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
        format_id=format_id,
        channel_count=channel_count,
        ppq=ppq,
        event_bytes=data_size,
        event_count=sum(counts.values()),
        event_id_counts=dict(counts),
        event_payload_bytes_by_id=dict(payload_sizes),
        version_payloads=tuple(versions),
        event_ids_needing_mapping_review=needs_review,
    )


def compare_inventories(before: EventInventory, after: EventInventory) -> dict[str, Any]:
    """Compare event ID counts; this is a guardrail, not proof of semantic equivalence."""
    all_ids = sorted(set(before.event_id_counts) | set(after.event_id_counts))
    changes = [
        {
            "event_id": event_id,
            "before": before.event_id_counts.get(event_id, 0),
            "after": after.event_id_counts.get(event_id, 0),
        }
        for event_id in all_ids
        if before.event_id_counts.get(event_id, 0) != after.event_id_counts.get(event_id, 0)
    ]
    return {
        "event_id_counts_match_except_version_event": not changes,
        "event_id_count_changes": changes,
        "input_event_count": before.event_count,
        "output_event_count": after.event_count,
        "input_sha256": before.sha256,
        "output_sha256": after.sha256,
        "note": "Matching event counts do not prove that parameter payloads or playback are equivalent.",
    }
