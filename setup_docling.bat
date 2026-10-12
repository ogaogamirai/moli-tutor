@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  setup_docling.bat - Moli-Tutor optional feature: Docling
REM  Converts PDF / complex HTML into structured Markdown
REM  (used by tutor_cli.py ingest).
REM
REM  Usage:
REM    setup_docling.bat [install-dir]
REM    default: %LOCALAPPDATA%\moli-tutor\docling
REM    NOTE: do NOT install into a cloud-synced folder (Google Drive, OneDrive...).
REM ============================================================

set "REPO=%~dp0"
set "REQ=%REPO%requirements-docling.txt"
set "POINTER=%REPO%docling.path"

set "TARGET=%~1"

REM --- no argument and already configured -> nothing to do ---
if "%TARGET%"=="" (
  if exist "%POINTER%" (
    set /p EXISTING=<"%POINTER%"
    if exist "!EXISTING!" (
      echo [info] Docling is already configured:
      echo        !EXISTING!
      echo        Delete docling.path or pass an install dir to change it.
      goto :usage
    )
  )
  set "TARGET=%LOCALAPPDATA%\moli-tutor\docling"
)

echo [1/5] install dir: %TARGET%
if not exist "%TARGET%" mkdir "%TARGET%"

REM --- find Python 3.10-3.13 ---
set "PY="
py -3.11 -c "import sys" >nul 2>&1 && set "PY=py -3.11"
if not defined PY ( py -3.12 -c "import sys" >nul 2>&1 && set "PY=py -3.12" )
if not defined PY ( py -3.10 -c "import sys" >nul 2>&1 && set "PY=py -3.10" )
if not defined PY ( py -3.13 -c "import sys" >nul 2>&1 && set "PY=py -3.13" )
if not defined PY ( python -c "import sys" >nul 2>&1 && set "PY=python" )
if not defined PY (
  echo [error] Python 3.10-3.13 not found. Install from https://www.python.org/
  exit /b 1
)

set "VENV=%TARGET%\venv"
set "DOCLING_EXE=%VENV%\Scripts\docling.exe"

if exist "%DOCLING_EXE%" (
  echo [2/5] reusing existing venv
  goto :models
)

echo [2/5] creating venv: %VENV%
%PY% -m venv "%VENV%" || ( echo [error] failed to create venv & exit /b 1 )

echo [3/5] installing docling (first run takes a few minutes)
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
"%VENV%\Scripts\python.exe" -m pip install -r "%REQ%" || ( echo [error] pip install failed & exit /b 1 )

:models
echo [4/5] pre-downloading models for offline/portable use (~0.4GB, first run only)
if exist "%VENV%\Scripts\docling-tools.exe" (
  "%VENV%\Scripts\docling-tools.exe" models download layout tableformer rapidocr -o "%TARGET%\models"
)

echo [5/5] writing docling.path
>"%POINTER%" echo %DOCLING_EXE%

:usage
echo.
echo Usage:
echo   python -X utf8 tutor_cli.py ingest ^<pdf^> --out ^<dir^>
echo   e.g. python -X utf8 tutor_cli.py ingest "G:\path\to\book.pdf"
echo.
endlocal
