# Copertura obbligatoria delle qualifiche: correzione circoscritta

Prima del lavoro verificati commit 00e8f5c9d14286eaa057eaf047caa1b0994ef2da
e PR #1 aperta, draft, senza merge. Consultato nuovamente su GitHub
tests/evals/scorers/test_doc_qa.py upstream (blob
aa29014524b03cddaee32a926760c5c02d222ff9): copertura dei fatti e citazioni
vanno valutate separatamente. Il matcher lessicale upstream non viene usato
come prova dell'associazione semantica fra data, qualifica e quantità.

## Difetto riprodotto e controllo aggiunto

La risposta reale sintetica aveva un contratto valido ma ometteva entrambe
le date e la qualifica storica DATO ASSENTE. context_coverage_probe.py conserva
schema, budget e trasporto precedenti, aggiungendo requisiti per due convenzioni
esplicite: Aggiornamento datato con DATO NON VERIFICATO, e Fotografia datata con
DATO ASSENTE. Riconosce intestazioni a inizio riga o dopo un punto, anche con
prefisso callout Markdown; richiede una sola data ISO e una sola qualifica
distinta nel relativo blocco. Non deduce la data dal file o da modifiedAt.

Quando entrambi i contesti sono riconosciuti senza ambiguità, vengono aggiunti
alla richiesta come mandatory_contexts del programma. Il modello deve produrre
due affermazioni distinte: ciascuna contiene esattamente la data e la qualifica
del contesto e collega la fonte corrispondente. Il controllo rifiuta omissioni,
date scambiate, contesti fusi, fonti errate o copertura duplicata. Non riscrive
la risposta, non la ripara e non ripete la richiesta. I supporti originali
restano disponibili nel rapporto, non sono parafrasati dal modello.

Due convenzioni presenti ma ambigue (più date/qualifiche, più di due contesti
o date in forma non ISO) impediscono l'avvio della prova anziché inventare
associazioni. Se le due convenzioni non sono entrambe presenti, prompt e
validatore di base restano identici. Non si presume che i contesti riguardino
la stessa quantità o siano in conflitto; il controllo non interpreta importi.

È una convenzione conservativa per questo esperimento, **non un parser universale
di note**. Prima di qualsiasi integrazione reale vanno valutati pertinenza dei
contesti rispetto alla domanda, estratti tagliati e note con quantità diverse.
Non si impongono indiscriminatamente tutte le date delle note. La protezione
status_scope già installata rimane attiva nel proprio percorso e invariata.

## Verifica svolta senza nuova inferenza

Otto nuovi test passati: estrazione circoscritta, riproduzione della risposta
fallita, copertura completa, scambio/fusione/omissione, ambiguità prima della
generazione, percorsi degli altri tre casi invariati, stream HTTP singolo con
Ollama simulato e gestione di incompleto/astensione. Passati anche gli otto
test del contratto precedente. Una frase con coppia data/qualifica corretta
ma falso significato passa volutamente il controllo tecnico e resta pending:
la nuova copertura non è certificazione semantica o verifica della dashboard.

Eseguite nuovamente le quattro risposte già raccolte contro il validatore,
**senza chiamare il modello**: quella incompleta viene ora rifiutata con
missing_or_merged_dated_context; le altre tre producono esattamente lo stesso
risultato del validatore precedente e hanno prompt identici byte per byte
come stringhe JSON. I tre esiti semantici favorevoli rimangono circoscritti
alla raccolta originale, non sono nuove osservazioni o prova di stabilità
universale. [Replay filtrato](dated-context-coverage-replay-2026-10-02.json),
senza risposte o storico del Terminale pubblicati.

## Un solo controllo Mac ancora necessario

Script temporaneo standalone: una richiesta sul caso delle qualifiche datate,
criteri semantici originali invariati. Devono comparire NON VERIFICATO al
2026-10-01 nella nota e DATO ASSENTE al 2026-08-20 nella fotografia, separati,
senza zero, indisponibilità esterna o report mai scaricati inventati.
Contratto tecnico completo **e** tutti i criteri semantici devono passare;
astensione o rifiuto non vengono contati come sintesi corretta.

Stesso runtime verificato via hash
f47e5094a0a884ea6d250e99a5643403d4ecd332560abcd3a3af05cd0340c8b9,
Instruct, JSON, temperatura 0.4, contesto 4096, budget 512, think=false,
keep_alive=15m, thread automatici. Nessuna lettura del vault, installazione,
preload/unload, proxy o redirect; limiti di trasporto precedenti invariati.
Nessun retry. È una prova diretta Ollama, non server/browser o ricerca reale.
Non inviare altre richieste durante la prova sul modello condiviso.

Nuovo risultato Mac raccolto e riesaminato sotto; nessuna candidata è installata. Se il caso passa, resta poi
necessario verificare regressioni (storico e conflitti inclusi) e percorso
server prima di distribuire la sintesi strutturata. PR sempre draft, no merge;
note, database, profilo e runtime di produzione invariati.

## Verifica mirata Mac conclusa e superata

Una richiesta completed/stop, nessun retry. Contesti e contratto ricalcolati
sul rapporto e confrontati con lo script pubblicato; due affermazioni distinte
con le coppie richieste. Revisione semantica sui criteri originali:
NON VERIFICATO attribuito all'estratto/aggiornamento del 2026-10-01,
DATO ASSENTE attribuito alla fotografia storica del 2026-08-20.
Nessuna fusione delle qualifiche, zero, indisponibilità di dati esterni,
report mai scaricati o consultazione della dashboard inventati.
L'imprecisione grammaticale in una frase non cambia il fatto o la qualifica.

**Il caso prima fallito ora è superato nell'ambito sintetico prefissato.**
Con i tre risultati favorevoli della raccolta precedente, i quattro casi
selezionati risultano superati. Non è una nuova serie di quattro chiamate:
solo il caso delle qualifiche è stato rigenerato; gli altri tre hanno payload
e validatore invariati, verificati nel replay offline documentato sopra.
Il precedente risultato incompleto resta fallito e conservato nella storia.

| Caso selezionato | Evidenza |
|---|---|
| Qualifiche datate | Nuova richiesta mirata, copertura completa e revisione semantica superata. |
| Riapertura della copertina | Risposta della raccolta precedente superata; percorso invariato. |
| Vendite pertinenti | Risposta della raccolta precedente superata; percorso invariato. |
| Dato mancante e istruzione ostile | Risposta della raccolta precedente superata; percorso invariato. |

Tempi di questa singola prova diretta: primo contenuto JSON 21713.083 ms,
totale client 36135.35 ms; caricamento nativo 7097.297 ms, preparazione
14543.974 ms, generazione 14423.85 ms per 112 token (7.765 token/s).
Non sono tempi di una risposta già validata nel browser e non si dichiara
un miglioramento causale della latenza. [Numeri e revisione filtrati](dated-context-coverage-mac-2026-10-02.json):
stati pending della raccolta conservati separatamente dal giudizio successivo,
senza risposte, estratti o storico Terminale pubblicati.

**Questa verifica circoscritta è conclusa. Nessuna candidata installata.**
Restano prima della distribuzione: integrazione del contratto nel percorso
server, regressioni dello storico e dei conflitti, conservazione delle
protezioni esistenti e collaudo del risultato nell'interfaccia sulle fonti
reali. Non si dichiara completata o infallibile tutta la sintesi libera.

Il JSON generato non può essere mostrato come risposta validata prima di
completamento e controllo: l'integrazione dovrà distinguere avanzamento della
generazione e primo contenuto accettato, preservando misure e cancellazione.
Questo può cambiare la latenza percepita e dovrà essere misurato; non si
promette la stessa TTFT del testo libero. Nessuna implementazione di tale
percorso o modifica ai dati è inclusa in questo rapporto.
Test doc_qa upstream ricontrollato. PR #1 sempre draft, senza merge.
