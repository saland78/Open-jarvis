import { describe, expect, it } from 'vitest';
import { ChatMeasurement, chatTimes, commitChatTimes, subscribeChatTimes } from './andrea-chat-metrics';

describe('chat observation ownership', () => {
  it('keeps commits on the owning message and never measures a later reopening', () => {
    let now = 0;
    const row = new ChatMeasurement('conversation', 'message', () => now);
    now = 10; row.headers('a'.repeat(32)); row.content();
    commitChatTimes('other', 'message', true, true, true);
    expect(row.snapshot.times.firstCommitMs).toBeNull();
    now = 12; commitChatTimes('conversation', 'message', true, true, true);
    expect(row.snapshot.times.firstCommitMs).toBe(12);
    row.owner('other', 'conversation'); row.ended(); row.finishReason('stop'); row.finish('success');
    now = 1000; commitChatTimes('conversation', 'message', true, false, true);
    expect(row.snapshot).toMatchObject({ ownerAway: true, times: { status: 'completed', settledCommitMs: null } });
  });

  it('requires DONE and stop, preserves cancellation and exact request correlation', () => {
    const row = new ChatMeasurement('c', 'm'); row.headers('b'.repeat(32)); row.content();
    row.finishReason('stop'); row.finish('success');
    expect(row.snapshot.times.status).toBe('incomplete');
    const cancelled = new ChatMeasurement('c', 'cancel'); cancelled.headers('c'.repeat(32)); cancelled.finish('cancelled');
    cancelled.ended(); cancelled.finish('success');
    cancelled.correlate([{ id: 'b'.repeat(32), totalMs: 999 }]);
    expect(cancelled.snapshot.times).toMatchObject({ status: 'cancelled', server: null });
    cancelled.correlate([{ id: 'c'.repeat(32), totalMs: 1, status: 'cancelled', content: 'PRIVATE' }]);
    expect(cancelled.snapshot.times.server?.totalMs).toBe(1);
    expect(JSON.stringify(cancelled.snapshot)).not.toContain('PRIVATE');
  });

  it('evicts beyond fifty, notifies subscribers, and stores no message text', () => {
    const first = new ChatMeasurement('bounded', 'first'); let notices = 0;
    const unsubscribe = subscribeChatTimes('bounded', 'first', () => { notices++; });
    first.content(); expect(notices).toBe(1);
    for (let i = 0; i < 50; i++) new ChatMeasurement('bounded', String(i));
    expect(chatTimes('bounded', 'first')).toBeNull(); expect(notices).toBe(2);
    unsubscribe(); first.finish('cancelled'); expect(notices).toBe(2);
  });
});
