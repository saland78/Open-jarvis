import { beforeEach, describe, expect, it } from 'vitest';
import { BrowserNoteMeasurement, browserMeasurements, clearBrowserMeasurements } from './andrea-browser-metrics';

beforeEach(clearBrowserMeasurements);

describe('local browser timings', () => {
  it('distinguishes received content, first DOM commit and settled commit', () => {
    let now = 100;
    const m = new BrowserNoteMeasurement(() => now);
    now = 110; m.headers('a'.repeat(32)); m.mode('model_synthesis');
    now = 130; m.content();
    expect(m.snapshot().firstCommitMs).toBeNull();
    now = 140; expect(m.commit(true, true)).toBe(true);
    now = 180; m.content(); m.finish('success', true, 'stop');
    now = 190; expect(m.commit(true, true)).toBe(true);
    now = 200; expect(m.commit(true, true)).toBe(false);
    expect(m.snapshot()).toMatchObject({ headersMs: 10, firstContentMs: 30,
      firstCommitMs: 40, totalStreamMs: 80, settledCommitMs: 90, status: 'completed', inferenceUsed: true });
  });

  it('keeps direct responses separate and permits a single final batched UI update', () => {
    let now = 0; const m = new BrowserNoteMeasurement(() => now);
    m.mode('status_scope_quotes'); now = 4; m.content(); now = 5; m.finish('success', true, 'stop');
    now = 8; m.commit(true, true);
    expect(m.snapshot()).toMatchObject({ inferenceUsed: false, firstCommitMs: 8, settledCommitMs: 8 });
  });

  it('does not count source events or a completed transport without a stop reason as completed text', () => {
    const m = new BrowserNoteMeasurement(() => 0); m.mode('brief_quotes'); m.commit(false, true);
    m.finish('success', true, 'stop');
    expect(m.snapshot().status).toBe('incomplete'); expect(m.snapshot().firstCommitMs).toBeNull();
    const other = new BrowserNoteMeasurement(() => 0); other.content(); other.finish('success', true, null);
    expect(other.snapshot().status).toBe('incomplete');
  });

  it('preserves cancellation, truncation, errors and missing DONE', () => {
    for (const [outcome, done, reason, expected] of [
      ['cancelled', true, 'stop', 'cancelled'], ['error', true, 'stop', 'error'],
      ['success', true, 'length', 'truncated'], ['success', false, 'stop', 'incomplete'],
    ] as const) {
      const m = new BrowserNoteMeasurement(() => 0); m.content(); m.finish(outcome, done, reason);
      m.finish('success', true, 'stop'); expect(m.snapshot().status).toBe(expected);
    }
  });

  it('correlates only the exact ID and whitelists numerical server fields without foreign timestamps or content', () => {
    const m = new BrowserNoteMeasurement(() => 0); m.headers('a'.repeat(32));
    m.correlate([{ id: 'b'.repeat(32), totalMs: 999 }]); expect(m.snapshot().server).toBeNull();
    m.correlate([{ id: 'a'.repeat(32), retrievalMs: 4, firstTextMs: 30, totalMs: 70, status: 'completed',
      generationMs: -1, generationFirstTextMs: 'not a duration', query: 'PRIVATE_QUERY', text: 'PRIVATE_TEXT', path: 'PRIVATE_PATH' }]);
    expect(m.snapshot().server).toMatchObject({ retrievalMs: 4, firstTextMs: 30, totalMs: 70, generationMs: null, generationFirstTextMs: null });
    expect(JSON.stringify(browserMeasurements())).not.toContain('PRIVATE');
    const snapshot = m.snapshot(); snapshot.server!.totalMs = 123;
    expect(m.snapshot().server!.totalMs).toBe(70);
    const malformed = new BrowserNoteMeasurement(() => 0); malformed.headers('PRIVATE_HEADER'); malformed.mode('PRIVATE_MODE');
    expect(malformed.snapshot()).toMatchObject({ requestId: null, answerMode: null, inferenceUsed: null });
  });

  it('retains at most 50 independent requests and marks background observations', () => {
    for (let i = 0; i < 52; i++) { const m = new BrowserNoteMeasurement(() => i, i !== 51); m.headers(i.toString(16).padStart(32, '0')); }
    const rows = browserMeasurements(); expect(rows).toHaveLength(50);
    expect(rows[0].requestId).toBe('2'.padStart(32, '0')); expect(rows[49].backgroundObserved).toBe(true);
    const m = new BrowserNoteMeasurement(() => 0); m.visibility(false); m.visibility(true);
    expect(m.snapshot().backgroundObserved).toBe(true);
    clearBrowserMeasurements(); expect(browserMeasurements()).toEqual([]);
  });
});
