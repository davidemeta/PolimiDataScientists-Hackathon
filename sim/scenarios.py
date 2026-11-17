"""
Catalogo delle varianti di mercato plausibili per domani.

Ogni scenario cambia UN aspetto rispetto a `base` (così si capisce cosa conta).
Domani: scegliete lo scenario più simile al gioco vero, oppure create
`SCENARIOS["real"] = make("base", ...)` copiando i parametri veri dal codice degli organizzatori.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Dict

from sim.market import MarketConfig

_BASE = MarketConfig()


def make(base: str = "base", **overrides) -> MarketConfig:
    return replace(SCENARIOS[base] if base in SCENARIOS else _BASE, **overrides)


SCENARIOS: Dict[str, MarketConfig] = {"base": _BASE}
SCENARIOS.update({
    # --- tipo d'asta ---
    "uniform": make(auction_type="uniform"),
    "second_price": make(auction_type="second_price"),
    "known_auction": make(announce_auction_type=True),          # l'agente sa che è pay-as-bid
    "known_uniform": make(auction_type="uniform", announce_auction_type=True),
    "known_second_price": make(auction_type="second_price", announce_auction_type=True),
    "announced_supply": make(announce_supply=True, supply_noise=0.4),
    "high_reserve": make(reserve_price={"A": 6.0, "B": 6.0}),
    # --- forma della domanda ---
    "linear_demand": make(demand_model="linear"),
    "cheapest_first": make(demand_model="cheapest_first"),
    "noisy_demand": make(demand_noise=0.4, season_amplitude=0.4),
    # --- tempi ---
    "sell_next_turn": make(sell_same_turn=False),
    "prod_from_stock": make(production_after_auction=False),
    "slow_pipeline": make(sell_same_turn=False, production_after_auction=False),
    # --- informazioni ---
    "hidden_prices": make(info_competitor_prices=False),
    "hidden_clearing": make(info_clearing_price=False),
    "blind": make(info_competitor_prices=False, info_clearing_price=False),
    # --- scarsità e costi ---
    "scarce": make(supply_per_agent={"A": 25.0, "B": 25.0}),
    "glut": make(supply_per_agent={"A": 80.0, "B": 80.0}),
    "costly_storage": make(holding_cost=3.0, raw_holding_cost=1.0),
    "salvage": make(salvage_value=15.0),
    "fixed_costs": make(fixed_cost=80.0),
    "low_cash": make(start_cash=1500.0),
    # --- scala ---
    "short": make(n_turns=10),
    "long": make(n_turns=80),
    "single_product": make(products=["P1"], recipes={"P1": {"A": 2, "B": 1}}, labor_cost={"P1": 5.0},
                           market_size_per_agent={"P1": 30.0}, demand_alpha={"P1": 4.0},
                           demand_k={"P1": 0.10}, demand_pmax={"P1": 70.0}),
})

# Combinazioni "peggiori" per lo stress test (più aspetti sfavorevoli insieme)
SCENARIOS.update({
    "hard_mix": make(sell_same_turn=False, production_after_auction=False, info_competitor_prices=False,
                     demand_model="cheapest_first", supply_per_agent={"A": 25.0, "B": 25.0}),
    "uniform_linear_short": make(auction_type="uniform", demand_model="linear", n_turns=12),
})
