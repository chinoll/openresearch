import React from 'react';
import ReactMarkdown from 'react-markdown';
import { ChatMessage } from '@shared/types';

// ─── 用户消息 ──────────────────────────────────────
export function UserMessage({ data }: { data: string }) {
  return (
    <div className="flex items-start gap-2 py-1">
      <span className="text-terminal-green font-bold shrink-0">&gt;</span>
      <span className="text-zinc-100">{data}</span>
    </div>
  );
}

// ─── AI 文字回复 ───────────────────────────────────
export function AIMessage({ data }: { data: string }) {
  if (!data) return null;
  return (
    <div className="border border-terminal-cyan/40 rounded-md p-3 my-1 bg-zinc-900/60">
      <div className="text-terminal-cyan text-xs mb-1 font-bold">● AI</div>
      <div className="prose-terminal text-sm text-zinc-200 leading-relaxed">
        <ReactMarkdown>{data}</ReactMarkdown>
      </div>
    </div>
  );
}

// ─── 工具调用通知 ──────────────────────────────────
export function ToolCallCard({ data }: { data: { name: string; input: any } }) {
  return (
    <div className="flex items-center gap-2 py-0.5 text-xs text-terminal-yellow">
      <span>⚡</span>
      <span className="font-bold">{data.name}</span>
      <span className="text-zinc-500">{JSON.stringify(data.input)}</span>
    </div>
  );
}

// ─── 论文卡片 ──────────────────────────────────────
export function PaperCard({ data }: { data: any }) {
  if (!data) return null;
  const meta = data.metadata || data;
  return (
    <div className="border border-blue-500/40 rounded-md p-3 my-1 bg-zinc-900/60">
      <div className="text-blue-400 font-bold text-sm">📄 {meta.title || data.paper_id || '未知论文'}</div>
      {meta.authors && (
        <div className="text-zinc-400 text-xs mt-0.5">
          👥 {(Array.isArray(meta.authors) ? meta.authors : [meta.authors]).slice(0, 3).join(', ')}
        </div>
      )}
      {meta.published && <div className="text-zinc-500 text-xs">📅 {meta.published?.slice(0, 10)}</div>}
      <div className="flex gap-2 mt-1">
        {data.paper_id && <span className="text-zinc-600 text-xs">ID: {data.paper_id}</span>}
        {data.source_type && (
          <span className="text-terminal-green text-xs">{data.source_type.toUpperCase()}</span>
        )}
      </div>
    </div>
  );
}

// ─── 论文列表 ──────────────────────────────────────
export function PaperList({ data }: { data: any[] }) {
  if (!data?.length) return <div className="text-zinc-500 text-sm">没有论文</div>;
  return (
    <div className="border border-blue-500/40 rounded-md p-3 my-1 bg-zinc-900/60">
      <div className="text-blue-400 font-bold text-sm mb-2">📄 论文列表 ({data.length})</div>
      <div className="space-y-0.5">
        {data.slice(0, 20).map((p, i) => (
          <div key={p.paper_id || i} className="flex items-center gap-2 text-xs">
            <span className="text-zinc-500 w-5 text-right">{i + 1}.</span>
            <span className="text-zinc-300 font-mono">{p.paper_id}</span>
            <span className="text-zinc-400 truncate">— {p.title?.slice(0, 60)}</span>
            {p.has_tex && <span className="text-terminal-green shrink-0">[TeX]</span>}
          </div>
        ))}
        {data.length > 20 && (
          <div className="text-zinc-500 text-xs">... 还有 {data.length - 20} 篇</div>
        )}
      </div>
    </div>
  );
}

// ─── 洞察卡片 ──────────────────────────────────────
const INSIGHT_STYLE: Record<string, string> = {
  observation: 'border-zinc-500/40 text-zinc-300',
  question: 'border-yellow-500/40 text-yellow-400',
  connection: 'border-cyan-500/40 text-cyan-400',
  surprise: 'border-purple-500/40 text-purple-400',
  critique: 'border-red-500/40 text-red-400',
  insight: 'border-green-500/40 text-green-400',
};
const INSIGHT_EMOJI: Record<string, string> = {
  observation: '👀', question: '❓', connection: '🔗',
  surprise: '😮', critique: '🔍', insight: '💡',
};

export function InsightCard({ data }: { data: any }) {
  if (!data) return null;
  const style = INSIGHT_STYLE[data.insight_type] || 'border-zinc-500/40 text-zinc-300';
  const emoji = INSIGHT_EMOJI[data.insight_type] || '💭';
  return (
    <div className={`border rounded-md p-3 my-1 bg-zinc-900/60 ${style}`}>
      <div className="flex items-center gap-2 text-xs mb-1">
        <span>{emoji} {data.insight_type}</span>
        <span>{'⭐'.repeat(data.importance || 3)}</span>
        <span className="text-zinc-600">{data.id}</span>
      </div>
      <div className="text-zinc-200 text-sm">{data.content}</div>
      {data.section && <div className="text-zinc-500 text-xs mt-0.5">§ {data.section}</div>}
    </div>
  );
}

// ─── 洞察列表 ──────────────────────────────────────
export function InsightList({ data }: { data: any[] }) {
  if (!data?.length) return <div className="text-zinc-500 text-sm">没有洞察</div>;
  return (
    <div className="border border-cyan-500/40 rounded-md p-3 my-1 bg-zinc-900/60">
      <div className="text-terminal-cyan font-bold text-sm mb-2">💭 洞察列表 ({data.length})</div>
      <div className="space-y-0.5">
        {data.slice(0, 12).map((ins, i) => {
          const emoji = INSIGHT_EMOJI[ins.insight_type] || '💭';
          return (
            <div key={ins.id || i} className="flex items-center gap-2 text-xs">
              <span>{emoji}</span>
              <span className="text-zinc-400 font-mono">{ins.id}</span>
              <span className="text-zinc-300 truncate">{ins.content?.slice(0, 65)}</span>
              <span className="shrink-0">{'⭐'.repeat(ins.importance || 3)}</span>
            </div>
          );
        })}
        {data.length > 12 && <div className="text-zinc-500 text-xs">... 还有 {data.length - 12} 条</div>}
      </div>
    </div>
  );
}

// ─── 疑问卡片 ──────────────────────────────────────
const Q_STYLE: Record<string, string> = {
  unsolved: 'border-red-500/40',
  partial: 'border-yellow-500/40',
  solved: 'border-green-500/40',
};
const Q_EMOJI: Record<string, string> = { unsolved: '❓', partial: '🤔', solved: '✅' };

export function QuestionCard({ data }: { data: any }) {
  if (!data) return null;
  return (
    <div className={`border rounded-md p-3 my-1 bg-zinc-900/60 ${Q_STYLE[data.status] || 'border-zinc-500/40'}`}>
      <div className="flex items-center gap-2 text-xs mb-1">
        <span>{Q_EMOJI[data.status] || '❓'} [{data.status}]</span>
        <span className="text-zinc-600">{data.id}</span>
      </div>
      <div className="text-zinc-200 text-sm">{data.content}</div>
      <div className="text-zinc-500 text-xs mt-0.5">
        {data.question_type} | {'⭐'.repeat(data.importance || 3)}
        {data.answers?.length > 0 && <span className="text-green-500 ml-2">✓ {data.answers.length} 个答案</span>}
      </div>
    </div>
  );
}

// ─── 疑问列表 ──────────────────────────────────────
export function QuestionList({ data }: { data: any[] }) {
  if (!data?.length) return <div className="text-zinc-500 text-sm">没有疑问</div>;
  const groups = { unsolved: [] as any[], partial: [] as any[], solved: [] as any[] };
  data.forEach(q => {
    const g = groups[q.status as keyof typeof groups];
    if (g) g.push(q);
  });
  return (
    <div className="border border-yellow-500/40 rounded-md p-3 my-1 bg-zinc-900/60">
      <div className="text-terminal-yellow font-bold text-sm mb-2">❓ 疑问列表 ({data.length})</div>
      {groups.unsolved.length > 0 && (
        <div className="mb-2">
          <div className="text-red-400 text-xs font-bold mb-1">未解决 ({groups.unsolved.length})</div>
          {groups.unsolved.slice(0, 6).map((q, i) => (
            <div key={q.id || i} className="flex items-center gap-2 text-xs">
              <span>❓</span>
              <span className="text-zinc-400 font-mono">{q.id}</span>
              <span className="text-zinc-300 truncate">{q.content?.slice(0, 55)}</span>
            </div>
          ))}
        </div>
      )}
      {groups.partial.length > 0 && (
        <div className="text-yellow-400 text-xs">🤔 部分解决: {groups.partial.length} 个</div>
      )}
      {groups.solved.length > 0 && (
        <div className="text-green-400 text-xs">✅ 已解决: {groups.solved.length} 个</div>
      )}
    </div>
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
    <div className="border-2 border-terminal-cyan/50 rounded-md p-4 my-1 bg-zinc-900/80">
      <div className="text-terminal-cyan font-bold mb-3">📊 OpenResearch 仪表盘</div>
      <div className="grid grid-cols-5 gap-4">
        {[
          { label: '📄 论文', value: papers, color: 'text-blue-400' },
          { label: '💭 洞察', value: insights, color: 'text-cyan-400' },
          { label: '❓ 疑问', value: questions, color: 'text-yellow-400' },
          { label: '✅ 解决率', value: solveRate, color: 'text-green-400' },
          { label: '💡 想法', value: ideas, color: 'text-purple-400' },
        ].map(({ label, value, color }) => (
          <div key={label} className="text-center">
            <div className={`text-xs ${color} font-bold`}>{label}</div>
            <div className="text-white text-2xl font-mono mt-1">{value}</div>
          </div>
        ))}
      </div>
      <div className="text-zinc-600 text-xs mt-3">输入 /help 查看命令，或直接用中文提问</div>
    </div>
  );
}

// ─── 成功/错误 ─────────────────────────────────────
export function SuccessCard({ data }: { data: string }) {
  return <div className="text-terminal-green text-sm py-0.5">✅ {data}</div>;
}

export function ErrorCard({ data }: { data: string }) {
  return <div className="text-red-400 text-sm py-0.5">❌ {data}</div>;
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
