"""Decide quanto produrre di ogni prodotto."""
from __future__ import annotations

from typing import Dict

from agent.memory import Memory
from agent.interface import Observation


def plan_production(obs: Observation, mem: Memory, cfg: dict, prices: Dict[str, float]) -> Dict[str, int]:
    info = obs.info
    sell_turns_left = obs.turns_left + (1 if info.sell_same_turn else 0)
    desired: Dict[str, int] = {}
    unit_margin: Dict[str, float] = {}

    for p in info.products:
        cost = mem.unit_cost(obs, p)
        unit_margin[p] = prices[p] - cost
        if unit_margin[p] <= 0 or sell_turns_left <= 0:
            desired[p] = 0           # non conviene produrre (o non si fa più in tempo a vendere)
            continue
        exp_sales = mem.expected_sales(obs, p)
        stock = obs.product_inventory.get(p, 0)
        target = exp_sales * cfg["target_stock_turns"] - stock
        # non produrre più di quanto si riesce a vendere prima della fine
        sellable = exp_sales * sell_turns_left - stock
        desired[p] = max(0, int(round(min(target, sellable))))

    # capacità: dai priorità ai prodotti con margine unitario più alto
    cap_left = info.capacity
    for p in sorted(desired, key=lambda x: -unit_margin[x]):
        desired[p] = min(desired[p], cap_left)
        cap_left -= desired[p]
    return desired
