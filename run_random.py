"""
Il nostro agente su N mercati CASUALI (sim/random_markets.py), con avversari casuali (1-9).
Serve a scoprire in quali tipi di mercato va male, senza immaginarli in anticipo.

  python3 run_random.py                      # 300 mercati
  python3 run_random.py --n 1000 --seed0 5000
  python3 run_random.py --set comp_stat=median --profile glut

Metrica: "percentile di rank" = (rank - 1) / (N agenti - 1): 0 = primo, 1 = ultimo.
"""
from __future__ import annotations

import argparse
import csv
import os
import statistics
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

from agent.config import make_config
from agent.core import SmartAgent
from run_tournament import parse_value
from sim.market import Market
from sim.opponents import league
from sim.random_markets import describe, random_market


def _one(args):
    seed, cfg, turns = args
    mc = random_market(seed, turns)
    agents = [SmartAgent("team", cfg)] + league(seed, 1, 9)
    m = Market(agents, mc, seed=seed)
    sc = m.run()
    n = len(sc)
    rank = 1 + sum(x > sc[0] for x in sc)
    others = sorted(sc[1:], reverse=True)
    best_other = others[0] if others else sc[0]
    return dict(seed=seed, n_agents=n, rank=rank, pct=(rank - 1) / max(1, n - 1), ours=sc[0], best_other=best_other,
                profit_ratio=(sc[0] / best_other) if best_other > 0 else None,
                errors=m.errors[0] + agents[0].errors, invalid=m.invalid[0], ms=m.max_time[0] * 1000,
                **describe(mc))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--out", default="results/random.csv")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--turns", default=None, help='durate tra cui scegliere, es. "5,8,10,12" (partite corte)')
    args = ap.parse_args()
    overrides = {k: parse_value(v) for k, v in (kv.split("=", 1) for kv in args.set)}
    cfg = make_config(overrides, profile=args.profile)

    t0 = time.time()
    with ProcessPoolExecutor() as ex:
        turns = [int(x) for x in args.turns.split(",")] if args.turns else None
        rows = list(ex.map(_one, [(args.seed0 + i, cfg, turns) for i in range(args.n)], chunksize=8))
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    pct = [r["pct"] for r in rows]
    first = sum(r["rank"] == 1 for r in rows)
    neg = sum(r["ours"] < 0 for r in rows)
    print(f"{args.n} mercati casuali in {time.time() - t0:.1f}s · errori {sum(r['errors'] for r in rows)} · "
          f"azioni invalide {sum(r['invalid'] for r in rows)} · max {max(r['ms'] for r in rows):.1f} ms/turno")
    print(f"percentile di rank medio {statistics.mean(pct):.3f} (0 = primo) · primi in {first}/{args.n} "
          f"({100 * first / args.n:.0f}%) · metà bassa {sum(p > 0.5 for p in pct)} · profitto negativo {neg}")
    if args.quiet:
        return

    print("\nPercentile di rank medio per caratteristica del mercato (n = numero di mercati):")
    feats = ["auction", "known_auction", "demand", "same_turn", "prod_after", "comp_info", "clear_info",
             "labor_zero", "salvage", "fixed", "materials", "products", "turns"]
    for f in feats:
        groups = defaultdict(list)
        for r in rows:
            groups[r[f]].append(r["pct"])
        cells = "  ".join(f"{k}: {statistics.mean(v):.2f} (n={len(v)})" for k, v in sorted(groups.items(), key=lambda kv: str(kv[0])))
        print(f"  {f:14} {cells}")
    buckets = defaultdict(list)
    for r in rows:
        ls = r["log_scale"]
        buckets["scala < ×0.3" if ls < -0.5 else "scala ×0.3-×3" if ls < 0.5 else "scala ×3-×30" if ls < 1.5 else "scala > ×30"].append(r["pct"])
    print("  scala          " + "  ".join(f"{k}: {statistics.mean(v):.2f} (n={len(v)})" for k, v in buckets.items()))

    print("\nI 12 casi peggiori:")
    for r in sorted(rows, key=lambda r: (-r["pct"], r["ours"]))[:12]:
        print(f"  seed {r['seed']:>5}: {r['rank']}°/{r['n_agents']}  noi {r['ours']:>10.0f}  migliore {r['best_other']:>10.0f}  "
              f"{r['auction']}{'(nota)' if r['known_auction'] else ''} {r['demand']} mat={r['materials']} prod={r['products']} "
              f"turni={r['turns']} stesso_turno={r['same_turn']} prod_dopo_asta={r['prod_after']} "
              f"info_comp={r['comp_info']} info_asta={r['clear_info']} scala={10 ** r['log_scale']:.2g}")
    print(f"\nDettagli: {args.out}")


if __name__ == "__main__":
    main()
