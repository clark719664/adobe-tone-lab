param([string]$Destination = (Join-Path $PSScriptRoot 'portable-cache'))
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$Destination = (Resolve-Path -LiteralPath $Destination).Path
function Get-Pinned([string]$Url,[string]$Path,[string]$Hash) {
    if (-not (Test-Path -LiteralPath $Path)) {
        & curl.exe -L --fail --silent --show-error --max-time 600 $Url -o $Path
        if ($LASTEXITCODE -ne 0) { throw "Download failed: $Url" }
    }
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash -ne $Hash) { throw "Hash mismatch: $Path" }
}
$Package = Join-Path $Destination 'AdobeDNGConverter_x64_18_7.exe'
Get-Pinned 'https://download.adobe.com/pub/adobe/dng/win/AdobeDNGConverter_x64_18_7.exe' $Package '360B392693999094AC6D22E863DB297FB5AD299F767120F08C548EE2138CC90E'
$Signature = Get-AuthenticodeSignature -LiteralPath $Package
if ($Signature.Status -ne 'Valid' -or $Signature.SignerCertificate.Subject -notmatch 'Adobe Inc\.') { throw 'Adobe signature is not valid.' }
$Archive = Join-Path $Destination 'innoextract.zip'
Get-Pinned 'https://constexpr.org/innoextract/files/innoextract-1.9-windows.zip' $Archive '6989342C9B026A00A72A38F23B62A8E6A22CC5DE69805CF47D68AC2FEC993065'
$Extractor = Join-Path $Destination 'innoextract'
Expand-Archive -LiteralPath $Archive -DestinationPath $Extractor -Force
$Portable = Join-Path $Destination 'portable'
& (Join-Path $Extractor 'innoextract.exe') -e -I 'app\Adobe DNG Converter.exe' -I 'app\vcruntime140.dll' -I 'app\vcruntime140_1.dll' -I 'autopf\Adobe\Adobe DNG Converter\adobe_c2pa.dll' -d $Portable $Package
if ($LASTEXITCODE -ne 0) { throw 'Portable extraction failed.' }
Copy-Item -LiteralPath (Join-Path $Portable 'autopf/Adobe/Adobe DNG Converter/adobe_c2pa.dll') -Destination (Join-Path $Portable 'app/adobe_c2pa.dll') -Force
$Exe = Join-Path $Portable 'app/Adobe DNG Converter.exe'
if ((Get-FileHash -LiteralPath $Exe -Algorithm SHA256).Hash -ne '6FD0AF0D40E72AB634460FD00085A035AE7D5048BC69FBD19AE926C7E904E8A1') { throw 'Extracted executable hash mismatch.' }
Write-Output $Exe
