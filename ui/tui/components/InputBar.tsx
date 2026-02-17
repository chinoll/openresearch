import React, { useState } from 'react';
import { Box, Text, useInput, useApp } from 'ink';
import TextInput from 'ink-text-input';

interface Props {
  onSubmit: (input: string) => void;
  isLoading: boolean;
}

export default function InputBar({ onSubmit, isLoading }: Props) {
  const [value, setValue] = useState('');
  const { exit } = useApp();

  const handleSubmit = (val: string) => {
    const trimmed = val.trim();
    if (!trimmed) return;
    if (trimmed === '/exit' || trimmed === '/quit') {
      exit();
      return;
    }
    onSubmit(trimmed);
    setValue('');
  };

  return (
    <Box
      borderStyle="single"
      borderColor={isLoading ? 'gray' : 'green'}
      paddingX={1}
    >
      <Text color={isLoading ? 'gray' : 'green'} bold>
        {isLoading ? '⠿' : '>'}{' '}
      </Text>
      <TextInput
        value={value}
        onChange={setValue}
        onSubmit={handleSubmit}
        placeholder={isLoading ? '等待响应...' : '输入命令 (/help) 或直接提问...'}
        focus={!isLoading}
      />
    </Box>
  );
}
