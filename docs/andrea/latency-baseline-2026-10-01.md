# Baseline del percorso testuale locale — 2026-10-01

## Condizioni e risultato

Raccolta eseguita sul Mac tramite collaudo.py timings, con tre richieste di chat brevissima e tre sintesi sulla stessa nota KPI. Modello osservato: qwen3:4b-instruct-2507-q4_K_M. È installata la correzione dei titoli nominati (sorgenti e540a871c2f42d0a8d3a47e573fd18e9dd96eb47, aggiornamento fbc7dd36ca4fdcf0697398935c84135edeead23f). Nessuna modifica a modello, configurazione o dati per questa raccolta.

Tutte le sei richieste hanno stream completo, finishReason stop e stato completed. Le tre ricerche sulle note non sono parziali, usano una fonte e generano una sintesi con il modello. Il client non conserva le risposte o gli estratti: answer è null. Nessuna nuova valutazione semantica è ricavabile da queste risposte scartate; i verdetti di accuratezza sono quelli del collaudo separato.

## Misure delle sei prove

| Percorso / prova | Primo testo client, ms | Totale client, ms | Ricerca/preparazione, ms | Primo testo dal via del percorso di generazione, ms | Durata percorso di generazione, ms |
|---|---:|---:|---:|---:|---:|
| Chat 1 | 7357,97 | 7579,20 | — | 7340,43 | 7562,67 |
| Chat 2 | 150,91 | 364,20 | — | 148,88 | 363,03 |
| Chat 3 | 154,43 | 387,31 | — | 152,76 | 386,91 |
| Note 1 | 14072,19 | 38254,03 | 1982,42 | 12087,81 | 36270,51 |
| Note 2 | 2046,98 | 25785,20 | 1895,92 | 149,36 | 23888,36 |
| Note 3 | 2028,90 | 19352,31 | 1880,44 | 146,72 | 17470,86 |

| Mediana su tre prove | Primo testo client | Totale client |
|---|---:|---:|
| Chat brevissima | 154,43 ms | 387,31 ms |
| Sintesi sulla nota | 2046,98 ms | 25785,20 ms |

La ricerca/preparazione delle fonti ha mediana 1895,92 ms. Nella prova centrale delle note, il percorso di generazione occupa 23888,36 ms. Nelle seconde e terze richieste sulle note, il primo testo arriva circa 147–149 ms dopo l'avvio di quel percorso: l'attesa totale iniziale comprende soprattutto i circa 1,9 secondi di recupero.

## Interpretazione e limiti

- La chat richiesta emette soltanto una risposta brevissima; la sintesi sulle note svolge un lavoro diverso. Le mediane non misurano una velocità generale del sistema e non sono un confronto controllato della sola ricerca.
- Le prime richieste di chat e note hanno attese maggiori. Caricamento, prefill, cache o contesa non sono misurati separatamente in questi dati; non vengono diagnosticati dal solo primo testo. Stato freddo/caldo non determinato.
- I tempi client sono misurati dal Terminale, non dal browser. Le misure server registrano il passaggio ad ASGI. La durata del percorso di generazione include routing e trasporto: non è il tempo puro di Ollama.
- usage è null. I 2 chunk della chat e i 195/197/146 chunk delle note non vengono trattati come token; non vengono calcolati token al secondo, throughput o energia.
- Tre prove per percorso non sostengono percentili di coda o garanzie di prestazione. Nessun risultato è stato rimosso come presunto avvio freddo.
- Non è misurata una pipeline vocale: acquisizione audio, speech-to-text, text-to-speech e riproduzione restano funzioni future.

Consultati nuovamente i test upstream tests/telemetry/test_phase_metrics_new.py, riferimento c4da16e1ca3d21f4cc1905d4200063e564104f0f. Le fasi di primo testo e durata restano distinte; non si attiva la telemetria energetica o si attribuisce al prefill una durata non misurata. Il file upstream è consultato, non si dichiara eseguita qui la sua suite completa.

## Stato della fase e direzione successiva

Il collaudo finito previsto per il collegamento Obsidian è concluso: avvio e collegamento, ricerca e lettura già confermate, sei casi sintetici revisionati, precedenza della nota nominata e risposta citata verificati sul vault reale, baseline temporale raccolta. Sono esiti dei percorsi controllati, non una certificazione di ogni nota o sintesi libera. Non è stato verificato alcun report KDP reale e nessuna memoria salvata costituisce apprendimento.

La fase successiva riguarda qualità e latenza dell'intero percorso testuale. Questi dati indicano due punti concreti da progettare: contenuto/lunghezza e contesto della sintesi, che occupa gran parte del totale, e recupero delle fonti, che incide sull'attesa iniziale. Le modifiche dovranno mantenere citazioni, rilevamento dei conflitti, rifiuto dei dati non verificati come zero, invalidazione delle fonti cambiate e stati di troncamento comprensibili. Non è ancora stata applicata un'ottimizzazione a seguito di queste misure.

Il modello attuale e il progetto Jarvis originale restano invariati. La PR è draft e non viene unita a main. Nessun testo personale delle note, screenshot o contenuto di risposta è incluso in questa baseline.
