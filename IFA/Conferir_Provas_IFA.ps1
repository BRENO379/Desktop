<#
  Conferir_Provas_IFA.ps1
  Confere a pasta de um cliente contra o CHECKLIST DE PROVAS DO IFA (43 itens,
  blocos A a H) e gera um CSV dizendo o que já existe e o que falta.
  A conferência é feita pelo NOME dos arquivos (o script não abre os documentos).

  COMO USAR:
    1. Salve este arquivo em qualquer pasta (ex.: Documentos).
    2. Clique com o botão direito > "Executar com o PowerShell" e escolha a pasta
       do cliente na janela que abrir.
       Se o Windows bloquear, abra o PowerShell e rode:
       powershell -ExecutionPolicy Bypass -File "C:\caminho\Conferir_Provas_IFA.ps1"
    3. Abra o CSV gerado dentro da própria pasta do cliente:
       "Checklist_IFA_<cliente>_<data>.csv" (se a pasta for somente leitura,
       o CSV vai para a Área de Trabalho).

  VÁRIOS CLIENTES DE UMA VEZ (ex.: substituídos de uma ação coletiva):
    powershell -ExecutionPolicy Bypass -File "C:\caminho\Conferir_Provas_IFA.ps1" -Pasta "C:\IFA\Ponte Nova" -Lote
    Cada subpasta é tratada como um cliente. Sai um CSV único, uma linha por
    cliente, na pasta informada: "Checklist_IFA_LOTE_<data>.csv".

  DICA PARA ACERTAR 100%:
    Comece o nome de cada arquivo pelo código do item do checklist:
    A1_PROCURACAO.pdf, D1_CNES_HISTORICO.pdf, E1_FNS_2024.pdf, F1_FICHA_FINANCEIRA_2023.pdf ...
    Sem o código, o script tenta reconhecer o documento por palavras-chave do nome.
#>

param(
    [string]$Pasta,      # pasta do cliente (ou pasta-mãe, com -Lote)
    [switch]$Lote,       # cada subpasta = um cliente
    [switch]$SemPausa    # não espera ENTER no final (uso em rotinas automáticas)
)

# ---------- 1. Itens do checklist (código, bloco, prioridade, a quem se aplica) ----------
# Regex: palavras-chave procuradas no nome do arquivo, já sem acentos e em minúsculas.
# Excluir: palavras que, se presentes, indicam que o arquivo é de OUTRO item.
# Manual: itens que não dá para reconhecer pelo nome; ficam como "CONFERIR MANUALMENTE".
function Novo-Item($cod, $bloco, $prio, $aplica, $doc, $regex, $excluir = '', [switch]$manual) {
    [pscustomobject]@{ Codigo = $cod; Bloco = $bloco; Prioridade = $prio; AplicaSe = $aplica
                       Documento = $doc; Regex = $regex; Excluir = $excluir; Manual = [bool]$manual }
}
$E = 'ESSENCIAL'; $I = 'IMPORTANTE'; $R = 'REFORÇO'
$sempre = 'Sempre'; $coletiva = 'Só ação coletiva'; $execucao = 'Só execução'

$itens = @(
    Novo-Item 'A1' 'A. Cliente'   $E $sempre   'Procuração com poderes para receber, dar quitação e renunciar ao excedente de RPV' 'procuracao|substabelecimento' 'sindicato|entidade|fasminas|federacao'
    Novo-Item 'A2' 'A. Cliente'   $E $sempre   'RG e CPF legíveis' '\brg\b|\bcpf\b|identidade|\bcnh\b' 'lista|substituidos'
    Novo-Item 'A3' 'A. Cliente'   $I $sempre   'Comprovante de residência em nome do cliente' 'residencia|endereco|conta de (luz|agua|energia)|cemig|copasa'
    Novo-Item 'A4' 'A. Cliente'   $I $sempre   'Declaração de hipossuficiência' 'hipossuficien|gratuidade|justica gratuita'
    Novo-Item 'A5' 'A. Cliente'   $I $sempre   'Contrato de honorários' 'honorario'
    Novo-Item 'B1' 'B. Entidade'  $E $coletiva 'Estatuto social da entidade' 'estatuto (social|do sindicato|da entidade|da federacao|fasminas)|estatuto sind'
    Novo-Item 'B2' 'B. Entidade'  $E $coletiva 'Certidão de registro sindical' 'registro sindical|certidao sindical|\bmte\b'
    Novo-Item 'B3' 'B. Entidade'  $E $coletiva 'Ata de eleição e posse da diretoria' '(ata|termo).*(eleicao|diretoria)|posse.*diretoria'
    Novo-Item 'B4' 'B. Entidade'  $E $coletiva 'Procuração da entidade' 'procuracao.*(sindicato|entidade|fasminas|federacao)|(sindicato|entidade|fasminas|federacao).*procuracao'
    Novo-Item 'B5' 'B. Entidade'  $I $coletiva 'Ata de assembleia autorizando a ação' 'assembleia|lista de presenca'
    Novo-Item 'B6' 'B. Entidade'  $E $coletiva 'Lista de substituídos (nome, CPF, matrícula, cargo)' 'substituidos|lista.*(filiados|servidores|agentes|acs|ace)|\brol\b'
    Novo-Item 'B7' 'B. Entidade'  $I $coletiva 'Prova de filiação' 'filiacao|filiado|mensalidade sindical' 'lista'
    Novo-Item 'C1' 'C. Vínculo'   $E $sempre   'Nomeação e posse ou contrato / CTPS' 'nomeacao|termo de posse|\bposse\b|contrato de trabalho|\bctps\b|carteira de trabalho' 'diretoria|eleicao|honorario'
    Novo-Item 'C2' 'C. Vínculo'   $I $sempre   'Edital e homologação do processo seletivo' 'edital|homologacao|processo seletivo|concurso|ec 51|certificacao'
    Novo-Item 'C3' 'C. Vínculo'   $E $sempre   'Declaração funcional (cargo, lotação, 40 h, situação)' '(declaracao|certidao) (funcional|de vinculo|de tempo)|declaracao.*(cargo|lotacao|jornada)'
    Novo-Item 'C4' 'C. Vínculo'   $I $sempre   'Ficha funcional / assentamentos' 'ficha funcional|assentamento|afastamento|licenca|readaptacao'
    Novo-Item 'C5' 'C. Vínculo'   $E $sempre   'Lei municipal do regime jurídico' 'regime juridico|estatuto d[oa]s? servidor|lei.*(celetista|\bclt\b)'
    Novo-Item 'D1' 'D. CNES'      $E $sempre   'Histórico do profissional no CNES (todo o período)' 'cnes|datasus' '\bmte\b|sindical'
    Novo-Item 'D2' 'D. CNES'      $E $sempre   'CNES da competência anterior ao crédito, ano a ano' 'cnes.*competencia|competencia.*cnes' '\bmte\b|sindical'
    Novo-Item 'D3' 'D. CNES'      $E $sempre   'Relatório de pagamento da APS (ACS pagos e suspensos)' 'relatorio.*pagamento|relatorioaps|gerenciaaps|pagamento aps|e ?gestor'
    Novo-Item 'D4' 'D. CNES'      $I $sempre   'Número do Cartão Nacional de Saúde (CNS)' '\bcns\b|cartao (nacional de )?(de )?saude|cartao sus'
    Novo-Item 'D5' 'D. CNES'      $R $sempre   'Produção do ACS no e-SUS / SIAPS' 'producao|\be ?sus\b|siaps|sisab'
    Novo-Item 'E1' 'E. Repasse'   $E $sempre   'Extratos do FNS com a parcela adicional, ano a ano' '\bfns\b|fundo nacional|consultafns|extrato.*repasse|repasse.*(fns|fundo|uniao|federal)'
    Novo-Item 'E2' 'E. Repasse'   $E $sempre   'Portaria do Ministério da Saúde com o valor do ano' 'portaria.*\b(ms|gm|ministerio|saude)\b|\bdou\b|diario oficial da uniao' 'nomeacao'
    Novo-Item 'E3' 'E. Repasse'   $R $sempre   'Extrato da conta do Fundo Municipal de Saúde' 'fundo municipal|\bfms\b|extrato.*conta'
    Novo-Item 'E4' 'E. Repasse'   $R $sempre   'Receita no Portal da Transparência / SICOM' 'sicom|transparencia.*receita|receita.*(transparencia|sus|fns)' 'medica'
    Novo-Item 'E5' 'E. Repasse'   $R $sempre   'Relatório Anual de Gestão / atas do Conselho de Saúde' '\brag\b|relatorio anual de gestao|conselho municipal de saude|\bcms\b|digisus'
    Novo-Item 'F1' 'F. Não pago'  $E $sempre   'Fichas financeiras completas (período não prescrito)' 'ficha.? financ|fichas financ'
    Novo-Item 'F2' 'F. Não pago'  $E $sempre   'Contracheques de out/nov/dez de cada ano' 'contra ?cheque|holerite|demonstrativo de pagamento|recibo de pagamento' 'colega'
    Novo-Item 'F3' 'F. Não pago'  $I $sempre   'Requerimento administrativo + resposta' 'requerimento|pedido administrativo|protocolo' 'lai|e ?sic'
    Novo-Item 'F4' 'F. Não pago'  $I $sempre   'Pedido pela LAI e resposta' '\blai\b|\be ?sic\b|acesso a informacao|12 ?527'
    Novo-Item 'F5' 'F. Não pago'  $R $sempre   'Empenhos / folha sem a rubrica do incentivo' 'empenho|folha de pagamento|despesa.*pessoal'
    Novo-Item 'G1' 'G. Lei local' $E $sempre   'Lei municipal que prevê o repasse do IFA / 14º' 'lei.*(\bifa\b|incentivo|decimo quarto|14o|14 salario|parcela adicional)|(\bifa\b|incentivo|decimo quarto|14o|parcela adicional).*\blei\b'
    Novo-Item 'G2' 'G. Lei local' $I $sempre   'Lei do PCCS / lei do vencimento' 'pccs|plano de (carreira|cargos)|lei.*(vencimento|piso)'
    Novo-Item 'G3' 'G. Lei local' $R $sempre   'Prova de pagamento do IFA em anos anteriores ou a colegas' 'colega|anos? anteriores|pagamento anterior|ifa pago'
    Novo-Item 'G4' 'G. Lei local' $R $sempre   'Projeto de lei, mensagem, atas da Câmara ou acordo' 'projeto de lei|mensagem|ata.*camara|acordo|termo de compromisso'
    Novo-Item 'G5' 'G. Lei local' $R $sempre   'LOA / LDO / QDD com dotação' '\bloa\b|\bldo\b|\bqdd\b|orcament'
    Novo-Item 'H1' 'H. Cálculo'   $E $sempre   'Planilha de cálculo ano a ano' 'planilha|calculo|memoria'
    Novo-Item 'H2' 'H. Cálculo'   $E $sempre   'Critério de correção e juros (índices) - conferir na planilha' '' '' -manual
    Novo-Item 'H3' 'H. Cálculo'   $E $execucao 'Demonstrativo discriminado do crédito (CPC, art. 534)' 'demonstrativo.*(calculo|credito|debito)|534|cumprimento'
    Novo-Item 'H4' 'H. Cálculo'   $E $execucao 'Título executivo + certidão de trânsito em julgado' 'sentenca|acordao|transito|titulo executivo'
    Novo-Item 'H5' 'H. Cálculo'   $I $sempre   'Lei municipal de RPV' '\brpv\b|pequeno valor'
    Novo-Item 'H6' 'H. Cálculo'   $I $sempre   'Definição do valor da causa e do juízo' '' '' -manual
)

$extensoes = @('.pdf', '.doc', '.docx', '.odt', '.rtf', '.txt', '.xls', '.xlsx', '.xlsm', '.ods', '.csv',
               '.jpg', '.jpeg', '.png', '.tif', '.tiff', '.heic', '.html', '.htm', '.msg', '.eml', '.zip')

# ---------- 2. Funções auxiliares ----------
# Tira acentos, troca _ - . por espaço e passa para minúsculas ("14º" vira "14o").
function Normalizar([string]$texto) {
    $d = $texto.ToLowerInvariant().Normalize([Text.NormalizationForm]::FormKD)
    $sb = New-Object System.Text.StringBuilder
    foreach ($c in $d.ToCharArray()) {
        if ([Globalization.CharUnicodeInfo]::GetUnicodeCategory($c) -ne [Globalization.UnicodeCategory]::NonSpacingMark) {
            [void]$sb.Append($c)
        }
    }
    return (($sb.ToString() -replace '[_\-\.\(\)\[\]{},;+]+', ' ') -replace '\s+', ' ').Trim()
}

# Retorna os códigos de item que um arquivo atende.
function Classificar([string]$nomeBase) {
    $n = Normalizar $nomeBase
    # Código no início do nome (ex.: "D1_CNES.pdf" ou "07_D1_CNES.pdf") vale sozinho e encerra a busca.
    if ($n -match '^(\d{1,3}\s)?([a-h][1-7])(\s|$)') {
        $cod = $Matches[2].ToUpper()
        if ($itens | Where-Object { $_.Codigo -eq $cod }) { return @($cod) }
    }
    $achados = @()
    foreach ($it in $itens) {
        if ($it.Manual -or -not $it.Regex) { continue }
        if ($n -match $it.Regex) {
            if ($it.Excluir -and $n -match $it.Excluir) { continue }
            $achados += $it.Codigo
        }
    }
    return $achados
}

# Lista os arquivos de uma pasta (com subpastas). Erros de permissão são contados, não param o script.
function Listar-Arquivos([string]$caminho) {
    $errosLeitura = $null
    $arquivos = @(Get-ChildItem -LiteralPath $caminho -Recurse -File -ErrorAction SilentlyContinue -ErrorVariable errosLeitura |
        Where-Object { $extensoes -contains $_.Extension.ToLower() -and $_.Name -notlike 'Checklist_IFA_*' })
    return [pscustomobject]@{ Arquivos = $arquivos; Erros = @($errosLeitura).Count }
}

# Confere uma pasta de cliente e devolve uma linha por item (+ arquivos não reconhecidos).
function Conferir-Cliente([string]$caminho) {
    $lista = Listar-Arquivos $caminho
    $porItem = @{}
    $naoClassificados = New-Object System.Collections.Generic.List[string]
    foreach ($arq in $lista.Arquivos) {
        $relativo = $arq.FullName.Substring($caminho.TrimEnd('\', '/').Length).TrimStart('\', '/')
        $codigos = @(Classificar $arq.BaseName)
        if ($codigos.Count -eq 0) { $naoClassificados.Add($relativo); continue }
        foreach ($c in $codigos) {
            if (-not $porItem.ContainsKey($c)) { $porItem[$c] = New-Object System.Collections.Generic.List[string] }
            $porItem[$c].Add($relativo)
        }
    }
    $linhas = foreach ($it in $itens) {
        if ($it.Manual) { $status = 'CONFERIR MANUALMENTE'; $encontrados = '' }
        elseif ($porItem.ContainsKey($it.Codigo)) { $status = 'OK'; $encontrados = ($porItem[$it.Codigo] -join ' | ') }
        else { $status = 'FALTA'; $encontrados = '' }
        [pscustomobject][ordered]@{
            Codigo = $it.Codigo; Bloco = $it.Bloco; Documento = $it.Documento; Prioridade = $it.Prioridade
            AplicaSe = $it.AplicaSe; Status = $status; Arquivos = $encontrados
        }
    }
    $extras = foreach ($nc in $naoClassificados) {
        [pscustomobject][ordered]@{
            Codigo = '-'; Bloco = '-'; Documento = 'Arquivo não reconhecido (renomeie com o código do item)'; Prioridade = '-'
            AplicaSe = '-'; Status = 'NÃO RECONHECIDO'; Arquivos = $nc
        }
    }
    return [pscustomobject]@{ Linhas = @($linhas); Extras = @($extras); TotalArquivos = $lista.Arquivos.Count; Erros = $lista.Erros }
}

# Grava CSV que o Excel em português abre direto (separador ";" e UTF-8 com BOM).
function Salvar-Csv($dados, [string]$destino) {
    $enc = 'UTF8'
    if ($PSVersionTable.PSVersion.Major -ge 6) { $enc = 'utf8BOM' }
    $dados | Export-Csv -LiteralPath $destino -Delimiter ';' -NoTypeInformation -Encoding $enc -ErrorAction Stop
}

# Tenta salvar no local pedido; se não der (pasta só leitura), salva na Área de Trabalho.
function Salvar-ComReserva($dados, [string]$pastaDestino, [string]$nomeArquivo) {
    $destino = Join-Path $pastaDestino $nomeArquivo
    try { Salvar-Csv $dados $destino; return $destino }
    catch {
        Write-Warning "Não foi possível salvar em '$pastaDestino': $($_.Exception.Message)"
        $desktop = [Environment]::GetFolderPath('Desktop')
        if (-not $desktop -or -not (Test-Path -LiteralPath $desktop)) { $desktop = $HOME }
        $destino = Join-Path $desktop $nomeArquivo
        try { Salvar-Csv $dados $destino; return $destino }
        catch { Write-Error "Falha ao salvar o CSV também em '$desktop': $($_.Exception.Message)"; return $null }
    }
}

# Remove caracteres que o Windows não aceita em nome de arquivo.
function Nome-Seguro([string]$t) { return (($t -replace '[\\/:*?"<>|]', '') -replace '\s+', '_') }

function Pausar { if (-not $SemPausa) { Read-Host 'Pressione ENTER para fechar' | Out-Null } }

# ---------- 3. Escolha da pasta (janela do Windows; se não houver, pergunta no terminal) ----------
if (-not $Pasta) {
    try {
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
        $janela = New-Object System.Windows.Forms.FolderBrowserDialog
        $janela.Description = 'Escolha a pasta do cliente (com -Lote: a pasta que contém as pastas dos clientes)'
        $dono = New-Object System.Windows.Forms.Form -Property @{ TopMost = $true }   # janela aparece na frente
        if ($janela.ShowDialog($dono) -eq [System.Windows.Forms.DialogResult]::OK) { $Pasta = $janela.SelectedPath }
        $dono.Dispose()
    } catch {
        $Pasta = Read-Host 'Cole o caminho da pasta do cliente'
    }
    if (-not $Pasta) {
        Write-Host 'Nenhuma pasta escolhida. Nada foi feito.' -ForegroundColor Yellow
        Pausar
        exit 1
    }
}
$Pasta = $Pasta.Trim().Trim('"')
if (-not (Test-Path -LiteralPath $Pasta -PathType Container)) {
    Write-Host "Pasta não encontrada: '$Pasta'. Confira o caminho e rode de novo." -ForegroundColor Red
    Pausar
    exit 1
}
$Pasta = (Resolve-Path -LiteralPath $Pasta).ProviderPath
$data = Get-Date -Format 'yyyyMMdd_HHmm'

# ---------- 4A. Modo LOTE: uma linha por cliente ----------
if ($Lote) {
    $clientes = @(Get-ChildItem -LiteralPath $Pasta -Directory -ErrorAction SilentlyContinue | Sort-Object Name)
    if ($clientes.Count -eq 0) {
        Write-Host "Nenhuma subpasta de cliente encontrada em '$Pasta'." -ForegroundColor Yellow
        Pausar
        exit 1
    }
    $consolidado = New-Object System.Collections.Generic.List[object]
    foreach ($cli in $clientes) {
        Write-Host "Conferindo: $($cli.Name)" -ForegroundColor Cyan
        try {
            $r = Conferir-Cliente $cli.FullName
            $essFaltando = @($r.Linhas | Where-Object { $_.Status -eq 'FALTA' -and $_.Prioridade -eq $E -and $_.AplicaSe -eq $sempre } | ForEach-Object Codigo)
            $linha = [ordered]@{
                Cliente            = $cli.Name
                Arquivos           = $r.TotalArquivos
                ItensOK            = @($r.Linhas | Where-Object Status -eq 'OK').Count
                EssenciaisFaltando = $essFaltando.Count
                CodigosFaltando    = ($essFaltando -join ', ')
                NaoReconhecidos    = $r.Extras.Count
            }
            foreach ($l in $r.Linhas) { $linha[$l.Codigo] = $l.Status }
        } catch {
            # Linha de erro com as mesmas colunas, para não desalinhar o CSV
            Write-Warning "Erro ao conferir '$($cli.Name)': $($_.Exception.Message)"
            $linha = [ordered]@{ Cliente = $cli.Name; Arquivos = 'ERRO'; ItensOK = ''; EssenciaisFaltando = ''
                                 CodigosFaltando = $_.Exception.Message; NaoReconhecidos = '' }
            foreach ($it in $itens) { $linha[$it.Codigo] = 'ERRO' }
        }
        $consolidado.Add([pscustomobject]$linha)
    }
    $saida = Salvar-ComReserva ($consolidado | Sort-Object Cliente) $Pasta ("Checklist_IFA_LOTE_{0}.csv" -f $data)
    Write-Host ''
    Write-Host "Concluído: $($clientes.Count) cliente(s) conferido(s)." -ForegroundColor Green
    Write-Host "  - Clientes sem nenhum essencial faltando: $(@($consolidado | Where-Object { $_.EssenciaisFaltando -eq 0 }).Count)"
    if ($saida) { Write-Host "CSV salvo em: $saida" }
    Pausar
    exit 0
}

# ---------- 4B. Modo UM CLIENTE ----------
$nomeCliente = Split-Path -Leaf $Pasta
Write-Host "Conferindo a pasta: $Pasta" -ForegroundColor Cyan
try { $r = Conferir-Cliente $Pasta }
catch {
    Write-Host "Erro ao ler a pasta: $($_.Exception.Message)" -ForegroundColor Red
    Pausar
    exit 1
}
if ($r.TotalArquivos -eq 0) { Write-Warning 'Nenhum documento encontrado na pasta (PDF, Word, Excel, imagem...). Todos os itens ficarão como FALTA.' }

$saida = Salvar-ComReserva (@($r.Linhas) + @($r.Extras)) $Pasta ("Checklist_IFA_{0}_{1}.csv" -f (Nome-Seguro $nomeCliente), $data)

# ---------- 5. Resumo na tela ----------
$faltaEss = @($r.Linhas | Where-Object { $_.Status -eq 'FALTA' -and $_.Prioridade -eq $E -and $_.AplicaSe -eq $sempre })
$faltaImp = @($r.Linhas | Where-Object { $_.Status -eq 'FALTA' -and $_.Prioridade -eq $I -and $_.AplicaSe -eq $sempre })
$faltaCol = @($r.Linhas | Where-Object { $_.Status -eq 'FALTA' -and $_.AplicaSe -eq $coletiva } | ForEach-Object Codigo)
$faltaExe = @($r.Linhas | Where-Object { $_.Status -eq 'FALTA' -and $_.AplicaSe -eq $execucao } | ForEach-Object Codigo)
Write-Host ''
Write-Host "=== CHECKLIST IFA - $nomeCliente ===" -ForegroundColor White
Write-Host "Documentos lidos: $($r.TotalArquivos)   |   Itens OK: $(@($r.Linhas | Where-Object Status -eq 'OK').Count) de $($itens.Count)"
Write-Host ''
Write-Host "ESSENCIAIS FALTANDO ($($faltaEss.Count)):" -ForegroundColor Red
foreach ($f in $faltaEss) { Write-Host ("  [{0}] {1}" -f $f.Codigo, $f.Documento) }
Write-Host ''
Write-Host "IMPORTANTES FALTANDO ($($faltaImp.Count)): $(($faltaImp | ForEach-Object Codigo) -join ', ')" -ForegroundColor Yellow
if ($faltaCol.Count -gt 0) { Write-Host "Se for AÇÃO COLETIVA, faltam também: $($faltaCol -join ', ')" -ForegroundColor Yellow }
if ($faltaExe.Count -gt 0) { Write-Host "Se for EXECUÇÃO, faltam também: $($faltaExe -join ', ')" -ForegroundColor Yellow }
if ($r.Extras.Count -gt 0) {
    Write-Host "Arquivos não reconhecidos: $($r.Extras.Count) - renomeie com o código do item (ex.: D1_CNES.pdf) e rode de novo." -ForegroundColor DarkYellow
}
if ($r.Erros -gt 0) { Write-Host "Pastas/arquivos ignorados por falta de permissão: $($r.Erros)" -ForegroundColor DarkYellow }
Write-Host 'Lembrete: H2 (índices na planilha) e H6 (valor da causa e juízo) são conferidos manualmente.'
if ($saida) { Write-Host "CSV salvo em: $saida" -ForegroundColor Green }
Pausar
