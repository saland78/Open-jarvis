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

## Raccolta Mac ancora da eseguire

Scaricare lo script da un commit preciso, verificarne SHA-256, poi eseguirlo nella finestra Controlli con OpenJarvis acceso. Eseguire la serie una volta. Esaminare singole misure, inclusioni/esclusioni e mediane prima di scegliere un componente da ottimizzare. Le nove richieste sul Mac non sono già state eseguite o dichiarate superate. Non confondere i tempi simulati di sviluppo con una baseline del Mac.
