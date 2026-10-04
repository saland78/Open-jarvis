# Qualifica e consultazione complete vincolate alla fonte

Stato al 2026-10-04: **aggiornamento installato, compilazione completa sul Mac e collaudo della nota reale superati**. La revisione del significato conferma i quattro fatti selezionati e la frase corrente completa con le indicazioni di consultazione. Esito circoscritto al caso e al formato riconosciuto; nessuna verifica esterna o garanzia su altre sintesi. Questo difetto è chiuso nel caso collaudato; il prossimo task riguarda la latenza, senza perdere informazioni o controlli.

## Difetto e soluzione

Il [collaudo del prefisso](qualification-clause-fix.md#esito-reale-del-collaudo-mac) conserva soggetto, predicato, aggettivo, etichetta e delimitazione alla nota, ma la continuazione generata omette la consultazione di dashboard o report con periodo, titolo e marketplace. Il vincolo nativo ammetteva qualsiasi continuazione breve: quel criterio di qualità rimaneva affidato solo al prompt. Esito completo fallito, senza adozione.

[qualification_sentence_guard.py](../../scripts/andrea/qualification_sentence_guard.py) deriva **la frase corrente completa dal suo passaggio originale**. Riusa il controllo di unicità e degli intervalli di caratteri già testato; la continuazione deve coincidere con la convenzione di consultazione riconosciuta. Supporta il testo del caso pubblico e la forma con «report KDP» presente nella nota reale. Non estende per ipotesi formulazioni ignote: le rifiuta prima di una richiesta.

Il campo text corrente riceve nello schema nativo un **const** contenente quella frase, senza inventare o completare parole. Dopo la generazione tutti i controlli precedenti rimangono attivi; un secondo controllo verifica provenienza, metadati, schema e uguaglianza esatta del testo con la frase originale normalizzata solo nella presentazione Markdown. Se cambia predicato, ambito, consultazione o uno dei tre riferimenti necessari, la risposta è rifiutata. Nessuna riparazione dopo la generazione e nessun retry.

**Origine del testo dichiarata:** F3 è una frase letterale sostenuta dalla fonte e vincolata prima della generazione; F1, F2 e F4 restano sintesi del modello. Non è una sintesi interamente libera, apprendimento del modello o verifica della dashboard. I contesti datati conservano le associazioni originali già fissate nello schema. L'uguaglianza della frase corrente non certifica il significato dei restanti record o la verità esterna.

Non sono cambiati i criteri della prova precedente per promuoverla: l'omissione resta un fallimento. La nuova correzione cambia il componente responsabile della preservazione della frase critica e rende trasparente il suo carattere letterale.

## Verifica e ricerca

Prima delle modifiche verificati fork al commit e4ad0d6fd1630938f0c187ae0c37195cb6c43a83 e PR #1 draft, non unita. Consultati nuovamente [test structured output upstream](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/engine/test_structured_output.py): riusato il passaggio dello schema JSON completo attraverso l'engine Ollama già presente. La suite upstream completa non è stata eseguita e i test di payload non certificano il significato.

Verificato il supporto specifico nel riferimento llama.cpp b10969 dichiarato da Ollama v0.34.2: [convertitore](https://github.com/ggml-org/llama.cpp/blob/b10969/common/json-schema-to-grammar.cpp) gestisce KIND_CONST come valore letterale JSON; [test](https://github.com/ggml-org/llama.cpp/blob/b10969/tests/test-json-schema-to-grammar.cpp) includono string const e literal string with escapes con type string. Consultazione del codice distinta dall'esecuzione dei test C++ o dalla verifica del runner installato sul Mac. Il controllo indipendente rifiuta un output non conforme anche se il motore ignora il vincolo.

**49 test passati**: 14 nuovi e 35 regressioni della candidata precedente, del trasporto, della diagnosi e del prompt. Il test nuovo riproduce esattamente la continuazione osservata: il guard precedente la accetta, il guard completo la rifiuta senza testo mostrato o riparato. Il replay dell'intero JSON reale raccolto conferma lo stesso esito senza una nuova inferenza. Coperti omissione di periodo/titolo/marketplace, negazione, ripetizione, ambito o verbo alterati, aggiunte, fonte o schema mutati, istruzioni estranee, hash, interruzioni e protocollo. Verificate anche le formulazioni riconosciute delle fonti e la forma con KDP, conteggi distinti e provenienza. Una regressione esplicita mantiene pending_review quando un altro record contiene una negazione semanticamente errata: il campo letterale non è un oracolo generale del significato.

```sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../OpenJarvis-brief-build/src:scripts/andrea:tests python -m unittest test_andrea_qualification_sentence_guard test_andrea_qualification_sentence_fix_probe test_andrea_qualification_clause_guard test_andrea_qualification_clause_fix_probe test_andrea_concise_qualification_text test_andrea_qualification_rejection_diagnostic test_andrea_qualification_prompt -q
```

## Una sola verifica sul Mac

[qualification_sentence_fix_probe.py](../../scripts/andrea/qualification_sentence_fix_probe.py), 18282 byte, SHA-256 **e6bfae47a55f4568f6b4cdef339fc273a5edc0ef4a0770a7c96889235b6a636f**. Incorpora copie esatte verificate di qualification_clause_guard.py (ad01e5192b19fc4bad068a0cdc288d9889fa0166eb2db6720283887910559757) e qualification_sentence_guard.py (976e22ad3ba6671011cc63c0d18ae21a39e4647d4ad698454b70db983b943866). Il vecchio modulo riusa solo la verifica del passaggio originale: non protegge più soltanto il prefisso del nuovo campo.

Riusa esclusivamente trasporto e caricatore della baseline dalla copia temporanea precedente, /tmp/OpenJarvis-concise-qualification-probe.py, SHA-256 6cbfecc754d8ab4fb46399d703e73effcd4bdd1a796994edd621e8fd37a9a975. Non esegue il vecchio confronto a quattro richieste. Verifica questi sorgenti e tutti gli otto hash di produzione prima di caricare moduli o usare la rete; nessuna configurazione privata o nota del vault letta. Se un file manca, è collegato o non coincide, si ferma senza scaricare altro.

Una richiesta del caso avversariale pubblico già definito; nessun nuovo canary, warm-up, seed, retry o scaricamento di modelli. qwen3:4b-instruct-2507-q4_K_M, temperatura 0,4, num_ctx 4096, num_predict 512, think=false, keep_alive=15m e scelta automatica dei thread invariati. Solo 127.0.0.1:11434, senza proxy o redirect. Non legge il vault, non scrive file o bytecode e non installa la candidata. OpenJarvis e Controlli restano aperti; eseguire in Controlli, evitando altre chat durante la richiesta.

Mantiene risposta accettata tecnicamente e JSON diagnostico distinto, passaggi originali e origini dei campi, categorie di rifiuto, durate client e contatori nativi. Errori non espongono messaggi arbitrari. Control+C interrompe senza altra richiesta. Limiti del trasporto ereditati: timeout socket 90 s e verifiche fra letture, 4 MiB di stream, 256 KiB per riga e 32000 caratteri generati; non è una scadenza rigida durante una lettura bloccata. Tempi diretti distinti dalla UI e dal server, nessun nuovo confronto prestazionale.

## Criteri di completamento

- Stream completo/stop senza retry o troncamento.
- Frase corrente integralmente conforme al passaggio originale, compresi predicato, qualifica, ambito e consultazione con periodo, titolo e marketplace.
- Quattro record e rispettive provenienze conservati; conteggio dichiarato e variabilità corretti, qualifica corrente e assenza storica distinte con le date originali.
- Riesame dei tre record generati: nessuna deduzione di zero, importo o verifica esterna inventati, nessuna fusione delle qualifiche o istruzione estranea seguita.
- F3 dichiarato letterale; altri record dichiarati sintesi. Il codice di uscita 0 indica accettazione tecnica e pending_review, non qualità universale.

Dopo questo riscontro restano integrazione nel percorso di produzione e collaudo del caso reale, con indicazione UI del campo letterale. Non sono già certificati dal prototipo. Fino al loro completamento non passare a latenza, voce, memoria o altri task. Nessuna adozione automatica o ripetizione di una prova negativa.

Note, dati personali, runtime, modello, profilo, dipendenze e Jarvis originale invariati. PR #1 resta draft, nessun merge.


## Esito della singola prova Mac e integrazione

La richiesta sintetica prevista termina con stop, senza retry o riparazioni. Quattro record presenti: conteggio e variabilità corretti, qualifica corrente e assenza storica separate con le rispettive date, frase corrente completa inclusi periodo, titolo e marketplace. Nessuno zero, importo o controllo esterno inventato; l'istruzione estranea non viene eseguita. F3 è dichiarato letterale e gli altri tre record sono generati. Revisione manuale favorevole **per questo caso**; pending_review rimane il verdetto automatico. Il [rapporto filtrato](qualification-sentence-fix-mac-2026-10-04.json) contiene solo durate, conteggi e categorie, senza storico del Terminale o note personali.

Totale client 35777,602 ms, primo frammento 19023,333 ms, caricamento nativo 4320,931 ms e cache dichiarata zero. Queste misure dirette non sono tempi UI e non dimostrano un guadagno prestazionale rispetto alle altre prove. Nessuna ulteriore richiesta al modello per questa chiusura. I precedenti esperimenti falliti restano tali.

La [integrazione in produzione](qualification-sentence-production.md) mantiene gli stessi due guard e il percorso del caso sintetico. La frase completa entra nel contratto nativo prima della generazione; il controllo indipendente non ripara l'output. Rimangono rilettura completa della nota al termine, controllo di vault/stato/contenuto, rifiuti su numeri e date, un'unica generazione, gestione di timeout e cancellazione. Il profilo del libro conserva schema e prompt precedenti.

**148 controlli Python e 12 controlli dell'interfaccia superati**; bundle Vite/PWA prodotto. Il compilatore TypeScript 7 nativo di questo ambiente si arresta prima di controllare il progetto per readlink /proc/self/exe non disponibile: non viene dichiarata superata la build combinata npm run build. Nessuna dipendenza sostituita per aggirarlo; verifica della compilazione completa sul Mac al riavvio ancora necessaria.

I test storici ricostruiscono gli archivi pubblici esatti di note_facts e dei componenti precedenti, mantenendo tutti gli hash originali dei probe. Questi ultimi restano diagnostici di quelle versioni e rifiutano intenzionalmente una nuova installazione non corrispondente; non sono stati resi meno rigorosi per accettare la versione nuova. La provenienza della frase è dichiarata sia nel testo del backend sia nelle descrizioni della pagina.


## Collaudo di produzione concluso

Aggiornamento installato e compilazione completa riuscita sul Mac. La successiva singola sintesi della nota reale è tecnicamente accettata e supera il confronto manuale con tutti i passaggi selezionati, compresa la consultazione completa. Il [rapporto di produzione](qualification-sentence-production.md#chiusura-verificata-sulla-nota-reale--2026-10-04) distingue questa chiusura dagli stati precedenti: circa 45,29 s fino all'aggiornamento della risposta UI, nessuna nuova inferenza per archiviare l'esito. Nessun testo personale pubblicato. Il caso sintetico e quello reale osservati sono superati; i campi letterali non certificano altre parafrasi o dati esterni. I riferimenti a verifiche ancora necessarie nelle sezioni precedenti documentano lo stato prima del collaudo, ora concluso. Prossimo task: latenza con i medesimi requisiti di qualità.
