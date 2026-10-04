# Correzione dell'avvio dello script di confronto

## Esito osservato

Il 2026-10-04 il primo avvio sul Mac della prova isolata si è fermato con `NameError: name 'SYNTHETIC_ORDINARY' is not defined`. La versione pubblicata al commit `2e8ac5f8a975ec1dfecb75944c0d5273540dc6aa`, checksum `72bd2b65bfceb69dcfbb596bd53b575b016945cf0081642ee7e23ea020e8dfc0`, è ritirata per questo errore di avvio. Nessuna delle quattro richieste del confronto era stata inviata: la preparazione dei casi si interrompeva prima della costruzione del trasporto. Nessun file di OpenJarvis, nota, database, profilo o dipendenza modificato. La latenza e la qualità della candidata restano non misurate sul Mac.

## Causa e correzione

Le costanti `SYNTHETIC_ORDINARY`, `SYNTHETIC_ADVERSARIAL` e `CRITERIA` erano presenti nel file, ma dopo il blocco `if __name__ == '__main__'` che chiamava `main()`. I test precedenti importavano il modulo: quel blocco veniva saltato e le costanti diventavano disponibili prima di chiamare le funzioni. Il lancio diretto con `python script.py progetto` esercitava invece l'ordine sbagliato. L'errore è stato riprodotto con il lancio diretto della stessa versione, prima di modificarla.

Il blocco di avvio è ora l'ultima istruzione del file. La candidata, i testi sintetici, il modello, l'ordine A/B e B/A, i limiti, gli hash della produzione, i validatori e le soglie del 20% restano identici. È aggiunta la modalità `--check-only`, che verifica gli undici sorgenti e prepara entrambi i casi senza rete o inferenza. È alternativa a `--native-only`; il comando normale conserva le quattro richieste previste e l'interruzione al primo errore tecnico.

SHA-256 dello script corretto: `f2a07935fd413412dbb3b71a49f4a69731fab923470900ab62d05af13c27fddd` (26079 byte). Verificare questo valore prima di eseguire il file scaricato.

Non basta compilare la sintassi o importare il modulo per certificare il suo avvio. Sono aggiunti due controlli con un nuovo processo Python:

- Lancio diretto con `--check-only`: undici hash verificati, due casi pronti, nessuna rete/inferenza/modifica, esiti qualità e prestazioni non valutati.
- Lancio diretto con lo stesso schema di comando dato ad Andrea, senza opzioni: quattro richieste HTTP a un simulatore locale sulla porta predefinita, tutti i quattro fatti nelle risposte finali, nessun retry o modifica ai file verificati. La porta viene prima occupata dal simulatore: se non è disponibile, il test si ferma senza inviare richieste a un eventuale altro servizio.

Questi controlli eseguono davvero `__main__` e avrebbero rilevato l'ordine precedente. Il simulatore non usa Ollama o note personali e i suoi numeri non sono un benchmark.

## Verifiche concluse e limite

I **18 test della prova isolata** passano, inclusi i due nuovi lanci in un processo separato, i precedenti controlli di contratto, prove originali, date, numeri, limiti, soglie e trasporto HTTP. Nessuna modifica al ponte, ai guard installati o alla candidata di sintesi; nessun nuovo collaudo della qualità necessario per correggere il solo avvio. Restano da effettuare le quattro richieste sintetiche reali inizialmente previste, non una ripetizione di un confronto già concluso.

Prima della correzione è stato verificato il branch del fork e consultati nuovamente upstream [test_structured_output.py](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/engine/test_structured_output.py) e [test_standalone_security.py](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/cli/test_standalone_security.py). I test dei launcher mantengono distinti avvio, cablaggio e inferenza; i nuovi controlli qui coprono anche il processo Python reale. Nessuna intera suite upstream eseguita.

Per riprendere sul Mac: lasciare OpenJarvis acceso e usare soltanto il Terminale Controlli per scaricare e verificare la versione corretta. Eseguire poi una volta lo script normale. Nessuna installazione, rebuild o riavvio di OpenJarvis necessario. PR #1 resta draft e non unita; Jarvis originale rimane indipendente.
