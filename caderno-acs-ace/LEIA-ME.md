# Caderno de Provas ACS/ACE — como instalar e usar

**O que faz:** você informa *município + UF*; a ferramenta consulta o CNES e o e-Gestor,
guarda cada resposta com SHA-256 e entrega o caderno pronto para juntada
(PDF + DOCX ABNT + XLSX + gráficos), já conferido.

```
Município/UF ─► IBGE (códigos) ─► e-Gestor (série mensal) ─► CNES (3 CBOs × setembros)
            ─► relação nominal ─► apuração 515105+322255 ─► XLSX · gráficos · DOCX · PDF
            ─► conferência automática ─► VOCÊ olha as folhas de contato ─► juntada
```

---

## Opção A — dentro do Claude (recomendado)

1. Gere o pacote: compacte a pasta `caderno-acs-ace` inteira em `caderno-acs-ace.zip`
   (botão direito na pasta → *Enviar para* → *Pasta compactada*).
2. No claude.ai: **Configurações → Capacidades → Skills → Enviar skill** e escolha o `.zip`.
3. Em qualquer conversa, escreva:

```
Caderno de provas ACS/ACE: Ponte Nova/MG.
```

O Claude roda o script, olha as páginas e responde com o quadro de setembro, o achado
de reclassificação, os limites e as pendências.

## Opção B — no seu PC (Windows), sem IA

**Uma vez só:**

1. Instale o **Python 3.11 ou mais novo** — https://www.python.org/downloads/
   ⚠ Na primeira tela do instalador, marque **"Add python.exe to PATH"**.
2. Instale o **LibreOffice** — https://pt-br.libreoffice.org/baixe-ja/
   (gera o PDF e confere as fórmulas; sem ele, o PDF sai pelo Word, se houver).

**Toda vez:**

1. Dê **duplo clique** em `Gerar_Caderno_ACS_ACE.bat`.
2. Responda: município, UF e, se quiser, o período (`AAAAMM`). Enter = padrão.
3. Aguarde ≈ 3 minutos. A pasta `CADERNO_ACS_ACE_<MUNICÍPIO>_<UF>_<data>` aparece na
   Área de Trabalho.
4. **Abra `conferencia\folha_contato_01.png` (e as seguintes) e olhe cada página** antes de juntar.

Linha de comando (opções avançadas):

```bat
python scripts\caderno.py --municipio "Ipatinga" --uf MG --inicio 202101 --fim 202609
python scripts\caderno.py --municipio "Ipatinga" --uf MG --conferencia-mensal
python scripts\caderno.py --reprocessar "C:\Users\voce\Desktop\CADERNO_ACS_ACE_IPATINGA_MG_2026-10-19_1358"
```

---

## O que sai na pasta

| Arquivo | Para quê |
|---|---|
| `CADERNO_ACS_ACE_….pdf` | **Juntada** (com marcadores de navegação) |
| `CADERNO_ACS_ACE_….docx` | Editar, se precisar |
| `CADERNO_ACS_ACE_….xlsx` | Planilha com fórmulas (5 abas) — inclui relação nominal para cruzar com filiados |
| `GRAFICO_1_COMPOSICAO_CBO.png` | Gráfico para colar na petição |
| `evidencias\` e `EVIDENCIAS_SHA256.zip` | Respostas brutas + `MANIFESTO_SHA256.txt` — **junte o .zip** com o caderno |
| `conferencia\` | Páginas renderizadas e folhas de contato para inspeção |
| `RESUMO.md` | Os 4 blocos: quadro de setembro, achado, limites, pendências |
| `dados.json` | Tudo que foi apurado (permite `--reprocessar` sem nova consulta) |

## Problemas comuns

| Mensagem | O que fazer |
|---|---|
| `Python nao encontrado` | Reinstale o Python marcando "Add python.exe to PATH" |
| `Município ... não encontrado. Parecidos: ...` | Corrija a grafia (acento é opcional) |
| Vários itens "não apurado" | CNES/e-Gestor fora do ar. Rode de novo mais tarde; o caderno lista o que faltou |
| `Sem conversor DOCX→PDF` | Instale o LibreOffice (ou tenha o Word instalado) |
| `não foi possível recalcular` no XLSX | Sem LibreOffice: abra o XLSX no Excel e confira se há `#REF!`/`#VALOR!` |
| Mudou o layout do CNES | Leia `references/fontes_e_armadilhas.md` e ajuste `scripts/fontes.py` |

## LGPD

A relação nominal traz **nomes de servidores** (dado público do CNES, mas pessoal).
Use só no processo. **Não** suba a pasta de saída para repositório público
(o `.gitignore` deste repositório já bloqueia `CADERNO_ACS_ACE_*/`).
