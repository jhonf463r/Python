' IABV v1.5 -- One-click launcher
' Double-click this file to start IABV.
' The MCP server + Cloudflare tunnel run hidden in the background.
' Only the IABV UI window is visible.
'
' To create a desktop shortcut:
'   Right-click this file > Send to > Desktop (create shortcut)

Set WshShell = CreateObject("WScript.Shell")

' Launch start_iabv.ps1 with -StartUI -Quiet in a hidden PowerShell window.
' The MCP + tunnel run in the background; only the PySide6 UI appears.
Dim scriptDir, cmd
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
cmd = "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & scriptDir & "\start_iabv.ps1"" -StartUI -Quiet"

' 0 = vbHide (no visible window), False = don't wait for it to finish
WshShell.Run cmd, 0, False
