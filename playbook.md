# Playbook per domani: dal briefing al profilo giusto

Scopo: trasformare le risposte del briefing (14:30-14:45) in **un profilo dell'agente e 2-3 parametri da ritarare**, senza perdere tempo.

- La strategia generale è in [strategy.md](strategy.md).
- I concetti economici sono in [knowledge_base.md](knowledge_base.md).
- I numeri citati qui vengono da `run_matrix.py`: 28 scenari × 5 profili × 3 gruppi di avversari, su tre blocchi di seed. L'ultimo blocco non è mai stato usato per decidere (metodo nel §2).

---

## 1. Albero decisionale (seguitelo in quest'ordine)

```
1. TIPO D'ASTA  (e scrivetelo in adapter.py → GameInfo.auction_type!)
   ├─ si paga la PROPRIA offerta (pay-as-bid / primo prezzo) ...... balanced  → vai al punto 2
   ├─ secondo prezzo
   │    ├─ e l'avete scritto in auction_type ...................... balanced  (offre già il valore da solo)
   │    └─ non si sa con certezza / non impostato ................. single_price  (rank da 1,43 a 1,08)
   └─ prezzo unico (uniform)
        ├─ punteggio = profitto ................................... single_price  (circa +1k di profitto, stesso rank)
        └─ punteggio = classifica ................................. balanced
   (con uniform o second_price il punto 2 non si applica)

2. COSTI E DURATA (solo con aste pay-as-bid)
   ├─ magazzino caro (costo di stoccaggio alto) ..................... glut   (rank da 1,20 a 1,08)
   ├─ partita corta (≤ 15 turni) .................................... glut   (rank da 1,87 a 1,55)
   └─ tutto il resto ................................................ balanced
        (glut è in media appena meglio: rank 1,06 contro 1,10, +0,5k di profitto.
         Provatelo con il comando rapido del §3 sullo scenario vero)

3. TEMPI (se diversi da "compro, produco e vendo nello stesso turno")
   └─ già gestiti dall'agente: impostate SOLO i flag in GameInfo (adapter.py)
        sell_same_turn=False           → si vende il turno dopo la produzione
        production_after_auction=False → si produce solo con materiali già in magazzino

4. INFORMAZIONI VISIBILI
   └─ già gestite: se manca il prezzo d'aggiudicazione l'agente lo deduce dalle proprie
      vincite; se mancano i prezzi dei concorrenti salta l'ancoraggio al mercato.
      Lasciate il campo vuoto nell'adapter, NON mettete zero.
      Se il gioco annuncia le unità all'asta prima delle offerte → current_supply.

5. PUNTEGGIO (si applica sopra il profilo scelto)
   ├─ classifica relativa ........ override  anti_escalation=False   (= profilo rank)
   ├─ profitto assoluto .......... lasciate anti_escalation=True (default)
   └─ media su più partite ....... guardate il MINIMO nel torneo, non solo la media
```

**Come combinare un profilo con gli override.** In `adapter.py` cambiate `PROFILE`, oppure scrivete:

```python
SmartAgent(name="team", profile="glut", config={"anti_escalation": False})
```

---

## 2. Cosa dicono i numeri

**Metodo.** Le misure vengono da `run_matrix.py`: 28 scenari × 5 profili × 3 gruppi di avversari (mixed, league, tough), su tre blocchi di seed:
- `tune` (0-…);
- `holdout` (1000-…), già usato per scegliere v2-v4, quindi non più indipendente;
- `fresh` (5000-…, 20 partite), **mai usato per decidere nulla**.

Un profilo diverso da `balanced` è consigliato solo se migliora su `tune` **e** `holdout` e poi si conferma su `fresh`.

**Risultato:** in quasi tutti gli scenari `balanced` va bene quanto i profili specializzati. L'agente si adatta già da solo ai tempi, alle informazioni nascoste e alla scarsità. Le eccezioni, confermate su tutti e tre i blocchi, sono queste:

| Scenario | Profilo | Rank fresh (balanced) | Profitto fresh (balanced) |
|---|---|---|---|
| `second_price` (tipo d'asta **non** indicato all'agente) | **single_price** | 1,08 (1,43) | 18,5k (13,4k) |
| `known_second_price` (tipo d'asta indicato) | balanced | 1,13 | 18,6k (la regola automatica offre già il valore) |
| `uniform` / `known_uniform` | **single_price** se il punteggio è il profitto | 1,15 (1,08-1,17) | 14,3k (13,1-13,6k) |
| `costly_storage` | **glut** | 1,08 (1,20) | 14,8k (14,3k) |
| `short` (10 turni) | **glut** | 1,55 (1,87) | 5,8k (5,5k) |
| tutti gli altri 22 scenari | **balanced** | 1,00-1,17 | — |

Media su `fresh` degli scenari pay-as-bid:

| Profilo | Rank | Profitto |
|---|---|---|
| balanced | 1,096 | 16,1k |
| rank | 1,078 | 16,2k |
| profit | 1,069 | 16,2k |
| glut | 1,064 | 16,7k |
| single_price | 4,08 | 3,0k |

**Il profilo `single_price` va usato SOLO con aste uniform o second_price.** Con aste pay-as-bid è disastroso: rank circa 4, profitto circa 3k, perché paga ogni unità al proprio valore.

> Nota: nelle prime misure avevo incluso anche un gruppo `self` (avversari = copie di `balanced`). Lì `balanced` fa circa 2,5 per simmetria e ogni altro profilo parte avvantaggiato, cosa che gonfiava i vantaggi dei profili. È stato tolto dal default di `run_matrix.py`, ma si può ancora usare con `--lineup self`.

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

### Avversari che cambiano strategia o sbagliano a caso

Nella libreria ci sono anche:
- **Switcher**, che cambia strategia ogni 5-8 turni circa (bandit → sniper → dumper…);
- **Trembler**, un agente "scarso" che nel 15-30% delle decisioni fa una cosa assurda: prezzo ×0,2 o ×4, offerta ×5, produzione zero.

Il lineup `chaos` ne mette 5 insieme. L'agente **vince 20 partite su 20** su `base`, e su tutti i 28 scenari ha rank 1,05-1,08.

Ho provato tre protezioni, tutte disponibili come flag ma spente di default:
- `comp_stat="median"`: mediana dei prezzi dei concorrenti;
- `clear_outlier_cap=0.4`: limite ai dati d'asta anomali;
- `change_detect=True`: rilevamento dei cambi (CUSUM), che fa ripartire le stime dal dato nuovo.

**Nessuna migliora**, su nessuno dei tre blocchi di seed: il profitto scende di 0,2-1,2k e il rank non cambia oltre il rumore. Il motivo probabile è che l'agente non classifica gli avversari ma reagisce ai segnali aggregati (prezzo d'asta, vendite, magazzino), che assorbono già i cambi di strategia. Inoltre filtrare i dati "strani" fa perdere anche le informazioni vere.

**Quando riprovarle domani:** se nel log (`logs/live.csv`) vedete i prezzi dei concorrenti (`comp_*`) saltare in modo assurdo da un turno all'altro e l'agente inseguirli. Confrontate con `run_tournament.py --scenario real --set comp_stat=median`.

## 6. Limiti da tenere a mente

- **Tutto è tarato sul simulatore di prova.** Il valore del playbook è nella *direzione* (quale profilo per quale tipo di gioco e quali parametri toccare), non nei numeri esatti.
- Le differenze tra profili sotto ~0,08 di rank sono rumore statistico. Per questo il playbook consiglia `balanced` in quei casi.
- `single_price` con aste pay-as-bid è catastrofico. Controllate due volte il tipo d'asta prima di usarlo.
