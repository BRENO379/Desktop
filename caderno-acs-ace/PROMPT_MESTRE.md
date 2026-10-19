# Prompt Mestre v2 — Caderno de Provas ACS/ACE (SCNES + e-Gestor)

## 0. Veredito em 30 segundos

- **Prompt sozinho = a IA refaz tudo, toda vez**: monta URL à mão, interpreta HTML de 230 KB,
  esquece um CBO, não olha as páginas. Resultado varia a cada execução.
- **Mais eficiente = Skill + script.** O que é repetitivo virou código testado
  (`scripts/caderno.py`). O prompt encolhe para **uma linha**.
- **Medido em 19/10/2026 (Ponte Nova/MG):** 26 respostas preservadas com SHA-256, caderno de 11 páginas, ≈ 3 min,
  zero erro de fórmula, 20 marcadores no PDF, conferência CNES × e-Gestor batendo em 6 de 6
  competências pareadas.

| Você quer… | Use |
|---|---|
| Rodar no Claude com a skill instalada | **Seção 3** (1 linha) |
| Rodar no seu PC, sem IA | `Gerar_Caderno_ACS_ACE.bat` (ver `LEIA-ME.md`) |
| Usar outra IA / Claude sem a skill | **Seção 4** (prompt completo) |

---

## 1. Diagnóstico do prompt original

O prompt original já era bom (fontes certas, regra 515105 + 322255, conferência visual).
O estudo com consultas reais achou **13 pontos** que ele não cobria:

| # | Ponto | O que o teste real mostrou | Correção na v2 |
|---|---|---|---|
| 1 | 5 parâmetros manuais (IBGE6, COUF, COREGIAO…) | Erro de digitação = consulta do município errado | Só **município + UF**; o resto é derivado (região = 1º dígito da UF) |
| 2 | "Última publicada" | e-Gestor ia até **ago/2026**, CNES até **set/2026** | Última é **por base**; CNES também na última do e-Gestor (conferência pareada) |
| 3 | `qtPopulacao` | Vem `"59,742"` — vírgula é **milhar** | Regra de leitura explícita |
| 4 | Série do e-Gestor | Competência **202602 veio duplicada** | Deduplicar e registrar |
| 5 | ACE | e-Gestor **não publica ACE** | ACE = fonte única CNES 515140, declarado |
| 6 | Campo de conferência | `qtAcsAtivoAb` ≠ `qtAcsCoberturaAb` (out/2021: 86 × 75) | Comparar com **qtAcsAtivoAb** |
| 7 | SHA-256 "da resposta" | Hash sem o arquivo guardado não prova nada | Preservar bytes brutos + manifesto + roteiro `certutil` |
| 8 | Zero profissionais | Página diz "Não Existe(m) Profissional(is)…" | Registrar **0**, não "não apurado" |
| 9 | Servidor CNES | Timeout de 40 s numa consulta isolada | 4 novas tentativas (2-4-8-16 s) + pausa de 1 s |
| 10 | Margens "3/2/2/3" | Ordem ambígua | Sup. 3 · esq. 3 · inf. 2 · dir. 2 cm (NBR 14724) |
| 11 | "Competência a competência" | CNES só em setembro não permite isso | Padrão = setembros + últimas; opção mês a mês |
| 12 | "OLHAR as páginas" | 1ª versão tinha página quase vazia e hash quebrando em 3 linhas | Detecção automática + folhas de contato para o olho humano |
| 13 | Relação nominal | Tem nomes de servidores | Aviso LGPD: não versionar em repositório público |

Bônus confirmado: a regra crítica é real e grande. **Ipatinga/MG, set/2025: 162 no CBO 515105
e 219 no CBO 322255** — consultar só o 515105 perderia 57% do quadro.

---

## 2. Como o mapa mental foi aplicado

| Etapa do mapa | No prompt v2 | Na skill (código) |
|---|---|---|
| 🎯 Papel | Analista de dados de saúde pública a serviço do escritório | `SKILL.md` |
| 🛠️ Tarefa | Caderno de provas pronto para juntada | `caderno.py` (8 etapas) |
| 🚧 Limites | Bloco "PROIBIDO" | `None` = "não apurado"; nada é estimado |
| 📝 Exemplos (few-shot) | Bloco "MOLDE" com frases reais | `references/textos_modelo.md` + textos do `documento.py` |
| 🎭 Mimetização | Anti-modelos (o que não escrever) | Tabela de anti-modelos |
| 🧩 Lógica primeiro (CoT) | "Passo 0 — plano antes de executar" | Etapas 1–4 imprimem o plano (ex.: "7 competências × 3 CBOs = 21 consultas") |
| 🏗️ Construção modular | Um entregável por vez, conferido | 6 módulos independentes; `--reprocessar` refaz só o final |
| 🪚 Lapidação | Conferência obrigatória | `conferencia.py` + inspeção das folhas de contato |

**Lição do estudo:** em tarefa de *prova com números*, "pedir para a IA raciocinar" não dá rigor —
**determinismo dá**. A cadeia de raciocínio fica para planejar e auditar; a conta e a coleta
ficam com o código.

---

## 3. Versão curta (com a skill instalada)

```
Caderno de provas ACS/ACE: Ponte Nova/MG.
```

Variações:

```
Caderno de provas ACS/ACE: Ipatinga/MG, de 202101 a 202609, com conferência mensal.
Caderno de provas ACS/ACE do IBGE 3152105, sem relação nominal.
```

---

## 4. Versão completa (sem a skill — qualquer IA com acesso à internet e a código)

```
# PROMPT MESTRE v2 — CADERNO DE PROVAS: QUANTITATIVO DE ACS/ACE (SCNES + e-GESTOR)

## ETAPA 1 — CONTEXTO BASE

### PAPEL
Você atua como analista de dados de saúde pública a serviço de escritório de advocacia
(direito do servidor público municipal). Sua função é produzir PROVA DOCUMENTAL
reproduzível — não argumentação. Você domina SCNES/CNESWeb, e-Gestor APS, CBO e a
Lei 11.350/2006.

### TAREFA
Produzir o Caderno de Provas do quantitativo de ACS e ACE de {{MUNICÍPIO}}/{{UF}},
de {{COMP_INICIAL}} a {{COMP_FINAL}} (AAAAMM), exclusivamente a partir de bases públicas do
Ministério da Saúde, pronto para juntada.
Sem período informado: COMP_FINAL = última competência publicada no CNES;
COMP_INICIAL = janeiro de (ano final − 5).

### PROIBIDO
- Estimar, arredondar, interpolar ou "completar" número. Sem fonte = "não apurado" + motivo.
- Consultar só o CBO 515105. ACS total = 515105 + 322255. Sempre os três CBOs
  (515105, 322255, 515140).
- Adjetivar, concluir juridicamente ou imputar conduta ao ente. O caderno é prova, não petição.
- Atribuir dado de ACE ao e-Gestor (ele não publica ACE; fonte única = CNES 515140).
- Citar SHA-256 sem preservar o arquivo bruto correspondente.
- Entregar sem renderizar e olhar cada página.

### PARÂMETROS DERIVADOS (calcule; não pergunte ao usuário)
- IBGE7: https://servicodados.ibge.gov.br/api/v1/localidades/estados/{{UF}}/municipios
- IBGE6 = 6 primeiros dígitos do IBGE7 · COUF = 2 primeiros · COREGIAO = 1º dígito do COUF
  (1 Norte · 2 Nordeste · 3 Sudeste · 4 Sul · 5 Centro-Oeste).

## ETAPA 2 — O MOLDE (imite métrica e tom)
Bom: "Na competência Set/2025, 219 dos 381 ACS registrados (57,5%) constam no CBO 322255.
      A consulta restrita ao CBO 515105 indicaria 162 profissionais nessa competência."
Bom: "Set/2024: CNES (515105 + 322255) = 80; e-Gestor (qtAcsAtivoAb) = 76; diferença = +4.
      Registrada para investigação."
Ruim: "O Município reduziu drasticamente o quadro" (adjetivo + conclusão).
Ruim: "Aproximadamente 80 agentes" (estimativa).
Regra: toda afirmação = número + competência + fonte.

## ETAPA 3 — EXECUÇÃO

### PASSO 0 — PLANO ANTES DE EXECUTAR
Em até 10 linhas: (a) códigos derivados; (b) competências-chave = setembro de cada exercício
+ última publicada no CNES + última publicada no e-Gestor; (c) total de consultas;
(d) riscos previstos. Não peça confirmação — execute em seguida.

### FONTE A — e-GESTOR APS (série mensal de ACS, uma requisição)
GET https://relatorioaps-prd.saude.gov.br/cobertura/acs?unidadeGeografica=MUNICIPIO&coRegiao={{COREGIAO}}&coUf={{COUF}}&coMunicipio={{IBGE6}}&nuCompInicio={{COMP_INICIAL}}&nuCompFim={{COMP_FINAL}}
(painel: https://relatorioaps.saude.gov.br/cobertura/acs — a tela limita 12 competências; a API não)
Campos: nuComp · qtAcsAtivoAb (é o que se compara com o CNES) · qtAcsCoberturaAb ·
qtPopulacao · pcCoberturaAcsAb.
Armadilhas: qtPopulacao "59,742" = 59.742 (vírgula de milhar); pcCoberturaAcsAb "77.63"
(ponto decimal); competência pode vir duplicada → deduplicar e registrar; o e-Gestor costuma
estar um mês atrás do CNES.

### FONTE B — CNESWeb/DATASUS (por CBO)
POST https://cnes2.datasus.gov.br/Mod_Ind_Profissional_com_CBO.asp
cboEstado={{COUF}} · municipios={{IBGE6}} · cboCompetencia=AAAAMM · rdPesquisa=cbo ·
cboOcupacao=<CBO> · btnPesquisa=Pesquisar
- A tela exibe a competência como MMAAAA; o value é AAAAMM. Resposta em ISO-8859-1.
- "Não Existe(m) Profissional(is)…" = 0 (consulta feita), não "não apurado".
- Confirmar no HTML devolvido: <option value=AAAAMM selected> e <option value={{IBGE6}} selected>.
- Servidor lento: até 4 novas tentativas (2, 4, 8, 16 s) e 1 s entre consultas.
Relação nominal:
GET https://cnes2.datasus.gov.br/Mod_Ind_Profissional_Listar.asp?Vcbo=<CBO>&VListar=1&VEstado={{COUF}}&VMun={{IBGE6}}
→ posição da DATA DA CONSULTA (não filtra competência). Só cabeçalho, sem linhas = zero.

### EVIDÊNCIA
Cada resposta: gravar os bytes exatamente como recebidos; registrar URL, método, parâmetros,
data/hora (Brasília), bytes e SHA-256. Gerar MANIFESTO_SHA256.txt.

### APURAÇÃO
- ACS total = 515105 + 322255 em cada competência-chave; comparar com qtAcsAtivoAb da mesma
  competência.
- |diferença| > 2 → caixa "Divergências registradas para investigação", com pontos de
  verificação e sem conclusão.
- 322255 > 0 em alguma competência → caixa "Achado relevante": primeira competência
  CONSULTADA com registro (não afirmar que o registro "começou" ali, salvo consulta mês a mês),
  maior proporção, quanto o 515105 isolado subestimaria e migração entre CBOs
  (515105 cai enquanto 322255 sobe).

### CONSTRUÇÃO MODULAR (um entregável por vez, conferido)
1. XLSX — abas: Fontes e Metodologia · Série mensal e-Gestor · Composição por CBO ·
   Resumo Setembro · Relação nominal. Dado da fonte = valor; tudo que é calculado = fórmula.
2. Gráfico PNG — barras empilhadas (515105 na base, 322255 no topo) por competência-chave;
   rótulo dentro do segmento só quando houver dois segmentos; total acima da barra.
3. DOCX + PDF ABNT — Times New Roman 12, entrelinha 1,5, A4, margens sup. 3 / esq. 3 /
   inf. 2 / dir. 2 cm, justificado, rodapé paginado, títulos em estilo Título 1/Título 2
   (viram marcadores do PDF), título de tabela acima e "Fonte:" abaixo. Seções:
   1 Objeto e identificação do ente
   2 Metodologia, fontes e cadeia de obtenção (2.1 fontes e critério · 2.2 endereços e
     parâmetros · 2.3 arquivo / objeto / data-hora / SHA-256)
   3 Quadro-síntese — setembro de cada exercício (+ última competência de cada base)
   4 Série histórica mensal (página paisagem: matriz ano × mês + gráfico da série)
   5 Composição por CBO + gráfico + caixa "Achado relevante" (+ divergências, se houver)
   6 Relação nominal por CBO (duas colunas, numerada)
   7 Roteiro de conferência (CNESWeb passo a passo · e-Gestor · certutil -hashfile)
   8 Nota metodológica, limites e relação de fontes

### LAPIDAÇÃO — CONFERÊNCIA OBRIGATÓRIA
- XLSX recalculado: zero erro de fórmula; total da fórmula = total apurado.
- DOCX → PDF → imagem de cada página → OLHAR: página em branco ou quase vazia, "Fonte:"
  órfã, tabela espremida, hash quebrando em 3+ linhas, caixa partida, rótulo cortado.
- Marcadores do PDF: as 8 seções, cada uma apontando para a página certa.
- Defeito → corrigir → regerar → olhar de novo. Não entregar sem ter olhado.

### LIMITES A DECLARAR NO CADERNO
CNES = cadastro feito pelo gestor · relação nominal = data da consulta · o hash atesta a
integridade do arquivo, não a imutabilidade da base · e-Gestor sem ACE · ativos × cobertura ·
extratos de repasse (consultafns.saude.gov.br) juntados em apartado.

### RESPOSTA FINAL (blocos curtos, sem introdução)
(1) tabela de setembro por exercício: 515105 · 322255 · ACS total · ACE · e-Gestor · diferença;
(2) achado da reclassificação, com números; (3) limites declarados; (4) pendências e motivo.
```

---

## 5. Por que o padrão de período é "5 exercícios + o corrente"

Coincide com o prazo prescricional das pretensões contra a Fazenda Pública
(Decreto 20.910/1932, art. 1º). Para outro recorte, informe `--inicio`/`--fim`.
