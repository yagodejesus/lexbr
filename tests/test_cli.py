import json
from pathlib import Path

from lexbr.cli import main

EXEMPLO = str(Path(__file__).parent.parent / "exemplos" / "lei_exemplo.txt")


def test_estrutura(capsys):
    assert main(["estrutura", EXEMPLO]) == 0
    out = capsys.readouterr().out
    assert "Lei nº 99.999/2026 — 7 artigos" in out and "[revogado]" in out
    assert main(["estrutura", EXEMPLO, "--formato", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["numero"] == "99999"


def test_trechos(tmp_path):
    saida = tmp_path / "t.jsonl"
    assert main(["trechos", EXEMPLO, "-o", str(saida)]) == 0
    linhas = saida.read_text(encoding="utf-8").splitlines()
    assert len(linhas) == 6 and json.loads(linhas[0])["citacao"] == "Lei nº 99.999/2026, art. 1º"


def test_citacoes(tmp_path, capsys):
    f = tmp_path / "parecer.txt"
    f.write_text("Com base no art. 7º, IX, da LGPD.", encoding="utf-8")
    assert main(["citacoes", str(f)]) == 0
    assert "art7_cpt_inc9" in capsys.readouterr().out
