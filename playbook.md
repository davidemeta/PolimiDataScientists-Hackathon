# Playbook per domani: dal briefing al profilo giusto

Scopo: trasformare le risposte del briefing (14:30-14:45) in **un profilo dell'agente e 2-3 parametri da ritarare**, senza perdere tempo.

- La strategia generale è in [strategy.md](strategy.md).
- I concetti economici sono in [knowledge_base.md](knowledge_base.md).
- I numeri citati qui vengono da `run_matrix.py`: 26 scenari × 6 profili × 4 gruppi di avversari, ripetuti su **due set di seed indipendenti**. Un profilo diverso da `balanced` è consigliato solo se migliora il rank su entrambi i set.

---

## 1. Albero decisionale (seguitelo in quest'ordine)

```
1. TIPO D'ASTA
   ├─ si paga la PROPRIA offerta (pay-as-bid / primo prezzo) ........ vai al punto 2
   └─ prezzo unico (uniform) o secondo prezzo ...................... profilo  single_price
         (offrire vicino al valore costa poco: con second_price il rank passa da 1,73 a 1,02,
          con uniform da 1,43 a 1,18)
         → poi passate direttamente al punto 5

2. DOMANDA E MATERIE PRIME
   ├─ materie prime scarse e domanda alta (sold-out facili) ....... profilo  scarce
   ├─ domanda lineare / rumorosa, prezzo minimo d'asta alto,
   │  magazzino caro, cassa iniziale bassa, guerra di prezzi ...... profilo  glut
   └─ non si sa / misto ........................................... profilo  balanced

3. TEMPI (se diversi da "compro, produco e vendo nello stesso turno")
   └─ già gestiti dall'agente: impostate SOLO i flag in GameInfo (adapter.py)
        sell_same_turn=False           → si vende il turno dopo la produzione
        production_after_auction=False → si produce solo con materiali già in magazzino
      Con "vendo il turno dopo" il profilo scarce rende di più (rank da 1,43 a 1,27)

4. INFORMAZIONI VISIBILI
   └─ già gestite: se manca il prezzo d'aggiudicazione l'agente lo deduce dalle proprie
      vincite; se mancano i prezzi dei concorrenti salta l'ancoraggio al mercato.
      Lasciate il campo vuoto nell'adapter, NON mettete zero.

5. PUNTEGGIO (si applica sopra il profilo scelto)
   ├─ classifica relativa ........ override  anti_escalation=False   (oppure profilo rank)
   ├─ profitto assoluto .......... lasciate anti_escalation=True (default)
   └─ media su più partite ....... guardate il MINIMO nel torneo, non solo la media
```

**Come combinare un profilo con gli override.** In `adapter.py` cambiate `PROFILE`, oppure scrivete:

```python
SmartAgent(name="team", profile="single_price", config={"anti_escalation": False})
```

---

## 2. Scenario → profilo consigliato

Il rank è quello sui seed di verifica (holdout), come media su 4 gruppi di avversari: mixed, league, tough e self.

| Scenario (`sim/scenarios.py`) | Profilo | Rank (balanced) | Profitto (balanced) |
|---|---|---|---|
| `base`, `known_auction`, `announced_supply`, `salvage`, `fixed_costs`, `prod_from_stock`, `hidden_clearing`, `blind`, `glut`, `short`, `hard_mix` | **balanced** | 1,32–1,63 | — |
| `uniform` | **single_price** | 1,18 (1,43) | 14,6k (13,2k) |
| `second_price` | **single_price** | 1,02 (1,73) | 20,8k (14,5k) |
| `uniform_linear_short` | **single_price** | 1,47 (1,68) | 6,4k (6,4k) |
| `cheapest_first` | **scarce** | 1,33 (1,52) | 15,5k (14,8k) |
| `sell_next_turn` | **scarce** | 1,27 (1,43) | 12,2k (12,6k) |
| `long` (80 turni) | **scarce** | 1,08 (1,40) | 41,2k (41,2k) |
| `linear_demand` | **glut** | 1,32 (1,52) | 13,0k (12,0k) |
| `noisy_demand` | **glut** | 1,37 (1,53) | 13,4k (12,7k) |
| `high_reserve` | **glut** | 1,35 (1,45) | 13,6k (13,0k) |
| `scarce` | **glut** | 1,43 (1,57) | 11,2k (10,6k) |
| `costly_storage` | **glut** | 1,42 (1,53) | 13,3k (12,6k) |
| `low_cash` | **glut** | 1,32 (1,50) | 16,2k (13,7k) |
| `slow_pipeline` | **glut** | 1,27 (1,42) | 14,0k (13,0k) |
| `single_product` | **glut** | 1,42 (1,57) | 10,4k (10,1k) |
| `hidden_prices` | **rank** | 1,33 (1,48) | 16,3k (16,2k) |

**Il profilo `single_price` è da usare SOLO con aste uniform o second_price.** Con aste pay-as-bid è disastroso: rank circa 4, profitto circa 3k, perché paga ogni unità al proprio valore.

**Se non sapete scegliere tra `balanced` e `glut`**: su tutti gli scenari pay-as-bid `glut` è leggermente meglio, sia per rank (1,04-1,08 contro 1,05-1,10, escluso il gruppo `self`) sia per profitto (+0,5k). Domani provate entrambi con il comando rapido del §3.

> Nota sul gruppo `self`: lì gli avversari sono copie di `balanced`, quindi qualsiasi profilo diverso parte avvantaggiato e `balanced` contro sé stesso fa circa 2,5 per simmetria. Per questo i rank assoluti sono intorno a 1,3-1,5 e non 1,0. Contano i confronti tra profili, non il valore assoluto.

---

## 3. Procedura di domani, minuto per minuto

| Ora | Cosa | Comando / file |
|---|---|---|
| 14:30-14:45 | Briefing: compilate l'albero del §1 (una persona scrive, una fa domande) | questo file |
| 14:45-15:05 | Leggete il simulatore vero (checklist in strategy.md §5) | — |
| 15:05-15:20 | **Adapter**: mappate i campi, normalizzate il turno a 0-based, impostate i flag dei tempi e `PROFILE` | `adapter.py` |
| 15:20 | Test e **prima submission** | `python3 tests/test_robustness.py` |
| 15:20-15:40 | Create lo scenario `real` copiando i parametri veri (vedi sotto) | `sim/scenarios.py` |
| 15:40 | Confronto rapido dei profili sullo scenario vero | `python3 run_matrix.py --quick --scenario real` |
| 15:45-17:00 | Tuning di 2-3 parametri (vedi §4), sempre con `run_tournament.py --scenario real --sweep ...` | — |
| 17:00-17:20 | Matrice completa sullo scenario vero, scelta finale, submission | `python3 run_matrix.py --scenario real --games 20` |
| 17:20-17:45 | **Freeze.** Solo controllo che la submission sia stata accettata | — |

**Creare lo scenario `real`** (in fondo a `sim/scenarios.py`):

```python
SCENARIOS["real"] = make("base",
    n_turns=..., auction_type="...", demand_model="...",          # i valori veri
    sell_same_turn=..., production_after_auction=...,
    supply_per_agent={...}, market_size_per_agent={...},
    info_competitor_prices=..., info_clearing_price=...)
```

Se la loro domanda non è logit, lineare o cheapest_first, scegliete quella più simile: serve solo per confrontare i profili, non deve essere perfetta.

---

## 4. Quali parametri ritarare per primi

| Situazione osservata | Parametri (in `agent/config.py`) | Direzione |
|---|---|---|
| Perdiamo troppe aste / produciamo poco | `bid_surplus_share`, `bid_cap_over_last` | ↑ |
| Strapaghiamo le materie prime (offerta ≫ prezzo d'aggiudicazione nel log) | `bid_surplus_share`, `holt_beta` | ↓ |
| Magazzino che cresce, invenduti a fine partita | `target_stock_turns`, `stockout_boost_base`, `liquidation_turns` | ↓ / ↓ / ↑ |
| Sempre sold-out, prezzi dei concorrenti in salita | `target_stock_turns`, `stockout_boost_base`, `margin_step` | ↑ |
| Guerra di prezzi (prezzi dei concorrenti che crollano) | `margin_min`, `market_band_low` | ↑ / ↓ (oppure profilo `glut`) |
| Partita corta (≤ 15 turni) | `explore_turns`, `liquidation_turns` | 0-2 / 1 |
| Rincorsa sui prezzi d'asta con un rivale | `anti_escalation`, `escalation_turns` | True / 2 |

Il log turno per turno è in `logs/team.csv` (con `run_game.py`) o in `logs/live.csv` (con l'adapter). Guardate le colonne `bidmax_*` e `clear_*` per i soldi strapagati, e `stock_*` e `sales_*` per gli invenduti.

---

## 5. Contromisure per tipo di avversario osservato

Questo è il comportamento del nostro agente contro ciascun tipo nella libreria (`sim/opponents.py`), e cosa fare se domani ne riconoscete uno.

| Se un avversario… | È probabilmente un… | Cosa succede / cosa fare |
|---|---|---|
| offre molto sopra il prezzo d'aggiudicazione e vince tutto | **Overbidder** | Brucia la cassa in 5-6 turni. **Non inseguitelo**: l'anti-rincorsa fa già questo |
| mette prezzi sempre sotto il minimo dei concorrenti | **Undercutter** | Pericoloso quando i prodotti scarseggiano. Il pavimento (`margin_min`, `market_band_low`) evita di seguirlo in perdita |
| vende sotto costo per metà partita | **Dumper** | Chiude in negativo. Non seguitelo; profilo `glut` se dura a lungo |
| compra tutta l'offerta di un materiale | **Hoarder** | Paga cara ogni unità. Il nostro valore massimo limita l'offerta; spostate la produzione sul prodotto che usa meno quel materiale (l'agente lo fa già, dando priorità al margine unitario) |
| tiene prezzi alti e li taglia di colpo se tagliate voi | **Colluder** (tit-for-tat) | Conviene stargli **appena sotto**, non molto sotto, per non far scattare la punizione |
| copia il prezzo medio | **Copycat** | Segue il mercato: è un rivale costante, si batte sul volume e sulle aste |
| cambia markup a scatti all'inizio, poi si stabilizza | **BanditPricer** | Impara in fretta. Nella libreria è il rivale più forte nel lineup league |

Risultati attuali sui seed di taratura: lineup `league` (3-7 avversari casuali) **1° in 18 partite su 20**; lineup `tough` (hoarder, dumper, colluder, copycat) **1° in 19 su 20**.

---

## 6. Limiti da tenere a mente

- **Tutto è tarato sul simulatore di prova.** Il valore del playbook è nella *direzione* (quale profilo per quale tipo di gioco e quali parametri toccare), non nei numeri esatti.
- Le differenze tra profili sotto ~0,08 di rank sono rumore statistico. Per questo il playbook consiglia `balanced` in quei casi.
- `single_price` con aste pay-as-bid è catastrofico. Controllate due volte il tipo d'asta prima di usarlo.
