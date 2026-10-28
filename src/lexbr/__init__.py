"""lexbr — leis brasileiras estruturadas: dispositivos, citações e trechos prontos para RAG."""

__version__ = "0.1.0"

from .citacoes import Citacao, NormaRef, extrair_citacoes
from .modelos import Dispositivo, Norma, Trecho
from .parser import ler_arquivo, ler_norma

__all__ = [
    "__version__",
    "Citacao",
    "Dispositivo",
    "Norma",
    "NormaRef",
    "Trecho",
    "extrair_citacoes",
    "ler_arquivo",
    "ler_norma",
]
