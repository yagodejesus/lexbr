"""Linha de comando: ``lexbr lei.txt``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .citacoes import extrair_citacoes
from .parser import ler_arquivo


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lexbr", description="Estrutura leis brasileiras e extrai citações, prontas para RAG.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="comando", required=True)

    e = sub.add_parser("estrutura", help="mostra a árvore de uma norma (texto, .html ou .txt)")
    e.add_argument("arquivo")
    e.add_argument("--formato", choices=("arvore", "json", "markdown"), default="arvore")
    e.add_argument("--apelido", help="nome popular, ex.: LGPD")

    t = sub.add_parser("trechos", help="gera trechos (chunks) em JSONL para RAG")
    t.add_argument("arquivo")
    t.add_argument("-o", "--saida", help="arquivo .jsonl (padrão: stdout)")
    t.add_argument("--max", type=int, default=1500, help="máximo de caracteres por trecho")
    t.add_argument("--revogados", action="store_true", help="inclui dispositivos revogados/vetados")
    t.add_argument("--apelido")

    c = sub.add_parser("citacoes", help="extrai citações de normas de um texto")
    c.add_argument("arquivo", help="arquivo de texto ('-' para stdin)")
    c.add_argument("--json", action="store_true")

    a = p.parse_args(argv)
    if a.comando == "citacoes":
        texto = sys.stdin.read() if a.arquivo == "-" else Path(a.arquivo).read_text(encoding="utf-8")
        cits = extrair_citacoes(texto)
        if a.json:
            print(
                json.dumps(
                    [{"trecho": x.trecho, "normalizada": x.normalizada, "urn": x.urn} for x in cits],
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            for x in cits:
                print(f"{x.normalizada:<55} {x.urn or ''}")
        return 0

    norma = ler_arquivo(a.arquivo, a.apelido)
    if a.comando == "trechos":
        linhas = [json.dumps(tr.to_dict(), ensure_ascii=False) for tr in norma.trechos(a.max, a.revogados)]
        conteudo = "\n".join(linhas) + "\n"
        if a.saida:
            Path(a.saida).write_text(conteudo, encoding="utf-8")
            print(f"lexbr: {len(linhas)} trechos de {norma.nome} → {a.saida}", file=sys.stderr)
        else:
            sys.stdout.write(conteudo)
        return 0
    if a.formato == "json":
        print(norma.to_json())
    elif a.formato == "markdown":
        print(norma.to_markdown())
    else:
        print(f"{norma.nome} — {len(norma.artigos())} artigos" + (f" · {norma.urn}" if norma.urn else ""))
        for d in norma.dispositivos():
            recuo = "  " * d.nivel
            marca = " [revogado]" if d.revogado else " [vetado]" if d.vetado else ""
            resumo = (d.titulo or d.texto)[:70]
            print(f"{recuo}{d.rotulo}{marca}  {resumo}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
