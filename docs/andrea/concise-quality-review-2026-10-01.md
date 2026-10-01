# Revisione dei sei casi con sintesi breve — 2026-10-01

## Esito del controllo di qualità

Dopo l'installazione di update_concise.py dal commit 722748cec97254f69f778f9b4d51a90be59b9fb4, tre file fissati al commit 519b0d085cf302ac38155986a32c5dc4e64a1911, hash e backup sono confermati sul Mac. Il server locale risponde HTTP 200 e il vault risulta disponibile in sola lettura.

Il primo tentativo del collaudo era interrotto prima della prima risposta, con porta 8008 non raggiungibile; non produce un esito semantico e non viene contato come suite fallita o riuscita. Dopo il ripristino della disponibilità del server è stata eseguita una suite completa.

**I sei casi della suite completa sono superati nella revisione del significato rispetto ai criteri originali.** Tutti i controlli formali sono veri, gli stream completati senza troncamento. Dataset e criteri sono confrontati con quality_cases.json pubblicato e restano invariati. qualityVerdict rimane pending_review nel raccoglitore: questa revisione documentata è distinta dai controlli automatici.

| Caso | Percorso | Revisione |
|---|---|---|
| explicit | explicit_fields | Due libri, fotografia al 2026-08-20, mercati dichiarati e citazione N1; nessun conteggio aggiunto. |
| unknown | model_synthesis | Dato non verificato limitato all'estratto, senza zero, indisponibilità esterna o presunto report mai scaricato; citazione N1. |
| conflict | explicit_fields | 0 e 2 restano discordanti, citate entrambe le fonti, nessuna scelta tramite data del file. |
| historical | model_synthesis | Problema del codice a barre descritto come risolto e copertina corretta disponibile dalla data della fonte; la frase successiva limita i problemi non documentati agli estratti. Citazione N1. |
| opinion | explicit_fields | Due copie nel settembre 2026 riportate come dichiarazione della nota sintetica con N1; nessuna percentuale estranea. |
| no_answer | model_synthesis | Royalty di ottobre non determinabili dagli estratti; nessuno zero, importo inventato o estensione del limite alle informazioni esterne. Citazione N1. |

Tre risposte usano campi espliciti senza inferenza; tre usano il modello Instruct locale. I casi di conteggio diretto non provano l'obbedienza del modello al nuovo stile. Nessun dato di vendita reale o report KDP è verificato: tutte le fonti della suite sono sintetiche, già pubblicate.

## Tempi e lunghezza di questa esecuzione

| Caso | Primo testo client, ms | Totale client, ms | Parole approssimative | Inferenza |
|---|---:|---:|---:|---|
| explicit | 19,98 | 20,04 | 26 | No |
| unknown | 14850,76 | 21261,09 | 34 | Sì |
| conflict | 1,98 | 2,12 | 53 | No |
| historical | 2209,80 | 12357,71 | 38 | Sì |
| opinion | 2,75 | 2,82 | 26 | No |
| no_answer | 1813,51 | 7733,26 | 25 | Sì |

Le tre sintesi del modello hanno due frasi e 25–38 parole, contando semplicemente le parti separate da spazi, incluse le citazioni. Il conteggio non è tokenizzazione. L'etichetta tra virgolette del caso unknown è presentata con escape nel testo incollato; nella lettura semantica è la stessa etichetta DATO NON VERIFICATO e non cambia i criteri o i fatti.

Questi tempi non includono la ricerca nelle note reali: gli estratti sintetici sono forniti al backend. Le durate differenti dei casi non costituiscono una misura controllata del beneficio sul riassunto reale. L'attesa di circa 14,85 secondi del primo caso con modello è osservata; causa e stato freddo/caldo non sono determinati. usage è null e i chunk non vengono trattati come token.

Consultati nuovamente quality_cases.json del commit installato e tests/evals/scorers/test_doc_qa.py upstream al commit c4da16e1ca3d21f4cc1905d4200063e564104f0f. Il controllo formale delle citazioni resta separato dalla lettura del significato; l'intera suite upstream non viene dichiarata eseguita.

## Stato del collaudo previsto

Installazione, disponibilità del server e sei casi di qualità sono confermati. Restano la raccolta confrontabile di tre chat brevi e tre sintesi con la stessa ricerca, poi un riassunto della nota reale confrontato con gli estratti. Non si dichiara ancora superato il criterio di miglioramento del tempo totale o conclusa la verifica della nuova modifica.

La baseline precedente resta in [search-work-mac-review-2026-10-01.md](search-work-mac-review-2026-10-01.md). La preparazione e i criteri del nuovo intervento restano in [concise-synthesis-2026-10-01.md](concise-synthesis-2026-10-01.md). I precedenti fallimenti semantici non vengono cancellati o riclassificati.

Sono risultati dei sei esempi, non una certificazione di ogni sintesi, di informazioni esterne o di apprendimento. Non sono pubblicati il file incollato, storia del Terminale, note personali o screenshot. PR draft; nessuna unione a main. Il modello e Jarvis originale restano invariati.
