# Alternative PowerShell script to run run_gui_shell.bat without showing console window
# This approach uses WScript.Shell to run the command invisibly

$ScriptPath = Join-Path $PSScriptRoot "run_gui_shell.bat"

if (Test-Path $ScriptPath) {
    # Create a WScript Shell object
    $WSHShell = New-Object -ComObject WScript.Shell
    
    # Run the batch file with window style 0 (hidden)
    $WSHShell.Run($ScriptPath, 0, $false)
    
    Write-Host "GUI Shell started invisibly via WScript (hidden window mode)"
} else {
    Write-Host "Error: run_gui_shell.bat not found at path $ScriptPath"
    Write-Host "Current directory: $PSScriptRoot"
    Write-Host "Please make sure run_gui_shell.bat exists in the same directory as this script."
}