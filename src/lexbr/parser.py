"""Leitura do texto de normas brasileiras (como copiado do Planalto, do LexML ou de PDFs)."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .modelos import ESTRUTURAIS, Dispositivo, Norma
from .util import MESES, romano, sem_acento, tipo_norma

__all__ = ["ler_norma", "ler_arquivo"]

_D = r"[-–—]"
RE_EPIGRAFE = re.compile(
    r"^(LEI COMPLEMENTAR|LEI|DECRETO-LEI|DECRETO|MEDIDA PROVIS[ÓO]RIA|EMENDA CONSTITUCIONAL|RESOLU[ÇC][ÃA]O|"
    r"PORTARIA|INSTRU[ÇC][ÃA]O NORMATIVA)\s+N[º°o.]*\s*([\d.]+)\s*,?\s+DE\s+(\d{1,2})[º°o]?\s+DE\s+([A-ZÇ]+)\s+DE\s+(\d{4})",
    re.I,
)
RE_ESTRUTURA = re.compile(
    r"^(PARTE|LIVRO|T[ÍI]TULO|CAP[ÍI]TULO|SUBSE[ÇC][ÃA]O|SE[ÇC][ÃA]O)\s+([IVXLCDM]+|[ÚU]NIC[OA]|\d+)(?:-([A-Z]))?\b\.?"
    rf"\s*(?:{_D}\s*)?(.*)$",
    re.I,
)
RE_ARTIGO = re.compile(
    rf"^Art\.?\s*(\d+(?:\.\d{{3}})*)\s*(?:[º°o](?![a-zà-ú]))?\s*(?:-([A-Z]{{1,2}})(?![A-Za-zà-ú]))?\s*[.:]?\s*(?:{_D}\s*)?(.*)$"
)
RE_PARAGRAFO = re.compile(
    rf"^(?:§\s*(\d+)\s*(?:[º°o](?![a-zà-ú]))?(?:-([A-Z])(?![A-Za-zà-ú]))?|(Par[áa]grafo\s+[úu]nico))\s*[.:]?\s*(?:{_D}\s*)?(.*)$",
    re.I,
)
RE_INCISO = re.compile(rf"^([IVXLCDM]+)(?:-([A-Z]))?\s*{_D}\s*(.*)$")
RE_ALINEA = re.compile(r"^([a-z])(?:-([A-Z]))?\)\s*(.*)$")
RE_ITEM = re.compile(r"^(\d{1,2})[.)]\s+(.*)$")
RE_FECHO = re.compile(r"^Bras[íi]lia\s*,\s*\d", re.I)
RE_PREAMBULO = re.compile(
    r"^(?:O|A)\s+(?:PRESIDENT[EA]|VICE-PRESIDENTE|CONGRESSO|MESA)|^Fa[çc]o saber|^O PRESIDENTE|decreta\s*:|promulga",
    re.I,
)
RE_ANOTACAO = re.compile(
    r"\((?:Inclu[íi]d[oa]|Reda[çc][ãa]o dada|Revogad[oa]|Vide|Vig[êe]ncia|Regulamento|Regulamenta[çc][ãa]o|"
    r"Promulga[çc][ãa]o|Produ[çc][ãa]o de efeitos?|Renumerad[oa]|Acrescid[oa]|Vetad[oa]|Inclus[ãa]o|Express[ãa]o|"
    r"Suspens[ãa]o|Declara[çc][ãa]o|Convers[ãa]o|Vig[êe]ncia encerrada)[^()]*(?:\([^()]*\)[^()]*)*\)",
    re.I,
)


def _anotacoes(texto: str) -> tuple[str, list[str]]:
    notas = [m.group() for m in RE_ANOTACAO.finditer(texto)]
    limpo = RE_ANOTACAO.sub("", texto)
    if re.fullmatch(r"\s*\(?\s*VETAD[OA]\s*\)?\s*\.?\s*", limpo, re.I):
        notas.append("(VETADO)")
        limpo = ""
    if notas and not limpo.strip(" .;:"):
        limpo = ""
    return " ".join(limpo.split()), notas


def _sufixo(numero: str, letra: str | None) -> str:
    return f"{numero}-{letra.upper()}" if letra else numero


def _tipo_estrutura(palavra: str) -> str:
    p = sem_acento(palavra).lower()
    return {
        "parte": "parte",
        "livro": "livro",
        "titulo": "titulo",
        "capitulo": "capitulo",
        "secao": "secao",
        "subsecao": "subsecao",
    }[p]


def ler_norma(texto: str, apelido: str | None = None) -> Norma:
    """Transforma o texto de uma lei, decreto, MP etc. numa árvore de dispositivos."""
    norma = Norma(apelido=apelido)
    pilha: list[Dispositivo] = []
    ultimo: Dispositivo | None = None
    estado = "inicio"  # inicio → ementa → preambulo → corpo → fecho
    fecho: list[str] = []

    def anexar(d: Dispositivo) -> None:
        nonlocal ultimo
        while pilha and pilha[-1].nivel >= d.nivel:
            pilha.pop()
        if pilha:
            d.pai = pilha[-1]
            pilha[-1].filhos.append(d)
        else:
            norma.filhos.append(d)
        pilha.append(d)
        ultimo = d

    for n, bruta in enumerate(texto.splitlines(), 1):
        linha = " ".join(bruta.replace("\u00a0", " ").split())
        if not linha:
            continue
        if estado == "fecho":
            fecho.append(linha)
            continue
        if estado == "inicio":
            m = RE_EPIGRAFE.match(linha)
            if m:
                norma.epigrafe = linha
                norma.tipo = tipo_norma(m.group(1))
                norma.numero = m.group(2).replace(".", "")
                mes = MESES.get(sem_acento(m.group(4)).lower())
                if mes:
                    norma.data = date(int(m.group(5)), mes, int(m.group(3)))
                estado = "ementa"
                continue
        if RE_FECHO.match(linha) and estado in ("corpo", "preambulo"):
            estado = "fecho"
            fecho.append(linha)
            continue

        m = RE_ESTRUTURA.match(linha)
        if m and (m.group(1).isupper() or estado == "corpo"):
            estado = "corpo"
            numero = m.group(2)
            num = str(romano(numero)) if re.fullmatch(r"[IVXLCDM]+", numero, re.I) else sem_acento(numero).lower()
            titulo, notas = _anotacoes(m.group(4))
            anexar(
                Dispositivo(_tipo_estrutura(m.group(1)), _sufixo(num, m.group(3)), titulo=titulo, anotacoes=notas, linha=n)
            )
            continue
        m = RE_ARTIGO.match(linha)
        if m:
            estado = "corpo"
            texto_art, notas = _anotacoes(m.group(3))
            anexar(
                Dispositivo("artigo", _sufixo(m.group(1).replace(".", ""), m.group(2)), texto_art, anotacoes=notas, linha=n)
            )
            continue
        if estado == "corpo":
            m = RE_PARAGRAFO.match(linha)
            if m:
                numero = "unico" if m.group(3) else _sufixo(m.group(1), m.group(2))
                t, notas = _anotacoes(m.group(4))
                anexar(Dispositivo("paragrafo", numero, t, anotacoes=notas, linha=n))
                continue
            m = RE_INCISO.match(linha)
            if m and pilha and any(p.tipo in ("artigo", "paragrafo") for p in pilha):
                t, notas = _anotacoes(m.group(3))
                anexar(Dispositivo("inciso", _sufixo(str(romano(m.group(1))), m.group(2)), t, anotacoes=notas, linha=n))
                continue
            m = RE_ALINEA.match(linha)
            if m and pilha and any(p.tipo == "inciso" for p in pilha):
                t, notas = _anotacoes(m.group(3))
                anexar(Dispositivo("alinea", _sufixo(str(ord(m.group(1)) - 96), m.group(2)), t, anotacoes=notas, linha=n))
                continue
            m = RE_ITEM.match(linha)
            if m and pilha and any(p.tipo == "alinea" for p in pilha):
                t, notas = _anotacoes(m.group(2))
                anexar(Dispositivo("item", m.group(1), t, anotacoes=notas, linha=n))
                continue
            # continuação: nome de capítulo na linha seguinte ou texto quebrado
            if ultimo is not None:
                t, notas = _anotacoes(linha)
                if ultimo.tipo in ESTRUTURAIS and not ultimo.titulo:
                    ultimo.titulo = t
                else:
                    ultimo.texto = f"{ultimo.texto} {t}".strip()
                ultimo.anotacoes.extend(notas)
            continue
        if estado == "ementa":
            if RE_PREAMBULO.search(linha):
                norma.preambulo = linha
                estado = "preambulo"
            else:
                norma.ementa = f"{norma.ementa} {linha}".strip()
            continue
        if estado in ("preambulo", "inicio"):
            norma.preambulo = f"{norma.preambulo} {linha}".strip()
    norma.fecho = "\n".join(fecho)
    return norma


def ler_arquivo(caminho: str | Path, apelido: str | None = None) -> Norma:
    bruto = Path(caminho).read_bytes()
    try:
        texto = bruto.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = bruto.decode("cp1252")
    if "<html" in texto[:2000].lower():
        texto = _html_para_texto(texto)
    return ler_norma(texto, apelido)


def _html_para_texto(html: str) -> str:
    """Converte o HTML das páginas de legislação em texto, linha por parágrafo (riscados são removidos)."""
    import html as h

    t = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", html)
    t = re.sub(r"(?is)<(strike|s|del)\b.*?</\1>", " ", t)  # texto revogado aparece riscado
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</h\d>|</li>|</tr>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return h.unescape(t)
