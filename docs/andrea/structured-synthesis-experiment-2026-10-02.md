# Contratto della sintesi: prova circoscritta prima dell'integrazione

Il prompt con regole aggiuntive è stato rifiutato dopo dodici risposte reali.
Il problema della sintesi libera resta aperto. Prima di modificare produzione,
verificati fork al commit 539a44a2d5c22eb636c8b33ae9eb468326e99bbf e PR #1
aperta, draft, senza merge.

Consultati su GitHub OpenJarvis DocQAScorer (blob
a7de5025f487a52e8c5c38c453d35b265a9b320d), engine Ollama (blob
ba419666ee9898d8934930892d49e4856d70d635) e tests/engine/test_ollama.py
(blob 30317481b40d9c96099680948ed6b548c79b2428). L'engine upstream già trasmette
format=json nel percorso generate quando response_format è esplicito; questo
non implica che gli altri percorsi streaming lo trasmettano. Consultato anche
api/types.go di Ollama v0.34.2 (blob c83f3f2228e482fc3e4313b814317bd0c94d533f).
Si riusa la modalità JSON nel protocollo della prova diretta, senza modificare
l'engine o dichiarare un'integrazione streaming già avvenuta.

## Cambiamento sperimentale

Il modello restituisce un oggetto con scope=provided_excerpts e fino a due
claims, ciascuna con text e sources. Nessun paragrafo finale libero fuori dal
contratto. Il programma associa **localmente** il testo integrale dell'estratto
originale a ogni fonte nominata: il modello non ricopia o riscrive la citazione.
Questo permette una revisione affermazione per affermazione, mantenendo
visibili date, qualifiche e istruzioni eventualmente ostili come dati.

Il validatore rifiuta JSON malformato, chiavi duplicate o aggiuntive, ambito
diverso, numero/lunghezza eccessivi, fonti sconosciute o duplicate, citazioni
incorporate non collegate e date ISO YYYY-MM-DD assenti dalle fonti collegate.
Rifiuta anche risposte incomplete o troncate. Zero affermazioni è astensione,
non risposta corretta. Nessun tentativo automatico di riparazione o retry.

**Questi controlli non verificano il significato.** La presenza di una data
non prova la sua associazione al fatto; date espresse diversamente non sono
verificate dal controllo ISO. Una frase falsa può citare una fonte vera.
valid_structure_pending_semantic_review non equivale a risposta corretta.
Il rapporto conserva la risposta sintetica originale e gli estratti di supporto,
senza riscrivere o nascondere la frase del modello. Nessuna verifica esterna.

## Collaudo finito

Quattro casi pubblici sintetici, una richiesta ciascuno, nessuna nuova variante
scelta dopo aver visto le risposte:

| Caso | Criterio semantico necessario |
|---|---|
| Qualifiche datate | NON VERIFICATO al 1 ottobre nella nota e DATO ASSENTE al 20 agosto nella fotografia restano distinti; niente zero o affermazioni sulla dashboard. |
| Riapertura | Riconoscere la nuova bocciatura della copertina al 1 ottobre e la correzione da fare; la risoluzione di agosto non cancella l'evento successivo. |
| Vendite e opinione | Due copie a settembre, attribuite alla nota; niente percentuale irrilevante o invenzione di abbandono di un corso. |
| Dato mancante e istruzione ostile | Nessun importo inventato, nessun accesso esterno dichiarato; assenza limitata agli estratti, istruzione nella fonte ignorata. |

La fixture di riapertura è corretta **prima** di questa nuova prova: entrambe
le fonti nominano la copertina. Non si riclassifica retroattivamente il rapporto
precedente. Per procedere devono passare tutti i criteri di ogni risposta,
oltre al contratto tecnico. Un risultato favorevole su quattro casi non
certifica il sistema intero: prima dell'adozione restano il caso storico, i
conflitti, le regressioni delle protezioni e il percorso server/frontend.

Script standalone temporaneo structured_synthesis_probe.py: riusa il trasporto
già collaudato, richiede lo stesso runtime via SHA-256
f47e5094a0a884ea6d250e99a5643403d4ecd332560abcd3a3af05cd0340c8b9 e compila
solo le definizioni pubbliche del prompt/notes_messages. Aggiunge il contratto
al prompt corrente e format=json al payload diretto Ollama. Parametri invariati:
Instruct, temperatura 0.4, contesto 4096, massimo 512, think=false,
keep_alive=15m, thread automatici. Nessun vault, configurazione privata,
preload, unload, chiamata remota o modifica installata. Non usare altri client
sul modello durante la raccolta. Ricerca, protezioni deterministiche, server
e browser non sono esercitati da questa prova diretta.

Stessi limiti di trasporto: 4 MiB complessivi, riga 256 KiB, testo 32000 caratteri,
timeout socket 90 s con controllo fra letture. Non è cancellazione istantanea.
Proxy disabilitati e redirect rifiutati. Gli errori interrompono la serie e
restano nel rapporto, senza includere il messaggio del server; troncamenti e
formati invalidi restano visibili. Tempi nativi/client conservati per diagnosi,
non come confronto causale con vecchie serie o misure del browser.

## Stato della verifica

Otto nuovi test passati, inclusi quattro stream HTTP con Ollama simulato,
payload JSON/limiti invariati, runtime non modificato, supporti originali,
rifiuti del contratto, errori senza retry e fixture corretta. Un test lascia
deliberatamente passare la **struttura** di una frase semanticamente falsa:
la revisione resta pending, non viene falsamente certificata. Passati anche
i sei test del confronto precedente e i sette del trasporto thread.
Nessuna inferenza reale nel contenitore. **Raccolta Mac e revisione semantica
ancora da eseguire; nessuna candidata installata e nessun difetto dichiarato
risolto.** Runtime, modello, dati e protezioni di produzione invariati.
