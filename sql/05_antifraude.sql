-- =============================================================
-- 05 · ANTIFRAUDE EM RESGATES — score por regras
-- Cada regra soma pontos ao score. Score ≥ 3 → alerta para revisão.
--   R1 (+2) dispositivo usado por 4+ contas
--   R2 (+1) 1º resgate em até 7 dias após o cadastro
--   R3 (+1) 5+ compras nas primeiras 72h de conta
--   R4 (+1) resgatou ≥ 90% dos pontos que ganhou
--   R5 (+1) ticket médio ≥ 2,5× o ticket médio do parceiro em que mais compra
--
-- v2 (após analisar os falsos negativos da v1):
--   R6 (+2) dispositivo com 3+ contas cadastradas numa janela de até 15 dias
--           → pega anéis "cautelosos" que espalham contas em vários aparelhos,
--             sem marcar famílias (2 contas) nem totens de loja (cadastros espaçados)
-- =============================================================

CREATE OR REPLACE TABLE mart_antifraude AS
WITH contas_por_disp AS (
    SELECT id_dispositivo,
           COUNT(*)                                                AS contas_no_dispositivo,
           DATE_DIFF('day', MIN(data_cadastro), MAX(data_cadastro)) AS janela_cadastros_dias
    FROM stg_clientes GROUP BY 1
),
compras AS (
    SELECT c.id_cliente,
           COUNT(t.id_transacao)                                    AS compras_total,
           COUNT(t.id_transacao) FILTER (
               WHERE t.data_hora <= c.data_cadastro + INTERVAL 72 HOUR) AS compras_72h,
           SUM(t.pontos_total)                                      AS pontos_ganhos,
           AVG(t.valor_compra)                                      AS ticket_medio
    FROM stg_clientes c
    JOIN stg_transacoes t USING (id_cliente)
    GROUP BY 1
),
parceiro_principal AS (   -- parceiro onde o cliente mais compra (desempate pelo menor id)
    SELECT id_cliente, id_parceiro AS parceiro_principal
    FROM (SELECT id_cliente, id_parceiro,
                 ROW_NUMBER() OVER (PARTITION BY id_cliente ORDER BY COUNT(*) DESC, id_parceiro) AS rn
          FROM stg_transacoes GROUP BY 1, 2)
    WHERE rn = 1
),
ticket_parceiro AS (
    SELECT id_parceiro, AVG(valor_compra) AS ticket_parceiro
    FROM stg_transacoes GROUP BY 1
),
resg AS (
    SELECT id_cliente,
           COUNT(*)                AS resgates,
           SUM(pontos_resgatados)  AS pontos_resgatados,
           MIN(data_hora)          AS primeiro_resgate
    FROM stg_resgates GROUP BY 1
),
regras AS (
    SELECT c.id_cliente, c.data_cadastro, c.uf, c.id_dispositivo,
           d.contas_no_dispositivo, d.janela_cadastros_dias, k.compras_total, k.compras_72h,
           k.pontos_ganhos, r.resgates, r.pontos_resgatados,
           DATE_DIFF('hour', c.data_cadastro, r.primeiro_resgate) / 24.0 AS dias_ate_1o_resgate,
           ROUND(k.ticket_medio / tp.ticket_parceiro, 2)                AS ticket_vs_parceiro,
           (d.contas_no_dispositivo >= 4)::INT                          AS r1_disp_compartilhado,
           (DATE_DIFF('day', c.data_cadastro, r.primeiro_resgate) <= 7)::INT AS r2_resgate_rapido,
           (k.compras_72h >= 5)::INT                                    AS r3_rajada_compras,
           (r.pontos_resgatados >= 0.9 * k.pontos_ganhos)::INT          AS r4_esvaziou_saldo,
           (k.ticket_medio >= 2.5 * tp.ticket_parceiro)::INT            AS r5_ticket_atipico,
           (d.contas_no_dispositivo >= 3 AND d.janela_cadastros_dias <= 15)::INT AS r6_cadastros_em_lote
    FROM stg_clientes c
    JOIN compras k USING (id_cliente)
    JOIN parceiro_principal pp USING (id_cliente)
    JOIN resg    r USING (id_cliente)                -- só quem resgatou
    JOIN contas_por_disp d USING (id_dispositivo)
    JOIN ticket_parceiro tp ON tp.id_parceiro = pp.parceiro_principal
)
SELECT *,
       2 * r1_disp_compartilhado + r2_resgate_rapido + r3_rajada_compras
         + r4_esvaziou_saldo + r5_ticket_atipico                    AS score_v1,
       (2 * r1_disp_compartilhado + r2_resgate_rapido + r3_rajada_compras
         + r4_esvaziou_saldo + r5_ticket_atipico) >= 3               AS alerta_v1,
       2 * r1_disp_compartilhado + r2_resgate_rapido + r3_rajada_compras
         + r4_esvaziou_saldo + r5_ticket_atipico + 2 * r6_cadastros_em_lote AS score_risco,
       (2 * r1_disp_compartilhado + r2_resgate_rapido + r3_rajada_compras
         + r4_esvaziou_saldo + r5_ticket_atipico + 2 * r6_cadastros_em_lote) >= 3 AS alerta
FROM regras
ORDER BY score_risco DESC, pontos_resgatados DESC, id_cliente;
