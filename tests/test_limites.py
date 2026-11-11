from datetime import date
from types import SimpleNamespace

import pytest

from src import agente, llm
from src.limites import ContadorDiario
from tests.llm_falso import LLMQueNaoPodeSerChamado


# ----------------------------------------------------------------------------- limite diário
def test_contador_bloqueia_ao_atingir_o_limite():
    c = ContadorDiario(limite=3)
    assert [c.consumir() for _ in range(5)] == [True, True, True, False, False]
    assert c.restantes() == 0


def test_contador_zera_no_dia_seguinte():
    dia = {"hoje": date(2026, 11, 11)}
    c = ContadorDiario(limite=2, hoje=lambda: dia["hoje"])
    c.consumir(); c.consumir()
    assert c.consumir() is False
    dia["hoje"] = date(2026, 11, 12)
    assert c.restantes() == 2
    assert c.consumir() is True


# ----------------------------------------------------------------------------- tamanho da pergunta
def test_pergunta_longa_e_recusada_sem_chamar_llm(df):
    pergunta = "Como foi o teste A/B? " * 20  # > 300 caracteres
    r = agente.responder_pergunta(pergunta, df, LLMQueNaoPodeSerChamado())
    assert r["recusada"] is True
    assert r["motivo"] == "muito_longa"


def test_pergunta_no_limite_passa():
    assert agente.checar_escopo("a" * agente.MAX_CARACTERES_PERGUNTA) is None


# ----------------------------------------------------------------------------- teto de tokens
def _resposta_falsa(finish_reason):
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish_reason)])


def test_resposta_cortada_gera_erro_claro():
    with pytest.raises(llm.RespostaCortada):
        llm.ClienteOpenAI._checar_corte(_resposta_falsa("length"))
    llm.ClienteOpenAI._checar_corte(_resposta_falsa("stop"))  # não levanta


def test_tetos_de_tokens_definidos():
    assert llm.MAX_TOKENS_TEXTO and llm.MAX_TOKENS_FERRAMENTAS
