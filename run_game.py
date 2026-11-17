"""
Una singola partita con log dettagliato del nostro agente in logs/team.csv.

  python3 run_game.py --seed 3 --turns 30
"""
from __future__ import annotations

import argparse

from agent.config import STABLE_CONFIG
from agent.core import SmartAgent
from sim.market import Market, MarketConfig
from sim.opponents import HighPricer, Overbidder, RandomAgent, Undercutter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--turns", type=int, default=30)
    ap.add_argument("--debug", action="store_true", help="rilancia le eccezioni invece di usare il fallback")
    args = ap.parse_args()

    agents = [SmartAgent("team", log_path="logs/team.csv", debug=args.debug),
              Undercutter(), HighPricer(), Overbidder(), RandomAgent(seed=args.seed),
              SmartAgent("stable", STABLE_CONFIG)]
    market = Market(agents, MarketConfig(n_turns=args.turns), seed=args.seed)
    scores = market.run()

    print(f"{'turno':>5} " + " ".join(f"{a.name[:10]:>11}" for a in agents))
    for h in market.history[:: max(1, args.turns // 10)]:
        print(f"{h['turn']:>5} " + " ".join(f"{c:>11.0f}" for c in h["cash"]))
    print("\nPunteggio finale:")
    for a, s, e, inv in sorted(zip(agents, scores, market.errors, market.invalid), key=lambda x: -x[1]):
        print(f"  {a.name:<12} {s:>10.0f}   errori={e} azioni_invalide={inv}")
    print("\nLog dettagliato: logs/team.csv")


if __name__ == "__main__":
    main()
