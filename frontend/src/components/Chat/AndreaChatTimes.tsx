import { useLayoutEffect, useSyncExternalStore } from 'react';
import { chatTimes, commitChatTimes, subscribeChatTimes } from '../../lib/andrea-chat-metrics';
import { AndreaResponseTimes } from '../../pages/AndreaResponseTimes';

export function AndreaChatTimes({ conversationId, messageId, hasText, isLive }: {
  conversationId: string; messageId: string; hasText: boolean; isLive: boolean;
}) {
  const observation = useSyncExternalStore(
    listener => subscribeChatTimes(conversationId, messageId, listener),
    () => chatTimes(conversationId, messageId),
    () => null,
  );
  useLayoutEffect(() => {
    if (observation) commitChatTimes(conversationId, messageId, hasText, isLive, document.visibilityState === 'visible');
  }, [conversationId, messageId, hasText, isLive, observation]);
  return observation ? <div className="mt-3"><AndreaResponseTimes times={observation.times} chat ownerAway={observation.ownerAway} /></div> : null;
}
