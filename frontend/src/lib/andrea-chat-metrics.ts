import { BrowserNoteMeasurement, type BrowserTimes } from './andrea-browser-metrics';

// Ownership identifiers live only here, never in ChatMessage or localStorage.
export interface ChatTimes { times: BrowserTimes; ownerAway: boolean }
const entries = new Map<string, ChatMeasurement>();
const listeners = new Map<string, Set<() => void>>();
const key = (conversation: string, message: string) => JSON.stringify([conversation, message]);
function notify(id: string) { listeners.get(id)?.forEach(listener => listener()); }
export function chatTimes(conversation: string, message: string): ChatTimes | null {
  return entries.get(key(conversation, message))?.snapshot ?? null;
}
export function subscribeChatTimes(conversation: string, message: string, listener: () => void) {
  const id = key(conversation, message);
  const set = listeners.get(id) ?? new Set(); set.add(listener); listeners.set(id, set);
  return () => { set.delete(listener); if (!set.size) listeners.delete(id); };
}
export function commitChatTimes(conversation: string, message: string, hasText: boolean, isLive: boolean, visible: boolean) {
  entries.get(key(conversation, message))?.commit(hasText, isLive, visible);
}

export class ChatMeasurement {
  private readonly measurement: BrowserNoteMeasurement;
  snapshot: ChatTimes;
  private id: string;
  private done = false;
  private reason: unknown = null;
  constructor(conversation: string, message: string, clock?: () => number, visible = true) {
    this.id = key(conversation, message);
    this.measurement = new BrowserNoteMeasurement(clock, visible);
    this.snapshot = { times: this.measurement.snapshot(), ownerAway: false };
    entries.set(this.id, this);
    if (entries.size > 50) {
      const oldest = entries.keys().next().value!;
      entries.delete(oldest); notify(oldest);
    }
    notify(this.id);
  }
  private publish() {
    this.snapshot = { times: this.measurement.snapshot(), ownerAway: this.snapshot.ownerAway };
    if (entries.get(this.id) === this) notify(this.id);
  }
  headers(id: string | null) { this.measurement.headers(id); this.publish(); }
  content() { this.measurement.mode('model_synthesis'); this.measurement.content(); this.publish(); }
  ended() { this.done = true; }
  finishReason(reason: unknown) { if (reason) this.reason = reason; }
  visibility(visible: boolean) { this.measurement.visibility(visible); this.publish(); }
  owner(active: string | null, conversation: string) {
    if (active !== conversation && this.snapshot.times.settledCommitMs === null) {
      this.snapshot.ownerAway = true; this.publish();
    }
  }
  commit(hasText: boolean, isLive: boolean, visible: boolean) {
    // Reopening a historic reply is not its first rendering latency.
    if (this.snapshot.ownerAway || this.snapshot.times.status === 'cancelled' || (isLive && this.snapshot.times.status !== 'running')) return;
    if (this.measurement.commit(hasText, visible)) this.publish();
  }
  finish(outcome: 'success' | 'cancelled' | 'error') {
    this.measurement.finish(outcome, this.done, this.reason); this.publish();
  }
  correlate(records: unknown) { this.measurement.correlate(records); this.publish(); }
}
