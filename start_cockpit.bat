@echo off
setlocal
pushd "%~dp0"
set "PY=%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe"
if not exist "%PY%" set "PY=pythonw"
set PYTHONUTF8=1
start "Moli-Tutor" "%PY%" "%~dp0tutor_cockpit.py" --state "%~dp0tutor_state.json"
popd
endlocal
