# Verifica Mac della riduzione del lavoro di ricerca — 2026-10-01

## Esito

L'aggiornamento update_search_work.py pubblicato nel commit 4dcf62d49b50091153c8a3842e295896808e12b1 è installato sul Mac: tre file sorgenti fissati al commit 7342b2257bc4b1de4a1dee476a15ddb05267c73a, hash verificati e backup creato. Il riavvio è riuscito. Non sono modificate configurazioni, dipendenze, note o database da questo aggiornamento.

Nel browser, la stessa domanda naturale sulla nota KPI nominata restituisce 320 risultati, 364 note controllate, 14 note escluse e la fonte attiva prevista al primo posto con le righe originali. Durata di questa ricerca: 1427 ms; la precedente singola rilevazione era 3304 ms. Il conteggio e l'estratto mostrato mantengono il risultato già controllato. Lo screenshot e il testo privato non sono pubblicati.

La successiva raccolta nel Terminale ripete il comando precedente: tre chat brevissime e tre sintesi con notes-query "kpi self publishing". Tutte le sei richieste hanno done true, finishReason stop e stato completed. Le tre ricerche sulle note sono complete, usano una fonte e answerMode model_synthesis con inferenceUsed true. answer e usage sono null: non sono conservate risposte o estratti e non viene ricavato un nuovo verdetto semantico da contenuti scartati.

**Il controllo previsto per questo aggiornamento è concluso:** installazione, riavvio, ricerca nell'interfaccia e raccolta dei tempi completati. Sono risultati dei percorsi esaminati; non certificano tutte le sintesi o ogni fonte del vault.

## Confronto delle mediane, tre prove per percorso

| Misura | Prima | Dopo |
|---|---:|---:|
| Ricerca/preparazione delle note | 1895,92 ms | 810,26 ms |
| Primo testo client della sintesi | 2046,98 ms | 963,42 ms |
| Totale client della sintesi | 25785,20 ms | 24346,53 ms |
| Primo testo client della chat brevissima | 154,43 ms | 150,04 ms |
| Totale client della chat brevissima | 387,31 ms | 354,97 ms |

La ricerca/preparazione mostra una riduzione osservata del 57,26%; l'attesa mediana del primo testo sulle note del 52,93%. Non sono garanzie generali su ogni richiesta o stime di percentili. La chat brevissima non usa il recupero delle note; le sue piccole variazioni non vengono attribuite alla modifica.

## Sei misure dopo l'aggiornamento

| Percorso/prova | Primo testo client, ms | Totale client, ms | Ricerca/preparazione, ms | Primo testo dal via della generazione, ms | Percorso di generazione, ms |
|---|---:|---:|---:|---:|---:|
| Chat 1 | 6654,90 | 6864,60 | — | 6637,06 | 6847,61 |
| Chat 2 | 146,78 | 351,63 | — | 145,10 | 351,59 |
| Chat 3 | 150,04 | 354,97 | — | 148,10 | 353,93 |
| Note 1 | 13089,98 | 36299,44 | 810,26 | 12278,04 | 35488,20 |
| Note 2 | 963,42 | 18354,11 | 812,75 | 149,05 | 17540,48 |
| Note 3 | 948,05 | 24346,53 | 801,13 | 145,32 | 23544,58 |

Nelle seconde e terze richieste sulle note, il primo testo segue il via della generazione di circa 145–149 ms; il recupero, circa 0,8 secondi, rimane parte dell'attesa iniziale. La prima richiesta di chat attende circa 6,65 secondi e la prima sintesi circa 13,09 secondi. Causa e stato freddo/caldo non sono determinati.

## Interpretazione e limiti

- La durata totale della sintesi diminuisce meno dell'attesa iniziale: mediana 24,35 secondi. Le durate di generazione variano e non sono state modificate da questo intervento; il cambiamento del totale non è attribuito interamente al recupero.
- Tre prove prima e tre dopo, in sequenza, non isolano tutte le condizioni del sistema. La misura conferma un beneficio osservato in questo collaudo, insieme alla riduzione deterministica degli estratti preparati nei test sintetici.
- La prima scansione nel browser e le successive misure nel Terminale sono contesti diversi; il valore 1427 ms non si mescola alla mediana server di 810,26 ms.
- I tempi client provengono dal Terminale. ASGI non misura il rendering del browser. Il percorso di generazione comprende routing e trasporto, non soltanto il calcolo puro del modello.
- I chunk delle sintesi sono 194, 147 e 195: non sono token. Non viene calcolato un throughput senza usage; il testo scartato non consente di confrontare lunghezza o qualità delle risposte.
- La baseline precedente resta in [latency-baseline-2026-10-01.md](latency-baseline-2026-10-01.md). Il controllo semantico separato e i suoi limiti restano in [quality-review-2026-10-01.md](quality-review-2026-10-01.md).
- Consultato nuovamente tests/telemetry/test_phase_metrics_new.py upstream al commit c4da16e1ca3d21f4cc1905d4200063e564104f0f. È consultato, non si dichiara eseguita la sua suite completa o attivata telemetria energetica.
- Modello, prompt, contesto e massimo 512 token restano invariati. Nessun dato esterno KDP è verificato e il modello non è addestrato da questa modifica.

## Direzione successiva

Il recupero è migliorato nel collaudo previsto. Il punto successivo riguarda contenuto, lunghezza e contesto della sintesi, mantenendo fonti, conflitti, limiti e segnalazione del troncamento. La generazione e le prime attese lunghe richiedono interventi distinti basati su misure; non si deduce la loro causa da questa raccolta. La pipeline vocale resta una funzione futura.

Nessun altro test di questa raccolta è richiesto. PR draft, senza unione a main; Jarvis originale separato.
