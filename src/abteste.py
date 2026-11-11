"""Teste A/B de duas proporções (sem LLM). Devolve dicts simples.

Grupo A = controle; grupo B = campanha de bônus por metas.
A diferença é sempre B - A, em pontos percentuais (p.p.).
"""

from __future__ import annotations

import math

import pandas as pd
from statsmodels.stats.proportion import (
    confint_proportions_2indep,
    proportions_ztest,
)

# metrica -> (descrição, coluna da base/denominador ou None = todos, coluna do sucesso)
METRICAS = {
    "primeira_para_cinco": (
        "1ª entrega → 5 entregas em 30 dias", "primeira_entrega", "cinco_entregas_30d"),
    "cadastro_para_primeira": (
        "Cadastro → 1ª entrega", None, "primeira_entrega"),
    "cadastro_para_cinco": (
        "Cadastro → 5 entregas em 30 dias", None, "cinco_entregas_30d"),
    "cadastro_para_documentos": (
        "Cadastro → documentos enviados", None, "enviou_documentos"),
}

ALFA = 0.05
N_MINIMO_POR_GRUPO = 100     # abaixo disso, avisamos que a amostra é pequena
MIN_SUCESSOS_E_FALHAS = 10   # regra prática para a aproximação normal valer


def _arred(x: float, casas: int) -> float | None:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return round(float(x), casas)


def _contar(df: pd.DataFrame, base: str | None, sucesso: str, grupo: str) -> tuple[int, int]:
    sub = df[df["grupo"] == grupo]
    if base is not None:
        sub = sub[sub[base] == 1]
    return int(sub[sucesso].sum()), int(len(sub))


def calcular(sucessos_a: int, n_a: int, sucessos_b: int, n_b: int) -> dict:
    """Teste de duas proporções a partir de contagens. Útil para testes com casos conhecidos."""
    avisos: list[str] = []
    if n_a == 0 or n_b == 0:
        return {
            "grupo_A": {"n": n_a, "sucessos": sucessos_a, "taxa_pct": None},
            "grupo_B": {"n": n_b, "sucessos": sucessos_b, "taxa_pct": None},
            "diferenca_pp": None, "ic95_pp": None, "p_valor": None,
            "significativo": False, "amostra_pequena": True,
            "avisos": ["Um dos grupos não tem nenhuma observação; não é possível testar."],
            "conclusao": "Não há dados suficientes para comparar os grupos.",
        }

    taxa_a, taxa_b = sucessos_a / n_a, sucessos_b / n_b
    diferenca = taxa_b - taxa_a

    amostra_pequena = False
    if min(n_a, n_b) < N_MINIMO_POR_GRUPO:
        amostra_pequena = True
        avisos.append(f"Amostra pequena: menos de {N_MINIMO_POR_GRUPO} pessoas em algum grupo.")
    if min(sucessos_a, n_a - sucessos_a, sucessos_b, n_b - sucessos_b) < MIN_SUCESSOS_E_FALHAS:
        amostra_pequena = True
        avisos.append("Poucos sucessos ou falhas em algum grupo: o teste pode ser impreciso.")

    # Teste z de duas proporções (B vs A). Se as taxas forem idênticas, p = 1.
    if sucessos_a + sucessos_b in (0, n_a + n_b):
        p_valor = 1.0
    else:
        _, p_valor = proportions_ztest([sucessos_b, sucessos_a], [n_b, n_a])

    # Intervalo de confiança de 95% para a diferença B - A (método de Wald).
    ic_baixo, ic_alto = confint_proportions_2indep(
        sucessos_b, n_b, sucessos_a, n_a, method="wald", compare="diff", alpha=ALFA)

    ic_inclui_zero = ic_baixo <= 0 <= ic_alto
    significativo = bool(p_valor < ALFA and not ic_inclui_zero)

    if significativo:
        direcao = "maior" if diferenca > 0 else "menor"
        conclusao = (f"Há evidência estatística (p < 0,05) de que a taxa do grupo B é "
                     f"{direcao} que a do grupo A.")
    else:
        conclusao = ("Não há evidência suficiente de diferença entre os grupos "
                     "(p-valor alto e/ou intervalo de confiança inclui zero).")

    return {
        "grupo_A": {"n": n_a, "sucessos": sucessos_a, "taxa_pct": _arred(100 * taxa_a, 2)},
        "grupo_B": {"n": n_b, "sucessos": sucessos_b, "taxa_pct": _arred(100 * taxa_b, 2)},
        "diferenca_pp": _arred(100 * diferenca, 2),
        "ic95_pp": [_arred(100 * ic_baixo, 2), _arred(100 * ic_alto, 2)],
        "p_valor": _arred(p_valor, 4),
        "significativo": significativo,
        "amostra_pequena": amostra_pequena,
        "avisos": avisos,
        "conclusao": conclusao,
    }


def teste_ab(df: pd.DataFrame, metrica: str = "primeira_para_cinco",
             cidade: str | None = None) -> dict:
    """Compara grupo B vs A numa métrica de conversão. Opcionalmente filtra uma cidade."""
    if metrica not in METRICAS:
        raise ValueError(f"Métrica desconhecida: {metrica!r}. Opções: {list(METRICAS)}")
    descricao, base, sucesso = METRICAS[metrica]

    if cidade is not None:
        df = df[df["cidade"] == cidade]

    s_a, n_a = _contar(df, base, sucesso, "A")
    s_b, n_b = _contar(df, base, sucesso, "B")

    resultado = calcular(s_a, n_a, s_b, n_b)
    return {"metrica": metrica, "descricao": descricao,
            "cidade": cidade or "todas", **resultado}


def teste_ab_por_cidade(df: pd.DataFrame, metrica: str = "primeira_para_cinco") -> dict:
    """Roda o teste A/B separadamente para cada cidade."""
    return {
        str(c): teste_ab(df, metrica, cidade=c)
        for c in sorted(df["cidade"].unique())
    }
