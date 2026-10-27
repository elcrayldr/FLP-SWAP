"""Known FL Studio release/build references.

These entries are reference data, not proof that every FLP was created by
that exact build. Windows and macOS builds must never be conflated.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Release:
    version: str
    platform: str
    build: Optional[str] = None
    date: Optional[str] = None
    channel: str = "release"
    source: Optional[str] = None


RELEASES = (
    Release("20.8.3", "windows", "2304"),
    Release("21.0.3", "windows", "3517", "2023-04-12", source="https://forum.image-line.com/viewtopic.php?t=302819"),
    Release("21.0.3", "macos", "3036", "2023-04-12", source="https://forum.image-line.com/viewtopic.php?t=302819"),
    Release("21.2.2", "windows", "3914", source="https://www.neowin.net/software/fl-studio-2122-build-3914/"),
    Release("21.2.2", "macos", "3470"),
    Release("21.2.3", "windows", "4004", "2024-02-06", source="https://forum.image-line.com/viewtopic.php?t=322575"),
    Release("21.2.3", "macos", "3586", "2024-02-06", source="https://forum.image-line.com/viewtopic.php?t=322575"),
    Release("25.1.1", "windows", date="2025-07-17", source="https://forum.image-line.com/viewtopic.php?t=335051"),
    Release("25.1.5", "windows", date="2025-09-08"),
    Release("25.2", "windows", date="2025-11-25"),
    Release("26.1.0", "windows", "5530", "2026-07-07", source="https://forum.image-line.com/viewtopic.php?p=2065297"),
    Release("26.1.0", "macos", "5294", "2026-07-07", source="https://forum.image-line.com/viewtopic.php?p=2065297"),
    Release("26.1.3", "windows", "5570", "2026-07-27", source="https://forum.image-line.com/viewtopic.php?t=341668"),
    Release("26.1.3", "macos", "5336", "2026-07-27", source="https://forum.image-line.com/viewtopic.php?t=341668"),
    Release("26.1.4", "windows", "5589", "2026-08-10", source="https://forum.image-line.com/viewtopic.php?t=341850"),
    Release("26.1.4", "macos", "5356", "2026-08-10", source="https://forum.image-line.com/viewtopic.php?t=341850"),
    Release("26.1.5", "windows", "5618", "2026-08-24", source="https://forum.image-line.com/viewtopic.php?t=342068"),
    Release("26.1.5", "macos", "5384", "2026-08-24", source="https://forum.image-line.com/viewtopic.php?t=342068"),
    Release("26.1.6", "windows", "5639", "2026-09-07", source="https://forum.image-line.com/viewtopic.php?t=342331"),
    Release("26.1.6", "macos", "5406", "2026-09-07", source="https://forum.image-line.com/viewtopic.php?t=342331"),
    Release("26.1.7", "windows", "5653", "2026-10-01", source="https://forum.image-line.com/viewtopic.php?t=342646"),
    Release("26.1.7", "macos", "5419", "2026-10-01", source="https://forum.image-line.com/viewtopic.php?t=342646"),
    Release("26.1.7b", "windows", "5654", "2026-10-12", channel="beta"),
    Release("26.1.7b", "macos", "5421", "2026-10-12", channel="beta"),
)


def find_release(version: str, platform: str, build: Optional[str] = None) -> Optional[Release]:
    """Return an exact matching catalog entry; never guess a missing build."""
    candidates = [
        r for r in RELEASES
        if r.version.casefold() == version.casefold()
        and r.platform.casefold() == platform.casefold()
    ]
    if build is not None:
        candidates = [r for r in candidates if r.build == str(build)]
    return candidates[0] if len(candidates) == 1 else None
