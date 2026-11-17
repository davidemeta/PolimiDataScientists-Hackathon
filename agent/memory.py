"""
Memoria dell'agente: storia del mercato e stime aggiornate a ogni turno.
Qui si "impara" dai risultati del turno precedente.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from agent.estimators import EMA, Holt, mean
from agent.interface import Action, Observation


class Memory:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.ready = False
        self.last_action: Optional[Action] = None

    def _init(self, obs: Observation) -> None:
        cfg = self.cfg
        a = cfg["ema_alpha"]
        info = obs.info
        # prezzi d'aggiudicazione: EMA semplice (vecchio metodo) e Holt con trend (nuovo)
        self.ema_clear: Dict[str, EMA] = {m: EMA(a) for m in info.materials}
        self.holt_clear: Dict[str, Holt] = {
            m: Holt(cfg["holt_alpha"], cfg["holt_beta"], cfg["holt_phi"]) for m in info.materials}
        self.winrate: Dict[str, EMA] = {m: EMA(0.5) for m in info.materials}
        self.last_winrate: Dict[str, Optional[float]] = {m: None for m in info.materials}
        self.premium: Dict[str, float] = {m: cfg["bid_premium"] for m in info.materials}
        self.clear_hist: Dict[str, List[float]] = {m: [] for m in info.materials}
        self.supply_hist: Dict[str, List[int]] = {m: [] for m in info.materials}
        # rincorsa: magazzino che cresce / vendite che non tengono il passo
        self.prev_total_stock: Optional[int] = None
        self.stock_growing = False
        self.last_sellthrough: Optional[float] = None
        # vendite e concorrenti
        self.ema_comp: Dict[str, EMA] = {p: EMA(a) for p in info.products}
        self.prev_comp: Dict[str, Optional[float]] = {p: None for p in info.products}
        self.ema_sales: Dict[str, EMA] = {p: EMA(a) for p in info.products}
        self.stockout_streak: Dict[str, int] = {p: 0 for p in info.products}
        self.last_boost: Dict[str, float] = {p: 1.0 for p in info.products}
        self.margin: Dict[str, float] = {p: cfg["margin_init"] for p in info.products}
        # prezzo "confermato dal mercato": media dei nostri prezzi nei turni in cui abbiamo venduto quasi tutto
        self.confirmed_price: Dict[str, EMA] = {p: EMA(a) for p in info.products}
        self.demand_points: Dict[str, List[Tuple[float, float]]] = {p: [] for p in info.products}
        self.ready = True

    # ------------------------------------------------------------------
    def update(self, obs: Observation) -> None:
        if not self.ready:
            self._init(obs)
        if obs.turn == 0 or self.last_action is None:
            return
        info = obs.info
        last = self.last_action
        self._update_auctions(obs, last)
        for p in info.products:
            self._update_product(obs, last, p)
        total_stock = sum(obs.product_inventory.get(p, 0) for p in info.products)
        sold = sum(obs.last_sales.get(p, 0) for p in info.products)
        self.stock_growing = self.prev_total_stock is not None and total_stock > self.prev_total_stock
        self.prev_total_stock = total_stock
        self.last_sellthrough = sold / (sold + total_stock) if sold + total_stock > 0 else None

    def _update_auctions(self, obs: Observation, last: Action) -> None:
        cfg = self.cfg
        requested: Dict[str, int] = {}
        for b in last.bids:
            requested[b.material] = requested.get(b.material, 0) + b.qty
        for m in obs.info.materials:
            if obs.last_supply.get(m) is not None:
                self.supply_hist[m].append(obs.last_supply[m])
                del self.supply_hist[m][:-10]
            req = requested.get(m, 0)
            cp = obs.last_clearing_price.get(m)
            if cp is None and cfg["infer_clearing"] and req > 0:
                cp = self._implied_clearing(m, last, obs)
            if cp is not None:
                self.ema_clear[m].update(cp)
                self.holt_clear[m].update(cp)
                self.clear_hist[m].append(cp)
            if req <= 0:
                continue
            raw_wr = min(1.0, obs.last_won.get(m, 0) / req)
            self.last_winrate[m] = raw_wr
            ema_wr = self.winrate[m].update(raw_wr)
            if cfg["premium_mode"] == "fast":
                # reazione al turno appena giocato (niente media = niente ritardo),
                # e discesa più rapida della salita: strapagare costa su OGNI unità
                if raw_wr >= cfg["winrate_high"]:
                    self.premium[m] -= cfg["premium_step_down"]
                elif raw_wr < cfg["winrate_low"]:
                    self.premium[m] += cfg["premium_step"]
            else:  # "ema": vecchio comportamento
                if ema_wr >= cfg["winrate_high"]:
                    self.premium[m] -= cfg["premium_step"]
                elif ema_wr < cfg["winrate_low"]:
                    self.premium[m] += cfg["premium_step"]
            self.premium[m] = min(cfg["premium_max"], max(cfg["premium_min"], self.premium[m]))

    def _implied_clearing(self, m: str, last: Action, obs: Observation) -> Optional[float]:
        """
        Prezzo d'aggiudicazione NON visibile: lo deduciamo dalle nostre offerte e da cosa abbiamo vinto.
          - pagato in media meno della nostra offerta più bassa → asta a prezzo unico: il pagato È il prezzo
          - vinto tutto   → il prezzo era sotto la nostra offerta più bassa: proviamo a scendere
          - vinto niente  → il prezzo era sopra la nostra offerta più alta: proviamo a salire
          - vinto in parte → il prezzo è circa quello dell'offerta servita per ultima
        """
        cfg = self.cfg
        bids = sorted((b for b in last.bids if b.material == m), key=lambda b: -b.price)
        if not bids:
            return None
        req = sum(b.qty for b in bids)
        won = obs.last_won.get(m, 0)
        paid = obs.last_paid.get(m, 0.0)
        lo, hi = bids[-1].price, bids[0].price
        if won > 0 and paid / won < lo - 1e-6:
            return paid / won
        if won >= req:
            return lo * (1 - cfg["probe_down"])
        if won == 0:
            return hi * (1 + cfg["probe_up"])
        filled = 0
        for b in bids:
            filled += b.qty
            if filled >= won:
                return b.price
        return lo

    def _update_product(self, obs: Observation, last: Action, p: str) -> None:
        cfg = self.cfg
        comp = mean(obs.last_competitor_prices.get(p) or [])
        comp_rising = False
        if comp is not None:
            prev = self.prev_comp[p]
            comp_rising = prev is not None and comp > prev * (1 + cfg["comp_rise_threshold"])
            self.prev_comp[p] = comp
            self.ema_comp[p].update(comp)

        sold = obs.last_sales.get(p, 0)
        left = obs.product_inventory.get(p, 0)
        if not obs.info.sell_same_turn:
            # i pezzi prodotti nel turno scorso non erano in vendita: non contano come "invenduti"
            left = max(0, left - obs.last_produced.get(p, 0))
        my_price = last.prices.get(p)
        offered = sold + left
        if my_price is None or offered <= 0:
            return

        if cfg["demand_estimator"] == "adaptive":
            self._update_demand_adaptive(p, sold, left, comp_rising)
        else:  # "ema": vecchio comportamento
            self.ema_sales[p].update(sold * (cfg["stockout_boost"] if left == 0 else 1.0))

        sellthrough = sold / offered
        if sellthrough >= cfg["sellthrough_high"]:
            self.confirmed_price[p].update(my_price)
            self.margin[p] += cfg["margin_step"]
        elif sellthrough < cfg["sellthrough_low"]:
            self.margin[p] -= cfg["margin_step"]
        self.margin[p] = min(cfg["margin_max"], max(cfg["margin_min"], self.margin[p]))
        # punto di domanda solo se NON siamo andati sold-out (altrimenti la domanda vera è >= sold)
        if left > 0:
            pts = self.demand_points[p]
            pts.append((my_price, float(sold)))
            del pts[:-cfg["demand_window"]]

    def _update_demand_adaptive(self, p: str, sold: int, left: int, comp_rising: bool) -> None:
        """
        Sold-out → la domanda vera è >= vendite. Crescita che ACCELERA con i sold-out consecutivi
        (come lo 'slow start' di TCP), più veloce se anche i concorrenti alzano i prezzi
        (segnale che il prodotto scarseggia per tutti). Appena restano scorte, si taglia in fretta.
        """
        cfg = self.cfg
        est = self.ema_sales[p]
        if left == 0:
            self.stockout_streak[p] += 1
            k = self.stockout_streak[p]
            boost = min(cfg["stockout_boost_max"], cfg["stockout_boost_base"] ** k)
            if comp_rising:
                boost *= 1 + cfg["comp_rise_bonus"]
            self.last_boost[p] = boost
            candidate = sold * boost
            # con il sold-out non abbiamo prove che la domanda sia scesa: la stima non si abbassa
            est.value = candidate if est.value is None else max(est.value, candidate)
        else:
            self.stockout_streak[p] = 0
            self.last_boost[p] = 1.0
            # domanda osservata davvero (non censurata): aggiornamento rapido verso il dato
            a = cfg["sales_down_alpha"]
            est.value = sold if est.value is None else a * sold + (1 - a) * est.value

    # ------------------------------------------------------------------
    def escalating(self, m: str) -> bool:
        """
        Rincorsa sui prezzi d'asta: il prezzo d'aggiudicazione di m è salito per N turni di fila
        E le nostre vendite non tengono il passo (magazzino che cresce o sell-through basso).
        Se il prezzo sale ma vendiamo tutto, la domanda giustifica la salita: non è una rincorsa.
        """
        cfg = self.cfg
        n = cfg["escalation_turns"]
        h = self.clear_hist[m]
        if len(h) < n + 1:
            return False
        rising = all(h[-i] > h[-i - 1] * (1 + cfg["escalation_min_rise"]) for i in range(1, n + 1))
        weak_sales = self.stock_growing or (
            self.last_sellthrough is not None and self.last_sellthrough < cfg["escalation_sellthrough"])
        return rising and weak_sales

    def value_price(self, p: str, our_price: float) -> float:
        """
        Prezzo di vendita usato per calcolare il VALORE delle materie prime. Con il prezzo
        'costo + margine' il valore sale insieme al costo dei materiali (circolo vizioso):
        lo ancoriamo al prezzo a cui il mercato ha davvero comprato tutto.
        """
        conf = self.confirmed_price[p].value
        if self.cfg["value_anchor"] != "confirmed" or conf is None:
            return our_price
        return min(our_price, conf * (1 + self.cfg["value_anchor_slack"]))

    def clearing_forecast(self, m: str) -> Optional[float]:
        """Previsione del prezzo d'aggiudicazione del PROSSIMO turno (None se nessun dato)."""
        if self.cfg["price_forecast"] == "holt":
            return self.holt_clear[m].forecast()
        return self.ema_clear[m].value

    def material_price(self, m: str) -> float:
        v = self.clearing_forecast(m)
        return self.cfg["default_material_price"] if v is None else v

    def unit_cost(self, obs: Observation, p: str) -> float:
        """Costo di RIMPIAZZO di un'unità: materie prime ai prezzi correnti + lavorazione."""
        rec = obs.info.recipes[p]
        return obs.info.labor_cost[p] + sum(q * self.material_price(m) for m, q in rec.items())

    def expected_sales(self, obs: Observation, p: str) -> float:
        info = obs.info
        default = info.capacity / max(1, len(info.products)) * self.cfg["initial_sales_share"]
        return self.ema_sales[p].get(default)
