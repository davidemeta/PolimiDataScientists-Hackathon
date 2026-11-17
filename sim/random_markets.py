"""
Generatore di mercati CASUALI ("domain randomization"): tutto varia insieme, così si scoprono
i casi in cui l'agente va male senza doverli immaginare in anticipo.

Varia: numero di materie prime (1-5) e prodotti (1-4), ricette, capacità, costi di lavorazione,
SCALA dei prezzi (×0.1 … ×100), elasticità e dimensione del mercato, offerta di materie prime,
tipo d'asta, funzione di domanda, tempi della filiera, informazioni visibili, costi, cassa, durata.
"""
from __future__ import annotations

import math
import random
from typing import Dict

from sim.market import MarketConfig


def random_market(seed: int, turns=None) -> MarketConfig:
    """`turns`: lista di durate tra cui scegliere (es. [5, 8, 10, 12] per partite corte)."""
    r = random.Random(seed)
    scale = 10 ** r.uniform(-1, 2)                       # prezzi da ×0.1 a ×100 rispetto al mercato base
    n_mat = r.randint(1, 5)
    n_prod = r.randint(1, 4)
    materials = [f"M{i + 1}" for i in range(n_mat)]
    products = [f"P{j + 1}" for j in range(n_prod)]

    mat_ref = {m: 5.0 * scale * r.uniform(0.5, 2.0) for m in materials}   # prezzo "tipico" di ogni materiale
    recipes: Dict[str, Dict[str, int]] = {}
    for p in products:
        k = r.randint(1, min(3, n_mat))
        recipes[p] = {m: r.randint(1, 3) for m in r.sample(materials, k)}
    labor_zero = r.random() < 0.1                        # a volte la lavorazione è gratis (niente indizio di scala)
    labor = {p: 0.0 if labor_zero else round(scale * r.uniform(2, 10), 4) for p in products}
    cost_ref = {p: labor[p] + sum(q * mat_ref[m] for m, q in recipes[p].items()) for p in products}

    market_size = {p: r.uniform(10, 40) for p in products}
    k_logit = {p: r.uniform(1.5, 3.0) / cost_ref[p] for p in products}
    alpha = {p: k_logit[p] * cost_ref[p] * r.uniform(1.7, 2.3) for p in products}
    pmax = {p: cost_ref[p] * r.uniform(2.5, 4.5) for p in products}

    tightness = r.uniform(0.4, 1.6)                      # <1 materie prime scarse, >1 abbondanti
    supply = {}
    for m in materials:
        need = sum(recipes[p].get(m, 0) * market_size[p] for p in products)
        supply[m] = max(1.0, tightness * need * 0.8)
    capacity = r.randint(15, 120)

    return MarketConfig(
        n_turns=r.choice(turns or [8, 12, 20, 30, 30, 40, 60, 100]),
        start_cash=5000.0 * scale * r.uniform(0.3, 2.0),
        materials=materials, products=products, recipes=recipes, labor_cost=labor, capacity=capacity,
        holding_cost=cost_ref[products[0]] * r.uniform(0.0, 0.15),
        raw_holding_cost=min(mat_ref.values()) * r.uniform(0.0, 0.05),
        salvage_value=cost_ref[products[0]] * r.choice([0.0, 0.0, 0.0, r.uniform(0.2, 0.8)]),
        fixed_cost=5000.0 * scale * r.choice([0.0, 0.0, r.uniform(0.002, 0.02)]),
        sell_same_turn=r.random() < 0.7,
        production_after_auction=r.random() < 0.7,
        auction_type=r.choice(["pay_as_bid", "pay_as_bid", "uniform", "second_price"]),
        announce_auction_type=r.random() < 0.5,
        announce_supply=r.random() < 0.3,
        supply_per_agent=supply,
        supply_noise=r.uniform(0.0, 0.4),
        reserve_price={m: mat_ref[m] * r.uniform(0.05, 0.6) for m in materials},
        demand_model=r.choice(["logit", "logit", "linear", "cheapest_first"]),
        market_size_per_agent=market_size,
        demand_alpha=alpha, demand_k=k_logit, demand_pmax=pmax,
        demand_noise=r.uniform(0.0, 0.4),
        season_amplitude=r.uniform(0.0, 0.4),
        season_period=r.randint(6, 20),
        info_competitor_prices=r.random() < 0.8,
        info_clearing_price=r.random() < 0.8,
    )


def describe(mc: MarketConfig) -> dict:
    """Caratteristiche principali, per capire dove l'agente va male."""
    labor = sum(mc.labor_cost.values()) / max(1, len(mc.labor_cost))
    return dict(
        scale=round(min(mc.reserve_price.values()) / 0.3 / 5.0, 2) if mc.reserve_price else 1.0,
        materials=len(mc.materials), products=len(mc.products), turns=mc.n_turns, capacity=mc.capacity,
        auction=mc.auction_type, known_auction=mc.announce_auction_type, demand=mc.demand_model,
        same_turn=mc.sell_same_turn, prod_after=mc.production_after_auction,
        comp_info=mc.info_competitor_prices, clear_info=mc.info_clearing_price,
        labor_zero=labor == 0.0, salvage=mc.salvage_value > 0, fixed=mc.fixed_cost > 0,
        log_scale=round(math.log10(max(1e-9, (mc.start_cash / 5000.0))), 2),
    )
