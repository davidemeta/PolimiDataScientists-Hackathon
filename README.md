# Agente per l'AI Dynamic Pricing Hackathon

Questo è lo scheletro dell'agente, pronto da collegare all'API vera degli organizzatori. Usa **solo la libreria standard di Python** (3.9+), quindi non serve installare niente.

- Strategia complessiva: [strategy.md](strategy.md)
- Concetti di economia: [knowledge_base.md](knowledge_base.md)
- **Domani dopo il briefing: [playbook.md](playbook.md)**, che indica quale profilo usare per quale gioco

## Comandi

```bash
python3 tests/test_robustness.py                 # 17 test, tutti gli scenari × profili: mai crash né azioni invalide
python3 run_game.py --seed 3                     # una partita, log in logs/team.csv
python3 run_tournament.py                        # torneo contro 8 gruppi di avversari
python3 run_tournament.py --lineup league --scenario uniform --profile single_price
python3 run_tournament.py --sweep "bid_surplus_share=0.1,0.2,0.3,0.5" --scenario real
python3 run_matrix.py --quick --scenario base    # quale profilo conviene? (meno di 1 secondo)
python3 run_matrix.py --seeds fresh              # matrice completa 28 scenari × 5 profili (circa 15 secondi)
```

## Struttura

```
agent/                  ← IL NOSTRO AGENTE (quello che si consegna)
  interface.py          Observation / Action / GameInfo (il "contratto" agente ↔ gioco)
  core.py               SmartAgent.act(obs): flusso del turno, try/except, fallback sicuro, reset a nuova partita
  config.py             TUTTI i parametri + PROFILES (balanced, rank, profit, single_price, glut) + STABLE_CONFIG (v1)
  memory.py             storia di mercato: EMA dei prezzi d'asta, dei concorrenti e delle vendite; markup adattivo; premium d'asta
  estimators.py         EMA, regressione lineare della domanda, prezzo ottimo p* = (a/b + c)/2
  pricing.py            prezzo: markup adattivo + modello di domanda + banda di mercato + esplorazione + liquidazione finale
  production.py         quanto produrre: vendite attese × copertura − scorte, capacità ai prodotti più redditizi
  bidding.py            offerte: valore marginale della materia prima (tetto) + EMA prezzo d'aggiudicazione + 2 fasce di prezzo
  safety.py             validazione: quantità intere ≥ 0, capacità, cassa, prezzi finiti
  logger.py             CSV con una riga per turno
sim/                    ← SOLO PER I TEST LOCALI
  market.py             simulatore di prova: aste pay-as-bid/uniform/second_price, domanda logit/linear/cheapest_first,
                        tempi della filiera, informazioni nascoste, costi
  scenarios.py          catalogo di 28 varianti di mercato (+ dove aggiungere lo scenario "real" domani)
  opponents.py          14 tipi di avversario (compresi Switcher e Trembler) + lineup casuale "league"
adapter.py              ← DA COMPLETARE DOMANI: traduce l'API vera ↔ Observation/Action, sceglie il PROFILE
run_game.py, run_tournament.py, run_matrix.py, tests/, playbook.md
```

## Domani: come collegarlo (ruolo A, circa 20 minuti)

1. Leggete il bot di esempio e la documentazione degli organizzatori. **Prima di tutto capite il formato di submission**: un file solo? Una cartella? Una classe con un nome preciso? Se serve un file unico, unite `agent/*.py` + `adapter.py` in un solo file (con un assistente di coding sono 2 minuti) e rilanciate i test. `agent/` è autosufficiente: non dipende da `sim/`.
2. Completate `adapter.py`: mappate i loro dati su `Observation` e convertite la nostra `Action` nel loro formato. Se il loro modello del gioco è diverso (per esempio si vende il turno dopo la produzione, oppure la produzione usa solo materiali già in magazzino), impostate i flag `sell_same_turn` e `production_after_auction` in `GameInfo`.
3. **Prima submission subito**, con i parametri di default.
4. Aggiornate `sim/market.py` / `MarketConfig` per assomigliare al loro simulatore: tipo d'asta, forma della domanda, numero di turni, costi. Più il simulatore locale è simile a quello vero, più il torneo è affidabile.
5. Da qui in poi ogni modifica segue questo giro: `tests` → `run_tournament` → confronto con `stable` → commit → submission.

## Come lavorano i tre ruoli

| Ruolo | File | Cosa provare |
|---|---|---|
| A: integrazione | `adapter.py`, `sim/market.py`, `tests/` | adapter, simulatore fedele all'originale, submission |
| B: aste | `bidding.py`, parametri `bid_*`, `premium_*`, `tier_*` | tetto d'offerta, bid shading, reazione al tasso di vittoria |
| C: prezzi e produzione | `pricing.py`, `production.py`, parametri `margin_*`, `target_stock_turns`, `liquidation_*` | markup, modello di domanda, finale |

## Regole per lavorare insieme

- **Un parametro alla volta**, e almeno 20 partite su più lineup. Guardate la media **e** il minimo.
- Quando una versione batte `stable` su tutti i lineup: consegnatela, poi copiate la sua config **come dizionario letterale** in `STABLE_CONFIG`. Oggi `STABLE_CONFIG` è solo `dict(DEFAULT_CONFIG)`, quindi va congelata.
- **Non ottimizzate troppo sul simulatore di prova**: è un'approssimazione. Fidatevi di più di un miglioramento che vale su tutti i lineup che di un +20% su uno solo.
- `SmartAgent(debug=True)` rilancia le eccezioni, e serve in sviluppo. **In submission lasciate `debug=False`.**

## Risultati attuali (simulatore di prova)

La versione di default è la **v4** (profilo `balanced`). Rispetto alla v3 aggiunge un pavimento ai prezzi: `margin_min=0.15` e mai più del 5% sotto la media dei concorrenti. Il miglioramento è piccolo. Su 23 scenari pay-as-bid, con seed mai usati per decidere (5000+) e avversari mixed, league e tough, il rank passa da 1,112 a 1,096 e il profitto da 15,6k a 16,1k.

Lineup sullo scenario `base`, 20 partite:

| Lineup | Media | Minimo | Rank | Vittorie |
|---|---|---|---|---|
| mixed | 16,7k | 11,2k | 1,05 | 19/20 |
| aggressive | 12,8k | 4,0k | 1,00 | 20/20 |
| passive | 38,7k | 33,9k | 1,00 | 20/20 |
| league (3-7 avversari casuali) | 14,8k | 8,1k | 1,10 | 18/20 |
| tough (hoarder, dumper, colluder, copycat) | 10,2k | 9,1k | 1,05 | 19/20 |

**Robustezza agli scenari.** Prima di questo lavoro l'agente crollava in diversi scenari, perché non gestiva le informazioni nascoste e la filiera lenta. Il test è lo stesso per le due colonne: 6 agenti, seed 0-9.

| Scenario | v3 | v4 |
|---|---|---|
| prezzo d'aggiudicazione nascosto | 0,5k | 17,0k |
| nessuna informazione | 0,4k | 14,0k |
| filiera lenta (produzione da magazzino, vendita il turno dopo), rank | 3,6 | 1,0 |
| scenario peggiore combinato, rank | 4,2 | 1,0 |

Il dettaglio per scenario e profilo è in [playbook.md](playbook.md).

### Storia delle versioni (ogni modifica ha un flag in config.py)

| Versione | Modifica | Flag |
|---|---|---|
| v2 | Stima della domanda adattiva (crescita che accelera con i sold-out consecutivi) | `demand_estimator="adaptive"` |
| v2 | Previsione del prezzo d'asta con trend (Holt) + offerta = previsione + quota del margine, con tetto sull'ultimo prezzo | `price_forecast`, `bid_rule`, `bid_cap_over_last` |
| v3 | Anti-rincorsa sulle aste + valore dei materiali ancorato al prezzo confermato dal mercato | `anti_escalation`, `value_anchor` |
| v4 | Prezzo d'aggiudicazione nascosto dedotto dalle proprie vincite | `infer_clearing`, `probe_down`, `probe_up` |
| v4 | Ritardo della filiera: acquisti, produzione e finale coerenti con `sell_same_turn` / `production_after_auction` | automatico |
| v4 | Tipo d'asta noto → regola d'offerta automatica; offerta annunciata → offerte più o meno aggressive | `auto_auction_rule`, `supply_sensitivity` |
| v4 | Pavimento ai prezzi: niente guerre di prezzo | `margin_min=0.15`, `market_band_low=0.05` |

**Avversari che cambiano strategia o sbagliano a caso** (lineup `chaos`: 2 switcher e 3 trembler): 20 vittorie su 20 su `base`, rank 1,05-1,08 sui 28 scenari. Statistiche robuste e rilevamento dei cambi (CUSUM) sono disponibili come flag ma **non migliorano**, quindi restano spenti (dettagli nel playbook §5).

### Attenzione

- **Profitto o classifica?** L'anti-rincorsa protegge il profitto ma può lasciare materie prime ai rivali. Se il punteggio è la classifica, usate il profilo `rank` (`anti_escalation=False`).
- **`single_price` va usato solo con aste uniform o second_price.** Con le aste pay-as-bid è disastroso.
- I valori sono tarati sul simulatore di prova. Domani vanno ritarati con lo scenario `real` (vedi playbook §3).
