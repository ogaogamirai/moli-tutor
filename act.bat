@echo off
rem Moli-Tutor: enqueue one action_request into tutor_state.json (id auto +1).
rem Usage:  act.bat --scroll-to "半環"
rem         act.bat --heading-index 26
rem         act.bat --clear-highlight
setlocal
pushd "%~dp0"
set "PY=python"
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
"%PY%" -X utf8 "%~dp0tutor_cli.py" act --state "%~dp0tutor_state.json" %*
popd
endlocal
