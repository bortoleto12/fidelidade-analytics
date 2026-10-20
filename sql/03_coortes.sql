-- =============================================================
-- 03 · RETENÇÃO POR COORTE
-- Coorte = mês de cadastro (a partir de 2024). Retenção no mês N =
-- % dos clientes da coorte que fizeram ao menos 1 compra N meses depois.
-- =============================================================

CREATE OR REPLACE TABLE mart_coortes AS
WITH coorte AS (
    SELECT id_cliente, DATE_TRUNC('month', data_cadastro)::DATE AS mes_coorte
    FROM stg_clientes
    WHERE data_cadastro >= DATE '2024-01-01'
),
atividade AS (
    SELECT DISTINCT id_cliente, mes FROM stg_transacoes
),
tamanho AS (
    SELECT mes_coorte, COUNT(*) AS clientes_coorte FROM coorte GROUP BY 1
)
SELECT c.mes_coorte,
       DATE_DIFF('month', c.mes_coorte, a.mes)               AS mes_desde_cadastro,
       t.clientes_coorte,
       COUNT(DISTINCT a.id_cliente)                          AS clientes_ativos,
       ROUND(COUNT(DISTINCT a.id_cliente) * 1.0 / t.clientes_coorte, 4) AS taxa_retencao
FROM coorte c
JOIN atividade a USING (id_cliente)
JOIN tamanho  t USING (mes_coorte)
WHERE a.mes >= c.mes_coorte
GROUP BY 1, 2, 3
ORDER BY 1, 2;

-- Retenção média por canal de aquisição (mês 3 e mês 6)
CREATE OR REPLACE TABLE mart_retencao_canal AS
WITH coorte AS (
    SELECT id_cliente, canal_aquisicao, DATE_TRUNC('month', data_cadastro)::DATE AS mes_coorte
    FROM stg_clientes
    WHERE data_cadastro BETWEEN DATE '2024-01-01' AND DATE '2025-06-30'  -- coortes com 6+ meses de vida
),
ativ AS (SELECT DISTINCT id_cliente, mes FROM stg_transacoes)
SELECT canal_aquisicao,
       COUNT(DISTINCT c.id_cliente) AS clientes,
       ROUND(COUNT(DISTINCT CASE WHEN DATE_DIFF('month', mes_coorte, a.mes) = 3 THEN c.id_cliente END)
             * 1.0 / COUNT(DISTINCT c.id_cliente), 4) AS retencao_m3,
       ROUND(COUNT(DISTINCT CASE WHEN DATE_DIFF('month', mes_coorte, a.mes) = 6 THEN c.id_cliente END)
             * 1.0 / COUNT(DISTINCT c.id_cliente), 4) AS retencao_m6
FROM coorte c
LEFT JOIN ativ a USING (id_cliente)
GROUP BY 1
ORDER BY retencao_m6 DESC;
