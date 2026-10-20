-- =============================================================
-- 04 · EFICÁCIA DE CAMPANHAS (teste A/B com grupo de controle)
-- Compara TRATAMENTO (recebeu a oferta) x CONTROLE (não recebeu)
-- na janela da campanha e no parceiro-alvo.
--   conversão   = % de clientes com ≥1 compra na janela
--   uplift      = diferença tratamento − controle
--   GMV incremental = (GMV/cliente trat − GMV/cliente ctrl) × nº tratados
--   ROI         = (GMV incremental × margem − custo) / custo
-- =============================================================

CREATE OR REPLACE TABLE mart_campanhas AS
WITH resultado_cliente AS (
    SELECT p.id_campanha, p.id_cliente, p.grupo,
           COUNT(t.id_transacao)             AS compras,
           COALESCE(SUM(t.valor_compra), 0)  AS gmv,
           COALESCE(SUM(t.pontos_bonus), 0)  AS pontos_bonus
    FROM stg_campanha_publico p
    JOIN stg_campanhas c USING (id_campanha)
    LEFT JOIN stg_transacoes t
           ON t.id_cliente = p.id_cliente
          AND t.data_hora BETWEEN c.data_inicio AND c.data_fim
          AND (c.id_parceiro_alvo = 0 OR t.id_parceiro = c.id_parceiro_alvo)
    GROUP BY ALL
),
grupo AS (
    SELECT id_campanha, grupo,
           COUNT(*)                                   AS clientes,
           AVG(CASE WHEN compras > 0 THEN 1 ELSE 0 END) AS conversao,
           AVG(gmv)                                   AS gmv_por_cliente,
           SUM(pontos_bonus)                          AS pontos_bonus
    FROM resultado_cliente
    GROUP BY ALL
),
lado_a_lado AS (
    SELECT id_campanha,
           MAX(clientes)        FILTER (WHERE grupo = 'tratamento') AS n_trat,
           MAX(clientes)        FILTER (WHERE grupo = 'controle')   AS n_ctrl,
           MAX(conversao)       FILTER (WHERE grupo = 'tratamento') AS conv_trat,
           MAX(conversao)       FILTER (WHERE grupo = 'controle')   AS conv_ctrl,
           MAX(gmv_por_cliente) FILTER (WHERE grupo = 'tratamento') AS gmv_cli_trat,
           MAX(gmv_por_cliente) FILTER (WHERE grupo = 'controle')   AS gmv_cli_ctrl,
           MAX(pontos_bonus)    FILTER (WHERE grupo = 'tratamento') AS pontos_bonus
    FROM grupo
    GROUP BY 1
)
SELECT c.id_campanha, c.nome_campanha, c.tipo,
       c.data_inicio::DATE AS data_inicio, c.data_fim::DATE AS data_fim,
       p.n_trat, p.n_ctrl,
       ROUND(p.conv_trat, 4)                                   AS conversao_tratamento,
       ROUND(p.conv_ctrl, 4)                                   AS conversao_controle,
       ROUND(p.conv_trat - p.conv_ctrl, 4)                     AS uplift_pp,
       ROUND(p.conv_trat / NULLIF(p.conv_ctrl, 0) - 1, 4)      AS uplift_relativo,
       -- teste z para diferença de proporções
       ROUND((p.conv_trat - p.conv_ctrl) / SQRT(
             ((p.conv_trat * p.n_trat + p.conv_ctrl * p.n_ctrl) / (p.n_trat + p.n_ctrl))
           * (1 - (p.conv_trat * p.n_trat + p.conv_ctrl * p.n_ctrl) / (p.n_trat + p.n_ctrl))
           * (1.0 / p.n_trat + 1.0 / p.n_ctrl)), 2)            AS z_score,
       ROUND(p.gmv_cli_trat, 2)                                AS gmv_por_cliente_trat,
       ROUND(p.gmv_cli_ctrl, 2)                                AS gmv_por_cliente_ctrl,
       ROUND((p.gmv_cli_trat - p.gmv_cli_ctrl) * p.n_trat, 2)  AS gmv_incremental,
       ROUND(p.pontos_bonus * prm.valor_ponto_reais
             + p.n_trat * c.custo_disparo_por_cliente, 2)      AS custo_campanha,
       -- margem de contribuição assumida de 20% sobre o GMV incremental
       ROUND(((p.gmv_cli_trat - p.gmv_cli_ctrl) * p.n_trat * 0.20
             - (p.pontos_bonus * prm.valor_ponto_reais + p.n_trat * c.custo_disparo_por_cliente))
             / (p.pontos_bonus * prm.valor_ponto_reais + p.n_trat * c.custo_disparo_por_cliente), 2)
                                                               AS roi
FROM lado_a_lado p
JOIN stg_campanhas c USING (id_campanha)
CROSS JOIN param prm
ORDER BY c.data_inicio;
