Option Explicit
Dim shell, fso, root, python, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root
python = "pythonw.exe"
If fso.FileExists(root & "\.venv\Scripts\pythonw.exe") Then python = root & "\.venv\Scripts\pythonw.exe"
command = """" & python & """ """ & root & "\launch_web.pyw" & """"
On Error Resume Next
shell.Run command, 0, False
If Err.Number <> 0 Then MsgBox "Unable to start Python. Install Python 3.10+ with NumPy and OpenCV, or select the correct .venv.", 16, "Offside Studio"
