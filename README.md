# FLP-SWAP

Portable Windows application for inspecting FL Studio projects and attempting a best-effort structured rewrite between selected FL Studio version labels.

> **Important limitation:** FLP-SWAP does not yet provide a universal, verified compatibility converter for every FL Studio version. The current conversion engine uses PyFLP to parse and serialize the project model, sets the requested saved-version field, validates the output container, and writes a separate copy. This is a real read/serialize/write pass, but it does **not** guarantee that the target FL Studio version will open the project, preserve every plugin state, or sound identically.

## Current workflow

1. Select an input `.flp` file.
2. Choose the source version (or leave it on automatic detection).
3. Choose the target version.
4. Choose a new output filename and run **Convert copy**.
5. FLP-SWAP checks the output container and saved version, reports event counts and preserves the original file.

The version selectors include all **110 release labels** requested for this project, from FruityLoops 1.0.0 through FL Studio 2026.1.7. This includes historical 1.x–3.x FruityLoops versions, FL Studio 4–21 releases, 2024–2026 marketing-year labels, and the explicit build variants supplied for 12.5.1, 20.6.2, 20.8.3, 20.8.4, 20.9.2, and 2025 releases.

The complete UI catalog is maintained in `flpswap/fl_versions.py`. Marketing-year labels and explicit build labels are mapped to dotted version/build values where specified. These are selectable labels; their presence does not mean FLP-SWAP can recreate or validate every historical FL Studio binary or guarantee cross-version compatibility.

## What the current engine does

- Parses the project with the third-party PyFLP semantic model.
- Re-serializes that model to a new FLP file and sets its stored version to the selected target.
- Checks that the output container can be parsed and that its stored version matches the requested target.
- Never overwrites the source file.
- Reports that compatibility is **not verified** and warns that plugin states and newer/older event semantics may not map across versions.

## What it does not yet do

- It does not have a complete mapping of every event, native plugin, VST/VST3 plugin state, automation feature, or project feature across FL Studio 11–26.
- It does not automatically replace unsupported plugins with equivalent instruments/effects.
- A successful save and a valid FLP container do not prove that the target FL Studio can open or correctly play the project.
- Older versions may reject newer project data even when the stored version label has changed.
- Newer versions may reinterpret or omit data from older projects; test each result in FL Studio and compare playback.

## Build portable Windows app

Requires Python 3.11+ on Windows:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m flpswap
```

Build:

```bat
build_windows.bat
```

The portable output is `dist\FLPSwap\FLPSwap.exe`. Zip and distribute the **entire** `dist\FLPSwap` folder, not the EXE alone. If Inno Setup 6 is installed, the local build script also creates an installer in `dist\installer`.

GitHub Actions builds the portable folder and Windows installer. Open [Actions](https://github.com/elcrayldr/FLP-SWAP/actions), choose the latest successful run, and download `FLPSwap-Windows-Portable` or `FLPSwap-Windows-Installer` from Artifacts.

## Dependency notice

FLP-SWAP uses [PyFLP](https://github.com/demberto/PyFLP), an unofficial FL Studio project parser/serializer distributed under GPL-3.0-or-later. Review its license and include the corresponding license/source notices when redistributing the bundled application. PyFLP is not affiliated with Image-Line.

## Safety

Keep the original FLP. Treat every output as experimental until it has been opened in the exact target FL Studio version and checked for patterns, notes, automation, mixer routing, plugin states, samples, and audible playback.
