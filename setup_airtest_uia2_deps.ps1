Param(
  [string]$PocoRoot
)

if (-not $PocoRoot) {
  $PocoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
}

try {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
} catch {}

$thirdparty = Join-Path $PocoRoot 'thirdparty'
$site = Join-Path $thirdparty 'site-packages'
$whlDir = Join-Path $thirdparty 'whl'
$tmp = Join-Path $thirdparty '_tmp'

New-Item -Force -ItemType Directory -Path $thirdparty | Out-Null
New-Item -Force -ItemType Directory -Path $site | Out-Null
New-Item -Force -ItemType Directory -Path $whlDir | Out-Null
New-Item -Force -ItemType Directory -Path $tmp | Out-Null

$packages = @(
  # Core UIA2 + deps (py3.6 compatible)
  @{name='uiautomator2';       version='2.16.21'; selector='*py3-none-any.whl'},
  @{name='adbutils';           version='1.2.12';  selector='*py3-none-any.whl'},
  @{name='apkutils2';          version='1.0.0';   selector='*.tar.gz'},      # sdist
  @{name='requests';           version='2.27.1';  selector='*py2.py3-none-any.whl'},
  @{name='urllib3';            version='1.26.16'; selector='*py2.py3-none-any.whl'},
  @{name='certifi';            version='2022.12.7'; selector='*py3-none-any.whl'},
  @{name='idna';               version='3.4';     selector='*py3-none-any.whl'},
  @{name='charset-normalizer'; version='2.0.12';  selector='*py3-none-any.whl'},
  @{name='packaging';          version='21.3';    selector='*py3-none-any.whl'},
  @{name='pyparsing';          version='2.4.7';   selector='*py2.py3-none-any.whl'},
  @{name='logzero';            version='1.7.0';   selector='*py2.py3-none-any.whl'},
  @{name='filelock';           version='3.4.1';   selector='*py2.py3-none-any.whl'},
  @{name='retry';              version='0.9.2';   selector='*py2.py3-none-any.whl'},
  @{name='whichcraft';         version='0.6.1';   selector='*py2.py3-none-any.whl'},
  @{name='xmltodict';          version='0.13.0';  selector='*py2.py3-none-any.whl'},
  @{name='cigam';              version='0.0.3';   selector='*py3-none-any.whl'},
  @{name='progress';           version='1.6';     selector='*.tar.gz'},      # sdist
  @{name='colored';            version='1.4.2';   selector='*py2.py3-none-any.whl'}
)

function Get-PyPI-JSON($name, $version) {
  $url = "https://pypi.org/pypi/$name/$version/json"
  try { return Invoke-RestMethod -Uri $url -UseBasicParsing } catch { return $null }
}

function Select-Url($meta, $selector) {
  if (-not $meta) { return $null }
  foreach ($f in $meta.urls) {
    if ($f.filename -like $selector) { return $f.url }
  }
  return $null
}

function Ensure-Downloaded($name, $version, $selector) {
  $meta = Get-PyPI-JSON $name $version
  if (-not $meta) { Write-Warning "PyPI meta not found: $name==$version"; return $null }
  $url = Select-Url $meta $selector
  if (-not $url) {
    # fallback: prefer wheel if available else sdist
    $wheel = Select-Url $meta "*.whl"
    $sdist = Select-Url $meta "*.tar.gz"
    $url = $wheel; if (-not $url) { $url = $sdist }
  }
  if (-not $url) { Write-Warning "No file found for $name==$version"; return $null }
  $dst = Join-Path $tmp (Split-Path $url -Leaf)
  Write-Host "Downloading $name==$version => $(Split-Path $url -Leaf)" -ForegroundColor Green
  Invoke-WebRequest -Uri $url -OutFile $dst -UseBasicParsing
  return $dst
}

function Install-PackageArchive($path) {
  $file = Split-Path $path -Leaf
  if ($file -match '\.whl$' -or $file -match '\.zip$') {
    Write-Host "Expanding wheel $file" -ForegroundColor Yellow
    try { Expand-Archive -Force -Path $path -DestinationPath $site } catch { Write-Warning $_ }
    try { Copy-Item -Force $path $whlDir } catch {}
    return $true
  }
  if ($file -match '\.tar\.gz$') {
    $extractTo = Join-Path $tmp ([IO.Path]::GetFileNameWithoutExtension([IO.Path]::GetFileNameWithoutExtension($file)))
    New-Item -Force -ItemType Directory -Path $extractTo | Out-Null
    # Prefer tar if available (Win10+ usually has bsdtar)
    $tar = (Get-Command tar.exe -ErrorAction SilentlyContinue)
    if ($tar) {
      Write-Host "Extracting sdist with tar: $file" -ForegroundColor Yellow
      Push-Location $extractTo
      & $tar -xf $path
      Pop-Location
    } else {
      # Fallback: try .NET/PowerShell 5 limited support via System.IO.Compression (gz only) is not sufficient for tar
      Write-Warning "tar.exe not found; attempting PowerShell extraction"
      try {
        # Try using 7z if available
        $p7z = (Get-Command 7z.exe -ErrorAction SilentlyContinue)
        if ($p7z) {
          & $p7z x -so $path | & $p7z x -aoa -si -ttar -o$extractTo
        } else {
          Write-Warning "Please install 7zip or ensure tar.exe is available and re-run."
          return $false
        }
      } catch {
        Write-Warning $_; return $false
      }
    }
    # Find top-level importable package dir and copy into site-packages
    $copied = $false
    Get-ChildItem -Recurse -Directory $extractTo | ForEach-Object {
      $base = Split-Path $_.FullName -Leaf
      if ($base -in @('apkutils2','progress')) {
        $dst = Join-Path $site $base
        if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
        Copy-Item -Recurse -Force $_.FullName $dst
        Write-Host "Installed sdist package folder: $base" -ForegroundColor Cyan
        $copied = $true
      }
    }
    if (-not $copied) { Write-Warning "Could not locate package folder inside sdist: $file" }
    return $copied
  }
  Write-Warning "Unknown archive type: $file"
  return $false
}

Write-Host "PocoRoot: $PocoRoot"
Write-Host "Thirdparty: $thirdparty"
Write-Host "Site-packages: $site"

foreach ($p in $packages) {
  $name=$p.name; $ver=$p.version; $sel=$p.selector
  $arc = Ensure-Downloaded $name $ver $sel
  if ($null -ne $arc) {
    $ok = Install-PackageArchive $arc
    if (-not $ok) { Write-Warning "Install failed: $name==$ver ($arc)" }
  }
}

Write-Host "Done. thirdparty/site-packages is populated. Restart IDE and retry." -ForegroundColor Green

