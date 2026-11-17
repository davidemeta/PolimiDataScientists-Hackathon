"""
Torneo locale: il nostro agente contro diversi gruppi di avversari, su molte partite.

Esempi:
  python3 run_tournament.py                                  # tutti i lineup, 20 partite ciascuno
  python3 run_tournament.py --lineup aggressive --games 50
  python3 run_tournament.py --sweep "bid_fraction=0.7,0.8,0.9,1.0"
  python3 run_tournament.py --set margin_init=0.5 --set bid_premium=0.1
"""
from __future__ import annotations

import argparse
import statistics
from typing import Callable, Dict, List

from agent.config import STABLE_CONFIG, make_config
from agent.core import SmartAgent
from sim.market import Market, MarketConfig
from agent.config import DEFAULT_CONFIG
from sim.opponents import (BanditPricer, Colluder, Copycat, Dumper, FixedAgent, HighPricer, Hoarder, Overbidder,
                           RandomAgent, Switcher, Trembler, Undercutter, league)

OURS = "team"

# ogni lineup: funzione (config_nostra, seed) -> lista di agenti
LINEUPS: Dict[str, Callable] = {
    "mixed": lambda cfg, s: [SmartAgent(OURS, cfg), Undercutter(), HighPricer(), Overbidder(),
                             RandomAgent(seed=s), SmartAgent("stable", STABLE_CONFIG)],
    "aggressive": lambda cfg, s: [SmartAgent(OURS, cfg), Undercutter("uc1"), Undercutter("uc2"),
                                  Overbidder("ob1"), Overbidder("ob2")],
    "passive": lambda cfg, s: [SmartAgent(OURS, cfg), HighPricer("hp1"), HighPricer("hp2", 0.5),
                               FixedAgent()],
    "mirror": lambda cfg, s: [SmartAgent(OURS, cfg)] + [SmartAgent(f"stable{k}", STABLE_CONFIG) for k in range(4)],
    "duel": lambda cfg, s: [SmartAgent(OURS, cfg), SmartAgent("stable", STABLE_CONFIG)],
    # gara "vera": avversari estratti a caso dalla libreria (3-7), diversi a ogni partita
    "league": lambda cfg, s: [SmartAgent(OURS, cfg)] + league(s),
    # squadre che sanno fare il loro mestiere: copie della versione attuale + strategie "intelligenti"
    "self": lambda cfg, s: [SmartAgent(OURS, cfg)] + [SmartAgent(f"cur{k}", DEFAULT_CONFIG) for k in range(3)],
    "tough": lambda cfg, s: [SmartAgent(OURS, cfg), Hoarder(), Dumper(), Colluder(), Copycat()],
    # avversari che cambiano strategia e agenti "scarsi" che sbagliano a caso
    "chaos": lambda cfg, s: [SmartAgent(OURS, cfg), Switcher("sw1", seed=s), Switcher("sw2", period=5, seed=s + 1),
                             Trembler("tr1", seed=s + 2), Trembler("tr2", inner=BanditPricer(seed=s), eps=0.3, seed=s + 3),
                             Trembler("tr3", inner=SmartAgent("smart_tr", DEFAULT_CONFIG), eps=0.15, seed=s + 4)],
}


def parse_value(v: str):
    for cast in (int, float):
        try:
            return cast(v)
        except ValueError:
            pass
    return {"true": True, "false": False}.get(v.lower(), v)


def run_lineup(name: str, cfg: dict, games: int, market_cfg: MarketConfig, seed0: int = 0) -> Dict[str, dict]:
    scores: Dict[str, List[float]] = {}
    ranks: Dict[str, List[int]] = {}
    errors: Dict[str, int] = {}
    invalid: Dict[str, int] = {}
    max_time: Dict[str, float] = {}
    for g in range(games):
        agents = LINEUPS[name](cfg, seed0 + g)
        market = Market(agents, market_cfg, seed=seed0 + g)
        result = market.run()
        order = sorted(range(len(agents)), key=lambda i: -result[i])
        for pos, i in enumerate(order):
            a = agents[i].name
            scores.setdefault(a, []).append(result[i])
            ranks.setdefault(a, []).append(pos + 1)
            errors[a] = errors.get(a, 0) + market.errors[i] + getattr(agents[i], "errors", 0)
            invalid[a] = invalid.get(a, 0) + market.invalid[i]
            max_time[a] = max(max_time.get(a, 0.0), market.max_time[i])
    out = {}
    for a, s in scores.items():
        out[a] = dict(mean=statistics.mean(s), std=statistics.pstdev(s), min=min(s), max=max(s),
                      rank=statistics.mean(ranks[a]), wins=sum(r == 1 for r in ranks[a]),
                      errors=errors[a], invalid=invalid[a], ms=max_time[a] * 1000)
    return out


def print_table(title: str, res: Dict[str, dict], games: int) -> None:
    print(f"\n=== {title} ({games} partite) ===")
    print(f"{'agente':<14}{'media':>10}{'dev.std':>10}{'min':>10}{'max':>10}{'rank':>7}{'vitt.':>7}{'err':>5}{'inv':>5}{'ms':>7}")
    for a, r in sorted(res.items(), key=lambda kv: -kv[1]["mean"]):
        mark = " <==" if a == OURS else ""
        print(f"{a:<14}{r['mean']:>10.0f}{r['std']:>10.0f}{r['min']:>10.0f}{r['max']:>10.0f}"
              f"{r['rank']:>7.2f}{r['wins']:>7}{r['errors']:>5}{r['invalid']:>5}{r['ms']:>7.1f}{mark}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lineup", default="all", help=f"uno tra {list(LINEUPS)} oppure 'all'")
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--turns", type=int, default=30)
    ap.add_argument("--auction", default="pay_as_bid", choices=["pay_as_bid", "uniform"])
    ap.add_argument("--set", action="append", default=[], help="override parametro: nome=valore")
    ap.add_argument("--profile", default=None, help="profilo da agent/config.py PROFILES")
    ap.add_argument("--scenario", default="base", help="scenario da sim/scenarios.py")
    ap.add_argument("--sweep", default=None, help='es. "bid_fraction=0.7,0.8,0.9"')
    args = ap.parse_args()

    overrides = {}
    for kv in args.set:
        k, v = kv.split("=", 1)
        overrides[k] = parse_value(v)
    base_cfg = make_config(overrides, profile=args.profile)
    from dataclasses import replace
    from sim.scenarios import SCENARIOS
    market_cfg = SCENARIOS[args.scenario]
    if args.scenario == "base":   # retrocompatibilità con --turns / --auction
        market_cfg = replace(market_cfg, n_turns=args.turns, auction_type=args.auction)
    lineups = list(LINEUPS) if args.lineup == "all" else [args.lineup]

    if args.sweep:
        key, values = args.sweep.split("=", 1)
        values = [parse_value(v) for v in values.split(",")]
        print(f"\nSweep su '{key}' — punteggio del NOSTRO agente (media / minimo / rank medio) per lineup")
        header = f"{key:>14}" + "".join(f"{l:>26}" for l in lineups) + f"{'rank medio':>12}"
        print(header)
        for v in values:
            cfg = dict(base_cfg, **{key: v})
            cells, rks = [], []
            for l in lineups:
                r = run_lineup(l, cfg, args.games, market_cfg)[OURS]
                cells.append(f"{r['mean']:>9.0f} /{r['min']:>7.0f} /{r['rank']:>5.2f}")
                rks.append(r["rank"])
            print(f"{str(v):>14}" + "".join(f"{c:>26}" for c in cells) + f"{statistics.mean(rks):>12.2f}")
        return

    for l in lineups:
        print_table(l, run_lineup(l, base_cfg, args.games, market_cfg), args.games)


if __name__ == "__main__":
    main()
