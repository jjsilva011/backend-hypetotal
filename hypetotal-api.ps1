#requires -Version 5.1
param([string]$HypeTotalApiBase = $env:HYPETOTAL_API_BASE)

if (-not $HypeTotalApiBase -or [string]::IsNullOrWhiteSpace($HypeTotalApiBase)) {
  $HypeTotalApiBase = "https://api.hypetotal.com"
}
$script:HTApiBase = $HypeTotalApiBase.TrimEnd('/')

function _Invoke-Api {
  param(
    [Parameter(Mandatory)][ValidateSet("GET","POST","PATCH","DELETE")] [string]$Method,
    [Parameter(Mandatory)][string]$Path,
    [string]$BodyJson
  )
  $uri = "$script:HTApiBase$Path"
  try {
    if ($PSBoundParameters.ContainsKey("BodyJson")) {
      return Invoke-RestMethod -Method $Method -Uri $uri -ContentType "application/json" -Body $BodyJson
    } else {
      return Invoke-RestMethod -Method $Method -Uri $uri
    }
  } catch {
    $resp = $_.Exception.Response
    if ($resp -and $resp.GetResponseStream()) {
      $reader = New-Object IO.StreamReader($resp.GetResponseStream())
      $errText = $reader.ReadToEnd()
    } else {
      $errText = ($_ | Out-String)
    }
    throw "API error: $Method $uri`n$errText"
  }
}

function New-Product {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Name,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Sku,
    [Parameter(Mandatory)][ValidateRange(0,2147483647)][int]$PriceCents,
    [ValidateRange(0,2147483647)][int]$Stock = 0,
    [string]$Description = ""
  )
  $body = @{
    name        = $Name
    sku         = $Sku
    description = $Description
    price_cents = $PriceCents
    stock       = $Stock
  } | ConvertTo-Json -Depth 5

  _Invoke-Api -Method POST -Path "/api/products/" -BodyJson $body
}

function Set-ProductStock {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)][int]$Id,
    [Parameter(Mandatory)][ValidateRange(0,2147483647)][int]$Stock
  )
  $patch = @{ stock = $Stock } | ConvertTo-Json -Depth 3
  _Invoke-Api -Method PATCH -Path "/api/products/$Id/" -BodyJson $patch
}

function Remove-Product {
  [CmdletBinding(SupportsShouldProcess)]
  param([Parameter(Mandatory)][int]$Id)
  if ($PSCmdlet.ShouldProcess("Product $Id","DELETE")) {
    _Invoke-Api -Method DELETE -Path "/api/products/$Id/" | Out-Null
  }
}

function Get-Products {
  [CmdletBinding()]
  param(
    [ValidateRange(1,100)][int]$PerPage = 10,
    [ValidateRange(1,2147483647)][int]$Page = 1
  )
  _Invoke-Api -Method GET -Path "/api/products/?per_page=$PerPage&page=$Page"
}

Write-Host "HypeTotal helpers carregados. Base: $script:HTApiBase" -ForegroundColor Green
Write-Host "Funções: New-Product, Set-ProductStock, Remove-Product, Get-Products" -ForegroundColor Green
