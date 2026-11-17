"""
Memoria dell'agente: storia del mercato e stime aggiornate a ogni turno.
Qui si "impara" dai risultati del turno precedente.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from agent.estimators import EMA, mean
from agent.interface import Action, Observation


class Memory:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.ready = False
        self.last_action: Optional[Action] = None

    def _init(self, obs: Observation) -> None:
        a = self.cfg["ema_alpha"]
        info = obs.info
        self.ema_clear: Dict[str, EMA] = {m: EMA(a) for m in info.materials}
        self.winrate: Dict[str, EMA] = {m: EMA(0.5) for m in info.materials}
        self.premium: Dict[str, float] = {m: self.cfg["bid_premium"] for m in info.materials}
        self.ema_comp: Dict[str, EMA] = {p: EMA(a) for p in info.products}
        self.ema_sales: Dict[str, EMA] = {p: EMA(a) for p in info.products}
        self.margin: Dict[str, float] = {p: self.cfg["margin_init"] for p in info.products}
        self.demand_points: Dict[str, List[Tuple[float, float]]] = {p: [] for p in info.products}
        self.ready = True

    # ------------------------------------------------------------------
    def update(self, obs: Observation) -> None:
        if not self.ready:
            self._init(obs)
        if obs.turn == 0 or self.last_action is None:
            return
        cfg = self.cfg
        info = obs.info
        last = self.last_action

        # --- aste: prezzo d'aggiudicazione e tasso di vittoria ---
        requested: Dict[str, int] = {}
        for b in last.bids:
            requested[b.material] = requested.get(b.material, 0) + b.qty
        for m in info.materials:
            cp = obs.last_clearing_price.get(m)
            if cp is not None:
                self.ema_clear[m].update(cp)
            req = requested.get(m, 0)
            if req > 0:
                wr = self.winrate[m].update(min(1.0, obs.last_won.get(m, 0) / req))
                if wr >= cfg["winrate_high"]:
                    self.premium[m] -= cfg["premium_step"]
                elif wr < cfg["winrate_low"]:
                    self.premium[m] += cfg["premium_step"]
                self.premium[m] = min(cfg["premium_max"], max(cfg["premium_min"], self.premium[m]))

        # --- vendite: prezzi concorrenti, domanda, markup ---
        for p in info.products:
            comp = mean(obs.last_competitor_prices.get(p) or [])
            if comp is not None:
                self.ema_comp[p].update(comp)
            sold = obs.last_sales.get(p, 0)
            left = obs.product_inventory.get(p, 0)
            my_price = last.prices.get(p)
            offered = sold + left
            if my_price is None or offered <= 0:
                continue
            # se siamo andati sold-out la domanda vera era più alta: gonfia un po' la stima
            self.ema_sales[p].update(sold * (cfg["stockout_boost"] if left == 0 else 1.0))
            sellthrough = sold / offered
            if sellthrough >= cfg["sellthrough_high"]:
                self.margin[p] += cfg["margin_step"]
            elif sellthrough < cfg["sellthrough_low"]:
                self.margin[p] -= cfg["margin_step"]
            self.margin[p] = min(cfg["margin_max"], max(cfg["margin_min"], self.margin[p]))
            # punto di domanda solo se NON siamo andati sold-out (altrimenti la domanda vera è >= sold)
            if left > 0:
                pts = self.demand_points[p]
                pts.append((my_price, float(sold)))
                del pts[:-cfg["demand_window"]]

    # ------------------------------------------------------------------
    def material_price(self, m: str) -> float:
        return self.ema_clear[m].get(self.cfg["default_material_price"])

    def unit_cost(self, obs: Observation, p: str) -> float:
        """Costo di RIMPIAZZO di un'unità: materie prime ai prezzi correnti + lavorazione."""
        rec = obs.info.recipes[p]
        return obs.info.labor_cost[p] + sum(q * self.material_price(m) for m, q in rec.items())

    def expected_sales(self, obs: Observation, p: str) -> float:
        info = obs.info
        default = info.capacity / max(1, len(info.products)) * self.cfg["initial_sales_share"]
        return self.ema_sales[p].get(default)
