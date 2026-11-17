"""Decide le offerte alle aste per le materie prime."""
from __future__ import annotations

import math
from typing import Dict, List

from agent.memory import Memory
from agent.interface import Bid, Observation


def material_values(obs: Observation, mem: Memory, prices: Dict[str, float],
                    production: Dict[str, int]) -> Dict[str, float]:
    """
    Valore marginale di un'unità di materia prima = massimo che conviene pagarla.
      valore(m) = (prezzo_prodotto - lavorazione - costo_altri_materiali) / unità_di_m
    Se m serve a più prodotti, si prende il valore più alto tra quelli che produciamo.
    """
    info = obs.info
    values: Dict[str, float] = {m: 0.0 for m in info.materials}
    for p, qty in production.items():
        if qty <= 0:
            continue
        rec = info.recipes[p]
        for m, need in rec.items():
            others = sum(q * mem.material_price(o) for o, q in rec.items() if o != m)
            v = (mem.value_price(p, prices[p]) - info.labor_cost[p] - others) / need
            values[m] = max(values[m], v)
    return values


def plan_bids(obs: Observation, mem: Memory, cfg: dict, prices: Dict[str, float],
              production: Dict[str, int]) -> List[Bid]:
    info = obs.info
    # ritardo della filiera: materiale comprato oggi → prodotto tra `a` turni → venduto dopo altri `s`
    lag = (0 if info.production_after_auction else 1) + (0 if info.sell_same_turn else 1)
    if obs.turns_left < max(cfg["endgame_turns"], lag):
        return []        # finale: materie prime che non faremo in tempo a trasformare e vendere

    raw_after = dict(obs.raw_inventory)
    if not info.production_after_auction:
        # oggi si produce con il magazzino attuale: quello che resta serve per la produzione di domani
        for p, q in production.items():
            rec = info.recipes[p]
            feasible = min([q] + [raw_after.get(m, 0) // k for m, k in rec.items()])
            for m, k in rec.items():
                raw_after[m] = raw_after.get(m, 0) - k * feasible

    # fabbisogno = materiali per la produzione desiderata - quelli disponibili
    need: Dict[str, int] = {m: 0 for m in info.materials}
    for p, q in production.items():
        for m, per_unit in info.recipes[p].items():
            need[m] += per_unit * q
    for m in need:
        need[m] = max(0, need[m] - raw_after.get(m, 0))

    values = material_values(obs, mem, prices, production)
    bids: List[Bid] = []
    for m in info.materials:
        if need[m] <= 0 or values[m] <= 0:
            continue
        ceiling = values[m] * cfg["bid_fraction"]          # MAI oltre questo
        forecast = mem.clearing_forecast(m)      # prezzo d'aggiudicazione previsto per questo turno
        auction = info.auction_type if cfg["auto_auction_rule"] else None
        share = cfg["bid_surplus_share_uniform"] if auction == "uniform" else cfg["bid_surplus_share"]
        share *= _supply_factor(obs, mem, cfg, m)
        if auction == "second_price":
            # asta al secondo prezzo: offrire il proprio valore è la strategia dominante
            price = ceiling
        elif forecast is None:
            price = ceiling * cfg["first_bid_fraction"]
        elif cfg["bid_rule"] == "surplus_share" and ceiling > forecast:
            # offri sopra il prezzo previsto una QUOTA del margine che c'è tra previsione e valore:
            # più vale per noi la materia prima, più conviene non perdere l'asta
            price = forecast + min(1.0, share) * (ceiling - forecast)
            price = min(ceiling, price * (1 + mem.premium[m]))
        else:
            price = min(ceiling, forecast * (1 + mem.premium[m]))
        # tetto rispetto all'ULTIMO prezzo osservato: quando il prezzo cambia direzione il trend
        # "sfora" per qualche turno, e in un'asta pay-as-bid ogni euro sopra il necessario è perso
        last_cp = obs.last_clearing_price.get(m) or (mem.clear_hist[m][-1] if mem.clear_hist[m] else None)
        if auction == "second_price":
            last_cp = None   # niente tetti: al secondo prezzo non si paga la propria offerta
        if cfg["bid_cap_over_last"] is not None and last_cp:
            price = min(price, last_cp * (1 + cfg["bid_cap_over_last"]))
        # anti-rincorsa: se il prezzo sale da N turni e noi non vendiamo tutto, smettiamo di inseguire.
        # Offriamo al massimo l'ultimo prezzo d'aggiudicazione (niente trend, niente premio):
        # se l'altro vuole continuare a salire, che bruci la SUA cassa.
        if cfg["anti_escalation"] and last_cp and mem.escalating(m):
            price = min(price, last_cp * (1 - cfg["escalation_backoff"]))
        if price <= 0:
            continue
        low_qty = int(math.floor(need[m] * cfg["tier_low_share"]))
        high_qty = need[m] - low_qty
        bids.append(Bid(m, round(price, 2), high_qty))
        if low_qty > 0:
            bids.append(Bid(m, round(price * (1 - cfg["tier_discount"]), 2), low_qty))
    return _fit_budget(bids, obs, mem, cfg, production)


def _fit_budget(bids: List[Bid], obs: Observation, mem: Memory, cfg: dict, production: Dict[str, int]) -> List[Bid]:
    """
    Le materie prime sono COMPLEMENTARI: vincere A senza B non serve a niente.
    Se la cassa non basta per tutte le offerte, riduciamo TUTTE le quantità nella stessa proporzione
    (kit completi), invece di lasciare che la validazione tagli le offerte più care e ci lasci
    con materiali spaiati. Finché non conosciamo i prezzi (nessun dato d'asta) spendiamo al massimo
    una quota della cassa: la scala dei prezzi potrebbe essere molto diversa da quella stimata.
    """
    if not bids or not cfg["kit_budget"]:
        return bids
    info = obs.info
    labor = sum(info.labor_cost.get(p, 0.0) * q for p, q in production.items())
    budget = max(0.0, obs.cash * (1 - cfg["cash_buffer"]) - labor)
    if all(mem.clearing_forecast(m) is None for m in info.materials):
        budget = min(budget, obs.cash * cfg["blind_budget_share"])
    total = sum(b.price * b.qty for b in bids)
    if total <= budget or total <= 0:
        return bids
    f = budget / total
    out = [Bid(b.material, b.price, int(b.qty * f)) for b in bids]
    return [b for b in out if b.qty > 0]


def _supply_factor(obs: Observation, mem: Memory, cfg: dict, m: str) -> float:
    """Offerta annunciata sotto la media → asta più contesa → quota più alta (e viceversa)."""
    cur = obs.current_supply.get(m)
    if not cur or cfg["supply_sensitivity"] <= 0:
        return 1.0
    hist = mem.supply_hist.get(m) or []
    if not hist:
        return 1.0
    avg = sum(hist) / len(hist)
    return max(0.5, min(2.0, (avg / cur) ** cfg["supply_sensitivity"]))
