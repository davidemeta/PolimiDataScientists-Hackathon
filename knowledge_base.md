# Knowledge Base: economia per ingegneri informatici

I concetti minimi per capire il gioco, con esempi numerici e formule da tradurre in codice. Da leggere in circa 30-40 minuti.

---

## 1. Il modello di business del gioco

Ogni turno la vostra azienda fa quattro cose:

```
  ASTA (compri materie prime)  →  PRODUZIONE (materie prime → prodotto)  →  VENDITA (fissi il prezzo)  →  PROFITTO
```

**Profitto = Ricavi − Costi**
- **Ricavi** = prezzo × quantità venduta
- **Costi** = materie prime pagate all'asta + costo di produzione + costi di magazzino + eventuali costi fissi

Le tre decisioni sono collegate tra loro:
- il prezzo di vendita determina quanto vale una materia prima;
- quanto vale una materia prima determina quanto offrite all'asta;
- quante materie prime vincete determina quanto potete produrre e vendere.

---

## 2. Materie prime e "ricetta" (Bill of Materials)

Un prodotto richiede una certa quantità di materie prime. Questa ricetta si chiama BOM (*Bill of Materials*).

Esempio: **1 Prodotto = 2 unità di A + 1 unità di B + 10€ di lavorazione**.

Le materie prime si comprano all'asta e i prezzi cambiano ogni turno. Se manca anche solo un ingrediente non potete produrre. Per questo si dice che le materie prime sono *complementari*: vincere A senza B è inutile.

---

## 3. Tipi di costo

| Concetto | Definizione | Perché conta |
|---|---|---|
| **Costo variabile** | Cresce con la quantità prodotta (materie prime, lavorazione). | Determina il prezzo minimo sensato. |
| **Costo fisso** | Si paga comunque (affitto, costo per turno). | Non dipende da quanto producete, quindi **non** deve influenzare le decisioni di breve periodo. |
| **Costo marginale (MC)** | Il costo di produrre **una unità in più**. | Regola chiave: conviene produrre o vendere un'unità solo se il ricavo supera il costo marginale. |
| **Costo medio** | Costo totale diviso per le unità. | Utile per capire se nel complesso si è in profitto. |
| **Sunk cost (costo affondato)** | Un costo già sostenuto e non recuperabile. | **Va ignorato** nelle decisioni future. |

**Esempio di sunk cost (fondamentale per il finale):** avete 50 prodotti in magazzino che vi sono costati 30€ l'uno, e mancano 2 turni alla fine. Se a fine partita valgono zero, venderli a 15€ **conviene**, perché 15€ è meglio di 0€. Il fatto che vi siano costati 30€ è irrilevante: quei soldi sono già spesi.

---

## 4. La funzione di domanda (il concetto più importante)

La **funzione di domanda** dice **quante unità vendete a un certo prezzo**. Più alto il prezzo, meno vendete.

### Domanda lineare (la più comune nei simulatori)
```
q(p) = a − b·p
```
- `a` è la domanda massima, quella che avreste a prezzo 0.
- `b` dice quante vendite perdete per ogni euro in più di prezzo.

**Esempio:** con `q = 100 − 2p` vendete 80 unità a 10€, 40 unità a 30€ e 0 unità a 50€.

### Prezzo che massimizza il profitto (monopolio, domanda lineare)
Il profitto è `π(p) = (p − c) · (a − b·p)`, dove `c` è il costo marginale unitario. Ponendo la derivata uguale a zero si ottiene:

```
p* = (a/b + c) / 2
```

**Esempio:** con `a = 100`, `b = 2` e `c = 10`, il prezzo ottimo è `p* = (50 + 10)/2 = 30`. Il confronto con i prezzi vicini conferma che 30 è il massimo:

| Prezzo | Quantità | Profitto unitario | Profitto |
|---|---|---|---|
| 25 | 50 | 15 | 750 |
| **30** | **40** | **20** | **800** ← massimo |
| 35 | 30 | 25 | 750 |

Nota che il prezzo ottimo **non** è "il più alto possibile" né "il più basso per vendere tutto": sta nel mezzo.

```python
def optimal_price_linear(a, b, c):
    return (a / b + c) / 2
```

### Altre forme possibili nel codice
- **Esponenziale o logit:** `q = A · exp(−k·p)`. Il prezzo ottimo è `p* = c + 1/k`.
- **Logit con concorrenti** (molto comune): la vostra quota di mercato vale
  ```
  quota_i = exp(−k·p_i) / Σ_j exp(−k·p_j)
  ```
  Chi ha il prezzo più basso prende più clienti, ma non tutti. Il vostro prezzo ottimo dipende quindi dai prezzi degli altri.
- **Winner-takes-all:** il più economico prende tutta la domanda, fino a esaurire le scorte, poi tocca al secondo, e così via.

> **Se trovate la funzione di domanda nel codice del simulatore, avete un vantaggio enorme:** potete calcolare il prezzo ottimo invece di indovinarlo.

### Stimare la domanda se non è nota
Raccogliete coppie `(prezzo, quantità venduta)` turno per turno e fate una regressione lineare. La pendenza stimata è `−b` e l'intercetta è `a`:
```python
import numpy as np
slope, intercept = np.polyfit(prices, quantities, 1)   # q ≈ intercept + slope·p
a, b = intercept, -slope
```
Servono prezzi **diversi** tra loro per stimare bene. Per questo nei primi turni conviene variare il prezzo (vedi §9).

---

## 5. Elasticità della domanda

L'**elasticità** misura quanto sono sensibili i clienti al prezzo:
```
ε = (variazione % della quantità) / (variazione % del prezzo) = (dq/dp) · (p/q)
```
- Se `|ε| > 1` la domanda è **elastica**: se alzate il prezzo perdete molti clienti, e il ricavo scende.
- Se `|ε| < 1` la domanda è **anelastica**: se alzate il prezzo perdete pochi clienti, e il ricavo sale.

**Regola del markup ottimo** (vale per qualsiasi forma di domanda):
```
(p − c) / p = 1 / |ε|
```
Più i clienti sono sensibili al prezzo, più basso deve essere il margine.

**Esempio:** con `q = 100 − 2p` e `p = 30` si ha `ε = −2 · 30/40 = −1.5`. Il markup ottimo è quindi `1/1.5 = 66.7%`, e infatti `(30 − 10)/30 = 66.7%` ✓.

**In pratica:** se c'è molta concorrenza con prodotti identici, la domanda è molto elastica, quindi margini bassi. Se la concorrenza è poca, si può tenere un margine alto.

---

## 6. Gestione delle scorte

### Costo di magazzino (holding cost)
Tenere prodotti invenduti spesso costa (`h` € per unità per turno), e a fine partita possono valere zero. Più scorte = più rischio.

### Problema del newsvendor (quanto produrre con domanda incerta)
Avete due possibili errori:
- produrre **troppo** costa `Co` per ogni unità invenduta (costo meno valore di recupero);
- produrre **troppo poco** costa `Cu` per ogni vendita persa (cioè il margine `p − c`).

La quantità ottima da produrre è il quantile della domanda pari al **rapporto critico**:
```
rapporto critico = Cu / (Cu + Co)
```
**Esempio:** con `p = 30`, `c = 10` e valore di recupero 0, si ha `Cu = 20` e `Co = 10`. Il rapporto critico è `20/30 = 0.67`, quindi conviene produrre la quantità che copre la domanda nel 67% dei casi.

**Regola semplice:** margine alto → producete un po' di più; margine basso o scorte che si deprezzano → producete un po' di meno.

---

## 7. Concorrenza: teoria dei giochi in pillole

Nel gioco tutti agiscono **simultaneamente**, quindi non sapete cosa faranno gli altri in questo turno, ma vedete cosa hanno fatto in quelli precedenti.

### Equilibrio di Nash
È una situazione in cui nessun giocatore ha interesse a cambiare strategia, dato quello che fanno gli altri.

### Concorrenza di Bertrand (sui prezzi)
Se i prodotti sono identici e i clienti comprano dal più economico, ognuno ha interesse ad abbassare il prezzo di un centesimo sotto l'altro. Alla fine **tutti vendono al costo e il profitto è zero**. È la "guerra dei prezzi": da evitare.

### Concorrenza di Cournot (sulle quantità)
Se si compete su quanto produrre, i prezzi restano sopra il costo. Più concorrenti ci sono, più il prezzo si avvicina al costo.

### Gioco ripetuto e collusione tacita
Il gioco dura molti turni, quindi conviene **cooperare implicitamente** tenendo prezzi alti:
- **Tit-for-tat:** si parte cooperativi, prezzo alto. Se qualcuno abbassa, si risponde abbassando per un turno, poi si torna a cooperare.
- Funziona perché la minaccia di ritorsione scoraggia gli altri dal tagliare i prezzi.
- **Attenzione al finale:** quando la partita sta per finire, la minaccia di ritorsione non vale più e tutti tendono a tagliare. Tenetene conto negli ultimi turni.

### Dilemma del prigioniero
Se tutti tengono prezzi alti, tutti guadagnano bene. Se uno taglia, guadagna molto lui e gli altri perdono. Se tutti tagliano, tutti guadagnano poco. La guerra di prezzi è il caso "tutti tagliano".

---

## 8. Le aste

### Terminologia
- **Valore privato (`v`):** quanto vale per voi l'oggetto. Qui è il valore marginale della materia prima (vedi sotto).
- **Offerta (`bid`):** quanto dichiarate di essere disposti a pagare.
- **Prezzo di riserva:** il prezzo minimo sotto cui il venditore non vende.
- **Busta chiusa:** ognuno offre senza vedere le offerte degli altri.

### Quanto vale per voi una materia prima
È il massimo che potete pagare senza andare in perdita:
```
valore_max(A) = (prezzo_vendita_atteso − costo_lavorazione − costo_altri_materiali) / unità_di_A_per_prodotto
```
**Esempio:** il prodotto si vende a 50€, la lavorazione costa 10€, B costa 10€ e la ricetta richiede 2 unità di A. Allora `valore_max(A) = (50 − 10 − 10)/2 = 15€`. **Sopra 15€ per unità di A, ogni prodotto vi fa perdere soldi.**

### Tipi di asta

| Tipo | Come funziona | Strategia ottima |
|---|---|---|
| **Primo prezzo, busta chiusa** | Vince chi offre di più e paga **la propria offerta**. | **Offrite meno del vostro valore** (*bid shading*). Se offrite esattamente `v` il guadagno è zero anche quando vincete. |
| **Secondo prezzo, busta chiusa (Vickrey)** | Vince chi offre di più ma paga **la seconda offerta più alta**. | **Offrite esattamente il vostro valore `v`.** È una strategia dominante: non potete fare di meglio. |
| **Inglese (ascendente)** | Il prezzo sale finché ne resta uno. | Restate fino al vostro valore, poi uscite. È equivalente al secondo prezzo. |
| **Olandese (discendente)** | Il prezzo scende e vince il primo che accetta. | Equivalente al primo prezzo. |
| **Multi-unità, prezzo uniforme** | Più unità in palio, tutti i vincitori pagano lo stesso prezzo, quello di equilibrio. | Simile al secondo prezzo: offrite vicino al valore. |
| **Multi-unità, pay-as-bid** | Ogni vincitore paga la propria offerta. | Come il primo prezzo: offrite meno del valore. |

### Bid shading: di quanto stare sotto (primo prezzo)
Con `n` partecipanti simmetrici, il risultato teorico è:
```
bid ≈ v · (n − 1) / n
```
- Con 2 concorrenti si offre circa il 50% del valore, con 5 circa l'80%, con 10 circa il 90%.
- **Più concorrenti ci sono, più si deve offrire vicino al valore.**

In pratica conviene adattare l'offerta guardando il **prezzo di aggiudicazione dei turni precedenti**:
```python
bid = min(valore_max, ema_prezzo_aggiudicazione * 1.02)   # poco sopra il prezzo tipico, mai oltre il valore
```

### Maledizione del vincitore (winner's curse)
Se vincete sempre, probabilmente state offrendo troppo. Chi vince un'asta è spesso chi ha sovrastimato di più il valore dell'oggetto. Controllate sempre: **vincere costa?**

---

## 9. Esplorazione e sfruttamento (bandit)

Quando non conoscete la domanda, c'è un compromesso:
- **Esplorare** vuol dire provare prezzi diversi per imparare la curva di domanda;
- **Sfruttare** vuol dire usare il prezzo che finora ha reso di più.

### ε-greedy (il più semplice)
Con probabilità ε (per esempio 10%) provate un prezzo diverso; altrimenti usate il migliore trovato finora. Riducete ε man mano che passano i turni.

### Thompson Sampling / UCB
Sono varianti più intelligenti: provano più spesso le opzioni incerte ma promettenti.

**In un gioco di poche decine di turni:** esplorate solo nei primi 3-5 turni, con 2-3 prezzi diversi, poi stimate la domanda con la regressione (§4) e sfruttate.

---

## 10. Stimatori semplici (quelli che userete davvero)

### Media mobile esponenziale (EMA)
```python
ema = alpha * nuovo_valore + (1 - alpha) * ema     # alpha tra 0.2 e 0.4
```
- Un `alpha` alto reagisce in fretta ma è rumoroso.
- Un `alpha` basso è più stabile ma lento.

Usatela per i prezzi dei concorrenti, il prezzo di aggiudicazione delle aste e le vendite per turno.

### Regressione lineare
Serve per stimare la funzione di domanda (§4) o il trend dei prezzi.

### Perché bastano
Con poche decine di osservazioni, modelli complessi (reti neurali, TimesFM) non hanno abbastanza dati per fare meglio. In più il mercato cambia perché gli avversari si adattano, quindi conta di più reagire rapidamente che prevedere con precisione.

---

## 11. Glossario rapido

| Termine | Significato |
|---|---|
| **Margine / markup** | (prezzo − costo) / costo, oppure / prezzo. Specificate sempre quale. |
| **Ricavo marginale (MR)** | Ricavo in più vendendo un'unità in più. Il profitto massimo si ha quando MR = MC. |
| **Quota di mercato** | Le vostre vendite divise per le vendite totali del mercato. |
| **Liquidità / cassa** | I soldi disponibili ora. Finirli può significare bancarotta. |
| **Prezzo di aggiudicazione** | Il prezzo a cui si chiude un'asta. |
| **Valore di recupero (salvage)** | Quanto vale un'unità invenduta a fine partita, spesso 0. |
| **Strategia dominante** | Una strategia che è la migliore qualunque cosa facciano gli altri. |
| **Oligopolio** | Mercato con pochi venditori che si influenzano a vicenda, cioè esattamente il vostro gioco. |

---

## 12. Riassunto in 6 righe

1. **Prezzo:** c'è un ottimo nel mezzo, `p* = (a/b + c)/2` con domanda lineare. Margine basso se i clienti sono sensibili al prezzo.
2. **Asta:** prima calcolate il valore massimo della materia prima. Al secondo prezzo offrite quel valore, al primo prezzo offrite meno.
3. **Produzione:** producete quanto vendete. Se il margine è alto sbagliate per eccesso, se è basso per difetto.
4. **Concorrenza:** evitate la guerra di prezzi (Bertrand). Cooperate tacitamente e punite brevemente chi taglia.
5. **Finale:** i costi già sostenuti non contano. Liquidate tutto a qualsiasi prezzo sopra il valore di recupero.
6. **Stima:** EMA e regressione lineare. Esplorate poco all'inizio, poi sfruttate.
