# Roadmap dei moduli futuri

Requisiti raccolti il 2026-10-04 (Europe/Rome). Stato: pianificati, non implementati né attivati nel profilo locale. Questo aggiornamento riguarda soltanto documentazione: non modifica il runtime o il Mac.

La base locale esistente rimane il punto di partenza. Jarvis originale e OpenJarvis personalizzato restano separati; la PR di lavoro resta draft, senza merge a main. Nessuna nota personale, configurazione privata, credenziale, database o registrazione audio va pubblicata.

## Priorità e dipendenze

1. Proseguire il [piano della latenza end-to-end](end-to-end-latency-plan.md): la [adozione del trasporto compatto](qualification-compact-wire-production.md#collaudo-reale-concluso-e-superato--2026-10-04) è installata e collaudata sul Mac, con quattro fatti riesaminati favorevolmente e testo nell’interfaccia a 26,381 s. Il lettore ha isolato le fasi della stessa richiesta: caricamento 5,08 s, contesto 11,90 s, produzione 9,33 s. Il task è chiuso, senza ulteriori ripetizioni. Task attivo sul contesto: [quattro campioni conclusi](qualification-context-prompt-experiment.md#esito-mac-della-serie-finita--2026-10-04), qualità e meno token favorevoli, soglia prestazionale originale non superata per cache. Nessuna adozione o ripetizione. Preparata [diagnosi distinta di due richieste con prefissi isolati](qualification-prefill-isolation-diagnostic.md), per il prefill quasi interamente nuovo; raccolta Mac ancora da eseguire. Nessuna nuova funzione attivata. Voce e altri moduli restano futuri.
2. Progettare memoria e correzioni consultabili ed eliminabili. Una preferenza salvata non equivale ad addestramento del modello; eventuali miglioramenti richiedono prove prima/dopo.
3. Introdurre progressivamente gli strumenti utili: ricerca web, confronto Amazon e controllo del Mac, ciascuno con limiti e collaudi propri.
4. Aggiungere prima trascrizione e risposta vocale locali, poi valutare un canale WhatsApp consentito e collaudare il percorso completo.
5. Proattività, email e accesso remoto seguono i rispettivi progetti separati. Nessuna attivazione indiscriminata delle funzioni upstream.

I task qui sotto non sostituiscono i precedenti obiettivi relativi a documenti, WordPress, SEO, manutenzione e scalabilità. Ogni modulo deve essere sostituibile e disattivabile senza reinstallare il progetto.

## WEB — ricerca quando le informazioni non bastano

- [ ] Definire quando cercare: richiesta esplicita, dati soggetti a cambiamento, conoscenze insufficienti o problema non risolto. Non trasformare ogni richiesta locale in una ricerca esterna.
- [ ] Valutare strumenti e test upstream, scegliere esplicitamente il fornitore e definire timeout e budget finiti. Non ereditare implicitamente il fallback a un diverso servizio esterno.
- [ ] Inviare soltanto le informazioni necessarie alla ricerca. Non caricare automaticamente vault, note, conversazioni o credenziali; segnalare le dipendenze esterne del modulo.
- [ ] Confrontare fonti pertinenti, preferendo documentazione ufficiale per problemi tecnici. Mostrare collegamenti, data della consultazione e limiti; distinguere fatti documentati, inferenze e soluzioni ancora da provare.
- [ ] Gestire fonti discordanti, risultati insufficienti, errori e accessi bloccati senza inventare la risposta. Le istruzioni contenute nelle pagine non autorizzano azioni o accesso ai dati.
- [ ] Collaudare un problema sintetico risolvibile, dati discordanti, assenza di risultati, timeout e una pagina con istruzioni ostili. Un risultato di ricerca o una citazione non certificano la correttezza della conclusione.

## SHOP — Amazon, prodotto, venditore e convenienza

Obiettivo: ricevere un bisogno e un budget, mostrare a schermo una selezione motivata e preparare un eventuale acquisto per la revisione dell'utente.

### Dati da distinguere

| Ambito | Segnali da valutare | Limite da conservare |
|---|---|---|
| Esigenza | Uso previsto, compatibilità, caratteristiche obbligatorie, budget | Il più economico può non soddisfare la richiesta |
| Prodotto | Analisi delle caratteristiche, voto, numero e recenza delle recensioni, problemi ricorrenti, variante recensita | Un voto alto o molte recensioni non provano da soli qualità o autenticità |
| Venditore | Identità di chi vende, feedback del venditore, numero, percentuale positiva, periodo e problemi recenti | Recensioni del prodotto e feedback del venditore sono dati differenti |
| Vendite | Quantità o indicazioni di acquisti mostrate dalla piattaforma, con periodo, fonte, granularità e ambito | Non dedurre vendite dalle recensioni; non inventare vendite totali o del singolo venditore quando non disponibili |
| Offerta | Variante, condizione, chi spedisce, prezzo completo, disponibilità, consegna, resi e garanzia dichiarati | Venduto da e spedito da non sono equivalenti; prezzo e condizioni vanno ricontrollati prima dell'ordine |

Un'indicazione approssimativa del tipo “acquistati nell'ultimo mese”, se disponibile, va riportata come indicazione della piattaforma nel suo periodo, non come un conteggio esatto indipendentemente verificato. Non attribuirla a un singolo venditore senza una fonte che lo dichiari. Un dato mancante rimane non disponibile: non significa zero e non dimostra che il venditore sia inaffidabile.

### Task

- [ ] Definire accesso consentito ai dati correnti del prodotto e dell'offerta, con provenienza e data. Valutare API, strumenti e navigazione prima di scegliere l'integrazione.
- [ ] Definire criteri e pesi configurabili per categoria e preferenze dell'utente. Separare giudizio sul prodotto, reputazione del venditore, convenienza e sufficienza delle informazioni; nessun punteggio va presentato come garanzia.
- [ ] Mostrare schede/carousel con immagine, caratteristiche pertinenti, prezzo totale, venditore, segnali osservati, motivo della raccomandazione, collegamenti e dati non verificabili. Valutare pannello affiancato o sostituzione temporanea della vista centrale.
- [ ] Gestire pochi feedback, dati contraddittori, offerte di più venditori sullo stesso prodotto e prezzi cambiati. Non dichiarare recensioni false o venditore affidabile con certezza senza prove sufficienti.
- [ ] Preparare il riepilogo di prodotto, variante, quantità, venditore, consegna e totale prima dell'approvazione finale dell'acquisto. La richiesta di confronto non autorizza automaticamente un ordine.
- [ ] Collaudare confronti sintetici e poi un controllo reale in sola lettura; nessun ordine di prova o pagamento implicito.

## MAC — azioni controllate sul computer

- [ ] Progettare comandi separati per apertura di applicazioni, musica, volume e luminosità. Verificare le API supportate e i permessi macOS necessari.
- [ ] Valutare la modifica della risoluzione dello schermo soltanto fra modalità supportate, con possibilità di ripristino. Cambiare risoluzione non aumenta le capacità hardware della GPU.
- [ ] Preferire azioni definite e con parametri validati; non esporre un terminale senza limiti al modello. Distinguere comando inviato, esito osservato, errore e stato non verificato.
- [ ] Verificare il risultato delle azioni semplici e separare approvazioni per acquisti, pubblicazioni, modifiche live o altre azioni con effetti rilevanti. Le pagine web o i messaggi di terzi non concedono permessi.
- [ ] Misurare i comandi semplici senza obbligarli a passare per una lunga generazione del modello. Collaudare prima azioni reversibili.

## VOICE — WhatsApp vocale in ingresso e in uscita

Percorso desiderato: vocale ricevuto → autenticazione del mittente → trascrizione locale → coordinamento di Jarvis → risposta controllata → sintesi vocale locale → invio del messaggio vocale.

- [ ] Collaudare prima STT e TTS sul Mac Intel, con componenti sostituibili e funzionamento testuale conservato.
- [ ] Verificare una modalità WhatsApp consentita per il caso d'uso, requisiti dell'account, disponibilità dell'integrazione e costi. La Business Platform ufficiale è destinata all'uso aziendale: non dare per acquisita l'idoneità di un assistente personale generico o il collegamento all'account personale.
- [ ] Implementare ricezione, download audio, gestione dei formati e invio audio; il canale Cloud API upstream esaminato invia soltanto testo. Non è già il flusso vocale richiesto.
- [ ] Accettare richieste solo dai mittenti autorizzati, verificare l'autenticità delle notifiche e gestire duplicati senza eseguire due volte la stessa azione. Applicare limiti di durata, dimensione e coda.
- [ ] Definire conservazione minima e cancellazione dei file audio temporanei. L'elaborazione può restare locale; il trasporto WhatsApp dipende comunque da servizi esterni. Non inviare automaticamente note intere come risposta.
- [ ] Prevedere Mac acceso e servizio raggiungibile, gestione dell'indisponibilità, errori di trascrizione e richiesta ambigua. Un vocale non elimina la revisione richiesta per gli acquisti o altre azioni rilevanti.
- [ ] Misurare separatamente ricezione/download, trascrizione, elaborazione, ricerca eventuale, TTS e invio. L'accettazione dell'invio non prova il momento di consegna o ascolto sul telefono.
- [ ] Collaudare un vocale sintetico italiano, errore STT, mittente non autorizzato, duplicato e servizio non disponibile; poi una prova reale autorizzata di andata e ritorno. Nessuna prova audio o integrazione WhatsApp dichiarata già riuscita.

## Regola comune di completamento

Ogni task operativo avrà criteri fissati prima della prova, un numero finito di controlli pertinenti e un esito separato per funzionamento, qualità e tempi. Test tecnici superati non certificano automaticamente il significato della risposta. Un fallimento resta documentato; non viene trasformato in successo cambiando i criteri dopo la prova.

## Riferimenti esaminati per la progettazione

- OpenJarvis: [WebSearchTool](https://github.com/open-jarvis/OpenJarvis/blob/main/src/openjarvis/tools/web_search.py) e [test web search](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/tools/test_web_search.py). Consultazione dei sorgenti e di un estratto dei test, non esecuzione o attivazione del modulo.
- OpenJarvis: [canale WhatsApp](https://github.com/open-jarvis/OpenJarvis/blob/792131feb3948aca0b54a94e0344f6827ff3129d/src/openjarvis/channels/whatsapp.py) e [test WhatsApp](https://github.com/open-jarvis/OpenJarvis/blob/792131feb3948aca0b54a94e0344f6827ff3129d/tests/channels/test_whatsapp.py). Il canale letto è send-only e costruisce un payload testo.
- Meta: [invio audio nella raccolta ufficiale Cloud API](https://www.postman.com/meta/whatsapp-business-platform/request/goznbg0/send-audio-message-by-id), [indice dei termini](https://whatsappbusiness.com/terms-and-conditions/) e [WhatsApp Terms for Business Platform](https://www.whatsapp.com/legal/WhatsApp-Terms-for-WhatsApp-Business-Platform?lang=en), versione efficace dal 2026-09-23. L'idoneità complessiva del nostro caso e i costi non sono stati accertati; andranno verificati prima dello sviluppo dell'integrazione.
- Amazon: [annuncio ufficiale sui feedback del venditore](https://sellercentral.amazon.it/seller-forums/discussions/t/d3eb8db1-ac01-4604-b454-5c0f5a40c282), che distingue la performance del venditore dalla soddisfazione sul prodotto.

Questi riferimenti non attestano disponibilità delle funzioni sul Mac o affidabilità di un prodotto/venditore specifico. Nessun account esterno collegato, acquisto eseguito o messaggio inviato per questo aggiornamento del piano.
