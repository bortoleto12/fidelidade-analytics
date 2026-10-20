"""
Gera o dashboard interativo em HTML (arquivo único, sem servidor) a partir dos marts.

Saída: docs/index.html  → pode ser aberto direto no navegador ou publicado no GitHub Pages.
A biblioteca Plotly.js é embutida no arquivo, então ele funciona até offline.

Uso:
    python src/gerar_dashboard_html.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly

RAIZ = Path(__file__).resolve().parents[1]
P = RAIZ / "data" / "processed"
TEMPLATE = RAIZ / "src" / "dashboard_template.html"
SAIDA = RAIZ / "docs" / "index.html"


def registros(df: pd.DataFrame, decimais: int = 4) -> list[dict]:
    df = df.copy()
    for c in df.select_dtypes("datetime").columns:
        df[c] = df[c].dt.strftime("%Y-%m-%d")
    for c in df.select_dtypes("float").columns:
        df[c] = df[c].round(decimais)
    return json.loads(df.to_json(orient="records", force_ascii=False))


def montar_dados() -> dict:
    kpis = pd.read_csv(P / "mart_kpis_mensais.csv")
    parceiros = (pd.read_csv(P / "mart_parceiros.csv")
                 .groupby(["mes", "categoria"], as_index=False)[["gmv", "transacoes"]].sum())
    rfm_cli = pd.read_csv(P / "mart_rfm.csv")
    # agregado por segmento x canal x faixa etária → permite filtrar o RFM no navegador
    rfm = (rfm_cli.groupby(["segmento", "canal_aquisicao", "faixa_etaria"], as_index=False)
           .agg(clientes=("id_cliente", "count"), gmv_12m=("valor_12m", "sum"),
                soma_recencia=("recencia_dias", "sum"), soma_freq=("frequencia_12m", "sum")))
    coortes = pd.read_csv(P / "mart_coortes.csv")
    coortes = coortes[coortes.mes_desde_cadastro <= 12][["mes_coorte", "mes_desde_cadastro",
                                                          "clientes_coorte", "taxa_retencao"]]
    canal = pd.read_csv(P / "mart_retencao_canal.csv")
    camp = pd.read_csv(P / "mart_campanhas.csv")
    aval = pd.read_csv(P / "avaliacao_antifraude.csv")
    fr = pd.read_csv(P / "mart_antifraude.csv")
    dist = fr.groupby("score_risco", as_index=False).agg(contas=("id_cliente", "count"),
                                                          pontos=("pontos_resgatados", "sum"))
    fila = fr[fr.score_risco >= 2][[
        "id_cliente", "id_dispositivo", "contas_no_dispositivo", "janela_cadastros_dias", "compras_72h",
        "dias_ate_1o_resgate", "pontos_resgatados", "score_risco", "r1_disp_compartilhado",
        "r2_resgate_rapido", "r3_rajada_compras", "r4_esvaziou_saldo", "r5_ticket_atipico",
        "r6_cadastros_em_lote"]]
    return {
        "kpis": registros(kpis), "parceiros": registros(parceiros, 2), "rfm": registros(rfm, 2),
        "coortes": registros(coortes), "canal": registros(canal), "campanhas": registros(camp),
        "aval": registros(aval), "fraude_dist": registros(dist), "fraude_fila": registros(fila, 2),
        "valor_ponto": 0.01,
    }


def main() -> None:
    dados = json.dumps(montar_dados(), ensure_ascii=False, separators=(",", ":"))
    plotly_js = (Path(plotly.__file__).parent / "package_data" / "plotly.min.js").read_text(encoding="utf-8")
    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("/*__DADOS__*/null", dados).replace("/*__PLOTLY__*/", plotly_js)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(html, encoding="utf-8")
    print(f"OK → {SAIDA}  ({SAIDA.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
