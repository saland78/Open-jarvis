# Fork personale: base separata e prima integrazione

Repository di lavoro: https://github.com/saland78/Open-jarvis

Sorgente: https://github.com/open-jarvis/OpenJarvis

Base importata: `c4da16e1ca3d21f4cc1905d4200063e564104f0f`, 1 ottobre 2026. Fork GitHub completo con storia originale, licenza Apache-2.0 e relazione upstream. `main` conserva la sorgente; le personalizzazioni iniziali sono su `feature/andrea-local-profile`. L'altra repository Jarvis rimane separata.

## Cosa è pronto

- Sorgente completa del progetto, non una ricostruzione dei suoi moduli.
- Profilo `profiles/andrea-local.toml`: Ollama loopback, modello non thinking 4B, italiano, risposte brevi, porta API 8008, agente semplice e ambiente iniziale senza memoria automatica, scheduler, apprendimento, skill discovery o analytics esterni.
- Permessi runtime abilitati con default deny, senza bypass locali. Il profilo shared concede una baseline upstream di lettura/rete/memoria in assenza di policy esplicita: non è una sandbox senza accessi. Prima dei connettori reali definire radici e policy specifiche e verificarle.

Il caricamento della configurazione è verificato usando il codice upstream reale. Il profilo da solo non realizza l'isolamento dei dati o dell'ambiente: l'avvio deve impostare anche i percorsi e gestire le variabili ereditate.

## Avvio da preparare e collaudare

La prima installazione sul Mac va guidata in una nuova cartella, con un Terminale identificato esplicitamente. Non sovrascrivere la cartella del Jarvis esistente. Non copiare il suo `.env`, il suo SQLite o il vault nel fork.

Per un launcher ripetibile servono:

1. Python supportato (3.10–3.13; preferire 3.12), uv e verifica dell'estensione Rust `openjarvis_rust`. Installare le dipendenze server con il lock upstream; costruire o installare l'estensione nativa con la procedura upstream prima dell'avvio protetto.
2. `OPENJARVIS_HOME` in una cartella dati nuova, fuori dalla sorgente e distinta da `~/.jarvis-local` e da eventuali installazioni OpenJarvis precedenti.
3. `OPENJARVIS_CONFIG` al percorso assoluto di `profiles/andrea-local.toml`, prima di importare moduli OpenJarvis; `JARVIS_NUM_CTX=4096` nell'ambiente del processo.
4. Ambiente di esecuzione senza credenziali cloud ereditate o importate. `engine.default=ollama` e `--engine ollama` non bastano: `jarvis serve` può costruire un MultiEngine se trova credenziali cloud. Il controllo versioni CLI effettua inoltre una richiesta esterna se non viene usato `--quiet`.
5. Porta API 8008 e, per l'interfaccia upstream, porta frontend 5178. Verificare occupazione e identità del processo; non terminare processi generici sulla sola porta.
6. Verificare modello, streaming, timeout, annullamento e gestione errori prima di dichiarare funzionante la chat. Nessun benchmark reale sul Mac è stato eseguito per il fork.

Non usare ancora questo profilo come sostituzione del Jarvis funzionante. I campi max_tokens e temperatura dell'intelligence non sostituiscono i valori predefiniti della richiesta HTTP: il client deve inviare esplicitamente il budget concordato. Il modello indicato è non thinking; il comportamento effettivo va verificato nella richiesta Ollama.

## Prossime integrazioni, in ordine

1. Launcher isolato e ciclo chat locale, con test su errori e cancellazione.
2. Obsidian in sola lettura: estratti dal corpo, citazioni con percorsi/righe, stato delle note, aggiornamenti ed eliminazioni. Il connettore upstream non va considerato equivalente alla correzione sviluppata nell'altro Jarvis senza verificarlo.
3. Memoria esplicita e revocabile. Migrare soltanto attraverso esportazione/importazione con schema e provenienza, mai copiando il vecchio database in una posizione prevista da un altro schema.
4. Skill personali adattate al formato supportato e provate su casi sintetici. Nessuna importazione indiscriminata o sincronizzazione automatica.
5. Strumenti, scheduler e feedback dopo i controlli del ciclo base, con permessi e limiti specifici.

Il fork rende tutti i componenti disponibili; la prima configurazione attiva solo quelli necessari al collaudo. Aggiungere funzioni non dimostra minore latenza: confrontare prima risposta, totale, qualità e fonti a parità di modello e carico.

## Stato dei controlli

Ambiente di sviluppo Linux, Python 3.12: installazione delle dipendenze server con `uv sync --locked --extra server --no-dev` completata. Verifica esplicita `RUST_AVAILABLE=False`: l'estensione Rust non è presente nell'ambiente di prova, quindi l'avvio con capability enforcement non è ancora validato. Non disabilitare i controlli per nascondere questo requisito. Caricamento del profilo e isolamento dei percorsi verificati, senza usare note, account o ricordi reali. Questo non prova l'inferenza Ollama, il frontend, le integrazioni o l'installazione sul Mac Intel.

Il fork è pubblico, come il progetto di origine. Non committare configurazioni locali, percorsi del vault, conversazioni, chiavi, email, ricordi, database o audio. La licenza originale rimane integra; documentare ogni modifica ai moduli upstream.
