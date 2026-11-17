"""
Interfaccia tra agente e gioco.

Domani, quando conoscerete l'API vera, NON riscrivete l'agente: scrivete un
adapter (vedi adapter.py) che traduce l'osservazione reale in `Observation`
e la nostra `Action` nel formato richiesto dagli organizzatori.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Bid:
    """Offerta per una materia prima: `qty` unità a `price` euro l'una."""
    material: str
    price: float
    qty: int


@dataclass
class Action:
    """Le tre decisioni di un turno."""
    bids: List[Bid] = field(default_factory=list)
    production: Dict[str, int] = field(default_factory=dict)   # prodotto -> unità da produrre
    prices: Dict[str, float] = field(default_factory=dict)     # prodotto -> prezzo di vendita


@dataclass
class GameInfo:
    """Informazioni statiche, note dall'inizio della partita."""
    n_turns: int
    n_agents: int
    materials: List[str]
    products: List[str]
    recipes: Dict[str, Dict[str, int]]       # prodotto -> {materia prima: unità necessarie}
    labor_cost: Dict[str, float]             # costo di lavorazione per unità di prodotto
    capacity: int                            # unità totali producibili per turno
    holding_cost: float                      # costo per unità di prodotto in magazzino per turno
    raw_holding_cost: float                  # costo per unità di materia prima in magazzino per turno
    salvage_value: float                     # valore di un prodotto invenduto a fine partita
    sell_same_turn: bool = True              # si vende nello stesso turno in cui si produce?
    production_after_auction: bool = True    # la produzione usa le materie prime vinte nello stesso turno?
    auction_type: Optional[str] = None       # "pay_as_bid" | "uniform" | "second_price" | None (sconosciuto)


@dataclass
class Observation:
    """Quello che l'agente vede all'inizio di ogni turno."""
    turn: int                                # 0-based
    info: GameInfo
    cash: float
    raw_inventory: Dict[str, int]
    product_inventory: Dict[str, int]
    # --- esiti del turno precedente (vuoti al turno 0) ---
    last_won: Dict[str, int] = field(default_factory=dict)
    last_paid: Dict[str, float] = field(default_factory=dict)
    last_clearing_price: Dict[str, Optional[float]] = field(default_factory=dict)  # prezzo vincente più basso
    last_supply: Dict[str, int] = field(default_factory=dict)
    last_produced: Dict[str, int] = field(default_factory=dict)
    last_sales: Dict[str, int] = field(default_factory=dict)
    last_competitor_prices: Dict[str, List[float]] = field(default_factory=dict)
    # --- opzionale: unità in vendita all'asta IN QUESTO turno, se il gioco le annuncia prima ---
    current_supply: Dict[str, int] = field(default_factory=dict)

    @property
    def turns_left(self) -> int:
        """Turni che restano DOPO quello corrente (0 = ultimo turno)."""
        return self.info.n_turns - self.turn - 1


class BaseAgent:
    """Tutti gli agenti (nostro e avversari) implementano `act`."""
    name: str = "base"

    def act(self, obs: Observation) -> Action:  # pragma: no cover
        raise NotImplementedError
