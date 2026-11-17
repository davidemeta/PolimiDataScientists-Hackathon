"""
Matrice di test: scenari di mercato × profili dell'agente × gruppi di avversari.
Dice quale profilo usare in quale scenario.

Esempi:
  python3 run_matrix.py                                   # tutto, seed di verifica (holdout)
  python3 run_matrix.py --quick --scenario base           # domani: risposta in pochi secondi
  python3 run_matrix.py --scenario uniform,second_price --profile balanced,uniform,second_price
  python3 run_matrix.py --seeds tune                      # seed usati per tarare i profili

Criterio "migliore": rank medio più basso sui lineup; a parità, profitto medio più alto.
Risultati completi in results/matrix.csv.
"""
from __future__ import annotations

import argparse
import csv
import os
import statistics
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Tuple

from agent.config import PROFILES, make_config
from run_tournament import OURS, run_lineup
from sim.scenarios import SCENARIOS

# "self" (copie di balanced) NON è nel default: favorisce artificialmente ogni profilo diverso da balanced
DEFAULT_LINEUPS = ["mixed", "league", "tough"]
# tune = taratura; holdout = usato per scegliere v2-v4 (non più indipendente); fresh = mai usato per decidere
SEEDS = {"tune": 0, "holdout": 1000, "fresh": 5000}


def _cell(args: Tuple[str, str, str, int, int]) -> dict:
    scenario, profile, lineup, games, seed0 = args
    r = run_lineup(lineup, make_config(profile=profile), games, SCENARIOS[scenario], seed0=seed0)[OURS]
    return dict(scenario=scenario, profile=profile, lineup=lineup, mean=round(r["mean"]), min=round(r["min"]),
                rank=round(r["rank"], 3), wins=r["wins"], errors=r["errors"], invalid=r["invalid"], ms=round(r["ms"], 2))


def _split(arg: str, universe) -> List[str]:
    if arg in ("all", "", None):
        return list(universe)
    items = [x.strip() for x in arg.split(",") if x.strip()]
    bad = [x for x in items if x not in universe]
    if bad:
        raise SystemExit(f"Sconosciuti: {bad}. Disponibili: {list(universe)}")
    return items


def summarize(rows: List[dict], profiles: List[str]) -> Dict[str, dict]:
    """Per ogni scenario: rank medio e profitto medio di ogni profilo (media sui lineup)."""
    out: Dict[str, dict] = {}
    for sc in dict.fromkeys(r["scenario"] for r in rows):
        per = {}
        for pr in profiles:
            rs = [r for r in rows if r["scenario"] == sc and r["profile"] == pr]
            if rs:
                per[pr] = dict(rank=statistics.mean(r["rank"] for r in rs), mean=statistics.mean(r["mean"] for r in rs),
                               min=min(r["min"] for r in rs), errors=sum(r["errors"] + r["invalid"] for r in rs))
        best = min(per, key=lambda p: (round(per[p]["rank"], 2), -per[p]["mean"]))
        out[sc] = dict(per=per, best=best)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all")
    ap.add_argument("--profile", default="all")
    ap.add_argument("--lineup", default=",".join(DEFAULT_LINEUPS))
    ap.add_argument("--games", type=int, default=10)
    ap.add_argument("--seeds", default="holdout", choices=list(SEEDS))
    ap.add_argument("--quick", action="store_true", help="3 partite, lineup mixed+league")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--out", default="results/matrix.csv")
    args = ap.parse_args()

    from run_tournament import LINEUPS
    scenarios = _split(args.scenario, SCENARIOS)
    profiles = _split(args.profile, PROFILES)
    lineups = _split("mixed,league" if args.quick else args.lineup, LINEUPS)
    games = 3 if args.quick else args.games
    seed0 = SEEDS[args.seeds]

    jobs = [(s, p, l, games, seed0) for s in scenarios for p in profiles for l in lineups]
    t0 = time.time()
    print(f"{len(jobs)} celle × {games} partite ({len(scenarios)} scenari, {len(profiles)} profili, "
          f"lineup {lineups}, seed {args.seeds}) ...", flush=True)
    if args.workers > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(args.workers) as ex:
            rows = list(ex.map(_cell, jobs, chunksize=4))
    else:
        rows = [_cell(j) for j in jobs]

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary = summarize(rows, profiles)
    colw = 15
    print(f"\nRank medio (sui lineup) · profitto medio in migliaia — * = migliore per lo scenario\n")
    print(f"{'scenario':22}" + "".join(f"{p[:colw - 1]:>{colw}}" for p in profiles))
    for sc, d in summary.items():
        cells = []
        for p in profiles:
            v = d["per"].get(p)
            mark = "*" if p == d["best"] else " "
            cells.append(f"{v['rank']:.2f}·{v['mean'] / 1000:>5.1f}k{mark}" if v else "-")
        print(f"{sc:22}" + "".join(f"{c:>{colw}}" for c in cells))

    errs = sum(r["errors"] + r["invalid"] for r in rows)
    print(f"\nErrori/azioni invalide del nostro agente: {errs}   ·   max ms/turno: {max(r['ms'] for r in rows):.1f}")
    if "balanced" in profiles:
        print("\nProfilo consigliato per scenario (Δ rispetto a balanced):")
        for sc, d in summary.items():
            b, bal = d["per"][d["best"]], d["per"]["balanced"]
            print(f"  {sc:22} → {d['best']:13} rank {b['rank']:.2f} (balanced {bal['rank']:.2f})  "
                  f"profitto {b['mean'] / 1000:.1f}k (balanced {bal['mean'] / 1000:.1f}k)")
    print(f"\n{time.time() - t0:.1f}s · dettagli in {args.out}")


if __name__ == "__main__":
    main()
