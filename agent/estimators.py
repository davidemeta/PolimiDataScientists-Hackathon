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


class Holt:
    """
    Livellamento esponenziale doppio (metodo di Holt) con trend smorzato.
      livello = alpha*x + (1-alpha)*(livello + phi*trend)       → dove si trova il prezzo
      trend   = beta*(Δlivello) + (1-beta)*phi*trend             → di quanto cambia per turno
      previsione(prossimo turno) = livello + phi*trend
    Segue il prezzo sia in salita sia in discesa, senza il ritardo dell'EMA semplice.
    phi < 1 smorza il trend, così non si estrapola all'infinito.
    """

    def __init__(self, alpha: float = 0.5, beta: float = 0.3, phi: float = 0.9):
        self.alpha, self.beta, self.phi = alpha, beta, phi
        self.level: Optional[float] = None
        self.trend = 0.0

    def update(self, x: float) -> float:
        if self.level is None:
            self.level = x
            return self.forecast()
        prev = self.level
        self.level = self.alpha * x + (1 - self.alpha) * (self.level + self.phi * self.trend)
        self.trend = self.beta * (self.level - prev) + (1 - self.beta) * self.phi * self.trend
        return self.forecast()

    def forecast(self) -> Optional[float]:
        if self.level is None:
            return None
        return max(0.01, self.level + self.phi * self.trend)


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
