' コンソール窓を出さずにコックピットだけ起動（ショートカット用）
Set sh = CreateObject("WScript.Shell")
root = Replace(WScript.ScriptFullName, WScript.ScriptName, "")
py = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python314\pythonw.exe"
cmd = """" & py & """ """ & root & "tutor_cockpit.py"" --state """ & root & "tutor_state.json"""
sh.Environment("PROCESS")("PYTHONUTF8") = "1"
sh.Run cmd, 0, False
