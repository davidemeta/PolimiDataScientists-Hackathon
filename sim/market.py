"""
Simulatore di PROVA del mercato. Non è quello degli organizzatori: serve per
testare robustezza e confrontare varianti dell'agente. Ogni aspetto incerto del
gioco vero è un'opzione di MarketConfig (vedi sim/scenarios.py per le combinazioni).

Ordine degli eventi in un turno (default):
  1. tutti gli agenti decidono simultaneamente (offerte, produzione, prezzi)
  2. aste a busta chiusa per ogni materia prima
  3. produzione (con production_after_auction=False avviene PRIMA delle aste)
  4. vendite (con sell_same_turn=False si vende solo ciò che era già in magazzino)
  5. costi di magazzino e costi fissi
Punteggio finale = cassa + valore di recupero delle scorte.
"""
from __future__ import annotations

import copy
import math
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from agent.interface import Action, BaseAgent, Bid, GameInfo, Observation


@dataclass
class MarketConfig:
    n_turns: int = 30
    start_cash: float = 5000.0
    materials: List[str] = field(default_factory=lambda: ["A", "B"])
    products: List[str] = field(default_factory=lambda: ["P1", "P2"])
    recipes: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
        "P1": {"A": 2, "B": 1},
        "P2": {"A": 1, "B": 2},
    })
    labor_cost: Dict[str, float] = field(default_factory=lambda: {"P1": 5.0, "P2": 8.0})
    capacity: int = 60
    holding_cost: float = 0.5
    raw_holding_cost: float = 0.1
    salvage_value: float = 0.0
    fixed_cost: float = 0.0                   # costo fisso per turno (affitto)
    # --- tempi ---
    sell_same_turn: bool = True               # False: ciò che produci oggi si vende da domani
    production_after_auction: bool = True     # False: si produce solo con materiali già in magazzino
    # --- aste ---
    auction_type: str = "pay_as_bid"          # "pay_as_bid" | "uniform" | "second_price"
    announce_auction_type: bool = False       # l'agente conosce il tipo d'asta (GameInfo.auction_type)?
    announce_supply: bool = False             # l'agente vede le unità in vendita prima di offrire?
    supply_per_agent: Dict[str, float] = field(default_factory=lambda: {"A": 40.0, "B": 40.0})
    supply_noise: float = 0.25
    reserve_price: Dict[str, float] = field(default_factory=lambda: {"A": 1.0, "B": 1.0})
    # --- domanda ---
    demand_model: str = "logit"               # "logit" | "linear" | "cheapest_first"
    market_size_per_agent: Dict[str, float] = field(default_factory=lambda: {"P1": 30.0, "P2": 22.0})
    demand_alpha: Dict[str, float] = field(default_factory=lambda: {"P1": 4.0, "P2": 4.5})   # logit
    demand_k: Dict[str, float] = field(default_factory=lambda: {"P1": 0.10, "P2": 0.08})     # logit
    demand_pmax: Dict[str, float] = field(default_factory=lambda: {"P1": 70.0, "P2": 80.0})  # linear / cheapest_first
    linear_share_elasticity: float = 4.0      # linear: quota ∝ (p_media / p_i)^elasticità
    demand_noise: float = 0.15
    season_amplitude: float = 0.2
    season_period: int = 12
    # --- informazioni visibili agli agenti ---
    info_competitor_prices: bool = True
    info_clearing_price: bool = True


@dataclass
class _AgentState:
    cash: float
    raw: Dict[str, int]
    prod: Dict[str, int]


class Market:
    def __init__(self, agents: List[BaseAgent], config: Optional[MarketConfig] = None,
                 seed: int = 0, time_limit: float = 1.0):
        self.cfg = config or MarketConfig()
        self.rng = random.Random(seed)
        self.agents = agents
        self.time_limit = time_limit
        c = self.cfg
        n = len(agents)
        self.info = GameInfo(
            n_turns=c.n_turns, n_agents=n, materials=list(c.materials), products=list(c.products),
            recipes=copy.deepcopy(c.recipes), labor_cost=dict(c.labor_cost), capacity=c.capacity,
            holding_cost=c.holding_cost, raw_holding_cost=c.raw_holding_cost,
            salvage_value=c.salvage_value, sell_same_turn=c.sell_same_turn,
            production_after_auction=c.production_after_auction,
            auction_type=c.auction_type if c.announce_auction_type else None,
        )
        self.states = [_AgentState(c.start_cash, {m: 0 for m in c.materials}, {p: 0 for p in c.products})
                       for _ in agents]
        self.last: List[dict] = [{} for _ in agents]
        self.last_public_prices: Dict[str, Dict[int, float]] = {p: {} for p in c.products}
        self.last_clearing: Dict[str, Optional[float]] = {m: None for m in c.materials}
        self.last_supply: Dict[str, int] = {}
        self.current_supply: Dict[str, int] = {}
        self.errors = [0] * n
        self.invalid = [0] * n
        self.max_time = [0.0] * n
        self.history: List[dict] = []

    # ------------------------------------------------------------------ API
    def run(self) -> List[float]:
        for t in range(self.cfg.n_turns):
            self.step(t)
        return self.scores()

    def scores(self) -> List[float]:
        sv = self.cfg.salvage_value
        return [s.cash + sv * sum(s.prod.values()) for s in self.states]

    # ------------------------------------------------------------- un turno
    def step(self, t: int) -> None:
        c = self.cfg
        n = len(self.agents)
        # con l'offerta annunciata la si estrae prima delle decisioni (altrimenti dopo, come sempre)
        self.current_supply = {m: self._draw_supply(m) for m in c.materials} if c.announce_supply else {}
        actions = [self._get_action(i, t) for i in range(n)]

        produced = [{p: 0 for p in c.products} for _ in range(n)]
        if not c.production_after_auction:
            self._produce(actions, produced)

        # --- aste ---
        won = [{m: 0 for m in c.materials} for _ in range(n)]
        paid = [{m: 0.0 for m in c.materials} for _ in range(n)]
        supply = {}
        for m in c.materials:
            s = self.current_supply[m] if c.announce_supply else self._draw_supply(m)
            supply[m] = s
            bids_by_agent = {i: [b for b in actions[i].bids if b.material == m] for i in range(n)}
            self.last_clearing[m] = self._auction(m, bids_by_agent, s, won, paid)
        self.last_supply = supply

        if c.production_after_auction:
            self._produce(actions, produced)

        # --- vendite ---
        season = 1 + c.season_amplitude * math.sin(2 * math.pi * t / c.season_period)
        sales = [{p: 0 for p in c.products} for _ in range(n)]
        public = {p: {} for p in c.products}
        for p in c.products:
            size = c.market_size_per_agent[p] * n * season * (1 + self.rng.uniform(-c.demand_noise, c.demand_noise))
            sellable = {i: self.states[i].prod[p] - (0 if c.sell_same_turn else produced[i][p]) for i in range(n)}
            sellers = [i for i in range(n) if sellable[i] > 0 and p in actions[i].prices]
            for i in sellers:
                public[p][i] = actions[i].prices[p]
            demand = self._demand(p, size, {i: actions[i].prices[p] for i in sellers}, sellable)
            for i, q in demand.items():
                q = max(0, min(sellable[i], q))
                self.states[i].prod[p] -= q
                self.states[i].cash += q * actions[i].prices[p]
                sales[i][p] = q
        self.last_public_prices = public

        # --- magazzino e costi fissi ---
        for st in self.states:
            st.cash -= (c.holding_cost * sum(st.prod.values()) + c.raw_holding_cost * sum(st.raw.values())
                        + c.fixed_cost)

        for i in range(n):
            self.last[i] = dict(won=won[i], paid=paid[i], produced=produced[i], sales=sales[i])
        self.history.append(dict(turn=t, supply=supply, clearing=dict(self.last_clearing),
                                 prices={p: dict(v) for p, v in public.items()},
                                 cash=[s.cash for s in self.states]))

    # ------------------------------------------------------------ domanda
    def _demand(self, p: str, size: float, prices: Dict[int, float], stock: Dict[int, int]) -> Dict[int, int]:
        c = self.cfg
        if not prices:
            return {}
        if c.demand_model == "logit":
            util = {i: math.exp(c.demand_alpha[p] - c.demand_k[p] * pr) for i, pr in prices.items()}
            denom = 1.0 + sum(util.values())
            return {i: int(round(size * u / denom)) for i, u in util.items()}
        pmax = c.demand_pmax[p]
        if c.demand_model == "linear":
            # domanda totale lineare nel prezzo medio, divisa in quote che premiano chi costa meno
            pmean = sum(prices.values()) / len(prices)
            total = max(0.0, 1.8 * size * (1 - pmean / pmax))
            w = {i: (pmean / max(pr, 0.01)) ** c.linear_share_elasticity for i, pr in prices.items()}
            sw = sum(w.values())
            return {i: int(round(total * wi / sw)) for i, wi in w.items()}
        if c.demand_model == "cheapest_first":
            # clienti con prezzo massimo uniforme in [0, pmax]: comprano dal più economico che ha scorte
            customers = 1.8 * size
            served = 0.0
            out = {}
            for i in sorted(prices, key=lambda j: (prices[j], self.rng.random())):
                willing = max(0.0, customers * (1 - prices[i] / pmax) - served)
                q = int(min(stock[i], willing))
                out[i] = q
                served += q
            return out
        raise ValueError(f"demand_model sconosciuto: {c.demand_model}")

    # ------------------------------------------------------------- helpers
    def _draw_supply(self, m: str) -> int:
        c = self.cfg
        mean = c.supply_per_agent[m] * len(self.agents)
        return max(0, int(round(mean * (1 + self.rng.uniform(-c.supply_noise, c.supply_noise)))))

    def _produce(self, actions: List[Action], produced: List[Dict[str, int]]) -> None:
        c = self.cfg
        for i, a in enumerate(actions):
            st = self.states[i]
            cap_left = c.capacity
            for p, q in a.production.items():
                rec = c.recipes[p]
                q = min(q, cap_left, *(st.raw[m] // need for m, need in rec.items()))
                if c.labor_cost[p] > 0:
                    q = min(q, int(max(0.0, st.cash) // c.labor_cost[p]))
                q = max(0, q)
                for m, need in rec.items():
                    st.raw[m] -= need * q
                st.prod[p] += q
                st.cash -= c.labor_cost[p] * q
                cap_left -= q
                produced[i][p] = q

    def _observation(self, i: int, t: int) -> Observation:
        c = self.cfg
        st = self.states[i]
        last = self.last[i]
        comp = {p: [pr for j, pr in self.last_public_prices[p].items() if j != i] for p in c.products}
        return Observation(
            turn=t, info=copy.deepcopy(self.info), cash=st.cash,
            raw_inventory=dict(st.raw), product_inventory=dict(st.prod),
            last_won=dict(last.get("won", {})), last_paid=dict(last.get("paid", {})),
            last_clearing_price=dict(self.last_clearing) if (t > 0 and c.info_clearing_price) else {},
            last_supply=dict(self.last_supply), last_produced=dict(last.get("produced", {})),
            last_sales=dict(last.get("sales", {})),
            last_competitor_prices=comp if (t > 0 and c.info_competitor_prices) else {},
            current_supply=dict(self.current_supply),
        )

    def _get_action(self, i: int, t: int) -> Action:
        obs = self._observation(i, t)
        t0 = time.perf_counter()
        try:
            a = self.agents[i].act(obs)
        except Exception:
            self.errors[i] += 1
            a = Action()
        dt = time.perf_counter() - t0
        self.max_time[i] = max(self.max_time[i], dt)
        if dt > self.time_limit:          # come farebbe un server vero: turno perso
            self.errors[i] += 1
            a = Action()
        return self._sanitize(i, a)

    def _sanitize(self, i: int, a) -> Action:
        """Scarta le parti non valide (e le conta), come farebbe un server."""
        c = self.cfg
        out = Action()
        if not isinstance(a, Action):
            self.invalid[i] += 1
            return out
        for b in a.bids or []:
            ok = (isinstance(b, Bid) and b.material in c.materials and _finite(b.price)
                  and b.price > 0 and isinstance(b.qty, int) and b.qty > 0)
            if ok:
                out.bids.append(b)
            else:
                self.invalid[i] += 1
        for p, q in (a.production or {}).items():
            if p in c.products and isinstance(q, int) and q >= 0:
                out.production[p] = q
            else:
                self.invalid[i] += 1
        for p, pr in (a.prices or {}).items():
            if p in c.products and _finite(pr) and pr > 0:
                out.prices[p] = float(pr)
            else:
                self.invalid[i] += 1
        return out

    def _auction(self, m, bids_by_agent, supply, won, paid) -> Optional[float]:
        """
        Asta multi-unità a busta chiusa. Le offerte si servono dalla più alta, finché ci sono unità.
          pay_as_bid   → ognuno paga la propria offerta
          uniform      → tutti pagano il prezzo vincente più basso
          second_price → tutti pagano la prima offerta ESCLUSA (o il prezzo minimo se nessuno è escluso)
        Ritorna il prezzo d'aggiudicazione pubblicato (il prezzo vincente più basso; per
        second_price il prezzo effettivamente pagato).
        """
        c = self.cfg
        units = []
        for i, bids in bids_by_agent.items():
            budget = max(0.0, self.states[i].cash)
            for b in sorted(bids, key=lambda b: -b.price):
                if b.price < c.reserve_price[m]:
                    continue
                q = min(b.qty, int(budget // b.price))
                if q <= 0:
                    continue
                budget -= q * b.price
                units.append((b.price, self.rng.random(), i, q))
        units.sort(key=lambda u: (-u[0], u[1]))
        remaining = supply
        alloc = []
        first_losing: Optional[float] = None
        for price, _, i, q in units:
            if remaining <= 0:
                first_losing = price if first_losing is None else first_losing
                break
            take = min(q, remaining)
            remaining -= take
            alloc.append((i, price, take))
            if take < q and first_losing is None:
                first_losing = price          # offerta servita solo in parte: è il prezzo marginale
        if not alloc:
            return None
        clearing = min(p for _, p, _ in alloc)
        if c.auction_type == "second_price":
            clearing = first_losing if first_losing is not None else c.reserve_price[m]
        for i, price, take in alloc:
            unit_price = price if c.auction_type == "pay_as_bid" else clearing
            self.states[i].cash -= unit_price * take
            self.states[i].raw[m] += take
            won[i][m] += take
            paid[i][m] += unit_price * take
        return clearing


def _finite(x) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False
