// Hook/callback harness for the real submit path. No claim of real browser paint.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
const h = vi.hoisted(() => ({ states: [] as unknown[], refs: [] as { current: unknown }[], si: 0, ri: 0,
  stream: vi.fn(), store: {} as any, subscribers: new Set<(s: any) => void>(), nextId: 0 }));
vi.mock('react', () => ({
  useState: (initial: unknown) => { const i = h.si++; if (!(i in h.states)) h.states[i] = initial;
    return [h.states[i], (value: unknown) => { h.states[i] = value; }]; },
  useRef: (initial: unknown) => h.refs[h.ri++] ||= { current: initial },
  useEffect: () => {}, useCallback: (callback: unknown) => callback,
}));
vi.mock('../../lib/store', () => ({
  generateId: () => `fixture-${++h.nextId}`,
  useAppStore: Object.assign((selector: (s: any) => unknown) => selector(h.store), {
    getState: () => h.store,
    subscribe: (listener: (s: any) => void) => { h.subscribers.add(listener); return () => h.subscribers.delete(listener); },
  }),
}));
vi.mock('../../lib/sse', () => ({ streamChat: h.stream, streamResearch: vi.fn() }));
vi.mock('../../lib/api', () => ({ getBase: () => '', fetchSavings: () => Promise.resolve({}) }));
vi.mock('../../hooks/useSpeech', () => ({ useSpeech: () => ({ state: 'idle', available: false }) }));
vi.mock('sonner', () => ({ toast: { error: vi.fn() } }));
import { InputArea } from './InputArea';
import { chatTimes } from '../../lib/andrea-chat-metrics';

function render() { h.si = 0; h.ri = 0; return InputArea(); }
function element(tree: any, title: string): any {
  if (Array.isArray(tree)) return tree.map(t => element(t, title)).find(Boolean);
  if (tree?.props) {
    if (tree.props.title === title) return tree;
    return element(tree.props.children, title);
  }
}
function send() { h.states[0] = 'synthetic request'; return element(render(), 'Send message').props.onClick() as Promise<void>; }
function gate() { let release!: () => void; const promise = new Promise<void>(r => { release = r; }); return { release, promise }; }
async function flush() { for (let i = 0; i < 20; i++) await Promise.resolve(); }
const chunk = (content = '', reason?: string) => ({ data: JSON.stringify({ choices: [{ delta: { content }, finish_reason: reason }] }) });

beforeEach(() => {
  vi.useFakeTimers(); vi.stubEnv('VITE_ANDREA_LOCAL', 'true'); h.states = []; h.refs = []; h.nextId = 0;
  h.subscribers.clear(); h.stream.mockReset();
  vi.stubGlobal('document', { visibilityState: 'visible', addEventListener: vi.fn(), removeEventListener: vi.fn() });
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"records":[]}')));
  h.store = { activeId: `owner-${Math.random()}`, selectedModel: 'fixture', streamState: { isStreaming: false }, messages: [],
    settings: { speechEnabled: false, maxTokens: 512, temperature: 0.4 }, models: [], deepResearch: false,
    setDeepResearch: vi.fn(), setSavings: vi.fn(), addLogEntry: vi.fn(), setLiveEnergy: vi.fn(),
    addMessage: (_id: string, message: any) => { h.store.messages.push(message); },
    updateLastAssistant: vi.fn((_id, content) => { h.store.messages.at(-1).content = content; }),
    setStreamState: (patch: object) => { Object.assign(h.store.streamState, patch); },
    resetStream: () => { h.store.streamState = { isStreaming: false }; },
  };
});
afterEach(() => { vi.clearAllTimers(); vi.useRealTimers(); vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

describe('local general chat measurement wiring', () => {
  it('consumes DONE after stop, sends only one generation, and keeps timings out of persisted messages', async () => {
    h.stream.mockImplementation(async function* (_request, _signal, observer) {
      observer.headers('a'.repeat(32)); yield chunk('Synthetic answer.'); yield chunk('', 'stop'); observer.done();
    });
    await send(); await flush();
    expect(chatTimes(h.store.activeId, 'fixture-2')?.times).toMatchObject({ status: 'completed', requestId: 'a'.repeat(32), firstCommitMs: null });
    expect(h.store.messages.at(-1).content).toBe('Synthetic answer.');
    expect(JSON.stringify(h.store.messages)).not.toContain('requestId');
    expect(h.stream).toHaveBeenCalledOnce(); expect(h.subscribers.size).toBe(0);
    expect(vi.mocked(fetch).mock.calls.filter(([url]) => String(url).includes('/api/andrea/metrics'))).toHaveLength(1);
  });

  it.each([['stop', 'incomplete'], ['length', 'truncated']])('labels EOF with %s as %s', async (reason, status) => {
    h.stream.mockImplementation(async function* () { yield chunk('Partial'); yield chunk('', reason); });
    await send(); expect(chatTimes(h.store.activeId, 'fixture-2')?.times.status).toBe(status);
    expect(h.store.messages.at(-1).content).toBe('Partial');
  });

  it('does not let cancelled late chunks or cleanup overwrite a new reply', async () => {
    const late = gate();
    h.stream.mockImplementationOnce(async function* (_request, _signal, observer) {
      observer.headers('a'.repeat(32)); await late.promise; yield chunk('OLD');
    }).mockImplementationOnce(async function* (_request, _signal, observer) {
      observer.headers('b'.repeat(32)); yield chunk('NEW'); yield chunk('', 'stop'); observer.done();
    });
    const old = send(); await flush(); element(render(), 'Stop generating').props.onClick();
    const newer = send(); await newer; late.release(); await old;
    expect(h.store.messages.at(-1).content).toBe('NEW');
    expect(chatTimes(h.store.activeId, 'fixture-2')?.times.status).toBe('cancelled');
    expect(chatTimes(h.store.activeId, 'fixture-4')?.times.status).toBe('completed');
    expect(h.store.updateLastAssistant.mock.calls.every(([, content]: any[]) => content !== 'OLD')).toBe(true);
  });

  it('marks an owner change without attaching observations to another conversation', async () => {
    const last = gate(); const owner = h.store.activeId;
    h.stream.mockImplementation(async function* (_request, _signal, observer) {
      yield chunk('Answer'); await last.promise; yield chunk('', 'stop'); observer.done();
    });
    const running = send(); await flush(); h.store.activeId = 'other'; h.subscribers.forEach(fn => fn(h.store));
    last.release(); await running;
    expect(chatTimes(owner, 'fixture-2')?.ownerAway).toBe(true);
    expect(chatTimes('other', 'fixture-2')).toBeNull();
  });

  it('keeps the nonlocal stop behavior and makes no local metrics request', async () => {
    vi.stubEnv('VITE_ANDREA_LOCAL', 'false');
    h.stream.mockImplementation(async function* (_request, _signal, observer) {
      expect(observer).toBeUndefined(); yield chunk('Answer'); yield chunk('', 'stop'); throw new Error('Should not read further');
    });
    await send(); expect(h.store.messages.at(-1).content).toBe('Answer');
    expect(chatTimes(h.store.activeId, 'fixture-2')).toBeNull();
    expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).includes('/api/andrea/metrics'))).toBe(false);
  });
});
