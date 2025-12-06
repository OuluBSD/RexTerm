# PowerShell script to run run_gui_shell.bat without showing console window
# This will run the batch file through a hidden window process

$ScriptPath = Join-Path $PSScriptRoot "run_gui_shell.bat"

# Check if the batch file exists
if (Test-Path $ScriptPath) {
    # Create a process start info object
    $StartInfo = New-Object System.Diagnostics.ProcessStartInfo
    $StartInfo.FileName = $ScriptPath
    $StartInfo.UseShellExecute = $true
    $StartInfo.CreateNoWindow = $true
    $StartInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden

    # Start the process with the specified settings
    $Process = [System.Diagnostics.Process]::Start($StartInfo)
    
    Write-Host "GUI Shell started without console window (Process ID: $($Process.Id))"
} else {
    Write-Host "Error: run_gui_shell.bat not found at path $ScriptPath"
    Write-Host "Current directory: $PSScriptRoot"
    Write-Host "Please make sure run_gui_shell.bat exists in the same directory as this script."
}