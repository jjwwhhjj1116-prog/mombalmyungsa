$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$renderRoot = Join-Path $repo "episodes\black-death-quarantine\renders"
$chunkRoot = Join-Path $renderRoot "chunks"
New-Item -ItemType Directory -Force -Path $chunkRoot | Out-Null

$ranges = @(
    @{ Start = 0; End = 999 },
    @{ Start = 1000; End = 1999 },
    @{ Start = 2000; End = 2999 },
    @{ Start = 3000; End = 3999 },
    @{ Start = 4000; End = 4999 },
    @{ Start = 5000; End = 5999 },
    @{ Start = 6000; End = 6692 }
)

$outputs = @()
foreach ($range in $ranges) {
    $output = Join-Path $chunkRoot ("chunk-{0:D4}-{1:D4}.mp4" -f $range.Start, $range.End)
    $outputs += $output
    & npx remotion render video/src/index.ts BlackDeathFinal $output `
        --public-dir video/public --codec h264 --crf 16 --overwrite `
        "--frames=$($range.Start)-$($range.End)" --concurrency=4 --muted
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Retrying failed range $($range.Start)-$($range.End) with concurrency 1"
        & npx remotion render video/src/index.ts BlackDeathFinal $output `
            --public-dir video/public --codec h264 --crf 16 --overwrite `
            "--frames=$($range.Start)-$($range.End)" --concurrency=1 --muted
        if ($LASTEXITCODE -ne 0) {
            throw "Remotion range failed twice: $($range.Start)-$($range.End)"
        }
    }
}

$concatList = Join-Path $chunkRoot "concat-list.txt"
$lines = $outputs | ForEach-Object { "file '$($_.Replace('\', '/'))'" }
[System.IO.File]::WriteAllLines($concatList, $lines, [System.Text.UTF8Encoding]::new($false))

$videoOnly = Join-Path $renderRoot "black-death-v1-video-only.mp4"
& ffmpeg -y -f concat -safe 0 -i $concatList -c copy -movflags +faststart $videoOnly
if ($LASTEXITCODE -ne 0) {
    throw "FFmpeg concat failed"
}

Write-Output $videoOnly
