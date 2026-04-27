' BURVE - IABV v1.5 -- One-click launcher
' Double-click this file (or the desktop shortcut) to start IABV.
' The MCP server + Cloudflare tunnel run hidden in the background.
' Only the IABV UI window is visible.

Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")

Dim scriptDir, iabvRoot, srcIco, dstIco

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
iabvRoot  = fso.GetParentFolderName(scriptDir)

' Copy BURVE icon to scripts/ if not already there (backward compat)
srcIco = fso.BuildPath(iabvRoot, "assets\burve.ico")
dstIco = fso.BuildPath(scriptDir, "burve.ico")
If fso.FileExists(srcIco) And Not fso.FileExists(dstIco) Then
    On Error Resume Next
    fso.CopyFile srcIco, dstIco, False
    On Error GoTo 0
End If

' Launch start_iabv.ps1 with -StartUI -Quiet in a hidden PowerShell window.
' The MCP + tunnel run in the background; only the PySide6 UI appears.
Dim cmd
cmd = "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & scriptDir & "\start_iabv.ps1"" -StartUI -Quiet"

' 0 = vbHide (no visible window), False = don't wait for it to finish
WshShell.Run cmd, 0, False
