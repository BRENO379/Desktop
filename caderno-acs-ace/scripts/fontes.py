# -*- coding: utf-8 -*-
"""
fontes.py — Coleta nas bases públicas do Ministério da Saúde.

O que este módulo faz:
  1. Descobre os códigos do município (IBGE 7 e 6 dígitos, UF, região) pela API do IBGE.
  2. Baixa a série mensal de ACS do e-Gestor APS (uma única requisição para o período todo).
  3. Consulta o CNESWeb por CBO e competência (515105, 322255, 515140).
  4. Baixa a relação nominal por CBO (posição da data da consulta).

Regra de ouro: TODA resposta é gravada em disco exatamente como chegou (bytes brutos),
com SHA-256 e data/hora. O caderno só usa números que vieram desses arquivos.
Falhas de rede não derrubam a automação: viram "não apurado" e entram na lista de pendências.
"""

import hashlib
import html
import json
import re
import time
import unicodedata
import difflib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Endereços das fontes (conferidos em out/2026)
# ---------------------------------------------------------------------------
URL_IBGE_MUNICIPIOS = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
URL_EGESTOR_PAINEL = "https://relatorioaps.saude.gov.br/cobertura/acs"
URL_EGESTOR_API = (
    "https://relatorioaps-prd.saude.gov.br/cobertura/acs"
    "?unidadeGeografica=MUNICIPIO&coRegiao={coregiao}&coUf={couf}"
    "&coMunicipio={ibge6}&nuCompInicio={inicio}&nuCompFim={fim}"
)
URL_CNES_CBO = "https://cnes2.datasus.gov.br/Mod_Ind_Profissional_com_CBO.asp"
URL_CNES_NOMINAL = (
    "https://cnes2.datasus.gov.br/Mod_Ind_Profissional_Listar.asp"
    "?Vcbo={cbo}&VListar=1&VEstado={couf}&VMun={ibge6}"
)

# CBOs obrigatórios — consultar OS TRÊS, sempre
CBOS = {
    "515105": "Agente Comunitário de Saúde",
    "322255": "Técnico em Agente Comunitário de Saúde",
    "515140": "Agente de Combate às Endemias",
}
CBOS_ACS = ("515105", "322255")   # ACS total = 515105 + 322255
CBO_ACE = "515140"

# Pausa entre consultas ao CNESWeb (servidor antigo e lento — não sobrecarregar)
PAUSA_CNES_SEG = 1.0


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def agora_brasilia():
    """Data/hora oficial de Brasília (usa tzdata se existir; senão UTC-3 fixo)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Sao_Paulo"))
    except Exception:
        return datetime.now(timezone(timedelta(hours=-3)))


def sha256_bytes(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def sem_acento(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", txt or "")
    return "".join(c for c in txt if not unicodedata.combining(c)).upper().strip()


def nova_sessao() -> requests.Session:
    """Sessão HTTP com novas tentativas automáticas (rede instável / servidor lento)."""
    s = requests.Session()
    tentativas = Retry(
        total=4, connect=4, read=4, backoff_factor=2,          # espera 2s, 4s, 8s, 16s
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
    )
    s.mount("https://", HTTPAdapter(max_retries=tentativas))
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CadernoProvasACS/1.0",
        "Accept-Language": "pt-BR,pt;q=0.9",
    })
    return s


class Evidencias:
    """
    Guarda cada resposta bruta em disco e registra a cadeia de obtenção
    (URL exata, método, parâmetros, data/hora, tamanho e SHA-256).
    """

    def __init__(self, pasta: Path):
        self.pasta = Path(pasta)
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.registros = []

    def gravar(self, codigo, fonte, descricao, url, metodo, parametros, resposta, extensao):
        dados = resposta.content
        nome = f"{codigo}.{extensao}"
        caminho = self.pasta / nome
        caminho.write_bytes(dados)
        reg = {
            "codigo": codigo,
            "fonte": fonte,
            "descricao": descricao,
            "url": url,
            "metodo": metodo,
            "parametros": parametros,
            "arquivo": nome,
            "bytes": len(dados),
            "sha256": sha256_bytes(dados),
            "http": resposta.status_code,
            "data_hora": agora_brasilia().strftime("%d/%m/%Y %H:%M:%S (horário de Brasília)"),
            "status": "ok",
            "erro": "",
        }
        self.registros.append(reg)
        return reg, dados

    def falha(self, codigo, fonte, descricao, url, metodo, parametros, erro):
        reg = {
            "codigo": codigo, "fonte": fonte, "descricao": descricao, "url": url,
            "metodo": metodo, "parametros": parametros, "arquivo": "", "bytes": 0,
            "sha256": "", "http": None,
            "data_hora": agora_brasilia().strftime("%d/%m/%Y %H:%M:%S (horário de Brasília)"),
            "status": "falha", "erro": str(erro)[:300],
        }
        self.registros.append(reg)
        return reg

    def gravar_manifesto(self):
        """Arquivo-texto com todos os hashes — permite conferir com certutil/sha256sum."""
        linhas = [
            "MANIFESTO DE INTEGRIDADE — respostas brutas preservadas",
            "Conferência no Windows:  certutil -hashfile \"ARQUIVO\" SHA256",
            "Conferência no Linux/Mac: sha256sum ARQUIVO",
            "",
        ]
        for r in self.registros:
            if r["status"] == "ok":
                linhas.append(f"{r['sha256']}  {r['arquivo']}  ({r['bytes']} bytes, {r['data_hora']})")
            else:
                linhas.append(f"FALHA  {r['codigo']}  — {r['erro']}")
        (self.pasta / "MANIFESTO_SHA256.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
        (self.pasta / "cadeia_de_obtencao.json").write_text(
            json.dumps(self.registros, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. IBGE — resolver o município
# ---------------------------------------------------------------------------
def _uf_sigla(m):
    """Sigla da UF no registro do IBGE (municípios novos podem vir sem microrregião)."""
    for caminho in (("microrregiao", "mesorregiao", "UF"), ("regiao-imediata", "regiao-intermediaria", "UF")):
        d = m
        for chave in caminho:
            d = (d or {}).get(chave)
        if d and d.get("sigla"):
            return d["sigla"]
    return ""


def resolver_municipio(sessao, nome=None, uf=None, ibge=None):
    """
    Devolve dict com nome oficial, UF, códigos IBGE (7 e 6 dígitos), código da UF e da região.
    Aceita o nome ("Ponte Nova") + UF ("MG") ou diretamente o código IBGE (6 ou 7 dígitos).
    Região = 1º dígito do código da UF (1 Norte, 2 Nordeste, 3 Sudeste, 4 Sul, 5 Centro-Oeste).
    """
    if ibge:
        cod = re.sub(r"\D", "", str(ibge))
        if len(cod) not in (6, 7):
            raise ValueError("Código IBGE deve ter 6 ou 7 dígitos.")
        # Busca o nome oficial e a UF na lista do estado (funciona com 6 ou 7 dígitos)
        try:
            r = sessao.get(URL_IBGE_MUNICIPIOS.format(uf=cod[:2]), timeout=(20, 60))
            r.raise_for_status()
            achado = next((m for m in r.json() if str(m["id"])[:len(cod)] == cod), None)
        except Exception as e:
            achado = None
            erro_ibge = e
        else:
            erro_ibge = "código não consta da lista do IBGE"
        if achado:
            c7 = str(achado["id"])
            return {"nome": achado["nome"], "uf": _uf_sigla(achado) or (uf or "").upper(), "ibge7": c7,
                    "ibge6": c7[:6], "couf": c7[:2], "coregiao": c7[0]}
        # Sem confirmação do IBGE: só segue se o usuário informou nome e UF (o caderno precisa identificar o ente)
        if not (nome and uf):
            raise ValueError(f"Não foi possível confirmar o código IBGE {cod} ({erro_ibge}). "
                             "Informe também --municipio e --uf.")
        return {"nome": nome, "uf": uf.upper(), "ibge7": cod if len(cod) == 7 else "",
                "ibge6": cod[:6], "couf": cod[:2], "coregiao": cod[0]}

    if not (nome and uf):
        raise ValueError("Informe --municipio e --uf, ou --ibge.")
    uf = uf.upper().strip()
    r = sessao.get(URL_IBGE_MUNICIPIOS.format(uf=uf), timeout=(20, 60))
    r.raise_for_status()
    lista = r.json()
    if not lista:
        raise ValueError(f"UF '{uf}' não encontrada no IBGE.")
    alvo = sem_acento(nome)
    for m in lista:
        if sem_acento(m["nome"]) == alvo:
            cod = str(m["id"])
            return {"nome": m["nome"], "uf": uf, "ibge7": cod, "ibge6": cod[:6],
                    "couf": cod[:2], "coregiao": cod[0]}
    parecidos = difflib.get_close_matches(alvo, [sem_acento(m["nome"]) for m in lista], n=5)
    raise ValueError(f"Município '{nome}/{uf}' não encontrado. Parecidos: {', '.join(parecidos) or 'nenhum'}")


# ---------------------------------------------------------------------------
# 2. e-Gestor APS — série mensal de ACS
# ---------------------------------------------------------------------------
def _int_br(valor):
    """'59,742' -> 59742 ; '78' -> 78. A API usa vírgula como separador de MILHAR."""
    if valor is None or str(valor).strip() == "":
        return None
    return int(re.sub(r"[^\d]", "", str(valor)))


def _float_api(valor):
    """'77.63' -> 77.63 (a API usa ponto como separador decimal)."""
    if valor is None or str(valor).strip() == "":
        return None
    return float(str(valor).replace(",", ""))


def coletar_egestor(sessao, ev: Evidencias, mun, inicio, fim):
    """
    Uma requisição para o período todo (a tela do painel limita a 12 competências; a API não).
    Retorna (linhas_normalizadas, avisos). Linhas: nuComp, qtAcsAtivoAb, qtAcsCoberturaAb,
    qtPopulacao, pcCoberturaAcsAb, anoPopulacao, origemPopulacao.
    """
    url = URL_EGESTOR_API.format(coregiao=mun["coregiao"], couf=mun["couf"], ibge6=mun["ibge6"],
                                 inicio=inicio, fim=fim)
    codigo = f"A_egestor_acs_{mun['ibge6']}_{inicio}_{fim}"
    avisos = []
    try:
        r = sessao.get(url, timeout=(20, 120))
        r.raise_for_status()
        reg, dados = ev.gravar(codigo, "e-Gestor APS", "Série mensal de ACS (cobertura APS)",
                               url, "GET", {}, r, "json")
        bruto = json.loads(dados.decode("utf-8"))
    except Exception as e:
        ev.falha(codigo, "e-Gestor APS", "Série mensal de ACS", url, "GET", {}, e)
        return [], [f"e-Gestor indisponível ou resposta inválida: {e}"]

    if not isinstance(bruto, list):
        return [], ["e-Gestor devolveu formato inesperado (não é lista) — série não apurada."]
    if not bruto:
        return [], ["e-Gestor devolveu lista vazia para o período — série não apurada."]

    # Conferir se a resposta é mesmo do município pedido
    outros = {x.get("coMunicipioIbge") for x in bruto} - {mun["ibge6"]}
    if outros:
        avisos.append(f"Resposta do e-Gestor contém códigos de outros municípios: {sorted(outros)} — descartados.")

    por_comp = {}
    for x in bruto:
        if x.get("coMunicipioIbge") != mun["ibge6"]:
            continue
        linha = {
            "nuComp": str(x.get("nuComp")),
            "qtAcsAtivoAb": _int_br(x.get("qtAcsAtivoAb")),
            "qtAcsCoberturaAb": _int_br(x.get("qtAcsCoberturaAb")),
            "qtPopulacao": _int_br(x.get("qtPopulacao")),
            "pcCoberturaAcsAb": _float_api(x.get("pcCoberturaAcsAb")),
            "anoPopulacao": x.get("nuAnoPopulacaoConsiderada"),
            "origemPopulacao": x.get("tpOrigemBasePopulacao"),
        }
        c = linha["nuComp"]
        if c in por_comp:
            # Armadilha real: a API às vezes repete a mesma competência
            if por_comp[c] == linha:
                avisos.append(f"Competência {c} veio duplicada na resposta da API (registros idênticos) — mantido 1.")
            else:
                avisos.append(f"Competência {c} veio duplicada com VALORES DIFERENTES — mantido o 1º; investigar.")
            continue
        por_comp[c] = linha
    linhas = [por_comp[c] for c in sorted(por_comp)]
    return linhas, avisos


# ---------------------------------------------------------------------------
# 3. CNESWeb — quantitativo por CBO e competência
# ---------------------------------------------------------------------------
def _decodificar_cnes(dados: bytes) -> str:
    """CNESWeb responde em ISO-8859-1."""
    return dados.decode("iso-8859-1", errors="replace")


def _tokens(texto_html: str):
    """Texto visível da página em sequência de 'pedaços' (sem tags/scripts)."""
    t = re.sub(r"<script.*?</script>", " ", texto_html, flags=re.S | re.I)
    t = re.sub(r"<select.*?</select>", " ", t, flags=re.S | re.I)   # tira a lista de 2.000+ CBOs
    partes = re.split(r"<[^>]+>", t)
    return [html.unescape(p).strip() for p in partes if html.unescape(p).strip()]


def competencias_disponiveis(sessao, ev: Evidencias):
    """Lê o formulário do CNESWeb e devolve as competências oferecidas (AAAAMM, decrescente)."""
    codigo = "B0_cnes_formulario_competencias"
    try:
        r = sessao.get(URL_CNES_CBO, timeout=(20, 120))
        r.raise_for_status()
        reg, dados = ev.gravar(codigo, "CNESWeb/DATASUS", "Formulário de consulta (competências disponíveis)",
                               URL_CNES_CBO, "GET", {}, r, "html")
    except Exception as e:
        ev.falha(codigo, "CNESWeb/DATASUS", "Formulário de consulta", URL_CNES_CBO, "GET", {}, e)
        return []
    texto = _decodificar_cnes(dados)
    bloco = re.search(r'name="cboCompetencia".*?</select>', texto, flags=re.S | re.I)
    if not bloco:
        return []
    # A página EXIBE MMAAAA, mas o value é AAAAMM — usamos o value
    comps = re.findall(r'<option\s+value="?(\d{6})"?', bloco.group(0), flags=re.I)
    return sorted(set(comps), reverse=True)


def consultar_cnes_cbo(sessao, ev: Evidencias, mun, competencia, cbo):
    """
    POST no CNESWeb. Retorna dict {total, status, evidencia, aviso}.
    status: 'ok' (número lido), 'zero' (página declara inexistência), 'nao_apurado'.
    """
    params = {
        "cboEstado": mun["couf"], "municipios": mun["ibge6"], "cboCompetencia": competencia,
        "rdPesquisa": "cbo", "cboOcupacao": cbo, "btnPesquisa": "Pesquisar",
    }
    codigo = f"B_cnes_cbo{cbo}_{mun['ibge6']}_{competencia}"
    time.sleep(PAUSA_CNES_SEG)
    try:
        r = sessao.post(URL_CNES_CBO, data=params, timeout=(20, 120))
        r.raise_for_status()
        reg, dados = ev.gravar(codigo, "CNESWeb/DATASUS",
                               f"Profissionais CBO {cbo} — competência {competencia}",
                               URL_CNES_CBO, "POST", params, r, "html")
    except Exception as e:
        ev.falha(codigo, "CNESWeb/DATASUS", f"CBO {cbo} — {competencia}", URL_CNES_CBO, "POST", params, e)
        return {"total": None, "status": "nao_apurado", "evidencia": codigo, "aviso": f"falha de rede: {e}"}

    texto = _decodificar_cnes(dados)

    # Prova interna: a própria página devolvida mostra os parâmetros selecionados
    ecos = {
        "competencia": re.search(rf'<option\s+value="?{competencia}"?\s+selected', texto, flags=re.I),
        "municipio": re.search(rf'<option\s+value="?{mun["ibge6"]}"?\s+selected', texto, flags=re.I),
    }
    aviso = ""
    if not all(ecos.values()):
        faltam = [k for k, v in ecos.items() if not v]
        aviso = f"página não confirma {', '.join(faltam)} selecionado(s) — conferir manualmente"

    if re.search(r"N[ãa]o\s+Existe\(m\)\s+Profissional", texto, flags=re.I):
        return {"total": 0, "status": "zero", "evidencia": codigo, "aviso": aviso}

    tk = _tokens(texto)
    total = None
    for i, t in enumerate(tk):
        if t == cbo and i + 2 < len(tk):
            num = tk[i + 2].replace(".", "")
            if num.isdigit():
                total = int(num)
                break
    if total is None:
        return {"total": None, "status": "nao_apurado", "evidencia": codigo,
                "aviso": "resposta sem a linha do CBO (layout mudou?) — não apurado"}
    return {"total": total, "status": "ok", "evidencia": codigo, "aviso": aviso}


def baixar_nominal(sessao, ev: Evidencias, mun, cbo):
    """Relação nominal (drill-down). É posição da DATA DA CONSULTA — não filtra competência."""
    url = URL_CNES_NOMINAL.format(cbo=cbo, couf=mun["couf"], ibge6=mun["ibge6"])
    codigo = f"C_cnes_nominal_cbo{cbo}_{mun['ibge6']}"
    time.sleep(PAUSA_CNES_SEG)
    try:
        r = sessao.get(url, timeout=(20, 180))
        r.raise_for_status()
        reg, dados = ev.gravar(codigo, "CNESWeb/DATASUS", f"Relação nominal CBO {cbo} (posição atual)",
                               url, "GET", {}, r, "html")
    except Exception as e:
        ev.falha(codigo, "CNESWeb/DATASUS", f"Relação nominal CBO {cbo}", url, "GET", {}, e)
        return {"nomes": None, "status": "nao_apurado", "evidencia": codigo, "aviso": f"falha de rede: {e}"}

    texto = _decodificar_cnes(dados)
    texto = re.sub(r"<script.*?</script>", " ", texto, flags=re.S | re.I)
    nomes = []
    for linha in re.findall(r"<tr[^>]*>(.*?)</tr>", texto, flags=re.S | re.I):
        cel = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
               for c in re.findall(r"<td[^>]*>(.*?)</td>", linha, flags=re.S | re.I)]
        if len(cel) == 3 and cel[0] and cel[0].upper() != "NOME" and re.fullmatch(r"[A-Z]{2}", cel[2] or ""):
            nomes.append(cel[0])
    # Sem profissionais: a página traz só o cabeçalho "Nome | Município | UF" (ou "Não Existe...")
    tem_cabecalho = re.search(r">\s*Nome\s*<.*?>\s*Munic[íi]pio\s*<.*?>\s*UF\s*<", texto, flags=re.S | re.I)
    if not nomes and not (tem_cabecalho or re.search(r"N[ãa]o\s+Existe", texto, flags=re.I)):
        return {"nomes": None, "status": "nao_apurado", "evidencia": codigo,
                "aviso": "nenhum nome lido (layout mudou?) — não apurado"}
    return {"nomes": nomes, "status": "ok", "evidencia": codigo, "aviso": ""}
