# Esito del collaudo locale dei riassunti — 2026-10-01

## Stato

La suite di accuratezza **non è superata**. Il prompt installato proviene dal commit 30a32f82c559345c1a960627bc5d961975e6cef1; l'aggiornatore è pubblicato nel commit 648799093aff63b1dfcbe3f28f4ace7d02cbd220.

Sei casi sintetici sono stati eseguiti sul Mac con qwen3:4b-instruct-2507-q4_K_M. Usano il prompt di produzione e gli estratti immutati di scripts/andrea/quality_cases.json. Non leggono il vault: il valore di due copie nel caso opinion è un dato sintetico, non una verifica delle vendite personali.

| Caso | Criteri fissati | Revisione del significato |
|---|---|---|
| explicit | Rispettati | Due libri, data e citazione corretti. |
| unknown | Rispettati | Dato non verificato limitato all'estratto; nessuno zero né indisponibilità dei dati esterni. |
| conflict | Non rispettati | Riporta 0 e 2 e cita entrambe le fonti, ma nega il conflitto perché le schede sono separate. La fonte non fornisce questa giustificazione. |
| historical | Rispettati | Descrive la risoluzione e limita l'assenza di problemi successivi agli estratti. Confermato anche nel controllo del singolo caso. |
| opinion | Rispettati, con un difetto aggiuntivo | Riporta due copie e settembre 2026, non introduce il 90% e attribuisce la valutazione. Tuttavia trasforma l'abbandono del self-publishing in abbandono di corsi; la frase finale sui contesti esterni è inoltre ambigua. |
| no_answer | Rispettati | Royalty di ottobre non determinabili dagli estratti, senza inventare importi. |

I criteri non sono stati modificati dopo le risposte. Cinque casi rispettano i criteri specifici originali, ma questo non cancella il contenuto non sostenuto dalla fonte nel caso opinion. La revisione complessiva resta negativa.

Tutti i sei stream sono completi, non troncati e superano i controlli formali sulle citazioni. Questo esito di protocollo non certifica l'accuratezza; qualityVerdict rimane pending_review nel raccoglitore.

## Misure raccolte

Primo testo al client: 1,35–2,07 secondi. Totale: 4,06–13,14 secondi. Sono durate di queste sei risposte diverse, misurate nel Terminale; non includono ricerca nel vault o rendering del browser. Stato freddo/caldo non determinato. Non sono un confronto fra chat e riassunto sulle note né una misura della futura pipeline vocale.

## Consultazione dell'upstream

Riferimento esaminato: open-jarvis/OpenJarvis, commit c4da16e1ca3d21f4cc1905d4200063e564104f0f.

- examples/doc_qa/doc_qa.py indicizza documenti e invoca Jarvis.ask con contesto.
- src/openjarvis/evals/scorers/doc_qa.py verifica corrispondenze di parole, presenza delle citazioni e una checklist opzionale. La corrispondenza di parole può approvare affermazioni semanticamente false; un modello giudice non è una prova indipendente della verità.

Il collegamento a documenti e l'esistenza dei test upstream non risolvono automaticamente i difetti osservati del modello locale.

## Vincoli per il prossimo intervento

Non ripetere la suite invariata per cercare una risposta favorevole. Non dichiarare il collaudo concluso. Non cambiare criteri, conteggi o modello per nascondere il fallimento.

Prima di un'altra installazione occorre progettare una risposta basata su evidenze controllabili: distinguere fatti espliciti, conflitti irrisolti, opinioni e dati non verificati, conservando citazioni ed estratti. I controlli automatici sulle forme o sui numeri devono dichiarare il proprio ambito; non possono essere presentati come una verifica generale del significato.

La parte già collaudata di collegamento, ricerca e lettura del vault rimane utile. La sintesi libera del modello non è ancora affidabile in tutti questi casi. Jarvis originale e configurazione locale restano separati. Nessuna nota personale o esportazione del vault è inclusa in questo documento.
