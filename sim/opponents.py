"""
Avversari di prova con comportamenti tipici delle squadre in un hackathon.
Il nostro agente deve andare bene contro TUTTI, non solo contro uno.
"""
from __future__ import annotations

import random
from typing import Dict, List

from sim.interface import Action, BaseAgent, Bid, Observation


def _mat_price(obs: Observation, m: str, default: float = 5.0) -> float:
    v = obs.last_clearing_price.get(m)
    return default if v is None else v


def _unit_cost(obs: Observation, p: str) -> float:
    rec = obs.info.recipes[p]
    return obs.info.labor_cost[p] + sum(q * _mat_price(obs, m) for m, q in rec.items())


def _split_capacity(obs: Observation, share: float = 1.0) -> Dict[str, int]:
    n = len(obs.info.products)
    return {p: int(obs.info.capacity * share / n) for p in obs.info.products}


def _bids_for(obs: Observation, production: Dict[str, int], price_fn) -> List[Bid]:
    need = {m: 0 for m in obs.info.materials}
    for p, q in production.items():
        for m, k in obs.info.recipes[p].items():
            need[m] += k * q
    bids = []
    for m, q in need.items():
        q -= obs.raw_inventory.get(m, 0)
        if q > 0:
            bids.append(Bid(m, round(max(0.5, price_fn(m)), 2), int(q)))
    return bids


class FixedAgent(BaseAgent):
    """Prezzi e offerte fissi: la squadra che non ha fatto in tempo ad adattare nulla."""

    def __init__(self, name="fixed", price_markup=0.6, bid=6.0):
        self.name, self.markup, self.bid = name, price_markup, bid

    def act(self, obs):
        prod = _split_capacity(obs, 0.6)
        prices = {p: round(20 + 10 * i + 15, 2) for i, p in enumerate(obs.info.products)}
        return Action(_bids_for(obs, prod, lambda m: self.bid), prod, prices)


class Undercutter(BaseAgent):
    """Taglia sempre i prezzi sotto il concorrente più economico: la 'guerra dei prezzi'."""

    def __init__(self, name="undercutter"):
        self.name = name

    def act(self, obs):
        prices = {}
        for p in obs.info.products:
            cost = _unit_cost(obs, p)
            comp = obs.last_competitor_prices.get(p) or []
            target = (min(comp) - 1.0) if comp else cost * 1.3
            prices[p] = round(max(cost * 1.02, target), 2)
        prod = _split_capacity(obs, 1.0)
        return Action(_bids_for(obs, prod, lambda m: _mat_price(obs, m) * 1.15), prod, prices)


class HighPricer(BaseAgent):
    """Margine alto, offerte basse: compra poco, vende caro."""

    def __init__(self, name="highpricer", markup=0.8):
        self.name, self.markup = name, markup

    def act(self, obs):
        prices = {p: round(_unit_cost(obs, p) * (1 + self.markup), 2) for p in obs.info.products}
        prod = _split_capacity(obs, 0.5)
        return Action(_bids_for(obs, prod, lambda m: _mat_price(obs, m) * 0.8), prod, prices)


class Overbidder(BaseAgent):
    """Offre tantissimo alle aste 'per essere sicuro di produrre': brucia margine."""

    def __init__(self, name="overbidder"):
        self.name = name

    def act(self, obs):
        prices = {}
        for p in obs.info.products:
            comp = obs.last_competitor_prices.get(p) or []
            prices[p] = round(sum(comp) / len(comp), 2) if comp else 40.0
        prod = _split_capacity(obs, 1.0)
        return Action(_bids_for(obs, prod, lambda m: _mat_price(obs, m, 8.0) * 1.5), prod, prices)


class RandomAgent(BaseAgent):
    """Azioni casuali ma valide."""

    def __init__(self, name="random", seed=None):
        self.name = name
        self.rng = random.Random(seed)

    def act(self, obs):
        prod = {p: self.rng.randint(0, obs.info.capacity // len(obs.info.products)) for p in obs.info.products}
        prices = {p: round(self.rng.uniform(15, 70), 2) for p in obs.info.products}
        return Action(_bids_for(obs, prod, lambda m: self.rng.uniform(2, 15)), prod, prices)
