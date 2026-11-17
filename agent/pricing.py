"""Decide il prezzo di vendita di ogni prodotto."""
from __future__ import annotations

from typing import Dict

from agent.estimators import linear_demand_fit, optimal_price_linear
from agent.memory import Memory
from agent.interface import Observation


def compute_prices(obs: Observation, mem: Memory, cfg: dict) -> Dict[str, float]:
    prices: Dict[str, float] = {}
    for p in obs.info.products:
        prices[p] = _price_for(obs, mem, cfg, p)
    return prices


def _price_for(obs: Observation, mem: Memory, cfg: dict, p: str) -> float:
    cost = mem.unit_cost(obs, p)

    # 1) regola del markup adattivo (sale se vendiamo tutto, scende se restano scorte)
    price = cost * (1 + mem.margin[p])

    # 2) se abbiamo abbastanza dati, mescola con il prezzo ottimo stimato dalla domanda
    fit = None
    if cfg["use_demand_model"]:
        fit = linear_demand_fit(mem.demand_points[p], cfg["demand_min_points"])
        if fit is not None:
            a, b = fit
            w = cfg["demand_model_weight"]
            price = (1 - w) * price + w * optimal_price_linear(a, b, cost)

    # 3) ancoraggio al mercato: niente estremi rispetto ai concorrenti
    mkt = mem.ema_comp[p].value
    if mkt is not None:
        price = min(max(price, mkt * (1 - cfg["market_band_low"])), mkt * (1 + cfg["market_band_high"]))

    # 4) esplorazione nei primi turni (per imparare la curva di domanda)
    if obs.turn < cfg["explore_turns"]:
        pattern = (0.0, 1.0, -1.0, 0.5, -0.5)
        price *= 1 + cfg["explore_spread"] * pattern[obs.turn % len(pattern)]

    # 5) pavimento: mai sotto il costo (+ markup minimo) fuori dal finale
    floor = cost * (1 + cfg["margin_min"])

    # 6) finale: le scorte a fine partita valgono salvage → svendi (i costi passati sono sunk)
    stock = obs.product_inventory.get(p, 0)
    if obs.turns_left < cfg["liquidation_turns"] and stock > 0:
        salvage = obs.info.salvage_value
        if fit is not None:
            a, b = fit
            per_turn = stock / (obs.turns_left + 1)
            clearing = (a - per_turn) / b          # prezzo a cui la domanda ≈ scorte da smaltire
            price = min(price, clearing)
        else:
            steps = cfg["liquidation_turns"] - obs.turns_left
            price *= (1 - cfg["liquidation_discount"]) ** steps
        floor = max(salvage, 0.0) + 0.01

    return max(price, floor)
