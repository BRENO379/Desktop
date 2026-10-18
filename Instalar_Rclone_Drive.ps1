<#
  Instalar_Rclone_Drive.ps1
  Instala o rclone, conecta o Google Drive do escritório (remoto "gdrive_lgm")
  e testa a conexão listando as pastas da raiz do Drive.

  COMO USAR:
    1. Clique com o botão direito neste arquivo > "Executar com o PowerShell".
       Se o Windows bloquear, abra o PowerShell e rode:
       powershell -ExecutionPolicy Bypass -File "C:\caminho\Instalar_Rclone_Drive.ps1"
    2. Quando o navegador abrir, entre com a conta Google do escritório e clique em "Permitir".
    3. Ao final aparecem as pastas do Drive. Pronto.

  Pode rodar de novo sem medo: o que já estiver instalado/configurado é pulado.
  Detalhes e solução de problemas: INSTALAR.md
#>

param(
    [string]$NomeRemoto = 'gdrive_lgm',
    # 'drive' = acesso total (ler e gravar) | 'drive.readonly' = só leitura
    [ValidateSet('drive', 'drive.readonly')]
    [string]$Escopo = 'drive'
)

# ---------- Funções de apoio ----------
function Write-Etapa([string]$texto) { Write-Host "`n==> $texto" -ForegroundColor Cyan }
function Write-Ok([string]$texto)    { Write-Host "    [OK] $texto" -ForegroundColor Green }

function Sair-ComErro([string]$mensagem) {
    Write-Host "`n[ERRO] $mensagem" -ForegroundColor Red
    Write-Host 'Consulte a seção "Problemas comuns" do INSTALAR.md.' -ForegroundColor Yellow
    Read-Host 'Pressione ENTER para fechar'
    exit 1
}

# O winget grava o rclone no PATH, mas a janela já aberta não "enxerga" a mudança.
# Esta função recarrega o PATH sem precisar fechar o PowerShell.
function Update-PathSessao {
    $env:Path = @(
        [Environment]::GetEnvironmentVariable('Path', 'Machine'),
        [Environment]::GetEnvironmentVariable('Path', 'User'),
        (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links')
    ) -join ';'
}

# Procura o rclone.exe: no PATH, na pasta de pacotes do winget ou na instalação manual.
function Find-Rclone {
    Update-PathSessao
    $cmd = Get-Command rclone -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $pastaWinget = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
    if (Test-Path -LiteralPath $pastaWinget) {
        $exe = Get-ChildItem -LiteralPath $pastaWinget -Filter 'rclone.exe' -Recurse -ErrorAction SilentlyContinue |
               Select-Object -First 1
        if ($exe) { return $exe.FullName }
    }

    $manual = Join-Path $env:LOCALAPPDATA 'rclone\rclone.exe'
    if (Test-Path -LiteralPath $manual) { return $manual }
    return $null
}

# ---------- 1. Instalação ----------
Write-Etapa 'Etapa 1/3 - Instalando o rclone'
$rclone = Find-Rclone

if ($rclone) {
    Write-Ok "rclone já instalado: $rclone"
} else {
    # Caminho A: winget (instalador oficial do Windows)
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host '    Instalando pelo winget (pode levar 1-2 minutos)...'
        winget install --id Rclone.Rclone --exact --silent --accept-source-agreements --accept-package-agreements
        $rclone = Find-Rclone
    } else {
        Write-Host '    winget não encontrado neste Windows. Usando download direto.' -ForegroundColor Yellow
    }

    # Caminho B: download direto do site oficial (se o winget falhar ou não existir)
    if (-not $rclone) {
        Write-Host '    Baixando de downloads.rclone.org...'
        $arquitetura = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'amd64' }
        $url     = "https://downloads.rclone.org/rclone-current-windows-$arquitetura.zip"
        $temp    = Join-Path $env:TEMP 'rclone_instalacao'
        $zip     = Join-Path $temp 'rclone.zip'
        $destino = Join-Path $env:LOCALAPPDATA 'rclone'
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            New-Item -ItemType Directory -Path $temp, $destino -Force -ErrorAction Stop | Out-Null
            Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing -ErrorAction Stop
            Expand-Archive -LiteralPath $zip -DestinationPath $temp -Force -ErrorAction Stop
            $exe = Get-ChildItem -LiteralPath $temp -Filter 'rclone.exe' -Recurse -ErrorAction Stop | Select-Object -First 1
            Copy-Item -LiteralPath $exe.FullName -Destination $destino -Force -ErrorAction Stop

            # Coloca a pasta no PATH do usuário para o comando "rclone" funcionar em qualquer janela
            $pathUsuario = [Environment]::GetEnvironmentVariable('Path', 'User')
            if (($pathUsuario -split ';') -notcontains $destino) {
                [Environment]::SetEnvironmentVariable('Path', ($pathUsuario.TrimEnd(';') + ";$destino"), 'User')
            }
        } catch {
            Sair-ComErro "Não foi possível baixar/instalar o rclone: $($_.Exception.Message)"
        } finally {
            Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
        }
        $rclone = Find-Rclone
    }

    if (-not $rclone) { Sair-ComErro 'A instalação terminou, mas o rclone.exe não foi encontrado.' }
    Write-Ok "rclone instalado: $rclone"
}
& $rclone version | Select-Object -First 1

# ---------- 2. Conexão com o Google Drive ----------
Write-Etapa "Etapa 2/3 - Conectando o Google Drive (remoto '$NomeRemoto')"
$remotos = @(& $rclone listremotes)

if ($remotos -contains "${NomeRemoto}:") {
    Write-Ok "Remoto '$NomeRemoto' já existe. Pulando configuração."
} else {
    Write-Host '    O NAVEGADOR VAI ABRIR AGORA:' -ForegroundColor Yellow
    Write-Host '      1) Entre com a conta Google do escritório'
    Write-Host '      2) Clique em "Permitir"'
    Write-Host '      3) Quando aparecer "Success!", volte para esta janela'
    Write-Host '    (Se o navegador não abrir, copie o link http://127.0.0.1:53682/... que aparecer abaixo.)'

    # Equivale a responder o "rclone config" com: tipo drive, escopo 1 (acesso total),
    # login automático pelo navegador = Sim, Drive compartilhado = Não.
    # "| Out-Null" esconde o token de acesso que o rclone imprime no final.
    & $rclone config create $NomeRemoto drive "scope=$Escopo" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Sair-ComErro 'A autorização no Google não foi concluída (janela fechada, acesso negado ou tempo esgotado). Rode o script de novo.'
    }
    Write-Ok "Remoto '$NomeRemoto' criado."
}

# ---------- 3. Teste ----------
Write-Etapa "Etapa 3/3 - Testando: rclone lsd ${NomeRemoto}:"
& $rclone lsd "${NomeRemoto}:"
if ($LASTEXITCODE -ne 0) {
    Sair-ComErro "O teste falhou. Para refazer o login rode: rclone config reconnect ${NomeRemoto}:"
}

Write-Host "`nTUDO PRONTO. As pastas acima estão no seu Google Drive." -ForegroundColor Green
Write-Host "Configuração salva em: $(& $rclone config file | Select-Object -Last 1)"
Write-Host 'ATENÇÃO: esse arquivo contém a chave de acesso ao Drive. Não envie nem compartilhe.' -ForegroundColor Yellow
Read-Host "`nPressione ENTER para fechar"
