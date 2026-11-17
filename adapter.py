"""
ADAPTER verso l'API vera degli organizzatori. È L'UNICO FILE da scrivere domani
per collegare l'agente (insieme a eventuali ritocchi a GameInfo/Observation).

Procedura (15-20 minuti, ruolo A):
  1. Guardate il bot di esempio degli organizzatori: che firma ha la funzione
     chiamata ogni turno? Cosa riceve (dict? oggetto? JSON?) e cosa deve tornare?
  2. Riempite `to_game_info` e `to_observation` mappando i loro campi sui nostri.
     Se manca un dato, mettete un default ragionevole (es. dizionario vuoto).
  3. Riempite `to_their_action` con il formato che si aspettano.
  4. Prima submission con l'agente così com'è.

Usate un assistente di coding: "ecco il loro bot di esempio e il nostro
agent/interface.py: completa adapter.py".
"""
from __future__ import annotations

from typing import Any

from agent.core import SmartAgent
from agent.interface import Action, GameInfo, Observation

# PROFILO: sceglietelo con playbook.md dopo il briefing ("balanced" se non sapete nulla)
PROFILE = "balanced"
_agent = SmartAgent(name="team", log_path="logs/live.csv", profile=PROFILE)
_info: GameInfo | None = None
_prev_turn: int | None = None


def to_game_info(raw: Any) -> GameInfo:
    # TODO: mappare i campi reali. Esempio ipotetico:
    return GameInfo(
        n_turns=raw["n_turns"],
        n_agents=raw.get("n_agents", 1),
        materials=list(raw["materials"]),
        products=list(raw["products"]),
        recipes=raw["recipes"],                       # {prodotto: {materia: unità}}
        labor_cost=raw.get("production_cost", {p: 0.0 for p in raw["products"]}),
        capacity=raw.get("capacity", 10**9),
        holding_cost=raw.get("holding_cost", 0.0),
        raw_holding_cost=raw.get("raw_holding_cost", 0.0),
        salvage_value=raw.get("salvage_value", 0.0),
        sell_same_turn=raw.get("sell_same_turn", True),
        production_after_auction=raw.get("production_after_auction", False),  # prudente
        # TODO: se il regolamento dice il tipo d'asta, mettetelo qui ("pay_as_bid" | "uniform" | "second_price"):
        #       l'agente adatta da solo la regola d'offerta. Se non si sa, lasciate None.
        auction_type=raw.get("auction_type"),
    )


def to_observation(raw: Any, info: GameInfo) -> Observation:
    # TODO: mappare i campi reali.
    # TODO IMPORTANTE: il nostro `turn` è 0-based (0 = primo turno, turns_left == 0 all'ultimo).
    #      Se il loro è 1-based usate raw["turn"] - 1, altrimenti la logica di fine partita
    #      (liquidazione, stop acquisti) scatta un turno in ritardo SENZA dare errori.
    return Observation(
        turn=raw["turn"],
        info=info,
        cash=raw["cash"],
        raw_inventory=raw.get("raw_inventory", {}),
        product_inventory=raw.get("product_inventory", {}),
        last_won=raw.get("last_won", {}),
        last_paid=raw.get("last_paid", {}),
        last_clearing_price=raw.get("last_clearing_price", {}),
        last_supply=raw.get("last_supply", {}),
        last_produced=raw.get("last_produced", {}),
        last_sales=raw.get("last_sales", {}),
        last_competitor_prices=raw.get("competitor_prices", {}),
        # TODO: se il gioco annuncia le unità in vendita all'asta PRIMA delle offerte, mappatele qui
        current_supply=raw.get("current_supply", {}),
    )


def to_their_action(action: Action) -> Any:
    # TODO: formato richiesto dagli organizzatori. Esempio ipotetico:
    return {
        "bids": [{"material": b.material, "price": b.price, "quantity": b.qty} for b in action.bids],
        "production": action.production,
        "prices": action.prices,
    }


def play_turn(raw_state: Any) -> Any:
    """Funzione da far chiamare al loro framework a ogni turno (rinominatela come serve)."""
    global _info, _prev_turn
    turn = raw_state["turn"]          # TODO: stesso campo usato in to_observation
    if _info is None or (_prev_turn is not None and turn <= _prev_turn):
        _info = to_game_info(raw_state)   # nuova partita nello stesso processo: rileggi le info
    _prev_turn = turn
    obs = to_observation(raw_state, _info)
    return to_their_action(_agent.act(obs))
