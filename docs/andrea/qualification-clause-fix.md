# Conservare il predicato e l'ambito delle qualifiche

Stato al 2026-10-04 (Europe/Rome): **correzione candidata implementata e 35 controlli di sviluppo superati; Ollama reale sul Mac e integrazione in produzione ancora da verificare**. Tutti gli altri task sono sospesi fino alla correzione e al collaudo di questo difetto. Il confronto prestazionale precedente resta fallito.

## Difetto osservato

La [diagnosi conclusa](qualification-rejection-diagnostic.md#confronto-della-frase-con-la-fonte-sintetica) contiene una fonte con «I valori aggiornati restano DATO NON VERIFICATO soltanto in questa nota», mentre la generazione usa «I valori sono DATO NON VERIFICATO». Il controllo precedente controlla il predicato soltanto quando trova la famiglia di parole «aggiornati»: eliminarla consente alla frase di passare perdendo persistenza, aggettivo e ambito esplicito. Il prefisso del renderer non rende la frase generata equivalente alla fonte.

Questo è un difetto riproducibile del controllo e della conservazione della clausola. Il JSON del rifiuto precedente per unsupported_value_update è invece stato scartato dal vecchio esperimento: questa correzione non pretende di ricostruirlo o promuovere retroattivamente quella prova.

## Correzione concreta

[qualification_clause_guard.py](../../scripts/andrea/qualification_clause_guard.py) ricava la clausola essenziale dal passaggio originale individuato dal piano, verificando identificatore della fonte, intervallo di caratteri e citazione. Tolta soltanto la presentazione Markdown, mantiene soggetto, aggettivo, predicato, etichetta, delimitazione alla nota e due punti. Accetta le convenzioni riconosciute con sono/restano/risultano e in questa nota/solo in questa nota/soltanto in questa nota. Una struttura sconosciuta o ambigua non produce un prefisso inventato.

Prima della generazione aggiunge al solo campo text della qualifica corrente un pattern nello schema JSON nativo. Il prefisso è letterale, ancorato all'inizio; la continuazione è su una riga e limitata affinché l'intera frase resti entro 400 caratteri. Il modello può riformulare la continuazione, conservando le indicazioni di consultazione. Il vincolo contiene parole della fonte specifica, non una risposta fissa scritta per il caso di prova.

Dopo la generazione esegue **tutti i controlli originali**, poi verifica indipendentemente la stessa clausola contro fonte e schema. Una risposta senza predicato o con ambito alterato è rifiutata anche se l'inferenza ignora il pattern. Non aggiunge un verbo al testo, non riscrive JSON rifiutato, non elimina «aggiornati», non rilassa il controllo precedente e non genera una seconda risposta automaticamente.

Il nuovo vincolo cambia soltanto il record corrente della famiglia riconosciuta delle quattro qualifiche. Fatti, date, prove e riferimenti restano originali; la famiglia libro non è modificata. Il prototipo è isolato: note_facts.py e gli altri otto sorgenti di produzione verificati restano byte per byte invariati.

**Trasparenza:** questa è generazione con una clausola letterale protetta, non parafrasi interamente libera, apprendimento del modello o verifica dei dati della fonte. Il controllo della clausola non è un validatore generale del significato. Una negazione nel record separato sulla variabilità può ancora passare i controlli tecnici: una regressione lo documenta e mantiene pending_review. La continuazione, gli altri record e la verità esterna richiedono revisione distinta.

## Ricerca primaria e riuso upstream

Prima delle modifiche verificati il fork al commit df5c3a9a377d46bb83b898aecf745bd1defc63da e PR #1 ancora draft, non unita. Consultato [OpenJarvis tests/engine/test_structured_output.py](https://github.com/open-jarvis/OpenJarvis/blob/792131feb3948aca0b54a94e0344f6827ff3129d/tests/engine/test_structured_output.py): si riusa il passaggio dello schema completo attraverso l'engine Ollama già presente nel fork. La presenza di quei test non certifica il significato delle risposte o ogni pattern; la suite completa upstream non è stata eseguita in questo intervento.

La [documentazione ufficiale Ollama](https://docs.ollama.com/capabilities/structured-outputs) descrive schemi nel parametro format e validazione della risposta. Controllata la versione installata dichiarata, [Ollama v0.34.2](https://github.com/ollama/ollama/tree/dfabde4539e42ba1e1eab50a3a50b88aea7958a0): [llm/llama_server.go](https://github.com/ollama/ollama/blob/dfabde4539e42ba1e1eab50a3a50b88aea7958a0/llm/llama_server.go) passa lo schema a llama-server; [LLAMA_CPP_VERSION](https://github.com/ollama/ollama/blob/dfabde4539e42ba1e1eab50a3a50b88aea7958a0/LLAMA_CPP_VERSION) indica b10969.

Consultati [convertitore](https://github.com/ggml-org/llama.cpp/blob/b10969/common/json-schema-to-grammar.cpp) e [test](https://github.com/ggml-org/llama.cpp/blob/b10969/tests/test-json-schema-to-grammar.cpp) di quel riferimento. Il convertitore richiede ancoraggi e supporta letterali, classi e ripetizioni limitate; alcuni pattern non supportati diventano un vincolo generico per stringhe. Per questo il pattern evita scorciatoie regex e lookaround, conserva un controllo indipendente nel backend e viene controllato anche con Ollama reale prima dell'adozione. Consultazione del sorgente distinta dall'esecuzione dei test C++ o dalla compilazione della grammatica sulla macchina di sviluppo.

## Collaudo finito sul Mac

[qualification_clause_fix_probe.py](../../scripts/andrea/qualification_clause_fix_probe.py), 14011 byte, SHA-256 **bb90a059196ec1cd05c3f89239c7a59b02dea84453e7cf1e450d39a236e9b0cb**. Incorpora una copia esatta verificata del modulo candidato (SHA-256 ad01e5192b19fc4bad068a0cdc288d9889fa0166eb2db6720283887910559757). Usa la copia temporanea già presente di concise_qualification_text_probe.py, SHA-256 6cbfecc754d8ab4fb46399d703e73effcd4bdd1a796994edd621e8fd37a9a975, solo come trasporto e caricatore della baseline verificata. Non esegue il suo precedente confronto a quattro richieste.

Tutti gli otto hash della produzione sono controllati prima di eseguire moduli o accedere alla rete. Se la copia temporanea manca, è collegata o è cambiata, si ferma senza scaricare altro automaticamente. Nessuna configurazione privata o nota reale viene letta.

Due richieste sintetiche al massimo, nessun retry:

1. **Compatibilità del vincolo nativo.** Piccolo oggetto con un campo text e pattern ricavato dal prefisso originale, continuazione massima di dieci caratteri. La richiesta chiede deliberatamente un testo incompatibile. Il risultato deve essere JSON senza chiavi duplicate, stream completato e testo conforme al pattern. Se fallisce, il secondo controllo non parte. Conformità osservata nel campione, non prova universale del convertitore.
2. **Caso difettoso.** Una generazione del caso avversariale pubblico già usato, con i messaggi e il piano di produzione avvolti dal nuovo vincolo. Contratto originale completo più controllo indipendente della clausola. Rimangono disponibili JSON grezzo, risposta resa soltanto se accettata tecnicamente e quattro passaggi originali per confronto manuale. Nessuna riparazione del testo.

Entrambe chiamano solo 127.0.0.1:11434, senza proxy o redirect, con qwen3:4b-instruct-2507-q4_K_M, temperatura 0,4, num_ctx 4096, num_predict 512, think=false e keep_alive=15m. Non si cambiano thread, modello, budget, profilo o dipendenze. Lasciare le finestre **OpenJarvis** e **Controlli** aperte; eseguire il collaudo in Controlli, evitando altre chat durante le due richieste. Non serve fermare il server per questo prototipo isolato.

Il collaudo non scrive file o bytecode e non installa la correzione. Vale il limite di trasporto già verificato: timeout socket 90 s e controlli fra letture, stream 4 MiB, riga 256 KiB, generazione 32000 caratteri; non si dichiara una scadenza esatta durante una lettura bloccata. Control+C interrompe senza retry. Durate native e client eventualmente stampate non sono un nuovo confronto prestazionale né misure della UI.

## Criteri prima di dichiarare il problema risolto

- Compatibilità osservata e caso difettoso completati senza truncation o retry.
- Conservazione letterale della clausola della fonte, compresi «aggiornati», «restano» e «soltanto in questa nota».
- Tutti i controlli originali superati, conteggio e variabilità conservati, qualifiche corrente e storica distinte con le rispettive date e riferimenti.
- Revisione della risposta rispetto ai quattro passaggi: indicazioni di consultazione conservate, niente zero dedotto, importi inventati, aggiornamenti avvenuti o estensioni alla dashboard; istruzioni ostili ignorate.
- Integrazione successiva nel percorso di produzione, con collaudo del caso reale e messaggio UI trasparente sulla clausola protetta. Il prototipo isolato non certifica già questi due passaggi.

Uscita 0 del prototipo significa accettazione tecnica e **pending_review**, non «tutto perfetto». Se uno dei due controlli fallisce, analizzare il JSON e la categoria già raccolti; non ritentare per trovare un campione favorevole e non passare ad altri task.

## Controlli di sviluppo conclusi

**35 test passati**: 14 nuovi (8 sul vincolo e 6 sul collaudo) e 21 regressioni del trasporto, diagnosi e prompt precedente. Riprodotta la frase osservata che prima passava e ora viene rifiutata senza riparazione. Coperti verbi e ambiti originali, negazione della clausola, omissione dell'aggettivo, ambito esterno, riordino, fonte mutata, prova ambigua, schema alterato, limiti, interruzioni, hash e assenza di scritture. Stream HTTP locale simulato con le due richieste completato. Ollama sul Mac non ancora eseguito per questa candidata; nessun esito reale dichiarato.

```sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../OpenJarvis-brief-build/src:scripts/andrea:tests python -m unittest test_andrea_qualification_clause_guard test_andrea_qualification_clause_fix_probe test_andrea_concise_qualification_text test_andrea_qualification_rejection_diagnostic test_andrea_qualification_prompt -q
```

PR #1 resta draft. Nessuna modifica al Jarvis originale o ai dati personali; nessuna nota o cronologia del Terminale pubblicata.
