# -*- coding: utf-8 -*-
"""
grafico.py — Gráficos PNG do caderno (impressão, fundo branco).

Gráfico 1: barras empilhadas por competência-chave — CBO 515105 na base, CBO 322255 no topo,
           rótulo direto em cada segmento e total acima da barra.
Gráfico 2: série mensal do e-Gestor (linha) com os totais do CNES (pontos) nas mesmas competências.

Cores validadas para daltonismo (azul #2a78d6 × laranja #eb6834: ΔE CVD 24,7).
"""

import matplotlib
matplotlib.use("Agg")                     # sem janela — funciona em servidor e no Windows
import matplotlib.pyplot as plt
from matplotlib import font_manager

AZUL = "#2a78d6"      # CBO 515105
LARANJA = "#eb6834"   # CBO 322255
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
GRADE = "#e4e3df"


def _fonte_serifada():
    """Times New Roman se existir (Windows); senão Liberation Serif (métrica idêntica); senão serif."""
    disponiveis = {f.name for f in font_manager.fontManager.ttflist}
    for nome in ("Times New Roman", "Liberation Serif", "DejaVu Serif"):
        if nome in disponiveis:
            return nome
    return "serif"


def _estilo():
    plt.rcParams.update({
        "font.family": _fonte_serifada(), "font.size": 10,
        "axes.edgecolor": TINTA_2, "axes.labelcolor": TINTA_2,
        "xtick.color": TINTA_2, "ytick.color": TINTA_2,
        "axes.spines.top": False, "axes.spines.right": False,
    })


def grafico_composicao(quadro, caminho, titulo):
    """Barras empilhadas 515105 + 322255 por competência-chave (só as apuradas)."""
    _estilo()
    linhas = [q for q in quadro if q["acs_total"] is not None]
    if not linhas:
        return None
    rot = [q["rotulo"] + ("*" if not q["comp"].endswith("09") else "") for q in linhas]
    base = [q["cbo515105"] for q in linhas]
    topo = [q["cbo322255"] for q in linhas]
    tot = [q["acs_total"] for q in linhas]
    maximo = max(tot) or 1

    larg_pol = max(6.3, 1.0 * len(linhas) + 1.5)          # ~16 cm na página retrato
    fig, ax = plt.subplots(figsize=(min(larg_pol, 9.4), 3.9), dpi=200)
    x = range(len(linhas))
    # Borda branca = respiro de 2 px entre os segmentos empilhados
    ax.bar(x, base, width=0.56, color=AZUL, edgecolor="white", linewidth=1.5,
           label="CBO 515105 — Agente Comunitário de Saúde")
    rotulo_322 = "CBO 322255 — Técnico em ACS" + (" (zero em todas as competências)" if not any(topo) else "")
    ax.bar(x, topo, width=0.56, bottom=base, color=LARANJA, edgecolor="white", linewidth=1.5,
           label=rotulo_322)

    # Rótulos diretos: dentro do segmento se couber; senão, ao lado.
    # Barra de um segmento só: basta o total acima (sem repetir o número dentro).
    for i, (vb, vt, t) in enumerate(zip(base, topo, tot)):
        if vb > 0 and vt > 0:
            if vb >= 0.09 * maximo:
                ax.text(i, vb / 2, f"{vb}", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
            else:
                ax.text(i + 0.32, vb / 2, f"{vb}", ha="left", va="center", color=TINTA, fontsize=8)
        if vt > 0 and vb > 0:
            if vt >= 0.09 * maximo:
                ax.text(i, vb + vt / 2, f"{vt}", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
            else:
                ax.text(i + 0.32, vb + vt / 2, f"{vt}", ha="left", va="center", color=TINTA, fontsize=8)
        ax.text(i, t + maximo * 0.025, f"{t}", ha="center", va="bottom", color=TINTA, fontsize=10, fontweight="bold")

    ax.set_xticks(list(x))
    ax.set_xticklabels(rot, fontsize=9)
    ax.set_ylim(0, maximo * 1.18)
    ax.set_ylabel("Profissionais (CNES)")
    ax.yaxis.grid(True, color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(titulo, fontsize=11, color=TINTA, loc="left", pad=26)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=8.5,
              handlelength=1.2, borderaxespad=0.2)
    if any(not q["comp"].endswith("09") for q in linhas):
        fig.text(0.01, 0.01, "* competência que não é setembro (última publicada).", fontsize=7.5, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(caminho, facecolor="white")
    plt.close(fig)
    return caminho


def grafico_serie(egestor_linhas, quadro, caminho, titulo):
    """Linha mensal e-Gestor (qtAcsAtivoAb) + pontos CNES (515105 + 322255) nas competências-chave."""
    _estilo()
    serie = [l for l in egestor_linhas if l["qtAcsAtivoAb"] is not None]
    if not serie:
        return None
    idx = {l["nuComp"]: i for i, l in enumerate(serie)}
    fig, ax = plt.subplots(figsize=(9.4, 3.1), dpi=200)          # largo e baixo: cabe com a matriz na mesma página paisagem
    ax.plot(range(len(serie)), [l["qtAcsAtivoAb"] for l in serie], color=AZUL, linewidth=1.6,
            label="e-Gestor APS — ACS ativos (qtAcsAtivoAb)")
    pts = [(idx[q["comp"]], q["acs_total"]) for q in quadro if q["acs_total"] is not None and q["comp"] in idx]
    if pts:
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=34, color=LARANJA, edgecolor="white",
                   linewidth=1.2, zorder=3, label="CNES — ACS total (515105 + 322255)")
    # Marcas no eixo: janeiro de cada ano
    marcas = [i for i, l in enumerate(serie) if l["nuComp"].endswith("01")] or [0]
    ax.set_xticks(marcas)
    ax.set_xticklabels([f"Jan/{serie[i]['nuComp'][:4]}" for i in marcas], fontsize=8.5)
    valores = [l["qtAcsAtivoAb"] for l in serie] + [p[1] for p in pts]
    ax.set_ylim(0, max(valores) * 1.15)
    ax.set_ylabel("ACS")
    ax.yaxis.grid(True, color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(titulo, fontsize=11, color=TINTA, loc="left", pad=22)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=8.5, borderaxespad=0.2)
    fig.tight_layout()
    fig.savefig(caminho, facecolor="white")
    plt.close(fig)
    return caminho
