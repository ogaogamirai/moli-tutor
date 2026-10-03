@echo off
chcp 65001 >nul
setlocal
pushd "%~dp0"
set "PY=%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe"
if not exist "%PY%" set "PY=pythonw"
set PYTHONUTF8=1
set "MAT=G:\マイドライブ\Projects\Teaching-materials\tropical-math"
echo 古いウィンドウだけ閉じても 8777 は残ります。更新が効かないときは stop_cockpit.bat を先に実行。
start "Moli-Tutor" "%PY%" "%~dp0tutor_cockpit.py" --state "%~dp0tutor_state.json" --material-dir "%MAT%" --port 8777
popd
endlocal
