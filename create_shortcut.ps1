$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path -Path $DesktopPath -ChildPath "Fx Downloader.lnk"
$TargetDir = "C:\Users\INDIA TECHNOLOGY\.gemini\antigravity\scratch\hd-video-downloader"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = "`"$TargetDir\Fx Downloader.vbs`""
$Shortcut.WorkingDirectory = $TargetDir
$Shortcut.Description = "Fx Downloader - Ultra High Quality Video & Audio Downloader"
$Shortcut.Save()

Write-Host "Desktop shortcut created successfully at: $ShortcutPath"
