"""Cálculos do funil de aquisição (sem LLM). Todas as funções devolvem dicts simples."""

from __future__ import annotations

import pandas as pd

# (chave, nome amigável, coluna 0/1 que indica que a pessoa chegou à etapa)
ETAPAS = [
    ("cadastro", "Cadastro", None),
    ("documentos", "Documentos enviados", "enviou_documentos"),
    ("aprovado", "Aprovado", "aprovado"),
    ("primeira_entrega", "Primeira entrega", "primeira_entrega"),
    ("cinco_entregas", "5 entregas em 30 dias", "cinco_entregas_30d"),
]

SEGMENTOS_VALIDOS = ("cidade", "canal", "grupo")


def _pct(parte: float, todo: float) -> float | None:
    """Porcentagem com 2 casas decimais (None se o denominador for zero)."""
    if not todo:
        return None
    return round(100 * parte / todo, 2)


def funil(df: pd.DataFrame) -> dict:
    """Contagem e conversão por etapa, e queda em relação à etapa anterior."""
    total = int(len(df))
    etapas = []
    anterior = total
    for chave, nome, coluna in ETAPAS:
        qtd = total if coluna is None else int(df[coluna].sum())
        conv_anterior = _pct(qtd, anterior)
        etapas.append({
            "etapa": chave,
            "nome": nome,
            "quantidade": qtd,
            "taxa_sobre_cadastro_pct": _pct(qtd, total),
            "taxa_sobre_etapa_anterior_pct": conv_anterior,
            "queda_vs_etapa_anterior_pct": None if conv_anterior is None
            else round(100 - conv_anterior, 2),
        })
        anterior = qtd
    return {"total_cadastros": total, "etapas": etapas}


def segmentar(df: pd.DataFrame, por: str) -> dict:
    """O mesmo funil, separado por cidade, canal ou grupo."""
    if por not in SEGMENTOS_VALIDOS:
        raise ValueError(f"'por' deve ser um de {SEGMENTOS_VALIDOS}, recebido: {por!r}")
    segmentos = {
        str(valor): funil(sub)
        for valor, sub in df.groupby(por, sort=True)
    }
    return {"por": por, "segmentos": segmentos}


def funil_para_tabela(resultado: dict) -> pd.DataFrame:
    """Converte o dict de funil() em tabela (para mostrar na interface)."""
    return pd.DataFrame(resultado["etapas"])
