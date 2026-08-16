import type { Message } from '../types';
import { useEffect, useRef } from 'react';

interface Props {
  messages: Message[];
  onClear: () => void;
}

export function EventFeed({ messages, onClear }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  const recentMessages = messages.slice(-50);

  return (
    <div className="event-feed">
      <div className="feed-header">
        <h3>📜 消息日志</h3>
        <button className="clear-btn" onClick={onClear}>清空</button>
      </div>
      <div className="feed-list">
        {recentMessages.length === 0 && (
          <div className="feed-empty">暂无消息</div>
        )}
        {recentMessages.map(m => (
          <div key={m.id} className={`feed-item ${m.type}`}>
            <span className="feed-tag">{m.type === 'diary' ? '📖' : '📰'}</span>
            <span className="feed-text">{m.text}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}