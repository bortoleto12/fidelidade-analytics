-- =============================================================
-- 02 · SEGMENTAÇÃO RFM (Recência, Frequência, Valor)
-- Janela: últimos 12 meses até a data de referência
-- =============================================================

CREATE OR REPLACE TABLE mart_rfm AS
WITH ref AS (SELECT data_referencia AS dr FROM param),
base AS (
    SELECT c.id_cliente, c.uf, c.faixa_etaria, c.canal_aquisicao, c.data_cadastro,
           MAX(t.data_hora)                                   AS ultima_compra,
           COUNT(t.id_transacao) FILTER (WHERE t.data_hora > (SELECT dr FROM ref) - INTERVAL 365 DAY)
                                                              AS frequencia_12m,
           COALESCE(SUM(t.valor_compra) FILTER (WHERE t.data_hora > (SELECT dr FROM ref) - INTERVAL 365 DAY), 0)
                                                              AS valor_12m
    FROM stg_clientes c
    LEFT JOIN stg_transacoes t USING (id_cliente)
    GROUP BY ALL
),
metricas AS (
    SELECT *,
           DATE_DIFF('day', ultima_compra, (SELECT dr FROM ref)) AS recencia_dias
    FROM base
    WHERE ultima_compra IS NOT NULL
),
notas AS (
    SELECT *,
           -- recência: quanto MENOR, melhor → ordem decrescente
           NTILE(5) OVER (ORDER BY recencia_dias DESC, id_cliente) AS r,
           NTILE(5) OVER (ORDER BY frequencia_12m, id_cliente)     AS f,
           NTILE(5) OVER (ORDER BY valor_12m, id_cliente)          AS m
    FROM metricas
)
SELECT *,
       r::VARCHAR || f::VARCHAR || m::VARCHAR AS rfm_codigo,
       CASE
           WHEN DATE_DIFF('day', data_cadastro, (SELECT dr FROM ref)) <= 60
                AND r >= 4                       THEN 'Novos'
           WHEN r >= 4 AND f >= 4 AND m >= 4     THEN 'Campeões'
           WHEN r >= 3 AND f >= 3                THEN 'Leais'
           WHEN r >= 4 AND f <= 2                THEN 'Promissores'
           WHEN r = 3  AND f <= 2                THEN 'Precisam de atenção'
           WHEN r = 2  AND f >= 3                THEN 'Em risco'
           WHEN r = 2                            THEN 'Hibernando'
           ELSE                                       'Perdidos'
       END AS segmento
FROM notas
ORDER BY id_cliente;

CREATE OR REPLACE TABLE mart_rfm_resumo AS
SELECT segmento,
       COUNT(*)                                        AS clientes,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct_clientes,
       ROUND(SUM(valor_12m), 2)                        AS gmv_12m,
       ROUND(SUM(valor_12m) * 100.0 / SUM(SUM(valor_12m)) OVER (), 1) AS pct_gmv_12m,
       ROUND(AVG(recencia_dias), 0)                    AS recencia_media_dias,
       ROUND(AVG(frequencia_12m), 1)                   AS frequencia_media_12m,
       ROUND(AVG(valor_12m), 2)                        AS valor_medio_12m
FROM mart_rfm
GROUP BY segmento
ORDER BY gmv_12m DESC;
