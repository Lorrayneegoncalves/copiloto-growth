"""Única parte do projeto que conhece o provedor do LLM (hoje: OpenAI).

O resto do código usa só a interface ClienteLLM:
  - gerar_texto(sistema, usuario) -> str
  - escolher_ferramentas(sistema, pergunta, ferramentas) -> RespostaFerramentas

Para trocar de provedor, crie outra classe com esses dois métodos e mude criar_cliente().

A chave vem de OPENAI_API_KEY (variável de ambiente, arquivo .env ou st.secrets).
Nunca escreva a chave no código.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

MODELO_PADRAO = "gpt-5-mini"

# Teto de tokens gerados por chamada (inclui o raciocínio interno do modelo).
# Valores definidos a partir do consumo medido; ver README > Controle de custo.
MAX_TOKENS_TEXTO = 6000        # maior medido: 2.300 (relatório)
MAX_TOKENS_FERRAMENTAS = 1500  # maior medido: 207


class RespostaCortada(RuntimeError):
    """O LLM atingiu o teto de tamanho antes de terminar a resposta."""


@dataclass
class RespostaFerramentas:
    """O que o LLM decidiu: chamar ferramentas e/ou responder em texto."""
    chamadas: list[dict] = field(default_factory=list)  # [{"nome": str, "argumentos": dict}]
    texto: str | None = None


class ClienteLLM:
    """Interface. Os testes usam um LLM falso com estes mesmos métodos."""

    def gerar_texto(self, sistema: str, usuario: str) -> str:
        raise NotImplementedError

    def escolher_ferramentas(self, sistema: str, pergunta: str,
                             ferramentas: list[dict]) -> RespostaFerramentas:
        raise NotImplementedError


def _ler_config(nome: str) -> str | None:
    """Procura a configuração em: variável de ambiente/.env e depois st.secrets."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    valor = os.environ.get(nome)
    if valor:
        return valor
    try:
        import streamlit as st
        return st.secrets.get(nome)  # type: ignore[no-any-return]
    except Exception:
        return None


def chave_configurada() -> bool:
    chave = _ler_config("OPENAI_API_KEY")
    return bool(chave) and chave != "coloque_sua_chave_aqui"


class ClienteOpenAI(ClienteLLM):
    def __init__(self, chave: str, modelo: str = MODELO_PADRAO):
        from openai import OpenAI  # importado aqui para os testes rodarem sem rede
        self.cliente = OpenAI(api_key=chave)
        self.modelo = modelo
        self.usos: list[dict] = []  # consumo de cada chamada (para medir custo)

    def _registrar(self, tipo: str, resposta) -> None:
        u = resposta.usage
        detalhes = getattr(u, "completion_tokens_details", None)
        self.usos.append({
            "tipo": tipo,
            "entrada": u.prompt_tokens,
            "saida": u.completion_tokens,
            "raciocinio": getattr(detalhes, "reasoning_tokens", None),
            "fim": resposta.choices[0].finish_reason,
        })

    @staticmethod
    def _checar_corte(resposta) -> None:
        if resposta.choices[0].finish_reason == "length":
            raise RespostaCortada("A resposta do LLM passou do tamanho máximo permitido e foi "
                                  "interrompida. Tente uma pergunta mais simples.")

    def gerar_texto(self, sistema: str, usuario: str) -> str:
        resposta = self.cliente.chat.completions.create(
            model=self.modelo,
            messages=[{"role": "system", "content": sistema},
                      {"role": "user", "content": usuario}],
            max_completion_tokens=MAX_TOKENS_TEXTO,
        )
        self._registrar("texto", resposta)
        self._checar_corte(resposta)
        return resposta.choices[0].message.content or ""

    def escolher_ferramentas(self, sistema: str, pergunta: str,
                             ferramentas: list[dict]) -> RespostaFerramentas:
        tools = [{
            "type": "function",
            "function": {"name": f["nome"], "description": f["descricao"],
                         "parameters": f["parametros"]},
        } for f in ferramentas]
        resposta = self.cliente.chat.completions.create(
            model=self.modelo,
            messages=[{"role": "system", "content": sistema},
                      {"role": "user", "content": pergunta}],
            tools=tools,
            tool_choice="auto",
            max_completion_tokens=MAX_TOKENS_FERRAMENTAS,
        )
        self._registrar("ferramentas", resposta)
        self._checar_corte(resposta)
        msg = resposta.choices[0].message
        chamadas = []
        for tc in msg.tool_calls or []:
            try:
                argumentos = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                argumentos = {"_erro": "argumentos inválidos"}
            chamadas.append({"nome": tc.function.name, "argumentos": argumentos})
        return RespostaFerramentas(chamadas=chamadas, texto=msg.content)


def criar_cliente() -> ClienteLLM:
    """Cria o cliente do provedor configurado. Falha com mensagem clara se faltar a chave."""
    chave = _ler_config("OPENAI_API_KEY")
    if not chave or chave == "coloque_sua_chave_aqui":
        raise RuntimeError("Chave da API não encontrada. Defina OPENAI_API_KEY no arquivo .env "
                           "ou nos Secrets do Streamlit.")
    modelo = _ler_config("MODELO") or MODELO_PADRAO
    return ClienteOpenAI(chave, modelo)
