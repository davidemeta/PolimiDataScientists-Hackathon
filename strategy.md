# Strategia: AI Dynamic Pricing Hackathon (PMDS × AIRIC)

**Quando:** 18 novembre 2026. Hacking dalle 14:45 alle 17:45, cioè **3 ore effettive**.
**Squadra:** 3 persone.
**Obiettivo:** costruire un agente che, turno per turno, partecipa alle aste per le materie prime, pianifica la produzione e fissa i prezzi, nello stesso mercato degli agenti delle altre squadre e con mosse simultanee.

I concetti economici citati qui sono spiegati in [knowledge_base.md](knowledge_base.md).

---

## 0. Le 10 regole d'oro (da rileggere quando siete sotto pressione)

1. **Un agente che non crasha batte un agente intelligente che crasha.**
2. **Fate una consegna entro le 15:30**, anche con un agente banale. Così avete testato il sito di submission.
3. **Leggete il codice del simulatore** prima di scrivere strategia: spesso domanda, aste e punteggio sono scritti lì in chiaro.
4. **Sapete come si calcola il punteggio** prima di decidere cosa ottimizzare.
5. **Non pagate mai una materia prima più di quanto vi frutta** (il valore marginale).
6. **Non producete più di quanto potete vendere** prima che la partita finisca.
7. **Gestite il finale:** negli ultimi turni smettete di comprare e svuotate il magazzino.
8. **Cambiate un parametro alla volta** e confrontate su più partite, mai su una sola.
9. **Testate contro avversari diversi**, non solo contro voi stessi.
10. **Dalle 17:30 non si tocca più niente.**

---

## 1. Stasera (17 nov), 45-60 minuti

- [ ] Python 3.10+ e un IDE funzionanti su tutti e 3 i laptop. Provate anche GitHub Codespaces come piano B.
- [ ] Pacchetti preinstallati: `numpy pandas scipy matplotlib scikit-learn`. Niente modelli pesanti come TimesFM o Timestral.
- [ ] Un repo Git privato condiviso, con tutti e 3 come collaboratori.
- [ ] Assistente di coding (Claude Code, Cursor o Copilot) installato e loggato su ogni laptop.
- [ ] Uno scheletro dell'agente già pronto (vedi §6), con wrapper sicuro, logging, stimatori EMA e script del torneo.
- [ ] Ognuno legge [knowledge_base.md](knowledge_base.md), almeno le sezioni 1-6.
- [ ] Caricabatterie, ciabatta, hotspot del telefono come backup del Wi-Fi.
- [ ] Ruoli decisi (vedi §3).

---

## 2. Tabella di marcia di domani

| Ora | Cosa | Chi |
|---|---|---|
| 14:00-14:30 | Check-in. Cercate posti vicino a una presa. Clonate lo starter kit appena è disponibile. | Tutti |
| 14:30-14:45 | **Briefing.** Uno prende appunti sulle domande del §4 e uno fa le domande agli organizzatori. | Tutti |
| 14:45-15:20 | **Leggete il codice del simulatore** (checklist §5). Il risultato è un `GAME_NOTES.md` di mezza pagina. | Tutti e 3 insieme |
| 15:20-15:35 | Agente baseline collegato all'interfaccia vera. **Prima submission.** | Integrazione |
| 15:35-17:00 | Miglioramenti in parallelo per ruolo. Ogni modifica passa dal torneo locale (§9). | Tutti |
| 17:00-17:20 | Integrazione finale e tuning dei parametri sul torneo. Submission intermedia. | Tutti |
| 17:20-17:30 | Ultimi test di robustezza (§10). **Submission finale.** | Integrazione |
| 17:30-17:45 | **Freeze.** Si controlla solo che la submission sia stata accettata. | Tutti |

---

## 3. Ruoli

| Ruolo | Responsabilità | Output |
|---|---|---|
| **A: Integrazione e infrastruttura** | Setup, collegamento all'API, wrapper sicuro, logging, torneo locale, submission. **Tiene sempre una versione `stable` pronta da consegnare.** | `agent.py` funzionante, `run_tournament.py` |
| **B: Aste e acquisti** | Valore marginale delle materie prime, quanto offrire, gestione del budget e della cassa. | `bidding.py` |
| **C: Prezzi e produzione** | Stima della domanda, prezzo, quantità da produrre, gestione delle scorte, logica di fine partita. | `pricing.py`, `production.py` |

**Regole Git:**
- `main` contiene **solo** versioni che girano senza errori.
- Ognuno lavora sul proprio file o branch, e A fa il merge.
- Un tag `v1`, `v2`, ... per ogni versione consegnata, così si può sempre tornare indietro.

---

## 4. Domande per il briefing (scrivete le risposte)

**Punteggio**
- Si misura il profitto finale, la cassa finale, il ranking o una media su più partite?
- Le scorte e le materie prime rimaste a fine partita valgono qualcosa?

**Partita**
- Quanti turni dura? Quante squadre ci sono nello stesso mercato?
- Quanti prodotti esistono e quante materie prime? Qual è la ricetta di ogni prodotto?

**Osservazioni**
- Cosa vede l'agente a ogni turno: prezzi dei concorrenti, offerte perdenti, prezzo di aggiudicazione, vendite degli altri?

**Aste**
- Sono a busta chiusa? Si paga il proprio prezzo o il secondo prezzo?
- Ci sono più unità in palio? Esiste un prezzo minimo (riserva)?

**Vincoli e penali**
- Ci sono costi di magazzino, capacità di produzione, bancarotta, debito?
- C'è un tempo massimo per turno?

**Regole tecniche**
- È permesso usare LLM o API esterne durante la gara? E gli assistenti di coding?
- Si può testare in locale? Quante submission si possono fare? Conta l'ultima o la migliore?
- Quali librerie sono disponibili nell'ambiente di valutazione?

---

## 5. Checklist di lettura del simulatore (14:45-15:20)

Cercate nel codice e annotate in `GAME_NOTES.md`:

- [ ] **Funzione di domanda.** Come si calcolano le vendite dato il prezzo? È lineare, esponenziale o logit? Dipende dai prezzi degli altri? C'è rumore? → Se è esplicita, **calcolate il prezzo ottimo con la formula** ([knowledge_base §4](knowledge_base.md)).
- [ ] **Divisione della domanda tra venditori.** Il più economico prende tutto, oppure le quote sono proporzionali?
- [ ] **Meccanismo d'asta.** Primo o secondo prezzo? Come si risolvono i pareggi? Si vince un'unità o un lotto?
- [ ] **Ricetta di produzione:** materiali necessari, costo e capacità.
- [ ] **Ordine degli eventi in un turno**, per esempio aste → produzione → vendite. Si può vendere nello stesso turno in cui si produce?
- [ ] **Costi:** magazzino, costi fissi, interessi.
- [ ] **Fine partita:** cosa succede alle scorte rimaste.
- [ ] **Validazione delle azioni.** Cosa succede con un'azione non valida? Viene ignorata, si prende una penale o si viene squalificati?
- [ ] **Casualità e seed.** La partita è deterministica?

> Con un assistente di coding si fa velocemente: «leggi il simulatore e riassumimi domanda, aste, ordine degli eventi e punteggio».

---

## 6. Architettura dell'agente

```
agent.py
 ├── observe(state)            → aggiorna la memoria (storia di prezzi, aste, vendite)
 ├── estimators.py             → EMA dei prezzi di mercato, del prezzo d'asta, della domanda
 ├── bidding.py                → offerte per le materie prime
 ├── production.py             → quanto produrre
 ├── pricing.py                → prezzo di vendita
 ├── safety.py                 → validazione delle azioni e fallback
 ├── config.py                 → TUTTI i parametri in un unico dizionario
 └── logger.py                 → CSV con una riga per turno
```

**Wrapper di sicurezza (obbligatorio):**
```python
def act(state):
    try:
        action = smart_policy(state)
        return validate(action, state)   # clamp: quantità ≥ 0, budget, materiali disponibili
    except Exception as e:
        log_error(e)
        return safe_default(state)       # es. nessuna offerta, prezzo = ultimo prezzo valido
```

**Parametri in `config.py`**, così il tuning è veloce:
```python
CFG = dict(
    margin_init=0.30,      # markup iniziale sul costo
    margin_step=0.05,      # quanto si muove il margine per turno
    bid_fraction=0.85,     # quota del valore marginale da offrire
    target_stock_turns=1.5,# scorta obiettivo = vendite attese * 1.5
    endgame_turns=3,       # turni finali in cui smettere di comprare
    ema_alpha=0.3,
    cash_buffer=0.10,      # quota di cassa da non spendere mai
)
```

---

## 7. Strategia per area

### 7.1 Prezzi (ruolo C)

**Baseline.** Si parte da `prezzo = costo_unitario × (1 + margine)` e il margine si adatta con le scorte:
- vendete tutto e il magazzino si svuota → alzate il margine (state lasciando soldi sul tavolo);
- le scorte si accumulano → abbassate il margine;
- non scendete mai sotto il costo marginale, tranne nel finale (vedi §7.4).

**Ancoraggio al mercato.** Restate in una fascia intorno alla media EMA dei prezzi dei concorrenti, per esempio tra -10% e +5%. Evitate gli estremi.

**Se la domanda è nota dal codice.** Calcolate il prezzo che massimizza il profitto con la formula (knowledge_base §4) e usatelo come punto di partenza.

**Se la domanda non è nota.** Nei primi turni esplorate con 2-3 prezzi diversi e stimate la pendenza con una regressione lineare tra prezzo e quantità venduta. Poi sfruttate quello che avete imparato (knowledge_base §9).

**Niente guerre di prezzo.** Se un concorrente svende sotto costo, **non seguitelo**: si brucerà da solo. Servite la domanda che resta, con il vostro margine.

**Collusione tacita** (legale nel gioco, knowledge_base §7). Se gli avversari tengono prezzi alti, teneteli alti anche voi. Se qualcuno abbassa, rispondete per 1-2 turni (tit-for-tat) e poi tornate su.

### 7.2 Aste e acquisti (ruolo B)

**Calcolate il valore marginale di ogni materia prima**, cioè il massimo che vi conviene pagare:
```
valore_max(materiale) = (prezzo_vendita_atteso − costo_produzione − costo_altri_materiali) / unità_necessarie
```
Non offrite mai più di questo valore.

**Quanto offrire:**
- **Asta al secondo prezzo:** offrite esattamente il valore marginale (è la strategia dominante).
- **Asta al primo prezzo:** offrite meno del valore (*bid shading*), per esempio `valore × bid_fraction`. Regolate la frazione in base a quanto spesso vincete:
  - vincete sempre → state pagando troppo, abbassate;
  - perdete sempre → alzate, ma mai oltre il valore.

**Usate il prezzo d'asta passato.** Tenete un'EMA dei prezzi di aggiudicazione e offrite poco sopra la stima, se resta sotto il vostro valore.

**Comprate solo quello che vi serve.** Il fabbisogno è `vendite_attese × turni_rimasti_utili − scorte_attuali`.

**Tenete un margine di cassa.** Non spendete mai l'ultimo 10% della cassa, per evitare la bancarotta.

**Lasciate strapagare gli altri.** Se un'asta è molto contesa, lasciatela vincere ad altri e comprate nei turni o sui materiali meno contesi.

**Blocco strategico** (solo con punteggio a classifica relativa). Comprare un materiale scarso a un prezzo leggermente sopra il vostro valore può valere la pena se toglie produzione ai rivali diretti. Fatelo con cautela.

### 7.3 Produzione e scorte (ruolo C)

**Quanto produrre.** Il calcolo base è `vendite_attese(prossimo turno) × target_stock_turns − scorte_attuali`, limitato dalla capacità e dai materiali disponibili.

Con domanda incerta usate la regola del **newsvendor** (knowledge_base §6):
- margine alto e magazzino a basso costo → producete un po' di più;
- margine basso o scorte che si deprezzano → producete un po' di meno.

### 7.4 Fine partita (spesso decisivo, molte squadre lo ignorano)

Se le scorte residue valgono zero a fine partita:
- **N turni prima della fine:** smettete di comprare materie prime che non riuscirete a trasformare e vendere in tempo.
- **Ultimi 1-2 turni:** abbassate i prezzi per liquidare. Qualsiasi prezzo sopra il valore di recupero (spesso zero) è guadagno, perché il costo è già sostenuto (*sunk cost*, knowledge_base §3).
- Non producete nell'ultimo turno se non si può più vendere.

### 7.5 Profilare gli avversari

Dai dati osservati classificate ogni concorrente:
- **Aggressivo:** prezzi sotto media, offerte alte. Non inseguitelo e aspettate che bruci la cassa.
- **Conservativo:** prezzi alti. Potete stare appena sotto di lui e prendere quote di mercato.
- **Casuale o rotto:** ignoratelo.

Se il punteggio è a classifica, prestate più attenzione ai rivali vicini a voi.

---

## 8. Strategie in base al tipo di punteggio

| Punteggio | Implicazione |
|---|---|
| **Profitto assoluto** | Massimizzate il vostro profitto. Cooperate tacitamente con prezzi alti e niente guerre. |
| **Classifica relativa** | Conta anche danneggiare gli altri: blocco sulle aste, prezzi aggressivi contro chi vi è vicino. Rischio controllato. |
| **Media su più partite** | Robustezza sopra tutto: niente strategie che ogni tanto vanno a picco. |
| **Cassa finale** | Il valore delle scorte non conta, quindi liquidazione aggressiva nel finale. |
| **Valore di cassa + scorte** | Il finale è meno critico, ma non accumulate comunque. |

---

## 9. Torneo locale (ruolo A, da avere entro le 16:00)

Simulate partite del vostro agente contro un **insieme di avversari**:
1. `copia_di_noi` (la versione stable precedente)
2. `svenditore`: prezzo = costo + 5%, offerte alte
3. `prezzi_alti`: margine del 60%, offerte basse
4. `casuale`: azioni casuali ma valide
5. `baseline_organizzatori`, se forniscono un bot di esempio

Fate girare 10-20 partite con seed diversi e confrontate **profitto medio e deviazione standard**. Tenete la versione con la **media migliore e il caso peggiore accettabile**.

Per il tuning, fate una piccola grid search su 2-3 parametri chiave (`bid_fraction`, `margin_init`, `endgame_turns`) solo dopo che tutto è stabile.

---

## 10. Test di robustezza prima di ogni submission

- [ ] Partita intera senza eccezioni (controllate il log).
- [ ] Nessuna azione con quantità negative, sopra il budget o senza materiali.
- [ ] Funziona anche se i dati sono vuoti al turno 0 (nessuna storia).
- [ ] Funziona se si perdono tutte le aste e se si vincono tutte.
- [ ] Tempo per turno sotto il limite, con margine.
- [ ] Nessuna dipendenza esterna che l'ambiente di valutazione non ha.
- [ ] Nessuna chiamata di rete, se non è permessa.

---

## 11. Uso dell'AI

- **Durante lo sviluppo:** usate un assistente di coding per leggere il simulatore e scrivere il codice. È il vero acceleratore (verificate che sia ammesso).
- **Dentro l'agente:** modelli numerici semplici (EMA, regressione lineare, regole). Niente LLM nel loop decisionale (lenti e imprevedibili), salvo richiesta esplicita delle regole. Niente TimesFM o Timestral: con poche decine di turni non battono un'EMA e aggiungono rischio.
- **Se volete dire "AI" nel pitch:** parlate di stima online della domanda, di un bandit per il prezzo e del profilo degli avversari. È AI vera, ma leggera.

---

## 12. Errori da evitare

- Passare la prima ora a scrivere strategia senza aver collegato l'agente all'API.
- Testare la submission per la prima volta alle 17:40.
- Ottimizzare contro una sola partita o un solo avversario.
- Entrare in una guerra di prezzo.
- Pagare all'asta più del valore marginale perché "dobbiamo produrre".
- Arrivare alla fine con il magazzino pieno.
- Fare merge non testati su `main` nell'ultima mezz'ora.
- Cambiare 5 parametri insieme e non sapere cosa ha funzionato.

---

## 13. Pitch (solo se previsto)

In 1-2 minuti:
1. La nostra filosofia: robustezza e disciplina sul margine.
2. Come stimiamo domanda e valore delle materie prime.
3. Come ci adattiamo agli avversari.
4. Il finale.
5. I numeri del torneo locale.
