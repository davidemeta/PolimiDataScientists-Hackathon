"""
TUTTI i parametri dell'agente in un unico posto. Per il tuning usate
run_tournament.py --sweep "nome=v1,v2,v3".
"""

DEFAULT_CONFIG = dict(
    # --- stimatori ---
    ema_alpha=0.3,                 # reattività delle medie mobili (0.2 stabile, 0.5 reattiva)
    default_material_price=5.0,    # prezzo stimato delle materie prime prima di avere dati

    # --- prezzi ---
    margin_init=0.40,              # markup iniziale sul costo di rimpiazzo
    margin_min=0.05,               # markup minimo (fuori dal finale)
    margin_max=2.0,
    margin_step=0.05,              # di quanto si muove il markup per turno
    sellthrough_high=0.90,         # vendo >= 90% di quello che ho → alzo il prezzo
    sellthrough_low=0.55,          # vendo < 55% → abbasso il prezzo
    market_band_low=0.15,          # non stare più del 15% sotto la media dei concorrenti
    market_band_high=0.10,         # né più del 10% sopra
    use_demand_model=True,         # usa regressione prezzo→vendite se affidabile
    demand_min_points=6,
    demand_window=12,              # usa solo gli ultimi N punti (il mercato cambia)
    demand_model_weight=0.5,       # peso del prezzo "ottimo da modello" vs regola del markup
    explore_turns=4,               # turni iniziali in cui variamo il prezzo per imparare la domanda
    explore_spread=0.08,
    liquidation_turns=2,           # ultimi N turni: svendi le scorte (se valgono 0 a fine partita)
    liquidation_discount=0.15,

    # --- produzione ---
    target_stock_turns=1.5,        # produci per coprire 1.5 turni di vendite attese
    initial_sales_share=0.5,       # al turno 0: vendite attese = capacità/n_prodotti * share
    stockout_boost=1.5,            # se vado sold-out, stimo domanda = vendite * 1.5

    # --- aste ---
    bid_fraction=0.90,             # mai offrire più del 90% del valore marginale
    first_bid_fraction=0.75,       # turno 0 (nessuna info): offri 75% del tetto
    bid_premium=0.05,              # offerta = prezzo d'aggiudicazione medio * (1 + premium)
    premium_step=0.03,
    premium_min=-0.30,
    premium_max=0.60,
    winrate_high=0.95,             # vinco quasi tutto → sto pagando troppo, abbasso
    winrate_low=0.60,              # vinco poco → alzo (sempre sotto il tetto)
    tier_low_share=0.3,            # 30% della quantità offerto a prezzo scontato (aste pay-as-bid)
    tier_discount=0.12,
    endgame_turns=0,               # smetti di comprare quando turns_left < N (0 se si vende nello stesso turno)
    cash_buffer=0.05,              # quota di cassa mai spesa
)

# Copia "congelata" dell'ultima versione consegnata: usata come avversario nel torneo.
# Quando fate una submission, copiate qui la config consegnata.
STABLE_CONFIG = dict(DEFAULT_CONFIG)


def make_config(overrides=None):
    cfg = dict(DEFAULT_CONFIG)
    if overrides:
        unknown = set(overrides) - set(cfg)
        if unknown:
            raise KeyError(f"Parametri sconosciuti: {unknown}")
        cfg.update(overrides)
    return cfg
