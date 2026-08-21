$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path -Path $DesktopPath -ChildPath "Fx Downloader.lnk"
$ExePath = "C:\Users\INDIA TECHNOLOGY\.gemini\antigravity\scratch\hd-video-downloader\dist\Fx Downloader\Fx Downloader.exe"
$FallbackVbs = "C:\Users\INDIA TECHNOLOGY\.gemini\antigravity\scratch\hd-video-downloader\Fx Downloader.vbs"
$IconPath = "C:\Users\INDIA TECHNOLOGY\.gemini\antigravity\scratch\hd-video-downloader\static\img\logo.ico"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
if (Test-Path $ExePath) {
    $Shortcut.TargetPath = $ExePath
    $Shortcut.WorkingDirectory = [System.IO.Path]::GetDirectoryName($ExePath)
} else {
    $Shortcut.TargetPath = "wscript.exe"
    $Shortcut.Arguments = "`"$FallbackVbs`""
    $Shortcut.WorkingDirectory = "C:\Users\INDIA TECHNOLOGY\.gemini\antigravity\scratch\hd-video-downloader"
}
$Shortcut.IconLocation = "$IconPath, 0"
$Shortcut.Description = "Fx Downloader - Ultra High Quality Video & Audio Downloader"
$Shortcut.Save()

Write-Host "Desktop shortcut updated with custom icon at: $ShortcutPath"
