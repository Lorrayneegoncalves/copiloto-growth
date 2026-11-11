import pytest

from src.metricas import funil, segmentar


def test_funil_totais_batem_com_csv(df):
    r = funil(df)
    qtd = {e["etapa"]: e["quantidade"] for e in r["etapas"]}
    assert r["total_cadastros"] == len(df)
    assert qtd["cadastro"] == len(df)
    assert qtd["documentos"] == df["enviou_documentos"].sum()
    assert qtd["aprovado"] == df["aprovado"].sum()
    assert qtd["primeira_entrega"] == df["primeira_entrega"].sum()
    assert qtd["cinco_entregas"] == df["cinco_entregas_30d"].sum()


def test_funil_taxas_e_quedas(df):
    etapas = funil(df)["etapas"]
    assert etapas[0]["taxa_sobre_cadastro_pct"] == 100.0
    for anterior, atual in zip(etapas, etapas[1:]):
        assert atual["quantidade"] <= anterior["quantidade"]
        esperado = round(100 * atual["quantidade"] / anterior["quantidade"], 2)
        assert atual["taxa_sobre_etapa_anterior_pct"] == esperado
        assert atual["queda_vs_etapa_anterior_pct"] == pytest.approx(100 - esperado)


@pytest.mark.parametrize("por", ["cidade", "canal"])
def test_segmentar_soma_igual_ao_total(df, por):
    r = segmentar(df, por)
    assert r["por"] == por
    assert sum(s["total_cadastros"] for s in r["segmentos"].values()) == len(df)
    assert set(r["segmentos"]) == set(df[por].unique())


def test_segmentar_rejeita_coluna_invalida(df):
    with pytest.raises(ValueError):
        segmentar(df, "cpf")
