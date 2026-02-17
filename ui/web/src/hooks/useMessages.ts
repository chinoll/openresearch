// Web 版 useMessages，与 TUI 版逻辑相同，但用于浏览器环境
import { useState, useCallback } from 'react';
import { ChatMessage, MessageType } from '@shared/types';
import {
  papersApi, insightsApi, questionsApi, ideasApi, statsApi, streamChat
} from '@shared/api/client';
import { parseCommand, resolveCommand, COMMAND_HELP } from '@shared/commands';

let msgCounter = 0;
const newId = () => `msg_${++msgCounter}`;

function makeMessage(type: MessageType, data: any): ChatMessage {
  return { id: newId(), type, data, timestamp: new Date() };
}

export function useMessages() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    makeMessage('dashboard', null),
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [history, setHistory] = useState<{ role: string; content: string }[]>([]);

  const push = useCallback((msg: ChatMessage) => {
    setMessages(prev => [...prev, msg]);
  }, []);

  const executeSlashCommand = useCallback(async (input: string) => {
    const parsed = parseCommand(input);
    if (!parsed) return;
    const cmd = resolveCommand(parsed.command);
    const args = parsed.args;

    try {
      if (cmd === 'help') {
        push(makeMessage('ai_text', Object.values(COMMAND_HELP).join('\n')));
      } else if (cmd === 'stats') {
        setIsLoading(true);
        const stats = await statsApi.global();
        push(makeMessage('dashboard', stats));
      } else if (cmd === 'download' && args[0]) {
        setIsLoading(true);
        push(makeMessage('tool_call', { name: 'download_paper', input: { arxiv_id: args[0] } }));
        const result = await papersApi.download(args[0]);
        push(makeMessage('paper_card', result));
        push(makeMessage('success', `论文 ${args[0]} 下载完成`));
      } else if (cmd === 'list') {
        setIsLoading(true);
        const target = args[0];
        if (target === 'papers') {
          const data = await papersApi.list();
          push(makeMessage('paper_list', data.papers));
        } else if (target === 'insights') {
          const data = await insightsApi.list();
          push(makeMessage('insight_list', data.insights));
        } else if (target === 'questions') {
          const status = args.find(a => ['unsolved', 'partial', 'solved'].includes(a));
          const data = await questionsApi.list({ status });
          push(makeMessage('question_list', data.questions));
        } else if (target === 'ideas') {
          const data = await ideasApi.list();
          push(makeMessage('idea_card', data.ideas));
        } else {
          push(makeMessage('error', `未知类型: ${target}`));
        }
      } else if (cmd === 'insight' && args.length > 0) {
        const result = await insightsApi.create({ content: args.join(' '), paper_id: 'unknown' });
        push(makeMessage('insight_card', result.insight));
        push(makeMessage('success', `洞察已记录: ${result.insight?.id}`));
      } else if (cmd === 'question' && args.length > 0) {
        const result = await questionsApi.create({ content: args.join(' '), paper_id: 'unknown' });
        push(makeMessage('question_card', result.question));
        push(makeMessage('success', `疑问已记录: ${result.question?.id}`));
      } else if (cmd === 'session') {
        if (args[0] === 'start' && args[1]) {
          const r = await insightsApi.startSession(args[1]);
          push(makeMessage('success', `阅读会话已开始: ${r.session_id}`));
        } else if (args[0] === 'end') {
          await insightsApi.endSession();
          push(makeMessage('success', '阅读会话已结束'));
        }
      } else {
        push(makeMessage('error', `未知命令: /${cmd}。输入 /help 查看帮助`));
      }
    } catch (err: any) {
      push(makeMessage('error', `命令失败: ${err.message}`));
    } finally {
      setIsLoading(false);
    }
  }, [push]);

  const sendToAI = useCallback(async (input: string) => {
    setIsLoading(true);
    const aiMsgId = newId();
    push({ id: aiMsgId, type: 'ai_text', data: '', timestamp: new Date() });

    try {
      let accText = '';
      for await (const event of streamChat(input, history)) {
        if (event.type === 'text') {
          accText += event.content;
          setMessages(prev =>
            prev.map(m => m.id === aiMsgId ? { ...m, data: accText } : m)
          );
        } else if (event.type === 'tool_call') {
          push(makeMessage('tool_call', { name: event.name, input: event.input }));
        } else if (event.type === 'tool_result') {
          const r = event.result;
          if (event.name === 'list_papers') push(makeMessage('paper_list', r.papers || []));
          else if (event.name === 'download_paper') push(makeMessage('paper_card', r));
          else if (event.name === 'list_insights') push(makeMessage('insight_list', r.insights || []));
          else if (event.name === 'create_insight') push(makeMessage('insight_card', r.insight));
          else if (event.name === 'list_questions') push(makeMessage('question_list', r.questions || []));
          else if (event.name === 'create_question') push(makeMessage('question_card', r.question));
          else if (event.name === 'get_statistics') push(makeMessage('dashboard', r));
        }
      }
      setHistory(prev => [
        ...prev,
        { role: 'user', content: input },
        { role: 'assistant', content: accText },
      ]);
    } catch (err: any) {
      push(makeMessage('error', `AI 请求失败: ${err.message}`));
    } finally {
      setIsLoading(false);
    }
  }, [history, push]);

  const sendMessage = useCallback(async (input: string) => {
    if (!input.trim()) return;
    push(makeMessage('user', input));
    if (input.startsWith('/')) {
      await executeSlashCommand(input);
    } else {
      await sendToAI(input);
    }
  }, [executeSlashCommand, sendToAI, push]);

  return { messages, isLoading, sendMessage };
}
