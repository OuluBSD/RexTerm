# PowerShell script to run run_gui_shell.bat with .NET Process class for maximum invisibility
# This approach has the most control over process creation

$ScriptPath = Join-Path $PSScriptRoot "run_gui_shell.bat"

if (Test-Path $ScriptPath) {
    # Define the process start info using .NET
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "cmd.exe"
    $psi.Arguments = "/c `"$ScriptPath`""
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.WorkingDirectory = $PSScriptRoot

    # Start the process
    $process = [System.Diagnostics.Process]::Start($psi)
    
    Write-Host "GUI Shell started without console window using .NET Process (Process ID: $($process.Id))"
} else {
    Write-Host "Error: run_gui_shell.bat not found at path $ScriptPath"
    Write-Host "Current directory: $PSScriptRoot"
    Write-Host "Please make sure run_gui_shell.bat exists in the same directory as this script."
}