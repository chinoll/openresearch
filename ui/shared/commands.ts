// Slash 命令解析，TUI 和 Web 共用

export interface ParsedCommand {
  command: string;
  args: string[];
  raw: string;
}

export function parseCommand(input: string): ParsedCommand | null {
  if (!input.startsWith('/')) return null;
  const parts = input.slice(1).trim().split(/\s+/);
  return {
    command: parts[0].toLowerCase(),
    args: parts.slice(1),
    raw: input,
  };
}

// 命令别名映射
const COMMAND_ALIASES: Record<string, string> = {
  dl: 'download',
  ls: 'list',
  q: 'question',
  i: 'insight',
};

export function resolveCommand(cmd: string): string {
  return COMMAND_ALIASES[cmd] || cmd;
}

// 命令帮助信息
export const COMMAND_HELP: Record<string, string> = {
  'download':  '/download <arxiv_id>  — 下载论文，如 /download 1810.04805',
  'list':      '/list papers|insights|questions|ideas  — 列出内容',
  'insight':   '/insight <内容>  — 快速记录洞察',
  'question':  '/question <内容>  — 快速记录疑问',
  'idea':      '/idea <标题>  — 快速记录想法',
  'answer':    '/answer <question_id> <内容>  — 为疑问添加答案',
  'session':   '/session start <paper_id> | end  — 阅读会话管理',
  'stats':     '/stats  — 显示统计仪表盘',
  'help':      '/help  — 显示帮助',
};
