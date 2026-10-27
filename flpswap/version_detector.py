"""Best-effort local FL Studio installation discovery for Windows."""
from dataclasses import dataclass
from pathlib import Path
import os
import platform
import re
import subprocess


@dataclass(frozen=True)
class Installation:
    executable: str
    file_version: str | None
    source: str


def _candidate_paths() -> list[Path]:
    candidates: list[Path] = []
    roots = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("LOCALAPPDATA"),
    ]
    for root in filter(None, roots):
        base = Path(root)
        candidates.extend([
            base / "Image-Line" / "FL Studio" / "FL64.exe",
            base / "Image-Line" / "FL Studio" / "FL.exe",
            base / "FL Studio" / "FL64.exe",
            base / "FL Studio" / "FL.exe",
        ])
    # Avoid recursively scanning whole drives; inspect only known installation roots.
    return candidates


def _windows_file_version(path: Path) -> str | None:
    if platform.system() != "Windows":
        return None
    # PowerShell reads Windows file metadata; failures simply leave version unknown.
    script = (
        "$p = (Get-Item -LiteralPath $args[0]).VersionInfo; "
        "if ($p.FileVersion) { $p.FileVersion }"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script, str(path)],
            capture_output=True, text=True, timeout=8, check=False,
        )
        value = result.stdout.strip()
        return value or None
    except (OSError, subprocess.SubprocessError):
        return None


def detect_installations() -> list[Installation]:
    found: dict[str, Installation] = {}
    for candidate in _candidate_paths():
        if candidate.is_file():
            resolved = str(candidate.resolve())
            found[resolved.casefold()] = Installation(
                executable=resolved,
                file_version=_windows_file_version(candidate),
                source="known installation path",
            )
    # Optional registry query is intentionally best-effort and read-only.
    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["where.exe", "FL64.exe"],
                capture_output=True, text=True, timeout=5, check=False,
            )
            for raw in result.stdout.splitlines():
                candidate = Path(raw.strip())
                if candidate.is_file():
                    resolved = str(candidate.resolve())
                    found.setdefault(resolved.casefold(), Installation(
                        executable=resolved,
                        file_version=_windows_file_version(candidate),
                        source="PATH",
                    ))
        except (OSError, subprocess.SubprocessError):
            pass
    return sorted(found.values(), key=lambda item: item.executable.casefold())
