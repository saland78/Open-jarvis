import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); vi.resetModules(); });

describe('personal local build', () => {
  it('ignores a saved external API URL and a build-time external override', async () => {
    vi.stubEnv('VITE_ANDREA_LOCAL', 'true');
    vi.stubEnv('VITE_API_URL', 'https://external.example');
    vi.stubGlobal('localStorage', { getItem: () => JSON.stringify({ apiUrl: 'https://saved.example' }) });
    const { getBase } = await import('./api');
    expect(getBase()).toBe('');
  });
  it('does not request analytics identity in the local build', async () => {
    vi.stubEnv('VITE_ANDREA_LOCAL', 'true');
    const fetcher = vi.fn();
    vi.stubGlobal('fetch', fetcher);
    const { initAnalytics } = await import('./analytics');
    await initAnalytics();
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('disables external leaderboard even when build credentials are supplied', async () => {
    vi.stubEnv('VITE_ANDREA_LOCAL', 'true');
    vi.stubEnv('VITE_SUPABASE_ANON_KEY', 'synthetic-public-key');
    const { LEADERBOARD_ENABLED, SUPABASE_ANON_KEY } = await import('./supabase');
    expect(LEADERBOARD_ENABLED).toBe(false);
    expect(SUPABASE_ANON_KEY).toBe('');
  });
  it('offers only the configured model even when Ollama also lists thinking models', async () => {
    vi.stubEnv('VITE_ANDREA_LOCAL', 'true');
    vi.stubGlobal('localStorage', { getItem: () => null });
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ data: [{id: 'qwen3:4b'}, {id: 'qwen-instruct'}] })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ model: 'qwen-instruct' }))));
    const { fetchModels } = await import('./api');
    expect(await fetchModels()).toEqual([{id: 'qwen-instruct'}]);
  });
  it('surfaces a streamed timeout instead of silently displaying an empty response', async () => {
    vi.stubEnv('VITE_ANDREA_LOCAL', 'true');
    vi.stubGlobal('localStorage', { getItem: () => null });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('data: {"error":{"message":"Timeout di prova"}}\n\ndata: [DONE]\n\n')));
    const { streamChat } = await import('./sse');
    const consume = async () => { for await (const _ of streamChat({ model: 'fixture', messages: [], stream: true })) { /* drain */ } };
    await expect(consume()).rejects.toThrow('Timeout di prova');
  });
  it('preserves source event identity across transport chunk boundaries', async () => {
    vi.stubEnv('VITE_ANDREA_LOCAL', 'true');
    vi.stubGlobal('localStorage', { getItem: () => null });
    const encoder = new TextEncoder();
    const body = new ReadableStream({ start(controller) {
      for (const part of ['event: local_sources\n', 'data: {"sources":[{"id":"N1"}]}\n\n', 'data: [DONE]\n\n']) controller.enqueue(encoder.encode(part));
      controller.close();
    }});
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body)));
    const { streamChat } = await import('./sse');
    const events = [];
    for await (const event of streamChat({ model: 'fixture', messages: [], stream: true })) events.push(event);
    expect(events).toEqual([{ event: 'local_sources', data: '{"sources":[{"id":"N1"}]}' }]);
  });
});
