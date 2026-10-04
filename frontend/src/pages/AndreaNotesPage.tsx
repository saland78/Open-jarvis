// Personal fork: explicit local read-only notes, separate from upstream ingestion.
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { authHeaders, getBase } from '../lib/api';
import { streamChat } from '../lib/sse';
import { useAppStore } from '../lib/store';
import { BrowserNoteMeasurement, type BrowserTimes } from '../lib/andrea-browser-metrics';
import { AndreaResponseTimes } from './AndreaResponseTimes';

interface Source {
  id?: string; path: string; title: string; status: string; text: string;
  startLine: number; endLine: number; modifiedAt: string; eligible: boolean;
  passages?: { text: string; startLine: number; endLine: number }[];
}
interface VaultStatus { available: boolean; configured: boolean; vault?: string; detail?: string }
interface SearchResult { query: string; results: Source[]; scanned: number; total: number; excluded: number; partial: boolean; skipped: number; elapsedMs: number }
interface Evidence { answerMode?: string; inferenceUsed?: boolean; query: string; sources: Source[]; excluded: number; partial: boolean; selectionScope?: string; synthesisPath?: string }
interface Note { path: string; title: string; text: string; status: string; modifiedAt: string }

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(getBase() + path, { ...options, headers: authHeaders({ 'Content-Type': 'application/json' }), cache: 'no-store' });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Richiesta non riuscita (${res.status}).`);
  return data;
}
const field = 'w-full rounded-lg border border-[var(--color-border)] px-3 py-2 bg-transparent min-w-0';
const button = 'rounded-lg border border-[var(--color-border)] px-3 py-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed';

export function AndreaNotesPage() {
  const [status, setStatus] = useState<VaultStatus | null>(null);
  const [folder, setFolder] = useState('');
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<SearchResult | null>(null);
  const [note, setNote] = useState<Note | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [answer, setAnswer] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [times, setTimes] = useState<BrowserTimes | null>(null);
  const controller = useRef<AbortController | null>(null);
  const metricsController = useRef<AbortController | null>(null);
  const observed = useRef<{ id: number; measurement: BrowserNoteMeasurement } | null>(null);
  const revision = useRef(0);
  const model = useAppStore(s => s.selectedModel);

  useEffect(() => {
    const abort = new AbortController();
    request<VaultStatus>('/api/andrea/notes/status', { signal: abort.signal })
      .then(data => { if (!abort.signal.aborted) { setStatus(data); setFolder(data.vault || ''); } })
      .catch(err => { if (!abort.signal.aborted) setError(err.message); });
    const visibility = () => observed.current?.measurement.visibility(document.visibilityState === 'visible');
    document.addEventListener('visibilitychange', visibility);
    return () => {
      abort.abort(); observed.current?.measurement.finish('cancelled');
      controller.current?.abort(); metricsController.current?.abort(); revision.current += 1;
      document.removeEventListener('visibilitychange', visibility);
    };
  }, []);

  useLayoutEffect(() => {
    const current = observed.current;
    if (current?.id === revision.current && (answer || times?.status !== 'running' && times)) {
      if (current.measurement.commit(Boolean(answer.trim()), document.visibilityState === 'visible')) {
        setTimes(current.measurement.snapshot());
      }
    }
  }, [answer, times?.status]);

  function start(kind: string) {
    observed.current?.measurement.finish('cancelled');
    controller.current?.abort();
    metricsController.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    const id = ++revision.current;
    setBusy(kind); setError('');
    return { abort, id };
  }
  function failed(err: unknown, abort: AbortController, id: number) {
    if (!abort.signal.aborted && id === revision.current) setError(err instanceof Error ? err.message : 'Operazione non riuscita.');
  }
  function finished(id: number) { if (id === revision.current) setBusy(''); }

  async function configure(value: string) {
    const { abort, id } = start('config');
    try {
      const data = await request<VaultStatus>('/api/andrea/notes/config', { method: 'POST', body: JSON.stringify({ vault: value }), signal: abort.signal });
      if (id !== revision.current) return;
      setStatus(data); setFolder(data.vault || ''); setResult(null); setNote(null); setEvidence(null); setAnswer(''); setTimes(null);
    } catch (err) { failed(err, abort, id); } finally { finished(id); }
  }
  async function search() {
    const { abort, id } = start('search');
    setResult(null); setNote(null); setEvidence(null); setAnswer(''); setTimes(null);
    try {
      const data = await request<SearchResult>('/api/andrea/notes/search?q=' + encodeURIComponent(query.trim()), { signal: abort.signal });
      if (id === revision.current) setResult(data);
    } catch (err) { failed(err, abort, id); } finally { finished(id); }
  }
  async function read(path: string) {
    const { abort, id } = start('read');
    setNote(null);
    try {
      const data = await request<Note>('/api/andrea/notes/read?path=' + encodeURIComponent(path), { signal: abort.signal });
      if (id === revision.current) setNote(data);
    } catch (err) { failed(err, abort, id); } finally { finished(id); }
  }
  async function summarize(brief = false, structured = false, notePath?: string) {
    if (!result) return;
    const measurement = new BrowserNoteMeasurement(undefined, document.visibilityState === 'visible');
    const { abort, id } = start('summary');
    observed.current = { id, measurement };
    setAnswer(''); setEvidence(null); setNote(null); setTimes(measurement.snapshot());
    let text = '';
    let done = false;
    let reason: unknown = null;
    try {
      for await (const event of streamChat({ model, messages: [{ role: 'user', content: result.query }], stream: true, notes_query: result.query, notes_brief: brief, notes_structured: structured,
        ...(notePath ? { notes_path: notePath } : {}) }, abort.signal,
        { headers: requestId => measurement.headers(requestId), done: () => { done = true; } })) {
        if (id !== revision.current) break;
        const data = JSON.parse(event.data);
        if (event.event === 'local_sources') {
          setEvidence(data); measurement.mode(data.answerMode, data.inferenceUsed);
        } else {
          if (data.choices?.[0]?.finish_reason) reason = data.choices[0].finish_reason;
          if (data.choices?.[0]?.delta?.content) {
            measurement.content(); text += data.choices[0].delta.content; setAnswer(text);
          }
        }
      }
      measurement.finish(abort.signal.aborted || id !== revision.current ? 'cancelled' : 'success', done, reason);
      if (!text && !abort.signal.aborted) setError('Nessun testo ricevuto per la risposta.');
      else if (id === revision.current && ['incomplete', 'truncated'].includes(measurement.snapshot().status)) setError('Risposta incompleta o troncata: non considerarla conclusa.');
    } catch (err) {
      measurement.finish(abort.signal.aborted || id !== revision.current ? 'cancelled' : 'error'); failed(err, abort, id);
    } finally {
      if (id === revision.current) {
        setTimes(measurement.snapshot());
        // Correlation is a separate read: it never delays text or retries generation.
        const metricsAbort = new AbortController(); metricsController.current = metricsAbort;
        void request<{ records: unknown[] }>('/api/andrea/metrics', { signal: metricsAbort.signal })
          .then(data => { if (id === revision.current && !metricsAbort.signal.aborted) { measurement.correlate(data.records); setTimes(measurement.snapshot()); } })
          .catch(() => { /* Missing server correlation stays explicitly unavailable. */ });
      }
      finished(id);
    }
  }
  function stop() {
    observed.current?.measurement.finish('cancelled');
    if (observed.current) setTimes(observed.current.measurement.snapshot());
    controller.current?.abort(); metricsController.current?.abort(); revision.current += 1;
    setBusy(''); setError('Risposta interrotta. Gli eventuali estratti e il testo parziale restano visibili.');
  }
  const canSummarize = Boolean(result?.results.some(s => s.eligible));
  const missingCitations = !['structured_refused', 'structured_abstained'].includes(evidence?.answerMode || '') && busy !== 'summary' && answer && evidence && !evidence.sources.some(s => answer.includes(`[${s.id}]`));
  const unknownCitations = busy !== 'summary' ? answer.match(/\[N\d+\]/g)?.filter(id => !evidence?.sources.some(s => `[${s.id}]` === id)) || [] : [];

  return (
    <section className="flex-1 overflow-y-auto min-w-0 p-4 md:p-8" aria-label="Note Obsidian">
      <div className="max-w-4xl mx-auto flex flex-col gap-5 min-w-0">
        <header className="pl-10 md:pl-0"><h1 className="text-2xl font-semibold">Note Obsidian</h1><p className="mt-2">Ricerca e lettura locale. Le note non vengono modificate.</p></header>
        <form className="flex flex-col gap-2" onSubmit={e => { e.preventDefault(); void configure(folder); }}>
          <label htmlFor="vault-folder">Cartella della banca dati</label>
          <input id="vault-folder" className={field} value={folder} onChange={e => setFolder(e.target.value)} placeholder="Incolla il percorso completo della cartella" disabled={Boolean(busy)} />
          <div className="flex flex-wrap gap-2"><button className={button} disabled={!folder.trim() || Boolean(busy)}>Collega cartella in sola lettura</button>{status?.configured ? <button type="button" className={button} disabled={Boolean(busy)} onClick={() => void configure('')}>Scollega</button> : null}</div>
          <p role="status" className="break-words">{status?.available ? `Cartella collegata: ${status.vault}` : status?.detail || 'Controllo della cartella…'}</p>
        </form>
        <form className="flex flex-col gap-2" onSubmit={e => { e.preventDefault(); void search(); }}>
          <label htmlFor="notes-query">Cerca nelle note Obsidian</label>
          <div className="flex gap-2"><input id="notes-query" className={field} maxLength={200} value={query} onChange={e => setQuery(e.target.value)} disabled={!status?.available || Boolean(busy)} /><button className={button} disabled={!status?.available || !query.trim() || Boolean(busy)}>{busy === 'search' ? 'Ricerca…' : 'Cerca note'}</button></div>
        </form>
        {error ? <p role="alert" className="rounded-lg border p-3">{error}</p> : null}
        {result ? <section aria-label="Risultati della ricerca" className="flex flex-col gap-3">
          <p>{result.total} risultati · {result.scanned} note controllate · {result.elapsedMs} ms</p>
          {result.partial ? <p>Ricerca parziale: raggiunto un limite di scansione. Non sono state controllate tutte le note.</p> : null}
          {result.skipped > 0 ? <p>{result.skipped} file non accessibili, collegati o troppo grandi saltati.</p> : null}
          {result.excluded > 0 ? <p>{result.excluded} note con stato non attivo, ambiguo o senza contenuto escluse dal riassunto.</p> : null}
          {result.results.map(s => <article key={s.path} className="border border-[var(--color-border)] rounded-lg p-4 min-w-0">
            <h2 className="font-semibold">{s.title}</h2><p className="text-sm break-words">{s.path} · righe {s.startLine}–{s.endLine} · stato dichiarato: {s.status}</p>
            <pre className="whitespace-pre-wrap break-words font-sans mt-2">{s.text || 'Nota senza corpo utilizzabile.'}</pre>
            <button className={button + ' mt-3'} disabled={Boolean(busy)} onClick={() => void read(s.path)}>Leggi nota</button>
            {s.eligible && s.status === 'active' ? <button className={button + ' mt-3 ml-2'} disabled={!model || Boolean(busy)} onClick={() => void summarize(false, true, s.path)}>Sintesi della nota</button> : null}
          </article>)}
          {result.total === 0 ? <p>Nessuna corrispondenza. Prova una parola diversa.</p> : null}
          {!canSummarize && result.total > 0 ? <p>Nessuna fonte attiva con contenuto utilizzabile per il riassunto.</p> : null}
          <div className="flex flex-wrap gap-2"><button className={button} disabled={!canSummarize || !model || Boolean(busy)} onClick={() => void summarize(true)}>Passaggi brevi dalle fonti</button><button className={button} disabled={!canSummarize || !model || Boolean(busy)} onClick={() => void summarize(false, true)}>Sintesi strutturata</button><button className={button} disabled={!canSummarize || !model || Boolean(busy)} onClick={() => void summarize()}>Sintesi libera del modello</button></div>
          <p>I passaggi brevi conservano il testo originale e il suo contesto. La sintesi strutturata viene mostrata dopo i controlli di formato, fonti e date; può ancora contenere errori di significato. Entrambe le sintesi vanno confrontate con le fonti.</p>
          <p>“Sintesi della nota” usa solo la nota scelta: profilo del libro e date, oppure conteggio dei titoli e qualifiche KPI datate, nei formati riconosciuti. È una selezione parziale dei fatti.</p>
          {!model ? <p>La ricerca funziona senza inferenza. Per la sintesi libera serve il modello locale configurato.</p> : null}
        </section> : null}
        {busy === 'summary' ? <div className="flex gap-3 items-center"><p role="status">Jarvis sta elaborando gli estratti…</p><button className={button} onClick={stop}>Interrompi risposta</button></div> : null}
        {times ? <AndreaResponseTimes times={times} /> : null}
        {answer || evidence ? <section aria-label="Riassunto delle fonti" className="border border-[var(--color-border)] rounded-lg p-4 flex flex-col gap-3">
          <h2 className="font-semibold">{evidence?.answerMode === 'structured_synthesis' ? 'Sintesi strutturata da verificare' : evidence?.answerMode === 'structured_refused' ? 'Sintesi strutturata non mostrata' : evidence?.answerMode === 'structured_abstained' ? 'Astensione dalla sintesi' : evidence?.answerMode === 'status_scope_quotes' ? 'Qualifiche datate dalle fonti' : evidence?.answerMode === 'brief_quotes' ? 'Passaggi brevi dalle fonti' : 'Risposta di Jarvis'}</h2><p className="whitespace-pre-wrap break-words">{answer || (evidence?.answerMode === 'structured_synthesis' ? 'Elaborazione e controlli in corso. Il testo compare solo dopo i controlli.' : 'In attesa del primo testo…')}</p>
          {evidence?.selectionScope === 'selected_note_facts' ? <p>La sintesi riguarda soltanto i fatti selezionati della nota scelta. La risposta indica le eventuali frasi riportate dalla fonte; gli altri punti sono sintesi del modello. Le intestazioni con le date delle qualifiche provengono dalla nota. I controlli tecnici non certificano il significato della risposta. Nessun dato verificato su sistemi esterni.</p> : null}
          <p>{evidence?.answerMode === 'status_scope_quotes' ? 'Protezione attiva: nessuna sintesi del modello generata. Intestazioni ed etichette sono copiate dagli estratti e possono riguardare dati diversi. Leggi le note per il contesto completo; nessun dato esterno verificato.' : evidence?.answerMode === 'brief_quotes' ? 'Questi passaggi sono copiati dalle fonti, senza generazione del modello. Sono una selezione parziale degli estratti, non una verifica dei dati o una risposta esaustiva.' : 'La risposta usa estratti, non le note intere. I conteggi riconosciuti e le frasi indicate come riprese dalla fonte possono essere riportati direttamente; gli altri punti sono sintesi del modello da verificare. Una citazione non dimostra che il dato della fonte sia vero o aggiornato.'}</p>
          {missingCitations || unknownCitations.length > 0 ? <p role="alert">Le citazioni della risposta sono mancanti o non corrispondono alle fonti fornite. Il riassunto va verificato.</p> : null}
          {evidence?.excluded ? <p>{evidence.excluded} note non utilizzabili escluse.</p> : null}
          {evidence?.partial ? <p>Anche le fonti del riassunto provengono da una ricerca parziale.</p> : null}
          {evidence?.sources.map(s => <article key={s.id} className="border-t pt-3">
            <h3 className="font-semibold">[{s.id}] {s.title}</h3><p className="text-sm break-words">{s.path}{s.passages ? '' : ` · righe ${s.startLine}–${s.endLine}`} · stato dichiarato: {s.status}</p>
            <p className="text-sm">{s.passages ? 'Passaggi originali separati' : 'Estratto consultato per la risposta'}; il file risultava aggiornato a: {s.modifiedAt}</p>
            {s.passages ? s.passages.map((p, i) => <div key={i}><p className="text-sm">Righe {p.startLine}–{p.endLine}</p><pre className="whitespace-pre-wrap break-words font-sans my-2">{p.text}</pre></div>) : <pre className="whitespace-pre-wrap break-words font-sans my-2">{s.text}</pre>}
            <button className={button} disabled={Boolean(busy)} onClick={() => void read(s.path)}>Leggi nota aggiornata</button>
          </article>)}
        </section> : null}
        {note ? <section aria-label="Lettura nota" className="border border-[var(--color-border)] rounded-lg p-4 min-w-0">
          <div className="flex flex-wrap justify-between gap-3"><h2 className="font-semibold">{note.title}</h2><button className={button} onClick={() => setNote(null)}>Chiudi nota</button></div>
          <p className="break-words">{note.path} · stato dichiarato: {note.status}</p><p className="text-sm my-2">Questa lettura mostra il file attuale. Può differire dall'estratto usato per una risposta precedente.</p>
          <pre className="whitespace-pre-wrap break-words font-mono text-sm">{note.text}</pre>
        </section> : null}
      </div>
    </section>
  );
}
