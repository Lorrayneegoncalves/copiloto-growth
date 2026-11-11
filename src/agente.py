"""Orquestra LLM + ferramentas + validador.

Modo 1 (relatório): código calcula -> LLM escreve -> validador confere (1 nova tentativa).
Modo 2 (pergunta):  filtro de escopo -> LLM escolhe ferramentas -> código executa
                    -> LLM responde com base nos resultados -> validador confere.
"""

from __future__ import annotations

import json
import unicodedata
from datetime import date

import pandas as pd

from src import abteste, ferramentas, metricas, validador
from src.llm import ClienteLLM

REGRAS = """Você é um analista de growth que explica resultados para um time de negócio.
Regras obrigatórias:
- Responda em português do Brasil, em tom profissional e direto.
- Use APENAS os números fornecidos nos RESULTADOS. Copie-os como estão (com vírgula decimal).
  Não calcule números novos (nada de diferenças relativas, somas ou médias próprias).
- Nunca preveja resultados futuros.
- Sempre cite limites: os dados são simulados, o tamanho da amostra importa e correlação não é causa.
- Se o p-valor for alto (>= 0,05) ou o intervalo de confiança incluir zero, diga explicitamente
  que NÃO há evidência suficiente.
- Os resultados por cidade têm amostras menores; trate-os como indícios, não como prova.
Estilo:
- Escreva para pessoas de negócio. NUNCA use nomes técnicos de campos ou métricas do código
  (como taxa_pct, diferenca_pp, ic95_pp, p_valor, n, primeira_para_cinco). Diga, por exemplo,
  "taxa de 45,38%", "diferença de 2,47 pontos percentuais", "intervalo de confiança de 95%
  de 0,16 a 4,79 pontos", "p-valor de 0,036" e "1ª entrega → 5 entregas em 30 dias".
- Formato brasileiro: vírgula decimal e ponto de milhar (20.000; 45,38%).
- Seja conciso: priorize o que muda a decisão, sem listar todos os números."""

SECOES_RELATORIO = """Escreva um relatório curto em Markdown com exatamente estas seções:
## Resumo
(3 frases)
## O que os dados mostram
## Riscos e limites
## Recomendação
## Próximo teste sugerido
Use no máximo 350 palavras no total. Cite obrigatoriamente os itens de "destaques"
(por exemplo, cidades onde a diferença foi negativa).
Não escreva título geral nem cabeçalho: ele é adicionado pelo sistema."""

MENSAGEM_RECUSA = {
    "previsao": "Não faço previsões de resultados futuros. Posso explicar o que os dados "
                "simulados mostram até agora (funil, segmentos e teste A/B).",
    "dados_pessoais": "Não respondo sobre dados pessoais ou de pessoas específicas. "
                      "Trabalho apenas com números agregados.",
    "alterar_dados": "Não posso alterar, apagar ou inserir dados. O app é somente leitura.",
    "fora_do_escopo": "Essa pergunta está fora do escopo. Posso responder sobre o funil de "
                      "conversão, segmentos por cidade/canal e o teste A/B da campanha (simulada).",
}

_TERMOS_FORA = {
    "previsao": ["prever", "previsao", "preveja", "projecao", "projetar", "futuro", "proximo mes",
                 "proximos meses", "proximo ano", "ano que vem", "vai ter", "vao ter",
                 "quantos teremos", "estimativa para", "forecast"],
    "dados_pessoais": ["cpf", "rg ", "telefone", "e-mail", "email", "endereco",
                       "nome do entregador", "nome dos entregadores", "nomes dos entregadores",
                       "quem e o entregador", "quem sao os entregadores", "dados pessoais",
                       "id do entregador", "contato d"],
    "alterar_dados": ["alterar", "altere", "apagar", "apague", "deletar", "delete", "remover",
                      "remova", "excluir", "exclua", "inserir", "insira", "modificar",
                      "modifique", "atualizar os dados", "atualize os dados", "editar", "edite",
                      "mudar os dados", "mude os dados", "sobrescrever"],
}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split()) + " "


def checar_escopo(pergunta: str) -> str | None:
    """Filtro determinístico (sem LLM). Devolve o motivo da recusa ou None se estiver ok."""
    texto = _normalizar(pergunta)
    if not texto.strip():
        return "fora_do_escopo"
    for motivo, termos in _TERMOS_FORA.items():
        if any(t in texto for t in termos):
            return motivo
    return None


def formatar_ptbr(obj):
    """Converte números para texto no formato brasileiro (20.000; 45,38; 0,036).

    Assim o LLM só copia os números já formatados. O validador continua comparando
    com os valores numéricos originais.
    """
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, int):
        return f"{obj:,}".replace(",", ".")
    if isinstance(obj, float):
        texto = f"{obj:.4f}".rstrip("0").rstrip(".")
        return texto.replace(".", ",")
    if isinstance(obj, dict):
        return {k: formatar_ptbr(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [formatar_ptbr(v) for v in obj]
    return obj


def _json(obj) -> str:
    return json.dumps(formatar_ptbr(obj), ensure_ascii=False, indent=1)


def _escrever_validado(llm: ClienteLLM, sistema: str, usuario: str, resultados) -> dict:
    """Pede o texto, valida os números e tenta UMA vez de novo se algo não bater."""
    texto = llm.gerar_texto(sistema, usuario)
    checagem = validador.validar(texto, resultados)
    tentativas = 1
    if not checagem["ok"]:
        tentativas = 2
        correcao = (usuario + "\n\nATENÇÃO: sua resposta anterior usou números que não existem "
                    f"nos RESULTADOS: {', '.join(checagem['numeros_invalidos'])}. Reescreva "
                    "usando somente números presentes nos RESULTADOS.")
        texto = llm.gerar_texto(sistema, correcao)
        checagem = validador.validar(texto, resultados)
    aviso = None
    if not checagem["ok"]:
        aviso = ("Atenção: o texto contém números que não foram encontrados nos cálculos: "
                 f"{', '.join(checagem['numeros_invalidos'])}. Confira com as abas Funil e A/B.")
    return {"texto": texto, "tentativas": tentativas,
            "numeros_invalidos": checagem["numeros_invalidos"], "aviso": aviso}


# ----------------------------------------------------------------------------- modo 1
def destaques(por_cidade: dict) -> dict:
    """Pontos de atenção calculados pelo CÓDIGO (não dependem do LLM perceber)."""
    negativas = {c: r["diferenca_pp"] for c, r in por_cidade.items()
                 if r["diferenca_pp"] is not None and r["diferenca_pp"] < 0}
    com_evidencia = [c for c, r in por_cidade.items() if r["significativo"]]
    return {
        "metrica_principal": "1ª entrega → 5 entregas em 30 dias",
        "cidades_com_diferenca_negativa_pp": negativas,
        "cidades_com_evidencia_isolada": com_evidencia or "nenhuma",
        "observacao": ("O efeito não é uniforme entre cidades; um total positivo pode esconder "
                       "cidades onde a campanha não funciona." if negativas else ""),
    }


def dados_para_relatorio(df: pd.DataFrame) -> dict:
    """Tudo o que o LLM recebe no relatório: só números já calculados."""
    por_cidade = abteste.teste_ab_por_cidade(df, "primeira_para_cinco")
    return {
        "aviso": "Dados 100% simulados para demonstração.",
        "destaques": destaques(por_cidade),
        "funil_geral": metricas.funil(df),
        "teste_ab_geral": abteste.teste_ab(df, "primeira_para_cinco"),
        "teste_ab_por_cidade": por_cidade,
        "teste_ab_cadastro_para_cinco": abteste.teste_ab(df, "cadastro_para_cinco"),
        "funil_por_canal": metricas.segmentar(df, "canal"),
    }


def cabecalho_relatorio() -> str:
    return ("# Relatório da campanha de bônus por metas\n\n"
            "> ⚠️ **Dados simulados para demonstração.** Todos os números são fictícios, "
            "gerados por código. Não representam nenhuma empresa real.\n>\n"
            f"> Gerado em {date.today():%d/%m/%Y}. Números calculados em Python; "
            "texto escrito por um LLM e conferido por um validador automático.\n\n")


def gerar_relatorio(df: pd.DataFrame, llm: ClienteLLM) -> dict:
    dados = dados_para_relatorio(df)
    usuario = f"{SECOES_RELATORIO}\n\nRESULTADOS (calculados pelo código):\n{_json(dados)}"
    r = _escrever_validado(llm, REGRAS, usuario, dados)
    return {**r, "markdown": cabecalho_relatorio() + r["texto"], "dados": dados}


# ----------------------------------------------------------------------------- modo 2
SISTEMA_ESCOLHA = (
    "Você ajuda a analisar uma campanha SIMULADA de aquisição de entregadores. "
    "Para responder, escolha a MENOR quantidade de ferramentas necessária (funil, segmentar, "
    "teste_ab). Em perguntas sobre o teste A/B sem métrica definida, use apenas a métrica "
    "principal da campanha: primeira_para_cinco. "
    "Se a pergunta não puder ser respondida com essas ferramentas (ex.: previsões, dados "
    "pessoais, alterar dados, assuntos fora da campanha), NÃO chame ferramentas e responda "
    "apenas com a palavra FORA_DO_ESCOPO."
)

MAX_CHAMADAS = 4


def responder_pergunta(pergunta: str, df: pd.DataFrame, llm: ClienteLLM) -> dict:
    base = {"pergunta": pergunta, "resposta": None, "recusada": False, "motivo": None,
            "ferramentas_usadas": [], "numeros_invalidos": [], "aviso": None, "tentativas": 0}

    motivo = checar_escopo(pergunta)
    if motivo:
        return {**base, "recusada": True, "motivo": motivo, "resposta": MENSAGEM_RECUSA[motivo]}

    escolha = llm.escolher_ferramentas(SISTEMA_ESCOLHA, pergunta, ferramentas.FERRAMENTAS)
    if not escolha.chamadas:
        return {**base, "recusada": True, "motivo": "fora_do_escopo",
                "resposta": MENSAGEM_RECUSA["fora_do_escopo"]}

    usadas = []
    for chamada in escolha.chamadas[:MAX_CHAMADAS]:
        resultado = ferramentas.executar(chamada["nome"], chamada["argumentos"], df)
        usadas.append({"nome": chamada["nome"], "argumentos": chamada["argumentos"],
                       "resultado": resultado})

    resultados = [u["resultado"] for u in usadas]
    usuario = (f"PERGUNTA: {pergunta}\n\nRESULTADOS das ferramentas (calculados pelo código):\n"
               f"{_json(usadas)}\n\nResponda à pergunta em no máximo 120 palavras, com base "
               "apenas nesses resultados, terminando com uma frase curta sobre os limites.")
    r = _escrever_validado(llm, REGRAS, usuario, resultados)
    aviso = r["aviso"]
    ignoradas = len(escolha.chamadas) - MAX_CHAMADAS
    if ignoradas > 0:
        nota = (f"Atenção: o LLM pediu {len(escolha.chamadas)} consultas e só as {MAX_CHAMADAS} "
                "primeiras foram executadas; a resposta pode estar incompleta.")
        aviso = f"{aviso} {nota}" if aviso else nota
    return {**base, "resposta": r["texto"], "ferramentas_usadas": usadas,
            "numeros_invalidos": r["numeros_invalidos"], "aviso": aviso,
            "tentativas": r["tentativas"]}
