# Protezione circoscritta delle qualifiche datate

Il controllo reale della sintesi libera del 2026-10-02 è fallito: una frase fondeva un valore non verificato nella nota con l'assenza dichiarata in una fotografia storica. Il precedente esito negativo resta valido. Questa modifica impedisce quel percorso riconoscibile mediante una risposta alternativa dichiarata, senza sostenere di aver corretto semanticamente ogni parafrasi del modello.

## Comportamento

Per una richiesta di sintesi sulle note, dopo i conteggi espliciti, il backend riconosce soltanto due convenzioni letterali: un'intestazione Aggiornamento con data ISO seguita dall'etichetta DATO NON VERIFICATO e un'intestazione Fotografia con data ISO seguita da DATO ASSENTE. Se sono presenti entrambe, anche in fonti diverse, non avvia Ollama. Risponde con intestazioni ed etichette letterali separate e citate. L'interfaccia mostra Qualifiche datate dalle fonti e dichiara che non è stata generata una sintesi del modello.

La regola è prudente: le etichette possono riguardare quantità diverse, e non viene dichiarato un conflitto. Non usa modifiedAt per scegliere la verità o la data dei fatti. Non completa una riga tagliata: copia soltanto l'etichetta completa e il contesto datato. I riferimenti interni ambigui causano astensione. Le intestazioni oltre 300 caratteri non vengono tagliate; invita alla lettura. Sono visualizzate al massimo sei coppie uniche, con avviso di selezione parziale.

Questa risposta non risolve una domanda esaustivamente, non certifica disponibilità di dashboard, non interpreta dato assente come zero e non verifica sistemi esterni. Altre formulazioni, date non ISO e contesti senza queste intestazioni non sono coperti. Il percorso generativo restante continua a richiedere revisione. Non è un validatore semantico universale e non equivale ad apprendimento del modello.

Chat, conteggi diretti, Passaggi brevi dalle fonti, prompt del modello, limiti Ollama e ricerca restano nei rispettivi percorsi. Le misure marcano answerMode=status_scope_quotes, inferenceUsed=false e tempi di generazione nulli. Il primo testo è misurato al confine ASGI, non al rendering del browser.

## Riferimento upstream e verifiche

Consultati nuovamente PR draft e sorgenti prima di modificare codice. Consultati [DocQAScorer](https://github.com/open-jarvis/OpenJarvis/blob/main/src/openjarvis/evals/scorers/doc_qa.py) e [relativi test](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/evals/scorers/test_doc_qa.py): fatti attesi e citazioni non bastano a garantire il significato di qualifiche temporali in ogni frase. La nuova protezione resta nel modulo locale isolato, senza attivare altri agenti o strumenti upstream.

- Riprodotto il fallimento della nuova regressione sul runtime precedente: attivava model_synthesis invece della risposta protetta.
- 82 test mirati passati, inclusi dieci nuovi controlli per date e qualifiche separate, ordine delle fonti, timestamp irrilevanti, righe tagliate, riferimenti ambigui, intestazioni limitate, integrazione ASGI con recupero reale sintetico, estratti forniti, precedenza dei conteggi, chat e modalità estrattiva, etichetta UI e misure senza testo privato.
- Suite adattatore usa il parser scalare upstream isolato. Non eseguita l'intera suite upstream né il backend Rust completo.
- Typecheck frontend e build Vite locale passati. Il contenitore richiede TypeScript JavaScript 5.9.3 e Workbox development; queste due impostazioni di collaudo non vengono distribuite. Build standard sul Mac successivamente riuscita; esito riportato sotto.
- Nessun browser Mac o nota privata consultato durante queste prove. Nessuna nuova misura di latenza Ollama è giustificata per il percorso senza inferenza.

## Collaudo sul Mac concluso

Installazione sul Mac completata il 2026-10-02: cinque file verificati e backup creato. Compilazione standard TypeScript, Vite e PWA riuscita; log arrivato all'avvio sulla porta 8008. Il browser inizialmente richiedeva un vecchio modulo della pagina: dopo l'istruzione di ricaricamento, il risultato aggiornato è stato mostrato e fornito da Andrea. Nessuna modifica aggiuntiva al codice per questo inconveniente.

La richiesta sul caso reale ha mostrato Qualifiche datate dalle fonti, con intestazione dell'aggiornamento e della fotografia separate e ciascuna associata alla propria etichetta e citazione. Non compare la frase che fonde le due qualifiche; la risposta e l'interfaccia dichiarano esplicitamente che la sintesi libera non è stata generata, che la selezione è parziale e che non sono stati verificati sistemi esterni. Il testo corrisponde al percorso deterministico già collaudato in sviluppo. La lettura della nota e le qualifiche erano state fornite nei passaggi precedenti; non è stata richiesta una nuova serie di prove identiche.

**Collaudo circoscritto della protezione concluso e superato.** Questo esito verifica l'alternativa dichiarata sul caso riconosciuto; non riclassifica il precedente test negativo della sintesi libera, non certifica tutte le parafrasi generative e non verifica dati attuali in dashboard esterne. Nessuna nuova misura delle prestazioni Ollama su un percorso senza inferenza. Nessun testo personale o screenshot pubblicato.

Note, database, profili e dipendenze non fanno parte dell'aggiornamento. Jarvis originale resta separato e intatto. PR draft: non unire a main. Nessun testo personale, screenshot o report KDP pubblicato.
