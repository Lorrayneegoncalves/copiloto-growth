from src import simular_dados


def test_mesma_semente_gera_mesmos_dados():
    a = simular_dados.gerar(n=2_000, semente=7)
    b = simular_dados.gerar(n=2_000, semente=7)
    assert a.equals(b)


def test_colunas_e_tamanho(df):
    esperadas = {"id", "data_cadastro", "cidade", "canal", "grupo", "enviou_documentos",
                 "aprovado", "primeira_entrega", "cinco_entregas_30d"}
    assert esperadas.issubset(df.columns)
    assert len(df) == simular_dados.N_CANDIDATOS
    assert df["cidade"].nunique() == 6
    assert set(df["canal"]) == {"indicação", "anúncio", "orgânico"}
    assert set(df["grupo"]) == {"A", "B"}


def test_ninguem_pula_etapa(df):
    # Quem chegou a uma etapa precisa ter passado pela anterior.
    assert (df["aprovado"] <= df["enviou_documentos"]).all()
    assert (df["primeira_entrega"] <= df["aprovado"]).all()
    assert (df["cinco_entregas_30d"] <= df["primeira_entrega"]).all()
