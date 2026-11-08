param(
    [Parameter(Mandatory = $true)][string]$Pdf,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [int]$MaxPages = 8,
    [int]$Width = 1240
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime] | Out-Null

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]
$asTaskAction = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction'
})[0]

function Await($operation, $resultType) {
    $method = $asTaskGeneric.MakeGenericMethod($resultType)
    $task = $method.Invoke($null, @($operation))
    $task.Wait(-1) | Out-Null
    return $task.Result
}

function AwaitAction($operation) {
    $task = $asTaskAction.Invoke($null, @($operation))
    $task.Wait(-1) | Out-Null
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$input = [System.IO.File]::OpenRead((Resolve-Path $Pdf).Path)
$random = [System.IO.WindowsRuntimeStreamExtensions]::AsRandomAccessStream($input)
$document = Await ([Windows.Data.Pdf.PdfDocument]::LoadFromStreamAsync($random)) ([Windows.Data.Pdf.PdfDocument])

$rendered = [Math]::Min([Math]::Max(0, $document.PageCount), $MaxPages)
$pages = @()
for ($index = 0; $index -lt $rendered; $index++) {
    $page = $document.GetPage($index)
    $options = New-Object Windows.Data.Pdf.PdfPageRenderOptions
    $options.DestinationWidth = [uint32]$Width
    $stream = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
    AwaitAction ($page.RenderToStreamAsync($stream, $options))
    $stream.Seek(0)
    $outPath = Join-Path $OutDir ("page_{0}.png" -f ($index + 1))
    $reader = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($stream)
    $writer = [System.IO.File]::Create($outPath)
    $reader.CopyTo($writer)
    $writer.Close()
    $reader.Close()
    $stream.Dispose()
    $height = [int][Math]::Round($page.Size.Height * ($Width / $page.Size.Width))
    $pages += [pscustomobject]@{
        no = $index + 1
        file = $outPath
        width = $Width
        height = $height
    }
}
$input.Close()
$result = [pscustomobject]@{
    total = $document.PageCount
    rendered = $rendered
    pages = $pages
}
Write-Output ($result | ConvertTo-Json -Compress -Depth 4)
