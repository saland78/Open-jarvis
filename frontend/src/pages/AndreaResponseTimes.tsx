import type { BrowserTimes } from '../lib/andrea-browser-metrics';

const labels = { running: 'In corso', completed: 'Completata', truncated: 'Troncata',
  incomplete: 'Incompleta', cancelled: 'Interrotta', error: 'Errore' };
const ms = (value: number | null | undefined) => value == null ? 'Non disponibile' : `${Math.round(value)} ms`;

export function AndreaResponseTimes({ times, chat = false, ownerAway = false }: { times: BrowserTimes; chat?: boolean; ownerAway?: boolean }) {
  const rows = [
    ['Primo contenuto ricevuto dal browser', ms(times.firstContentMs)],
    ['Primo aggiornamento della risposta nell’interfaccia', ms(times.firstCommitMs)],
    ['Fine dello streaming nel browser', ms(times.totalStreamMs)],
    ['Aggiornamento finale dell’interfaccia', ms(times.settledCommitMs)],
    ...(!chat ? [['Recupero delle note nel backend', ms(times.server?.retrievalMs)]] : []),
    ['Primo testo inviato dal backend', ms(times.server?.firstTextMs)],
    ['Totale nel backend', ms(times.server?.totalMs)],
  ];
  return <details className="border border-[var(--color-border)] rounded-lg p-4" aria-label="Tempi della risposta">
    <summary className="cursor-pointer">Tempi della risposta · {labels[times.status]}</summary>
    <p className="my-2">Percorso: {chat ? 'Chat locale con modello' : times.inferenceUsed === true ? 'Sintesi con modello' : times.inferenceUsed === false ? 'Risposta senza inferenza' : 'Non ancora determinato'}.</p>
    <table className="w-full text-sm"><tbody>{rows.map(([label, value]) => <tr key={label}><th className="text-left font-normal pr-3 py-1">{label}</th><td className="py-1">{value}</td></tr>)}</tbody></table>
    <p className="text-sm mt-2">{chat ? 'I tempi del browser partono dall’invio della richiesta di chat.' : 'I tempi del browser partono dall’invio della richiesta di risposta, dopo la ricerca.'} L’aggiornamento UI misura il testo inserito nell’interfaccia, non il momento esatto in cui lo schermo lo disegna. I tempi del backend usano un altro orologio: non vanno sommati a quelli del browser.</p>
    {ownerAway ? <p className="text-sm mt-2">Durante la risposta hai aperto un’altra conversazione. I commit successivi non sono misurati; escludi questa richiesta dai confronti dell’interfaccia.</p> : null}
    {times.backgroundObserved ? <p className="text-sm mt-2">Scheda osservata in secondo piano: escludi questa richiesta dai confronti di latenza dell’interfaccia.</p> : null}
    {!times.server ? <p className="text-sm mt-2">Misure backend non correlate o non ancora disponibili.</p> : times.server.status !== times.status ? <p className="text-sm mt-2">Stato backend distinto: {times.server.status || 'Non disponibile'}.</p> : null}
    <p className="text-sm mt-2">{chat ? 'Le ultime 50 misure di chat' : 'Le ultime 50 osservazioni'} restano in memoria nel browser, senza testo delle richieste o delle risposte. Ricaricare la pagina le cancella. Non certificano la qualità della risposta.</p>
    <details className="mt-2"><summary className="cursor-pointer">Dati numerici di questa richiesta</summary><pre className="text-xs whitespace-pre-wrap break-words mt-2">{JSON.stringify(times, null, 2)}</pre></details>
  </details>;
}
