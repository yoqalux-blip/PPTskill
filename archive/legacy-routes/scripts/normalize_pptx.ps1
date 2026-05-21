param(
    [Parameter(Mandatory = $true)]
    [string]$InputPpt,

    [Parameter(Mandatory = $true)]
    [string]$OutputPpt
)

$ErrorActionPreference = "Stop"

function Release-ComObject {
    param([object]$ComObject)
    if ($null -ne $ComObject) {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($ComObject)
    }
}

$powerPoint = $null
$presentation = $null
$resolvedInput = (Resolve-Path -LiteralPath $InputPpt).Path
$outputPath = [System.IO.Path]::GetFullPath($OutputPpt)
$outputDir = Split-Path -Parent $outputPath
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

try {
    $powerPoint = New-Object -ComObject PowerPoint.Application

    try {
        $presentation = $powerPoint.Presentations.Open2007($resolvedInput, $false, $true, $false, $true)
    }
    catch {
        $presentation = $powerPoint.Presentations.Open($resolvedInput, $false, $true, $false)
    }

    $presentation.SaveCopyAs($outputPath)
    Write-Output $outputPath
}
finally {
    if ($null -ne $presentation) {
        $presentation.Close()
    }
    if ($null -ne $powerPoint) {
        $powerPoint.Quit()
    }
    Release-ComObject $presentation
    Release-ComObject $powerPoint
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
