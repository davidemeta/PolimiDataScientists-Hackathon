# PolimiDataScientists — AI Dynamic Pricing Hackathon

Agente per l'**AI Dynamic Pricing Hackathon** (PMDS × AIRIC, Politecnico di Milano, 18 novembre 2026). A ogni turno il nostro agente:

1. fa offerte nelle **aste** per le materie prime;
2. **pianifica la produzione**;
3. fissa i **prezzi** di vendita.

Gioca contro gli agenti delle altre squadre, e tutti muovono in contemporanea.

Usa **solo la libreria standard di Python** (3.9+): non serve installare niente.

```bash
git clone https://github.com/davidemeta/PolimiDataScientists-Hackathon.git
cd PolimiDataScientists-Hackathon
python3 tests/test_robustness.py      # 18 test, devono essere tutti verdi
python3 run_tournament.py             # torneo locale contro 10 gruppi di avversari
```

## Documenti

| File | A cosa serve |
|---|---|
| **[playbook.md](playbook.md)** | **Da usare domani dopo il briefing**: albero decisionale per scegliere il profilo, procedura minuto per minuto, parametri da ritarare per primi |
| [strategy.md](strategy.md) | Strategia complessiva e divisione dei ruoli |
| [knowledge_base.md](knowledge_base.md) | Concetti di economia: aste, domanda, pricing, previsioni |

## Come funziona l'agente

A ogni turno `SmartAgent.act(obs)` esegue quattro passi:

- **Memoria** (`memory.py`): aggiorna la storia del mercato.
  - Previsione del prezzo d'asta con trend (Holt smorzato).
  - Prezzi dei concorrenti.
  - Domanda stimata in modo adattivo: cresce più in fretta se andiamo in sold-out più turni di fila.
  - Prezzo d'aggiudicazione dedotto dalle nostre vincite quando non è visibile.
- **Prezzi** (`pricing.py`): parte da un markup adattivo e lo mescola con un modello di domanda, p\* = (a/b + c)/2. Poi:
  - lo tiene dentro una banda attorno ai prezzi dei concorrenti;
  - esplora nei primi turni;
  - smaltisce le scorte ferme;
  - applica un pavimento al margine;
  - liquida tutto all'ultimo turno.
- **Produzione** (`production.py`): produce le vendite attese × copertura − scorte, rispettando i ritardi della filiera, e dà la capacità ai prodotti con il margine unitario più alto.
- **Offerte** (`bidding.py`): offerta = previsione + una quota del margine fino al valore massimo della materia prima. In più:
  - un tetto rispetto all'ultimo prezzo d'aggiudicazione;
  - un freno anti-rincorsa;
  - la regola d'offerta che si adatta al tipo d'asta;
  - materie prime complementari comprate a kit completi;
  - un budget prudente finché non ci sono dati.

Ogni turno è in un try/except con una mossa di riserva sicura. Tutte le azioni passano da una validazione (`safety.py`): quantità intere ≥ 0, capacità, cassa, prezzi finiti.

### Profili

Si sceglie un profilo con una riga: `PROFILE` in `adapter.py`, oppure `--profile` negli script.

| Profilo | Quando usarlo |
|---|---|
| `balanced` | default, asta pay-as-bid o tipo d'asta sconosciuto |
| `single_price` | asta **uniform**, oppure second-price non annunciata (con pay-as-bid è disastroso) |
| `glut` | partite corte, magazzino costoso, molta offerta |
| `rank` | se il punteggio è la classifica e non il profitto (anti-rincorsa spenta) |
| `profit` | offerte più prudenti, per massimizzare il profitto assoluto |

## Comandi

```bash
python3 tests/test_robustness.py                         # 18 test: scenari × profili, 80 mercati casuali, fuzz
python3 run_game.py --seed 3                             # una partita, log in logs/team.csv
python3 run_tournament.py                                # torneo contro 10 gruppi di avversari
python3 run_tournament.py --lineup league --scenario uniform --profile single_price
python3 run_tournament.py --sweep "bid_surplus_share=0.1,0.2,0.3" --scenario real
python3 run_matrix.py --quick --scenario base            # quale profilo conviene? (meno di 1 secondo)
python3 run_matrix.py --seeds fresh                      # 28 scenari × 5 profili (circa 15 secondi)
python3 run_random.py --n 600 --seed0 5000               # 600 mercati casuali (cambia tutto, anche la scala dei prezzi)
python3 run_random.py --n 2000 --turns 5,6,8,10,12,15    # solo partite corte
```

## Struttura

```
agent/                  ← IL NOSTRO AGENTE (quello che si consegna; non dipende da sim/)
  interface.py          Observation / Action / GameInfo: il "contratto" tra agente e gioco
  core.py               SmartAgent: flusso del turno, fallback sicuro, reset a ogni nuova partita
  config.py             tutti i parametri, PROFILES, STABLE_CONFIG (v1 congelata)
  memory.py             storia di mercato, previsioni, stima della domanda, prezzo dedotto
  estimators.py         EMA, Holt, regressione lineare della domanda
  pricing.py            prezzi
  production.py         produzione
  bidding.py            offerte nelle aste
  safety.py             validazione delle azioni
  logger.py             CSV con una riga per turno
sim/                    ← SOLO PER I TEST LOCALI
  market.py             simulatore: aste pay_as_bid / uniform / second_price; domanda logit / linear /
                        cheapest_first; ritardi della filiera; informazioni nascoste; costi
  scenarios.py          28 varianti di mercato (domani si aggiunge SCENARIOS["real"])
  random_markets.py     mercati casuali: 1-5 materie prime, 1-4 prodotti, prezzi da ×0,1 a ×100, …
  opponents.py          14 tipi di avversario (undercutter, hoarder, dumper, colluder, bandit, switcher, trembler, …)
adapter.py              ← DA COMPLETARE DOMANI: traduce l'API vera da e verso Observation/Action
run_game.py · run_tournament.py · run_matrix.py · run_random.py · tests/
```

## Domani: come collegarlo

1. **Capire il formato di submission**: un file? Una cartella? Una classe con un nome preciso? Se serve un file unico, unite `agent/*.py` e `adapter.py` e rilanciate i test.
2. **Completare `adapter.py`**: mappate i loro dati su `Observation` e convertite la nostra `Action` nel loro formato. I TODO sono già segnati nel file, compresi `auction_type`, `current_supply` e l'indice di turno a partire da 0. Impostate `sell_same_turn` e `production_after_auction` in base alle regole vere.
3. **Prima submission subito**, con `balanced` o con il profilo indicato dal playbook §1.
4. **Creare `SCENARIOS["real"]`** in `sim/scenarios.py` con i parametri veri, poi `run_matrix.py --quick --scenario real`.
5. Da qui in poi ogni modifica fa sempre lo stesso giro: test → torneo → confronto con `stable` → commit → submission.

| Ruolo | File | Cosa provare |
|---|---|---|
| A: integrazione | `adapter.py`, `sim/market.py`, `sim/scenarios.py` | adapter, simulatore fedele all'originale, submission |
| B: aste | `bidding.py`, parametri `bid_*` | quota del margine, tetto, anti-rincorsa |
| C: prezzi e produzione | `pricing.py`, `production.py`, parametri `margin_*`, `target_stock_turns`, `liquidation_*` | markup, modello di domanda, finale |

**Regole:**
- un parametro alla volta;
- almeno 20 partite su più lineup;
- guardare la media **e** il minimo.

In submission lasciate `debug=False`.

## Risultati (simulatore locale, v6)

Torneo sullo scenario `base`, 20 partite per lineup:

| Lineup | Media | Minimo | Rank | Vittorie |
|---|---|---|---|---|
| mixed | 17,5k | 12,6k | 1,00 | 20/20 |
| aggressive | 13,7k | 7,9k | 1,00 | 20/20 |
| passive | 39,0k | 33,8k | 1,00 | 20/20 |
| mirror | 13,1k | 10,2k | 1,00 | 20/20 |
| duel | 15,8k | 13,7k | 1,00 | 20/20 |
| tough (hoarder, dumper, colluder, copycat) | 10,8k | 9,6k | 1,00 | 20/20 |
| league (3-7 avversari casuali) | 15,2k | 8,7k | 1,10 | 19/20 |
| chaos (switcher + trembler) | 12,7k | 9,5k | 1,10 | 18/20 |
| crowded | 14,6k | 9,1k | 1,30 | 16/20 |

Su **mercati casuali** con avversari casuali (da 1 a 9), la v6 è stata misurata su blocchi di seed mai usati per tarare:
- tutte le durate: **1° nell'86%** dei mercati, in perdita in 2-3 mercati su 1.000;
- partite corte (5-15 turni): **1° nel 76-78%**, contro il 68% della v5.

Sui 28 scenari noti, con seed mai usati, il rank medio è **1,072**. Il dettaglio per scenario e profilo è nel [playbook](playbook.md) §2 e §6.

> Il lineup `self` (copie dello stesso agente) non entra nelle statistiche: lì ogni copia vince in media una partita su N.

### Storia delle versioni

Ogni modifica ha un flag in `config.py`, così si può spegnere e confrontare.

| Versione | Modifica | Flag |
|---|---|---|
| v2 | Domanda adattiva; previsione del prezzo d'asta con Holt; offerta = previsione + quota del margine, con tetto | `demand_estimator`, `price_forecast`, `bid_rule`, `bid_cap_over_last` |
| v3 | Anti-rincorsa; valore dei materiali ancorato al prezzo confermato | `anti_escalation`, `value_anchor` |
| v4 | Prezzo d'aggiudicazione nascosto dedotto; ritardi della filiera; regola d'offerta per tipo d'asta; pavimento ai prezzi | `infer_clearing`, `auto_auction_rule`, `supply_sensitivity`, `margin_min` |
| v5 | Mercati sconosciuti: scala dei prezzi stimata, offerte a kit, budget prudente senza dati, smaltimento delle scorte ferme | `default_material_price`, `kit_budget`, `blind_budget_share`, `stale_clearance`, `probe_accel` |
| v6 | Partite corte: avvio meno costoso | `margin_init`, `first_bid_fraction`, `liquidation_turns`, `target_stock_turns`, `bid_surplus_share` |

### Limiti

- I valori sono tarati su un simulatore di prova. Domani vanno ritarati sullo scenario `real` (playbook §3).
- **Profitto o classifica?** L'anti-rincorsa protegge il profitto ma può lasciare materie prime ai rivali. Se conta la classifica, usate il profilo `rank`.
- Statistiche robuste e rilevamento dei cambi (CUSUM) esistono come flag, ma non migliorano i risultati e restano spenti.
