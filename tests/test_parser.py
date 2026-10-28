from datetime import date
from pathlib import Path

import pytest

import lexbr

EXEMPLO = Path(__file__).parent.parent / "exemplos" / "lei_exemplo.txt"


@pytest.fixture(scope="module")
def norma():
    return lexbr.ler_arquivo(EXEMPLO, apelido="Lei dos Dados Abertos")


def test_cabecalho(norma):
    assert (norma.tipo, norma.numero, norma.data) == ("Lei", "99999", date(2026, 1, 1))
    assert norma.nome == "Lei nº 99.999/2026"
    assert norma.urn == "urn:lex:br:federal:lei:2026-01-01;99999"
    assert norma.ementa.startswith("Dispõe sobre o uso de dados abertos")
    assert "Faço saber" in norma.preambulo
    assert norma.fecho.startswith("Brasília, 1º de janeiro de 2026")


def test_estrutura(norma):
    caps = [d for d in norma.filhos]
    assert [c.rotulo for c in caps] == ["Capítulo I", "Capítulo II", "Capítulo III"]
    assert caps[0].titulo == "DISPOSIÇÕES PRELIMINARES"
    secoes = [d for d in caps[1].filhos if d.tipo == "secao"]
    assert [s.titulo for s in secoes] == ["Dos Requisitos", "Da Qualidade"]
    assert [a.numero for a in norma.artigos()] == ["1", "2", "3", "3-A", "4", "10", "11"]


def test_dispositivos_aninhados(norma):
    art2 = norma.artigo(2)
    assert [f.rotulo for f in art2.filhos] == ["I", "II", "III", "Parágrafo único"]
    item = norma.buscar("art. 2º, II, b, 1")
    assert item.texto == "dicionário de dados;"
    assert item.citacao == "art. 2º, II, b, 1"
    assert item.id_lexml == "art2_cpt_inc2_ali2_ite1"


def test_anotacoes_revogados_e_vetados(norma):
    assert norma.buscar("art. 3, § 2º").revogado
    assert norma.artigo("4").vetado
    art3a = norma.artigo("3-A")
    assert art3a.rotulo == "Art. 3º-A" and art3a.id_lexml == "art3-1"
    assert art3a.anotacoes == ["(Incluído pela Lei nº 99.998, de 2026)"]
    assert "Redação dada" in norma.buscar("art. 2, III").anotacoes[0]
    assert norma.buscar("art. 2, III").texto.endswith("do Município.")


def test_rotulos(norma):
    assert norma.artigo(10).rotulo == "Art. 10"
    assert norma.buscar("art. 2, parágrafo único").id_lexml == "art2_par1u"
    assert norma.buscar("art. 3, § 1º").citacao == "art. 3º, § 1º"
    assert norma.buscar("art. 99") is None and norma.buscar("bobagem") is None


def test_trechos_para_rag(norma):
    trechos = norma.trechos(max_caracteres=400)
    ids = [t.id.split("!")[1] for t in trechos]
    assert ids == ["art1", "art2#1", "art2#2", "art3", "art3-1", "art10#1", "art10#2", "art11"]  # sem o vetado
    t = trechos[1]
    assert t.texto.startswith("Lei nº 99.999/2026 (Lei dos Dados Abertos) › Capítulo I (DISPOSIÇÕES PRELIMINARES)")
    assert "Art. 2º Para os fins desta Lei" in trechos[2].texto  # o caput se repete na 2ª parte
    assert t.metadados["partes"] == 2 and t.citacao == "Lei nº 99.999/2026, art. 2º"
    assert all(len(x.texto) < 400 + 200 for x in trechos)
    assert "§ 2º" not in trechos[3].texto  # revogado fica de fora
    assert any("§ 2º" in x.texto for x in norma.trechos(incluir_revogados=True))


def test_exportacoes(norma):
    d = norma.to_dict()
    assert d["nome"] == "Lei nº 99.999/2026" and d["dispositivos"][0]["tipo"] == "capitulo"
    md = norma.to_markdown()
    assert "## Capítulo I — DISPOSIÇÕES PRELIMINARES" in md and "**Art. 1º** Esta Lei" in md and "~~" in md


def test_texto_com_variacoes_de_formatacao():
    texto = """DECRETO Nº 12.345, DE 5 DE MARÇO DE 2025
Regulamenta algo.
O PRESIDENTE DA REPÚBLICA, no uso da atribuição, decreta:
Art. 1o Fica criado o programa.
Art. 2º - O programa terá:
I – metas;
II — indicadores.
§ 1º. Os indicadores serão anuais.
Art. 1.000. Artigo de número grande."""
    n = lexbr.ler_norma(texto)
    assert n.tipo == "Decreto" and n.data == date(2025, 3, 5)
    assert [a.numero for a in n.artigos()] == ["1", "2", "1000"]
    assert [f.rotulo for f in n.artigo(2).filhos] == ["I", "II", "§ 1º"]


def test_html_do_planalto(tmp_path):
    html = tmp_path / "lei.html"
    html.write_text(
        "<html><body><p>LEI Nº 1.234, DE 2 DE MAIO DE 2020</p><p>Art. 1º Texto <strike>antigo</strike> atual.</p>"
        "<p>Art. 2º Outro.</p></body></html>",
        encoding="utf-8",
    )
    n = lexbr.ler_arquivo(html)
    assert n.artigo(1).texto == "Texto atual." and len(n.artigos()) == 2
