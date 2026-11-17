"""Decide le offerte alle aste per le materie prime."""
from __future__ import annotations

import math
from typing import Dict, List

from agent.memory import Memory
from agent.interface import Bid, Observation


def material_values(obs: Observation, mem: Memory, prices: Dict[str, float],
                    production: Dict[str, int]) -> Dict[str, float]:
    """
    Valore marginale di un'unità di materia prima = massimo che conviene pagarla.
      valore(m) = (prezzo_prodotto - lavorazione - costo_altri_materiali) / unità_di_m
    Se m serve a più prodotti, si prende il valore più alto tra quelli che produciamo.
    """
    info = obs.info
    values: Dict[str, float] = {m: 0.0 for m in info.materials}
    for p, qty in production.items():
        if qty <= 0:
            continue
        rec = info.recipes[p]
        for m, need in rec.items():
            others = sum(q * mem.material_price(o) for o, q in rec.items() if o != m)
            v = (prices[p] - info.labor_cost[p] - others) / need
            values[m] = max(values[m], v)
    return values


def plan_bids(obs: Observation, mem: Memory, cfg: dict, prices: Dict[str, float],
              production: Dict[str, int]) -> List[Bid]:
    info = obs.info
    if obs.turns_left < cfg["endgame_turns"]:
        return []        # finale: materie prime che non faremo in tempo a usare

    # fabbisogno = materiali per la produzione desiderata - quelli già in magazzino
    need: Dict[str, int] = {m: 0 for m in info.materials}
    for p, q in production.items():
        for m, per_unit in info.recipes[p].items():
            need[m] += per_unit * q
    for m in need:
        need[m] = max(0, need[m] - obs.raw_inventory.get(m, 0))

    values = material_values(obs, mem, prices, production)
    bids: List[Bid] = []
    for m in info.materials:
        if need[m] <= 0 or values[m] <= 0:
            continue
        ceiling = values[m] * cfg["bid_fraction"]          # MAI oltre questo
        ema = mem.ema_clear[m].value
        if ema is None:
            price = ceiling * cfg["first_bid_fraction"]
        else:
            price = min(ceiling, ema * (1 + mem.premium[m]))
        if price <= 0:
            continue
        low_qty = int(math.floor(need[m] * cfg["tier_low_share"]))
        high_qty = need[m] - low_qty
        bids.append(Bid(m, round(price, 2), high_qty))
        if low_qty > 0:
            bids.append(Bid(m, round(price * (1 - cfg["tier_discount"]), 2), low_qty))
    return bids
