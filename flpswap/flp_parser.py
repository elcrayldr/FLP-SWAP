"""Minimal, read-only parser for the documented FLP container and event framing.

This is intentionally not a project downgrade engine. It validates the outer FLhd/FLdt
container and extracts only the version event when its representation is unambiguous.
Unknown events are skipped, never rewritten.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct


@dataclass(frozen=True)
class FlpMetadata:
    valid_container: bool
    header_length: int | None
    format_id: int | None
    channel_count: int | None
    ppq: int | None
    event_bytes: int | None
    event_count: int
    saved_version: str | None
    warnings: tuple[str, ...]


class FlpFormatError(ValueError):
    """Raised when the file does not match the expected FLP container framing."""


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
    raise FlpFormatError("Invalid or truncated variable-length event size.")


def parse_flp_metadata(path: str | Path) -> FlpMetadata:
    """Read basic FLP header/event metadata without changing the file."""
    file_path = Path(path)
    raw = file_path.read_bytes()
    if len(raw) < 22:
        raise FlpFormatError("File is too small to contain a complete FLhd/FLdt header.")
    if raw[:4] != b"FLhd":
        raise FlpFormatError("Missing FLhd signature; this is not a recognized FLP container.")
    header_length = struct.unpack_from("<I", raw, 4)[0]
    if header_length != 6:
        raise FlpFormatError(f"Unexpected FLhd header length: {header_length} (expected 6).")
    format_id, channel_count, ppq = struct.unpack_from("<HHH", raw, 8)
    data_offset = 14
    if raw[data_offset:data_offset + 4] != b"FLdt":
        raise FlpFormatError("Missing FLdt data chunk after the FLhd header.")
    data_length = struct.unpack_from("<I", raw, data_offset + 4)[0]
    event_start = data_offset + 8
    event_end = event_start + data_length
    if event_end > len(raw):
        raise FlpFormatError(
            f"FLdt declares {data_length} event bytes, but the file ends {len(raw) - event_start} bytes after the data start."
        )
    if event_end != len(raw):
        trailing = len(raw) - event_end
        warnings = [f"{trailing} trailing byte(s) after the declared FLdt chunk."]
    else:
        warnings = []

    events = raw[event_start:event_end]
    offset = 0
    count = 0
    saved_version = None
    while offset < len(events):
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
        end = offset + size
        if end > len(events):
            raise FlpFormatError(f"Event {count + 1} (ID {event_id}) extends past the FLdt chunk.")
        payload = events[offset:end]
        if event_id == 199 and saved_version is None:
            candidate = payload.rstrip(b"\\x00").decode("ascii", errors="ignore").strip()
            # Do not report arbitrary binary data as a version string.
            if candidate and any(ch.isdigit() for ch in candidate) and all(
                ch.isdigit() or ch in ".-+abrc " for ch in candidate.lower()
            ):
                saved_version = candidate
        offset = end
        count += 1

    return FlpMetadata(
        valid_container=True,
        header_length=header_length,
        format_id=format_id,
        channel_count=channel_count,
        ppq=ppq,
        event_bytes=data_length,
        event_count=count,
        saved_version=saved_version,
        warnings=tuple(warnings),
    )
