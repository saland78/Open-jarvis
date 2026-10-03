# Baseline sintetica finita della latenza

## Scopo e confini

Dopo il collaudo funzionale delle misure browser nelle note e nella chat, raccogliere nove richieste di risposta comparabili sul Mac: tre chat generate, tre sintesi di estratti sintetici e tre risposte dirette a campi espliciti. Nessun modello, prompt, budget o runtime modificato per questa raccolta. La baseline non dichiara un miglioramento di velocità o la correttezza semantica delle risposte.

`scripts/andrea/baseline.py` può essere scaricato ed eseguito temporaneamente con il Python del progetto mentre OpenJarvis resta acceso sulla porta 8008. Non richiede installazione, dipendenze nuove, riavvio o sostituzione dei file del progetto. Verifica l'hash di `collaudo.py` prima di importarne il client HTTP già presente. Un client diverso causa arresto prima dell'invio delle richieste. Stato GitHub e PR draft verificati prima dello sviluppo.

Ordine fisso: chat, sintesi di estratti, risposta diretta; ripetuto tre volte. Nessun warm-up, retry automatico o scaricamento del modello dalla memoria. `firstInBatch` identifica soltanto la prima richiesta della serie, non uno stato freddo del modello. Stato caldo/freddo e carico di altri processi non sono determinati. Nessuna riconfigurazione globale di Ollama condiviso.

Le due richieste sulle note forniscono sempre `notes_sources` sintetici: non leggono il vault. Le fixture di sintesi storica e conteggio diretto riprendono i casi già pubblicati della suite quality. La ricerca nei contenuti del vault non viene misurata da questo recupero di estratti forniti; le osservazioni delle note reali restano un insieme distinto.

## Dati e criteri

Le durate principali sono invio → primo contenuto ricevuto dal client di controllo e invio → conclusione del trasporto. Il client non è il browser e non misura DOM o paint. I tempi backend correlati vengono riportati separatamente e non sommati alle durate del client. La lettura delle misure backend non genera una seconda risposta.

Il rapporto conserva ordinale, percorso, ripetizione, durate, stato, fine dello stream, modo della risposta e contatori token se presenti. Testi, fonti, percorsi personali, identificativi delle richieste e messaggi delle eccezioni non entrano nel rapporto. Le conversazioni esistenti, note, profili, configurazioni e database non vengono modificati. Lo script stampa il rapporto senza salvarlo automaticamente.

Errori, stream incompleti, troncamenti e percorsi diversi da quello atteso restano nelle nove posizioni originali. Le mediane includono solo richieste con DONE, stop, stato backend completed, primo testo misurato e percorso atteso: generazione effettivamente registrata nella chat; model_synthesis con inferenceUsed true nella sintesi; explicit_fields con inferenceUsed false e generazione nulla nella risposta diretta. Mostrare sempre i conteggi inclusi/esclusi. Un errore non diventa una misura pari a zero. Nessun percentile affidabile dichiarato con tre campioni per percorso.

`qualityVerdict` rimane `not_assessed`: lo scarto del testo nel test prestazionale impedisce una revisione semantica della risposta. Le verifiche quality e i precedenti esiti reali rimangono separati; una misura valida del trasporto non certifica che la risposta sia corretta. La baseline è il riferimento per una futura modifica isolata, con criteri di qualità invariati e ripristino disponibile.

## Verifica di sviluppo

- Sei nuovi test passati: numero e ordine delle richieste, fixture e instradamento diretto/generativo, esclusione dei contenuti privati, conservazione degli errori senza retry, stati/percorso errati esclusi dalle mediane, rifiuto del client non verificato prima dell'importazione.
- Quattro test precedenti del client di collaudo passati: SSE, fonti separate dal contenuto, modalità di qualità/breve e necessità di revisione.
- Nove richieste HTTP locali sul `LocalMode` effettivo con motore simulato: nove risultati completati sul percorso atteso, sei chiamate al modello simulato e tre risposte dirette senza inferenza. Adattatore senza vault configurato; nessuna nota letta. Questa prova verifica protocollo e instradamento, non tempi reali Ollama o qualità semantica.
- Consultato nuovamente `tests/server/test_stream_bridge.py` upstream al commit `1a9c8cf70fbc24872ba2327115040d4c7a99a11a`, che conserva risposte già prodotte senza una seconda inferenza. Suite upstream completa non eseguita.

Nessun file runtime/frontend modificato: non occorre una nuova build dell'interfaccia per questa raccolta. PR sempre draft senza merge, Jarvis originale intatto.

## Raccolta Mac conclusa

Script scaricato dal commit `26928d7cfad986a00ea2355851f06f5bc2c7a48e`, SHA-256 verificato `d017414bf247fa5cdf4241486a081cd3b19c8429868cf4647ea134003166f1e9`, ed eseguito il 2026-10-02 con il Python del progetto nella finestra Controlli. OpenJarvis è rimasto acceso. Serie conclusa una volta: nove richieste, tutte con DONE, stop, stato backend completed e percorso atteso; nessuna esclusione o retry. L'output ricevuto conteneva anche uno storico del Terminale: è stato estratto esclusivamente il rapporto finale della baseline, senza pubblicare lo storico o dati personali.

### Singole osservazioni

Le durate sono in millisecondi. Primo testo e totale sono misure del client di controllo, non del rendering nel browser. I valori backend sono correlati e hanno un orologio distinto.

| Ordinale | Percorso | Primo testo client | Totale client | Primo testo ASGI | Totale backend |
|---|---|---:|---:|---:|---:|
| 1 | Chat | 7003,32 | 7207,70 | 6984,14 | 7189,41 |
| 2 | Sintesi di estratto fornito | 7952,64 | 17995,86 | 7951,13 | 17995,36 |
| 3 | Campo esplicito diretto | 4,05 | 4,20 | 2,59 | 2,92 |
| 4 | Chat | 206,82 | 410,83 | 205,25 | 410,10 |
| 5 | Sintesi di estratto fornito | 177,11 | 10061,74 | 175,49 | 10060,98 |
| 6 | Campo esplicito diretto | 1,98 | 2,06 | 0,45 | 0,68 |
| 7 | Chat | 163,59 | 368,05 | 162,12 | 367,52 |
| 8 | Sintesi di estratto fornito | 175,98 | 10010,23 | 174,29 | 10009,42 |
| 9 | Campo esplicito diretto | 2,17 | 2,33 | 0,48 | 0,67 |

### Mediane e limiti

| Percorso | Campioni inclusi | Esclusi | Primo testo client mediano | Totale client mediano |
|---|---:|---:|---:|---:|
| Chat | 3 | 0 | 206,82 ms | 410,83 ms |
| Sintesi di estratto fornito | 3 | 0 | 177,11 ms | 10061,74 ms |
| Campo esplicito diretto | 3 | 0 | 2,17 ms | 2,33 ms |

Verificati nuovamente numero, ordine, stati, instradamento e calcolo delle mediane sul rapporto ricevuto. [Rapporto numerico filtrato](synthetic-latency-baseline-mac-2026-10-02.json), senza testi, fonti, percorsi privati o request ID. Nessun percentile derivato da tre campioni.

Le prime richieste di chat e sintesi hanno un'attesa iniziale maggiore, presente anche nel backend. Nelle due repliche successive il primo testo è molto più rapido. La differenza è osservata: non sono stati misurati caricamento Ollama, preparazione del contesto, cache, carico esterno o stato caldo/freddo, quindi non le viene attribuita una causa certa. Nessuna nuova configurazione o ottimizzazione è stata applicata durante questa serie.

Le tre sintesi impiegano rispettivamente 10043,22, 9884,63 e 9834,25 ms dal primo testo alla fine del trasporto client. È il tratto successivo al primo contenuto, non una misura isolata del solo calcolo del modello. I contatori token nel rapporto sono nulli: non calcolare token al secondo o confrontare efficienza per token da questi dati. La chat chiede una risposta molto breve, mentre la sintesi ha un contesto e un compito differenti; non trattare i loro totali come confronto fra motori identici a parità di lavoro.

Le risposte dirette hanno explicit_fields, inferenceUsed false e generazione nulla. Il recupero degli estratti forniti è fra 0,05 e 2,14 ms: questi valori non misurano la scansione del vault reale e non sostituiscono le precedenti osservazioni della ricerca nelle note.

**Baseline sintetica finita raccolta e verificata.** L'esito riguarda completezza della serie e misure dei percorsi; qualityVerdict resta not_assessed, perché i testi sono stati scartati. Nessuna verifica semantica universale o miglioramento prestazionale dichiarato. Non ripetere la stessa serie per cancellare i primi campioni lenti.

Il prossimo intervento deve prima distinguere l'attesa iniziale dai costi interni del percorso Ollama e dalla produzione successiva al primo testo. Solo dopo scegliere una modifica isolata con gli stessi casi e criteri di qualità. Nessuna funzione vocale attivata, nessun dato del vault pubblicato, runtime e dipendenze invariati. PR sempre draft senza merge.
