import React, { useEffect, useRef } from 'react';
import { ChatMessage } from '@shared/types';
import { renderCard } from './cards';

interface Props {
  messages: ChatMessage[];
}

export default function ContentArea({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-2 space-y-0.5">
      {messages.map(msg => renderCard(msg))}
      <div ref={bottomRef} />
    </div>
  );
}
