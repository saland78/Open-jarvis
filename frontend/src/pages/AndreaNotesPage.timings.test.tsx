// Hook/callback harness: tests ownership and lifecycle wiring, not screen paint.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
const h = vi.hoisted(() => ({ states: [] as unknown[], refs: [] as { current: unknown }[], stateIndex: 0,
  refIndex: 0, layouts: [] as (() => void)[], stream: vi.fn() }));
vi.mock('react', () => ({
  useState: (initial: unknown) => { const i = h.stateIndex++; if (!(i in h.states)) h.states[i] = initial;
    return [h.states[i], (value: unknown) => { h.states[i] = value; }]; },
  useRef: (initial: unknown) => { const i = h.refIndex++; return h.refs[i] ||= { current: initial }; },
  useEffect: () => {},
  useLayoutEffect: (effect: () => void) => { h.layouts.push(effect); },
}));
vi.mock('../lib/store', () => ({ useAppStore: (selector: (s: object) => unknown) => selector({ selectedModel: 'fixture' }) }));
vi.mock('../lib/api', () => ({ getBase: () => '', authHeaders: (headers: object) => headers }));
vi.mock('../lib/sse', () => ({ streamChat: h.stream }));
import { AndreaNotesPage } from './AndreaNotesPage';
import { browserMeasurements, clearBrowserMeasurements } from '../lib/andrea-browser-metrics';

function render(commit = true) {
  h.stateIndex = 0; h.refIndex = 0; h.layouts = [];
  const tree = AndreaNotesPage(); if (commit) for (const effect of h.layouts) effect(); return tree;
}
function button(tree: unknown, label: string): (() => void) | undefined {
  if (Array.isArray(tree)) { for (const child of tree) { const found = button(child, label); if (found) return found; } }
  else if (tree && typeof tree === 'object' && 'props' in tree) {
    const element = tree as { type: unknown; props: { children?: unknown; onClick?: () => void } };
    if (element.type === 'button' && element.props.children === label) return element.props.onClick;
    return button(element.props.children, label);
  }
}
function gate() { let release!: () => void; const promise = new Promise<void>(resolve => { release = resolve; }); return { promise, release }; }
const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };

beforeEach(() => {
  h.states = []; h.refs = []; h.stream.mockReset(); clearBrowserMeasurements();
  vi.stubGlobal('document', { visibilityState: 'visible' });
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"records":[]}')));
  render(); h.states[0] = { available: true, configured: true };
  h.states[3] = { query: 'Synthetic', results: [{ eligible: true, path: 'fixture.md', title: 'Fixture' }], total: 1, scanned: 1, excluded: 0, skipped: 0, elapsedMs: 1, partial: false };
});
afterEach(() => vi.unstubAllGlobals());

describe('notes measurement lifecycle ownership', () => {
  it('records first received content before a UI commit, then final commit without changing the response', async () => {
    const first = gate(); const last = gate();
    h.stream.mockImplementation(async function* (_payload, _signal, observer) {
      observer.headers('a'.repeat(32));
      yield { event: 'local_sources', data: '{"answerMode":"model_synthesis","sources":[]}' };
      await first.promise; yield { data: '{"choices":[{"delta":{"content":"Synthetic answer."}}]}' };
      await last.promise; yield { data: '{"choices":[{"delta":{},"finish_reason":"stop"}]}' }; observer.done();
    });
    button(render(), 'Sintesi del modello')!(); await flush();
    expect(browserMeasurements()[0].firstContentMs).toBeNull();
    first.release(); await flush();
    expect(browserMeasurements()[0].firstContentMs).not.toBeNull(); expect(browserMeasurements()[0].firstCommitMs).toBeNull();
    render(); expect(browserMeasurements()[0].firstCommitMs).not.toBeNull(); expect(h.states[6]).toBe('Synthetic answer.');
    last.release(); await flush(); render();
    expect(browserMeasurements()[0]).toMatchObject({ status: 'completed', inferenceUsed: true });
    expect(browserMeasurements()[0].settledCommitMs).not.toBeNull(); expect(h.stream).toHaveBeenCalledOnce();
  });

  it('ignores late chunks and metrics from an interrupted request after a new reply starts', async () => {
    const first = gate();
    h.stream.mockImplementationOnce(async function* (_payload, _signal, observer) {
      observer.headers('a'.repeat(32)); await first.promise;
      yield { data: '{"choices":[{"delta":{"content":"OLD ANSWER"}}]}' }; observer.done();
    }).mockImplementationOnce(async function* (_payload, _signal, observer) {
      observer.headers('b'.repeat(32)); yield { event: 'local_sources', data: '{"answerMode":"brief_quotes","sources":[]}' };
      yield { data: '{"choices":[{"delta":{"content":"NEW ANSWER"}}]}' };
      yield { data: '{"choices":[{"delta":{},"finish_reason":"stop"}]}' }; observer.done();
    });
    button(render(), 'Sintesi del modello')!(); await flush();
    button(render(), 'Interrompi risposta')!();
    button(render(), 'Passaggi brevi dalle fonti')!(); await flush(); render();
    first.release(); await flush(); render();
    expect(h.states[6]).toBe('NEW ANSWER');
    const rows = browserMeasurements(); expect(rows[0].status).toBe('cancelled');
    expect(rows[0].firstContentMs).toBeNull(); expect(rows[1]).toMatchObject({ status: 'completed', inferenceUsed: false, requestId: 'b'.repeat(32) });
    expect(vi.mocked(fetch)).toHaveBeenCalledOnce(); // only the new response's metric read
  });

  it('labels an EOF without DONE as incomplete while retaining partial text', async () => {
    h.stream.mockImplementation(async function* () { yield { data: '{"choices":[{"delta":{"content":"Partial."}}]}' }; });
    button(render(), 'Sintesi del modello')!(); await flush(); render();
    expect(browserMeasurements()[0].status).toBe('incomplete'); expect(h.states[6]).toBe('Partial.');
    expect(h.states[7]).toBe('Risposta incompleta o troncata: non considerarla conclusa.');
  });
});
