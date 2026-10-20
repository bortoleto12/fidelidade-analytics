"""
Executa a camada SQL (DuckDB) e exporta as tabelas analíticas (marts)
para data/processed/ — consumidas pelo notebook, pelo dashboard HTML e pelo app Streamlit.

Uso:
    python src/pipeline.py
"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd
from scipy.stats import norm

RAIZ = Path(__file__).resolve().parents[1]
SQL_DIR = RAIZ / "sql"
SAIDA = RAIZ / "data" / "processed"


def rodar_sql(con: duckdb.DuckDBPyConnection) -> None:
    for arq in sorted(SQL_DIR.glob("*.sql")):
        print(f"  ▸ {arq.name}")
        con.execute(arq.read_text(encoding="utf-8"))


def avaliar_antifraude(con) -> pd.DataFrame:
    """Compara os alertas com o gabarito (só existe porque os dados são sintéticos)."""
    partes = []
    for versao, col in [("v1 (regras R1–R5)", "alerta_v1"), ("v2 (+ R6 cadastros em lote)", "alerta")]:
        partes.append(con.sql(f"""
        WITH g AS (SELECT id_cliente, TRUE AS fraude FROM 'data/raw/gabarito_fraude.parquet'),
        a AS (SELECT a.id_cliente, a.{col} AS alerta, COALESCE(g.fraude, FALSE) AS fraude
              FROM mart_antifraude a LEFT JOIN g USING (id_cliente))
        SELECT '{versao}' AS versao, SUM((alerta AND fraude)::INT)          AS verdadeiros_positivos,
               SUM((alerta AND NOT fraude)::INT)      AS falsos_positivos,
               SUM((NOT alerta AND fraude)::INT)      AS falsos_negativos,
               (SELECT COUNT(*) FROM g)               AS fraudadores_reais,
               ROUND(SUM((alerta AND fraude)::INT) / NULLIF(SUM(alerta::INT), 0), 3) AS precisao,
               ROUND(SUM((alerta AND fraude)::INT) / (SELECT COUNT(*) FROM g), 3)   AS recall
        FROM a
        """).df())
    return pd.concat(partes, ignore_index=True)


def main() -> None:
    os.chdir(RAIZ)  # os SQLs usam caminhos relativos à raiz
    SAIDA.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    print("Executando SQL...")
    rodar_sql(con)

    # p-valor do teste de uplift (bicaudal)
    camp = con.table("mart_campanhas").df()
    camp["p_valor"] = (2 * (1 - norm.cdf(camp["z_score"].abs()))).round(4)
    camp["significativo_95"] = camp["p_valor"] < 0.05
    con.register("camp_df", camp)
    con.execute("CREATE OR REPLACE TABLE mart_campanhas AS SELECT * FROM camp_df")

    marts = ["mart_kpis_mensais", "mart_parceiros", "mart_rfm", "mart_rfm_resumo",
             "mart_coortes", "mart_retencao_canal", "mart_campanhas", "mart_antifraude"]
    print("Exportando marts...")
    for m in marts:
        df = con.table(m).df()
        df.to_csv(SAIDA / f"{m}.csv", index=False)
        print(f"  {m:<22} {len(df):>7,} linhas")

    av = avaliar_antifraude(con)
    av.to_csv(SAIDA / "avaliacao_antifraude.csv", index=False)
    print("\nAntifraude vs. gabarito:\n", av.to_string(index=False))
    print(f"\nOK → {SAIDA}")

    # dashboard HTML (docs/index.html) é regenerado com os marts novos
    from gerar_dashboard_html import main as gerar_html
    gerar_html()


if __name__ == "__main__":
    main()
