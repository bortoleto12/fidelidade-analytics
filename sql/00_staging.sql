-- =============================================================
-- 00 · STAGING — tipagem e camada base sobre os arquivos brutos
-- Executado pelo src/pipeline.py (DuckDB), a partir da raiz do repo
-- =============================================================

CREATE OR REPLACE TABLE stg_clientes AS
SELECT id_cliente,
       CAST(data_cadastro AS TIMESTAMP)      AS data_cadastro,
       uf, faixa_etaria, canal_aquisicao, id_dispositivo
FROM 'data/raw/clientes.parquet';

CREATE OR REPLACE TABLE stg_parceiros AS
SELECT * FROM 'data/raw/parceiros.parquet';

CREATE OR REPLACE TABLE stg_campanhas AS
SELECT * FROM 'data/raw/campanhas.parquet';

CREATE OR REPLACE TABLE stg_campanha_publico AS
SELECT * FROM 'data/raw/campanha_publico.parquet';

CREATE OR REPLACE TABLE stg_transacoes AS
SELECT t.*,
       t.pontos_base + t.pontos_bonus             AS pontos_total,
       DATE_TRUNC('month', t.data_hora)::DATE     AS mes
FROM 'data/raw/transacoes.parquet' t;

CREATE OR REPLACE TABLE stg_resgates AS
SELECT r.*,
       DATE_TRUNC('month', r.data_hora)::DATE     AS mes
FROM 'data/raw/resgates.parquet' r;

-- parâmetros do programa
CREATE OR REPLACE TABLE param AS
SELECT 0.01                       AS valor_ponto_reais,   -- custo de 1 ponto para o programa
       TIMESTAMP '2025-12-31 23:59:59' AS data_referencia;
