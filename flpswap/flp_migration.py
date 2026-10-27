"""Version-aware FLP event stream migration rules.

The rules in this module are intentionally narrow and evidence-based:
- FL 25.2+ opcode 0xAC has a 3-byte payload, not the classic 4 bytes.
- FL 25.2+ adds a UTF-16LE 0xC0 version banner and 0xAC marker that break
  FL 25.1.x; these are removed when targeting pre-25.2.
- Playlist clips (0xE9) use 80-byte records in FL25, 60-byte records in FL21-24,
  and 32-byte records before FL21. Older layouts retain the prefix of each record.
Other unknown/newer feature payloads are preserved and reported, not silently guessed.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct


class MigrationError(ValueError):
    pass


@dataclass(frozen=True)
class Event:
    event_id: int
    start: int
    payload_start: int
    end: int
    payload: bytes


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
    raise MigrationError("Longitud de evento FLP truncada.")


def _write_varint(value: int) -> bytes:
    out = bytearray()
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def _has_fl25_banner(raw: bytes) -> bool:
    return "FL Studio 25.".encode("utf-16le") in raw or "FL Studio 26.".encode("utf-16le") in raw


def read_events(raw: bytes) -> tuple[bytes, list[Event], bool]:
    if len(raw) < 22 or raw[:4] != b"FLhd" or raw[14:18] != b"FLdt":
        raise MigrationError("No es un contenedor FLP reconocido.")
    if struct.unpack_from("<I", raw, 4)[0] != 6:
        raise MigrationError("La cabecera FLhd no tiene el tamaño esperado.")
    length = struct.unpack_from("<I", raw, 18)[0]
    if 22 + length != len(raw):
        raise MigrationError("El tamaño del bloque FLdt no coincide con el archivo.")
    stream = raw[22:]
    special25 = _has_fl25_banner(raw)
    events: list[Event] = []
    offset = 0
    while offset < len(stream):
        start = offset
        event_id = stream[offset]
        offset += 1
        if event_id == 0xAC and special25:
            size = 3
        elif event_id <= 63:
            size = 1
        elif event_id <= 127:
            size = 2
        elif event_id <= 191:
            size = 4
        else:
            size, offset = _read_varint(stream, offset)
        payload_start = offset
        end = payload_start + size
        if end > len(stream):
            raise MigrationError(f"Evento 0x{event_id:02X} truncado en el FLP.")
        events.append(Event(event_id, start, payload_start, end, stream[payload_start:end]))
        offset = end
    return stream, events, special25


def _encode_event(event_id: int, payload: bytes, original: bytes | None = None) -> bytes:
    if event_id == 0xAC and len(payload) == 3:
        return bytes([event_id]) + payload
    if event_id <= 63:
        if len(payload) != 1:
            raise MigrationError(f"Payload incorrecto para evento 0x{event_id:02X}.")
        return bytes([event_id]) + payload
    if event_id <= 127:
        if len(payload) != 2:
            raise MigrationError(f"Payload incorrecto para evento 0x{event_id:02X}.")
        return bytes([event_id]) + payload
    if event_id <= 191:
        if len(payload) != 4:
            raise MigrationError(f"Payload incorrecto para evento 0x{event_id:02X}.")
        return bytes([event_id]) + payload
    return bytes([event_id]) + _write_varint(len(payload)) + payload


def _is_fl25_banner(event: Event) -> bool:
    return event.event_id == 0xC0 and event.payload.startswith("FL Studio".encode("utf-16le"))


def migrate_event_stream(raw: bytes, target_version: str) -> tuple[bytes, dict]:
    stream, events, source_has_fl25_format = read_events(raw)
    parts = [int(part) for part in target_version.split(".")]
    target_major = parts[0]
    target_minor = parts[1] if len(parts) > 1 else 0
    target_patch = parts[2] if len(parts) > 2 else 0
    target_build = parts[3] if len(parts) > 3 else None
    target_is_pre_25_2 = target_major < 25 or (target_major == 25 and target_minor < 2)
    target_playlist_size = 80 if target_major >= 25 else (60 if target_major >= 21 else 32)

    output = bytearray()
    version_count = 0
    build_count = 0
    removed_25_events = []
    resized_playlist_records = 0
    playlist_records = 0
    original_event_ids = []
    output_event_ids = []

    for event in events:
        event_id = event.event_id
        payload = event.payload
        original_event_ids.append(event_id)

        if event_id == 0xC7:  # FLVersion: ASCII, null-terminated
            version_count += 1
            if version_count > 1:
                raise MigrationError("Hay varios eventos FLVersion; no se modificará de forma ambigua.")
            version = ".".join(str(x) for x in parts)
            payload = version.encode("ascii") + b"\x00"
            output.extend(_encode_event(event_id, payload))
            output_event_ids.append(event_id)
            continue

        if event_id == 0x9F:  # FLBuild
            build_count += 1
            if build_count > 1:
                raise MigrationError("Hay varios eventos FLBuild; no se modificará de forma ambigua.")
            if target_build is None:
                # Do not leave a contradictory source build beside the new version.
                continue
            output.extend(_encode_event(event_id, struct.pack("<I", target_build)))
            output_event_ids.append(event_id)
            continue

        if target_is_pre_25_2 and source_has_fl25_format and event_id == 0xAC:
            removed_25_events.append("0xAC")
            continue
        if target_is_pre_25_2 and source_has_fl25_format and _is_fl25_banner(event):
            removed_25_events.append("0xC0-banner")
            continue

        if event_id == 0xE9 and source_has_fl25_format and target_playlist_size < 80:
            old_record_size = 80
            if len(payload) % old_record_size != 0:
                raise MigrationError(
                    f"El evento de playlist 0xE9 contiene {len(payload)} bytes; no es múltiplo de 80, "
                    "por lo que no se puede migrar con seguridad."
                )
            transformed = bytearray()
            for pos in range(0, len(payload), old_record_size):
                record = payload[pos:pos + old_record_size]
                transformed.extend(record[:target_playlist_size])
                playlist_records += 1
                resized_playlist_records += 1
            payload = bytes(transformed)

        output.extend(_encode_event(event_id, payload))
        output_event_ids.append(event_id)

    if version_count != 1:
        raise MigrationError("No se encontró exactamente un evento FLVersion (0xC7).")
    if build_count > 1:
        raise MigrationError("Hay varios eventos FLBuild; no se modificará de forma ambigua.")

    rebuilt = bytearray(raw[:22])
    rebuilt[18:22] = len(output).to_bytes(4, "little")
    rebuilt.extend(output)
    report = {
        "source_fl25_format_detected": source_has_fl25_format,
        "target_playlist_record_size": target_playlist_size,
        "removed_known_fl25_events": removed_25_events,
        "playlist_records_resized": resized_playlist_records,
        "playlist_records_seen": playlist_records,
        "version_events_rewritten": version_count,
        "build_event_updated": bool(build_count and target_build is not None),
        "event_count_before": len(events),
        "event_count_after": len(output_event_ids),
        "event_ids_added_or_removed": sorted(set(original_event_ids) ^ set(output_event_ids)),
        "known_rule_scope": (
            "FL25.2+ 0xAC/0xC0 compatibility and E9 clip record sizes only; "
            "unknown event/plugin semantics are not translated."
        ),
    }
    return bytes(rebuilt), report
