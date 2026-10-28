"""Numerais romanos, ordinais e nomes de tipos de norma."""

from __future__ import annotations

import re
import unicodedata

_ROMANOS = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
MESES = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
TIPOS = {
    "lei": "Lei",
    "lei complementar": "Lei Complementar",
    "decreto": "Decreto",
    "decreto-lei": "Decreto-Lei",
    "medida provisoria": "Medida Provisória",
    "emenda constitucional": "Emenda Constitucional",
    "resolucao": "Resolução",
    "portaria": "Portaria",
    "instrucao normativa": "Instrução Normativa",
    "lc": "Lei Complementar",
    "mp": "Medida Provisória",
    "ec": "Emenda Constitucional",
    "dl": "Decreto-Lei",
}
URN_TIPOS = {
    "Lei": "lei",
    "Lei Complementar": "lei.complementar",
    "Decreto": "decreto",
    "Decreto-Lei": "decreto.lei",
    "Medida Provisória": "medida.provisoria",
    "Emenda Constitucional": "emenda.constitucional",
    "Constituição": "constituicao",
}


def sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def romano(s: str) -> int:
    total, anterior = 0, 0
    for c in reversed(s.upper()):
        v = _ROMANOS[c]
        total = total - v if v < anterior else total + v
        anterior = max(anterior, v)
    return total


def para_romano(n: int) -> str:
    pares = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]
    out = ""
    for v, r in pares:
        while n >= v:
            out, n = out + r, n - v
    return out


def ordinal(numero: str) -> str:
    """``"7"`` → ``"7º"``; ``"10"`` → ``"10"`` (a partir do 10, sem o símbolo, como na técnica legislativa)."""
    base, _, sufixo = numero.partition("-")
    rotulo = f"{base}º" if base.isdigit() and int(base) < 10 else base
    return f"{rotulo}-{sufixo}" if sufixo else rotulo


def numero_lexml(numero: str) -> str:
    """``"3-A"`` → ``"3-1"`` (letras viram números, como no LexML)."""
    base, _, sufixo = numero.partition("-")
    return f"{base}-{'-'.join(str(ord(c) - 64) for c in sufixo.upper())}" if sufixo else base


def tipo_norma(texto: str) -> str | None:
    return TIPOS.get(re.sub(r"\s+", " ", sem_acento(texto).lower()).strip())


def numero_norma(texto: str) -> str:
    """``"13709"`` → ``"13.709"``."""
    d = texto.replace(".", "")
    if not d.isdigit():
        return texto
    return f"{int(d):,}".replace(",", ".")
