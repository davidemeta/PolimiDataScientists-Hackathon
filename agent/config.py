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
    margin_min=0.15,               # markup minimo (fuori dal finale): mai svendere durante la partita
    margin_max=2.0,
    margin_step=0.05,              # di quanto si muove il markup per turno
    sellthrough_high=0.90,         # vendo >= 90% di quello che ho → alzo il prezzo
    sellthrough_low=0.55,          # vendo < 55% → abbasso il prezzo
    market_band_low=0.05,          # non stare più del 5% sotto la media dei concorrenti (niente guerre di prezzo)
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
    demand_estimator="adaptive",   # "adaptive" (crescita che accelera) | "ema" (vecchio: vendite*stockout_boost)
    stockout_boost=1.5,            # solo per demand_estimator="ema"
    stockout_boost_base=1.2,       # adaptive: boost = base^k con k = sold-out consecutivi (1.2, 1.44, 1.73...)
    stockout_boost_max=2.5,        # tetto al boost
    comp_rise_threshold=0.02,      # concorrenti +2% di prezzo rispetto al turno prima = "stanno alzando"
    comp_rise_bonus=0.15,          # se alzano anche loro (scarsità), boost * 1.15
    sales_down_alpha=0.5,          # se restano scorte, la stima scende veloce verso le vendite vere

    # --- aste ---
    bid_fraction=0.90,             # mai offrire più del 90% del valore marginale
    first_bid_fraction=0.75,       # turno 0 (nessuna info): offri 75% del tetto
    price_forecast="holt",         # "holt" (livello + trend) | "ema" (vecchio: media semplice, in ritardo)
    holt_alpha=0.5,                # peso del dato nuovo sul livello
    holt_beta=0.3,                 # peso del cambiamento nuovo sul trend
    holt_phi=0.9,                  # smorzamento del trend (1 = nessuno)
    bid_rule="surplus_share",      # "premium": previsione*(1+premium) | "surplus_share": previsione + quota*(tetto - previsione)
    bid_surplus_share=0.3,         # solo surplus_share: quota del margine (tetto - previsione) aggiunta all'offerta
    bid_cap_over_last=0.20,        # mai offrire più del 20% sopra l'ultimo prezzo d'aggiudicazione (None = nessun tetto)
    infer_clearing=True,           # prezzo d'aggiudicazione nascosto: deducilo da offerte e vincite
    probe_down=0.08,               # ...se vinco tutto, stimo il prezzo 8% sotto la mia offerta più bassa
    probe_up=0.10,                 # ...se non vinco niente, 10% sopra la mia offerta più alta
    auto_auction_rule=True,        # se il tipo d'asta è noto: second_price → offri il valore; uniform → quota più alta
    bid_surplus_share_uniform=0.5, # quota del margine con asta uniform (si paga il prezzo unico, non la propria offerta)
    supply_sensitivity=1.0,        # offerta annunciata: quota del margine * (offerta_media / offerta_attuale)^sens
    comp_stat="mean",              # "mean" | "median": statistica dei prezzi dei concorrenti (median = robusta agli outlier)
    clear_outlier_cap=None,        # limita un dato d'asta anomalo a previsione ±cap (es. 0.4); None = nessun limite
    change_detect=False,           # CUSUM: se lo scarto è persistente il mercato è cambiato → riparti dal dato nuovo
    cusum_k=0.05,                  # scarto relativo "normale" tollerato per turno
    cusum_h=0.30,                  # soglia di scarto accumulato per dichiarare un cambio
    anti_escalation=True,          # smetti di inseguire i prezzi d'asta durante una rincorsa
    escalation_turns=3,            # rincorsa = prezzo d'aggiudicazione in salita per N turni di fila...
    escalation_min_rise=0.02,      # ...ognuno di almeno +2%...
    escalation_sellthrough=0.80,   # ...mentre il magazzino cresce o vendiamo meno dell'80%
    escalation_backoff=0.0,        # durante la rincorsa offri al massimo ultimo prezzo * (1 - backoff)
    value_anchor="confirmed",      # "confirmed": valore dei materiali calcolato sul prezzo confermato dal mercato | "own"
    value_anchor_slack=0.10,       # tolleranza sopra il prezzo confermato
    bid_premium=0.05,              # offerta = prezzo d'aggiudicazione previsto * (1 + premium)
    premium_mode="ema",            # "ema" (media del tasso di vittoria) | "fast" (reagisce all'ultimo turno: nei test perde troppe aste)
    premium_step=0.03,             # salita del premium quando si perde
    premium_step_down=0.06,        # discesa del premium quando si vince tutto (solo "fast")
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
# Quando fate una submission, copiate qui la config consegnata COME DIZIONARIO LETTERALE
# (non dict(DEFAULT_CONFIG), altrimenti cambia insieme ai default).
STABLE_CONFIG = dict(  # versione v1 (prima di Holt e domanda adattiva), congelata come dizionario letterale
    ema_alpha=0.3,
    default_material_price=5.0,
    margin_init=0.4,
    margin_min=0.05,
    margin_max=2.0,
    margin_step=0.05,
    sellthrough_high=0.9,
    sellthrough_low=0.55,
    market_band_low=0.15,
    market_band_high=0.1,
    use_demand_model=True,
    demand_min_points=6,
    demand_window=12,
    demand_model_weight=0.5,
    explore_turns=4,
    explore_spread=0.08,
    liquidation_turns=2,
    liquidation_discount=0.15,
    target_stock_turns=1.5,
    initial_sales_share=0.5,
    demand_estimator='ema',
    stockout_boost=1.5,
    stockout_boost_base=1.2,
    stockout_boost_max=2.5,
    comp_rise_threshold=0.02,
    comp_rise_bonus=0.15,
    sales_down_alpha=0.5,
    bid_fraction=0.9,
    bid_rule='premium',
    bid_surplus_share=0.3,
    bid_cap_over_last=None,
    infer_clearing=False,
    probe_down=0.08,
    probe_up=0.1,
    auto_auction_rule=False,
    bid_surplus_share_uniform=0.5,
    supply_sensitivity=0.0,
    comp_stat='mean',
    clear_outlier_cap=None,
    change_detect=False,
    cusum_k=0.05,
    cusum_h=0.3,
    anti_escalation=False,
    escalation_turns=3,
    escalation_min_rise=0.02,
    escalation_sellthrough=0.8,
    escalation_backoff=0.0,
    value_anchor='own',
    value_anchor_slack=0.1,
    first_bid_fraction=0.75,
    price_forecast='ema',
    holt_alpha=0.5,
    holt_beta=0.3,
    holt_phi=0.9,
    bid_premium=0.05,
    premium_mode='ema',
    premium_step=0.03,
    premium_step_down=0.06,
    premium_min=-0.3,
    premium_max=0.6,
    winrate_high=0.95,
    winrate_low=0.6,
    tier_low_share=0.3,
    tier_discount=0.12,
    endgame_turns=0,
    cash_buffer=0.05,
)


# Profili: override sopra DEFAULT_CONFIG per le varianti di gioco più probabili.
# Scelta guidata in playbook.md; i valori sono tarati con run_matrix.py (seed di taratura)
# e verificati su seed separati.
PROFILES = {
    "balanced": {},                                    # non si sa niente (= DEFAULT_CONFIG, v4)
    "rank": dict(anti_escalation=False),               # punteggio = classifica: non mollare le aste agli altri
    "profit": dict(bid_surplus_share=0.15),            # punteggio = profitto assoluto: compra meno caro
    # aste dove NON si paga la propria offerta (uniform / second_price): offrire vicino al valore costa poco
    "single_price": dict(bid_surplus_share=1.0, bid_surplus_share_uniform=1.0, bid_cap_over_last=None,
                         anti_escalation=False),
    "glut": dict(margin_min=0.25, market_band_low=0.0),   # magazzino caro / partita corta / guerra di prezzi
}


def make_config(overrides=None, profile=None):
    """Config = DEFAULT_CONFIG + profilo (opzionale) + override (opzionali)."""
    cfg = dict(DEFAULT_CONFIG)
    layers = []
    if profile:
        if profile not in PROFILES:
            raise KeyError(f"Profilo sconosciuto: {profile}. Disponibili: {list(PROFILES)}")
        layers.append(PROFILES[profile])
    if overrides:
        layers.append(overrides)
    for layer in layers:
        unknown = set(layer) - set(cfg)
        if unknown:
            raise KeyError(f"Parametri sconosciuti: {unknown}")
        cfg.update(layer)
    return cfg
