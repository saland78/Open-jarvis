import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AndreaMemoryPage, memoryRequest } from './AndreaMemoryPage';

afterEach(() => vi.unstubAllGlobals());
describe('explicit local memory', () => {
  it('reads only the local same-origin endpoint without browser caching', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ revision: 0, records: [] }) });
    vi.stubGlobal('fetch', fetch);
    expect((await memoryRequest()).records).toEqual([]);
    expect(fetch.mock.calls[0][0]).toBe('/api/andrea/memory');
    expect(fetch.mock.calls[0][1]).toMatchObject({ method: 'GET', cache: 'no-store', body: undefined });
  });
  it('sends reviewed content and its revision without adding permissions or inference', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ revision: 4, records: [] }) });
    vi.stubGlobal('fetch', fetch);
    const payload = { action: 'update', revision: 3, id: 'synthetic-id', record: { kind: 'correction', topic: 'Colore', text: 'Blu', active: true } };
    await memoryRequest(payload);
    const request = fetch.mock.calls[0][1];
    expect(request.method).toBe('POST');
    expect(JSON.parse(request.body)).toEqual(payload);
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it('preserves conflict errors instead of retrying or reporting a save', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: false, status: 409, json: async () => ({ detail: 'Ricarica e confronta prima di salvare.' }) });
    vi.stubGlobal('fetch', fetch);
    await expect(memoryRequest({ action: 'delete', revision: 1, id: 'old' })).rejects.toThrow('Ricarica e confronta');
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it('discloses declared provenance, bounded use and the distinction from training', () => {
    const html = renderToStaticMarkup(<AndreaMemoryPage />);
    expect(html).toContain('non addestra il modello');
    expect(html).toContain('8 voci e 2400');
    expect(html).toContain('senza verifica esterna');
    expect(html).toContain('Le sintesi delle note Obsidian usano soltanto le loro fonti');
  });
});
