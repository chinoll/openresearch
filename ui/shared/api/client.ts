// API 客户端，TUI 和 Web 共用

const BASE_URL = process.env.API_URL || 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ─── 论文 ─────────────────────────────────────────
export const papersApi = {
  list: () => request<{ papers: any[] }>('/api/papers/'),
  get: (id: string) => request<any>(`/api/papers/${id}`),
  download: (arxivId: string) =>
    request<any>('/api/papers/download', {
      method: 'POST',
      body: JSON.stringify({ arxiv_id: arxivId }),
    }),
};

// ─── 洞察 ─────────────────────────────────────────
export const insightsApi = {
  list: (params?: { paper_id?: string; insight_type?: string; unconverted_only?: boolean }) => {
    const qs = new URLSearchParams(params as any).toString();
    return request<{ insights: any[] }>(`/api/insights/${qs ? '?' + qs : ''}`);
  },
  create: (data: {
    content: string;
    paper_id: string;
    insight_type?: string;
    importance?: number;
    section?: string;
    quote?: string;
    tags?: string[];
  }) =>
    request<any>('/api/insights/', { method: 'POST', body: JSON.stringify(data) }),
  stats: () => request<any>('/api/insights/stats'),
  startSession: (paper_id: string) =>
    request<any>('/api/insights/session/start', {
      method: 'POST',
      body: JSON.stringify({ paper_id }),
    }),
  endSession: () =>
    request<any>('/api/insights/session/end', { method: 'POST', body: '{}' }),
};

// ─── 疑问 ─────────────────────────────────────────
export const questionsApi = {
  list: (params?: {
    paper_id?: string;
    status?: string;
    question_type?: string;
    min_importance?: number;
  }) => {
    const qs = new URLSearchParams(params as any).toString();
    return request<{ questions: any[] }>(`/api/questions/${qs ? '?' + qs : ''}`);
  },
  get: (id: string) => request<any>(`/api/questions/${id}`),
  create: (data: {
    content: string;
    paper_id: string;
    question_type?: string;
    importance?: number;
    section?: string;
    context?: string;
    tags?: string[];
  }) =>
    request<any>('/api/questions/', { method: 'POST', body: JSON.stringify(data) }),
  addAnswer: (
    questionId: string,
    data: {
      content: string;
      source: string;
      section?: string;
      quote?: string;
      confidence?: number;
    }
  ) =>
    request<any>(`/api/questions/${questionId}/answers`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateStatus: (questionId: string, status: string) =>
    request<any>(`/api/questions/${questionId}/status?status=${status}`, {
      method: 'PUT',
    }),
  stats: () => request<any>('/api/questions/stats'),
};

// ─── 想法 ─────────────────────────────────────────
export const ideasApi = {
  list: (params?: { status?: string; tag?: string }) => {
    const qs = new URLSearchParams(params as any).toString();
    return request<{ ideas: any[] }>(`/api/ideas/${qs ? '?' + qs : ''}`);
  },
  create: (data: {
    title: string;
    content: string;
    related_papers?: string[];
    tags?: string[];
  }) =>
    request<any>('/api/ideas/', { method: 'POST', body: JSON.stringify(data) }),
  stats: () => request<any>('/api/ideas/stats'),
};

// ─── 全局统计 ──────────────────────────────────────
export const statsApi = {
  global: () => request<any>('/api/stats'),
};

// ─── AI 对话（SSE 流式）─────────────────────────────
export async function* streamChat(
  message: string,
  history: { role: string; content: string }[] = []
): AsyncGenerator<{ type: string; [key: string]: any }> {
  const res = await fetch(`${BASE_URL}/api/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  });

  if (!res.ok || !res.body) {
    throw new Error(`Chat request failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6));
        } catch {}
      }
    }
  }
}
