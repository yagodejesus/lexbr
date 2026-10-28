"""Extração de citações a normas e dispositivos em texto livre (petições, pareceres, notícias, respostas de LLMs)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .util import URN_TIPOS, numero_lexml, numero_norma, ordinal, para_romano, romano, tipo_norma

__all__ = ["NormaRef", "Citacao", "extrair_citacoes", "APELIDOS"]

# Normas conhecidas pelo nome: regex → (tipo, número, ano, nome popular)
APELIDOS: list[tuple[str, tuple[str, str | None, int, str]]] = [
    (
        r"constitui[çc][ãa]o (?:da rep[úu]blica federativa do brasil|federal)(?: de 1988)?|\bCF(?:/88|/1988)?\b|\bCRFB(?:/88)?\b",
        ("Constituição", None, 1988, "Constituição Federal"),
    ),
    (r"c[óo]digo de defesa do consumidor|\bCDC\b", ("Lei", "8078", 1990, "Código de Defesa do Consumidor")),
    (r"c[óo]digo de processo civil|\bCPC(?:/2015|/15)?\b", ("Lei", "13105", 2015, "Código de Processo Civil")),
    (r"c[óo]digo de processo penal|\bCPP\b", ("Decreto-Lei", "3689", 1941, "Código de Processo Penal")),
    (r"c[óo]digo civil|\bCC(?:/2002|/02)\b", ("Lei", "10406", 2002, "Código Civil")),
    (r"c[óo]digo penal", ("Decreto-Lei", "2848", 1940, "Código Penal")),
    (r"consolida[çc][ãa]o das leis do trabalho|\bCLT\b", ("Decreto-Lei", "5452", 1943, "CLT")),
    (r"c[óo]digo tribut[áa]rio nacional|\bCTN\b", ("Lei", "5172", 1966, "Código Tributário Nacional")),
    (r"c[óo]digo de tr[âa]nsito brasileiro|\bCTB\b", ("Lei", "9503", 1997, "Código de Trânsito Brasileiro")),
    (r"estatuto da crian[çc]a e do adolescente|\bECA\b", ("Lei", "8069", 1990, "Estatuto da Criança e do Adolescente")),
    (r"lei geral de prote[çc][ãa]o de dados(?: pessoais)?|\bLGPD\b", ("Lei", "13709", 2018, "LGPD")),
    (r"marco civil da internet", ("Lei", "12965", 2014, "Marco Civil da Internet")),
    (r"lei de acesso [àa] informa[çc][ãa]o|\bLAI\b", ("Lei", "12527", 2011, "Lei de Acesso à Informação")),
    (r"lei maria da penha", ("Lei", "11340", 2006, "Lei Maria da Penha")),
    (r"nova lei de licita[çc][õo]es", ("Lei", "14133", 2021, "Lei de Licitações e Contratos")),
    (r"lei de responsabilidade fiscal|\bLRF\b", ("Lei Complementar", "101", 2000, "Lei de Responsabilidade Fiscal")),
]
_RE_APELIDO = [(re.compile(p, re.I), v) for p, v in APELIDOS]
_RE_NORMA = re.compile(
    r"\b(Lei Complementar|Lei|Decreto-Lei|Decreto|Medida Provis[óo]ria|Emenda Constitucional|LC|MP|EC|DL)\s*"
    r"(?:n[º°o.]*\s*)?(\d{1,3}(?:\.\d{3})+|\d{1,6})(?!\d)"
    r"(?:\s*/\s*(\d{4}|\d{2})(?!\d)|\s*,\s*de\s+(?:\d{1,2}[º°]?\s+de\s+[a-zç]+\s+de\s+)?(\d{4}))?",
    re.I,
)
_NUM = r"\d+(?:\.\d{3})*\s*(?:[º°o](?![a-zà-ú]))?(?:-[A-Z](?![A-Za-zà-ú]))?"
_QUAL = (
    r"(?:§\s*\d+\s*(?:[º°o](?![a-zà-ú]))?|par[áa]grafo\s+[úu]nico|(?:inciso\s+)?(?-i:[IVXLCDM]+)\b"
    r"|al[íi]nea\s+[\"“']?[a-z][\"”']?|[a-z]\)|item\s+\d+)"
)
_RE_ARTIGOS = re.compile(
    rf"\b(?:arts?\.|artigos?)\s*(?P<lista>{_NUM}(?:\s*(?:,|\be\b|\ba\b)\s*{_NUM})*)(?P<quals>(?:\s*,\s*{_QUAL})*)", re.I
)
_RE_QUAL_ANTES = re.compile(
    r"(?P<quals>(?:(?:§\s*\d+\s*(?:[º°o](?![a-zà-ú]))?|par[áa]grafo\s+[úu]nico|inciso\s+(?-i:[IVXLCDM]+)"
    r"|al[íi]nea\s+[\"“']?[a-z][\"”']?|item\s+\d+)\s*,?\s+d[oa]\s+)+)art(?:igo)?\.?\s*(?P<num>" + _NUM + ")",
    re.I,
)
_RE_LIGACAO = re.compile(r"\s*,?\s*(?:d[aoe]s?|desta|deste|na|no|nas|nos)\s+(?:referid[ao]\s+|mesm[ao]\s+)?", re.I)


@dataclass(frozen=True)
class NormaRef:
    tipo: str
    numero: str | None
    ano: int | None
    apelido: str | None = None

    @property
    def rotulo(self) -> str:
        if self.tipo == "Constituição":
            return "Constituição Federal"
        num = f" nº {numero_norma(self.numero)}" if self.numero else ""
        return f"{self.tipo}{num}" + (f"/{self.ano}" if self.ano else "")

    @property
    def urn(self) -> str | None:
        if self.tipo == "Constituição":
            return "urn:lex:br:federal:constituicao:1988-10-05;1988"
        if self.tipo not in URN_TIPOS or not self.numero or not self.ano:
            return None
        return f"urn:lex:br:federal:{URN_TIPOS[self.tipo]}:{self.ano};{self.numero}"


@dataclass(frozen=True)
class Citacao:
    trecho: str
    inicio: int
    fim: int
    norma: NormaRef | None = None
    artigo: str | None = None
    paragrafo: str | None = None
    inciso: str | None = None
    alinea: str | None = None
    item: str | None = None
    relativa: bool = False  # "desta Lei"

    @property
    def dispositivo(self) -> str:
        partes = []
        if self.artigo:
            partes.append(f"art. {ordinal(self.artigo)}")
        if self.paragrafo:
            partes.append("parágrafo único" if self.paragrafo == "unico" else f"§ {ordinal(self.paragrafo)}")
        if self.inciso:
            partes.append(para_romano(int(self.inciso.split("-")[0])))
        if self.alinea:
            partes.append(chr(96 + int(self.alinea)))
        if self.item:
            partes.append(self.item)
        return ", ".join(partes)

    @property
    def id_lexml(self) -> str | None:
        if not self.artigo:
            return None
        partes = [f"art{numero_lexml(self.artigo)}"]
        if self.paragrafo:
            partes.append("par1u" if self.paragrafo == "unico" else f"par{self.paragrafo}")
        if self.inciso:
            partes.append(f"inc{self.inciso}" if self.paragrafo else f"cpt_inc{self.inciso}")
        if self.alinea:
            partes.append(f"ali{self.alinea}")
        if self.item:
            partes.append(f"ite{self.item}")
        return "_".join(partes)

    @property
    def urn(self) -> str | None:
        if not self.norma or not self.norma.urn:
            return None
        return self.norma.urn + (f"!{self.id_lexml}" if self.id_lexml else "")

    @property
    def normalizada(self) -> str:
        """``"Lei nº 13.709/2018 (LGPD), art. 7º, IX"``."""
        partes = []
        if self.norma:
            apelido = f" ({self.norma.apelido})" if self.norma.apelido and self.norma.tipo != "Constituição" else ""
            partes.append(self.norma.rotulo + apelido)
        elif self.relativa:
            partes.append("(esta norma)")
        if self.dispositivo:
            partes.append(self.dispositivo)
        return ", ".join(partes)


def _ano(texto: str | None) -> int | None:
    if not texto:
        return None
    a = int(texto)
    if a < 100:
        a += 2000 if a <= date.today().year % 100 else 1900
    return a


def _normas(texto: str) -> list[tuple[int, int, NormaRef]]:
    achadas = []
    for m in _RE_NORMA.finditer(texto):
        tipo = tipo_norma(m.group(1))
        if tipo:
            achadas.append((m.start(), m.end(), NormaRef(tipo, m.group(2).replace(".", ""), _ano(m.group(3) or m.group(4)))))
    for regex, (tipo, numero, ano, apelido) in _RE_APELIDO:
        for m in regex.finditer(texto):
            if not any(s <= m.start() < e for s, e, _ in achadas):
                achadas.append((m.start(), m.end(), NormaRef(tipo, numero, ano, apelido)))
    return sorted(achadas, key=lambda x: x[0])


def _numero_artigo(texto: str) -> str:
    t = re.sub(r"[\sº°o.]", "", texto.strip()).upper()
    return t


def _qualificadores(texto: str) -> dict[str, str]:
    q: dict[str, str] = {}
    for m in re.finditer(r"§\s*(\d+)|par[áa]grafo\s+([úu]nico)", texto, re.I):
        q["paragrafo"] = m.group(1) or "unico"
    for m in re.finditer(r"(?:inciso\s+|(?<=,)\s*|^\s*)((?-i:[IVXLCDM]+))\b", texto, re.I):
        q["inciso"] = str(romano(m.group(1)))
    for m in re.finditer(r"al[íi]nea\s+[\"“']?([a-z])|(?<![a-z])([a-z])\)", texto, re.I):
        q["alinea"] = str(ord((m.group(1) or m.group(2)).lower()) - 96)
    for m in re.finditer(r"item\s+(\d+)", texto, re.I):
        q["item"] = m.group(1)
    return q


def _norma_depois(texto: str, fim: int, normas) -> tuple[NormaRef | None, bool, int]:
    m = _RE_LIGACAO.match(texto, fim)
    if not m:
        return None, False, fim
    pos = m.end()
    if re.match(
        r"(?:presente|desta|deste)?\s*(?:lei|decreto|c[óo]digo|norma|medida|resolu)", texto[pos : pos + 20], re.I
    ) and re.search(r"\b(?:desta|deste|presente)\s*$", texto[fim:pos], re.I):
        return None, True, pos
    for s, e, ref in normas:
        if s == pos:
            return ref, False, e
    return None, False, fim


def extrair_citacoes(texto: str) -> list[Citacao]:
    """Encontra citações como ``"art. 7º, IX, da Lei nº 13.709/2018"``, ``"§ 2º do art. 3º da LGPD"``,
    ``"arts. 186 e 927 do Código Civil"`` e ``"CF, art. 5º, LXXIX"``.

    Cada artigo vira uma :class:`Citacao` com a norma (quando identificada), os números
    normalizados, o identificador LexML e a URN.
    """
    normas = _normas(texto)
    citacoes: list[Citacao] = []
    ocupado: list[tuple[int, int]] = []

    for m in _RE_QUAL_ANTES.finditer(texto):
        q = _qualificadores(m.group("quals"))
        norma, relativa, fim = _norma_depois(texto, m.end(), normas)
        citacoes.append(
            Citacao(
                texto[m.start() : fim],
                m.start(),
                fim,
                norma,
                _numero_artigo(m.group("num")),
                q.get("paragrafo"),
                q.get("inciso"),
                q.get("alinea"),
                q.get("item"),
                relativa,
            )
        )
        ocupado.append((m.start(), fim))

    for m in _RE_ARTIGOS.finditer(texto):
        if any(s <= m.start() < e for s, e in ocupado):
            continue
        q = _qualificadores(m.group("quals"))
        norma, relativa, fim = _norma_depois(texto, m.end(), normas)
        if norma is None and not relativa:  # "CF, art. 5º" — norma antes do artigo
            antes = [
                (s, e, r) for s, e, r in normas if 0 <= m.start() - e <= 3 and texto[e : m.start()].strip() in (",", "")
            ]
            if antes:
                norma = antes[-1][2]
                ocupado.append((antes[-1][0], antes[-1][1]))
        numeros = re.findall(_NUM, m.group("lista"))
        intervalo = re.search(r"\ba\b", m.group("lista"))
        artigos = [_numero_artigo(n) for n in numeros]
        if intervalo and len(artigos) == 2 and artigos[0].isdigit() and artigos[1].isdigit():
            ini, fim_int = int(artigos[0]), int(artigos[1])
            if 0 < fim_int - ini <= 50:
                artigos = [str(i) for i in range(ini, fim_int + 1)]
        for i, art in enumerate(artigos):
            extra = q if i == len(artigos) - 1 or len(artigos) == 1 else {}
            citacoes.append(
                Citacao(
                    texto[m.start() : fim],
                    m.start(),
                    fim,
                    norma,
                    art,
                    extra.get("paragrafo"),
                    extra.get("inciso"),
                    extra.get("alinea"),
                    extra.get("item"),
                    relativa,
                )
            )
        ocupado.append((m.start(), fim))

    for s, e, ref in normas:  # normas citadas sem artigo
        if not any(a <= s < b for a, b in ocupado):
            citacoes.append(Citacao(texto[s:e], s, e, ref))
    return sorted(citacoes, key=lambda c: (c.inicio, c.artigo or ""))
