# Ricerca web esplicita — prima pagina, collaudo Mac concluso

Base verificata su GitHub: `9857880e0aa7803af4abeb0900d52899059327e8`, branch `feature/andrea-local-profile`, PR draft. Consultati prima del task tool web upstream, test web search e test dei permessi di ricerca negli agenti ibridi. Non attivare gli agenti generici o il loro fallback automatico.

## Esiti dei fornitori

Due ricerche pubbliche reali per fornitore sul Mac, senza retry: You.com 880,51 e 796,70 ms; DuckDuckGo 779,87 e 820,29 ms. Collegamenti principali pertinenti alle documentazioni Python e Ollama. Alcuni risultati storici o con snippet vuoti, non una garanzia di qualità universale. Risultati del motore, non pagine lette dal programma né sintesi del modello. I precedenti fallimenti di rete nel contenitore restano registrati nei documenti delle prove.

## Modulo preparato

Nuova pagina `/web-search`, voce Ricerca web nel profilo personale. Default DuckDuckGo, scelta manuale You.com chiaramente marcata come prova gratuita. Il profilo You.com MCP free è destinato alla valutazione: questa opzione non implica un servizio continuativo garantito. Nessuna chiave o pagamento attivato. La versione HTML DuckDuckGo non è una API garantita; un blocco deve restare un errore.

La richiesta same-origin `/api/andrea/web/search` accetta soltanto query e provider espliciti. Il testo va a quel fornitore; nessun caricamento di note, memoria o conversazioni. Non viene inferita una ricerca dalla chat. Campi ulteriori, provider sconosciuti e query vuote/troppo lunghe/di più righe sono rifiutati prima della rete. Host e Origin locali richiesti. La nuova rotta non concede capacità generiche agli agenti.

Un processo figlio isolato effettua la ricerca con i client già collaudati: timeout di 25 secondi dopo avvio del processo, kill e attesa su timeout/cancellazione, una richiesta attiva nel runtime e tre secondi minimi fra avvii. Per You.com sono necessarie anche inizializzazione ed elenco strumenti; le misure dell'intera richiesta includono questo costo. Niente retry o cambio di motore, redirect, cookie persistenti, proxy ambientali, apertura automatica di pagine, Ollama o salvataggio della ricerca. Il browser interrompe a 30 secondi e permette interruzione manuale. La navigazione fuori dalla pagina cancella la richiesta; risultati tardivi non rimpiazzano uno stato successivo.

Fino a tre schede: titolo, testo letterale del motore, link HTTPS, fornitore, data UTC di consultazione presentata in locale e durata backend. Snippet vuoto esplicitamente segnalato, risultati vuoti distinti da errori. React esegue escaping dei testi; link esterno con noreferrer/noopener. Gli URL sono filtrati sintatticamente, non verificati tramite DNS. L'utente può aprire un link; il programma non visita la fonte né può certificare il contenuto, la recenza o l'affidabilità.

## Verifiche in sviluppo

83 test Python pertinenti passati: nuovi client/servizio/route, errori, input, cooldown, timeout e cancellazione; regressioni memoria, fatti delle note e sintesi strutturata. Una prima esecuzione estesa non trovava i sorgenti upstream nel percorso Python; rieseguita con il mirror source disponibile, stessa selezione passata. 23 test frontend passati per web/memoria/note/profilo locale; richieste minime, nessun retry, fonte ostile escapata, URL eseguibile escluso, snippet mancante e avvisi della pagina.

Bundle Vite/PWA generato. Comando completo `npm run build` fermato dal compilatore TypeScript 7 nativo nel contenitore: `/proc/self/exe` non disponibile. Il bundler successivo è passato ma non sostituisce il typecheck. Questa limitazione del contenitore resta registrata; la successiva compilazione completa sul Mac è passata, come documentato sotto.

## Criteri finiti di installazione e collaudo

Aggiornamento separato, sorgenti pinned con hash e backup, controllo baseline, porta 8008 libera prima della sostituzione. Nessuna nota/configurazione/database/dipendenza aggiornata. Riavviare con il launcher esistente che compila il frontend; verificare completamento di TypeScript e Vite. Aprire Ricerca web, scegliere DuckDuckGo e cercare la query pubblica Python già usata, poi You.com con la query Ollama. Controllare query/fornitore mostrati, schede/link e tempi, nessun testo privato incluso. Una prova di interruzione è separata dalla qualità dei risultati. Se un passo fallisce, conservare l'errore e risolverlo prima di dichiarare concluso il modulo.

Installer `scripts/andrea/update_web_search.py`: sette file pinned al commit sorgente `efd8793d78a8e6b012404c13e381f14796924c07`, tre sostituzioni e quattro moduli nuovi. Sette test aggiuntivi passati per manifest/hash, backup e idempotenza, dati privati intatti, download corrotto, edit locale rifiutato prima della rete, porta occupata, rollback, modulo diverso/symlink e modifica durante il download. Totale dei controlli Python pertinenti: 90, su due selezioni complementari. Le fixture del vecchio runtime/App/Sidebar sono codice pubblico, non configurazioni del Mac.

## Interfaccia richiesta da Andrea

Indicatori piccoli sotto il nucleo; dati ampi al posto del nucleo con ritorno alla vista principale. Requisito registrato nella roadmap come composizione modulare futura. Questa pagina mostra risultati ampi; non implementa ancora nucleo animato, dashboard Second Brain o carosello Amazon. Sintesi web, confronto venditori/prodotti, acquisti e controllo del Mac sono task successivi distinti.

## Collaudo Mac concluso — 2026-10-04, Europe/Rome

Installazione dei sette file completata con verifica hash e backup; avvio tramite launcher esistente. Il log fornito mostra `tsc -b && vite build`, bundle e PWA completati e avvio sulla porta 8008. La limitazione TypeScript del contenitore non ha impedito la compilazione sul Mac; nessun cambiamento alle dipendenze necessario.

Due controlli nell'interfaccia del Mac, risultati osservati negli screenshot senza pubblicare immagini o cronologia:

| Fornitore | Query pubblica | Tempo backend | Esito della pagina |
|---|---|---|---|
| DuckDuckGo HTML | `site:docs.python.org asyncio wait_for` | 1171 ms | Tre schede leggibili, query/fornitore/data, estratti e link di documentazione Python |
| You.com MCP free, valutazione | `site:docs.ollama.com keep_alive` | 1528 ms | Tre schede di documentazione Ollama, link, query/fornitore/data; snippet assenti esplicitamente segnalati |

Terza prova finita: Andrea ha cliccato Interrompi ricerca e riportato il messaggio «Ricerca interrotta o scaduta. Nessun altro fornitore è stato contattato.». Gestione dell'interruzione osservata nell'interfaccia; la sola scritta non misura il momento della terminazione del processo figlio o prova indipendentemente le richieste esterne. Kill/reap e assenza di fallback sono controllati separatamente nei test del servizio e nel codice. Non ripetere fino al successo.

Concluso il task circoscritto di ricerca esplicita con risultati a schermo: installazione, compilazione, due fornitori e feedback di interruzione osservati. Nessuna sintesi web o lettura automatica delle pagine ancora implementata. I tempi includono la richiesta al fornitore e il lavoro del backend, non il tempo esatto di disegno sullo schermo; non equivalgono alla latenza della chat o del modello. Nessuna garanzia universale di pertinenza, aggiornamento, disponibilità dei fornitori o qualità delle risposte. Il profilo You.com resta valutazione.
