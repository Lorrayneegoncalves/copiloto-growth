"""Copiloto de Growth — interface Streamlit.

Rodar:  streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import agente, llm, simular_dados
from src.abteste import METRICAS, teste_ab, teste_ab_por_cidade
from src.metricas import funil, funil_para_tabela, segmentar

st.set_page_config(page_title="Copiloto de Growth", page_icon="📊", layout="wide")

AVISO = ("⚠️ **Dados simulados para demonstração.** Todos os números deste app são "
         "fictícios, gerados por código com efeitos definidos pela autora. "
         "Não representam nenhuma empresa real.")


@st.cache_data
def carregar_dados() -> pd.DataFrame:
    if not simular_dados.CAMINHO_CSV.exists():
        simular_dados.salvar(simular_dados.gerar())
    return pd.read_csv(simular_dados.CAMINHO_CSV)


def fmt_pct(x):
    return "—" if x is None else f"{x:.2f}%".replace(".", ",")


def fmt_pp(x):
    return "—" if x is None else f"{x:+.2f}".replace(".", ",") + " p.p."


def fmt_int(x):
    return f"{x:,}".replace(",", ".")


def tabela_br(tabela: pd.DataFrame, casas: int = 2):
    """Mostra números da tabela no formato brasileiro (20.000; 68,34)."""
    return tabela.style.format(decimal=",", thousands=".", precision=casas, na_rep="—")


# ----------------------------------------------------------------------------- topo
st.warning(AVISO)
st.title("📊 Copiloto de Growth")
st.caption("Análise de uma campanha (simulada) de aquisição de entregadores: "
           "funil de conversão e teste A/B. Grupo A = controle; grupo B = bônus por metas.")

df = carregar_dados()

aba_funil, aba_ab, aba_rel, aba_perg = st.tabs(
    ["🔻 Funil", "🧪 Teste A/B", "📝 Relatório", "💬 Pergunte à campanha"])

# ----------------------------------------------------------------------------- funil
with aba_funil:
    r = funil(df)
    etapas = r["etapas"]
    por_chave = {e["etapa"]: e for e in etapas}

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cadastros", fmt_int(r["total_cadastros"]))
    c2.metric("Fizeram a 1ª entrega", fmt_int(por_chave["primeira_entrega"]["quantidade"]))
    c3.metric("5 entregas em 30 dias", fmt_int(por_chave["cinco_entregas"]["quantidade"]))
    c4.metric("Conversão total", fmt_pct(por_chave["cinco_entregas"]["taxa_sobre_cadastro_pct"]))

    col_graf, col_tab = st.columns([1, 1])
    with col_graf:
        fig = go.Figure(go.Funnel(
            y=[e["nome"] for e in etapas],
            x=[e["quantidade"] for e in etapas],
            texttemplate="%{value:,} (%{percentInitial:.1%})",
        ))
        fig.update_layout(title="Funil geral", margin=dict(l=10, r=10, t=40, b=10), height=380,
                          separators=",.")
        st.plotly_chart(fig, width="stretch")
    with col_tab:
        st.markdown("**Conversão por etapa**")
        tabela = funil_para_tabela(r).rename(columns={
            "nome": "Etapa", "quantidade": "Pessoas",
            "taxa_sobre_cadastro_pct": "% do cadastro",
            "taxa_sobre_etapa_anterior_pct": "% da etapa anterior",
            "queda_vs_etapa_anterior_pct": "Queda vs anterior (%)",
        }).drop(columns="etapa")
        st.dataframe(tabela_br(tabela), hide_index=True, width="stretch")
        maior_queda = max(etapas[1:], key=lambda e: e["queda_vs_etapa_anterior_pct"])
        st.info(f"Maior queda: chegada em **{maior_queda['nome']}** "
                f"({fmt_pct(maior_queda['queda_vs_etapa_anterior_pct'])} não avançam).")

    st.divider()
    st.subheader("Funil por segmento")
    por = st.radio("Segmentar por", ["cidade", "canal"], horizontal=True,
                   format_func=str.capitalize)
    seg = segmentar(df, por)
    linhas = [
        {por: valor, "Etapa": e["nome"], "% do cadastro": e["taxa_sobre_cadastro_pct"],
         "% da etapa anterior": e["taxa_sobre_etapa_anterior_pct"], "Pessoas": e["quantidade"]}
        for valor, f in seg["segmentos"].items() for e in f["etapas"][1:]
    ]
    longo = pd.DataFrame(linhas)
    fig_seg = px.bar(longo, x="Etapa", y="% do cadastro", color=por, barmode="group",
                     title=f"% dos cadastros que chega a cada etapa, por {por}",
                     hover_data=["Pessoas", "% da etapa anterior"])
    fig_seg.update_layout(height=420, separators=",.", margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_seg, width="stretch")
    st.markdown("**Conversão em relação à etapa anterior (%)**")
    st.dataframe(tabela_br(longo.pivot(index=por, columns="Etapa", values="% da etapa anterior")
                           [[e["nome"] for e in etapas[1:]]]), width="stretch")

# ----------------------------------------------------------------------------- A/B
with aba_ab:
    metrica = st.selectbox("Métrica", list(METRICAS), format_func=lambda m: METRICAS[m][0])
    geral = teste_ab(df, metrica)

    st.subheader("Resultado geral (todas as cidades)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Grupo A (controle)", fmt_pct(geral["grupo_A"]["taxa_pct"]),
              help=f"{fmt_int(geral['grupo_A']['sucessos'])} de {fmt_int(geral['grupo_A']['n'])}")
    c2.metric("Grupo B (bônus)", fmt_pct(geral["grupo_B"]["taxa_pct"]),
              help=f"{fmt_int(geral['grupo_B']['sucessos'])} de {fmt_int(geral['grupo_B']['n'])}")
    c3.metric("Diferença (B − A)", fmt_pp(geral["diferenca_pp"]))
    c4.metric("p-valor", "—" if geral["p_valor"] is None
              else f"{geral['p_valor']:.4f}".replace(".", ","))
    if geral["ic95_pp"]:
        lo, hi = geral["ic95_pp"]
        st.markdown(f"Intervalo de confiança de 95% da diferença: **{fmt_pp(lo)} a {fmt_pp(hi)}**")
    (st.success if geral["significativo"] else st.info)(geral["conclusao"])
    for aviso in geral["avisos"]:
        st.warning(aviso)

    st.divider()
    st.subheader("Diferença B − A por cidade")
    por_cidade = teste_ab_por_cidade(df, metrica)
    linhas = []
    for cidade, res in {**por_cidade, "TOTAL": geral}.items():
        lo, hi = res["ic95_pp"] or (None, None)
        linhas.append({
            "Cidade": cidade,
            "n A": res["grupo_A"]["n"], "Taxa A (%)": res["grupo_A"]["taxa_pct"],
            "n B": res["grupo_B"]["n"], "Taxa B (%)": res["grupo_B"]["taxa_pct"],
            "Diferença (p.p.)": res["diferenca_pp"],
            "IC 95% mín": lo, "IC 95% máx": hi,
            "p-valor": res["p_valor"],
            "Evidência?": "Sim" if res["significativo"] else "Não",
            "Avisos": " ".join(res["avisos"]),
        })
    tab = pd.DataFrame(linhas)

    fig_ab = go.Figure(go.Scatter(
        x=tab["Diferença (p.p.)"], y=tab["Cidade"], mode="markers",
        marker=dict(size=11, color=["#d62728" if c == "TOTAL" else "#1f77b4"
                                    for c in tab["Cidade"]]),
        error_x=dict(type="data", symmetric=False,
                     array=tab["IC 95% máx"] - tab["Diferença (p.p.)"],
                     arrayminus=tab["Diferença (p.p.)"] - tab["IC 95% mín"],
                     color="#888888", thickness=2),
        hovertemplate="%{y}: %{x:.2f} p.p.<extra></extra>",
    ))
    fig_ab.add_vline(x=0, line_dash="dash", line_color="gray")
    fig_ab.update_layout(
        title="Ponto = diferença; barra = intervalo de confiança de 95%. "
              "Se a barra cruza o zero, não há evidência suficiente.",
        xaxis_title="Diferença B − A (pontos percentuais)",
        yaxis=dict(autorange="reversed"), height=420, separators=",.", margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_ab, width="stretch")
    st.dataframe(tabela_br(tab).format({"p-valor": lambda v: "—" if pd.isna(v)
                                        else f"{v:.4f}".replace(".", ",")}),
                 hide_index=True, width="stretch")

    negativas = [c for c, r in por_cidade.items() if (r["diferenca_pp"] or 0) < 0]
    sem_evidencia = [c for c, r in por_cidade.items() if not r["significativo"]]
    if negativas:
        st.warning(f"O efeito não é uniforme: a diferença foi **negativa** em "
                   f"{', '.join(negativas)}. Um resultado total positivo pode esconder "
                   f"cidades onde a campanha não funciona.")
    if len(sem_evidencia) == len(por_cidade):
        st.info("Nenhuma cidade, isoladamente, tem evidência suficiente de diferença "
                "(todos os intervalos cruzam o zero).")

    st.caption(
        "Cuidados na leitura: (1) dados simulados; (2) olhar várias cidades aumenta a chance "
        "de achar uma diferença só por acaso — resultados por cidade são indícios, não provas; "
        "(3) cada cidade tem amostra menor que o total, então os intervalos são mais largos."
    )


# ----------------------------------------------------------------------------- LLM
def obter_llm():
    """Cria o cliente do LLM ou mostra como configurar a chave."""
    if not llm.chave_configurada():
        st.info("Para usar esta aba, configure a chave da API: copie `.env.example` para `.env` "
                "e preencha `OPENAI_API_KEY` (ou use os Secrets do Streamlit Cloud).")
        return None
    try:
        return llm.criar_cliente()
    except Exception as e:  # noqa: BLE001
        st.error(f"Não foi possível iniciar o LLM: {e}")
        return None


def mostrar_validacao(r: dict):
    if r["aviso"]:
        st.warning(r["aviso"])
    elif r["tentativas"] == 2:
        st.success("✅ Validador: a 1ª versão tinha números sem origem; a 2ª tentativa "
                   "usa apenas números calculados pelo código.")
    else:
        st.success("✅ Validador: todos os números do texto vêm dos cálculos do código.")


LIMITE_PERGUNTAS_POR_VISITA = 10


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def relatorio_do_dia(_df: pd.DataFrame, _cliente) -> dict:
    """Gera o relatório uma vez e reaproveita por 24 h (os dados são fixos; economiza API)."""
    return agente.gerar_relatorio(_df, _cliente)


# ----------------------------------------------------------------------------- relatório
with aba_rel:
    st.markdown("O código calcula funil, teste A/B e segmentos; **só esses números** vão para o "
                "LLM, que escreve o texto. Um validador confere se cada número do texto existe "
                "nos cálculos.")
    cliente = obter_llm()
    if cliente and st.button("Gerar relatório", type="primary"):
        with st.spinner("Calculando e escrevendo o relatório..."):
            try:
                st.session_state["relatorio"] = relatorio_do_dia(df, cliente)
            except Exception as e:  # noqa: BLE001
                st.error(f"Erro ao chamar o LLM: {e}")
    rel = st.session_state.get("relatorio")
    if rel:
        mostrar_validacao(rel)
        st.caption("Para economizar a API, o relatório é gerado uma vez e reaproveitado por 24 h.")
        st.markdown(rel["markdown"])
        st.download_button("⬇️ Baixar relatório (.md)", rel["markdown"],
                           file_name="relatorio_campanha_simulada.md", mime="text/markdown")
        with st.expander("Números enviados ao LLM"):
            st.json(rel["dados"], expanded=False)

# ----------------------------------------------------------------------------- perguntas
EXEMPLOS = [
    "O grupo B foi melhor que o A no geral?",
    "Como foi o teste A/B em Porto Alegre?",
    "Qual canal converte melhor até a primeira entrega?",
    "Quantos entregadores teremos no próximo mês?",
]

with aba_perg:
    st.markdown("Pergunte em português. O LLM escolhe entre 3 ferramentas (`funil`, "
                "`segmentar`, `teste_ab`); o código executa e o LLM explica o resultado. "
                "Previsões, dados pessoais e alteração de dados são recusados.")
    cliente_p = obter_llm()
    if cliente_p:
        st.caption("Exemplos:")
        cols = st.columns(len(EXEMPLOS))
        for col, ex in zip(cols, EXEMPLOS):
            if col.button(ex, width="stretch"):
                st.session_state["pergunta"] = ex
        pergunta = st.text_input("Sua pergunta", key="pergunta")
        usadas = st.session_state.get("perguntas_feitas", 0)
        restantes = LIMITE_PERGUNTAS_POR_VISITA - usadas
        contador = st.empty()
        if st.button("Perguntar", type="primary", disabled=restantes <= 0) and pergunta.strip():
            st.session_state["perguntas_feitas"] = usadas + 1
            with st.spinner("Consultando as ferramentas..."):
                try:
                    st.session_state["resposta"] = agente.responder_pergunta(
                        pergunta, df, cliente_p)
                except Exception as e:  # noqa: BLE001
                    st.error(f"Erro ao chamar o LLM: {e}")
        restantes = LIMITE_PERGUNTAS_POR_VISITA - st.session_state.get("perguntas_feitas", 0)
        contador.caption(f"Perguntas restantes nesta visita: {max(restantes, 0)} de "
                         f"{LIMITE_PERGUNTAS_POR_VISITA} (limite para controlar o custo da API).")
        resp = st.session_state.get("resposta")
        if resp:
            st.markdown(f"**Pergunta:** {resp['pergunta']}")
            if resp["recusada"]:
                st.error(f"🚫 {resp['resposta']}")
            else:
                mostrar_validacao(resp)
                st.markdown(resp["resposta"])
                with st.expander("Ferramentas usadas e números retornados"):
                    for u in resp["ferramentas_usadas"]:
                        st.markdown(f"`{u['nome']}({u['argumentos']})`")
                        st.json(u["resultado"], expanded=False)
