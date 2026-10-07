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
function visibleText(tree: unknown): string {
  if (Array.isArray(tree)) return tree.map(visibleText).join(' ');
  if (tree && typeof tree === 'object' && 'props' in tree) return visibleText((tree as {props:{children?:unknown}}).props.children);
  return typeof tree === 'string' || typeof tree === 'number' ? String(tree) : '';
}
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
    button(render(), 'Sintesi libera del modello')!(); await flush();
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
    button(render(), 'Sintesi libera del modello')!(); await flush();
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
    button(render(), 'Sintesi libera del modello')!(); await flush(); render();
    expect(browserMeasurements()[0].status).toBe('incomplete'); expect(h.states[6]).toBe('Partial.');
    expect(h.states[7]).toBe('Risposta incompleta o troncata: non considerarla conclusa.');
  });
  it('opts in to structured generation and waits for accepted text', async () => {
    const validation = gate();
    h.stream.mockImplementation(async function* (payload, _signal, observer) {
      expect(payload.notes_structured).toBe(true); expect(payload.notes_brief).toBe(false);
      observer.headers('a'.repeat(32));
      yield { event: 'local_sources', data: '{"answerMode":"structured_synthesis","inferenceUsed":true,"sources":[]}' };
      await validation.promise;
      yield { data: '{"choices":[{"delta":{"content":"Validated synthesis [N1]."}}]}' };
      yield { data: '{"choices":[{"delta":{},"finish_reason":"stop"}]}' }; observer.done();
    });
    button(render(), 'Sintesi strutturata')!(); await flush(); render();
    expect(h.states[6]).toBe(''); expect(browserMeasurements()[0].firstContentMs).toBeNull();
    validation.release(); await flush(); render();
    expect(h.states[6]).toBe('Validated synthesis [N1].');
    expect(browserMeasurements()[0]).toMatchObject({status:'completed',answerMode:'structured_synthesis',inferenceUsed:true});
  });
  it('displays structured refusal with its actual inference flag', async () => {
    h.stream.mockImplementation(async function* (_payload, _signal, observer) {
      yield { event: 'local_sources', data: '{"answerMode":"structured_refused","inferenceUsed":false,"sources":[]}' };
      yield { data: '{"choices":[{"delta":{"content":"Sintesi strutturata non mostrata."}}]}' };
      yield { data: '{"choices":[{"delta":{},"finish_reason":"stop"}]}' }; observer.done();
    });
    button(render(), 'Sintesi strutturata')!(); await flush(); render();
    expect(browserMeasurements()[0]).toMatchObject({answerMode:'structured_refused',inferenceUsed:false});
  });

  it('sends the selected path without injecting cached snippets and renders separate proof lines', async () => {
    h.states[3] = { query: 'Broad search', results: [{ eligible: true, status: 'active', path: 'Books/example.md', title: 'Example', text: 'STALE PREVIEW' }],
      total: 1, scanned: 1, excluded: 0, skipped: 0, elapsedMs: 1, partial: true };
    const evidence = { answerMode:'structured_synthesis', inferenceUsed:true, synthesisPath:'source_facts',
      selectionScope:'selected_note_facts', partial:false, excluded:0, sources:[{
        id:'N1',title:'Example',path:'Books/example.md',status:'active',modifiedAt:'2030-01-01',
        startLine:8,endLine:30,text:'JOINED PASSAGES SHOULD NOT RENDER',passages:[
          {text:'Original first passage.',startLine:8,endLine:9},
          {text:'Original second passage.',startLine:30,endLine:30}]}] };
    h.stream.mockImplementation(async function* (payload, _signal, observer) {
      expect(payload).toMatchObject({ notes_path:'Books/example.md',notes_query:'Broad search',notes_structured:true,notes_brief:false });
      expect(payload.notes_sources).toBeUndefined(); expect(JSON.stringify(payload)).not.toContain('STALE PREVIEW');
      yield { event:'local_sources',data:JSON.stringify(evidence) };
      yield { data:'{"choices":[{"delta":{"content":"Model phrasing [N1]."}}]}' };
      yield { data:'{"choices":[{"delta":{},"finish_reason":"stop"}]}' }; observer.done();
    });
    button(render(),'Sintesi della nota')!(); await flush(); const tree = render();
    const text = visibleText(tree);
    expect(text).toMatch(/Righe\s+8\s*–\s*9/); expect(text).toMatch(/Righe\s+30\s*–\s*30/);
    expect(text).not.toMatch(/righe\s+8\s*–\s*30/); expect(text).not.toContain('JOINED PASSAGES');
    expect(text).toContain('I controlli tecnici non certificano il significato');
    expect(text).toContain('nota scelta'); expect(h.states[6]).toBe('Model phrasing [N1].');
    expect(h.stream).toHaveBeenCalledOnce(); expect(browserMeasurements()[0].status).toBe('completed');
  });

  it('does not offer the selected-note synthesis for inactive sources', () => {
    h.states[3] = { query:'Example',results:[{eligible:false,status:'superseded',path:'Old.md',title:'Old'}],total:1 };
    expect(button(render(),'Sintesi della nota')).toBeUndefined();
  });

  it('keeps selected-note generation pending until validated text arrives, then supports cancellation', async () => {
    const end = gate(); h.states[3] = { query:'Example',results:[{eligible:true,status:'active',path:'Example.md',title:'Example'}],total:1 };
    h.stream.mockImplementation(async function* (_payload,_signal,observer) {
      yield {event:'local_sources',data:'{"answerMode":"structured_synthesis","synthesisPath":"source_facts","selectionScope":"selected_note_facts","sources":[]}'};
      await end.promise; yield {data:'{"choices":[{"delta":{"content":"LATE"}}]}'}; observer.done();
    });
    button(render(),'Sintesi della nota')!(); await flush();
    expect(h.states[6]).toBe(''); expect(visibleText(render())).toContain('Elaborazione e controlli in corso');
    button(render(),'Interrompi risposta')!(); end.release(); await flush(); render();
    expect(h.states[6]).toBe(''); expect(browserMeasurements()[0].status).toBe('cancelled');
  });

});
