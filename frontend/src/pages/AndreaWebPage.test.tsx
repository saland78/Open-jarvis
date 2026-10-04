import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AndreaWebPage, WebResults, webRequest, safeSearchLink, type SearchResult } from './AndreaWebPage';
afterEach(() => vi.unstubAllGlobals());
const result: SearchResult = { provider: 'duckduckgo', providerLabel: 'DuckDuckGo HTML', query: 'public query', consultedAt: '2026-10-04T20:33:00Z', elapsedMs: 800, sources: [{ title: '<script>run()</script>', url: 'https://docs.python.org/a', snippet: '' }], pagesFetched: false, modelUsed: false, automaticRetries: 0 };
describe('explicit web search', () => {
  it('sends only query and provider to the local route, once', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => result }); vi.stubGlobal('fetch', fetch);
    const signal = new AbortController().signal;
    await webRequest('public query', 'duckduckgo', signal);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe('/api/andrea/web/search');
    expect(fetch.mock.calls[0][1]).toMatchObject({ signal, cache: 'no-store', method: 'POST' });
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ query: 'public query', provider: 'duckduckgo' });
  });
  it('does not retry failures or select an alternate provider', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: false, json: async () => ({ detail: 'blocked' }) }); vi.stubGlobal('fetch', fetch);
    await expect(webRequest('x', 'youcom', new AbortController().signal)).rejects.toThrow('blocked');
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it('shows public source text safely, missing snippet and provider time', () => {
    const html = renderToStaticMarkup(<WebResults result={result} />);
    expect(html).toContain('&lt;script&gt;'); expect(html).not.toContain('<script>');
    expect(html).toContain('Estratto non disponibile'); expect(html).toContain('800 ms');
    expect(html).toContain('noopener noreferrer'); expect(html).toContain('nessuna sintesi del modello');
  });
  it('refuses executable links and preserves explicit empty results', () => {
    expect(safeSearchLink('javascript:alert(1)')).toBe(false);
    expect(safeSearchLink('https://user:password@example.com/')).toBe(false);
    expect(renderToStaticMarkup(<WebResults result={{ ...result, sources: [] }} />)).toContain('Nessun risultato restituito');
  });
  it('discloses external sending and separates notes memory and conversation', () => {
    const html = renderToStaticMarkup(<AndreaWebPage />);
    expect(html).toContain('Note, memoria e conversazioni non vengono aggiunte');
    expect(html).toContain('You.com — prova gratuita'); expect(html).toContain('DuckDuckGo');
    expect(html).toContain('Testo da inviare');
  });
});
