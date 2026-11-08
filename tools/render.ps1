param(
    [Parameter(Mandatory = $true)][string]$Commands,
    [Parameter(Mandatory = $true)][string]$Out,
    [Parameter(Mandatory = $true)][string]$Meta
)

$ErrorActionPreference = 'Stop'
Add-Type -Path (Join-Path $PSScriptRoot 'renderer\FormRenderer.cs') `
    -ReferencedAssemblies System.Drawing, System.Web.Extensions
exit [Akshara.FormRenderer]::Main(@($Commands, $Out, $Meta))
