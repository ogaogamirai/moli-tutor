' コンソール窓を出さずにコックピットだけ起動（ショートカット用）
Set sh = CreateObject("WScript.Shell")
root = Replace(WScript.ScriptFullName, WScript.ScriptName, "")
py = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python314\pythonw.exe"
mat = "G:\マイドライブ\Projects\Teaching-materials\tropical-math"
cmd = """" & py & """ """ & root & "tutor_cockpit.py"" --state """ & root & "tutor_state.json"" --material-dir """ & mat & """ --port 8777"
sh.Environment("PROCESS")("PYTHONUTF8") = "1"
sh.Run cmd, 0, False
