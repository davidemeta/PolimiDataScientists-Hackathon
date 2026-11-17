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

## Risultati attuali (simulatore di prova, 20 partite, aste pay-as-bid)

Rank medio del nostro agente:

| Lineup | Rank medio | Partecipanti | Note |
|---|---|---|---|
| mixed | 2.1 | 6 | **2°**: l'Undercutter vince 11/20 (media 13.3k contro i nostri 11.8k), noi 7/20 |
| aggressive | 1.0 | 5 | vince 20/20 |
| passive | 1.0 | 4 | vince 20/20 |
| mirror / duel | ≈ media | 5 / 2 | oggi `stable` = stessa config, quindi è self-play |

Rispetto alla prima versione (`target_stock_turns=1.2`, `stockout_boost=1.3`), la taratura attuale (1.5 / 1.5) vinceva 18/20 nel mirror e 19/20 nel duel.

**Attenzione:** i valori 1.5 / 1.5 sono stati scelti sugli stessi 20 seed riportati qui, e hanno peggiorato il caso peggiore: il minimo in `aggressive` è circa 4.2k e in `mixed` circa 3.1k, entrambi sotto la cassa iniziale di 5k. **Sono valori provvisori**: non ottimizzate oltre sul simulatore di prova, ritarateli domani su quello vero.

Il rivale più pericoloso è l'**Undercutter**: produce a piena capacità e taglia i prezzi. Quando il mercato è scarso di prodotto, il volume conta. In mercati affollati di aggressivi, invece, produrre troppo fa male. È esattamente il tipo di compromesso che va ritarato sul simulatore vero.
