# Fontes e armadilhas — e-Gestor APS e CNESWeb

Levantamento feito em 19/10/2026 com consultas reais (Ponte Nova/MG, Ipatinga/MG e outros
municípios mineiros). Use quando o script falhar ou quando precisar coletar à mão.

## Códigos do município — só precisa do nome + UF

| Código | Como obter | Exemplo (Ponte Nova/MG) |
|---|---|---|
| IBGE 7 dígitos | `https://servicodados.ibge.gov.br/api/v1/localidades/estados/MG/municipios` | 3152105 |
| IBGE 6 dígitos (padrão CNES/e-Gestor) | 6 primeiros dígitos do IBGE 7 | 315210 |
| Código da UF | 2 primeiros dígitos do IBGE | 31 |
| Código da região | **1º dígito** do código da UF (1 N · 2 NE · 3 SE · 4 S · 5 CO) | 3 |

## Fonte A — e-Gestor APS (série mensal de ACS)

- Painel: `https://relatorioaps.saude.gov.br/cobertura/acs` (o antigo `egestorab.saude.gov.br/...relHistoricoCoberturaAB.xhtml` redireciona para cá).
- API que alimenta o painel (série inteira numa requisição; a tela limita a 12 competências):

```
GET https://relatorioaps-prd.saude.gov.br/cobertura/acs?unidadeGeografica=MUNICIPIO&coRegiao=3&coUf=31&coMunicipio=315210&nuCompInicio=202101&nuCompFim=202609
```

Resposta: JSON, lista de objetos. Campos usados:

| Campo | Significado | Formato real |
|---|---|---|
| `nuComp` | competência | `"202509"` (texto) |
| `qtAcsAtivoAb` | ACS ativos — **é este que se compara com o CNES** | `"77"` |
| `qtAcsCoberturaAb` | ACS considerados no cálculo de cobertura (pode ser menor) | `"77"` |
| `qtPopulacao` | população considerada | `"59,569"` ⚠ vírgula = separador de **milhar** |
| `pcCoberturaAcsAb` | cobertura % | `"74.33"` ⚠ ponto = separador **decimal** |
| `nuAnoPopulacaoConsiderada`, `tpOrigemBasePopulacao` | ano e origem da população | `"2024"`, `"DOU"` |

### Armadilhas do e-Gestor

1. **Competência duplicada na resposta** — em Ponte Nova, `202602` veio duas vezes (registros idênticos). Deduplicar e registrar o fato.
2. **Separadores invertidos** — `qtPopulacao` "59,742" é 59.742 habitantes, não 59,7.
3. **Defasagem**: em 19/10/2026 o e-Gestor ia até ago/2026 e o CNES até set/2026. "Última publicada" é por base; para conferir, consulte o CNES também na última competência do e-Gestor.
4. **Ativo × cobertura**: `qtAcsAtivoAb` e `qtAcsCoberturaAb` divergem em vários meses (ex.: Ponte Nova, out/2021: 86 × 75). Compare com o CNES usando `qtAcsAtivoAb`.
5. **Não há ACE** no e-Gestor. ACE tem fonte única: CNES 515140.

## Fonte B — CNESWeb/DATASUS (por CBO)

```
POST https://cnes2.datasus.gov.br/Mod_Ind_Profissional_com_CBO.asp
cboEstado=31&municipios=315210&cboCompetencia=202509&rdPesquisa=cbo&cboOcupacao=515105&btnPesquisa=Pesquisar
```

- Resposta HTML em **ISO-8859-1**, ~230 KB (a página inteira traz a lista de 2.000+ CBOs).
- Resultado: sequência `CBO | Descrição | Total | 515105 | AGENTE COMUNITARIO DE SAUDE | 77 | TOTAL | 77`.
- Zero profissionais: a página diz **"Não Existe(m) Profissional(is) nesta Especialidade para este Estado ou Município."** → registrar 0 (consulta feita, resultado zero), não "não apurado".
- A página devolvida **ecoa os parâmetros** (`<option value=202509 selected>`, `<option value=315210 selected>`): o próprio arquivo preservado prova o que foi consultado. O script confere isso.
- Competências: o `<select name="cboCompetencia">` **exibe MMAAAA (092025) mas o value é AAAAMM (202509)**. Cuidado: os CBOs também têm 6 dígitos — leia só o bloco desse select.
- `municipios=` vazio devolve o **total do estado** (MG, set/2026: 13.138 no CBO 322255).
- Servidor lento: 3–6 s por consulta; houve timeout de 40 s numa consulta isolada. Use novas tentativas com espera crescente e pausa de 1 s entre consultas.

### Relação nominal (drill-down)

```
GET https://cnes2.datasus.gov.br/Mod_Ind_Profissional_Listar.asp?Vcbo=515105&VListar=1&VEstado=31&VMun=315210
```

- Tabela `Nome | Município | UF`. **Sem parâmetro de competência**: é a posição atual. Prova: Ponte Nova tinha 129 nomes = total de set/2026 (última), não os 77 de set/2025.
- CBO sem profissionais: só o cabeçalho, sem linhas → lista vazia (não é falha).

## Regra crítica — reclassificação para "Técnico em ACS"

Muitos municípios relançaram ACS no CBO **322255** a partir de 2024. Amostra set/2025 (MG):

| Município | 515105 | 322255 | % que sumiria consultando só 515105 |
|---|---|---|---|
| Ipatinga | 162 | 219 | 57% |
| Montes Claros | 650 | 242 | 27% |
| Uberlândia | 491 | 114 | 19% |
| Sete Lagoas | 236 | 114 | 33% |
| Belo Horizonte | 2.398 | 0 | 0% |
| Ponte Nova | 77 | 0 | 0% |

Por isso: **sempre os três CBOs, sempre ACS = 515105 + 322255**.

## Integridade (SHA-256)

- Preservar os **bytes exatamente como recebidos** (não reabrir/salvar no navegador — muda o arquivo).
- O hash prova que o arquivo não mudou depois da extração. Não prova que nova consulta dará os mesmos bytes (a base pode ser retificada) — declarar isso nos limites.
- Windows: `certutil -hashfile "arquivo.html" SHA256` · Linux/Mac: `sha256sum arquivo.html`.
