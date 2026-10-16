<#
  Buscar_Felixlandia_PC.ps1
  Procura no PC arquivos de cálculo / registros financeiros ligados a Felixlândia
  (inclui "PROGRESSAO felixlandi", "Felixlândia" com ou sem acento) e gera um CSV
  em ordem alfabética na Área de Trabalho.

  COMO USAR:
    1. Salve este arquivo em qualquer pasta (ex.: Documentos).
    2. Clique com o botão direito > "Executar com o PowerShell".
       Se o Windows bloquear, abra o PowerShell e rode:
       powershell -ExecutionPolicy Bypass -File "C:\caminho\Buscar_Felixlandia_PC.ps1"
    3. Ao final, abra o arquivo "Felixlandia_PC_<data>.csv" na Área de Trabalho.
#>

# ---------- 1. Pastas onde procurar (as que não existirem são puladas) ----------
$pastas = @(
    [Environment]::GetFolderPath('MyDocuments'),
    [Environment]::GetFolderPath('Desktop'),
    (Join-Path $env:USERPROFILE 'Downloads'),
    $env:OneDrive,
    'D:\', 'E:\'
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -Unique

# ---------- 2. Filtros ----------
$extensoes   = @('.xlsx', '.xls', '.xlsm', '.csv', '.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png')
$regexFelix  = 'felixl|felix\s*lan'                  # cobre Felixlandia / Felixlândia / FELIXLANDIA
$regexFinanc = 'ficha|financeir|c[aá]lculo|calculo|mem[oó]ria|demonstrativ|contracheque|contra-cheque|holerite|folha|progress|valores|l[ií]quido|proventos'

$resultado = New-Object System.Collections.Generic.List[object]
$erros = 0

# ---------- 3. Varredura (erros de permissão não interrompem o script) ----------
foreach ($p in $pastas) {
    Write-Host "Procurando em: $p" -ForegroundColor Cyan
    try {
        Get-ChildItem -LiteralPath $p -Recurse -File -ErrorAction SilentlyContinue -ErrorVariable +errosLeitura |
        Where-Object { $extensoes -contains $_.Extension.ToLower() -and $_.FullName -match $regexFelix } |
        ForEach-Object {
            $resultado.Add([pscustomobject]@{
                Nome        = $_.Name
                Origem      = 'PC'
                Formato     = $_.Extension.TrimStart('.').ToUpper()
                Caminho     = $_.FullName
                TamanhoKB   = [math]::Round($_.Length / 1KB, 1)
                Modificado  = $_.LastWriteTime.ToString('dd/MM/yyyy HH:mm')
                Financeiro  = $(if ($_.FullName -match $regexFinanc) { 'Sim' } else { 'Verificar' })
            })
        }
    } catch {
        $erros++
        Write-Warning "Não foi possível ler parte de '$p': $($_.Exception.Message)"
    }
}
$erros += @($errosLeitura).Count

# ---------- 4. Ordena A-Z e salva CSV (Excel em português abre direto) ----------
$saida = Join-Path ([Environment]::GetFolderPath('Desktop')) ("Felixlandia_PC_{0}.csv" -f (Get-Date -Format 'yyyyMMdd_HHmm'))
try {
    $resultado | Sort-Object Nome, Caminho |
        Export-Csv -LiteralPath $saida -Delimiter ';' -NoTypeInformation -Encoding UTF8
    Write-Host ""
    Write-Host "Concluído: $($resultado.Count) arquivo(s) encontrados." -ForegroundColor Green
    Write-Host "  - Financeiros/cálculo: $(@($resultado | Where-Object Financeiro -eq 'Sim').Count)"
    Write-Host "  - Pastas/arquivos ignorados por falta de permissão: $erros"
    Write-Host "CSV salvo em: $saida"
} catch {
    Write-Error "Falha ao salvar o CSV em '$saida': $($_.Exception.Message)"
}
Read-Host "Pressione ENTER para fechar"
