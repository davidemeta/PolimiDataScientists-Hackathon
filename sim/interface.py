"""Compatibilità: l'interfaccia vive in agent/interface.py (così agent/ è autosufficiente)."""
from agent.interface import *  # noqa: F401,F403
from agent.interface import Action, BaseAgent, Bid, GameInfo, Observation  # noqa: F401
