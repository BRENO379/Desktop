# -*- coding: utf-8 -*-
"""
apuracao.py — Organiza os números coletados e aplica a REGRA CRÍTICA:

    ACS total = CBO 515105 + CBO 322255

Compara, competência a competência, o total do CNES com o qtAcsAtivoAb do e-Gestor.
Diferença maior que 2 (em módulo) = registrar para investigação — nunca silenciar.
Nada aqui estima número: o que não veio da fonte fica como None ("não apurado").
"""

from fontes import CBOS, CBOS_ACS, CBO_ACE

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
LIMITE_DIVERGENCIA = 2


def pct_br(valor: float) -> str:
    """66.94 -> '66,9%' (vírgula decimal)."""
    return f"{valor:.1f}%".replace(".", ",")


def fmt_dif(v) -> str:
    """Diferença com sinal: +4, -2, 0; None -> '—'."""
    if v is None:
        return "—"
    return f"+{v}" if v > 0 else str(v)


def rotulo_comp(comp: str) -> str:
    """'202509' -> 'Set/2025'."""
    return f"{MESES[int(comp[4:]) - 1]}/{comp[:4]}"


def comp_valida(comp: str) -> bool:
    return isinstance(comp, str) and len(comp) == 6 and comp.isdigit() and 1 <= int(comp[4:]) <= 12


def meses_entre(inicio: str, fim: str):
    a, m = int(inicio[:4]), int(inicio[4:])
    saida = []
    while f"{a}{m:02d}" <= fim:
        saida.append(f"{a}{m:02d}")
        m += 1
        if m == 13:
            a, m = a + 1, 1
    return saida


def competencias_chave(inicio, fim, disponiveis_cnes, ultima_egestor, mensal=False):
    """
    Setembro de cada exercício do período + última competência publicada no CNES
    + última competência publicada no e-Gestor (para a conferência ficar pareada).
    Com mensal=True, todas as competências do período (conferência completa, mais lenta).
    Devolve (lista_de_competencias, pendencias).
    """
    pend = []
    disp = set(disponiveis_cnes or [])
    if mensal:
        alvo = meses_entre(inicio, fim)
    else:
        alvo = [f"{a}09" for a in range(int(inicio[:4]), int(fim[:4]) + 1) if inicio <= f"{a}09" <= fim]
    extras = []
    if disp:
        ult_cnes = max(c for c in disp if c <= fim) if any(c <= fim for c in disp) else None
        if ult_cnes:
            extras.append(ult_cnes)
    if ultima_egestor and inicio <= ultima_egestor <= fim:
        extras.append(ultima_egestor)
    chave = sorted(set(alvo + extras))
    if disp:
        fora = [c for c in chave if c not in disp]
        for c in fora:
            pend.append(f"Competência {rotulo_comp(c)} não é oferecida pelo CNESWeb (ainda não publicada ou fora do histórico) — não apurada.")
        chave = [c for c in chave if c in disp]
    return chave, pend


def montar_quadro(chave, cnes, egestor_linhas, ultima_cnes=None, ultima_egestor=None):
    """
    cnes: {(comp, cbo): resultado_consultar_cnes_cbo}
    Devolve lista de linhas do quadro de composição por CBO com a conferência.
    """
    eg = {l["nuComp"]: l for l in egestor_linhas}
    quadro = []
    for comp in chave:
        v = {cbo: (cnes.get((comp, cbo)) or {}).get("total") for cbo in CBOS}
        acs = None if any(v[c] is None for c in CBOS_ACS) else v["515105"] + v["322255"]
        e = eg.get(comp, {}).get("qtAcsAtivoAb")
        dif = None if (acs is None or e is None) else acs - e
        if acs is None:
            situacao = "Não apurado (CNES)"
        elif e is None:
            situacao = "Sem dado no e-Gestor"
        elif abs(dif) > LIMITE_DIVERGENCIA:
            situacao = "Divergência > 2 — investigar"
        else:
            situacao = "Confere"
        papel = []
        if comp.endswith("09"):
            papel.append("setembro")
        if comp == ultima_cnes:
            papel.append("última CNES")
        if comp == ultima_egestor:
            papel.append("última e-Gestor")
        quadro.append({
            "comp": comp, "rotulo": rotulo_comp(comp), "papel": ", ".join(papel),
            "cbo515105": v["515105"], "cbo322255": v["322255"], "acs_total": acs,
            "ace515140": v[CBO_ACE], "egestor_ativo": e, "diferenca": dif, "situacao": situacao,
            "evidencias": [(cnes.get((comp, c)) or {}).get("evidencia", "") for c in CBOS],
        })
    return quadro


def achado_reclassificacao(quadro):
    """
    Verifica se há ACS lançados como 'Técnico em ACS' (CBO 322255).
    Texto estritamente factual: números, competências e proporção — sem adjetivo, sem conclusão jurídica.
    """
    com_dado = [q for q in quadro if q["acs_total"] is not None]
    com_tecnico = [q for q in com_dado if (q["cbo322255"] or 0) > 0]
    if not com_dado:
        return {"ha_achado": False, "texto": ["Não foi possível apurar a composição por CBO (consultas ao CNES sem resposta)."], "linhas": []}
    if not com_tecnico:
        return {"ha_achado": False, "linhas": [], "texto": [
            "Nas competências consultadas, o CNES não registra profissionais no CBO 322255 "
            "(Técnico em Agente Comunitário de Saúde) neste município. "
            "O quantitativo de ACS corresponde, portanto, ao CBO 515105."]}
    texto = []
    primeira = com_tecnico[0]
    texto.append(
        f"A partir da competência {primeira['rotulo']} (primeira competência consultada com registro), "
        f"o CNES passa a registrar profissionais no CBO 322255 (Técnico em Agente Comunitário de Saúde) neste município."
    )
    linhas = []
    for q in com_tecnico:
        pct = 100.0 * q["cbo322255"] / q["acs_total"] if q["acs_total"] else 0.0
        linhas.append((q["rotulo"], q["cbo515105"], q["cbo322255"], q["acs_total"], pct))
    maior = max(linhas, key=lambda x: x[4])
    texto.append(
        f"Na competência {maior[0]}, {maior[2]} dos {maior[3]} ACS registrados ({pct_br(maior[4])}) constam no CBO 322255. "
        f"A consulta restrita ao CBO 515105 indicaria {maior[1]} profissionais nessa competência, "
        f"ou seja, {maior[3] - maior[1]} a menos que o total apurado."
    )
    # Migração entre CBOs: a transição em que o 322255 aparece (de zero para positivo) enquanto o 515105 cai
    for a, b in zip(com_dado, com_dado[1:]):
        if a["cbo322255"] == 0 and b["cbo322255"] > 0 and b["cbo515105"] < a["cbo515105"]:
            texto.append(
                f"Entre {a['rotulo']} e {b['rotulo']}, o CBO 515105 passou de {a['cbo515105']} para {b['cbo515105']} "
                f"e o CBO 322255 de {a['cbo322255']} para {b['cbo322255']}; o total de ACS passou de "
                f"{a['acs_total']} para {b['acs_total']}."
            )
    return {"ha_achado": True, "texto": texto, "linhas": linhas}


def matriz_egestor(egestor_linhas, inicio, fim, campo="qtAcsAtivoAb"):
    """Matriz ano × mês. Célula vazia (None) = competência fora do período ou não publicada."""
    eg = {l["nuComp"]: l for l in egestor_linhas}
    anos = list(range(int(inicio[:4]), int(fim[:4]) + 1))
    return [(ano, [eg.get(f"{ano}{m:02d}", {}).get(campo) for m in range(1, 13)]) for ano in anos]


def divergencias(quadro):
    return [q for q in quadro if q["situacao"].startswith("Divergência")]
