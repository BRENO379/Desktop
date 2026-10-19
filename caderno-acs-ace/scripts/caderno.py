# -*- coding: utf-8 -*-
"""
caderno.py — Gera o CADERNO DE PROVAS do quantitativo de ACS/ACE de um município, de ponta a ponta.

USO (exemplos):
    python caderno.py --municipio "Ponte Nova" --uf MG
    python caderno.py --municipio "Ipatinga" --uf MG --inicio 202101 --fim 202609
    python caderno.py --ibge 3152105 --saida "C:\\Users\\voce\\Desktop"
    python caderno.py --municipio "Ponte Nova" --uf MG --conferencia-mensal   (CNES mês a mês — mais lento)

Padrões: --fim = última competência publicada no CNES; --inicio = janeiro de (ano do fim − 5),
ou seja, os cinco exercícios anteriores completos + o corrente.

Saída (uma pasta por execução):
    CADERNO_ACS_ACE_<MUNICIPIO>_<UF>.docx / .pdf / .xlsx
    GRAFICO_1_COMPOSICAO_CBO.png · GRAFICO_2_SERIE_MENSAL.png
    evidencias/  (respostas brutas + MANIFESTO_SHA256.txt + cadeia_de_obtencao.json)
    conferencia/ (páginas renderizadas + folhas de contato)
    RESUMO.md    (quadro de setembro, achado, limites, pendências)
"""

import argparse
import json
import re
import sys
import traceback
from pathlib import Path

try:                                   # console do Windows com acentos
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import fontes
import apuracao
from fontes import CBOS, Evidencias, agora_brasilia, sem_acento


def etapa(n, total, texto):
    print(f"\n[{n}/{total}] {texto}", flush=True)


def comp_arg(valor):
    if valor is None:
        return None
    v = re.sub(r"\D", "", valor)
    if not apuracao.comp_valida(v):
        raise argparse.ArgumentTypeError(f"competência inválida: {valor} (use AAAAMM, ex.: 202509)")
    return v


def main(argv=None):
    ap = argparse.ArgumentParser(description="Caderno de Provas — quantitativo de ACS/ACE (SCNES + e-Gestor)")
    ap.add_argument("--municipio", help='Nome do município, ex.: "Ponte Nova"')
    ap.add_argument("--uf", help="Sigla da UF, ex.: MG")
    ap.add_argument("--ibge", help="Código IBGE (6 ou 7 dígitos) — dispensa nome/UF")
    ap.add_argument("--inicio", type=comp_arg, help="Competência inicial AAAAMM")
    ap.add_argument("--fim", type=comp_arg, help="Competência final AAAAMM (padrão: última publicada no CNES)")
    ap.add_argument("--saida", default=".", help="Pasta onde criar a pasta do caderno (padrão: pasta atual)")
    ap.add_argument("--conferencia-mensal", action="store_true",
                    help="Consulta o CNES em TODAS as competências do período (conferência completa; ~10–20 min)")
    ap.add_argument("--sem-nominal", action="store_true", help="Não baixa a relação nominal")
    ap.add_argument("--sem-pdf", action="store_true", help="Não converte para PDF nem confere páginas")
    ap.add_argument("--reprocessar", metavar="PASTA",
                    help="Refaz XLSX/gráficos/DOCX/PDF a partir do dados.json de uma pasta já coletada (sem nova consulta)")
    a = ap.parse_args(argv)

    if a.reprocessar:
        pasta = Path(a.reprocessar).expanduser().resolve()
        try:
            dados = json.loads((pasta / "dados.json").read_text(encoding="utf-8"))
        except Exception as e:
            print(f"ERRO: não foi possível ler {pasta / 'dados.json'}: {e}")
            return 1
        print(f"Reprocessando {pasta.name} (sem nova consulta às fontes)...")
        return gerar_saidas(pasta, dados, a, 7, 8)

    total = 8
    avisos, pendencias = [], []
    sessao = fontes.nova_sessao()
    momento = agora_brasilia()

    # ------------------------------------------------------------------ 1
    etapa(1, total, "Identificando o município (IBGE)...")
    try:
        mun = fontes.resolver_municipio(sessao, a.municipio, a.uf, a.ibge)
    except Exception as e:
        print(f"  ERRO: {e}")
        return 1
    print(f"  {mun['nome']}/{mun['uf']} · IBGE {mun['ibge7'] or '—'} · CNES {mun['ibge6']} · UF {mun['couf']} · região {mun['coregiao']}")

    nome_pasta = f"CADERNO_ACS_ACE_{re.sub(r'[^A-Z0-9]+', '_', sem_acento(mun['nome'] or mun['ibge6']))}_{mun['uf'] or mun['couf']}"
    pasta = Path(a.saida).expanduser().resolve() / f"{nome_pasta}_{momento.strftime('%Y-%m-%d_%H%M')}"
    try:
        pasta.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        pasta = pasta.with_name(pasta.name + "_b")
        pasta.mkdir(parents=True)
    except Exception as e:
        print(f"  ERRO: não foi possível criar a pasta de saída {pasta}: {e}")
        return 1
    ev = Evidencias(pasta / "evidencias")
    print(f"  Pasta de saída: {pasta}")

    # ------------------------------------------------------------------ 2
    etapa(2, total, "Lendo competências disponíveis no CNESWeb...")
    disponiveis = fontes.competencias_disponiveis(sessao, ev)
    if disponiveis:
        print(f"  {len(disponiveis)} competências; mais recente: {apuracao.rotulo_comp(disponiveis[0])}")
    else:
        pendencias.append("Não foi possível ler a lista de competências do CNESWeb; as consultas foram feitas às cegas.")
        print("  AVISO: lista de competências indisponível.")
    fim = a.fim or (disponiveis[0] if disponiveis else momento.strftime("%Y%m"))
    if disponiveis and fim > disponiveis[0]:
        avisos.append(f"Competência final pedida ({fim}) é posterior à última publicada no CNES "
                      f"({disponiveis[0]}); usada a última publicada.")
        fim = disponiveis[0]
    inicio = a.inicio or f"{int(fim[:4]) - 5}01"
    if inicio > fim:
        print(f"  ERRO: competência inicial {inicio} é posterior à final {fim}.")
        return 1
    print(f"  Período: {apuracao.rotulo_comp(inicio)} a {apuracao.rotulo_comp(fim)}")

    # ------------------------------------------------------------------ 3
    etapa(3, total, "Baixando a série mensal de ACS do e-Gestor APS (requisição única)...")
    egestor, av = fontes.coletar_egestor(sessao, ev, mun, inicio, fim)
    avisos.extend(av)
    ultima_eg = egestor[-1]["nuComp"] if egestor else None
    faltam_eg = [c for c in apuracao.meses_entre(inicio, ultima_eg or fim) if c not in {l["nuComp"] for l in egestor}]
    if egestor:
        print(f"  {len(egestor)} competências; última publicada: {apuracao.rotulo_comp(ultima_eg)}")
        if faltam_eg:
            pendencias.append("e-Gestor sem dado nas competências: " + ", ".join(apuracao.rotulo_comp(c) for c in faltam_eg) + ".")
    else:
        pendencias.append("Série do e-Gestor não apurada — conferência CNES × e-Gestor prejudicada.")
    for x in av:
        print(f"  AVISO: {x}")

    # ------------------------------------------------------------------ 4
    chave, pend = apuracao.competencias_chave(inicio, fim, disponiveis, ultima_eg, mensal=a.conferencia_mensal)
    pendencias.extend(pend)
    ultima_cnes = max((c for c in disponiveis if c <= fim), default=None) if disponiveis else None
    n_cons = len(chave) * len(CBOS)
    etapa(4, total, f"Consultando o CNESWeb: {len(chave)} competências × 3 CBOs = {n_cons} consultas...")
    cnes = {}
    for comp in chave:
        linha = []
        for cbo in CBOS:
            r = fontes.consultar_cnes_cbo(sessao, ev, mun, comp, cbo)
            cnes[(comp, cbo)] = r
            linha.append(f"{cbo}={r['total'] if r['total'] is not None else 'n/apurado'}")
            if r["status"] == "nao_apurado":
                pendencias.append(f"CNES {apuracao.rotulo_comp(comp)} CBO {cbo}: {r['aviso']}.")
            elif r["aviso"]:
                avisos.append(f"CNES {apuracao.rotulo_comp(comp)} CBO {cbo}: {r['aviso']}.")
        print(f"  {apuracao.rotulo_comp(comp)}: " + "  ".join(linha), flush=True)

    # ------------------------------------------------------------------ 5
    nominal = {}
    if a.sem_nominal:
        etapa(5, total, "Relação nominal: pulada (--sem-nominal).")
        nominal = {cbo: {"nomes": None, "aviso": "não solicitada nesta execução"} for cbo in CBOS}
    else:
        etapa(5, total, "Baixando a relação nominal por CBO (posição da data da consulta)...")
        for cbo in CBOS:
            r = fontes.baixar_nominal(sessao, ev, mun, cbo)
            nominal[cbo] = r
            if r["nomes"] is None:
                pendencias.append(f"Relação nominal CBO {cbo}: {r['aviso']}.")
                print(f"  CBO {cbo}: não apurada ({r['aviso']})")
            else:
                print(f"  CBO {cbo}: {len(r['nomes'])} nomes")

    # ------------------------------------------------------------------ 6
    etapa(6, total, "Apurando (ACS = 515105 + 322255) e conferindo com o e-Gestor...")
    quadro = apuracao.montar_quadro(chave, cnes, egestor, ultima_cnes, ultima_eg)
    achado = apuracao.achado_reclassificacao(quadro)
    for q in apuracao.divergencias(quadro):
        avisos.append(f"Divergência > 2 em {q['rotulo']}: CNES {q['acs_total']} × e-Gestor {q['egestor_ativo']} "
                      f"(diferença {apuracao.fmt_dif(q['diferenca'])}) — registrada na seção 5 para investigação.")
    # relação nominal × total da última competência
    ult = next((q for q in quadro if q["comp"] == ultima_cnes), None)
    if ult:
        campo = {"515105": "cbo515105", "322255": "cbo322255", "515140": "ace515140"}
        for cbo, r in nominal.items():
            if r.get("nomes") is not None and ult[campo[cbo]] is not None and len(r["nomes"]) != ult[campo[cbo]]:
                avisos.append(f"Relação nominal CBO {cbo} tem {len(r['nomes'])} nomes; o total na competência "
                              f"{ult['rotulo']} é {ult[campo[cbo]]} — a relação reflete a data da consulta.")
    ev.gravar_manifesto()
    for q in quadro:
        print(f"  {q['rotulo']:>9}  ACS {q['acs_total'] if q['acs_total'] is not None else '—':>4}  "
              f"e-Gestor {q['egestor_ativo'] if q['egestor_ativo'] is not None else '—':>4}  {q['situacao']}")

    dados = {
        "municipio": mun, "inicio": inicio, "fim": fim,
        "data_extracao": momento.strftime("%d/%m/%Y %H:%M (horário de Brasília)"),
        "data_extracao_curta": momento.strftime("%d/%m/%Y"),
        "ultima_cnes": ultima_cnes, "ultima_egestor": ultima_eg,
        "egestor": egestor, "quadro": quadro, "achado": achado,
        "matriz": apuracao.matriz_egestor(egestor, inicio, fim),
        "nominal": nominal, "evidencias": ev.registros,
        "avisos": avisos, "pendencias": pendencias,
    }
    (pasta / "dados.json").write_text(json.dumps(dados, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    return gerar_saidas(pasta, dados, a, 7, total)


def gerar_saidas(pasta, dados, a, n, total):
    """Etapas finais: XLSX, gráficos, DOCX, PDF e conferência. Também usada pelo --reprocessar."""
    mun, quadro, egestor, pendencias = dados["municipio"], dados["quadro"], dados["egestor"], dados["pendencias"]
    nome_pasta = f"CADERNO_ACS_ACE_{re.sub(r'[^A-Z0-9]+', '_', sem_acento(mun['nome'] or mun['ibge6']))}_{mun['uf'] or mun['couf']}"
    etapa(n, total, "Gerando XLSX, gráficos e DOCX (ABNT)...")
    base = nome_pasta
    arq = {"xlsx": pasta / f"{base}.xlsx", "docx": pasta / f"{base}.docx"}
    graficos = {}
    try:
        import grafico
        titulo = f"ACS por CBO — {mun['nome']}/{mun['uf']}"
        graficos["composicao"] = grafico.grafico_composicao(quadro, pasta / "GRAFICO_1_COMPOSICAO_CBO.png", titulo)
        graficos["serie"] = grafico.grafico_serie(egestor, quadro, pasta / "GRAFICO_2_SERIE_MENSAL.png",
                                                  f"ACS ativos por mês — {mun['nome']}/{mun['uf']}")
        print("  gráficos ok")
    except Exception as e:
        pendencias.append(f"Gráficos não gerados: {e}")
        print(f"  AVISO gráficos: {e}")
    try:
        import planilha
        planilha.gerar_xlsx(dados, arq["xlsx"])
        print(f"  {arq['xlsx'].name}")
    except Exception as e:
        pendencias.append(f"XLSX não gerado: {e}")
        print(f"  ERRO XLSX: {e}")
        traceback.print_exc()
    try:
        import documento
        documento.gerar_docx(dados, arq["docx"], graficos)
        print(f"  {arq['docx'].name}")
    except Exception as e:
        pendencias.append(f"DOCX não gerado: {e}")
        print(f"  ERRO DOCX: {e}")
        traceback.print_exc()

    # ------------------------------------------------------------------ 8
    conf = None
    if a.sem_pdf or not arq["docx"].exists():
        etapa(n + 1, total, "Conferência: pulada.")
    else:
        etapa(n + 1, total, "Convertendo em PDF e conferindo (páginas, marcadores, fórmulas)...")
        import conferencia
        conf = conferencia.conferir_tudo(arq["docx"], arq["xlsx"], quadro, pasta / "conferencia")
        (pasta / "conferencia").mkdir(exist_ok=True)
        (pasta / "conferencia" / "relatorio_conferencia.json").write_text(
            json.dumps(conf, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        if conf["pdf"]:
            m = conf["marcadores"] or {}
            print(f"  PDF: {Path(conf['pdf']).name} · {m.get('paginas')} páginas")
            print(f"  Páginas em branco: {conf['paginas_em_branco'] or 'nenhuma'}")
            print(f"  Marcadores: {len(m.get('marcadores', []))} · seções faltando: {m.get('secoes_faltando') or 'nenhuma'}")
            print(f"  Folhas de contato p/ inspeção visual: {len(conf['folhas_contato'])} (pasta conferencia/)")
        x = conf.get("xlsx") or {}
        if x.get("ok") is True:
            print("  XLSX recalculado: zero erro de fórmula; totais conferem com a apuração.")
        elif x:
            print(f"  XLSX: {x}")
        for e in conf["erros"]:
            print(f"  ERRO: {e}")

    # ------------------------------------------------------------------ Evidências compactadas (para juntada)
    try:
        import shutil
        shutil.make_archive(str(pasta / "EVIDENCIAS_SHA256"), "zip", root_dir=pasta, base_dir="evidencias")
        print("  EVIDENCIAS_SHA256.zip pronto para juntada")
    except Exception as e:
        pendencias.append(f"Pasta de evidências não compactada: {e}")

    # ------------------------------------------------------------------ Resumo final
    escrever_resumo(pasta, dados, conf)
    print(f"\nConcluído. Abra: {pasta}")
    print("ATENÇÃO: olhe as folhas de contato (pasta conferencia/) antes de juntar o caderno.")
    return 0


def escrever_resumo(pasta, dados, conf):
    """RESUMO.md — os 4 blocos da resposta final."""
    f = lambda v: "—" if v is None else str(v)
    q = dados["quadro"]
    L = [f"# Resumo — {dados['municipio']['nome']}/{dados['municipio']['uf']} "
         f"({apuracao.rotulo_comp(dados['inicio'])} a {apuracao.rotulo_comp(dados['fim'])})", "",
         "## 1. Quadro de setembro por exercício", "",
         "| Exercício | 515105 | 322255 | ACS total | ACE 515140 | e-Gestor | Dif. | Situação |",
         "|---|---|---|---|---|---|---|---|"]
    for x in q:
        if x["comp"].endswith("09"):
            d = x["diferenca"]
            L.append(f"| {x['comp'][:4]} | {f(x['cbo515105'])} | {f(x['cbo322255'])} | **{f(x['acs_total'])}** | "
                     f"{f(x['ace515140'])} | {f(x['egestor_ativo'])} | {apuracao.fmt_dif(d)} | {x['situacao']} |")
    for x in q:
        if not x["comp"].endswith("09"):
            d = x["diferenca"]
            L.append(f"| {x['rotulo']} ({x['papel']}) | {f(x['cbo515105'])} | {f(x['cbo322255'])} | "
                     f"**{f(x['acs_total'])}** | {f(x['ace515140'])} | {f(x['egestor_ativo'])} | "
                     f"{apuracao.fmt_dif(d)} | {x['situacao']} |")
    L += ["", "## 2. Reclassificação de CBO", ""] + [f"- {t}" for t in dados["achado"]["texto"]]
    L += ["", "## 3. Limites declarados", "",
          "- CNES = cadastro feito pelo próprio gestor municipal.",
          "- Relação nominal = posição da data da consulta (CNESWeb não filtra competência pretérita).",
          "- e-Gestor não publica ACE — ACE tem fonte única (CNES).",
          "- Extratos de repasse (consultafns.saude.gov.br) não integram o caderno — juntar em apartado."]
    L += ["", "## 4. Pendências e avisos", ""]
    regs = dados["pendencias"] + dados["avisos"]
    L += [f"- {r}" for r in regs] if regs else ["- Nenhuma: todas as consultas retornaram resposta válida."]
    if conf:
        m = conf.get("marcadores") or {}
        x = conf.get("xlsx") or {}
        L += ["", "## Conferência automática", "",
              f"- Páginas do PDF: {m.get('paginas', '—')} · em branco: {conf.get('paginas_em_branco') or 'nenhuma'}",
              f"- Marcadores do PDF: {len(m.get('marcadores', []))} · seções faltando: {m.get('secoes_faltando') or 'nenhuma'}",
              f"- XLSX: {'zero erro de fórmula; totais conferem' if x.get('ok') else x}",
              "- **Inspeção visual obrigatória:** folhas de contato em `conferencia/`."]
    (pasta / "RESUMO.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário.")
        sys.exit(130)
