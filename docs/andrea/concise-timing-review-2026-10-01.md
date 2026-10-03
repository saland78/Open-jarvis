# Tempi sul Mac dopo lo stile di sintesi breve — 2026-10-01

## Esito della raccolta

Dopo l'installazione verificata di update_concise.py (installer 722748cec97254f69f778f9b4d51a90be59b9fb4, sorgenti 519b0d085cf302ac38155986a32c5dc4e64a1911), il controllo di qualità sui sei casi immutati è superato e documentato in [concise-quality-review-2026-10-01.md](concise-quality-review-2026-10-01.md).

La raccolta temporale successiva usa lo stesso comando e modello della baseline precedente: tre chat brevissime e tre sintesi con notes-query "kpi self publishing". Tutte le sei richieste sono completate, finishReason stop e nessun troncamento. Le tre ricerche sulle note non sono parziali, con una fonte e inferenza locale model_synthesis. answer e usage restano null: nessun testo privato o estratto è conservato.

## Mediane prima e dopo, tre prove per percorso

| Misura | Prima dello stile breve | Dopo |
|---|---:|---:|
| Ricerca/preparazione delle note | 810,26 ms | 866,36 ms |
| Primo testo client della sintesi | 963,42 ms | 1019,55 ms |
| Totale client della sintesi | 24346,53 ms | 13478,36 ms |
| Primo testo client della chat brevissima | 150,04 ms | 167,90 ms |
| Totale client della chat brevissima | 354,97 ms | 380,01 ms |

La durata totale mediana della sintesi diminuisce del 44,64% nella raccolta osservata. Il primo testo e il recupero non migliorano: circa 1,02 e 0,87 secondi. La chat non è modificata dal nuovo stile; le sue variazioni non vengono attribuite all'intervento.

## Sei misure complete dopo l'aggiornamento

| Percorso/prova | Primo testo client, ms | Totale client, ms | Recupero, ms | Primo testo dal via della generazione, ms | Percorso di generazione, ms |
|---|---:|---:|---:|---:|---:|
| Chat 1 | 1940,95 | 2151,76 | — | 1919,54 | 2131,52 |
| Chat 2 | 167,90 | 380,01 | — | 165,89 | 378,86 |
| Chat 3 | 152,73 | 359,81 | — | 150,76 | 358,81 |
| Note 1 | 7386,89 | 23070,40 | 1093,28 | 6292,02 | 21976,20 |
| Note 2 | 1017,22 | 12622,31 | 857,30 | 158,21 | 11764,21 |
| Note 3 | 1019,55 | 13478,36 | 866,36 | 151,49 | 12611,11 |

La mediana del percorso di generazione sulle note è 12611,11 ms. Nelle seconde e terze richieste il primo testo segue il via della generazione di circa 151–158 ms. La prima chat attende circa 1,94 secondi; la prima sintesi circa 7,39 secondi. Causa e stato freddo/caldo non sono determinati.

## Limiti della conclusione

- È un confronto di tre richieste prima e tre dopo, non una garanzia per ogni domanda o una stima dei percentili di coda. Le condizioni del sistema non sono completamente isolate.
- L'inferenza usa lo stesso modello e parametri; il testo richiesto ha uno stile diverso. I risultati sono coerenti con l'obiettivo di una risposta più breve, ma le risposte di timings sono scartate: non si deducono da questa raccolta lunghezza effettiva, equivalenza semantica o una causa unica del miglioramento.
- I chunk delle sintesi sono 128, 94 e 102; non sono token. Senza usage non si calcolano token al secondo. La qualità dei sei esempi è verificata separatamente; il riassunto delle fonti reali richiede ancora confronto.
- Il client è il Terminale, non il browser; il percorso di generazione include routing e trasporto, non il solo calcolo Ollama.
- Consultato nuovamente tests/telemetry/test_phase_metrics_new.py upstream al commit c4da16e1ca3d21f4cc1905d4200063e564104f0f. Non si dichiara eseguita l'intera suite upstream o misurata energia, caricamento o prefill.
- La baseline prima della modifica è conservata in [search-work-mac-review-2026-10-01.md](search-work-mac-review-2026-10-01.md), senza rimuovere prime richieste più lente.

## Stato

Installazione, sei casi di qualità e confronto dei tempi sono completati. **Resta soltanto il riassunto della medesima nota nell'interfaccia e il confronto con gli estratti reali.** Il criterio di riduzione osservata del tempo totale è rispettato; la verifica complessiva di questa nuova modifica non è ancora conclusa.

Non occorre ripetere questa raccolta invariata. Nessun dato KDP esterno o apprendimento è verificato. Il massimo resta 512 token; modello, dipendenze, dati e Jarvis originale restano invariati. PR draft, senza unione a main. Nessun screenshot, testo delle note o storia del Terminale è pubblicato.
