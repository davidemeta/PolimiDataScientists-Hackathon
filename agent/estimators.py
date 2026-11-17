"""Stimatori semplici e robusti (solo libreria standard)."""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple


class EMA:
    """Media mobile esponenziale: value = alpha*x + (1-alpha)*value."""

    def __init__(self, alpha: float, init: Optional[float] = None):
        self.alpha = alpha
        self.value = init

    def update(self, x: float) -> float:
        self.value = x if self.value is None else self.alpha * x + (1 - self.alpha) * self.value
        return self.value

    def get(self, default: float) -> float:
        return default if self.value is None else self.value


def linear_demand_fit(points: Sequence[Tuple[float, float]], min_points: int = 6
                      ) -> Optional[Tuple[float, float]]:
    """
    Stima q = a - b*p con minimi quadrati. Ritorna (a, b) oppure None se il
    fit non è affidabile (pochi punti, prezzi tutti uguali, pendenza sbagliata).
    """
    if len(points) < min_points:
        return None
    xs = [p for p, _ in points]
    ys = [q for _, q in points]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx < 1e-9 or (max(xs) - min(xs)) < 0.02 * mx:   # prezzi troppo simili
        return None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    a, b = my - slope * mx, -slope
    if b <= 0 or a <= 0:      # domanda che sale col prezzo = dati rumorosi, non fidarsi
        return None
    return a, b


def optimal_price_linear(a: float, b: float, cost: float) -> float:
    """Prezzo che massimizza (p - c) * (a - b p): p* = (a/b + c) / 2."""
    return (a / b + cost) / 2


def mean(xs: List[float]) -> Optional[float]:
    return sum(xs) / len(xs) if xs else None
