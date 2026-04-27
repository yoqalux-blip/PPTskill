param(
    [Parameter(Mandatory = $true)]
    [string]$PptPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [int]$Width = 2560
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

try {
    $resolvedPpt = (Resolve-Path -LiteralPath $PptPath).Path
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    $resolvedOutput = (Resolve-Path -LiteralPath $OutputDir).Path

    $powerPoint = New-Object -ComObject PowerPoint.Application
    $powerPoint.DisplayAlerts = 1

    try {
        $presentation = $powerPoint.Presentations.Open2007($resolvedPpt, $false, $true, $false, $true)
    }
    catch {
        $presentation = $powerPoint.Presentations.Open($resolvedPpt, $false, $true, $false)
    }
    $slideWidth = [double]$presentation.PageSetup.SlideWidth
    $slideHeight = [double]$presentation.PageSetup.SlideHeight
    $height = [int][Math]::Round($Width * $slideHeight / $slideWidth)

    foreach ($slide in $presentation.Slides) {
        $target = Join-Path $resolvedOutput ("slide-{0:D3}.png" -f $slide.SlideIndex)
        $slide.Export($target, "PNG", $Width, $height)
        Release-ComObject $slide
    }
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
