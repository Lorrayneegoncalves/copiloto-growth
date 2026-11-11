import pandas as pd
import pytest

from src import abteste
from src.abteste import calcular


def test_diferenca_conhecida_e_detectada():
    # A: 100/1000 = 10%; B: 200/1000 = 20% -> diferença de 10 p.p.
    r = calcular(sucessos_a=100, n_a=1000, sucessos_b=200, n_b=1000)
    assert r["grupo_A"]["taxa_pct"] == 10.0
    assert r["grupo_B"]["taxa_pct"] == 20.0
    assert r["diferenca_pp"] == 10.0
    assert r["p_valor"] < 0.001
    baixo, alto = r["ic95_pp"]
    assert 0 < baixo < 10 < alto
    assert r["significativo"] is True
    assert r["amostra_pequena"] is False
    assert "Há evidência" in r["conclusao"]


def test_sem_diferenca_nao_declara_vencedor():
    r = calcular(sucessos_a=150, n_a=1000, sucessos_b=150, n_b=1000)
    assert r["diferenca_pp"] == 0.0
    assert r["p_valor"] == pytest.approx(1.0)
    baixo, alto = r["ic95_pp"]
    assert baixo < 0 < alto
    assert r["significativo"] is False
    assert "Não há evidência suficiente" in r["conclusao"]


def test_amostra_pequena_gera_aviso():
    r = calcular(sucessos_a=3, n_a=20, sucessos_b=8, n_b=20)
    assert r["amostra_pequena"] is True
    assert r["avisos"]


def test_grupo_vazio_nao_quebra():
    r = calcular(0, 0, 5, 10)
    assert r["p_valor"] is None
    assert r["significativo"] is False


def test_teste_ab_com_dataframe():
    df = pd.DataFrame({
        "grupo": ["A"] * 4 + ["B"] * 4,
        "cidade": ["X"] * 8,
        "primeira_entrega": [1, 1, 1, 0, 1, 1, 1, 1],
        "cinco_entregas_30d": [1, 0, 0, 0, 1, 1, 1, 0],
    })
    r = abteste.teste_ab(df, "primeira_para_cinco")
    # A: base = 3 com 1ª entrega, 1 sucesso; B: base = 4, 3 sucessos
    assert (r["grupo_A"]["n"], r["grupo_A"]["sucessos"]) == (3, 1)
    assert (r["grupo_B"]["n"], r["grupo_B"]["sucessos"]) == (4, 3)
    assert r["amostra_pequena"] is True


def test_metrica_invalida(df):
    with pytest.raises(ValueError):
        abteste.teste_ab(df, "receita")


def test_por_cidade_cobre_todas(df):
    r = abteste.teste_ab_por_cidade(df)
    assert set(r) == set(df["cidade"].unique())
    soma_n = sum(v["grupo_A"]["n"] + v["grupo_B"]["n"] for v in r.values())
    assert soma_n == df["primeira_entrega"].sum()
