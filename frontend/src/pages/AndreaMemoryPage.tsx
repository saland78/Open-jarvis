import { useEffect, useState } from 'react';

type Entry = { id: string; kind: string; topic: string; text: string; active: boolean; createdAt: number; updatedAt: number };
type Snapshot = { revision: number; records: Entry[]; limits: { saved: number; active: number; contextChars: number } };
type Draft = Pick<Entry, 'kind' | 'topic' | 'text' | 'active'>;
const empty = (): Draft => ({ kind: 'preference', topic: '', text: '', active: false });
const labels: Record<string, string> = { preference: 'Preferenza', fact: 'Fatto dichiarato', correction: 'Correzione' };

export async function memoryRequest(payload?: unknown): Promise<Snapshot> {
  const response = await fetch('/api/andrea/memory', {
    method: payload === undefined ? 'GET' : 'POST', cache: 'no-store',
    headers: payload === undefined ? {} : { 'Content-Type': 'application/json' },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `Errore memoria (${response.status})`);
  return data;
}

export function AndreaMemoryPage() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [draft, setDraft] = useState<Draft>(empty);
  const [editing, setEditing] = useState<Entry | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const reload = async () => {
    setPending(true); setError('');
    try { setSnapshot(await memoryRequest()); }
    catch (e) { setError(e instanceof Error ? e.message : 'Memoria non disponibile'); }
    finally { setPending(false); }
  };
  useEffect(() => { void reload(); }, []);
  const save = async (remove?: Entry) => {
    if (!snapshot) return;
    setPending(true); setError(''); setNotice('');
    const payload = remove ? { action: 'delete', revision: snapshot.revision, id: remove.id }
      : editing ? { action: 'update', revision: snapshot.revision, id: editing.id, record: draft }
      : { action: 'create', revision: snapshot.revision, record: draft };
    try {
      setSnapshot(await memoryRequest(payload));
      if (!remove || editing?.id === remove.id) { setDraft(empty()); setEditing(null); }
      setDeleting(null);
      setNotice(remove ? 'Voce eliminata dalla memoria. Le conversazioni precedenti possono ancora contenerla: usa una nuova chat per il confronto.' : 'Voce salvata. Il modello non è stato addestrato.');
    } catch (e) { setError(e instanceof Error ? e.message : 'Salvataggio non riuscito'); }
    finally { setPending(false); }
  };
  const inputClass = 'w-full rounded-md border p-2 bg-transparent';
  return <main className="p-6 overflow-y-auto h-full space-y-5" style={{ color: 'var(--color-text)' }}>
    <h1 className="text-xl font-semibold">Memoria e correzioni</h1>
    <p>Salvi tu ogni voce. Le voci attive vengono inviate a Ollama locale in ogni nuova richiesta della chat, fino a 8 voci e 2400 caratteri di contesto. Le sintesi delle note Obsidian usano soltanto le loro fonti.</p>
    <p>Questi sono dati dichiarati da te, senza verifica esterna. Salvare una correzione non addestra il modello e non garantisce che la applichi: la sua risposta va verificata. Non salvare password o credenziali.</p>
    <button type="button" disabled={pending} className="border rounded px-3 py-2" onClick={() => void reload()}>Ricarica memoria</button>
    {error && <p role="alert" className="text-red-500">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {snapshot && <>
      <p>{snapshot.records.length} voci salvate · {snapshot.records.filter(r => r.active).length} attive · revisione {snapshot.revision}</p>
      <form className="space-y-3 max-w-2xl border rounded-lg p-4" onSubmit={e => { e.preventDefault(); void save(); }}>
        <h2 className="font-semibold">{editing ? `Modifica: ${editing.topic}` : 'Nuova voce'}</h2>
        <label className="block">Tipo<select className={inputClass} value={draft.kind} disabled={pending} onChange={e => setDraft({ ...draft, kind: e.target.value })}>
          {Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select></label>
        <label className="block">Argomento<input className={inputClass} required maxLength={80} disabled={pending} value={draft.topic} onChange={e => setDraft({ ...draft, topic: e.target.value })} /></label>
        <label className="block">Testo<textarea className={inputClass} rows={4} required maxLength={500} disabled={pending} value={draft.text} onChange={e => setDraft({ ...draft, text: e.target.value })} /></label>
        <label className="flex gap-2"><input type="checkbox" checked={draft.active} disabled={pending} onChange={e => setDraft({ ...draft, active: e.target.checked })} />Usa nelle chat</label>
        <p>Un solo argomento attivo per voce: modifica la voce esistente per correggerla. Argomenti diversi possono comunque contenere contraddizioni da controllare.</p>
        <button disabled={pending} className="border rounded px-3 py-2" type="submit">{pending ? 'Attendi…' : 'Salva voce'}</button>
        {editing && <button type="button" disabled={pending} className="ml-3 border rounded px-3 py-2" onClick={() => { setEditing(null); setDraft(empty()); }}>Annulla modifica</button>}
      </form>
      <section className="space-y-3" aria-label="Voci della memoria">
        {snapshot.records.length === 0 && <p>Nessuna voce salvata. Le conversazioni non vengono trasformate automaticamente in memoria.</p>}
        {snapshot.records.map(record => <article key={record.id} className="border rounded-lg p-4 space-y-2 max-w-2xl">
          <h2 className="font-semibold">{record.topic}</h2>
          <p>{labels[record.kind]} · {record.active ? 'Attiva nelle chat' : 'Salvata, non inviata al modello'} · Dichiarazione dell’utente</p>
          <p className="whitespace-pre-wrap break-words">{record.text}</p>
          <p className="text-sm">Aggiornata: {new Date(record.updatedAt * 1000).toLocaleString('it-IT')}</p>
          <button type="button" disabled={pending} className="border rounded px-3 py-2" onClick={() => { setEditing(record); setDraft({ kind: record.kind, topic: record.topic, text: record.text, active: record.active }); setNotice(''); }}>Modifica</button>
          <button type="button" disabled={pending} className="ml-3 border rounded px-3 py-2" onClick={() => setDeleting(record.id)}>Elimina</button>
          {deleting === record.id && <div><p>Eliminare questa voce dalla memoria? Le vecchie conversazioni restano separate.</p>
            <button type="button" disabled={pending} className="border rounded px-3 py-2" onClick={() => void save(record)}>Conferma eliminazione</button>
            <button type="button" disabled={pending} className="ml-3 border rounded px-3 py-2" onClick={() => setDeleting(null)}>Annulla</button></div>}
        </article>)}
      </section>
    </>}
  </main>;
}
