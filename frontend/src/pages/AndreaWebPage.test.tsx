import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AndreaWebPage, WebResults, webRequest, safeSearchLink, PageEvidence, pageRequest, type SearchResult, type PageRead, type PageSummary } from './AndreaWebPage';
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

const page: PageRead = { pageId: 'token', sourceId: 'W1', url: 'https://example.com/manual', title: 'Manuale', text: 'Testo originale <script>non eseguire</script>.', partial: true, consultedAt: result.consultedAt, readMs: 100, redirects: 0, modelUsed: false };
const summary: PageSummary = { outcome: 'accepted_pending_semantic_review', claims: [{ text: 'Una sintesi.', quote: 'Testo originale <script>non eseguire</script>.' }], pageId: 'token', sourceId: 'W1', generationAndChecksMs: 5000, qualityVerdict: 'pending_review', automaticRetries: 0 };
describe('explicit selected page', () => {
  it('sends only the selected URL or page token and question, no local context', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => page }); vi.stubGlobal('fetch', fetch);
    await pageRequest('read', { url: page.url }, new AbortController().signal);
    await pageRequest('summarize', { pageId: page.pageId, question: 'Riassumi' }, new AbortController().signal);
    expect(fetch.mock.calls[0][0]).toBe('/api/andrea/web/read');
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ url: page.url });
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({ pageId: 'token', question: 'Riassumi' });
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it('shows quotes safely and distinguishes technical acceptance from meaning', () => {
    const html = renderToStaticMarkup(<PageEvidence page={page} summary={summary} />);
    expect(html).toContain('Passaggio originale'); expect(html).toContain('non dimostrano');
    expect(html).toContain('primi 6000 caratteri'); expect(html).toContain('[W1]');
    expect(html).not.toContain('<script>');
  });
  it('does not expose a rejected model claim', () => {
    const html = renderToStaticMarkup(<PageEvidence page={page} summary={{ ...summary, outcome: 'rejected', reason: 'unsupported_number', claims: [{ text: 'FAKE CLAIM', quote: 'FAKE QUOTE' }] }} />);
    expect(html).not.toContain('FAKE CLAIM'); expect(html).not.toContain('FAKE QUOTE');
    expect(html).toContain('Sintesi non mostrata'); expect(html).toContain('unsupported_number');
  });
  it('requires an explicit page action and never fetches during initial rendering', () => {
    const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
    renderToStaticMarkup(<AndreaWebPage />);
    expect(fetch).not.toHaveBeenCalled();
    expect(renderToStaticMarkup(<WebResults result={result} onRead={() => {}} />)).toContain('Leggi pagina in Jarvis');
  });
});
