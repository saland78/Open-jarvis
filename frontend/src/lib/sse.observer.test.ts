import { afterEach, describe, expect, it, vi } from 'vitest';
import { BrowserNoteMeasurement } from './andrea-browser-metrics';
vi.mock('./api', () => ({ getBase: () => '', authHeaders: (headers: object) => headers }));
import { streamChat } from './sse';
const payload = { model: 'fixture', messages: [{ role: 'user', content: 'SYNTHETIC_QUERY' }], stream: true as const };
afterEach(() => vi.unstubAllGlobals());

describe('optional SSE measurement observer', () => {
  it('preserves split Unicode text and source events while reporting ID and DONE exactly once', async () => {
    const body = 'event: local_sources\ndata: {"answerMode":"brief_quotes","sources":[]}\n\n' +
      'data: {"choices":[{"delta":{"content":"Città."}}]}\n\n' +
      'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n';
    const bytes = new TextEncoder().encode(body);
    const stream = new ReadableStream({ start(controller) { for (const byte of bytes) controller.enqueue(new Uint8Array([byte])); controller.close(); } });
    const fetcher = vi.fn().mockResolvedValue(new Response(stream, { headers: { 'x-openjarvis-request-id': 'a'.repeat(32) } }));
    vi.stubGlobal('fetch', fetcher); const headers = vi.fn(); const done = vi.fn(); const events = [];
    for await (const event of streamChat(payload, undefined, { headers, done })) events.push(event);
    expect(events).toHaveLength(3); expect(events[0].event).toBe('local_sources');
    expect(JSON.parse(events[1].data).choices[0].delta.content).toBe('Città.');
    expect(headers).toHaveBeenCalledExactlyOnceWith('a'.repeat(32)); expect(done).toHaveBeenCalledOnce();
    expect(fetcher).toHaveBeenCalledOnce(); expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual(payload);
  });

  it('does not report DONE on an error or on an EOF missing the completion marker', async () => {
    for (const body of ['data: {"error":{"message":"Synthetic timeout"}}\n\n', 'data: {"choices":[{"delta":{"content":"Partial."}}]}\n\n']) {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body))); const done = vi.fn();
      try { for await (const _ of streamChat(payload, undefined, { done })) { /* consume */ } } catch { /* expected SSE error */ }
      expect(done).not.toHaveBeenCalled();
    }
  });

  it('observes HTTP headers on failure but still surfaces the existing HTTP error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"detail":"Synthetic refusal"}', { status: 400, headers: { 'x-openjarvis-request-id': 'b'.repeat(32) } })));
    const headers = vi.fn(); const done = vi.fn();
    const consume = async () => { for await (const _ of streamChat(payload, undefined, { headers, done })) { /* consume */ } };
    await expect(consume()).rejects.toThrow('Synthetic refusal');
    expect(headers).toHaveBeenCalledExactlyOnceWith('b'.repeat(32)); expect(done).not.toHaveBeenCalled();
  });

  it('joins real parsed SSE events with a content-free measurement without confusing sources with first text', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('event: local_sources\ndata: {"answerMode":"status_scope_quotes","text":"PRIVATE_SOURCE"}\n\ndata: {"choices":[{"delta":{"content":"PRIVATE_ANSWER"}}]}\n\ndata: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n', { headers: { 'x-openjarvis-request-id': 'c'.repeat(32) } })));
    let time = 0; const m = new BrowserNoteMeasurement(() => time); let done = false; let reason;
    for await (const event of streamChat(payload, undefined, { headers: id => m.headers(id), done: () => { done = true; } })) {
      const data = JSON.parse(event.data); time += 10;
      if (event.event === 'local_sources') { m.mode(data.answerMode); expect(m.snapshot().firstContentMs).toBeNull(); }
      else { if (data.choices[0].delta.content) m.content(); if (data.choices[0].finish_reason) reason = data.choices[0].finish_reason; }
    }
    m.finish('success', done, reason); time += 10; m.commit(true, true);
    expect(m.snapshot()).toMatchObject({ firstContentMs: 20, firstCommitMs: 40, status: 'completed', inferenceUsed: false });
    expect(JSON.stringify(m.snapshot())).not.toContain('PRIVATE');
  });
});
