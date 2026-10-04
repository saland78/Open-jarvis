# Ricerca web esplicita — prima pagina, collaudo Mac da completare

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

Bundle Vite/PWA generato. Comando completo `npm run build` fermato dal compilatore TypeScript 7 nativo nel contenitore: `/proc/self/exe` non disponibile. Il bundler successivo è passato ma non sostituisce il typecheck. Il typecheck completo e la compilazione sul Mac devono ancora passare: non dichiararli verificati qui. Nessun browser reale sul Mac collaudato per la nuova pagina.

## Criteri finiti di installazione e collaudo

Aggiornamento separato, sorgenti pinned con hash e backup, controllo baseline, porta 8008 libera prima della sostituzione. Nessuna nota/configurazione/database/dipendenza aggiornata. Riavviare con il launcher esistente che compila il frontend; verificare completamento di TypeScript e Vite. Aprire Ricerca web, scegliere DuckDuckGo e cercare la query pubblica Python già usata, poi You.com con la query Ollama. Controllare query/fornitore mostrati, schede/link e tempi, nessun testo privato incluso. Una prova di interruzione è separata dalla qualità dei risultati. Se un passo fallisce, conservare l'errore e risolverlo prima di dichiarare concluso il modulo.

## Interfaccia richiesta da Andrea

Indicatori piccoli sotto il nucleo; dati ampi al posto del nucleo con ritorno alla vista principale. Requisito registrato nella roadmap come composizione modulare futura. Questa pagina mostra risultati ampi; non implementa ancora nucleo animato, dashboard Second Brain o carosello Amazon. Sintesi web, confronto venditori/prodotti, acquisti e controllo del Mac sono task successivi distinti.
