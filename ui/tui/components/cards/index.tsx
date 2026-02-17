import React from 'react';
import { Box, Text } from 'ink';
import { ChatMessage } from '../../../shared/types.js';

// ─── 用户消息 ──────────────────────────────────────
export function UserMessage({ data }: { data: string }) {
  return (
    <Box marginY={0}>
      <Text color="green" bold>{'> '}</Text>
      <Text>{data}</Text>
    </Box>
  );
}

// ─── AI 文字回复 ───────────────────────────────────
export function AIMessage({ data }: { data: string }) {
  if (!data) return null;
  return (
    <Box flexDirection="column" borderStyle="round" borderColor="cyan" paddingX={1} marginY={0}>
      <Text color="cyan" dimColor>● AI</Text>
      <Text wrap="wrap">{data}</Text>
    </Box>
  );
}

// ─── 工具调用通知 ──────────────────────────────────
export function ToolCallCard({ data }: { data: { name: string; input: any } }) {
  return (
    <Box marginY={0}>
      <Text color="yellow">⚡ 调用工具: </Text>
      <Text color="yellow" bold>{data.name}</Text>
      <Text color="gray"> {JSON.stringify(data.input)}</Text>
    </Box>
  );
}

// ─── 论文卡片 ──────────────────────────────────────
export function PaperCard({ data }: { data: any }) {
  if (!data) return null;
  const meta = data.metadata || data;
  return (
    <Box flexDirection="column" borderStyle="single" borderColor="blue" paddingX={1} marginY={0}>
      <Text color="blue" bold>📄 {meta.title || data.paper_id || '未知论文'}</Text>
      {meta.authors && (
        <Text color="gray">👥 {(Array.isArray(meta.authors) ? meta.authors : [meta.authors]).join(', ')}</Text>
      )}
      {meta.published && <Text color="gray">📅 {meta.published?.slice(0, 10)}</Text>}
      {data.paper_id && <Text color="gray" dimColor>ID: {data.paper_id}</Text>}
      {data.source_type && <Text color="green" dimColor>格式: {data.source_type.toUpperCase()}</Text>}
    </Box>
  );
}

// ─── 论文列表 ──────────────────────────────────────
export function PaperList({ data }: { data: any[] }) {
  if (!data?.length) return <Text color="gray">没有论文</Text>;
  return (
    <Box flexDirection="column" borderStyle="single" borderColor="blue" paddingX={1} marginY={0}>
      <Text color="blue" bold>📄 论文列表 ({data.length})</Text>
      {data.slice(0, 15).map((p, i) => (
        <Box key={p.paper_id || i}>
          <Text color="gray">{String(i + 1).padStart(2)}. </Text>
          <Text bold>{p.paper_id}</Text>
          <Text color="gray"> — {(p.title || '').slice(0, 50)}</Text>
          {p.has_tex && <Text color="green"> [TeX]</Text>}
        </Box>
      ))}
      {data.length > 15 && <Text color="gray">... 还有 {data.length - 15} 篇</Text>}
    </Box>
  );
}

// ─── 洞察卡片 ──────────────────────────────────────
const INSIGHT_COLOR: Record<string, string> = {
  observation: 'white',
  question: 'yellow',
  connection: 'cyan',
  surprise: 'magenta',
  critique: 'red',
  insight: 'green',
};

const INSIGHT_EMOJI: Record<string, string> = {
  observation: '👀', question: '❓', connection: '🔗',
  surprise: '😮', critique: '🔍', insight: '💡',
};

export function InsightCard({ data }: { data: any }) {
  if (!data) return null;
  const color = INSIGHT_COLOR[data.insight_type] || 'white';
  const emoji = INSIGHT_EMOJI[data.insight_type] || '💭';
  return (
    <Box flexDirection="column" borderStyle="round" borderColor={color} paddingX={1} marginY={0}>
      <Box>
        <Text color={color}>{emoji} {data.insight_type}</Text>
        <Text color="yellow"> {'⭐'.repeat(data.importance || 3)}</Text>
        <Text color="gray" dimColor>  {data.id}</Text>
      </Box>
      <Text wrap="wrap">{data.content}</Text>
      {data.section && <Text color="gray" dimColor>§ {data.section}</Text>}
    </Box>
  );
}

// ─── 洞察列表 ──────────────────────────────────────
export function InsightList({ data }: { data: any[] }) {
  if (!data?.length) return <Text color="gray">没有洞察</Text>;
  return (
    <Box flexDirection="column" borderStyle="single" borderColor="cyan" paddingX={1} marginY={0}>
      <Text color="cyan" bold>💭 洞察列表 ({data.length})</Text>
      {data.slice(0, 10).map((ins, i) => {
        const emoji = INSIGHT_EMOJI[ins.insight_type] || '💭';
        return (
          <Box key={ins.id || i}>
            <Text color="gray">{emoji} </Text>
            <Text bold>{ins.id} </Text>
            <Text>{ins.content?.slice(0, 60)}</Text>
            <Text color="yellow"> {'⭐'.repeat(ins.importance || 3)}</Text>
          </Box>
        );
      })}
      {data.length > 10 && <Text color="gray">... 还有 {data.length - 10} 条</Text>}
    </Box>
  );
}

// ─── 疑问卡片 ──────────────────────────────────────
const STATUS_COLOR = { unsolved: 'red', partial: 'yellow', solved: 'green' };
const STATUS_EMOJI = { unsolved: '❓', partial: '🤔', solved: '✅' };

export function QuestionCard({ data }: { data: any }) {
  if (!data) return null;
  const color = STATUS_COLOR[data.status as keyof typeof STATUS_COLOR] || 'white';
  const emoji = STATUS_EMOJI[data.status as keyof typeof STATUS_EMOJI] || '❓';
  return (
    <Box flexDirection="column" borderStyle="round" borderColor={color} paddingX={1} marginY={0}>
      <Box>
        <Text color={color}>{emoji} [{data.status}]</Text>
        <Text color="gray" dimColor>  {data.id}</Text>
      </Box>
      <Text wrap="wrap">{data.content}</Text>
      <Text color="gray" dimColor>类型: {data.question_type} | 重要性: {'⭐'.repeat(data.importance || 3)}</Text>
      {data.answers?.length > 0 && (
        <Text color="green" dimColor>✓ {data.answers.length} 个答案</Text>
      )}
    </Box>
  );
}

// ─── 疑问列表 ──────────────────────────────────────
export function QuestionList({ data }: { data: any[] }) {
  if (!data?.length) return <Text color="gray">没有疑问</Text>;
  const groups = { unsolved: [] as any[], partial: [] as any[], solved: [] as any[] };
  data.forEach(q => {
    const g = groups[q.status as keyof typeof groups];
    if (g) g.push(q);
  });
  return (
    <Box flexDirection="column" borderStyle="single" borderColor="yellow" paddingX={1} marginY={0}>
      <Text color="yellow" bold>❓ 疑问列表 ({data.length})</Text>
      {groups.unsolved.length > 0 && (
        <Box flexDirection="column">
          <Text color="red">未解决 ({groups.unsolved.length}):</Text>
          {groups.unsolved.slice(0, 5).map((q, i) => (
            <Box key={q.id || i}>
              <Text color="red">  ❓ </Text>
              <Text bold>{q.id} </Text>
              <Text>{q.content?.slice(0, 55)}</Text>
            </Box>
          ))}
        </Box>
      )}
      {groups.partial.length > 0 && (
        <Box flexDirection="column">
          <Text color="yellow">部分解决 ({groups.partial.length}):</Text>
          {groups.partial.slice(0, 3).map((q, i) => (
            <Box key={q.id || i}>
              <Text color="yellow">  🤔 </Text>
              <Text bold>{q.id} </Text>
              <Text>{q.content?.slice(0, 55)}</Text>
            </Box>
          ))}
        </Box>
      )}
      {groups.solved.length > 0 && (
        <Text color="green">已解决: {groups.solved.length} 个</Text>
      )}
    </Box>
  );
}

// ─── 统计仪表盘 ────────────────────────────────────
export function Dashboard({ data }: { data: any }) {
  const papers = data?.papers?.total ?? '—';
  const insights = data?.insights?.total_insights ?? '—';
  const questions = data?.questions?.total_questions ?? '—';
  const solveRate = data?.questions?.solve_rate != null
    ? (data.questions.solve_rate * 100).toFixed(0) + '%' : '—';
  const ideas = data?.ideas?.total_ideas ?? '—';

  return (
    <Box flexDirection="column" borderStyle="double" borderColor="cyan" paddingX={2} marginY={0}>
      <Text color="cyan" bold>📊 OpenResearch 仪表盘</Text>
      <Box marginTop={1}>
        <Box flexDirection="column" marginRight={4}>
          <Text color="blue" bold>📄 论文</Text>
          <Text color="white" bold>{papers}</Text>
        </Box>
        <Box flexDirection="column" marginRight={4}>
          <Text color="cyan" bold>💭 洞察</Text>
          <Text color="white" bold>{insights}</Text>
        </Box>
        <Box flexDirection="column" marginRight={4}>
          <Text color="yellow" bold>❓ 疑问</Text>
          <Text color="white" bold>{questions}</Text>
        </Box>
        <Box flexDirection="column" marginRight={4}>
          <Text color="green" bold>✅ 解决率</Text>
          <Text color="white" bold>{solveRate}</Text>
        </Box>
        <Box flexDirection="column">
          <Text color="magenta" bold>💡 想法</Text>
          <Text color="white" bold>{ideas}</Text>
        </Box>
      </Box>
      <Text color="gray" dimColor>输入 /help 查看命令，或直接用中文提问</Text>
    </Box>
  );
}

// ─── 成功/错误提示 ─────────────────────────────────
export function SuccessCard({ data }: { data: string }) {
  return <Text color="green">✅ {data}</Text>;
}

export function ErrorCard({ data }: { data: string }) {
  return <Text color="red">❌ {data}</Text>;
}

// ─── 统一渲染入口 ──────────────────────────────────
export function renderCard(msg: ChatMessage) {
  switch (msg.type) {
    case 'user':          return <UserMessage key={msg.id} data={msg.data} />;
    case 'ai_text':       return <AIMessage key={msg.id} data={msg.data} />;
    case 'tool_call':     return <ToolCallCard key={msg.id} data={msg.data} />;
    case 'paper_card':    return <PaperCard key={msg.id} data={msg.data} />;
    case 'paper_list':    return <PaperList key={msg.id} data={msg.data} />;
    case 'insight_card':  return <InsightCard key={msg.id} data={msg.data} />;
    case 'insight_list':  return <InsightList key={msg.id} data={msg.data} />;
    case 'question_card': return <QuestionCard key={msg.id} data={msg.data} />;
    case 'question_list': return <QuestionList key={msg.id} data={msg.data} />;
    case 'dashboard':     return <Dashboard key={msg.id} data={msg.data} />;
    case 'success':       return <SuccessCard key={msg.id} data={msg.data} />;
    case 'error':         return <ErrorCard key={msg.id} data={msg.data} />;
    default:              return null;
  }
}
