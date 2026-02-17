import React, { useState, useRef, KeyboardEvent } from 'react';

interface Props {
  onSubmit: (input: string) => void;
  isLoading: boolean;
}

export default function InputBar({ onSubmit, isLoading }: Props) {
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const trimmed = value.trim();
      if (trimmed && !isLoading) {
        onSubmit(trimmed);
        setValue('');
      }
    }
  };

  return (
    <div className="border-t border-terminal-border bg-zinc-950 px-4 py-2">
      <div className="flex items-center gap-2">
        <span className="text-terminal-green font-bold shrink-0">
          {isLoading ? '⟳' : '>'}
        </span>
        <input
          ref={inputRef}
          className="flex-1 bg-transparent text-zinc-100 outline-none font-mono text-sm
                     placeholder-zinc-600 disabled:opacity-50"
          placeholder={isLoading ? '处理中…' : '输入命令 (/help) 或直接提问…'}
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          autoFocus
        />
        {value && (
          <span className="text-zinc-600 text-xs shrink-0">Enter ↵</span>
        )}
      </div>
    </div>
  );
}
