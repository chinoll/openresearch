import React from 'react';
import ContentArea from './components/ContentArea';
import InputBar from './components/InputBar';
import { useMessages } from './hooks/useMessages';

export default function App() {
  const { messages, isLoading, sendMessage } = useMessages();

  return (
    <div className="flex flex-col h-screen bg-terminal-bg text-zinc-100 font-mono">
      {/* 标题栏 */}
      <div className="border-b border-terminal-border px-4 py-2 flex items-center gap-3 shrink-0">
        <span className="text-terminal-cyan font-bold text-sm">● OpenResearch</span>
        <span className="text-zinc-600 text-xs">AI 驱动的学术阅读助手</span>
        <div className="ml-auto flex items-center gap-2">
          {isLoading && (
            <span className="text-terminal-yellow text-xs animate-pulse">● 处理中</span>
          )}
          <span className="text-zinc-600 text-xs">?  /help</span>
        </div>
      </div>

      {/* 消息流 */}
      <ContentArea messages={messages} />

      {/* 输入栏 */}
      <InputBar onSubmit={sendMessage} isLoading={isLoading} />
    </div>
  );
}
