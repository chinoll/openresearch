import { useState, useCallback } from 'react';
import { ChatMessage, MessageType } from '../../shared/types.js';
import {
  papersApi, insightsApi, questionsApi, ideasApi, statsApi, streamChat
} from '../../shared/api/client.js';
import { parseCommand, resolveCommand, COMMAND_HELP } from '../../shared/commands.js';

let msgCounter = 0;
function newId() { return `msg_${++msgCounter}`; }

function makeMessage(type: MessageType, data: any): ChatMessage {
  return { id: newId(), type, data, timestamp: new Date() };
}

export function useMessages() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    makeMessage('dashboard', null),  // 启动时显示仪表盘占位
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [history, setHistory] = useState<{ role: string; content: string }[]>([]);

  const push = useCallback((msg: ChatMessage) => {
    setMessages(prev => [...prev, msg]);
  }, []);

  const updateLast = useCallback((updater: (msg: ChatMessage) => ChatMessage) => {
    setMessages(prev => {
      const arr = [...prev];
      arr[arr.length - 1] = updater(arr[arr.length - 1]);
      return arr;
    });
  }, []);

  // 执行 slash 命令
  const executeSlashCommand = useCallback(async (input: string) => {
    const parsed = parseCommand(input);
    if (!parsed) return;

    const cmd = resolveCommand(parsed.command);
    const args = parsed.args;

    try {
      if (cmd === 'help') {
        const helpText = Object.values(COMMAND_HELP).join('\n');
        push(makeMessage('ai_text', helpText));

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
        const target = args[0];
        setIsLoading(true);
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
          push(makeMessage('error', `未知列表类型: ${target}。可用: papers, insights, questions, ideas`));
        }

      } else if (cmd === 'insight' && args.length > 0) {
        const content = args.join(' ');
        const insight = await insightsApi.create({ content, paper_id: 'unknown' });
        push(makeMessage('insight_card', insight.insight));
        push(makeMessage('success', `洞察已记录: ${insight.insight?.id}`));

      } else if (cmd === 'question' && args.length > 0) {
        const content = args.join(' ');
        const question = await questionsApi.create({ content, paper_id: 'unknown' });
        push(makeMessage('question_card', question.question));
        push(makeMessage('success', `疑问已记录: ${question.question?.id}`));

      } else if (cmd === 'session') {
        const action = args[0];
        if (action === 'start' && args[1]) {
          const result = await insightsApi.startSession(args[1]);
          push(makeMessage('success', `阅读会话已开始: ${result.session_id}`));
        } else if (action === 'end') {
          const result = await insightsApi.endSession();
          push(makeMessage('success', `阅读会话已结束`));
        }

      } else {
        push(makeMessage('error', `未知命令: /${cmd}。输入 /help 查看帮助`));
      }
    } catch (err: any) {
      push(makeMessage('error', `命令执行失败: ${err.message}`));
    } finally {
      setIsLoading(false);
    }
  }, [push]);

  // 发送自然语言给 AI
  const sendToAI = useCallback(async (input: string) => {
    setIsLoading(true);

    // AI 文字回复消息（累积更新）
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
          // 根据工具名渲染对应卡片
          const result = event.result;
          if (event.name === 'list_papers') {
            push(makeMessage('paper_list', result.papers || []));
          } else if (event.name === 'download_paper') {
            push(makeMessage('paper_card', result));
          } else if (event.name === 'list_insights') {
            push(makeMessage('insight_list', result.insights || []));
          } else if (event.name === 'create_insight') {
            push(makeMessage('insight_card', result.insight));
          } else if (event.name === 'list_questions') {
            push(makeMessage('question_list', result.questions || []));
          } else if (event.name === 'create_question') {
            push(makeMessage('question_card', result.question));
          } else if (event.name === 'get_statistics') {
            push(makeMessage('dashboard', result));
          }
        }
      }

      // 更新对话历史
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

  // 统一入口
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
