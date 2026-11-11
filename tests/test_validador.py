from src.validador import extrair_numeros, validar

RESULTADOS = {"taxa_A": 45.38, "taxa_B": 47.85, "diferenca_pp": 2.47, "ic95_pp": [0.16, 4.79],
              "p_valor": 0.036, "n": 20000, "negativa": -4.88}


def test_extrai_formatos_brasileiros():
    nums = {v for _, v, _ in extrair_numeros("20.000 cadastros, 45,38% e p = 0,036 e −4,88 p.p.")}
    assert {20000.0, 45.38, 0.036, -4.88} <= nums


def test_aceita_numeros_calculados_e_arredondados():
    texto = ("O grupo B teve 47,85% contra 45,4% do A (+2,5 p.p.; IC de 95% de 0,16 a 4,79; "
             "p = 0,036) em 20.000 cadastros. Em Porto Alegre a diferença foi de −4,88 p.p.")
    r = validar(texto, RESULTADOS)
    assert r["ok"], r["numeros_invalidos"]


def test_detecta_numero_inventado():
    r = validar("A campanha aumentou a conversão em 12,3% e trará 500 novos entregadores.",
                RESULTADOS)
    assert not r["ok"]
    assert "12,3" in r["numeros_invalidos"]
    assert "500" in r["numeros_invalidos"]


def test_arredondamento_tem_limite():
    # 45,5 não é arredondamento de 45,38 (com 1 casa seria 45,4)
    assert not validar("taxa de 45,5%", RESULTADOS)["ok"]


def test_ignora_datas_e_numeros_estruturais():
    texto = "Em 10/11/2026, com 95% de confiança, olhando 5 entregas em 30 dias, 6 cidades."
    assert validar(texto, RESULTADOS)["ok"]
