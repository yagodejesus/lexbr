<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
    <img src="assets/logo.svg" alt="lexbr" width="340">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/yagodejesus/lexbr/actions/workflows/ci.yml"><img src="https://github.com/yagodejesus/lexbr/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/lexbr/"><img src="https://img.shields.io/pypi/v/lexbr.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/lexbr/"><img src="https://img.shields.io/pypi/pyversions/lexbr.svg" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT"></a>
</p>

**Leis brasileiras estruturadas para RAG e legal tech: artigos, parágrafos, incisos e alíneas como dados — e citações reconhecidas em qualquer texto.**

> 🇺🇸 *Turn Brazilian legislation into structured data: parse laws and decrees into a tree of articles, paragraphs, items and sub-items; extract citations like "art. 7º, IX, da LGPD" from free text; and produce RAG-ready chunks with hierarchical context and LexML URNs. Zero dependencies.*

Quem constrói assistentes jurídicos com LLMs descobre rápido que dividir uma lei a cada 500 caracteres é má ideia: o inciso IX fica separado do caput que lhe dá sentido, o modelo não sabe de qual capítulo veio o trecho e cita "art. 7" sem dizer de qual lei. O `lexbr` entende a técnica legislativa brasileira e resolve isso.

```python
import lexbr

lei = lexbr.ler_arquivo("lgpd.html", apelido="LGPD")   # HTML do Planalto, .txt ou texto colado

lei.nome                          # 'Lei nº 13.709/2018'
lei.urn                           # 'urn:lex:br:federal:lei:2018-08-14;13709'
lei.buscar("art. 7º, IX")         # Dispositivo(tipo='inciso', ...)
lei.artigo("3-A").anotacoes       # ['(Incluído pela Lei nº ...)']

for t in lei.trechos(max_caracteres=1500):   # chunks para o seu banco vetorial
    t.texto      # 'Lei nº 13.709/2018 (LGPD) › Capítulo II (...) › Seção I (...)\nArt. 7º ...'
    t.citacao    # 'Lei nº 13.709/2018, art. 7º'
    t.urn        # 'urn:lex:br:federal:lei:2018-08-14;13709!art7'
```

```python
lexbr.extrair_citacoes("Nos termos do art. 7º, inciso IX, da Lei nº 13.709, de 14 de agosto de 2018, "
                       "e dos arts. 186 e 927 do Código Civil, bem como do § 2º do art. 3º da LGPD "
                       "e da CF, art. 5º, LXXIX.")
```

```text
Lei nº 13.709/2018, art. 7º, IX                         urn:lex:br:federal:lei:2018;13709!art7_cpt_inc9
Lei nº 10.406/2002 (Código Civil), art. 186             urn:lex:br:federal:lei:2002;10406!art186
Lei nº 10.406/2002 (Código Civil), art. 927             urn:lex:br:federal:lei:2002;10406!art927
Lei nº 13.709/2018 (LGPD), art. 3º, § 2º                urn:lex:br:federal:lei:2018;13709!art3_par2
Constituição Federal, art. 5º, LXXIX                    urn:lex:br:federal:constituicao:1988-10-05;1988!art5_cpt_inc79
```

## O que ele entende

**Estrutura.** Epígrafe (tipo, número e data), ementa, preâmbulo, Parte, Livro, Título, Capítulo, Seção e Subseção (com o nome na mesma linha ou na seguinte), artigos (`Art. 1º`, `Art. 10.`, `Art. 3º-A`, `Art. 1.000`), parágrafos (`§ 1º`, `Parágrafo único`), incisos (`I -`, `II –`, `III —`), alíneas (`a)`), itens (`1.`) e o fecho (`Brasília, …`).

**Anotações do Planalto.** `(Incluído pela Lei…)`, `(Redação dada pela…)`, `(Revogado pela…)`, `(Vide…)` e `(VETADO)` são separadas do texto e guardadas em `anotacoes`. Dispositivos revogados e vetados ficam marcados e, por padrão, fora dos trechos para RAG. No HTML, o texto riscado (redações antigas) é descartado.

**Citações em texto livre.** `art. 7º, IX, da Lei 13.709/2018`, `§ 2º do art. 3º`, `alínea b do inciso II do art. 2º`, `arts. 186 e 927`, `arts. 5º a 7º desta Lei`, `CF, art. 5º`, `Lei 8.078/90`, `LC 101/2000` — e nomes populares: Constituição Federal, Código Civil, CDC, CPC, CPP, Código Penal, CLT, CTN, CTB, ECA, LGPD, Marco Civil da Internet, LAI, Lei Maria da Penha, Lei de Responsabilidade Fiscal e nova Lei de Licitações.

**Identificadores LexML.** Cada dispositivo tem um id no estilo LexML (`art7_cpt_inc9`, `art3_par1`, `art2_par1u`) e, quando a norma é identificada, uma URN (`urn:lex:br:federal:lei:2018;13709!art7_cpt_inc9`) — ótima para deduplicar, linkar e citar fontes nas respostas do seu LLM.

## Trechos para RAG

`Norma.trechos()` gera um trecho por artigo. Se o artigo passar de `max_caracteres`, ele é dividido entre incisos e parágrafos, e **o caput se repete** em cada parte. Todo trecho começa com a hierarquia (norma › capítulo › seção) e traz metadados para filtros:

```python
{
  "id": "urn:lex:br:federal:lei:2026-01-01;99999!art2#2",
  "citacao": "Lei nº 99.999/2026, art. 2º",
  "contexto": "Lei nº 99.999/2026 › Capítulo I (DISPOSIÇÕES PRELIMINARES)",
  "metadados": {"artigo": "2", "parte": 2, "partes": 2, "estrutura": ["Capítulo I"], "anotacoes": []}
}
```

```bash
lexbr trechos lgpd.html --apelido LGPD -o lgpd.jsonl     # JSONL pronto para indexar
```

## Linha de comando

```bash
lexbr estrutura exemplos/lei_exemplo.txt                  # árvore no terminal
lexbr estrutura lei.html --formato markdown > lei.md      # Markdown limpo, revogados riscados
lexbr estrutura lei.txt --formato json                    # árvore completa em JSON
lexbr citacoes parecer.txt                                # citações normalizadas + URNs
```

## Instalação

```bash
pip install lexbr
```

## Como obter o texto das leis

Salve a página da norma no site do Planalto (Ctrl+S → `.html`) ou copie o texto para um `.txt`. O repositório traz uma norma **fictícia** de exemplo em [`exemplos/lei_exemplo.txt`](exemplos/lei_exemplo.txt), com capítulos, seções, alíneas, itens, dispositivos revogados e vetados.

## Limitações

- Anexos, tabelas e textos de tratados anexados a decretos não são estruturados.
- Normas estaduais e municipais são lidas normalmente, mas as URNs geradas seguem o padrão federal.
- Citações muito informais ("aquele artigo da LGPD sobre consentimento") não são reconhecidas.

## Desenvolvimento

```bash
git clone https://github.com/yagodejesus/lexbr && cd lexbr
pip install -e ".[dev]"
pytest && ruff check .
```

## Licença

MIT © Yago de Jesus Martins. Textos de leis não são objeto de direito autoral (Lei 9.610/98, art. 8º, IV).
