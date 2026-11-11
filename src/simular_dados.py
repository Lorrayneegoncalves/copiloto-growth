"""Gera os dados SIMULADOS da campanha de aquisição de entregadores.

ATENÇÃO: todos os dados são 100% fictícios, criados por este script.
Nenhum número representa uma empresa real. Os efeitos da campanha
foram definidos manualmente (ver EFEITO_B_POR_CIDADE).

Uso:
    python -m src.simular_dados
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEMENTE = 42
N_CANDIDATOS = 20_000
DIAS = 90
DATA_INICIO = pd.Timestamp("2026-01-01")

CAMINHO_CSV = Path(__file__).resolve().parent.parent / "data" / "entregadores.csv"

# Cidades e o peso (participação) de cada uma no total de cadastros.
CIDADES = {
    "São Paulo": 0.30,
    "Rio de Janeiro": 0.20,
    "Belo Horizonte": 0.15,
    "Curitiba": 0.12,
    "Recife": 0.12,
    "Porto Alegre": 0.11,
}

CANAIS = {"indicação": 0.25, "anúncio": 0.45, "orgânico": 0.30}

# Probabilidade base de passar de cada etapa (grupo A = controle).
P_DOCUMENTOS = {"indicação": 0.78, "anúncio": 0.62, "orgânico": 0.70}
P_APROVADO = 0.80
P_PRIMEIRA_ENTREGA = {"indicação": 0.72, "anúncio": 0.60, "orgânico": 0.66}
P_CINCO_ENTREGAS = 0.45  # 5 entregas em até 30 dias após a 1ª entrega

# Efeito do grupo B (bônus por metas) na etapa "1ª entrega -> 5 entregas",
# em pontos percentuais. DEFINIDO POR MIM para fins de demonstração:
# positivo em algumas cidades, nulo em Recife e negativo em Porto Alegre.
EFEITO_B_POR_CIDADE = {
    "São Paulo": 0.05,
    "Rio de Janeiro": 0.04,
    "Belo Horizonte": 0.03,
    "Curitiba": 0.01,
    "Recife": 0.00,
    "Porto Alegre": -0.07,
}


def _datas_apos(base: pd.Series, rng: np.random.Generator, min_d: int, max_d: int,
                mascara: np.ndarray) -> pd.Series:
    """Soma de min_d a max_d dias à data base, apenas onde a máscara é verdadeira."""
    dias = rng.integers(min_d, max_d + 1, size=len(base))
    datas = base + pd.to_timedelta(dias, unit="D")
    return datas.where(mascara)


def gerar(n: int = N_CANDIDATOS, semente: int = SEMENTE) -> pd.DataFrame:
    """Gera o DataFrame simulado. Mesma semente => mesmo resultado."""
    rng = np.random.default_rng(semente)

    cidade = rng.choice(list(CIDADES), size=n, p=list(CIDADES.values()))
    canal = rng.choice(list(CANAIS), size=n, p=list(CANAIS.values()))
    grupo = rng.choice(["A", "B"], size=n)
    data_cadastro = DATA_INICIO + pd.to_timedelta(rng.integers(0, DIAS, size=n), unit="D")
    data_cadastro = pd.Series(data_cadastro)

    # Etapa 1: envio de documentos
    p_doc = pd.Series(canal).map(P_DOCUMENTOS).to_numpy()
    enviou_documentos = rng.random(n) < p_doc

    # Etapa 2: aprovação (só quem enviou documentos)
    aprovado = enviou_documentos & (rng.random(n) < P_APROVADO)

    # Etapa 3: primeira entrega (só aprovados)
    p_pri = pd.Series(canal).map(P_PRIMEIRA_ENTREGA).to_numpy()
    primeira_entrega = aprovado & (rng.random(n) < p_pri)

    # Etapa 4: 5 entregas em 30 dias (só quem fez a 1ª). Aqui entra o efeito do grupo B.
    efeito = pd.Series(cidade).map(EFEITO_B_POR_CIDADE).to_numpy() * (grupo == "B")
    p_cinco = P_CINCO_ENTREGAS + efeito
    cinco_entregas_30d = primeira_entrega & (rng.random(n) < p_cinco)

    data_documentos = _datas_apos(data_cadastro, rng, 0, 7, enviou_documentos)
    data_aprovacao = _datas_apos(data_documentos, rng, 1, 5, aprovado)
    data_primeira_entrega = _datas_apos(data_aprovacao, rng, 0, 14, primeira_entrega)
    data_quinta_entrega = _datas_apos(data_primeira_entrega, rng, 3, 30, cinco_entregas_30d)

    df = pd.DataFrame({
        "id": np.arange(1, n + 1),
        "data_cadastro": data_cadastro.dt.date,
        "cidade": cidade,
        "canal": canal,
        "grupo": grupo,
        "enviou_documentos": enviou_documentos.astype(int),
        "data_documentos": data_documentos.dt.date,
        "aprovado": aprovado.astype(int),
        "data_aprovacao": data_aprovacao.dt.date,
        "primeira_entrega": primeira_entrega.astype(int),
        "data_primeira_entrega": data_primeira_entrega.dt.date,
        "cinco_entregas_30d": cinco_entregas_30d.astype(int),
        "data_quinta_entrega": data_quinta_entrega.dt.date,
    })
    return df


def salvar(df: pd.DataFrame, caminho: Path = CAMINHO_CSV) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False, encoding="utf-8")
    return caminho


if __name__ == "__main__":
    caminho = salvar(gerar())
    print(f"Dados simulados salvos em: {caminho}")
