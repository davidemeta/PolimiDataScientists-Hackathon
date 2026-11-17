"""
Rete di sicurezza: ogni azione passa da qui prima di essere inviata.
Obiettivo: ZERO azioni non valide, qualunque cosa succeda nella strategia.
"""
from __future__ import annotations

import math
from typing import Dict

from agent.interface import Action, Bid, Observation


def _finite_pos(x) -> bool:
    try:
        return math.isfinite(float(x)) and float(x) > 0
    except (TypeError, ValueError):
        return False


def validate(action: Action, obs: Observation, cfg: dict, fallback_prices: Dict[str, float]) -> Action:
    info = obs.info
    spendable = max(0.0, obs.cash * (1 - cfg["cash_buffer"]))

    # --- prezzi: positivi e finiti, per ogni prodotto ---
    prices: Dict[str, float] = {}
    for p in info.products:
        v = action.prices.get(p)
        if not _finite_pos(v):
            v = fallback_prices.get(p, 1.0)
        prices[p] = round(float(v), 2)

    # --- produzione: interi >= 0, capacità, materiali (se servono già in magazzino), cassa ---
    production: Dict[str, int] = {}
    cap_left = info.capacity
    raw = dict(obs.raw_inventory)
    labor_total = 0.0
    for p, q in action.production.items():
        if p not in info.products or not _finite_pos(q):
            continue
        q = min(int(q), cap_left)
        if not info.production_after_auction:
            rec = info.recipes[p]
            q = min([q] + [raw.get(m, 0) // need for m, need in rec.items()])
            for m, need in rec.items():
                raw[m] = raw.get(m, 0) - need * q
        labor = info.labor_cost.get(p, 0.0)
        if labor > 0:
            q = min(q, int((spendable - labor_total) // labor))
        q = max(0, q)
        if q > 0:
            production[p] = q
            cap_left -= q
            labor_total += labor * q

    # --- offerte: valide e con costo totale entro la cassa (prima le più alte) ---
    budget = spendable - labor_total
    bids = []
    for b in sorted(action.bids, key=lambda b: -float(b.price) if _finite_pos(b.price) else 0):
        if b.material not in info.materials or not _finite_pos(b.price) or not _finite_pos(b.qty):
            continue
        price = round(float(b.price), 2)
        qty = min(int(b.qty), int(budget // price)) if price > 0 else 0
        if qty > 0:
            bids.append(Bid(b.material, price, qty))
            budget -= qty * price

    return Action(bids=bids, production=production, prices=prices)


def safe_default(obs: Observation, fallback_prices: Dict[str, float]) -> Action:
    """Azione minima che non può sbagliare: nessun acquisto, nessuna produzione, vendi le scorte."""
    prices = {p: max(0.01, round(float(fallback_prices.get(p, 1.0)), 2)) for p in obs.info.products}
    return Action(bids=[], production={}, prices=prices)
