# Verifica circoscritta della sintesi libera — 2026-10-02

## Verdetto complessivo: non superato

Sono stati eseguiti i sei casi quality invariati e un controllo finale nell'interfaccia sulle fonti reali. Il controllo finale non conserva una distinzione sufficientemente esplicita fra assenza storica e valori attuali non verificati nella nota. Non viene ripetuta la domanda per scegliere un risultato favorevole e non viene modificata una nota personale per adattarla alla risposta.

Questo è un esito della versione installata, con il prompt libero precedente e il modello locale configurato. Non è una nuova prova della guida di stile breve ritirata. La modalità Passaggi brevi dalle fonti, già collaudata e superata, resta separata e il suo risultato non cambia.

## Sei casi sintetici: superati nei criteri fissati

Tutte le richieste sono completate con stop, senza troncamenti e con verifiche formali vere. Tre casi usano explicit_fields senza inferenza e tre model_synthesis con Ollama. La revisione del significato è distinta da qualityVerdict pending_review, che il raccoglitore non cambia automaticamente.

| Caso | Percorso | Revisione |
|---|---|---|
| explicit | Campo diretto | Conteggio e data della fotografia conservati, fonte prevista citata. |
| unknown | Sintesi del modello | Limite agli estratti disponibili, non verificato distinto da zero, nessuna indisponibilità esterna affermata. |
| conflict | Campo diretto | Entrambi i valori mantenuti; nessuna scelta dalla data del file. |
| historical | Sintesi del modello | Problema passato risolto; la seconda frase limita la conclusione agli estratti e non documenta problemi successivi. |
| opinion | Campo diretto | Quantità e periodo citati; opinione estranea omessa. |
| no_answer | Sintesi del modello | Mancanza limitata agli estratti, nessun importo o zero inventato. |

Durate client osservate, non benchmark comparativo: explicit 19,69 ms; unknown 24101,76 ms; conflict 2,29 ms; historical 14161,22 ms; opinion 2,82 ms; no_answer 4510,33 ms. Prima attesa lunga della sintesi unknown: 14104,23 ms; causa e stato freddo/caldo non determinati. Chunk non significa token, ASGI non misura il rendering del browser. Non è stata richiesta una nuova serie di tempi.

Nel Markdown allegato, il solo delimitatore sovraescapato attorno all'etichetta sintetica DATO NON VERIFICATO è stato normalizzato per leggere il JSON; significato e contenuto delle risposte restano quelli forniti. Non si attribuisce questa rappresentazione al backend senza prova.

## Controllo reale: non superato per ambito temporale

La fonte prevista è presente con file e righe e la risposta risulta terminata nell'interfaccia. Le date di pubblicazione coincidono con i passaggi consultati, la fotografia storica viene chiamata storica e non è inventata una scadenza di validità. Questi elementi sono favorevoli.

Rimane però un'unica formulazione indifferenziata per dati assenti oppure non verificati. La fonte distingue valori attuali non verificati nella nota e dati assenti nella fotografia storica. La parafrasi non conserva questa separazione e non rende esplicito il limite della nota per la frase sulle vendite. Non è dimostrato che la dashboard manchi di dati; la risposta non autorizza a concluderlo. Una citazione generica e l'avviso sotto la risposta non sostituiscono le qualifiche necessarie nella frase.

La verifica segue i criteri già emersi nel precedente controllo reale: non fondere ambiti temporali e non estendere all'esterno un limite dei materiali consultati. Consultati tests/evals/scorers/test_doc_qa.py upstream al commit c4da16e1ca3d21f4cc1905d4200063e564104f0f; il confronto lessicale e le citazioni non certificano da soli questi aspetti. Nessuna suite upstream completa eseguita in questa verifica.

## Stato dopo il controllo

Il collaudo richiesto è concluso con esito complessivo negativo. Nessun codice, parametro, dipendenza o dato del Mac modificato durante il test. Il backend locale, il recupero ottimizzato e la modalità estrattiva restano operativi; questo non approva la sintesi libera per tutti gli usi.

Un eventuale intervento successivo deve affrontare la rappresentazione e il controllo delle qualifiche temporali e dell'ambito delle affermazioni, con un caso sintetico che combini fotografia storica e dato corrente non verificato. Il problema non è risolto da un altro conteggio di citazioni né da una promessa di brevità. Nessuna correzione nuova è dichiarata completata.

Non vengono pubblicati screenshot, estratti personali o log integrali; nessuna dashboard o report esterno verificato. PR draft, non unire a main.
