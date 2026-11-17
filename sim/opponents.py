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


# ---------------------------------------------------------------------------
# Avversari aggiuntivi: comportamenti plausibili di altre squadre
# ---------------------------------------------------------------------------

def _mean_comp(obs: Observation, p: str):
    comp = obs.last_competitor_prices.get(p) or []
    return sum(comp) / len(comp) if comp else None


class Copycat(BaseAgent):
    """Copia il prezzo medio dei concorrenti e offre l'ultimo prezzo d'aggiudicazione."""

    def __init__(self, name="copycat"):
        self.name = name

    def act(self, obs):
        prices = {}
        for p in obs.info.products:
            mc = _mean_comp(obs, p)
            prices[p] = round(mc if mc else _unit_cost(obs, p) * 1.4, 2)
        prod = _split_capacity(obs, 0.7)
        return Action(_bids_for(obs, prod, lambda m: _mat_price(obs, m, 6.0)), prod, prices)


class Colluder(BaseAgent):
    """Prezzi alti (collusione tacita); se qualcuno taglia sotto di lui, punisce per 2 turni (tit-for-tat)."""

    def __init__(self, name="colluder", markup=0.9, punish_turns=2):
        self.name, self.markup, self.punish_turns = name, markup, punish_turns
        self.punish_left = 0
        self.last_prices: Dict[str, float] = {}

    def act(self, obs):
        if obs.turn == 0:
            self.punish_left, self.last_prices = 0, {}
        for p, mine in self.last_prices.items():
            comp = obs.last_competitor_prices.get(p) or []
            if comp and min(comp) < mine * 0.9:
                self.punish_left = self.punish_turns
        prices = {}
        for p in obs.info.products:
            cost = _unit_cost(obs, p)
            prices[p] = round(cost * (1.05 if self.punish_left > 0 else 1 + self.markup), 2)
        self.punish_left = max(0, self.punish_left - 1)
        self.last_prices = dict(prices)
        prod = _split_capacity(obs, 0.6)
        return Action(_bids_for(obs, prod, lambda m: _mat_price(obs, m)), prod, prices)


class Hoarder(BaseAgent):
    """Prova a comprare TUTTA l'offerta di un materiale per bloccare gli altri."""

    def __init__(self, name="hoarder", target=None):
        self.name, self.target = name, target

    def act(self, obs):
        info = obs.info
        target = self.target or max(info.materials, key=lambda m: sum(r.get(m, 0) for r in info.recipes.values()))
        supply = obs.current_supply.get(target) or obs.last_supply.get(target) or 40 * info.n_agents
        price = _mat_price(obs, target, 6.0) * 1.3
        qty = int(min(supply, obs.cash * 0.4 // max(price, 0.01)))
        prod = _split_capacity(obs, 1.0)
        bids = [b for b in _bids_for(obs, prod, lambda m: _mat_price(obs, m) * 1.05) if b.material != target]
        if qty > 0:
            bids.append(Bid(target, round(price, 2), qty))
        prices = {}
        for p in info.products:
            mc = _mean_comp(obs, p)
            prices[p] = round(mc if mc else _unit_cost(obs, p) * 1.4, 2)
        return Action(bids, prod, prices)


class Dumper(BaseAgent):
    """Svende SOTTO costo per la prima parte della partita (conquista quota), poi rialza."""

    def __init__(self, name="dumper", dump_share=0.6):
        self.name, self.dump_share = name, dump_share

    def act(self, obs):
        dumping = obs.turn < obs.info.n_turns * self.dump_share
        prices = {p: round(_unit_cost(obs, p) * (0.9 if dumping else 1.25), 2) for p in obs.info.products}
        prod = _split_capacity(obs, 1.0)
        return Action(_bids_for(obs, prod, lambda m: _mat_price(obs, m) * 1.1), prod, prices)


class BanditPricer(BaseAgent):
    """La squadra 'con l'AI': sceglie il markup con epsilon-greedy su 5 livelli, premiando il profitto."""

    ARMS = (0.1, 0.25, 0.4, 0.6, 0.9)

    def __init__(self, name="bandit", eps=0.15, seed=None):
        self.name, self.eps = name, eps
        self.rng = random.Random(seed)
        self._reset()

    def _reset(self):
        self.value = {a: 0.0 for a in self.ARMS}
        self.count = {a: 0 for a in self.ARMS}
        self.last_arm = None
        self.last_cost: Dict[str, float] = {}

    def act(self, obs):
        if obs.turn == 0:
            self._reset()
        if self.last_arm is not None:
            reward = sum(obs.last_sales.get(p, 0) * self.last_cost.get(p, 0) * self.last_arm
                         for p in obs.info.products)
            a = self.last_arm
            self.count[a] += 1
            self.value[a] += (reward - self.value[a]) / self.count[a]
        untried = [a for a in self.ARMS if self.count[a] == 0]
        if untried:
            arm = untried[0]
        elif self.rng.random() < self.eps:
            arm = self.rng.choice(self.ARMS)
        else:
            arm = max(self.ARMS, key=lambda a: self.value[a])
        self.last_arm = arm
        self.last_cost = {p: _unit_cost(obs, p) for p in obs.info.products}
        prices = {p: round(c * (1 + arm), 2) for p, c in self.last_cost.items()}
        prod = _split_capacity(obs, 0.8)
        return Action(_bids_for(obs, prod, lambda m: _mat_price(obs, m) * 1.1), prod, prices)


class Sniper(BaseAgent):
    """Offre l'ultimo prezzo d'aggiudicazione + 1 centesimo; prezzi a markup fisso."""

    def __init__(self, name="sniper", markup=0.35):
        self.name, self.markup = name, markup

    def act(self, obs):
        prices = {p: round(_unit_cost(obs, p) * (1 + self.markup), 2) for p in obs.info.products}
        prod = _split_capacity(obs, 0.8)
        return Action(_bids_for(obs, prod, lambda m: _mat_price(obs, m, 6.0) + 0.01), prod, prices)


def opponent_pool(seed: int):
    """Tutti i tipi di avversario, per estrarre lineup casuali ('league')."""
    from agent.config import STABLE_CONFIG
    from agent.core import SmartAgent
    return [
        lambda k: Undercutter(f"undercutter{k}"),
        lambda k: HighPricer(f"highpricer{k}"),
        lambda k: Overbidder(f"overbidder{k}"),
        lambda k: RandomAgent(f"random{k}", seed=seed + k),
        lambda k: FixedAgent(f"fixed{k}"),
        lambda k: Copycat(f"copycat{k}"),
        lambda k: Colluder(f"colluder{k}"),
        lambda k: Hoarder(f"hoarder{k}"),
        lambda k: Dumper(f"dumper{k}"),
        lambda k: BanditPricer(f"bandit{k}", seed=seed + k),
        lambda k: Sniper(f"sniper{k}"),
        lambda k: SmartAgent(f"v1_{k}", STABLE_CONFIG),
    ]


def league(seed: int, min_n: int = 3, max_n: int = 7):
    """Lineup casuale ma riproducibile: da min_n a max_n avversari estratti dalla libreria."""
    rng = random.Random(10_000 + seed)
    pool = opponent_pool(seed)
    n = rng.randint(min_n, max_n)
    return [rng.choice(pool)(k) for k in range(n)]
