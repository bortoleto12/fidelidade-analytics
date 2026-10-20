"""
Gera um dataset SINTÉTICO de um programa de fidelidade de coalizão (varejo).

Nenhum dado real é usado: tudo é simulado com distribuições estatísticas para
reproduzir padrões comuns do mundo real:
  - crescimento da base e churn (clientes deixam de comprar)
  - sazonalidade (Black Friday, Natal, Dia das Mães)
  - campanhas com grupo de CONTROLE (permite medir uplift de verdade)
  - anéis de fraude em resgates (dispositivo compartilhado, contas novas,
    acúmulo relâmpago de pontos e resgate imediato)

Uso:
    python src/gerar_dados.py            # gera em data/raw/
    python src/gerar_dados.py --clientes 5000 --seed 7
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "data" / "raw"

INICIO = pd.Timestamp("2024-01-01")
FIM = pd.Timestamp("2025-12-31 23:59:59")

UFS = ["SP", "RJ", "MG", "PR", "RS", "SC", "BA", "PE", "GO", "DF", "CE", "ES"]
PESO_UFS = [0.30, 0.12, 0.11, 0.08, 0.07, 0.06, 0.06, 0.05, 0.04, 0.04, 0.04, 0.03]
FAIXAS = ["18-24", "25-34", "35-44", "45-54", "55+"]
PESO_FAIXAS = [0.14, 0.30, 0.27, 0.17, 0.12]
CANAIS = ["app", "loja", "site", "indicacao"]
PESO_CANAIS = [0.45, 0.30, 0.15, 0.10]

PARCEIROS = pd.DataFrame(
    [
        (1, "Mercado Bom Preço", "supermercado", 1.0),
        (2, "Super Econômico", "supermercado", 1.0),
        (3, "Farma Vida", "farmacia", 1.0),
        (4, "Drogaria Central", "farmacia", 1.0),
        (5, "Posto Estrada Azul", "posto", 1.0),
        (6, "Posto Rota Sul", "posto", 1.0),
        (7, "Moda Urbana", "moda", 1.5),
        (8, "Casa & Lar", "casa", 1.5),
        (9, "EletroMax", "eletronicos", 2.0),
        (10, "Livraria Página", "livraria", 2.0),
    ],
    columns=["id_parceiro", "nome_parceiro", "categoria", "pontos_por_real"],
)
# frequência relativa e ticket médio (R$) por parceiro
FREQ_PARCEIRO = np.array([0.22, 0.18, 0.12, 0.10, 0.12, 0.08, 0.07, 0.05, 0.03, 0.03])
TICKET_PARCEIRO = np.array([180, 150, 70, 65, 220, 210, 160, 240, 900, 90])

CATALOGO = pd.DataFrame(
    [
        ("Cupom R$10", "cupom", 1000),
        ("Cupom R$25", "cupom", 2500),
        ("Cupom R$50", "cupom", 5000),
        ("Ingresso de cinema", "experiencia", 1800),
        ("Milhas aéreas (1.000)", "milhas", 3000),
        ("Vale-combustível R$50", "combustivel", 4500),
        ("Fone bluetooth", "produto", 12000),
    ],
    columns=["premio", "categoria_premio", "pontos"],
)

CAMPANHAS = pd.DataFrame(
    [
        # id, nome, tipo, inicio, fim, parceiro alvo (0 = todos), multiplicador, uplift real simulado
        (1, "Pontos em Dobro – Supermercado", "pontos_em_dobro", "2024-03-01", "2024-03-31", 1, 2.0, 0.35),
        (2, "Dia das Mães – Moda", "pontos_em_dobro", "2024-04-25", "2024-05-12", 7, 2.0, 0.60),
        (3, "Abasteça e Ganhe", "bonus_fixo", "2024-07-01", "2024-07-31", 5, 1.0, 0.05),
        (4, "Black Friday Turbo", "pontos_em_triplo", "2024-11-20", "2024-12-02", 0, 3.0, 0.80),
        (5, "Volta às Aulas – Livraria", "pontos_em_dobro", "2025-01-20", "2025-02-15", 10, 2.0, 0.25),
        (6, "Saúde em Dia – Farmácia", "pontos_em_dobro", "2025-05-01", "2025-05-31", 3, 2.0, 0.40),
        (7, "Reativação – Sentimos sua falta", "reativacao", "2025-08-01", "2025-08-31", 0, 2.0, 0.15),
        (8, "Black Friday Turbo 2025", "pontos_em_triplo", "2025-11-19", "2025-12-01", 0, 3.0, 0.70),
    ],
    columns=["id_campanha", "nome_campanha", "tipo", "data_inicio", "data_fim",
             "id_parceiro_alvo", "multiplicador_pontos", "lat_uplift"],
)
CAMPANHAS["data_inicio"] = pd.to_datetime(CAMPANHAS["data_inicio"])
CAMPANHAS["data_fim"] = pd.to_datetime(CAMPANHAS["data_fim"]) + pd.Timedelta(hours=23, minutes=59)
CAMPANHAS["bonus_fixo_pontos"] = np.where(CAMPANHAS["tipo"] == "bonus_fixo", 200, 0)
CAMPANHAS["custo_disparo_por_cliente"] = [0.12, 0.12, 0.10, 0.15, 0.12, 0.12, 0.20, 0.15]
CAMPANHAS["pct_controle"] = 0.20

VALOR_PONTO = 0.01  # R$ por ponto (custo do ponto para o programa)


def peso_sazonal(datas: pd.DatetimeIndex) -> np.ndarray:
    """Peso relativo de compra por dia (1 = normal)."""
    w = np.ones(len(datas))
    mes, dia, dow = datas.month.values, datas.day.values, datas.dayofweek.values
    w *= np.where(dow >= 4, 1.25, 1.0)                     # sexta–domingo
    w *= np.where(mes == 12, 1.45, 1.0)                    # Natal
    w *= np.where((mes == 11) & (dia >= 20), 1.9, 1.0)     # Black Friday
    w *= np.where((mes == 5) & (dia <= 12), 1.25, 1.0)     # Dia das Mães
    w *= np.where(mes.astype(int) == 2, 0.85, 1.0)         # fevereiro fraco
    w *= np.where((dia >= 1) & (dia <= 7), 1.10, 1.0)      # começo do mês (salário)
    return w


def gerar_clientes(n: int, rng: np.random.Generator) -> pd.DataFrame:
    # base cresce ao longo do tempo: mais cadastros no fim do período
    dias_total = (FIM.normalize() - INICIO).days
    u = rng.beta(1.3, 1.0, n)
    data_cad = INICIO + pd.to_timedelta((u * dias_total).astype(int), unit="D")
    data_cad = data_cad + pd.to_timedelta(rng.integers(8 * 60, 22 * 60, n), unit="m")
    # 15% da base já existia antes de 2024 (clientes "legado")
    legado = rng.random(n) < 0.15
    data_cad = np.where(
        legado,
        pd.Timestamp("2022-01-01") + pd.to_timedelta(rng.integers(0, 730, n), unit="D"),
        data_cad,
    )
    canal = rng.choice(CANAIS, n, p=PESO_CANAIS)
    df = pd.DataFrame(
        {
            "id_cliente": np.arange(1, n + 1),
            "data_cadastro": pd.to_datetime(data_cad),
            "uf": rng.choice(UFS, n, p=PESO_UFS),
            "faixa_etaria": rng.choice(FAIXAS, n, p=PESO_FAIXAS),
            "canal_aquisicao": canal,
        }
    )
    # atributos latentes (NÃO exportados): frequência, ticket, tempo de vida
    freq = rng.gamma(shape=1.6, scale=1.4, size=n)                # compras/mês
    freq *= np.select([canal == "indicacao", canal == "app"], [1.3, 1.15], 1.0)
    ticket_mult = rng.lognormal(0, 0.35, n)
    vida_media = np.select([canal == "indicacao", canal == "app", canal == "site"], [520, 430, 300], 360)
    vida = rng.exponential(vida_media)
    vida = np.where(rng.random(n) < 0.12, rng.integers(1, 20, n), vida)  # "one-and-done"
    df["lat_freq"], df["lat_ticket"], df["lat_vida"] = freq, ticket_mult, vida
    df["id_dispositivo"] = [f"DV{rng.integers(10**9, 10**10)}" for _ in range(n)]
    # algumas famílias compartilham dispositivo (falso positivo realista)
    fam = rng.choice(n, size=int(n * 0.03), replace=False)
    df.loc[fam[1::2], "id_dispositivo"] = df.loc[fam[0::2][: len(fam[1::2])], "id_dispositivo"].values
    # totens de autoatendimento em loja: vários clientes legítimos no mesmo aparelho
    em_loja = df.index[df.canal_aquisicao == "loja"].values
    for t in range(4):
        idx = rng.choice(em_loja, size=int(rng.integers(8, 25)), replace=False)
        df.loc[idx, "id_dispositivo"] = f"DVTOTEM{t + 1:03d}"
    return df


def sortear_datas(ini: pd.Timestamp, fim: pd.Timestamp, k: int, rng, dias_idx, pesos) -> pd.DatetimeIndex:
    a = max(0, (ini.normalize() - INICIO).days)
    b = min(len(dias_idx) - 1, (fim.normalize() - INICIO).days)
    if k <= 0 or b < a:
        return pd.DatetimeIndex([])
    p = pesos[a : b + 1] / pesos[a : b + 1].sum()
    d = rng.choice(np.arange(a, b + 1), size=k, p=p)
    minutos = rng.normal(15 * 60, 3 * 60, k).clip(6 * 60, 23 * 60 + 50).astype(int)
    return dias_idx[d] + pd.to_timedelta(minutos, unit="m")


def gerar_transacoes(cli: pd.DataFrame, rng) -> pd.DataFrame:
    dias_idx = pd.date_range(INICIO, FIM.normalize(), freq="D")
    pesos = peso_sazonal(dias_idx)
    linhas = []
    for c in cli.itertuples(index=False):
        ini = max(c.data_cadastro, INICIO)
        fim = min(c.data_cadastro + pd.Timedelta(days=float(c.lat_vida)), FIM)
        if fim <= ini:
            continue
        meses = (fim - ini).days / 30.4
        k = rng.poisson(c.lat_freq * meses)
        if c.data_cadastro >= INICIO and k == 0:
            k = 1  # todo cadastro novo faz ao menos a 1ª compra
        datas = sortear_datas(ini, fim, k, rng, dias_idx, pesos)
        if len(datas) == 0:
            continue
        if c.data_cadastro >= INICIO:  # 1ª compra costuma acontecer junto com o cadastro
            primeira = c.data_cadastro + pd.Timedelta(minutes=int(rng.integers(5, 48 * 60)))
            datas = datas.delete(0).append(pd.DatetimeIndex([min(primeira, FIM)]))
        linhas.append(pd.DataFrame({"id_cliente": c.id_cliente, "data_hora": datas, "lat_tm": c.lat_ticket}))
    tx = pd.concat(linhas, ignore_index=True)
    tx["id_parceiro"] = rng.choice(PARCEIROS["id_parceiro"], len(tx), p=FREQ_PARCEIRO)
    tx["id_campanha"] = pd.NA
    return tx


def aplicar_campanhas(cli, tx, rng):
    """Define público (tratamento x controle) e injeta compras incrementais."""
    dias_idx = pd.date_range(INICIO, FIM.normalize(), freq="D")
    pesos = peso_sazonal(dias_idx)
    publicos, extras = [], []
    cli_idx = cli.set_index("id_cliente")
    for camp in CAMPANHAS.itertuples(index=False):
        # elegíveis: clientes cadastrados antes da campanha e com compra nos 180 dias anteriores
        janela = tx[(tx.data_hora < camp.data_inicio) & (tx.data_hora >= camp.data_inicio - pd.Timedelta(days=180))]
        if camp.tipo == "reativacao":
            ativos_recentes = set(tx[(tx.data_hora < camp.data_inicio) &
                                     (tx.data_hora >= camp.data_inicio - pd.Timedelta(days=90))].id_cliente)
            ant = tx[(tx.data_hora < camp.data_inicio - pd.Timedelta(days=90)) &
                     (tx.data_hora >= camp.data_inicio - pd.Timedelta(days=365))]
            eleg = np.array(sorted(set(ant.id_cliente) - ativos_recentes))
        else:
            eleg = janela.id_cliente.unique()
        eleg = rng.permutation(eleg)
        if camp.tipo not in ("pontos_em_triplo", "reativacao"):
            eleg = eleg[: int(len(eleg) * 0.6)]  # campanhas segmentadas atingem parte da base
        grupo = np.where(rng.random(len(eleg)) < camp.pct_controle, "controle", "tratamento")
        publicos.append(pd.DataFrame({"id_campanha": camp.id_campanha, "id_cliente": eleg, "grupo": grupo}))

        # compras incrementais para o tratamento
        trat = eleg[grupo == "tratamento"]
        dur_meses = (camp.data_fim - camp.data_inicio).days / 30.4 + 0.03
        base_freq = cli_idx.loc[trat, "lat_freq"].values
        if camp.id_parceiro_alvo:
            base_freq = base_freq * FREQ_PARCEIRO[camp.id_parceiro_alvo - 1]
        if camp.tipo == "reativacao":
            base_freq = np.full(len(trat), 0.9)  # base é ~0 para inativos
        k = rng.poisson(base_freq * dur_meses * camp.lat_uplift)
        for cid, n in zip(trat[k > 0], k[k > 0]):
            d = sortear_datas(camp.data_inicio, camp.data_fim, n, rng, dias_idx, pesos)
            extras.append(pd.DataFrame({"id_cliente": cid, "data_hora": d,
                                        "lat_tm": cli_idx.at[cid, "lat_ticket"],
                                        "id_parceiro": camp.id_parceiro_alvo or rng.choice(PARCEIROS.id_parceiro, n, p=FREQ_PARCEIRO)}))
    tx = pd.concat([tx] + extras, ignore_index=True)
    pub = pd.concat(publicos, ignore_index=True)

    # marca transações do grupo tratamento dentro da janela (e parceiro) como "da campanha"
    tx["id_campanha"] = pd.array([pd.NA] * len(tx), dtype="Int64")
    for camp in CAMPANHAS.itertuples(index=False):
        trat_ids = pub[(pub.id_campanha == camp.id_campanha) & (pub.grupo == "tratamento")].id_cliente
        m = (tx.data_hora.between(camp.data_inicio, camp.data_fim)
             & tx.id_cliente.isin(trat_ids) & tx.id_campanha.isna())
        if camp.id_parceiro_alvo:
            m &= tx.id_parceiro == camp.id_parceiro_alvo
        tx.loc[m, "id_campanha"] = camp.id_campanha
    return tx, pub


def valores_e_pontos(tx, rng):
    tk = TICKET_PARCEIRO[tx.id_parceiro.values - 1] * tx.lat_tm.values
    tx["valor_compra"] = np.round(rng.gamma(4.0, tk / 4.0), 2).clip(5, None)
    ppr = PARCEIROS.set_index("id_parceiro").pontos_por_real.reindex(tx.id_parceiro).values
    camp = CAMPANHAS.set_index("id_campanha")
    mult = tx.id_campanha.map(camp.multiplicador_pontos).astype(float).fillna(1.0).values
    bonus = tx.id_campanha.map(camp.bonus_fixo_pontos).astype(float).fillna(0).values
    tx["pontos_base"] = np.floor(tx.valor_compra.values * ppr).astype(int)
    tx["pontos_bonus"] = (np.floor(tx.pontos_base * (mult - 1)) + bonus).astype(int)
    return tx


def injetar_fraude(cli, tx, rng, n_aneis=6):
    """Anéis de fraude: contas novas, mesmo dispositivo, rajada de compras e resgate imediato."""
    novos_cli, novas_tx, gabarito = [], [], []
    prox_id = cli.id_cliente.max() + 1
    for a in range(n_aneis):
        # metade dos anéis é "afobada" (tudo em 3–4 dias, poucos aparelhos);
        # a outra metade é "cautelosa" (mais aparelhos, compras espalhadas em semanas)
        cauteloso = a % 2 == 1
        n_contas = int(rng.integers(12, 30))
        dia = INICIO + pd.Timedelta(days=int(rng.integers(120, 690)))
        n_devs = max(1, n_contas // 3) if cauteloso else int(rng.integers(1, 3))
        devs = [f"DVF{rng.integers(10**8, 10**9)}" for _ in range(n_devs)]
        posto = int(rng.choice([5, 6]))
        for i in range(n_contas):
            cid = prox_id; prox_id += 1
            cad = dia + pd.Timedelta(minutes=int(rng.integers(0, (10 if cauteloso else 3) * 24 * 60)))
            novos_cli.append({"id_cliente": cid, "data_cadastro": cad, "uf": rng.choice(["SP", "RJ", "GO"]),
                              "faixa_etaria": rng.choice(["18-24", "25-34"]), "canal_aquisicao": "site",
                              "id_dispositivo": devs[i % len(devs)]})
            k = int(rng.integers(6, 15))
            janela_min = (rng.integers(8, 25) if cauteloso else 4) * 24 * 60
            datas = cad + pd.to_timedelta(np.sort(rng.integers(30, janela_min, k)), unit="m")
            valores = np.round(rng.uniform(250, 480, k) if cauteloso else rng.uniform(380, 650, k), 2)
            novas_tx.append(pd.DataFrame({"id_cliente": cid, "data_hora": datas, "id_parceiro": posto,
                                          "valor_compra": valores, "lat_tm": 1.0,
                                          "id_campanha": pd.array([pd.NA] * k, dtype="Int64")}))
            gabarito.append({"id_cliente": cid, "anel_fraude": a + 1})
    cli = pd.concat([cli, pd.DataFrame(novos_cli)], ignore_index=True)
    ftx = pd.concat(novas_tx, ignore_index=True)
    ftx["pontos_base"] = np.floor(ftx.valor_compra).astype(int)
    ftx["pontos_bonus"] = 0
    tx = pd.concat([tx, ftx], ignore_index=True)
    return cli, tx, pd.DataFrame(gabarito)


def gerar_resgates(cli, tx, gabarito, rng):
    fraudadores = set(gabarito.id_cliente)
    tx = tx.sort_values(["id_cliente", "data_hora"])
    tx["pontos_total"] = tx.pontos_base + tx.pontos_bonus
    dev = cli.set_index("id_cliente").id_dispositivo
    cat = CATALOGO.sort_values("pontos")
    linhas = []
    for cid, g in tx.groupby("id_cliente", sort=False):
        fraude = cid in fraudadores
        saldo, prop = 0, (1.0 if fraude else rng.beta(2, 3))  # propensão a resgatar
        alvo = None
        for dt, pts in zip(g.data_hora.values, g.pontos_total.values):
            saldo += pts
            if alvo is None:
                alvo = cat.pontos.min() if fraude else rng.choice(cat.pontos.values[:6])
            if saldo >= alvo and (fraude or rng.random() < prop * 0.6):
                if fraude:  # resgata tudo o que puder, rápido
                    escolha = cat[cat.pontos <= saldo].iloc[-1]
                    atraso = rng.integers(10, 6 * 60)
                else:
                    escolha = cat[cat.pontos == alvo].iloc[0]
                    atraso = rng.integers(60, 20 * 24 * 60)
                linhas.append({"id_cliente": cid,
                               "data_hora": pd.Timestamp(dt) + pd.Timedelta(minutes=int(atraso)),
                               "premio": escolha.premio, "categoria_premio": escolha.categoria_premio,
                               "pontos_resgatados": int(escolha.pontos), "id_dispositivo": dev.at[cid]})
                saldo -= escolha.pontos
                alvo = None
    r = pd.DataFrame(linhas)
    r = r[r.data_hora <= FIM].sort_values("data_hora").reset_index(drop=True)
    r.insert(0, "id_resgate", np.arange(1, len(r) + 1))
    return r


def main(n_clientes: int, seed: int):
    rng = np.random.default_rng(seed)
    SAIDA.mkdir(parents=True, exist_ok=True)
    print(f"Gerando {n_clientes:,} clientes (seed={seed})...")
    cli = gerar_clientes(n_clientes, rng)
    tx = gerar_transacoes(cli, rng)
    tx, pub = aplicar_campanhas(cli, tx, rng)
    tx = valores_e_pontos(tx, rng)
    cli, tx, gab = injetar_fraude(cli, tx, rng)
    res = gerar_resgates(cli, tx, gab, rng)

    tx = tx.sort_values("data_hora").reset_index(drop=True)
    tx.insert(0, "id_transacao", np.arange(1, len(tx) + 1))
    tx = tx[["id_transacao", "id_cliente", "id_parceiro", "data_hora", "valor_compra",
             "pontos_base", "pontos_bonus", "id_campanha"]]
    cli_out = cli[["id_cliente", "data_cadastro", "uf", "faixa_etaria", "canal_aquisicao", "id_dispositivo"]]
    camp_out = CAMPANHAS.drop(columns=["lat_uplift"])

    arquivos = {"clientes": cli_out, "parceiros": PARCEIROS, "campanhas": camp_out,
                "campanha_publico": pub, "transacoes": tx, "resgates": res,
                "catalogo_premios": CATALOGO, "gabarito_fraude": gab}
    for nome, df in arquivos.items():
        df.to_parquet(SAIDA / f"{nome}.parquet", index=False)  # versionado no Git (leve)
        df.to_csv(SAIDA / f"{nome}.csv", index=False)          # cópia amigável p/ Excel/BI
        print(f"  {nome:<18} {len(df):>9,} linhas")
    print(f"OK → {SAIDA}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--clientes", type=int, default=20_000)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    main(a.clientes, a.seed)
