"""
Dashboard do Programa de Fidelidade — Streamlit
Rodar localmente:  streamlit run app/app.py
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

P = Path(__file__).resolve().parents[1] / "data" / "processed"
AZUL, LARANJA, CINZA = "#2a78d6", "#eb6834", "#a9a8a2"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

st.set_page_config(page_title="Programa de Fidelidade · Analytics", page_icon="📊", layout="wide")


@st.cache_data
def carregar():
    d = {
        "kpis": pd.read_csv(P / "mart_kpis_mensais.csv", parse_dates=["mes"]),
        "parceiros": pd.read_csv(P / "mart_parceiros.csv", parse_dates=["mes"]),
        "rfm": pd.read_csv(P / "mart_rfm_resumo.csv"),
        "rfm_cli": pd.read_csv(P / "mart_rfm.csv"),
        "coortes": pd.read_csv(P / "mart_coortes.csv", parse_dates=["mes_coorte"]),
        "canal": pd.read_csv(P / "mart_retencao_canal.csv"),
        "camp": pd.read_csv(P / "mart_campanhas.csv"),
        "fraude": pd.read_csv(P / "mart_antifraude.csv"),
        "aval": pd.read_csv(P / "avaliacao_antifraude.csv"),
    }
    return d


def brl(v):
    if abs(v) >= 1e6:
        return f"R$ {v/1e6:,.1f} mi".replace(".", ",")
    if abs(v) >= 1e3:
        return f"R$ {v/1e3:,.0f} mil".replace(",", ".")
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def mes_pt(d):
    return f"{MESES[d.month - 1]}/{d:%y}"


def layout(fig, h=360):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified",
                      legend=dict(orientation="h", y=1.08, x=0), plot_bgcolor="rgba(0,0,0,0)")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.2)")
    return fig


d = carregar()
st.title("📊 Programa de Fidelidade · Analytics")
st.caption("Dados 100% sintéticos · SQL (DuckDB) + Python · por Bianca Bortoleto")

aba = st.tabs(["Visão geral", "Segmentos RFM", "Retenção", "Campanhas", "Antifraude"])

# ---------------------------------------------------------------- Visão geral
with aba[0]:
    k = d["kpis"]
    meses = list(k.mes)
    ini, fim = st.select_slider("Período", options=meses, value=(meses[0], meses[-1]), format_func=mes_pt)
    f = k[(k.mes >= ini) & (k.mes <= fim)]
    n = len(f)
    ant = k[(k.mes < ini)].tail(n)  # período anterior de mesmo tamanho

    def delta(atual, anterior):
        return f"{(atual / anterior - 1):+.0%} vs. período anterior" if len(ant) == n and anterior else None

    c = st.columns(4)
    c[0].metric("GMV", brl(f.gmv.sum()), delta(f.gmv.sum(), ant.gmv.sum()))
    c[1].metric("Novos cadastros", f"{f.novos_clientes.sum():,}".replace(",", "."),
                delta(f.novos_clientes.sum(), ant.novos_clientes.sum()))
    c[2].metric("Ticket médio", brl(f.gmv.sum() / f.transacoes.sum()))
    c[3].metric("Passivo de pontos (fim do período)", brl(f.passivo_reais.iloc[-1]))

    col1, col2 = st.columns([3, 2])
    with col1:
        st.subheader("GMV mensal")
        fig = px.line(f, x="mes", y="gmv", markers=True, color_discrete_sequence=[AZUL])
        fig.update_traces(hovertemplate="%{y:,.0f}")
        st.plotly_chart(layout(fig).update_yaxes(title=None, tickprefix="R$ ").update_xaxes(title=None),
                        width="stretch")
    with col2:
        st.subheader("GMV por categoria de parceiro")
        pc = d["parceiros"]
        pc = pc[(pc.mes >= ini) & (pc.mes <= fim)].groupby("categoria", as_index=False).gmv.sum().sort_values("gmv")
        fig = px.bar(pc, x="gmv", y="categoria", orientation="h", color_discrete_sequence=[AZUL])
        fig.update_traces(hovertemplate="R$ %{x:,.0f}<extra></extra>")
        st.plotly_chart(layout(fig).update_layout(hovermode="closest").update_xaxes(title=None)
                        .update_yaxes(title=None), width="stretch")

    st.subheader("Clientes ativos x novos cadastros")
    fig = go.Figure()
    fig.add_bar(x=f.mes, y=f.clientes_ativos, name="Clientes ativos", marker_color=AZUL)
    fig.add_bar(x=f.mes, y=f.novos_clientes, name="Novos cadastros", marker_color=CINZA)
    st.plotly_chart(layout(fig, 300).update_layout(barmode="group"), width="stretch")

# ---------------------------------------------------------------- RFM
with aba[1]:
    r = d["rfm"]
    st.markdown("Notas de 1 a 5 em **Recência**, **Frequência** e **Valor** (últimos 12 meses) → segmentos acionáveis.")
    col1, col2 = st.columns([3, 2])
    with col1:
        long = r.melt(id_vars="segmento", value_vars=["pct_clientes", "pct_gmv_12m"], var_name="m", value_name="pct")
        long["m"] = long.m.map({"pct_clientes": "% dos clientes", "pct_gmv_12m": "% do GMV (12m)"})
        fig = px.bar(long, x="pct", y="segmento", color="m", barmode="group", orientation="h",
                     color_discrete_map={"% dos clientes": CINZA, "% do GMV (12m)": AZUL},
                     category_orders={"segmento": list(r.sort_values("gmv_12m", ascending=False).segmento)})
        fig.update_traces(hovertemplate="%{x:.1f}%<extra></extra>")
        st.plotly_chart(layout(fig, 420).update_layout(hovermode="closest", legend_title=None)
                        .update_xaxes(title=None, ticksuffix="%").update_yaxes(title=None), width="stretch")
    with col2:
        st.dataframe(r[["segmento", "clientes", "recencia_media_dias", "frequencia_media_12m", "valor_medio_12m"]]
                     .rename(columns={"recencia_media_dias": "recência (dias)", "frequencia_media_12m": "compras/ano",
                                      "valor_medio_12m": "R$/ano"}),
                     hide_index=True, width="stretch")
    seg = st.selectbox("Ver clientes do segmento", r.segmento)
    st.dataframe(d["rfm_cli"].query("segmento == @seg")
                 [["id_cliente", "uf", "canal_aquisicao", "recencia_dias", "frequencia_12m", "valor_12m", "rfm_codigo"]]
                 .sort_values("valor_12m", ascending=False).head(200), hide_index=True, width="stretch")
    st.caption("Exibindo até 200 clientes, ordenados por valor.")

# ---------------------------------------------------------------- Retenção
with aba[2]:
    co = d["coortes"]
    mat = co[co.mes_desde_cadastro <= 12].pivot(index="mes_coorte", columns="mes_desde_cadastro", values="taxa_retencao")
    fig = px.imshow(mat.values * 100, x=[str(c) for c in mat.columns], y=[mes_pt(i) for i in mat.index],
                    color_continuous_scale=SEQ, zmin=20, zmax=100, text_auto=".0f", aspect="auto")
    fig.update_traces(hovertemplate="Coorte %{y} · mês %{x}: %{z:.0f}%<extra></extra>")
    fig.update_layout(coloraxis_colorbar=dict(ticksuffix="%", title=None))
    st.subheader("Retenção por coorte de cadastro (%)")
    st.plotly_chart(layout(fig, 620).update_layout(hovermode="closest")
                    .update_xaxes(title="Meses desde o cadastro"), width="stretch")
    st.subheader("Retenção por canal de aquisição")
    ca = d["canal"].melt(id_vars="canal_aquisicao", value_vars=["retencao_m3", "retencao_m6"], var_name="m")
    ca["m"] = ca.m.map({"retencao_m3": "Mês 3", "retencao_m6": "Mês 6"})
    fig = px.bar(ca, x="canal_aquisicao", y="value", color="m", barmode="group",
                 color_discrete_map={"Mês 3": CINZA, "Mês 6": AZUL})
    fig.update_traces(hovertemplate="%{y:.0%}<extra></extra>")
    st.plotly_chart(layout(fig, 320).update_layout(hovermode="closest", legend_title=None)
                    .update_yaxes(title=None, tickformat=".0%").update_xaxes(title=None), width="stretch")

# ---------------------------------------------------------------- Campanhas
with aba[3]:
    cp = d["camp"].copy()
    st.markdown("Cada campanha teve **20% do público como grupo de controle**. "
                "O uplift é a diferença de conversão tratamento − controle; ROI considera 20% de margem sobre o GMV incremental.")
    so_sig = st.toggle("Mostrar só campanhas com efeito significativo (p < 0,05)")
    if so_sig:
        cp = cp[cp.significativo_95]
    c = st.columns(3)
    c[0].metric("GMV incremental total", brl(cp.gmv_incremental.sum()))
    c[1].metric("Custo total", brl(cp.custo_campanha.sum()))
    c[2].metric("ROI consolidado", f"{(cp.gmv_incremental.sum()*0.2 - cp.custo_campanha.sum())/cp.custo_campanha.sum():.1f}x".replace(".", ","))
    cp["Resultado"] = cp.significativo_95.map({True: "Significativo", False: "Sem efeito comprovado"})
    fig = px.scatter(cp, x="uplift_pp", y="roi", size="n_trat", color="Resultado", hover_name="nome_campanha",
                     color_discrete_map={"Significativo": AZUL, "Sem efeito comprovado": CINZA}, size_max=40)
    fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>Uplift: %{x:.1%}<br>ROI: %{y:.1f}x<extra></extra>")
    fig.add_hline(y=0, line_color="gray", line_width=1)
    st.plotly_chart(layout(fig, 400).update_layout(hovermode="closest", legend_title=None)
                    .update_xaxes(title="Uplift na conversão", tickformat=".0%", showgrid=True,
                                  gridcolor="rgba(128,128,128,0.2)")
                    .update_yaxes(title="ROI", ticksuffix="x"), width="stretch")
    st.dataframe(cp[["nome_campanha", "n_trat", "n_ctrl", "conversao_tratamento", "conversao_controle",
                     "uplift_pp", "p_valor", "gmv_incremental", "custo_campanha", "roi"]],
                 hide_index=True, width="stretch",
                 column_config={
                     "conversao_tratamento": st.column_config.NumberColumn("conv. tratamento", format="percent"),
                     "conversao_controle": st.column_config.NumberColumn("conv. controle", format="percent"),
                     "uplift_pp": st.column_config.NumberColumn("uplift", format="percent"),
                     "gmv_incremental": st.column_config.NumberColumn("GMV incremental", format="R$ %.0f"),
                     "custo_campanha": st.column_config.NumberColumn("custo", format="R$ %.0f"),
                     "roi": st.column_config.NumberColumn("ROI", format="%.1fx"),
                 })

# ---------------------------------------------------------------- Antifraude
with aba[4]:
    fr, av = d["fraude"], d["aval"]
    st.markdown("Score por regras explicáveis. **Score ≥ 3 → alerta** para revisão manual.")
    v2 = av.iloc[-1]
    c = st.columns(4)
    c[0].metric("Contas em alerta", int(fr.alerta.sum()))
    c[1].metric("Pontos resgatados em alerta", f"{int(fr[fr.alerta].pontos_resgatados.sum()):,}".replace(",", "."))
    c[2].metric("Precisão (v2)", f"{v2.precisao:.0%}", f"{v2.precisao - av.iloc[0].precisao:+.0%} vs. v1")
    c[3].metric("Recall (v2)", f"{v2.recall:.0%}", f"{v2.recall - av.iloc[0].recall:+.0%} vs. v1")
    corte = st.slider("Score mínimo para alerta", 1, 7, 3)
    dist = fr.groupby("score_risco", as_index=False).size()
    dist["Situação"] = (dist.score_risco >= corte).map({True: "Em alerta", False: "Normal"})
    fig = px.bar(dist, x="score_risco", y="size", color="Situação", log_y=True,
                 color_discrete_map={"Em alerta": LARANJA, "Normal": CINZA})
    fig.update_traces(hovertemplate="Score %{x}: %{y} contas<extra></extra>")
    st.plotly_chart(layout(fig, 300).update_layout(hovermode="closest", legend_title=None)
                    .update_xaxes(title="Score de risco", dtick=1).update_yaxes(title="Contas (escala log)"),
                    width="stretch")
    regras = ["r1_disp_compartilhado", "r2_resgate_rapido", "r3_rajada_compras", "r4_esvaziou_saldo",
              "r5_ticket_atipico", "r6_cadastros_em_lote"]
    st.subheader("Fila de revisão")
    st.dataframe(fr[fr.score_risco >= corte][["id_cliente", "id_dispositivo", "contas_no_dispositivo",
                 "compras_72h", "dias_ate_1o_resgate", "pontos_resgatados", "score_risco"] + regras],
                 hide_index=True, width="stretch")
