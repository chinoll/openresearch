// 共用类型定义

export interface Paper {
  paper_id: string;
  title: string;
  authors: string[];
  published?: string;
  abstract?: string;
  has_tex?: boolean;
  has_pdf?: boolean;
}

export interface Insight {
  id: string;
  content: string;
  paper_id: string;
  section?: string;
  page?: number;
  quote?: string;
  insight_type: 'observation' | 'question' | 'connection' | 'surprise' | 'critique' | 'insight';
  importance: number;
  tags: string[];
  converted_to_idea: boolean;
  created_at: string;
}

export interface Answer {
  content: string;
  source: string;
  section?: string;
  page?: number;
  quote?: string;
  confidence: number;
  created_at: string;
}

export interface Question {
  id: string;
  content: string;
  paper_id: string;
  section?: string;
  question_type: 'understanding' | 'method' | 'experiment' | 'application' | 'limitation' | 'extension' | 'comparison' | 'implementation';
  importance: number;
  difficulty: number;
  status: 'unsolved' | 'partial' | 'solved';
  answers: Answer[];
  tags: string[];
  created_at: string;
  resolved_at?: string;
}

export interface Idea {
  id: string;
  title: string;
  content: string;
  related_papers: string[];
  tags: string[];
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface Statistics {
  papers: { total: number };
  insights: {
    total_insights?: number;
    by_type?: Record<string, number>;
  };
  questions: {
    total_questions?: number;
    by_status?: Record<string, number>;
    solve_rate?: number;
  };
  ideas: {
    total_ideas?: number;
  };
}

// 消息流类型（内容区展示用）
export type MessageType =
  | 'user'           // 用户输入
  | 'ai_text'        // AI 文字回复
  | 'tool_call'      // 工具调用通知
  | 'tool_result'    // 工具结果展示
  | 'paper_card'     // 论文卡片
  | 'paper_list'     // 论文列表
  | 'insight_card'   // 洞察卡片
  | 'insight_list'   // 洞察列表
  | 'question_card'  // 疑问卡片
  | 'question_list'  // 疑问列表
  | 'idea_card'      // 想法卡片
  | 'dashboard'      // 统计仪表盘
  | 'error'          // 错误信息
  | 'success';       // 成功提示

export interface ChatMessage {
  id: string;
  type: MessageType;
  data: any;
  timestamp: Date;
}
