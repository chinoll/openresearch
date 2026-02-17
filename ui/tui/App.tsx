import React from 'react';
import { Box, Text, useApp } from 'ink';
import ContentArea from './components/ContentArea.js';
import InputBar from './components/InputBar.js';
import { useMessages } from './hooks/useMessages.js';

export default function App() {
  const { messages, isLoading, sendMessage } = useMessages();

  return (
    <Box flexDirection="column" height="100%">
      {/* 标题栏 */}
      <Box borderStyle="single" borderColor="cyan" paddingX={1}>
        <Text color="cyan" bold>OpenResearch</Text>
        <Text color="gray">  论文 | 洞察 | 疑问 | 想法 | AI助手</Text>
        <Text color="gray" dimColor>   /help 查看命令  /exit 退出</Text>
      </Box>

      {/* 动态内容区 */}
      <ContentArea messages={messages} isLoading={isLoading} />

      {/* 底部输入框 */}
      <InputBar onSubmit={sendMessage} isLoading={isLoading} />
    </Box>
  );
}
