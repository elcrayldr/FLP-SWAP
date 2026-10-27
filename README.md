# FLP SWAP

Portable Windows application for inspecting FL Studio project files, detecting installed FL Studio builds, reporting plugin availability, and progressively implementing verified project compatibility transformations.

> **Development status:** foundation/scaffolding. This repository does not yet claim that FL Studio 26 projects can be converted reliably to FL Studio 21.3.6. A valid file header or successful parse is not proof that a converted project will open or sound correctly.

## Goals
- Portable Windows x64 executable (PyInstaller).
- Detect installed FL Studio executable versions/builds where Windows metadata exposes them.
- Inspect FLP files without modifying the original.
- Keep version/build data explicit and distinguish Windows builds from macOS builds.
- Produce reports and preserve originals.
- Add conversion rules only when they are implemented and validated against real FL Studio projects.

## Run from source
Requires Python 3.11+ on Windows.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m flpswap
```

## Build portable executable
Run `build_windows.bat` on Windows. The output is placed in `dist\FLPSwap\`. GitHub Actions also builds the portable folder and publishes it as a workflow artifact.

## Current limitations
- FLP parsing is deliberately conservative; unknown binary structures are not rewritten.
- The version catalog contains known release/build references, not a complete authoritative database.
- Plugin inventory and FLP plugin-state migration are not yet implemented as a reliable conversion engine.
- No conversion is considered successful merely because the file can be read or its metadata changed.
- Real validation requires opening and checking the output in the actual target FL Studio version.

## Safety
The application never overwrites the input FLP. Treat converted projects as experimental until the report explicitly says the relevant transformation is implemented and validated.
