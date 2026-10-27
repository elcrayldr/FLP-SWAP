"""Conservative FLP inspector.

This module intentionally does not rewrite project bytes. FL Studio's project
format contains version-dependent structures; a generic file signature is
not enough to safely downgrade a project.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib


@dataclass(frozen=True)
class FlpInspection:
    path: str
    size_bytes: int
    sha256: str
    signature_hex: str
    signature_ascii: str
    status: str
    notes: tuple[str, ...]


def inspect_flp(path: str | Path) -> FlpInspection:
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(file_path)
    digest = hashlib.sha256()
    first = b""
    size = 0
    with file_path.open("rb") as stream:
        first = stream.read(32)
        size = len(first)
        digest.update(first)
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)

    notes = [
        "The original file was read only; no bytes were modified.",
        "The exact FL Studio version/build cannot be inferred reliably from this generic signature alone.",
        "No conversion has been performed.",
    ]
    if size < 8:
        status = "invalid_or_truncated"
        notes.append("The file is unusually small and may be truncated.")
    else:
        status = "inspected_unverified_format"
        notes.append("A full version-aware FLP parser and real-project validation are still required.")
    ascii_signature = "".join(chr(b) if 32 <= b <= 126 else "." for b in first[:16])
    return FlpInspection(
        path=str(file_path.resolve()),
        size_bytes=size,
        sha256=digest.hexdigest(),
        signature_hex=first[:16].hex(" "),
        signature_ascii=ascii_signature,
        status=status,
        notes=tuple(notes),
    )
