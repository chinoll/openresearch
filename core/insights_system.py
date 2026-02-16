"""
Insights System - 洞察驱动的想法生成系统
阅读论文 → 记录洞察 → 提炼想法 → 组合想法
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Insight:
    """
    洞察 - 阅读论文时的即时理解

    特点：
    - 轻量级，快速记录
    - 可以碎片化
    - 必须关联到论文具体位置
    - 是想法的原材料
    """
    id: str
    content: str                     # 洞察内容（可以是一句话）
    paper_id: str                    # 论文 ID
    section: Optional[str] = None    # 章节
    page: Optional[int] = None       # 页码
    quote: Optional[str] = None      # 触发洞察的原文
    created_at: str = ""

    # 洞察类型
    insight_type: str = "observation"  # observation, question, connection, surprise

    # 情感/重要性
    importance: int = 3              # 1-5，重要性评分
    tags: List[str] = field(default_factory=list)

    # 是否已经转化为想法
    converted_to_idea: bool = False
    idea_ids: List[str] = field(default_factory=list)  # 基于此洞察生成的想法

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'Insight':
        return cls(**data)


class InsightType:
    """洞察类型"""
    OBSERVATION = "observation"      # 观察："这里用了X方法"
    QUESTION = "question"            # 疑问："为什么这样做？"
    CONNECTION = "connection"        # 联系："这和Y论文相似"
    SURPRISE = "surprise"            # 惊讶："没想到可以这样"
    CRITIQUE = "critique"            # 批评："这里有问题"
    INSIGHT = "insight"              # 顿悟："原来是这样！"


@dataclass
class IdeaFromInsights:
    """
    基于洞察生成的想法

    与 StructuredIdea 的区别：
    - 这个是从洞察提炼而来
    - 明确记录了源洞察
    """
    id: str
    title: str
    content: str
    source_insights: List[str]       # 源洞察 ID 列表
    paper_id: str                    # 主要论文
    created_at: str
    updated_at: str

    # 分类
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # 状态
    status: str = "draft"            # draft, refined, published
    confidence: float = 1.0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'IdeaFromInsights':
        return cls(**data)


class InsightsManager:
    """洞察管理器"""

    def __init__(self, storage_dir: Path):
        """
        初始化洞察管理器

        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.insights_dir = self.storage_dir / "insights"
        self.ideas_dir = self.storage_dir / "ideas_from_insights"

        self.insights_dir.mkdir(parents=True, exist_ok=True)
        self.ideas_dir.mkdir(parents=True, exist_ok=True)

        # 索引
        self.index_file = self.storage_dir / "insights_index.json"
        self.index = self._load_index()

        logger.info("Insights Manager initialized")

    def _load_index(self) -> Dict:
        """加载索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'insights': {},
            'ideas': {},
            'paper_to_insights': {},   # 论文 → 洞察
            'insight_to_ideas': {},    # 洞察 → 想法
            'reading_sessions': []     # 阅读会话
        }

    def _save_index(self):
        """保存索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)

    # ==================== 洞察管理 ====================

    def create_insight(self,
                      content: str,
                      paper_id: str,
                      section: str = None,
                      page: int = None,
                      quote: str = None,
                      insight_type: str = InsightType.OBSERVATION,
                      importance: int = 3,
                      tags: List[str] = None) -> Insight:
        """
        快速创建洞察

        Args:
            content: 洞察内容（一句话即可）
            paper_id: 论文 ID
            section: 章节
            page: 页码
            quote: 原文引用
            insight_type: 洞察类型
            importance: 重要性 (1-5)
            tags: 标签

        Returns:
            创建的洞察
        """
        insight_id = str(uuid.uuid4())[:8]

        insight = Insight(
            id=insight_id,
            content=content,
            paper_id=paper_id,
            section=section,
            page=page,
            quote=quote,
            insight_type=insight_type,
            importance=importance,
            tags=tags or []
        )

        self._save_insight(insight)
        self._update_index_insight(insight)

        logger.info(f"Created insight: {insight_id}")
        return insight

    def get_insight(self, insight_id: str) -> Optional[Insight]:
        """获取洞察"""
        insight_file = self.insights_dir / f"{insight_id}.json"
        if not insight_file.exists():
            return None

        with open(insight_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return Insight.from_dict(data)

    def get_insights_by_paper(self, paper_id: str) -> List[Insight]:
        """获取某论文的所有洞察"""
        insight_ids = self.index['paper_to_insights'].get(paper_id, [])
        return [self.get_insight(iid) for iid in insight_ids if self.get_insight(iid)]

    def get_insights_by_type(self, insight_type: str) -> List[Insight]:
        """按类型获取洞察"""
        all_insights = self.get_all_insights()
        return [i for i in all_insights if i.insight_type == insight_type]

    def get_unconverted_insights(self, paper_id: str = None) -> List[Insight]:
        """获取未转化为想法的洞察"""
        if paper_id:
            insights = self.get_insights_by_paper(paper_id)
        else:
            insights = self.get_all_insights()

        return [i for i in insights if not i.converted_to_idea]

    def get_all_insights(self) -> List[Insight]:
        """获取所有洞察"""
        insights = []
        for insight_file in self.insights_dir.glob("*.json"):
            insight = self.get_insight(insight_file.stem)
            if insight:
                insights.append(insight)

        insights.sort(key=lambda x: x.created_at, reverse=True)
        return insights

    # ==================== 想法生成 ====================

    def create_idea_from_insights(self,
                                  title: str,
                                  content: str,
                                  insight_ids: List[str],
                                  category: str = None,
                                  tags: List[str] = None) -> IdeaFromInsights:
        """
        从洞察生成想法

        Args:
            title: 想法标题
            content: 想法内容
            insight_ids: 源洞察 ID 列表
            category: 类别
            tags: 标签

        Returns:
            创建的想法
        """
        if not insight_ids:
            raise ValueError("Must provide at least one insight")

        # 验证洞察存在
        insights = []
        for iid in insight_ids:
            insight = self.get_insight(iid)
            if not insight:
                raise ValueError(f"Insight not found: {iid}")
            insights.append(insight)

        # 获取主要论文（第一个洞察的论文）
        paper_id = insights[0].paper_id

        idea_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        idea = IdeaFromInsights(
            id=idea_id,
            title=title,
            content=content,
            source_insights=insight_ids,
            paper_id=paper_id,
            created_at=now,
            updated_at=now,
            category=category,
            tags=tags or []
        )

        self._save_idea(idea)
        self._update_index_idea(idea)

        # 标记洞察已转化
        for insight in insights:
            insight.converted_to_idea = True
            insight.idea_ids.append(idea_id)
            self._save_insight(insight)

        logger.info(f"Created idea from {len(insights)} insights: {idea_id}")
        return idea

    def get_idea(self, idea_id: str) -> Optional[IdeaFromInsights]:
        """获取想法"""
        idea_file = self.ideas_dir / f"{idea_id}.json"
        if not idea_file.exists():
            return None

        with open(idea_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return IdeaFromInsights.from_dict(data)

    def get_all_ideas(self) -> List[IdeaFromInsights]:
        """获取所有想法"""
        ideas = []
        for idea_file in self.ideas_dir.glob("*.json"):
            idea = self.get_idea(idea_file.stem)
            if idea:
                ideas.append(idea)

        ideas.sort(key=lambda x: x.created_at, reverse=True)
        return ideas

    # ==================== 阅读会话 ====================

    def start_reading_session(self, paper_id: str, notes: str = "") -> str:
        """开始阅读会话"""
        session_id = str(uuid.uuid4())[:8]

        session = {
            'id': session_id,
            'paper_id': paper_id,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'notes': notes,
            'insights_created': [],
            'ideas_created': []
        }

        self.index['reading_sessions'].append(session)
        self._save_index()

        logger.info(f"Started reading session: {session_id} for paper {paper_id}")
        return session_id

    def end_reading_session(self, session_id: str) -> Dict:
        """结束阅读会话"""
        for session in self.index['reading_sessions']:
            if session['id'] == session_id:
                session['end_time'] = datetime.now().isoformat()
                self._save_index()
                return session

        raise ValueError(f"Session not found: {session_id}")

    def add_insight_to_session(self, session_id: str, insight_id: str):
        """添加洞察到会话"""
        for session in self.index['reading_sessions']:
            if session['id'] == session_id:
                if insight_id not in session['insights_created']:
                    session['insights_created'].append(insight_id)
                    self._save_index()
                return

    def get_session_summary(self, session_id: str) -> Dict:
        """获取会话摘要"""
        for session in self.index['reading_sessions']:
            if session['id'] == session_id:
                insights = [self.get_insight(iid) for iid in session['insights_created']]
                insights = [i for i in insights if i]

                return {
                    'session': session,
                    'num_insights': len(insights),
                    'insights_by_type': self._count_by_type(insights),
                    'unconverted_insights': len([i for i in insights if not i.converted_to_idea])
                }

        return None

    # ==================== 统计和分析 ====================

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        all_insights = self.get_all_insights()
        all_ideas = self.get_all_ideas()

        return {
            'total_insights': len(all_insights),
            'converted_insights': len([i for i in all_insights if i.converted_to_idea]),
            'unconverted_insights': len([i for i in all_insights if not i.converted_to_idea]),
            'total_ideas': len(all_ideas),
            'papers_with_insights': len(self.index['paper_to_insights']),
            'insights_by_type': self._count_by_type(all_insights),
            'avg_insights_per_paper': len(all_insights) / max(len(self.index['paper_to_insights']), 1)
        }

    def suggest_ideas_from_insights(self, paper_id: str = None) -> List[Dict]:
        """
        建议可以从洞察生成的想法

        基于：
        - 相似主题的洞察
        - 同一章节的洞察
        - 高重要性的洞察
        """
        if paper_id:
            insights = self.get_unconverted_insights(paper_id)
        else:
            insights = self.get_unconverted_insights()

        # 按章节分组
        by_section = {}
        for insight in insights:
            section = insight.section or "General"
            if section not in by_section:
                by_section[section] = []
            by_section[section].append(insight)

        # 建议
        suggestions = []
        for section, section_insights in by_section.items():
            if len(section_insights) >= 2:  # 至少2个洞察
                suggestions.append({
                    'section': section,
                    'num_insights': len(section_insights),
                    'insight_ids': [i.id for i in section_insights],
                    'preview': [i.content[:50] for i in section_insights[:3]]
                })

        return suggestions

    # ==================== 内部方法 ====================

    def _save_insight(self, insight: Insight):
        """保存洞察"""
        insight_file = self.insights_dir / f"{insight.id}.json"
        with open(insight_file, 'w', encoding='utf-8') as f:
            json.dump(insight.to_dict(), f, indent=2, ensure_ascii=False)

    def _save_idea(self, idea: IdeaFromInsights):
        """保存想法"""
        idea_file = self.ideas_dir / f"{idea.id}.json"
        with open(idea_file, 'w', encoding='utf-8') as f:
            json.dump(idea.to_dict(), f, indent=2, ensure_ascii=False)

    def _update_index_insight(self, insight: Insight):
        """更新洞察索引"""
        self.index['insights'][insight.id] = {
            'content': insight.content[:100],
            'paper_id': insight.paper_id,
            'created_at': insight.created_at
        }

        # 论文索引
        if insight.paper_id not in self.index['paper_to_insights']:
            self.index['paper_to_insights'][insight.paper_id] = []
        if insight.id not in self.index['paper_to_insights'][insight.paper_id]:
            self.index['paper_to_insights'][insight.paper_id].append(insight.id)

        self._save_index()

    def _update_index_idea(self, idea: IdeaFromInsights):
        """更新想法索引"""
        self.index['ideas'][idea.id] = {
            'title': idea.title,
            'paper_id': idea.paper_id,
            'created_at': idea.created_at
        }

        # 洞察→想法索引
        for insight_id in idea.source_insights:
            if insight_id not in self.index['insight_to_ideas']:
                self.index['insight_to_ideas'][insight_id] = []
            if idea.id not in self.index['insight_to_ideas'][insight_id]:
                self.index['insight_to_ideas'][insight_id].append(idea.id)

        self._save_index()

    def _count_by_type(self, insights: List[Insight]) -> Dict:
        """按类型统计洞察"""
        counts = {}
        for insight in insights:
            t = insight.insight_type
            counts[t] = counts.get(t, 0) + 1
        return counts


# 使用示例
if __name__ == "__main__":
    manager = InsightsManager(storage_dir=Path("./data/insights_research"))

    # 开始阅读会话
    session_id = manager.start_reading_session(
        paper_id="1706_03762",
        notes="阅读 Transformer 论文"
    )

    # 阅读时快速记录洞察
    insight1 = manager.create_insight(
        content="完全不用RNN，只用attention，这个想法很大胆",
        paper_id="1706_03762",
        section="Introduction",
        page=1,
        insight_type=InsightType.SURPRISE,
        importance=5
    )
    manager.add_insight_to_session(session_id, insight1.id)

    insight2 = manager.create_insight(
        content="Multi-head attention 类似于 CNN 的多个 filter",
        paper_id="1706_03762",
        section="Model Architecture",
        page=5,
        insight_type=InsightType.CONNECTION,
        importance=4
    )
    manager.add_insight_to_session(session_id, insight2.id)

    insight3 = manager.create_insight(
        content="位置编码用sin/cos，为什么不用学习的embedding？",
        paper_id="1706_03762",
        section="Model Architecture",
        page=6,
        insight_type=InsightType.QUESTION,
        importance=3
    )
    manager.add_insight_to_session(session_id, insight3.id)

    # 结束会话
    manager.end_reading_session(session_id)

    # 查看未转化的洞察
    unconverted = manager.get_unconverted_insights("1706_03762")
    print(f"\n未转化的洞察: {len(unconverted)} 个")

    # 从洞察生成想法
    idea = manager.create_idea_from_insights(
        title="Transformer的三个关键创新",
        content="""
        基于阅读洞察，Transformer有三个关键创新：
        1. 完全基于attention，去除循环
        2. Multi-head attention提供多视角
        3. 位置编码解决序列信息
        """,
        insight_ids=[insight1.id, insight2.id, insight3.id],
        category="concept",
        tags=["transformer", "attention"]
    )

    # 统计
    stats = manager.get_statistics()
    print(f"\n统计信息:")
    print(json.dumps(stats, indent=2))
