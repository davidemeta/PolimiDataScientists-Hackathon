"""Log CSV: una riga per turno. Aprite il file con pandas o Excel per capire cosa succede."""
from __future__ import annotations

import csv
import os
from typing import Optional

from agent.interface import Action, Observation


class TurnLogger:
    def __init__(self, path: Optional[str]):
        self.path = path
        self._writer = None
        self._file = None
        self._header = None

    def log(self, obs: Observation, action: Action, mem, error: str = "") -> None:
        if not self.path:
            return
        info = obs.info
        row = dict(turn=obs.turn, cash=round(obs.cash, 2), error=error)
        bid_qty = {m: 0 for m in info.materials}
        bid_max = {m: 0.0 for m in info.materials}
        for b in action.bids:
            bid_qty[b.material] += b.qty
            bid_max[b.material] = max(bid_max[b.material], b.price)
        for m in info.materials:
            row[f"raw_{m}"] = obs.raw_inventory.get(m, 0)
            row[f"won_{m}"] = obs.last_won.get(m, 0)
            row[f"clear_{m}"] = obs.last_clearing_price.get(m)
            row[f"bidqty_{m}"] = bid_qty[m]
            row[f"bidmax_{m}"] = bid_max[m]
            if getattr(mem, "ready", False):
                row[f"premium_{m}"] = round(mem.premium[m], 3)
        for p in info.products:
            row[f"stock_{p}"] = obs.product_inventory.get(p, 0)
            row[f"sales_{p}"] = obs.last_sales.get(p, 0)
            row[f"price_{p}"] = action.prices.get(p)
            row[f"prod_{p}"] = action.production.get(p, 0)
            comp = obs.last_competitor_prices.get(p) or []
            row[f"comp_{p}"] = round(sum(comp) / len(comp), 2) if comp else None
            if getattr(mem, "ready", False):
                row[f"margin_{p}"] = round(mem.margin[p], 3)
                row[f"cost_{p}"] = round(mem.unit_cost(obs, p), 2)
        if self._writer is None:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            self._file = open(self.path, "w", newline="")
            self._header = list(row.keys())
            self._writer = csv.DictWriter(self._file, fieldnames=self._header, extrasaction="ignore")
            self._writer.writeheader()
        self._writer.writerow(row)
        self._file.flush()
