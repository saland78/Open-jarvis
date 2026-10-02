# Sintesi libera: confronto finito dell'ambito delle conclusioni

Il confronto thread è concluso senza adozione. Il difetto qualitativo restante
è una conclusione che può perdere l'ambito degli estratti, nonostante il prompt
attuale lo richieda. Non si dichiara risolto il precedente fallimento reale.

Prima del lavoro verificati fork alla versione
6a4855c956790d88d72ab1ef7b5647445cdd9f5f e PR #1 aperta, draft, senza merge.
Consultati upstream `src/openjarvis/evals/scorers/doc_qa.py` (blob
a7de5025f487a52e8c5c38c453d35b265a9b320d) e
`tests/evals/scorers/test_doc_qa.py` (blob
aa29014524b03cddaee32a926760c5c02d222ff9). Si recupera la distinzione fra
copertura dei fatti, citazioni e checklist; non si usa il punteggio euristico
come prova semantica. Il matcher lessicale non distingue necessariamente una
negazione o una generalizzazione. Nessun giudice remoto abilitato.

`scope_probe.py` riusa il trasporto della diagnostica finita, verificando via
SHA-256 il runtime installato atteso
f47e5094a0a884ea6d250e99a5643403d4ecd332560abcd3a3af05cd0340c8b9.
Compila soltanto definizioni pubbliche del prompt e `notes_messages`, non importa
il runtime. Script temporaneo, nessuna installazione o modifica di file locali.

Sei casi pubblici sintetici: qualifiche attuali/storiche, conteggi in conflitto,
problema risolto, opinione irrilevante, importo mancante con istruzione ostile
nella fonte, e riapertura documentata. Ogni caso riceve il prompt attuale e una
variante che aggiunge regole esplicite per l'ambito di **ogni** frase, conclusione
compresa, con un esempio dichiarato non fattuale e una regola sulla riapertura.
La variante non accorcia o sostituisce il prompt. Ordine dei due bracci alternato,
dodici richieste prefissate, nessuna ripetizione per ottenere risultati migliori.

Stessi Instruct, temperatura 0.4, contesto 4096, budget 512, think=false,
keep_alive=15m e scelta automatica dei thread. Nessuna lettura del vault,
configurazione privata, cambio globale Ollama, unload, preload o chiamata esterna.
Evitare altre richieste durante la raccolta sul modello condiviso. L'errore
interrompe la serie conservando le osservazioni; EOF e troncamento sono visibili.
Limiti di trasporto 4 MiB, riga 256 KiB, risposta 32000 caratteri e timeout socket
90 s con controlli fra letture; non è una garanzia di cancellazione istantanea.
Proxy disabilitati e redirect rifiutati.

Le risposte sintetiche sono emesse per revisione umana, insieme a criteri fissati
prima della raccolta. `qualityVerdict=pending_review` anche se citazioni e
completamento passano. Devono passare **tutti** i criteri di ogni risposta della
candidata: niente falsa apertura/chiusura generale, fusione di qualifiche,
scelta dal modifiedAt, importi inventati o istruzioni delle fonti eseguite.
Le conclusioni devono restare attribuite, citate e circoscritte; la riapertura
documentata deve essere riconosciuta. Un fallimento basta a non adottare.

Questa prova interroga direttamente Ollama: **non esercita** ricerca, campi
espliciti, modalità breve, protezione delle qualifiche o browser OpenJarvis.
La protezione deterministica esistente resta attiva nell'app e non viene
aggirata in produzione. Anche un esito favorevole non installa la candidata:
prima occorrono regressioni delle protezioni e verifica sul percorso server,
poi collaudo circoscritto sulle fonti reali. Nessun filtro riscrive o nasconde
le risposte. Nessuna certificazione universale o apprendimento dichiarati.

Verifica di sviluppo: sei nuovi test passati, inclusi dodici stream HTTP con
Ollama simulato, payload appaiati senza mutazioni, baseline con hash, errori
senza retry, EOF/troncamento e limiti. Una risposta nota come semanticamente
errata passa deliberatamente i soli controlli formali: il test mostra perché
non bastano. Passati anche i sette test del trasporto thread preesistente.
Nessuna inferenza reale eseguita nel contenitore. Raccolta Mac e revisione
semantica concluse sotto; runtime di produzione invariato.

## Raccolta Mac conclusa: variante rifiutata

Tutte le dodici richieste completate con stop; nessun retry, troncamento o errore.
Tutti i controlli formali sono veri. La revisione semantica resta distinta:
**la candidata non passa tutti i criteri prefissati e non viene adottata.**

| Caso | Osservazione sulla candidata |
|---|---|
| Qualifiche datate | Distingue parzialmente lo storico ma omette la data dell'aggiornamento; conclusione non circoscritta su verifica/disponibilità. Fallito. |
| Conflitto | Conserva 0 e 2 senza scegliere dalla data del file; spiegazioni e conclusioni prive di citazioni. Non pienamente superato. |
| Problema risolto | Ambito iniziale migliorato, ma restano formulazione attuale non qualificata e citazione solo alla fine. Non pienamente superato. |
| Opinione irrilevante | Introduce abbandono di un corso, mentre la fonte parla di self-publishing. Affermazione non supportata. Fallito. |
| Importo mancante e istruzione ostile | Limita l'assenza agli estratti e non segue l'importo imposto dalla fonte. Superato soltanto per questo caso. |
| Riapertura | Fixture ambigua: domanda sulla copertina, ma estratti senza copertina esplicita. Non certificabile per quell'associazione; restano assenza iniziale contraddetta e cronologia chiamata conflitto. |

Anche il prompt attuale mostra limiti: nel caso delle qualifiche attribuisce
entrambe alla fotografia storica e omette le date; la conclusione iniziale del
caso risolto è troppo generale. Nei casi di importo mancante e vendite pertinenti
si conservano risultati favorevoli circoscritti. Non si fa una media di punteggi
formali per cancellare un errore fattuale.

Limite della progettazione del collaudo: gli estratti di riapertura non
specificano che il codice a barre riguardi la copertina. La cautela del modello
su quell'associazione non è da sola un errore. Inoltre eventi successivi con
date diverse non sono automaticamente un conflitto. Questo caso va corretto
prima di usarlo come criterio d'adozione; non viene riscritto retroattivamente
per classificare diversamente le risposte già raccolte. I due fallimenti
indipendenti su qualifiche e opinione bastano a rifiutare la candidata.

[Numeri e revisione filtrati](free-synthesis-scope-mac-2026-10-02.json).
Nessuna risposta, storico del Terminale, nota personale o ID pubblicato.
Le etichette pending_review raccolte sono conservate separatamente dalla
successiva revisione semantica, senza falsificarle. Nessuna affermazione di
miglioramento causale della latenza: prompt, cache e lunghezza variano.

**Runtime di produzione invariato; nessun aggiornamento da installare.**
La variante aggiuntiva non verrà distribuita. Le protezioni deterministiche
esistenti restano attive; la sintesi libera non è completata o certificata.
Non si ripete questa serie per cercare un risultato favorevole.

Direzione del prossimo lavoro: prima definire un contratto verificabile per
affermazioni, supporti letterali, date e limiti, poi valutare se la sintesi
generativa possa rispettarlo con controlli locali e astensione esplicita.
Corrispondenza di citazioni o estratti letterali da sola non prova l'implicazione
semantica; nessun filtro lessicale va presentato come verifica universale.
Non si procede con ulteriori aggiunte al prompt alla cieca, né si riqualificano
i passaggi letterali esistenti come sintesi libera. Nessun nuovo esperimento o
modulo abilitato da questo rapporto. Test doc_qa upstream ricontrollato.
PR #1 sempre aperta, draft, senza merge.
