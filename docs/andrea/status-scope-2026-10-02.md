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
- Typecheck frontend e build Vite locale passati. Il contenitore richiede TypeScript JavaScript 5.9.3 e Workbox development; queste due impostazioni di collaudo non vengono distribuite. Build standard sul Mac ancora da verificare per questa modifica.
- Nessun browser Mac o nota privata consultato durante queste prove. Nessuna nuova misura di latenza Ollama è giustificata per il percorso senza inferenza.

## Chiusura sul Mac ancora da eseguire

Installare l'aggiornamento verificato a porta 8008 ferma, riavviare e verificare disponibilità del vault in sola lettura. Eseguire una sola richiesta di Sintesi del modello sugli stessi KPI: deve apparire Qualifiche datate dalle fonti, con due contesti datati separati, nessuna frase che fonde le qualifiche e nessuna pretesa di generazione. Confrontare le due etichette con la nota aperta. Il collaudo della protezione è superato soltanto dopo questo controllo; non riqualifica come superato il test precedente della sintesi libera.

Note, database, profili e dipendenze non fanno parte dell'aggiornamento. Jarvis originale resta separato e intatto. PR draft: non unire a main. Nessun testo personale, screenshot o report KDP pubblicato.
