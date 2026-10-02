// Local, bounded numerical observations. No query, source, answer or path storage.
export type BrowserStatus = 'running' | 'completed' | 'truncated' | 'incomplete' | 'cancelled' | 'error';
export interface ServerTimes {
  retrievalMs: number | null; firstTextMs: number | null;
  generationFirstTextMs: number | null; generationMs: number | null;
  totalMs: number | null; status: BrowserStatus | 'timeout' | 'retrieval_error' | null;
}
export interface BrowserTimes {
  requestId: string | null; answerMode: string | null; inferenceUsed: boolean | null;
  headersMs: number | null; firstContentMs: number | null;
  firstCommitMs: number | null; settledCommitMs: number | null;
  totalStreamMs: number | null; status: BrowserStatus;
  backgroundObserved: boolean; server: ServerTimes | null;
}
const MODES = new Set(['model_synthesis', 'brief_quotes', 'explicit_fields', 'status_scope_quotes']);
const SERVER_STATUSES = new Set(['running', 'completed', 'truncated', 'incomplete', 'cancelled', 'error', 'timeout', 'retrieval_error']);
const records: BrowserTimes[] = [];
function duration(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null;
}
function copy(record: BrowserTimes): BrowserTimes {
  return { ...record, server: record.server ? { ...record.server } : null };
}
export function browserMeasurements(): BrowserTimes[] { return records.map(copy); }
export function clearBrowserMeasurements() { records.length = 0; }

export class BrowserNoteMeasurement {
  private started: number;
  private value: BrowserTimes;
  constructor(private clock: () => number = () => performance.now(), visible = true) {
    this.started = clock();
    this.value = { requestId: null, answerMode: null, inferenceUsed: null,
      headersMs: null, firstContentMs: null, firstCommitMs: null, settledCommitMs: null,
      totalStreamMs: null, status: 'running', backgroundObserved: !visible, server: null };
    records.push(this.value);
    if (records.length > 50) records.shift();
  }
  private elapsed(): number { return Math.round(Math.max(0, this.clock() - this.started) * 100) / 100; }
  snapshot(): BrowserTimes { return copy(this.value); }
  visibility(visible: boolean) { if (!visible && this.value.status === 'running') this.value.backgroundObserved = true; }
  headers(id: string | null) {
    if (this.value.status !== 'running') return;
    this.value.headersMs = this.elapsed();
    this.value.requestId = id && /^[a-f0-9]{32}$/.test(id) ? id : null;
  }
  mode(mode: unknown) {
    if (typeof mode !== 'string' || !MODES.has(mode) || this.value.status !== 'running') return;
    this.value.answerMode = mode;
    this.value.inferenceUsed = mode === 'model_synthesis';
  }
  content() {
    if (this.value.status === 'running' && this.value.firstContentMs === null) this.value.firstContentMs = this.elapsed();
  }
  // Called from React's layout effect after DOM commit, not proof of screen paint.
  commit(hasText: boolean, visible: boolean): boolean {
    if (!visible) this.value.backgroundObserved = true;
    let changed = false;
    if (hasText && this.value.firstContentMs !== null && this.value.firstCommitMs === null) {
      this.value.firstCommitMs = this.elapsed(); changed = true;
    }
    if (this.value.status !== 'running' && this.value.settledCommitMs === null) {
      this.value.settledCommitMs = this.elapsed(); changed = true;
    }
    return changed;
  }
  finish(outcome: 'success' | 'cancelled' | 'error', done = false, reason: unknown = null) {
    if (this.value.status !== 'running') return;
    this.value.totalStreamMs = this.elapsed();
    this.value.status = outcome !== 'success' ? outcome :
      reason === 'length' ? 'truncated' :
      done && reason === 'stop' && this.value.firstContentMs !== null ? 'completed' : 'incomplete';
  }
  correlate(serverRecords: unknown) {
    if (!this.value.requestId || !Array.isArray(serverRecords)) return;
    const matched = serverRecords.find(row => row && typeof row === 'object' && row.id === this.value.requestId);
    if (!matched) return;
    this.value.server = {
      retrievalMs: duration(matched.retrievalMs), firstTextMs: duration(matched.firstTextMs),
      generationFirstTextMs: duration(matched.generationFirstTextMs), generationMs: duration(matched.generationMs),
      totalMs: duration(matched.totalMs),
      status: typeof matched.status === 'string' && SERVER_STATUSES.has(matched.status) ? matched.status : null,
    };
  }
}
