@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python launcher 'py' was not found. Install Python 3.11+ from python.org.
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  py -3.11 -m venv .venv
  if errorlevel 1 (
    echo ERROR: Could not create virtual environment.
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
pip install -r requirements.txt
if errorlevel 1 exit /b 1

pyinstaller --noconfirm --clean --windowed --name FLPSwap --collect-submodules flpswap --collect-all pyflp flpswap\__main__.py
if errorlevel 1 (
  echo ERROR: PyInstaller build failed.
  exit /b 1
)

echo.
echo Build complete: %CD%\dist\FLPSwap\FLPSwap.exe
echo This is a portable onedir build. Zip the entire dist\FLPSwap folder to distribute it.
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" installer\FLPSwap.iss)
exit /b 0
