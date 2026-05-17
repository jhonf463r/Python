' BURVE - IABV v1.5 -- One-click launcher
' Double-click this file (or the desktop shortcut) to start IABV.
' Daily launcher: only the IABV UI window is started.
' MCP + Cloudflare tunnel are available from start_iabv.ps1 when remote
' auditing/Devin access is explicitly needed.
'
' P0.25: this launcher never exits silently because of iabv_start.lock.
' PowerShell owns lock validation and writes startup_audit.jsonl so the
' organism can observe failed births before Python/bootstrap exists.

Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")

Dim scriptDir, iabvRoot, srcIco, dstIco

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
iabvRoot  = fso.GetParentFolderName(scriptDir)

' Ensure logs dir exists; start_iabv.ps1 writes startup_audit.jsonl there.
Dim logsDir
logsDir = fso.BuildPath(fso.BuildPath(iabvRoot, "data"), "logs")
If Not fso.FolderExists(logsDir) Then fso.CreateFolder(logsDir)

' Copy BURVE icon to scripts/ if not already there (backward compat)
srcIco = fso.BuildPath(iabvRoot, "assets\burve.ico")
dstIco = fso.BuildPath(scriptDir, "burve.ico")
If fso.FileExists(srcIco) And Not fso.FileExists(dstIco) Then
    On Error Resume Next
    fso.CopyFile srcIco, dstIco, False
    On Error GoTo 0
End If

' Launch start_iabv.ps1 with -StartUI -Quiet -UiOnly in a hidden PowerShell
' window. The PySide6 UI appears; MCP + tunnel are skipped for local use.
Dim cmd
cmd = "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & scriptDir & "\start_iabv.ps1"" -StartUI -Quiet -UiOnly"

' 0 = vbHide (no visible window), False = don't wait for it to finish
WshShell.Run cmd, 0, False
