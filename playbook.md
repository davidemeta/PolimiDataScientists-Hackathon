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
   │    └─ non si sa con certezza / non impostato ................. single_price  (rank da 1,60 a 1,05)
   └─ prezzo unico (uniform) ...................................... single_price  (da +1,5k a +2,8k di profitto,
                                                                                    rank uguale o migliore)
   (con uniform o second_price il punto 2 non si applica)

2. COSTI E DURATA (solo con aste pay-as-bid)
   ├─ magazzino caro (costo di stoccaggio alto) ..................... glut   (rank da 1,17 a 1,03)
   ├─ partita corta (≤ 15 turni) .................................... glut   (rank da 1,28-1,43 a 1,13-1,18)
   └─ tutto il resto ................................................ balanced
        (glut è in media appena meglio: rank 1,06 contro 1,08, +0,6k di profitto.
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
| `second_price` (tipo d'asta **non** indicato all'agente) | **single_price** | 1,05 (1,60) | 21,0k (13,5k) |
| `known_second_price` (tipo d'asta indicato) | balanced | 1,05 | 21,3k (la regola automatica offre già il valore) |
| `uniform` / `known_uniform` | **single_price** | 1,07 (1,15-1,22) | 16,5k (13,7-13,9k) |
| `costly_storage` | **glut** | 1,03 (1,17) | 15,2k (14,5k) |
| `short` (10 turni) | **glut** | 1,18 (1,28) | 6,4k (6,0k) |
| tutti gli altri scenari | **balanced** (glut di poco meglio) | 1,00-1,15 | — |

I numeri sono della v6, sui seed `fresh`. Le cinque righe con un profilo diverso da balanced sono confermate anche su `tune` e `holdout`.

Media su `fresh` degli scenari pay-as-bid:

| Profilo | Rank | Profitto |
|---|---|---|
| balanced | 1,078 | 16,2k |
| rank | 1,073 | 16,3k |
| profit | 1,095 | 15,9k |
| glut | 1,059 | 16,8k |
| single_price | 4,42 | 2,0k |

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

## 6. Mercati casuali: quando il gioco vero non somiglia a nessuno scenario

`python3 run_random.py` genera mercati in cui **varia tutto insieme**:
- da 1 a 5 materie prime e da 1 a 4 prodotti, con ricette casuali;
- capacità e costi di lavorazione;
- **scala dei prezzi da ×0,1 a ×100**;
- elasticità e dimensione del mercato, abbondanza di materie prime;
- da 2 a 10 agenti e da 8 a 100 turni;
- tipo d'asta, domanda, tempi e informazioni visibili.

Risultato su 600 mercati mai usati per decidere (seed 5000+), con il profilo balanced:
- **1° nell'81% dei mercati**;
- percentile di rank medio 0,065 (0 = primo, 1 = ultimo);
- in perdita solo in 2 mercati su 600;
- zero errori e zero azioni non valide.

Su un secondo blocco (seed 9000+): 1° nell'86% dei mercati, percentile 0,046.

Cosa hanno fatto emergere, e come l'ho corretto (v5):

| Problema trovato | Correzione | Flag |
|---|---|---|
| Costanti tarate su prezzi di 5-60 €: con prezzi ×100 o ×0,1 il primo turno era sballato | Prezzo iniziale dei materiali stimato dalla scala (costo di lavorazione, oppure cassa iniziale) | `default_material_price=None` |
| Cassa insufficiente → la validazione tagliava le offerte più care → materiali **spaiati**, nessun prodotto fabbricabile | Se la cassa non basta, tutte le offerte si riducono in proporzione (kit completi) | `kit_budget` |
| Prezzi sconosciuti al turno 0 → si spendeva tutto alla cieca | Senza dati d'asta si spende al massimo il 35% della cassa | `blind_budget_share` |
| Scorte invendute ferme per 90 turni a un prezzo sopra il mercato, mentre il magazzino costava → bancarotta | Smaltimento: dopo 2 turni senza vendite, prezzo 2% sotto il concorrente più economico (sono costi affondati) | `stale_clearance` |
| Con il prezzo d'asta nascosto e la scala sbagliata, la stima saliva solo del 10% a turno | Il passo di ricerca raddoppia se si perde (o si vince) tutto per più turni | `probe_accel` |

Effetto, misurato su 600 mercati nuovi:
- percentile di rank da 0,117 a **0,065**;
- mercati in perdita da 17 a **2**;
- 1° posto dal 75% all'**81%**.

**Il costo:** sugli scenari "conosciuti" del catalogo il profitto scende dell'1,4% (rank da 1,106 a 1,109, dentro il rumore). È un'assicurazione: domani il mercato sarà sconosciuto.

Restano un po' più deboli, pur restando quasi sempre primi:
- le partite molto corte (8-12 turni), con percentile circa 0,13;
- i mercati con 4 materie prime, circa 0,12;
- i mercati con un solo prodotto, circa 0,10.

---

### Partite corte (v6)

Ho fatto 2.000 simulazioni di partite da 5 a 15 turni su mercati casuali. È emerso che **i primi 2 turni sono in perdita**: −8% e −2% della cassa iniziale, perché l'agente compra alla cieca e strapaga. In una partita da 5 turni questo costo d'avvio pesa tantissimo. Inoltre le sconfitte sono di misura: in mediana facciamo il 91% del vincitore.

Ho fatto uno sweep di 9 parametri e poi di 10 combinazioni, misurando su un blocco di taratura, uno di verifica e uno di mercati di ogni durata. Sono cambiati cinque default:

| Parametro | Prima | v6 | Perché |
|---|---|---|---|
| `margin_init` | 0,40 | **0,60** | si parte con un prezzo più alto, quindi meno perdite nei primi turni |
| `first_bid_fraction` | 0,75 | **0,55** | al turno 0 si strapaga meno quando i prezzi non si conoscono |
| `liquidation_turns` | 2 | **1** | si svende solo all'ultimo turno, non per due turni |
| `target_stock_turns` | 1,5 | **1,25** | meno scorte, quindi meno rischio di invenduto |
| `bid_surplus_share` | 0,30 | **0,15** | offerte un po' meno aggressive |

Risultati su blocchi di seed **mai usati per tarare**:

| Misura | v5 | v6 |
|---|---|---|
| Partite corte: 1° posto | 68% | **76-78%** |
| Partite corte: percentile di rank | 0,123 | **0,074-0,084** |
| Tutte le durate: 1° posto | 81% | **86%** |
| Tutte le durate: percentile di rank | 0,065 | **0,043-0,047** |
| Scenari noti (pay-as-bid, fresh): rank | 1,113 | **1,072** (profitto +0,4k; scenario peggiore da 2,05 a 1,27) |

Con la partita corta il profilo `glut` dà ancora un piccolo vantaggio (vedi §1).

## 7. Limiti da tenere a mente

- **Tutto è tarato sul simulatore di prova.** Il valore del playbook è nella *direzione* (quale profilo per quale tipo di gioco e quali parametri toccare), non nei numeri esatti.
- Le differenze tra profili sotto ~0,08 di rank sono rumore statistico. Per questo il playbook consiglia `balanced` in quei casi.
- `single_price` con aste pay-as-bid è catastrofico. Controllate due volte il tipo d'asta prima di usarlo.
