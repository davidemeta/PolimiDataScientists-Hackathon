"""
Mercati AFFOLLATI (30-40 agenti, come una gara con ~100 iscritti in squadre da 3).

Avversari "realistici": una quota di agenti COMPETENTI (copie del nostro agente con parametri
perturbati e profili diversi, oppure la v1) + bot semplici dalla libreria (undercutter, hoarder, ...).
Offerta di materie prime e domanda scalano col numero di agenti (per_agent nel MarketConfig).

  python3 run_crowd.py                                  # N = 10,20,35,45 · tutti i profili · base + casuali
  python3 run_crowd.py --n-agents 35 --smart 0.6 --games 40
  python3 run_crowd.py --profile balanced --set margin_min=0.25
  python3 run_crowd.py --market base,scarce --thin 7          # torta fissa: fetta per agente minuscola

Metriche: percentile di rank (0 = primo), % top-1, % top-10%, profitto medio (cassa finale − iniziale), % in perdita.
"""
from __future__ import annotations

import argparse
import random
import statistics
import time
from dataclasses import replace
from concurrent.futures import ProcessPoolExecutor

from agent.config import PROFILES, STABLE_CONFIG, make_config
from agent.core import SmartAgent
from run_tournament import parse_value
from sim.market import Market
from sim.opponents import opponent_pool
from sim.random_markets import random_market
from sim.scenarios import SCENARIOS

# parametri perturbati per gli avversari competenti (altre squadre con agenti ragionevoli)
_PERTURB = {
    "margin_init": (0.2, 0.8), "margin_min": (0.0, 0.3), "bid_surplus_share": (0.05, 0.6),
    "target_stock_turns": (1.0, 2.0), "first_bid_fraction": (0.4, 0.9), "market_band_low": (0.0, 0.15),
}


def crowd(seed: int, n_opp: int, smart_share: float):
    rng = random.Random(77_000 + seed)
    pool = opponent_pool(seed)
    opps = []
    for k in range(n_opp):
        if rng.random() < smart_share:
            r = rng.random()
            if r < 0.2:
                opps.append(SmartAgent(f"v1_{k}", dict(STABLE_CONFIG)))
            else:
                over = {p: rng.uniform(lo, hi) for p, (lo, hi) in _PERTURB.items()}
                over["anti_escalation"] = rng.random() < 0.5
                prof = rng.choice([None, None, "v6", "profit", "glut"])
                opps.append(SmartAgent(f"smart{k}", make_config(over, profile=prof)))
        else:
            opps.append(rng.choice(pool)(k))
    return opps


def _one(args):
    seed, cfg, n_agents, smart, market, thin = args
    mc = random_market(seed) if market == "random" else SCENARIOS[market]
    if thin != 1.0:   # torta FISSA: offerta e domanda totali non crescono con N → fetta per agente minuscola
        mc = replace(mc, supply_per_agent={k: v / thin for k, v in mc.supply_per_agent.items()},
                     market_size_per_agent={k: v / thin for k, v in mc.market_size_per_agent.items()})
    agents = [SmartAgent("team", cfg)] + crowd(seed, n_agents - 1, smart)
    sc = Market(agents, mc, seed=seed).run()
    rank = 1 + sum(x > sc[0] for x in sc)
    return dict(rank=rank, pct=(rank - 1) / (len(sc) - 1), ours=sc[0] - mc.start_cash, top10=rank <= max(1, round(0.1 * len(sc))),
                best_other=max(sc[1:]) - mc.start_cash)


def evaluate(cfg, n_agents, smart, market, games, seed0, ex, thin=1.0):
    rows = list(ex.map(_one, [(seed0 + i, cfg, n_agents, smart, market, thin) for i in range(games)], chunksize=2))
    return dict(pct=statistics.mean(r["pct"] for r in rows), first=sum(r["rank"] == 1 for r in rows) / games,
                top10=sum(r["top10"] for r in rows) / games, rank=statistics.mean(r["rank"] for r in rows),
                profit=statistics.mean(r["ours"] for r in rows), loss=sum(r["ours"] < 0 for r in rows) / games)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-agents", default="10,20,35,45")
    ap.add_argument("--smart", type=float, default=0.5, help="quota di avversari competenti")
    ap.add_argument("--profile", default="all")
    ap.add_argument("--market", default="base,random")
    ap.add_argument("--games", type=int, default=30)
    ap.add_argument("--seed0", type=int, default=5000)
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--thin", type=float, default=1.0,
                    help="divide offerta e domanda per agente (es. 7 = torta fissa pensata per ~5 agenti con 35 in gara)")
    args = ap.parse_args()
    overrides = {k: parse_value(v) for k, v in (kv.split("=", 1) for kv in args.set)}
    profiles = list(PROFILES) if args.profile == "all" else args.profile.split(",")
    t0 = time.time()
    with ProcessPoolExecutor() as ex:
        for market in args.market.split(","):
            for n in [int(x) for x in args.n_agents.split(",")]:
                print(f"\n=== mercato {market} · {n} agenti · {int(100 * args.smart)}% competenti · thin {args.thin} · {args.games} partite ===")
                print(f"{'profilo':14} {'pct':>6} {'rank':>6} {'1°':>5} {'top10%':>7} {'profitto':>10} {'perdita':>8}")
                for p in profiles:
                    r = evaluate(make_config(overrides, profile=p), n, args.smart, market, args.games, args.seed0, ex, args.thin)
                    print(f"{p:14} {r['pct']:6.3f} {r['rank']:6.1f} {100 * r['first']:4.0f}% {100 * r['top10']:6.0f}% "
                          f"{r['profit']:10.0f} {100 * r['loss']:7.0f}%", flush=True)
    print(f"\n{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
