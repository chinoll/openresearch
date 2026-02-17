"""
疑问系统 (Questions System)

专门用于记录和管理阅读论文时产生的疑问，追踪问题的解决过程。

核心功能：
- 记录阅读时的疑问
- 分类疑问类型（理解、方法、实验、应用等）
- 追踪疑问状态（未解决、部分解决、已解决）
- 记录答案和解决方案
- 关联论文和洞察
- 问题之间的关联
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path


@dataclass
class Answer:
    """问题的答案"""
    content: str                      # 答案内容
    source: str                       # 答案来源：paper_id 或 "own_thinking"
    section: Optional[str] = None     # 如果来自论文，具体章节
    page: Optional[int] = None        # 页码
    quote: Optional[str] = None       # 相关引用
    confidence: float = 0.8           # 答案置信度 0-1
    created_at: str = ""              # 创建时间

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class Question:
    """疑问/问题"""
    id: str                                    # 问题ID
    content: str                               # 问题内容
    paper_id: str                              # 来源论文
    section: Optional[str] = None              # 论文章节
    page: Optional[int] = None                 # 页码
    context: Optional[str] = None              # 问题上下文

    # 分类和属性
    question_type: str = "understanding"       # 问题类型
    importance: int = 3                        # 重要性 1-5
    difficulty: int = 3                        # 难度 1-5
    tags: List[str] = field(default_factory=list)

    # 状态追踪
    status: str = "unsolved"                   # unsolved, partial, solved
    answers: List[Answer] = field(default_factory=list)

    # 关联
    related_papers: List[str] = field(default_factory=list)  # 可能包含答案的论文
    related_insights: List[str] = field(default_factory=list)  # 相关洞察
    related_questions: List[str] = field(default_factory=list)  # 相关问题

    # 元数据
    created_at: str = ""
    resolved_at: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def add_answer(self, answer: Answer):
        """添加答案"""
        self.answers.append(answer)
        # 根据答案更新状态
        if answer.confidence >= 0.8:
            self.status = "solved"
            self.resolved_at = datetime.now().isoformat()
        elif self.status == "unsolved":
            self.status = "partial"

    def mark_solved(self):
        """标记为已解决"""
        self.status = "solved"
        self.resolved_at = datetime.now().isoformat()

    def get_best_answer(self) -> Optional[Answer]:
        """获取最佳答案（置信度最高）"""
        if not self.answers:
            return None
        return max(self.answers, key=lambda a: a.confidence)


@dataclass
class ReadingQuestionSession:
    """阅读疑问会话"""
    id: str
    paper_id: str
    start_time: str
    end_time: Optional[str] = None
    questions_count: int = 0
    sections_covered: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    def __post_init__(self):
        if not self.start_time:
            self.start_time = datetime.now().isoformat()


class QuestionsManager:
    """疑问系统管理器"""

    # 问题类型
    QUESTION_TYPES = {
        'understanding': '理解性问题（不理解概念、方法等）',
        'method': '方法问题（为什么这样设计、能否改进等）',
        'experiment': '实验问题（为什么这样实验、缺少什么实验等）',
        'application': '应用问题（能否应用到其他场景等）',
        'limitation': '局限性问题（方法的缺陷、适用范围等）',
        'extension': '扩展问题（如何改进、未来方向等）',
        'comparison': '比较问题（与其他方法的关系等）',
        'implementation': '实现问题（如何实现、技术细节等）'
    }

    def __init__(self, knowledge_dir: str = "knowledge"):
        self.knowledge_dir = Path(knowledge_dir)
        self.questions_dir = self.knowledge_dir / "questions"
        self.questions_dir.mkdir(parents=True, exist_ok=True)

        self.questions_file = self.questions_dir / "questions.json"
        self.sessions_file = self.questions_dir / "question_sessions.json"

        self.questions: Dict[str, Question] = {}
        self.sessions: Dict[str, ReadingQuestionSession] = {}
        self.current_session: Optional[ReadingQuestionSession] = None

        self._load_data()

    def _load_data(self):
        """加载数据"""
        # 加载问题
        if self.questions_file.exists():
            with open(self.questions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for q_data in data:
                    # 重建Answer对象
                    if 'answers' in q_data:
                        q_data['answers'] = [
                            Answer(**ans) for ans in q_data['answers']
                        ]
                    question = Question(**q_data)
                    self.questions[question.id] = question

        # 加载会话
        if self.sessions_file.exists():
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for s_data in data:
                    session = ReadingQuestionSession(**s_data)
                    self.sessions[session.id] = session

    def _save_data(self):
        """保存数据"""
        # 保存问题
        questions_list = []
        for question in self.questions.values():
            q_dict = asdict(question)
            questions_list.append(q_dict)

        with open(self.questions_file, 'w', encoding='utf-8') as f:
            json.dump(questions_list, f, ensure_ascii=False, indent=2)

        # 保存会话
        sessions_list = [asdict(s) for s in self.sessions.values()]
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump(sessions_list, f, ensure_ascii=False, indent=2)

    def start_session(self, paper_id: str) -> str:
        """开始问题记录会话"""
        session_id = f"qsession_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session = ReadingQuestionSession(
            id=session_id,
            paper_id=paper_id,
            start_time=datetime.now().isoformat()
        )
        self.sessions[session_id] = session
        self.current_session = session
        self._save_data()
        return session_id

    def end_session(self, notes: Optional[str] = None) -> Optional[ReadingQuestionSession]:
        """结束当前会话"""
        if not self.current_session:
            return None

        self.current_session.end_time = datetime.now().isoformat()
        if notes:
            self.current_session.notes = notes

        session = self.current_session
        self.current_session = None
        self._save_data()
        return session

    def create_question(
        self,
        content: str,
        paper_id: str,
        question_type: str = "understanding",
        section: Optional[str] = None,
        page: Optional[int] = None,
        context: Optional[str] = None,
        importance: int = 3,
        difficulty: int = 3,
        tags: Optional[List[str]] = None
    ) -> Question:
        """创建问题"""
        question_id = f"q_{len(self.questions) + 1:04d}"

        question = Question(
            id=question_id,
            content=content,
            paper_id=paper_id,
            section=section,
            page=page,
            context=context,
            question_type=question_type,
            importance=importance,
            difficulty=difficulty,
            tags=tags or []
        )

        self.questions[question_id] = question

        # 如果在会话中，更新会话统计
        if self.current_session and self.current_session.paper_id == paper_id:
            self.current_session.questions_count += 1
            if section and section not in self.current_session.sections_covered:
                self.current_session.sections_covered.append(section)

        self._save_data()
        return question

    def add_answer(
        self,
        question_id: str,
        content: str,
        source: str,
        section: Optional[str] = None,
        page: Optional[int] = None,
        quote: Optional[str] = None,
        confidence: float = 0.8
    ) -> bool:
        """为问题添加答案"""
        if question_id not in self.questions:
            return False

        answer = Answer(
            content=content,
            source=source,
            section=section,
            page=page,
            quote=quote,
            confidence=confidence
        )

        self.questions[question_id].add_answer(answer)
        self._save_data()
        return True

    def update_question_status(self, question_id: str, status: str) -> bool:
        """更新问题状态"""
        if question_id not in self.questions:
            return False

        self.questions[question_id].status = status
        if status == "solved":
            self.questions[question_id].resolved_at = datetime.now().isoformat()

        self._save_data()
        return True

    def link_questions(self, question_id1: str, question_id2: str) -> bool:
        """关联两个问题"""
        if question_id1 not in self.questions or question_id2 not in self.questions:
            return False

        # 双向关联
        if question_id2 not in self.questions[question_id1].related_questions:
            self.questions[question_id1].related_questions.append(question_id2)
        if question_id1 not in self.questions[question_id2].related_questions:
            self.questions[question_id2].related_questions.append(question_id1)

        self._save_data()
        return True

    def get_question(self, question_id: str) -> Optional[Question]:
        """获取问题"""
        return self.questions.get(question_id)

    def get_questions_by_paper(self, paper_id: str) -> List[Question]:
        """获取论文的所有问题"""
        return [q for q in self.questions.values() if q.paper_id == paper_id]

    def get_questions_by_type(self, question_type: str) -> List[Question]:
        """按类型获取问题"""
        return [q for q in self.questions.values() if q.question_type == question_type]

    def get_questions_by_status(self, status: str) -> List[Question]:
        """按状态获取问题"""
        return [q for q in self.questions.values() if q.status == status]

    def get_unsolved_questions(self, paper_id: Optional[str] = None) -> List[Question]:
        """获取未解决的问题"""
        questions = self.get_questions_by_status("unsolved")
        if paper_id:
            questions = [q for q in questions if q.paper_id == paper_id]
        return questions

    def search_questions(
        self,
        keyword: Optional[str] = None,
        paper_id: Optional[str] = None,
        question_type: Optional[str] = None,
        status: Optional[str] = None,
        min_importance: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> List[Question]:
        """搜索问题"""
        results = list(self.questions.values())

        if keyword:
            keyword_lower = keyword.lower()
            results = [
                q for q in results
                if keyword_lower in q.content.lower()
            ]

        if paper_id:
            results = [q for q in results if q.paper_id == paper_id]

        if question_type:
            results = [q for q in results if q.question_type == question_type]

        if status:
            results = [q for q in results if q.status == status]

        if min_importance:
            results = [q for q in results if q.importance >= min_importance]

        if tags:
            results = [
                q for q in results
                if any(tag in q.tags for tag in tags)
            ]

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self.questions)
        if total == 0:
            return {
                'total_questions': 0,
                'by_status': {},
                'by_type': {},
                'by_paper': {},
                'solve_rate': 0.0
            }

        # 按状态统计
        by_status = {}
        for q in self.questions.values():
            by_status[q.status] = by_status.get(q.status, 0) + 1

        # 按类型统计
        by_type = {}
        for q in self.questions.values():
            by_type[q.question_type] = by_type.get(q.question_type, 0) + 1

        # 按论文统计
        by_paper = {}
        for q in self.questions.values():
            by_paper[q.paper_id] = by_paper.get(q.paper_id, 0) + 1

        # 解决率
        solved = by_status.get('solved', 0)
        solve_rate = solved / total

        return {
            'total_questions': total,
            'by_status': by_status,
            'by_type': by_type,
            'by_paper': by_paper,
            'solve_rate': solve_rate,
            'total_sessions': len(self.sessions)
        }

    def suggest_related_papers(self, question_id: str) -> List[str]:
        """建议可能包含答案的论文（基于标签和内容）"""
        if question_id not in self.questions:
            return []

        question = self.questions[question_id]
        # 这里可以实现更复杂的推荐逻辑
        # 简单实现：返回已关联的论文
        return question.related_papers

    def export_questions_by_paper(self, paper_id: str, format: str = 'markdown') -> str:
        """导出论文的所有问题"""
        questions = self.get_questions_by_paper(paper_id)

        if format == 'markdown':
            lines = [f"# 论文 {paper_id} 的疑问列表\n"]

            # 按状态分组
            unsolved = [q for q in questions if q.status == 'unsolved']
            partial = [q for q in questions if q.status == 'partial']
            solved = [q for q in questions if q.status == 'solved']

            if unsolved:
                lines.append("## 未解决的问题\n")
                for q in unsolved:
                    lines.append(f"### {q.id}: {q.content}")
                    lines.append(f"- 类型: {q.question_type}")
                    lines.append(f"- 重要性: {q.importance}/5")
                    if q.section:
                        lines.append(f"- 章节: {q.section}")
                    if q.context:
                        lines.append(f"- 上下文: {q.context}")
                    lines.append("")

            if partial:
                lines.append("## 部分解决的问题\n")
                for q in partial:
                    lines.append(f"### {q.id}: {q.content}")
                    if q.answers:
                        lines.append("#### 当前答案:")
                        for ans in q.answers:
                            lines.append(f"- {ans.content} (置信度: {ans.confidence})")
                    lines.append("")

            if solved:
                lines.append("## 已解决的问题\n")
                for q in solved:
                    lines.append(f"### {q.id}: {q.content}")
                    best_answer = q.get_best_answer()
                    if best_answer:
                        lines.append(f"**答案**: {best_answer.content}")
                        lines.append(f"- 来源: {best_answer.source}")
                        if best_answer.section:
                            lines.append(f"- 章节: {best_answer.section}")
                    lines.append("")

            return "\n".join(lines)

        return json.dumps([asdict(q) for q in questions], ensure_ascii=False, indent=2)
