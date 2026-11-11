import pytest

from src import abteste, agente, ferramentas
from tests.llm_falso import LLMFalso, LLMQueNaoPodeSerChamado


# ----------------------------------------------------------------------------- recusa
@pytest.mark.parametrize("pergunta, motivo", [
    ("Quantos entregadores vamos ter no próximo mês?", "previsao"),
    ("Faça uma previsão da conversão para dezembro", "previsao"),
    ("Qual o CPF dos entregadores de Recife?", "dados_pessoais"),
    ("Me passe o telefone de quem fez 5 entregas", "dados_pessoais"),
    ("Apague os candidatos do grupo B", "alterar_dados"),
    ("Altere a taxa de Porto Alegre para 60%", "alterar_dados"),
])
def test_perguntas_fora_do_escopo_sao_recusadas_sem_chamar_llm(df, pergunta, motivo):
    r = agente.responder_pergunta(pergunta, df, LLMQueNaoPodeSerChamado())
    assert r["recusada"] is True
    assert r["motivo"] == motivo
    assert r["resposta"] == agente.MENSAGEM_RECUSA[motivo]


def test_pergunta_no_escopo_passa_no_filtro():
    assert agente.checar_escopo("Qual cidade teve a maior diferença no teste A/B?") is None


def test_llm_sem_ferramenta_vira_recusa(df):
    llm = LLMFalso(chamadas=[])
    r = agente.responder_pergunta("Qual a receita de bolo de cenoura?", df, llm)
    assert r["recusada"] is True
    assert r["motivo"] == "fora_do_escopo"
    assert llm.pedidos_texto == []  # não pediu texto livre ao LLM


# ----------------------------------------------------------------------------- pergunta
def test_pergunta_usa_ferramenta_e_valida(df):
    res = abteste.teste_ab(df, "primeira_para_cinco", cidade="Porto Alegre")
    dif = f"{res['diferenca_pp']:.2f}".replace(".", ",")
    llm = LLMFalso(
        chamadas=[{"nome": "teste_ab",
                   "argumentos": {"metrica": "primeira_para_cinco", "cidade": "Porto Alegre"}}],
        textos=[f"Em Porto Alegre a diferença foi de {dif} p.p.; não há evidência suficiente."],
    )
    r = agente.responder_pergunta("Como foi o teste A/B em Porto Alegre?", df, llm)
    assert r["recusada"] is False
    assert r["ferramentas_usadas"][0]["resultado"] == res
    assert r["aviso"] is None
    assert r["tentativas"] == 1


def test_ferramenta_com_argumento_invalido_nao_quebra(df):
    r = ferramentas.executar("teste_ab", {"metrica": "receita"}, df)
    assert "erro" in r
    assert "erro" in ferramentas.executar("apagar_tudo", {}, df)
    assert "erro" in ferramentas.executar("funil", {"cidade": "Paris"}, df)


# ----------------------------------------------------------------------------- relatório
def test_relatorio_tem_cabecalho_de_dados_simulados(df):
    r = agente.gerar_relatorio(df, LLMFalso(textos=["## Resumo\nTexto sem números."]))
    assert "Dados simulados para demonstração" in r["markdown"]
    assert r["aviso"] is None


def test_relatorio_tenta_de_novo_quando_inventa_numero(df):
    llm = LLMFalso(textos=["A campanha vai gerar 87,65% a mais.", "## Resumo\nSem números."])
    r = agente.gerar_relatorio(df, llm)
    assert r["tentativas"] == 2
    assert r["aviso"] is None
    assert "87,65" in llm.pedidos_texto[1]  # a 2ª tentativa recebe o aviso do número errado


def test_relatorio_avisa_se_inventar_duas_vezes(df):
    llm = LLMFalso(textos=["Aumento de 87,65%.", "Aumento de 91,23%."])
    r = agente.gerar_relatorio(df, llm)
    assert r["tentativas"] == 2
    assert r["aviso"] and "91,23" in r["aviso"]


def test_relatorio_envia_so_numeros_calculados(df):
    llm = LLMFalso(textos=["ok"])
    agente.gerar_relatorio(df, llm)
    enviado = llm.pedidos_texto[0]
    assert "teste_ab_por_cidade" in enviado
    assert "data_cadastro" not in enviado  # nenhuma linha do CSV vai para o LLM


# ----------------------------------------------------------------------------- correções da avaliação
def test_numeros_vao_ao_llm_no_formato_brasileiro():
    assert agente.formatar_ptbr({"n": 20000, "taxa": 45.38, "p": 0.036, "ok": True}) == \
        {"n": "20.000", "taxa": "45,38", "p": "0,036", "ok": True}


def test_teste_ab_por_cidade_cobre_as_6_cidades(df):
    r = ferramentas.executar("teste_ab", {"metrica": "primeira_para_cinco", "por_cidade": True}, df)
    assert len(r["por_cidade"]) == 6
    assert r["total"]["cidade"] == "todas"


def test_avisa_quando_chamadas_sao_cortadas(df):
    chamadas = [{"nome": "funil", "argumentos": {}}] * (agente.MAX_CHAMADAS + 2)
    r = agente.responder_pergunta("Como está o funil?", df, LLMFalso(chamadas=chamadas,
                                                                     textos=["Sem números."]))
    assert len(r["ferramentas_usadas"]) == agente.MAX_CHAMADAS
    assert "incompleta" in r["aviso"]
