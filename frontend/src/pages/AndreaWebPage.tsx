import { useEffect, useRef, useState } from 'react';

type Provider = 'duckduckgo' | 'youcom';
type Source = { title: string; url: string; snippet: string };
export type SearchResult = { provider: Provider; providerLabel: string; query: string; consultedAt: string; elapsedMs: number; sources: Source[]; pagesFetched: false; modelUsed: false; automaticRetries: 0 };

export function safeSearchLink(url: string): boolean {
  try { const parsed = new URL(url); return parsed.protocol === 'https:' && !parsed.username && !parsed.password; }
  catch { return false; }
}

export async function webRequest(query: string, provider: Provider, signal: AbortSignal): Promise<SearchResult> {
  const response = await fetch('/api/andrea/web/search', {
    method: 'POST', cache: 'no-store', signal,
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query, provider }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `Ricerca non riuscita (${response.status})`);
  return data;
}

export function WebResults({ result }: { result: SearchResult }) {
  return <section aria-label="Risultati web" className="space-y-4">
    <h2 className="text-lg font-semibold">Risultati per: {result.query}</h2>
    <p>{result.providerLabel} · {result.elapsedMs} ms · {new Date(result.consultedAt).toLocaleString('it-IT')}</p>
    <p>Risultati del motore di ricerca. Le pagine non sono state lette da Jarvis; nessuna sintesi del modello generata. Titoli ed estratti possono essere incompleti o non aggiornati.</p>
    {result.sources.length === 0 && <p>Nessun risultato restituito dal fornitore per questa ricerca.</p>}
    <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
      {result.sources.map(source => <article key={source.url} className="border rounded-xl p-4 space-y-3 min-w-0" style={{ background: 'var(--color-bg-secondary)' }}>
        <h3 className="font-semibold break-words">{source.title}</h3>
        <p className="break-words whitespace-pre-wrap">{source.snippet || 'Estratto non disponibile. Apri la fonte per consultarla.'}</p>
        {safeSearchLink(source.url) && <a className="underline break-all" href={source.url} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">Apri fonte: {source.url}</a>}
      </article>)}
    </div>
  </section>;
}

export function AndreaWebPage() {
  const [query, setQuery] = useState('');
  const [provider, setProvider] = useState<Provider>('duckduckgo');
  const [result, setResult] = useState<SearchResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const controller = useRef<AbortController | null>(null);
  const generation = useRef(0);
  useEffect(() => () => { generation.current += 1; controller.current?.abort(); }, []);
  const search = async () => {
    if (controller.current) return;
    const current = new AbortController(); controller.current = current;
    const sequence = ++generation.current;
    setPending(true); setError(''); setResult(null);
    const deadline = window.setTimeout(() => current.abort(), 30000);
    try {
      const data = await webRequest(query.trim(), provider, current.signal);
      if (sequence === generation.current) setResult(data);
    } catch (e) {
      if (sequence === generation.current) setError(current.signal.aborted ? 'Ricerca interrotta o scaduta. Nessun altro fornitore è stato contattato.' : e instanceof Error ? e.message : 'Ricerca non disponibile');
    } finally {
      window.clearTimeout(deadline);
      if (sequence === generation.current) { controller.current = null; setPending(false); }
    }
  };
  return <main className="p-6 overflow-y-auto h-full space-y-5" style={{ color: 'var(--color-text)' }}>
    <h1 className="text-xl font-semibold">Ricerca web</h1>
    <p>Il testo che scrivi qui viene inviato soltanto al fornitore scelto. Note, memoria e conversazioni non vengono aggiunte alla ricerca.</p>
    <form className="space-y-3 max-w-2xl" onSubmit={e => { e.preventDefault(); void search(); }}>
      <label className="block">Fornitore<select className="w-full border rounded p-2 bg-transparent" disabled={pending} value={provider} onChange={e => setProvider(e.target.value as Provider)}>
        <option value="duckduckgo">DuckDuckGo</option><option value="youcom">You.com — prova gratuita</option>
      </select></label>
      {provider === 'youcom' && <p>Profilo MCP gratuito destinato alla valutazione. Disponibilità e limiti dipendono da You.com; nessuna chiave o pagamento configurato.</p>}
      <label className="block">Testo da inviare<input className="w-full border rounded p-2 bg-transparent" required maxLength={200} disabled={pending} value={query} onChange={e => setQuery(e.target.value)} placeholder="Scrivi una ricerca pubblica" /></label>
      <button className="border rounded px-3 py-2" type="submit" disabled={pending || !query.trim()}>{pending ? 'Ricerca in corso…' : 'Cerca sul web'}</button>
      {pending && <button className="ml-3 border rounded px-3 py-2" type="button" onClick={() => controller.current?.abort()}>Interrompi ricerca</button>}
    </form>
    {error && <p role="alert" className="text-red-500">{error}</p>}
    {pending && <p role="status">Attendo il fornitore scelto…</p>}
    {result && <WebResults result={result} />}
  </main>;
}
