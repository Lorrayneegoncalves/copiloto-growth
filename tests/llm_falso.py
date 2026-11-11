"""LLM falso (mock) para os testes: devolve respostas pré-definidas, sem internet."""

from src.llm import ClienteLLM, RespostaFerramentas


class LLMFalso(ClienteLLM):
    def __init__(self, textos=None, chamadas=None):
        self.textos = list(textos or [])
        self.chamadas = chamadas or []
        self.pedidos_texto = []
        self.pedidos_ferramentas = 0

    def gerar_texto(self, sistema, usuario):
        self.pedidos_texto.append(usuario)
        return self.textos.pop(0) if self.textos else ""

    def escolher_ferramentas(self, sistema, pergunta, ferramentas):
        self.pedidos_ferramentas += 1
        return RespostaFerramentas(chamadas=self.chamadas, texto=None)


class LLMQueNaoPodeSerChamado(ClienteLLM):
    def gerar_texto(self, sistema, usuario):
        raise AssertionError("O LLM não deveria ter sido chamado")

    def escolher_ferramentas(self, sistema, pergunta, ferramentas):
        raise AssertionError("O LLM não deveria ter sido chamado")
