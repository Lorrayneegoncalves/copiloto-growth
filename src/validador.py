"""Confere se os números escritos pelo LLM existem nos resultados calculados pelo código.

Regra de tolerância: um número escrito com N casas decimais é aceito se for o
arredondamento de algum número calculado (ex.: "45,4" aceita 45,38; "2,5" aceita 2,47).
"""

from __future__ import annotations

import re

# Números "estruturais" que podem aparecer sem vir dos cálculos:
# contagens pequenas (1 a 10), 30 dias, 90 dias, 95% de confiança, 100%, alfa de 0,05.
PERMITIDOS = {float(i) for i in range(0, 11)} | {30.0, 90.0, 95.0, 100.0, 0.05}

_DATA = re.compile(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b|\b\d{4}-\d{2}-\d{2}\b")
# 1) milhar com ponto (20.000 / 1.234,5)  2) decimal com vírgula ou ponto  3) inteiro
_NUMERO = re.compile(r"(?<![\w.,])[-−]?(?:[1-9]\d{0,2}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)")


def extrair_numeros(texto: str) -> list[tuple[str, float, int]]:
    """Devolve (trecho original, valor, casas decimais) para cada número do texto."""
    texto = _DATA.sub(" ", texto)
    encontrados = []
    for m in _NUMERO.finditer(texto):
        bruto = m.group(0)
        limpo = bruto.replace("−", "-")
        if re.fullmatch(r"-?[1-9]\d{0,2}(?:\.\d{3})+(?:,\d+)?", limpo):
            limpo = limpo.replace(".", "")          # tira separador de milhar
        limpo = limpo.replace(",", ".")
        casas = len(limpo.split(".")[1]) if "." in limpo else 0
        encontrados.append((bruto, float(limpo), casas))
    return encontrados


def coletar_numeros(obj) -> set[float]:
    """Todos os números (em valor absoluto) dentro de dicts/listas de resultados."""
    numeros: set[float] = set()
    if isinstance(obj, bool):
        return numeros
    if isinstance(obj, (int, float)):
        numeros.add(abs(float(obj)))
    elif isinstance(obj, dict):
        for v in obj.values():
            numeros |= coletar_numeros(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            numeros |= coletar_numeros(v)
    return numeros


def _bate(valor: float, casas: int, calculados: set[float]) -> bool:
    tolerancia = 0.5 * 10 ** (-casas) + 1e-9
    return any(abs(valor - c) <= tolerancia for c in calculados)


def validar(texto: str, resultados) -> dict:
    """Compara os números do texto com os resultados. Devolve os números sem origem."""
    calculados = coletar_numeros(resultados) | PERMITIDOS
    invalidos = []
    for bruto, valor, casas in extrair_numeros(texto):
        if not _bate(abs(valor), casas, calculados):
            invalidos.append(bruto)
    return {"ok": not invalidos, "numeros_invalidos": invalidos}
