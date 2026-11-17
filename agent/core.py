"""
Il nostro agente. Flusso di ogni turno:
  osserva → aggiorna memoria → prezzi → produzione → offerte → valida → logga
Qualsiasi eccezione → azione sicura (l'agente NON deve mai crashare).
"""
from __future__ import annotations

import traceback
from typing import Dict, Optional

from agent.bidding import plan_bids
from agent.config import make_config
from agent.logger import TurnLogger
from agent.memory import Memory
from agent.pricing import compute_prices
from agent.production import plan_production
from agent.safety import safe_default, validate
from agent.interface import Action, BaseAgent, Observation


class SmartAgent(BaseAgent):
    def __init__(self, name: str = "team", config: Optional[dict] = None, log_path: Optional[str] = None,
                 debug: bool = False, profile: Optional[str] = None):
        self.name = name
        self.cfg = make_config(config, profile=profile)   # profili in agent/config.py → PROFILES
        self.mem = Memory(self.cfg)
        self.logger = TurnLogger(log_path)
        self.debug = debug          # True = rilancia le eccezioni (utile in sviluppo)
        self.errors = 0
        self._last_prices: Dict[str, float] = {}
        self._prev_turn: Optional[int] = None

    def reset(self) -> None:
        """Nuova partita: dimentica tutto quello che si è imparato nella precedente."""
        self.mem = Memory(self.cfg)
        self._last_prices = {}
        self._prev_turn = None

    def act(self, obs: Observation) -> Action:
        error = ""
        # se il turno non avanza, è iniziata una nuova partita nello stesso processo
        if self._prev_turn is not None and obs.turn <= self._prev_turn:
            self.reset()
        self._prev_turn = obs.turn
        try:
            self.mem.update(obs)
            prices = compute_prices(obs, self.mem, self.cfg)
            production = plan_production(obs, self.mem, self.cfg, prices)
            bids = plan_bids(obs, self.mem, self.cfg, prices, production)
            action = validate(Action(bids, production, prices), obs, self.cfg, self._fallback_prices(obs))
        except Exception as e:  # noqa: BLE001 - è voluto: mai crashare
            if self.debug:
                raise
            self.errors += 1
            error = f"{type(e).__name__}: {e}"
            traceback.print_exc()
            action = safe_default(obs, self._fallback_prices(obs))
        self.mem.last_action = action
        self._last_prices = dict(action.prices)
        try:
            self.logger.log(obs, action, self.mem, error)
        except Exception:  # il logging non deve mai rompere l'agente
            pass
        return action

    def _fallback_prices(self, obs: Observation) -> Dict[str, float]:
        out = {}
        for p in obs.info.products:
            if p in self._last_prices:
                out[p] = self._last_prices[p]
            else:
                try:
                    out[p] = self.mem.unit_cost(obs, p) * 1.3
                except Exception:
                    out[p] = 2.0 * self.mem.default_material_price() if self.mem.ready else 1.0
        return out
