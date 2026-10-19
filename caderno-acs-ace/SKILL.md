---
name: caderno-acs-ace
description: Gera o Caderno de Provas do quantitativo de Agentes Comunitários de Saúde (ACS) e de Agentes de Combate às Endemias (ACE) de um município, extraído do SCNES/CNESWeb e do e-Gestor APS — XLSX, gráficos, DOCX e PDF no padrão ABNT, com as respostas brutas preservadas e SHA-256, conferência CNES × e-Gestor competência a competência, achado de reclassificação de CBO e relação nominal. Use sempre que o pedido envolver quantitativo, número ou quadro de ACS/ACE de um município; consulta ao CNES pelos CBOs 515105, 322255 ou 515140; cobertura de ACS no e-Gestor; ou prova documental de ACS/ACE para ação contra município (IFA, piso salarial, EC 120/2022, Lei 11.350/2006) — mesmo que o usuário só diga "puxa os ACS de tal cidade".
---

# Caderno de Provas — quantitativo de ACS/ACE (SCNES + e-Gestor)

O trabalho pesado é **código determinístico** (`scripts/caderno.py`): coleta, apuração, planilha,
gráficos, DOCX, PDF e conferência. O seu papel é: rodar, **olhar** o resultado, corrigir se preciso
e responder em blocos curtos. Não refaça à mão o que o script faz — é mais lento e erra mais.

O usuário é advogado, tem TDAH e 1.500 processos: não pergunte várias coisas. Se faltar o período,
use o padrão do script (últimos 5 exercícios + o corrente) e diga isso no resumo.

## Fluxo (4 passos)

```
1 identificar município/UF/período ─► 2 rodar o script ─► 3 OLHAR as páginas ─► 4 responder + entregar
```

### 1. Parâmetros

Só são necessários **município + UF**. O script descobre sozinho: código IBGE (7 e 6 dígitos),
código da UF, região (1º dígito da UF) e a última competência publicada em cada base.
Período opcional em `AAAAMM`. Se o usuário der o código IBGE, use `--ibge`.

### 2. Rodar

```bash
pip install -r requirements.txt          # 1ª vez
python scripts/caderno.py --municipio "Ponte Nova" --uf MG
python scripts/caderno.py --municipio "Ipatinga" --uf MG --inicio 202101 --fim 202609 --saida /pasta
```

| Opção | Quando usar |
|---|---|
| `--conferencia-mensal` | Pedirem conferência CNES × e-Gestor **mês a mês** (≈ 15 min; ~6 consultas/min ao CNES) |
| `--sem-nominal` | Não querem a relação nominal |
| `--reprocessar PASTA` | Refazer XLSX/DOCX/PDF a partir do `dados.json` (após ajuste no código), sem nova consulta |

O script imprime cada etapa `[n/8]`. Falha de rede **não derruba** a execução: o item vira
"não apurado" e entra em Pendências (seção 8.2 do caderno e `RESUMO.md`).

### 3. Conferir — obrigatório, nunca entregue sem olhar

O script já: converte em PDF, detecta página em branco, confere os 8 marcadores do PDF e
recalcula o XLSX (zero erro de fórmula + totais iguais à apuração). Mesmo assim, **abra com
`Read` cada `conferencia/folha_contato_NN.png`** e procure:

- página quase vazia (linha "Fonte" ou parágrafo órfão antes de quebra de seção);
- tabela espremida ou célula quebrando número/hash em 3+ linhas;
- caixa "Achado relevante" partida entre páginas;
- rótulo cortado ou sobreposto nos gráficos (`GRAFICO_*.png` em resolução cheia).

Achou defeito → ajuste `scripts/documento.py` ou `scripts/grafico.py` → `--reprocessar PASTA` → olhe de novo.

### 4. Responder e entregar

Resposta em 4 blocos curtos, sem introdução (o `RESUMO.md` já vem pronto):
1. tabela do quadro de setembro por exercício (515105 · 322255 · ACS total · ACE · e-Gestor · diferença);
2. o achado da reclassificação (322255), se houver — com números;
3. limites declarados;
4. pendências (o que ficou não apurado e por quê).

Entregue (`SendUserFile`): `.pdf`, `.docx`, `.xlsx`, `GRAFICO_1_COMPOSICAO_CBO.png` e
`EVIDENCIAS_SHA256.zip` (gerado pelo script; sem ele o SHA-256 não serve para nada).

## Regras que não se negociam

- **ACS total = CBO 515105 + CBO 322255.** Consultar só o 515105 subestima o quadro
  (Ipatinga/MG, set/2025: 162 no 515105 e 219 no 322255 — 57% ficariam de fora).
- **Nenhum número estimado.** O que não veio da fonte é "não apurado", com o motivo.
- **|CNES − e-Gestor| > 2 = registrar para investigação**, nunca silenciar (o script cria a caixa
  "Divergências registradas" na seção 5).
- **O caderno é prova, não petição:** PT-BR formal e impessoal, sem adjetivo e sem conclusão
  jurídica. Modelos de redação em `references/textos_modelo.md`.
- **ACE não existe no e-Gestor** — para ACE a fonte é só o CNES; diga isso, não "concilie".
- **Relação nominal = posição da data da consulta** (o CNESWeb não filtra competência pretérita).
- Extratos de repasse (consultafns.saude.gov.br) **não** entram no caderno — juntados em apartado.
- **LGPD:** a relação nominal tem nomes de servidores. Não versionar a pasta de saída em
  repositório público nem gravar nomes em memória.

## Se o script não puder rodar

Sem rede para `*.saude.gov.br`/`*.datasus.gov.br`, ou layout das páginas mudou: leia
`references/fontes_e_armadilhas.md` (URLs, parâmetros, formatos de resposta, armadilhas já
vividas) e faça a coleta manual seguindo as mesmas regras; registre a mudança de layout como
pendência e corrija o parser em `scripts/fontes.py`.

## Arquivos

| Arquivo | Papel |
|---|---|
| `scripts/caderno.py` | Orquestrador (CLI) — 8 etapas |
| `scripts/fontes.py` | IBGE, e-Gestor, CNESWeb: coleta, evidência bruta, SHA-256 |
| `scripts/apuracao.py` | Regra crítica, conferência, achado de reclassificação |
| `scripts/planilha.py` | XLSX (valores das fontes + fórmulas para tudo que é calculado) |
| `scripts/grafico.py` | Gráficos PNG (paleta validada para daltonismo) |
| `scripts/documento.py` | DOCX ABNT — 8 seções |
| `scripts/conferencia.py` | PDF, páginas, folhas de contato, marcadores, recálculo do XLSX |
| `references/fontes_e_armadilhas.md` | Detalhe técnico das fontes + armadilhas |
| `references/textos_modelo.md` | Molde de redação (few-shot) e o que não escrever |
