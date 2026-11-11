"""Funções expostas ao LLM (function calling).

O LLM só ESCOLHE qual ferramenta usar e com quais argumentos.
Quem executa e valida é este código. Os números saem sempre do Python.
"""

from __future__ import annotations

import pandas as pd

from src import abteste, metricas

CIDADES = ["Belo Horizonte", "Curitiba", "Porto Alegre", "Recife", "Rio de Janeiro", "São Paulo"]
CANAIS = ["anúncio", "indicação", "orgânico"]

FERRAMENTAS = [
    {
        "nome": "funil",
        "descricao": ("Calcula o funil de conversão (cadastro → documentos → aprovado → "
                      "1ª entrega → 5 entregas em 30 dias): quantidade, % sobre o cadastro, "
                      "% sobre a etapa anterior e queda. Pode filtrar por cidade, canal e grupo."),
        "parametros": {
            "type": "object",
            "properties": {
                "cidade": {"type": "string", "enum": CIDADES},
                "canal": {"type": "string", "enum": CANAIS},
                "grupo": {"type": "string", "enum": ["A", "B"],
                          "description": "A = controle; B = campanha de bônus por metas"},
            },
            "additionalProperties": False,
        },
    },
    {
        "nome": "segmentar",
        "descricao": "Calcula o mesmo funil separado por cidade, por canal ou por grupo (A/B).",
        "parametros": {
            "type": "object",
            "properties": {"por": {"type": "string", "enum": list(metricas.SEGMENTOS_VALIDOS)}},
            "required": ["por"],
            "additionalProperties": False,
        },
    },
    {
        "nome": "teste_ab",
        "descricao": ("Teste A/B de duas proporções (B − A): taxas, diferença em pontos "
                      "percentuais, intervalo de confiança de 95%, p-valor e conclusão. "
                      "Pode ser o total (todas as cidades juntas), uma cidade específica, ou "
                      "por_cidade=true para receber o total E o resultado de cada uma das 6 "
                      "cidades de uma vez (use para comparar cidades)."),
        "parametros": {
            "type": "object",
            "properties": {
                "metrica": {"type": "string", "enum": list(abteste.METRICAS),
                            "description": "; ".join(f"{k} = {v[0]}"
                                                     for k, v in abteste.METRICAS.items())},
                "cidade": {"type": "string", "enum": CIDADES},
                "por_cidade": {"type": "boolean",
                               "description": "true = total + resultado separado de cada cidade"},
            },
            "required": ["metrica"],
            "additionalProperties": False,
        },
    },
]


def _validar(nome: str, argumentos: dict) -> str | None:
    """Confere nome e argumentos contra o esquema. Devolve mensagem de erro ou None."""
    esquema = next((f["parametros"] for f in FERRAMENTAS if f["nome"] == nome), None)
    if esquema is None:
        return f"Ferramenta desconhecida: {nome!r}."
    if not isinstance(argumentos, dict):
        return "Argumentos devem ser um objeto."
    props = esquema["properties"]
    for chave, valor in argumentos.items():
        if chave not in props:
            return f"Argumento não permitido: {chave!r}."
        if "enum" in props[chave] and valor not in props[chave]["enum"]:
            return f"Valor inválido para {chave!r}: {valor!r}."
        if props[chave].get("type") == "boolean" and not isinstance(valor, bool):
            return f"Valor inválido para {chave!r}: deve ser true ou false."
    for obrigatorio in esquema.get("required", []):
        if obrigatorio not in argumentos:
            return f"Falta o argumento obrigatório {obrigatorio!r}."
    return None


def executar(nome: str, argumentos: dict, df: pd.DataFrame) -> dict:
    """Executa a ferramenta pedida pelo LLM. Erros viram {'erro': ...}, nunca exceção."""
    erro = _validar(nome, argumentos)
    if erro:
        return {"erro": erro}
    if nome == "funil":
        sub = df
        for coluna in ("cidade", "canal", "grupo"):
            if coluna in argumentos:
                sub = sub[sub[coluna] == argumentos[coluna]]
        return {"filtros": argumentos or "nenhum", **metricas.funil(sub)}
    if nome == "segmentar":
        return metricas.segmentar(df, argumentos["por"])
    if nome == "teste_ab":
        if argumentos.get("por_cidade"):
            return {"total": abteste.teste_ab(df, argumentos["metrica"]),
                    "por_cidade": abteste.teste_ab_por_cidade(df, argumentos["metrica"])}
        return abteste.teste_ab(df, argumentos["metrica"], cidade=argumentos.get("cidade"))
    return {"erro": f"Ferramenta sem implementação: {nome!r}."}
