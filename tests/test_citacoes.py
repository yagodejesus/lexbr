import pytest

from lexbr import extrair_citacoes


def normalizadas(texto):
    return [c.normalizada for c in extrair_citacoes(texto)]


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("art. 7º, inciso IX, da Lei nº 13.709, de 14 de agosto de 2018", "Lei nº 13.709/2018, art. 7º, IX"),
        ("art. 7º, IX, da Lei 13.709/2018", "Lei nº 13.709/2018, art. 7º, IX"),
        ("§ 2º do art. 3º da LGPD", "Lei nº 13.709/2018 (LGPD), art. 3º, § 2º"),
        ("CF, art. 5º, LXXIX", "Constituição Federal, art. 5º, LXXIX"),
        ("art. 5º, X, da Constituição Federal", "Constituição Federal, art. 5º, X"),
        ("art. 42, parágrafo único, do CDC", "Lei nº 8.078/1990 (Código de Defesa do Consumidor), art. 42, parágrafo único"),
        ("alínea b do inciso II do art. 2º", "art. 2º, II, b"),
        ("art. 1º-A da Lei Complementar nº 101/2000", "Lei Complementar nº 101/2000, art. 1º-A"),
        ("art. 482 da CLT", "Decreto-Lei nº 5.452/1943 (CLT), art. 482"),
    ],
)
def test_formas_comuns(texto, esperado):
    assert normalizadas(texto) == [esperado]


def test_varios_artigos_e_intervalos():
    assert normalizadas("arts. 186 e 927 do Código Civil") == [
        "Lei nº 10.406/2002 (Código Civil), art. 186",
        "Lei nº 10.406/2002 (Código Civil), art. 927",
    ]
    assert len(extrair_citacoes("arts. 5º a 7º desta Lei")) == 3
    assert all(c.relativa for c in extrair_citacoes("arts. 5º a 7º desta Lei"))


def test_ano_com_dois_digitos_e_normas_sem_artigo():
    [c] = extrair_citacoes("conforme a Lei 8.078/90")
    assert c.norma.ano == 1990 and c.artigo is None
    assert c.urn == "urn:lex:br:federal:lei:1990;8078"


def test_urns_e_ids():
    [c] = extrair_citacoes("art. 7º, inciso IX, da Lei nº 13.709/2018")
    assert c.id_lexml == "art7_cpt_inc9"
    assert c.urn == "urn:lex:br:federal:lei:2018;13709!art7_cpt_inc9"
    [p] = extrair_citacoes("§ 1º do art. 3º da Lei nº 1.234/2020")
    assert p.id_lexml == "art3_par1"


def test_posicoes():
    texto = "Veja o art. 5º da Lei 8.078/90 para mais detalhes."
    [c] = extrair_citacoes(texto)
    assert texto[c.inicio : c.fim] == c.trecho == "art. 5º da Lei 8.078/90"


def test_texto_sem_citacoes():
    assert extrair_citacoes("A artesã vendeu 5 cestos e a lei da oferta e da procura fez o resto.") == []
