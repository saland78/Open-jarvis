# DuckDuckGo — prova separata prima dell'integrazione

Stato GitHub verificato prima del lavoro: branch `feature/andrea-local-profile`, commit `2783cadae170fbae425938654a52d4b06e3ceacf`. Consultati upstream `src/openjarvis/tools/web_search.py`, `tests/tools/test_web_search.py` e `tests/agents/test_hybrid_provider_search_security.py`. La chiamata upstream a `DDGS.text()` non imposta un backend esplicito: non usarla per questa prova di isolamento del fornitore.

La [documentazione ufficiale DuckDuckGo](https://duckduckgo.com/duckduckgo-help-pages/features/non-javascript) indica le versioni HTML e Lite. Questa prova usa soltanto `https://html.duckduckgo.com/html/`, senza presumere una API stabile o una garanzia di servizio. I selettori HTML sono un contratto del parser locale da verificare sul Mac, non una API garantita dalla documentazione. Non gestisce CAPTCHA o aggira blocchi.

## Prova finita

`scripts/andrea/duckduckgo_provider_probe.py` è autonomo, usa la libreria standard e non legge il progetto, vault, memoria, cronologia o configurazioni. Non installa dipendenze né modifica OpenJarvis. Stesse due query pubbliche della prova You.com, senza argomenti personalizzabili: `site:docs.python.org asyncio wait_for` e `site:docs.ollama.com keep_alive`.

Massimo due richieste POST, una per query; niente retry, cookie, proxy, redirect, paginazione o cambio di fornitore. Il limite complessivo del figlio è 45 secondi; apertura con timeout di 8 secondi, risposta fino a 1 MiB. Il processo viene terminato su scadenza o interruzione, con conservazione degli eventuali risultati precedenti. HTTP diversi da 200, challenge, formato sconosciuto e HTML incompleto del risultato sono errori, non ricerche vuote. Il vuoto è accettato soltanto con un marcatore HTML riconosciuto di assenza risultati.

Il parser estrae titoli, collegamenti e snippet, esclude contenitori pubblicitari riconosciuti e script, decodifica collegamenti DuckDuckGo senza visitarli, limita e deduplica fino a tre risultati. URL HTTPS controllati sintatticamente, non certificazione DNS o sicurezza per una futura visita. Nessun risultato viene aperto o inviato al modello. I testi restano dati; il programma non interpreta istruzioni remote. La revisione di pertinenza resta distinta dalla riuscita del trasporto.

## Esiti disponibili

You.com sul Mac: due ricerche completate senza retry alle 2026-10-04 22:25 Europe/Rome, 880,51 ms e 796,70 ms per le chiamate di ricerca. Risultati con domini ufficiali attesi; primo indice Python pertinente a `wait_for`, FAQ e API Ollama pertinenti a `keep_alive`. Alcuni risultati Python storici e snippet vuoti: il collegamento è verificato per queste due prove, non qualità universale o sintesi web. Nessuna installazione del modulo web.

DuckDuckGo: nove test locali passati, più gli undici You.com rimasti verdi (20 complessivi). Coprono HTML annidato, caratteri, wrapper, deduplicazione e limiti; pubblicità/script/URL scartati senza contaminare la fonte precedente; URL privati; challenge, formato sconosciuto e codifica errata; richiesta fissa e assenza di redirect; HTTP/tipo/dimensione; errore seconda query senza retry; scadenza/interruzione e terminazione.

Una prova reale nel contenitore si è fermata sulla prima richiesta con `network_or_timeout`, zero risultati e nessun retry. Non è un successo, né dimostra lo stesso esito sul Mac. DuckDuckGo sul Mac non ancora verificato.

## Criteri sul Mac e passo successivo

Lasciare OpenJarvis acceso; scaricare lo script separatamente in `/tmp`, verificarne l'hash e avviarlo dal Terminale Controlli con il Python già disponibile. Rivedere il report: due richieste completate, risultati pertinenti con domini ufficiali, niente blocchi o ripetizioni. Non integrare un fornitore fallito e non sostituirlo silenziosamente. Se il formato reale differisce, diagnosticare sulla sola risposta pubblica e conservare l'esito originale.

Poi progettare la pagina locale Ricerca web con query esplicita, fornitore visibile, collegamenti e data di consultazione, gestione snippet assente e errori comprensibili. Il profilo You.com MCP free resta valutazione: per l'uso continuativo verificare condizioni e disponibilità prima di adottarlo. Sintesi, apertura pagine, ricerche autonome, acquisti Amazon e azioni sul computer restano passi separati non abilitati da queste prove.
