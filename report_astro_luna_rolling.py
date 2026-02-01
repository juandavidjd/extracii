<#
Master pipeline para RadarPremios (robusto)
- Scrapers (opcionales)
- Limpieza + checks (existencia, headers, frescura)
- Carga DB + matriz
- Mantenimiento DB (opcional)
- Scoring parametrizable (señales/pesos/caps)
- Evaluación + (opcional) reporte rolling
#>

[CmdletBinding()]
param(
    # Operativos
    [switch] $OnlyScoring,
    [switch] $SkipScrapers,
    [switch] $DryRun,
    [switch] $Report3D,
    [switch] $NoVacuum,
    [string] $HoraCorte     = "11:00",   # antes de esta hora se permite "ayer"
    # Scoring (señales)
    [int]    $Seed          = 12345,
    [int]    $Gen           = 200,
    [int]    $Top           = 20,
    [int]    $Shortlist     = 10,
    [double] $WeightHotCold = 0.25,
    [double] $WeightCal     = 0.25,
    [double] $WeightDP      = 0.25,
    [double] $WeightExact   = 0.25,
    [int]    $CapDigitPos   = 50,
    [int]    $CapExact      = 100,
    [int]    $CalHorizon    = 60
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"

# === Rutas ===
$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root    = Split-Path -Parent $BaseDir
$DbFile  = Join-Path $Root "radar_premios.db"
$LogDir  = Join-Path $Root "logs"
$RepDir  = Join-Path $Root "reportes"
$Lock    = Join-Path $Root ".master.lock"
$LogFile = Join-Path $LogDir ("master_{0:yyyyMMdd_HHmmss}.log.txt" -f (Get-Date))
New-Item -ItemType Directory -Force -Path $LogDir,$RepDir | Out-Null

# === Utilidades ===
function Show-Info($msg, $val="") { Write-Host "[INFO] $msg $val" }
function Show-Step($msg)          { Write-Host "`n[STEP] $msg" }
function Show-Cmd($argv)          { Write-Host "[CMD ] $($argv -join ' ')" }
function Show-Ok($rc,$ms)         { Write-Host "[OK  ] RC=$rc  (${ms} ms)" }
function Show-Err($msg)           { Write-Host "[ERR ] $msg" }

function Invoke-Step([string]$label, [string[]]$argv) {
    Show-Step $label
    Show-Cmd $argv
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        if ($PSBoundParameters.ContainsKey('DryRun') -and $DryRun) {
            Write-Host "[DRY] (omitido)"
            $sw.Stop(); Show-Ok 0 $sw.ElapsedMilliseconds; return 0
        }
        & $argv *>> $LogFile
        $rc = $LASTEXITCODE
        $sw.Stop()
        if ($rc -ne 0) { throw "Fallo RC=$rc" }
        Show-Ok $rc $sw.ElapsedMilliseconds
        return $rc
    } catch {
        Show-Err $_.Exception.Message
        throw
    }
}

function New-Lock {
    if (Test-Path $Lock) { throw "Ya hay una ejecución en curso (lock: $Lock)" }
    Set-Content -Path $Lock -Value ([DateTime]::Now.ToString("s"))
}
function Remove-Lock {
    if (Test-Path $Lock) { Remove-Item $Lock -Force }
}

# === Inicio ===
Write-Host "=== Master pipeline iniciado ==="
Show-Info "Base:" $DbFile
Show-Info "Log: " $LogFile
Set-Location $Root

# Transcript
Start-Transcript -Path $LogFile -Append | Out-Null
New-Lock
try {
    if (-not $OnlyScoring -and -not $SkipScrapers) {
        Invoke-Step "Scraper LOTERÍAS"             @("python", (Join-Path $BaseDir "scraper_loterias.py"))
        Invoke-Step "Scraper ASTRO LUNA"           @("python", (Join-Path $BaseDir "scraper_astroluna.py"))
        Invoke-Step "Scraper BALOTO premios"       @("python", (Join-Path $BaseDir "scraper_baloto_premios.py"))
        Invoke-Step "Scraper BALOTO resultados"    @("python", (Join-Path $BaseDir "scraper_baloto_resultados.py"))
        Invoke-Step "Scraper REVANCHA premios"     @("python", (Join-Path $BaseDir "scraper_revancha_premios.py"))
        Invoke-Step "Scraper REVANCHA resultados"  @("python", (Join-Path $BaseDir "scraper_revancha_resultados.py"))
    }

    if (-not $OnlyScoring) {
        # Limpieza + checks (existencia, headers, frescura estricta)
        Invoke-Step "LIMPIAR CSVs (crudo→limpio + checks)" @(
            "python", (Join-Path $BaseDir "limpiar_csvs.py"),
            "--required","astro_luna.csv",
            "--expect-headers","astro_luna.csv:fecha,ganador",
            "--freshness-check","--freshness-target","astro_luna.csv","--freshness-col","fecha","--hora-corte",$HoraCorte
        )

        # Carga a DB
        Invoke-Step "CARGAR DB" @("python", (Join-Path $BaseDir "cargar_db.py"))

        # Generación de matriz AstroLuna y actualizaciones relacionadas
        Invoke-Step "GENERAR MATRIZ ASTRO LUNA" @("python", (Join-Path $BaseDir "gen_matriz_astroluna.py"))
        Invoke-Step "CARGAR DB post-matriz"     @("python", (Join-Path $BaseDir "cargar_db_postmatriz.py"))
        Invoke-Step "ACTUALIZAR_BASE_ASTROLUNA" @("python", (Join-Path $BaseDir "actualizar_astroluna.py"))

        if (-not $NoVacuum) {
            Invoke-Step "MANTENIMIENTO DB" @("python", (Join-Path $BaseDir "mantenimiento_db.py"))
        }
    }

    # Scoring (señales y caps completamente parametrizables)
    Invoke-Step "SCORING CANDIDATOS" @(
        "python", (Join-Path $BaseDir "score_candidates.py"),
        "--seed", $Seed,
        "--gen", $Gen,
        "--top", $Top,
        "--shortlist", $Shortlist,
        "--weight-hotcold", $WeightHotCold,
        "--weight-cal", $WeightCal,
        "--weight-dp", $WeightDP,
        "--weight-exact", $WeightExact,
        "--cap-digitpos", $CapDigitPos,
        "--cap-exact", $CapExact,
        "--cal-horizon", $CalHorizon
    )

    # Evaluación/veredictos
    Invoke-Step "EVALUAR RUN RECIENTE" @("python", (Join-Path $BaseDir "evaluate_recent.py"))

    if ($Report3D) {
        $html = Join-Path $RepDir "astro_luna_rolling.html"
        $csv  = Join-Path $RepDir "astro_luna_rolling.csv"
        Invoke-Step "REPORTE rolling 3d AstroLuna" @(
            "python", (Join-Path $BaseDir "report_astro_luna_rolling.py"),
            "--db", $DbFile, "--k", $Shortlist, "--out_csv", $csv, "--out_html", $html
        )
        Show-Info "Reporte:" $html
    }

    Write-Host "=== Pipeline OK ==="
}
catch {
    Show-Err $_.Exception.Message
    exit 1
}
finally {
    Stop-Transcript | Out-Null
    Remove-Lock
    Set-Location $BaseDir
    Write-Host "=== Master pipeline FINALIZADO ==="
    Show-Info "Log en:" $LogFile
}
