"""
Test di robustezza: l'agente non deve MAI crashare né produrre azioni invalide.
Lanciateli prima di ogni submission:

  python3 tests/test_robustness.py
  (oppure: python3 -m pytest tests/)
"""
from __future__ import annotations

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core import SmartAgent  # noqa: E402
from sim.interface import Action, GameInfo, Observation  # noqa: E402
from sim.market import Market, MarketConfig  # noqa: E402
from sim.opponents import Overbidder, RandomAgent, Undercutter  # noqa: E402


def _run(cfg: MarketConfig, n_opp: int = 3, seed: int = 0):
    ours = SmartAgent("team", debug=True)          # debug=True: un'eccezione fa fallire il test
    agents = [ours] + [RandomAgent(f"r{k}", seed=seed + k) for k in range(n_opp)]
    m = Market(agents, cfg, seed=seed)
    scores = m.run()
    assert m.errors[0] == 0, "l'agente ha sollevato eccezioni"
    assert m.invalid[0] == 0, f"{m.invalid[0]} azioni invalide"
    assert m.max_time[0] < 0.1, f"troppo lento: {m.max_time[0]:.3f}s per turno"
    return scores[0]


def test_default_game():
    _run(MarketConfig())


def test_many_seeds():
    for s in range(30):
        _run(MarketConfig(), seed=s)


def test_no_supply():
    _run(MarketConfig(supply_per_agent={"A": 0, "B": 0}))


def test_huge_supply():
    _run(MarketConfig(supply_per_agent={"A": 1000, "B": 1000}))


def test_no_cash():
    _run(MarketConfig(start_cash=0.0))


def test_tiny_cash():
    _run(MarketConfig(start_cash=3.0))


def test_alone():
    _run(MarketConfig(), n_opp=0)


def test_one_turn():
    _run(MarketConfig(n_turns=1))


def test_two_turns():
    _run(MarketConfig(n_turns=2))


def test_zero_demand():
    _run(MarketConfig(market_size_per_agent={"P1": 0.0, "P2": 0.0}))


def test_uniform_auction():
    _run(MarketConfig(auction_type="uniform"))


def test_single_product():
    _run(MarketConfig(products=["P1"], recipes={"P1": {"A": 2, "B": 1}}, labor_cost={"P1": 5.0},
                      market_size_per_agent={"P1": 30.0}, demand_alpha={"P1": 4.0}, demand_k={"P1": 0.1}))


def test_salvage_value():
    _run(MarketConfig(salvage_value=10.0))


def test_vs_aggressive():
    ours = SmartAgent("team", debug=True)
    m = Market([ours, Undercutter(), Overbidder()], MarketConfig(), seed=1)
    m.run()
    assert m.errors[0] == 0 and m.invalid[0] == 0


def test_same_instance_two_games():
    """Il valutatore potrebbe riusare lo stesso agente per più partite: niente stato che 'trapela'."""
    ours = SmartAgent("team", debug=True)
    for seed, cfg in [(0, MarketConfig(n_turns=30)), (1, MarketConfig(n_turns=10, start_cash=500.0))]:
        m = Market([ours, RandomAgent(seed=seed)], cfg, seed=seed)
        m.run()
        assert m.errors[0] == 0 and m.invalid[0] == 0
    fresh = SmartAgent("fresh")
    m2 = Market([fresh, RandomAgent(seed=1)], MarketConfig(n_turns=10, start_cash=500.0), seed=1)
    m2.run()
    # dopo il reset, la memoria dev'essere quella di una partita da 10 turni, non 30+10
    assert ours._prev_turn == 9
    assert ours.mem.margin == fresh.mem.margin, "la memoria non è stata resettata tra le partite"


def test_all_scenarios_all_profiles():
    """Ogni scenario del catalogo × ogni profilo: nessuna eccezione, nessuna azione invalida, veloce."""
    from agent.config import PROFILES, make_config
    from sim.opponents import league
    from sim.scenarios import SCENARIOS
    for name, mc in SCENARIOS.items():
        for prof in PROFILES:
            ours = SmartAgent("team", make_config(profile=prof), debug=True)
            m = Market([ours] + league(7), mc, seed=7)
            m.run()
            assert m.errors[0] == 0, f"{name}/{prof}: eccezioni"
            assert m.invalid[0] == 0, f"{name}/{prof}: {m.invalid[0]} azioni invalide"
            assert m.max_time[0] < 0.1, f"{name}/{prof}: troppo lento"


def test_fuzz_observations():
    """Osservazioni casuali e anche assurde: l'azione deve restare valida."""
    rng = random.Random(42)
    for _ in range(500):
        info = GameInfo(n_turns=rng.randint(1, 50), n_agents=rng.randint(1, 8), materials=["A", "B"],
                        products=["P1", "P2"], recipes={"P1": {"A": 2, "B": 1}, "P2": {"A": 1, "B": 2}},
                        labor_cost={"P1": rng.uniform(0, 20), "P2": rng.uniform(0, 20)},
                        capacity=rng.randint(0, 100), holding_cost=0.5, raw_holding_cost=0.1,
                        salvage_value=0.0, production_after_auction=rng.random() < 0.5,
                        sell_same_turn=rng.random() < 0.5,
                        auction_type=rng.choice([None, "pay_as_bid", "uniform", "second_price"]))
        agent = SmartAgent("fuzz", debug=True)
        for t in range(info.n_turns):
            obs = Observation(
                turn=t, info=info, cash=rng.choice([0.0, -50.0, rng.uniform(0, 10000)]),
                raw_inventory={"A": rng.randint(0, 50), "B": rng.randint(0, 50)},
                product_inventory={"P1": rng.randint(0, 50), "P2": rng.randint(0, 50)},
                last_won={"A": rng.randint(0, 50), "B": rng.randint(0, 50)} if t else {},
                last_clearing_price={"A": rng.choice([None, rng.uniform(0.01, 50)]),
                                     "B": rng.choice([None, rng.uniform(0.01, 50)])} if t else {},
                last_sales={"P1": rng.randint(0, 50), "P2": rng.randint(0, 50)} if t else {},
                last_competitor_prices={"P1": [rng.uniform(1, 100) for _ in range(rng.randint(0, 5))],
                                        "P2": []} if t and rng.random() < 0.7 else {},
                last_paid={"A": rng.uniform(0, 300), "B": rng.uniform(0, 300)} if t else {},
                last_produced={"P1": rng.randint(0, 30), "P2": rng.randint(0, 30)} if t else {},
                last_supply={"A": rng.randint(0, 200), "B": rng.randint(0, 200)} if t else {},
                current_supply={"A": rng.randint(0, 200), "B": rng.randint(0, 200)} if rng.random() < 0.3 else {},
            )
            a = agent.act(obs)
            _check_action(a, obs)


def _check_action(a: Action, obs: Observation):
    info = obs.info
    assert set(a.prices) == set(info.products)
    for p, v in a.prices.items():
        assert math.isfinite(v) and v > 0, f"prezzo invalido {p}={v}"
    assert sum(a.production.values()) <= info.capacity
    for p, q in a.production.items():
        assert isinstance(q, int) and q >= 0
    cost = sum(b.price * b.qty for b in a.bids)
    cost += sum(info.labor_cost[p] * q for p, q in a.production.items())
    assert cost <= max(0.0, obs.cash) + 1e-6, f"spesa {cost:.2f} > cassa {obs.cash:.2f}"
    for b in a.bids:
        assert b.material in info.materials and b.qty > 0 and b.price > 0 and isinstance(b.qty, int)


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in tests:
        try:
            f()
            print(f"OK    {n}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {n}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} test passati")
    sys.exit(1 if failed else 0)
