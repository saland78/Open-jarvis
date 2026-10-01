# Estratti preparati dopo la selezione — 2026-10-01

## Problema e modifica

La baseline sul Mac registra circa 1,90 secondi di ricerca/preparazione prima della sintesi. Il codice preparava un estratto per ogni nota trovata, prima di selezionare i dieci risultati restituiti. Questa modifica completa prima ricerca e ordinamento usando contenuto, titolo, percorso e stato; prepara gli estratti soltanto per i dieci risultati restituiti.

Tutte le note accessibili continuano a essere controllate entro gli stessi limiti. Conteggi totali, note escluse, precedenza dei titoli nominati, ordinamento, selezione delle fonti e numeri di riga mantengono le stesse regole. Non viene aggiunta una cache di query o risposte. La cache esistente dei file mantiene i controlli su inode, dimensione, mtime e ctime; le letture sicure, gli stati esclusi e il blocco della sintesi quando la ricerca è parziale restano attivi.

Il limite di scansione resta 10 secondi. Ridurre lavoro durante la scansione può consentire di completare ricerche che prima raggiungevano il limite, ma non si dichiara eliminato ogni limite o ogni possibile ricerca parziale. Il primo testo della sintesi continua a richiedere recupero e generazione.

## Verifiche di sviluppo

Consultati prima della modifica i test upstream tests/memory/test_retrieval_quality.py e tests/connectors/test_obsidian.py: ordinamento, limite dei risultati, conservazione delle fonti, nessuna corrispondenza, file Markdown e frontmatter. La modifica usa il parser già integrato; non attiva un database, un modello di embedding o l'ingestione upstream.

Il nuovo controllo sul lavoro eseguito riproduce prima della modifica 81 preparazioni di estratti invece delle dieci necessarie. Dopo la modifica passa, con conteggio di 81 corrispondenze, 20 note escluse e nota nominata al primo posto. Sono controllati anche assenza di risultati, forma pubblica degli estratti, aggiornamento delle righe e cambio di stato della fonte nominata.

Passano 53 controlli mirati: 24 sull'adattatore e recupero, 12 su evidenze/ASGI, 8 sulle misure, 3 sul client, 6 sulla transazione esistente. Il parser scalar upstream è eseguito in isolamento nella checkout parziale. Non sono eseguiti l'intera suite upstream, il backend Rust completo, Ollama o un nuovo collaudo sul Mac. La sintassi Python è verificata.

## Confronto su corpus sintetico

Confronto con vault.py al commit e75246e01d053cf1dd05dc7ecb9a1abac31fb470, SHA-256 45824df7d3427a1632ccd6ea00562f855bf298e188672bc738bb0ff337989161. Nel contenitore di sviluppo, un corpus di 364 file Markdown UTF-8 contiene 363 trascrizioni sintetiche, una nota catalogo nominata e 14 stati superseded, per 3.019.818 byte complessivi. Ogni trascrizione include una riga lunga ottenuta ripetendo 160 volte una frase sintetica. Non contiene note personali.

Sei ricerche esercitano domanda con titolo nominato, titolo esatto, termine generico, royalty, una trascrizione nominata e termine senza corrispondenza. Prima e dopo, tutti i campi pubblici dei risultati coincidono, escluso elapsedMs. Per le tre misure seguenti le cache dei file sono già popolate; si alternano vecchia e nuova versione sullo stesso corpus. Non si misura Ollama.

| Prova | Versione precedente, ms | Nuova versione, ms | Estratti prima/dopo |
|---|---:|---:|---:|
| 1 | 472,34 | 245,63 | 364 / 10 |
| 2 | 474,24 | 247,28 | 364 / 10 |
| 3 | 498,64 | 237,76 | 364 / 10 |
| Mediana | 474,24 | 245,63 | 364 / 10 |

In tutte le prove: 364 note controllate, 364 corrispondenze, 14 escluse, ricerca completa. Sono dati di un corpus sintetico in un ambiente diverso dal Mac: non prevedono un'accelerazione specifica sulle note reali, non misurano la prima scansione e non rappresentano il tempo totale delle risposte. La generazione della sintesi, che domina il totale nella baseline Mac, non è modificata in questo intervento.

## Aggiornamento e stato

scripts/andrea/update_search_work.py applica soltanto vault.py, i tre nuovi controlli e questo documento da un commit fissato. Verifica hash e baseline della versione installata, rifiuta modifiche incompatibili, richiede porta 8008 libera e conserva backup e rollback. Nessuna modifica a frontend, prompt, modello, budget, dipendenze, configurazioni, database o note. Suggested budget resta una proposta; il massimo del profilo resta 512 token.

La modifica è preparata e collaudata in sviluppo. Installazione e beneficio sul Mac restano da verificare. Il collaudo Obsidian precedente rimane documentato separatamente e non viene ripetuto per cercare una risposta favorevole. Dopo l'installazione è sufficiente una raccolta confrontabile dei tempi e il controllo delle fonti restituite per la stessa ricerca.

PR draft, senza unione a main. Jarvis originale sulla porta 7778 resta separato. Questa modifica non addestra il modello, non verifica dati KDP e non implementa la pipeline vocale.
