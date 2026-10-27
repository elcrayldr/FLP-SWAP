# FLP-SWAP

Portable Windows application for inspecting FL Studio projects and attempting a best-effort structured rewrite between selected FL Studio version labels.

> **Important limitation:** FLP-SWAP does not yet provide a universal, verified compatibility converter for every FL Studio version. The current conversion engine uses PyFLP to parse and serialize the project model, sets the requested saved-version field, validates the output container, and writes a separate copy. This is a real read/serialize/write pass, but it does **not** guarantee that the target FL Studio version will open the project, preserve every plugin state, or sound identically.

## Current workflow

1. Select an input `.flp` file.
2. Choose the source version (or leave it on automatic detection).
3. Choose the target version.
4. Choose a new output filename and run **Convert copy**.
5. FLP-SWAP checks the output container and saved version, reports event counts and preserves the original file.

The version list currently includes:
- FL Studio 11.0.0, 11.1.0, 11.1.3
- FL Studio 12.0.0, 12.1.0, 12.2.0, 12.3.0, 12.4.0, 12.5.0, 12.5.1
- FL Studio 20.0.0, 20.1.0, 20.5.0, 20.6.0, 20.7.0, 20.8.0, 20.9.0, 20.9.2
- FL Studio 21.0.0, 21.1.0, 21.2.0, 21.2.3
- FL Studio 24.1.0, 24.1.2
- FL Studio 2025.1.0, 2025.2.5
- FL Studio 26.1.1, 26.1.4, 26.1.7

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

The output is `dist\FLPSwap\FLPSwap.exe`. Zip and distribute the **entire** `dist\FLPSwap` folder, not the EXE alone.

GitHub Actions builds the portable folder and publishes it as a workflow artifact.

## Dependency notice

FLP-SWAP uses [PyFLP](https://github.com/demberto/PyFLP), an unofficial FL Studio project parser/serializer distributed under GPL-3.0-or-later. Review its license and include the corresponding license/source notices when redistributing the bundled application. PyFLP is not affiliated with Image-Line.

## Safety

Keep the original FLP. Treat every output as experimental until it has been opened in the exact target FL Studio version and checked for patterns, notes, automation, mixer routing, plugin states, samples, and audible playback.
