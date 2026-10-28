"""Estrutura de uma norma: :class:`Norma`, :class:`Dispositivo` e :class:`Trecho` (chunk para RAG)."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .util import URN_TIPOS, numero_lexml, numero_norma, ordinal, para_romano

__all__ = ["Dispositivo", "Norma", "Trecho", "NIVEIS", "ESTRUTURAIS"]

NIVEIS = {
    "parte": 0,
    "livro": 1,
    "titulo": 2,
    "capitulo": 3,
    "secao": 4,
    "subsecao": 5,
    "artigo": 6,
    "paragrafo": 7,
    "inciso": 8,
    "alinea": 9,
    "item": 10,
}
ESTRUTURAIS = ("parte", "livro", "titulo", "capitulo", "secao", "subsecao")
_NOMES = {
    "parte": "Parte",
    "livro": "Livro",
    "titulo": "Título",
    "capitulo": "Capítulo",
    "secao": "Seção",
    "subsecao": "Subseção",
}
_LEXML = {
    "parte": "prt",
    "livro": "liv",
    "titulo": "tit",
    "capitulo": "cap",
    "secao": "sec",
    "subsecao": "sub",
    "artigo": "art",
    "paragrafo": "par",
    "inciso": "inc",
    "alinea": "ali",
    "item": "ite",
}


@dataclass(eq=False)
class Dispositivo:
    tipo: str
    numero: str  # "7", "3-A", "unico", "9" (inciso IX), "2" (alínea b)
    texto: str = ""
    titulo: str = ""  # nome de capítulos, seções etc.
    anotacoes: list[str] = field(default_factory=list)
    filhos: list[Dispositivo] = field(default_factory=list)
    linha: int = 0
    pai: Dispositivo | None = field(default=None, repr=False)

    @property
    def nivel(self) -> int:
        return NIVEIS[self.tipo]

    @property
    def rotulo(self) -> str:
        if self.tipo == "artigo":
            return f"Art. {ordinal(self.numero)}"
        if self.tipo == "paragrafo":
            return "Parágrafo único" if self.numero == "unico" else f"§ {ordinal(self.numero)}"
        if self.tipo == "inciso":
            return para_romano(int(self.numero))
        if self.tipo == "alinea":
            return chr(96 + int(self.numero)) + ")"
        if self.tipo == "item":
            return f"{self.numero}."
        return f"{_NOMES[self.tipo]} {para_romano(int(self.numero)) if self.numero.isdigit() else self.numero}"

    @property
    def revogado(self) -> bool:
        return any("revogad" in a.lower() for a in self.anotacoes) and not self.texto.strip(" .")

    @property
    def vetado(self) -> bool:
        return any("vetad" in a.lower() for a in self.anotacoes) and not self.texto.strip(" .")

    def caminho(self) -> list[Dispositivo]:
        """Ancestrais (do mais alto ao próprio dispositivo)."""
        out, d = [], self
        while d is not None:
            out.append(d)
            d = d.pai
        return out[::-1]

    @property
    def artigo(self) -> Dispositivo | None:
        return next((d for d in self.caminho() if d.tipo == "artigo"), None)

    @property
    def citacao(self) -> str:
        """``"art. 7º, § 1º, II, a"``."""
        partes = []
        for d in self.caminho():
            if d.tipo == "artigo":
                partes.append(f"art. {ordinal(d.numero)}")
            elif d.tipo == "paragrafo":
                partes.append("parágrafo único" if d.numero == "unico" else f"§ {ordinal(d.numero)}")
            elif d.tipo in ("inciso", "alinea", "item"):
                partes.append(d.rotulo.rstrip(").") if d.tipo != "inciso" else d.rotulo)
        return ", ".join(partes)

    @property
    def id_lexml(self) -> str:
        """Identificador no estilo LexML: ``art7_cpt_inc9``, ``art3_par1``, ``art2_par1u``."""
        partes = []
        for d in self.caminho():
            if d.tipo in ESTRUTURAIS:
                continue
            if d.tipo == "paragrafo":
                partes.append("par1u" if d.numero == "unico" else f"par{d.numero}")
            elif d.tipo == "inciso" and d.pai is not None and d.pai.tipo == "artigo":
                partes.append(f"cpt_inc{d.numero}")
            else:
                partes.append(f"{_LEXML[d.tipo]}{numero_lexml(d.numero)}")
        return "_".join(partes)

    def iterar(self) -> Iterator[Dispositivo]:
        yield self
        for f in self.filhos:
            yield from f.iterar()

    def linha_texto(self) -> str:
        nota = f" {' '.join(self.anotacoes)}" if self.anotacoes else ""
        if self.tipo in ESTRUTURAIS:
            return f"{self.rotulo} — {self.titulo}".rstrip(" —")
        sep = " - " if self.tipo == "inciso" else " "
        texto = self.texto or ""
        return f"{self.rotulo}{sep}{texto}{nota}".strip()

    def texto_completo(self, incluir_revogados: bool = False) -> str:
        linhas = []
        for d in self.iterar():
            if not incluir_revogados and (d.revogado or d.vetado) and d is not self:
                continue
            linhas.append(d.linha_texto())
        return "\n".join(linhas)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"tipo": self.tipo, "numero": self.numero, "rotulo": self.rotulo}
        if self.titulo:
            d["titulo"] = self.titulo
        if self.texto:
            d["texto"] = self.texto
        if self.tipo not in ESTRUTURAIS:
            d["citacao"] = self.citacao
            d["id"] = self.id_lexml
        if self.anotacoes:
            d["anotacoes"] = self.anotacoes
        if self.revogado:
            d["revogado"] = True
        if self.vetado:
            d["vetado"] = True
        if self.filhos:
            d["filhos"] = [f.to_dict() for f in self.filhos]
        return d


@dataclass
class Trecho:
    """Pedaço pronto para indexar em RAG: texto com contexto e metadados."""

    id: str
    texto: str
    citacao: str
    contexto: str
    urn: str | None
    metadados: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "texto": self.texto,
            "citacao": self.citacao,
            "contexto": self.contexto,
            "urn": self.urn,
            "metadados": self.metadados,
        }


@dataclass
class Norma:
    tipo: str | None = None
    numero: str | None = None
    data: date | None = None
    epigrafe: str = ""
    ementa: str = ""
    preambulo: str = ""
    fecho: str = ""
    filhos: list[Dispositivo] = field(default_factory=list)
    apelido: str | None = None

    @property
    def ano(self) -> int | None:
        return self.data.year if self.data else None

    @property
    def nome(self) -> str:
        if not self.tipo:
            return "Norma"
        num = f" nº {numero_norma(self.numero)}" if self.numero else ""
        ano = f"/{self.ano}" if self.ano else ""
        return f"{self.tipo}{num}{ano}"

    @property
    def urn(self) -> str | None:
        if not (self.tipo in URN_TIPOS and self.numero and self.data):
            return None
        return f"urn:lex:br:federal:{URN_TIPOS[self.tipo]}:{self.data.isoformat()};{self.numero.replace('.', '')}"

    # ------------------------------------------------------------------ navegação
    def dispositivos(self) -> Iterator[Dispositivo]:
        for f in self.filhos:
            yield from f.iterar()

    def artigos(self) -> list[Dispositivo]:
        return [d for d in self.dispositivos() if d.tipo == "artigo"]

    def artigo(self, numero: str | int) -> Dispositivo | None:
        alvo = str(numero).replace("º", "").replace("°", "").upper().replace(" ", "")
        return next((a for a in self.artigos() if a.numero.upper() == alvo), None)

    def buscar(self, citacao: str) -> Dispositivo | None:
        """``norma.buscar("art. 2º, II, b, 1")``, ``"art. 3, § 1º"`` ou ``"art. 2, parágrafo único"``."""
        from .util import romano

        partes = [p.strip() for p in re.split(r",|\s+d[oa]\s+(?=art)", citacao) if p.strip()]
        if not partes:
            return None
        m = re.match(r"(?:art(?:igo)?\.?\s*)?(\d+)\s*[º°o]?\s*(?:-\s*([A-Za-z]))?$", partes[0], re.I)
        if not m:
            return None
        d = self.artigo(f"{m.group(1)}-{m.group(2).upper()}" if m.group(2) else m.group(1))
        for parte in partes[1:]:
            if d is None:
                return None
            p = parte.strip().rstrip(")").strip()
            if re.match(r"(?:§|par[áa]grafo)", p, re.I):
                n = "unico" if re.search(r"[úu]nico", p, re.I) else re.sub(r"\D", "", p)
                alvo = ("paragrafo", n)
            elif re.fullmatch(r"(?:inciso\s+)?[IVXLCDM]+", p):
                alvo = ("inciso", str(romano(p.split()[-1])))
            elif re.fullmatch(r"(?:al[íi]nea\s+)?[\"“']?[a-z][\"”']?", p, re.I):
                alvo = ("alinea", str(ord(p.strip("\"“”'")[-1].lower()) - 96))
            elif re.fullmatch(r"(?:item\s+)?\d+", p, re.I):
                alvo = ("item", re.sub(r"\D", "", p))
            else:
                return None
            d = next((f for f in d.filhos if (f.tipo, f.numero) == alvo), None)
        return d

    # ------------------------------------------------------------------- RAG
    def _contexto(self, artigo: Dispositivo) -> str:
        estrutura = [f"{d.rotulo} ({d.titulo})" if d.titulo else d.rotulo for d in artigo.caminho()[:-1]]
        return " › ".join([self.nome + (f" ({self.apelido})" if self.apelido else ""), *estrutura])

    def trechos(self, max_caracteres: int = 1500, incluir_revogados: bool = False) -> list[Trecho]:
        """Divide a norma em trechos para RAG: um por artigo, ou mais se o artigo for longo.

        Cada trecho traz a hierarquia (capítulo, seção…) e, quando o artigo é dividido,
        repete o caput para não perder o sentido dos incisos.
        """
        trechos: list[Trecho] = []
        for art in self.artigos():
            if not incluir_revogados and (art.revogado or art.vetado):
                continue
            contexto = self._contexto(art)
            caput = art.linha_texto()
            blocos: list[list[Dispositivo]] = [[]]
            tamanho = len(caput)
            for filho in art.filhos:
                if not incluir_revogados and (filho.revogado or filho.vetado):
                    continue
                t = len(filho.texto_completo(incluir_revogados)) + 1
                if blocos[-1] and tamanho + t > max_caracteres:
                    blocos.append([])
                    tamanho = len(caput)
                blocos[-1].append(filho)
                tamanho += t
            for i, bloco in enumerate(blocos):
                corpo = "\n".join(f.texto_completo(incluir_revogados) for f in bloco)
                texto = f"{contexto}\n{caput}" + (f"\n{corpo}" if corpo else "")
                sufixo = f"#{i + 1}" if len(blocos) > 1 else ""
                cit = f"{self.nome}, {art.citacao}"
                trechos.append(
                    Trecho(
                        id=(self.urn + "!" if self.urn else "") + art.id_lexml + sufixo,
                        texto=texto,
                        citacao=cit,
                        contexto=contexto,
                        urn=f"{self.urn}!{art.id_lexml}" if self.urn else None,
                        metadados={
                            "norma": self.nome,
                            "tipo": self.tipo,
                            "numero": self.numero,
                            "ano": self.ano,
                            "artigo": art.numero,
                            "parte": i + 1,
                            "partes": len(blocos),
                            "estrutura": [d.rotulo for d in art.caminho()[:-1]],
                            "anotacoes": art.anotacoes,
                        },
                    )
                )
        return trechos

    # ---------------------------------------------------------------- exportação
    def to_dict(self) -> dict[str, Any]:
        return {
            "tipo": self.tipo,
            "numero": self.numero,
            "data": self.data.isoformat() if self.data else None,
            "nome": self.nome,
            "urn": self.urn,
            "epigrafe": self.epigrafe,
            "ementa": self.ementa,
            "dispositivos": [f.to_dict() for f in self.filhos],
        }

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def to_markdown(self) -> str:
        linhas = [f"# {self.epigrafe or self.nome}"]
        if self.ementa:
            linhas += ["", f"*{self.ementa}*"]
        for d in self.dispositivos():
            texto = d.linha_texto()
            if d.revogado or d.vetado:
                texto = f"~~{texto}~~"
            if d.tipo in ESTRUTURAIS:
                linhas += ["", "#" * min(6, d.nivel + 2) + f" {d.rotulo}" + (f" — {d.titulo}" if d.titulo else "")]
            elif d.tipo == "artigo":
                linhas += ["", f"**{d.rotulo}**{texto[len(d.rotulo) :]}"]
            else:
                recuo = "  " * (d.nivel - NIVEIS["paragrafo"])
                linhas.append(f"{recuo}- {texto}")
        return "\n".join(linhas).strip() + "\n"

    def __repr__(self) -> str:
        return f"<Norma {self.nome}: {len(self.artigos())} artigos>"
