# Agente per l'AI Dynamic Pricing Hackathon

Questo è lo scheletro dell'agente, pronto da collegare all'API vera degli organizzatori. Usa **solo la libreria standard di Python** (3.9+), quindi non serve installare niente.

- Strategia complessiva: [strategy.md](strategy.md)
- Concetti di economia: [knowledge_base.md](knowledge_base.md)

## Comandi

```bash
python3 tests/test_robustness.py                 # 16 test: mai crash, mai azioni invalide
python3 run_game.py --seed 3                     # una partita, log in logs/team.csv
python3 run_tournament.py                        # torneo contro 5 gruppi di avversari
python3 run_tournament.py --sweep "bid_fraction=0.7,0.8,0.9,1.0"   # tuning di un parametro
python3 run_tournament.py --set margin_init=0.5 --lineup aggressive
python3 run_tournament.py --auction uniform      # aste a prezzo uniforme invece che pay-as-bid
```

## Struttura

```
agent/                  ← IL NOSTRO AGENTE (quello che si consegna)
  interface.py          Observation / Action / GameInfo (il "contratto" agente ↔ gioco)
  core.py               SmartAgent.act(obs): flusso del turno, try/except, fallback sicuro, reset a nuova partita
  config.py             TUTTI i parametri (+ STABLE_CONFIG = versione consegnata)
  memory.py             storia di mercato: EMA dei prezzi d'asta, dei concorrenti e delle vendite; markup adattivo; premium d'asta
  estimators.py         EMA, regressione lineare della domanda, prezzo ottimo p* = (a/b + c)/2
  pricing.py            prezzo: markup adattivo + modello di domanda + banda di mercato + esplorazione + liquidazione finale
  production.py         quanto produrre: vendite attese × copertura − scorte, capacità ai prodotti più redditizi
  bidding.py            offerte: valore marginale della materia prima (tetto) + EMA prezzo d'aggiudicazione + 2 fasce di prezzo
  safety.py             validazione: quantità intere ≥ 0, capacità, cassa, prezzi finiti
  logger.py             CSV con una riga per turno
sim/                    ← SOLO PER I TEST LOCALI
  market.py             simulatore di prova (aste busta chiusa, produzione, domanda logit)
  opponents.py          avversari: Undercutter, HighPricer, Overbidder, Random, Fixed
adapter.py              ← DA COMPLETARE DOMANI: traduce l'API vera ↔ Observation/Action
run_game.py, run_tournament.py, tests/
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

La versione di default è la **v3**. Come avversario di confronto c'è la **v1** (`STABLE_CONFIG`, congelata). Tutti i numeri qui sotto vengono da 30 partite con seed mai usati per la taratura (1000-1029).

Pay-as-bid, nel formato media / minimo / rank:

| Lineup | v1 | v2 | v3 |
|---|---|---|---|
| mixed | 11,1k / 1,2k / 2,57 | 17,2k / 11,4k / 1,00 | 16,5k / 10,2k / 1,00 |
| aggressive | 18,4k / 8,6k / 1,00 | 14,3k / 9,2k / 1,00 | 12,7k / 7,4k / 1,00 |
| passive | 26,2k / 22,6k / 1,00 | 33,0k / 28,5k / 1,00 | 34,1k / 30,7k / 1,00 |
| come la partita d'esempio | 16,6k / 6,3k / 1,93 | 18,2k / 14,0k / 1,33 | 18,7k / 13,5k / 1,50 |
| contro 2 copie di v2 e un undercutter | 6,8k / 4,6k / 2,80 | 7,2k / 5,2k / 2,20 | **8,8k / 6,8k / 1,73** |

Nella partita d'esempio (seed 4) i punteggi sono: v1 10,6k (2°), v2 9,5k (1°), **v3 11,7k (1°)**.

### Cosa è cambiato (ogni modifica ha un flag in config.py)

| Versione | Modifica | Flag |
|---|---|---|
| v2 | Stima della domanda adattiva: crescita che accelera con i sold-out consecutivi, bonus se anche i concorrenti alzano i prezzi | `demand_estimator="adaptive"` |
| v2 | Previsione del prezzo d'asta con trend (Holt) | `price_forecast="holt"` |
| v2 | Offerta = previsione + 20% del margine tra previsione e valore massimo | `bid_rule="surplus_share"` |
| v2 | Mai più del 20% sopra l'ultimo prezzo d'aggiudicazione | `bid_cap_over_last=0.20` |
| v3 | **Anti-rincorsa**: se il prezzo d'asta sale da 3 turni e il nostro magazzino cresce (o vendiamo meno dell'80%), offriamo al massimo l'ultimo prezzo d'aggiudicazione, senza trend e senza premio | `anti_escalation=True` |
| v3 | **Valore ancorato al mercato**: il valore delle materie prime si calcola sul prezzo a cui abbiamo davvero venduto tutto (+10%), non sul prezzo "costo + margine" che sale insieme al costo | `value_anchor="confirmed"` |
| — | Premio che reagisce subito all'ultimo turno: **peggiora**, non usato | `premium_mode="fast"` |

### Attenzione

- **Profitto o classifica?** La v3 compra meno durante le rincorse, quindi in media guadagna di più contro avversari che rincorrono. Però può lasciare materie prime ai rivali. Con le aste uniform, contro copie della v2, il profitto passa da 9,0k a 10,4k ma il rank peggiora da 1,97 a 2,57. Se domani il punteggio è la **classifica relativa**, provate `anti_escalation=False`. Se è il **profitto assoluto**, tenetela.
- **Il trend sbaglia ancora quando il prezzo cambia direzione.** Al turno 10 della partita d'esempio offriamo 24,3 quando l'asta si chiude a 16,9. Il tetto del +20% sull'ultimo prezzo limita il danno ma non lo elimina.
- I valori sono tarati sul simulatore di prova. Domani vanno ritarati su quello vero.
