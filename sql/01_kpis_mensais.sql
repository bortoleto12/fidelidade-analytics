-- =============================================================
-- 01 · KPIs MENSAIS DO PROGRAMA
-- Base ativa, aquisição, faturamento (GMV), ticket, pontos e passivo
-- =============================================================

CREATE OR REPLACE TABLE mart_kpis_mensais AS
WITH vendas AS (
    SELECT mes,
           COUNT(*)                         AS transacoes,
           COUNT(DISTINCT id_cliente)       AS clientes_ativos,
           SUM(valor_compra)                AS gmv,
           SUM(pontos_total)                AS pontos_emitidos,
           SUM(pontos_bonus)                AS pontos_bonus_campanha
    FROM stg_transacoes
    GROUP BY mes
),
novos AS (
    SELECT DATE_TRUNC('month', data_cadastro)::DATE AS mes,
           COUNT(*)                                 AS novos_clientes
    FROM stg_clientes
    GROUP BY 1
),
resg AS (
    SELECT mes,
           COUNT(*)                   AS resgates,
           SUM(pontos_resgatados)     AS pontos_resgatados
    FROM stg_resgates
    GROUP BY mes
)
SELECT v.mes,
       COALESCE(n.novos_clientes, 0)                         AS novos_clientes,
       v.clientes_ativos,
       v.transacoes,
       ROUND(v.gmv, 2)                                       AS gmv,
       ROUND(v.gmv / v.transacoes, 2)                        AS ticket_medio,
       ROUND(v.transacoes / v.clientes_ativos, 2)            AS frequencia_media,
       v.pontos_emitidos,
       v.pontos_bonus_campanha,
       COALESCE(r.resgates, 0)                               AS resgates,
       COALESCE(r.pontos_resgatados, 0)                      AS pontos_resgatados,
       -- passivo = pontos emitidos ainda não resgatados (acumulado)
       SUM(v.pontos_emitidos - COALESCE(r.pontos_resgatados, 0))
           OVER (ORDER BY v.mes)                             AS passivo_pontos,
       ROUND(SUM(v.pontos_emitidos - COALESCE(r.pontos_resgatados, 0))
           OVER (ORDER BY v.mes) * (SELECT valor_ponto_reais FROM param), 2)
                                                             AS passivo_reais,
       -- crescimento mês contra mês do GMV
       ROUND(v.gmv / LAG(v.gmv) OVER (ORDER BY v.mes) - 1, 4) AS gmv_var_mom
FROM vendas v
LEFT JOIN novos n USING (mes)
LEFT JOIN resg  r USING (mes)
ORDER BY v.mes;

-- Visão por parceiro (mix do programa)
CREATE OR REPLACE TABLE mart_parceiros AS
SELECT t.mes, p.id_parceiro, p.nome_parceiro, p.categoria,
       COUNT(*)                         AS transacoes,
       COUNT(DISTINCT t.id_cliente)     AS clientes,
       ROUND(SUM(t.valor_compra), 2)    AS gmv,
       ROUND(AVG(t.valor_compra), 2)    AS ticket_medio,
       SUM(t.pontos_total)              AS pontos_emitidos
FROM stg_transacoes t
JOIN stg_parceiros p USING (id_parceiro)
GROUP BY ALL
ORDER BY t.mes, gmv DESC;
