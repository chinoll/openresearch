import React, { useEffect, useRef } from 'react';
import { Box, Text, Static } from 'ink';
import { ChatMessage } from '../../shared/types.js';
import { renderCard } from './cards/index.js';

interface Props {
  messages: ChatMessage[];
  isLoading: boolean;
}

export default function ContentArea({ messages, isLoading }: Props) {
  return (
    <Box flexDirection="column" flexGrow={1} overflowY="hidden" paddingX={1}>
      {/* 使用 Static 渲染已完成的消息（性能优化）*/}
      <Static items={messages.slice(0, -1)}>
        {(msg) => (
          <Box key={msg.id} marginBottom={0}>
            {renderCard(msg)}
          </Box>
        )}
      </Static>

      {/* 最后一条消息（可能正在更新）*/}
      {messages.length > 0 && (
        <Box marginBottom={0}>
          {renderCard(messages[messages.length - 1])}
        </Box>
      )}

      {/* 加载指示 */}
      {isLoading && (
        <Box>
          <Text color="cyan" dimColor>⠿ 处理中...</Text>
        </Box>
      )}
    </Box>
  );
}
