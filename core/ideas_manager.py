"""
Ideas Manager - 研究想法管理系统
支持串行和并行两种阅读模式
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
class Idea:
    """研究想法/笔记"""
    id: str
    title: str
    content: str
    created_at: str
    updated_at: str
    version: int = 1
    related_papers: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    status: str = "active"  # active, refined, archived
    parent_id: Optional[str] = None  # 如果是更新版本，指向原想法

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ReadingSession:
    """阅读会话 - 追踪一次阅读活动"""
    id: str
    mode: str  # serial（串行）或 parallel（并行）
    papers: List[str]  # 论文 ID 列表
    ideas_created: List[str]  # 产生的想法 ID
    start_time: str
    end_time: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


class IdeasManager:
    """研究想法管理器"""

    def __init__(self, storage_dir: Path):
        """
        初始化想法管理器

        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.ideas_dir = self.storage_dir / "ideas"
        self.sessions_dir = self.storage_dir / "reading_sessions"

        self.ideas_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # 索引文件
        self.index_file = self.storage_dir / "ideas_index.json"
        self.ideas_index = self._load_index()

        logger.info("Ideas Manager initialized")

    def _load_index(self) -> Dict:
        """加载想法索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'ideas': {},
            'paper_to_ideas': {},  # 论文 -> 想法映射
            'tag_to_ideas': {},    # 标签 -> 想法映射
        }

    def _save_index(self):
        """保存索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.ideas_index, f, indent=2, ensure_ascii=False)

    def create_idea(self,
                   title: str,
                   content: str,
                   related_papers: List[str] = None,
                   tags: List[str] = None,
                   parent_id: str = None) -> Idea:
        """
        创建新想法

        Args:
            title: 想法标题
            content: 想法内容
            related_papers: 相关论文 ID 列表
            tags: 标签列表
            parent_id: 父想法 ID（如果是更新版本）

        Returns:
            创建的想法对象
        """
        idea_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        # 如果是更新版本，获取版本号
        version = 1
        if parent_id:
            parent = self.get_idea(parent_id)
            if parent:
                version = parent.version + 1

        idea = Idea(
            id=idea_id,
            title=title,
            content=content,
            created_at=now,
            updated_at=now,
            version=version,
            related_papers=related_papers or [],
            tags=tags or [],
            parent_id=parent_id
        )

        # 保存想法
        self._save_idea(idea)

        # 更新索引
        self._update_index(idea)

        logger.info(f"Created idea: {idea_id} - {title}")
        return idea

    def update_idea(self,
                   idea_id: str,
                   title: str = None,
                   content: str = None,
                   related_papers: List[str] = None,
                   tags: List[str] = None,
                   create_new_version: bool = False) -> Idea:
        """
        更新想法

        Args:
            idea_id: 想法 ID
            title: 新标题（可选）
            content: 新内容（可选）
            related_papers: 新的相关论文列表（可选）
            tags: 新的标签列表（可选）
            create_new_version: 是否创建新版本

        Returns:
            更新后的想法对象
        """
        original_idea = self.get_idea(idea_id)
        if not original_idea:
            raise ValueError(f"Idea not found: {idea_id}")

        if create_new_version:
            # 创建新版本
            new_idea = self.create_idea(
                title=title or original_idea.title,
                content=content or original_idea.content,
                related_papers=related_papers or original_idea.related_papers,
                tags=tags or original_idea.tags,
                parent_id=idea_id
            )

            # 标记原想法为已精炼
            original_idea.status = "refined"
            self._save_idea(original_idea)

            return new_idea
        else:
            # 直接更新
            if title:
                original_idea.title = title
            if content:
                original_idea.content = content
            if related_papers is not None:
                original_idea.related_papers = related_papers
            if tags is not None:
                original_idea.tags = tags

            original_idea.updated_at = datetime.now().isoformat()
            self._save_idea(original_idea)

            return original_idea

    def get_idea(self, idea_id: str) -> Optional[Idea]:
        """获取想法"""
        idea_file = self.ideas_dir / f"{idea_id}.json"
        if not idea_file.exists():
            return None

        with open(idea_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return Idea(**data)

    def get_ideas_by_paper(self, paper_id: str) -> List[Idea]:
        """获取与某篇论文相关的所有想法"""
        idea_ids = self.ideas_index['paper_to_ideas'].get(paper_id, [])
        return [self.get_idea(iid) for iid in idea_ids if self.get_idea(iid)]

    def get_ideas_by_tag(self, tag: str) -> List[Idea]:
        """获取某个标签的所有想法"""
        idea_ids = self.ideas_index['tag_to_ideas'].get(tag, [])
        return [self.get_idea(iid) for iid in idea_ids if self.get_idea(iid)]

    def get_all_ideas(self, status: str = None) -> List[Idea]:
        """获取所有想法"""
        ideas = []
        for idea_file in self.ideas_dir.glob("*.json"):
            idea = self.get_idea(idea_file.stem)
            if idea and (status is None or idea.status == status):
                ideas.append(idea)

        # 按创建时间倒序排列
        ideas.sort(key=lambda x: x.created_at, reverse=True)
        return ideas

    def get_idea_evolution(self, idea_id: str) -> List[Idea]:
        """获取想法的演进历史"""
        evolution = []
        current = self.get_idea(idea_id)

        if not current:
            return []

        # 向前追溯
        while current:
            evolution.insert(0, current)
            if current.parent_id:
                current = self.get_idea(current.parent_id)
            else:
                break

        # 向后查找（找到所有子版本）
        def find_children(parent_id: str) -> List[Idea]:
            children = []
            for idea in self.get_all_ideas():
                if idea.parent_id == parent_id:
                    children.append(idea)
                    children.extend(find_children(idea.id))
            return children

        if evolution:
            children = find_children(evolution[-1].id)
            evolution.extend(children)

        return evolution

    def start_reading_session(self,
                             mode: str,
                             papers: List[str] = None,
                             notes: str = "") -> ReadingSession:
        """
        开始一个阅读会话

        Args:
            mode: 'serial'（串行）或 'parallel'（并行）
            papers: 计划阅读的论文列表
            notes: 会话笔记

        Returns:
            阅读会话对象
        """
        session_id = str(uuid.uuid4())[:8]

        session = ReadingSession(
            id=session_id,
            mode=mode,
            papers=papers or [],
            ideas_created=[],
            start_time=datetime.now().isoformat(),
            notes=notes
        )

        self._save_session(session)

        logger.info(f"Started {mode} reading session: {session_id}")
        return session

    def end_reading_session(self, session_id: str, notes: str = "") -> ReadingSession:
        """结束阅读会话"""
        session = self._load_session(session_id)
        if session:
            session.end_time = datetime.now().isoformat()
            if notes:
                session.notes = notes
            self._save_session(session)
            logger.info(f"Ended reading session: {session_id}")

        return session

    def add_idea_to_session(self, session_id: str, idea_id: str):
        """将想法添加到阅读会话"""
        session = self._load_session(session_id)
        if session and idea_id not in session.ideas_created:
            session.ideas_created.append(idea_id)
            self._save_session(session)

    def get_recent_sessions(self, limit: int = 10) -> List[ReadingSession]:
        """获取最近的阅读会话"""
        sessions = []
        for session_file in self.sessions_dir.glob("*.json"):
            session = self._load_session(session_file.stem)
            if session:
                sessions.append(session)

        sessions.sort(key=lambda x: x.start_time, reverse=True)
        return sessions[:limit]

    def search_ideas(self, query: str, search_in: List[str] = None) -> List[Idea]:
        """
        搜索想法

        Args:
            query: 搜索关键词
            search_in: 搜索范围 ['title', 'content', 'tags']

        Returns:
            匹配的想法列表
        """
        if search_in is None:
            search_in = ['title', 'content', 'tags']

        query_lower = query.lower()
        results = []

        for idea in self.get_all_ideas():
            match = False

            if 'title' in search_in and query_lower in idea.title.lower():
                match = True
            if 'content' in search_in and query_lower in idea.content.lower():
                match = True
            if 'tags' in search_in and any(query_lower in tag.lower() for tag in idea.tags):
                match = True

            if match:
                results.append(idea)

        return results

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        all_ideas = self.get_all_ideas()

        return {
            'total_ideas': len(all_ideas),
            'active_ideas': len([i for i in all_ideas if i.status == 'active']),
            'refined_ideas': len([i for i in all_ideas if i.status == 'refined']),
            'total_tags': len(self.ideas_index['tag_to_ideas']),
            'papers_with_ideas': len(self.ideas_index['paper_to_ideas']),
            'total_sessions': len(list(self.sessions_dir.glob("*.json")))
        }

    # 内部方法

    def _save_idea(self, idea: Idea):
        """保存想法到文件"""
        idea_file = self.ideas_dir / f"{idea.id}.json"
        with open(idea_file, 'w', encoding='utf-8') as f:
            json.dump(idea.to_dict(), f, indent=2, ensure_ascii=False)

    def _update_index(self, idea: Idea):
        """更新索引"""
        # 添加到主索引
        self.ideas_index['ideas'][idea.id] = {
            'title': idea.title,
            'created_at': idea.created_at,
            'tags': idea.tags,
            'papers': idea.related_papers
        }

        # 更新论文映射
        for paper_id in idea.related_papers:
            if paper_id not in self.ideas_index['paper_to_ideas']:
                self.ideas_index['paper_to_ideas'][paper_id] = []
            if idea.id not in self.ideas_index['paper_to_ideas'][paper_id]:
                self.ideas_index['paper_to_ideas'][paper_id].append(idea.id)

        # 更新标签映射
        for tag in idea.tags:
            if tag not in self.ideas_index['tag_to_ideas']:
                self.ideas_index['tag_to_ideas'][tag] = []
            if idea.id not in self.ideas_index['tag_to_ideas'][tag]:
                self.ideas_index['tag_to_ideas'][tag].append(idea.id)

        self._save_index()

    def _save_session(self, session: ReadingSession):
        """保存阅读会话"""
        session_file = self.sessions_dir / f"{session.id}.json"
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)

    def _load_session(self, session_id: str) -> Optional[ReadingSession]:
        """加载阅读会话"""
        session_file = self.sessions_dir / f"{session_id}.json"
        if not session_file.exists():
            return None

        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return ReadingSession(**data)


# 使用示例
if __name__ == "__main__":
    manager = IdeasManager(storage_dir=Path("./data/research_notes"))

    # 串行模式示例
    print("=== 串行模式示例 ===")
    serial_session = manager.start_reading_session(
        mode="serial",
        papers=["paper1", "paper2"],
        notes="深度阅读 Transformer 相关论文"
    )

    # 阅读 paper1 后记录想法
    idea1 = manager.create_idea(
        title="注意力机制的本质是动态权重",
        content="通过 Q、K、V 三个矩阵，注意力机制实现了内容寻址...",
        related_papers=["paper1"],
        tags=["attention", "transformer"]
    )
    manager.add_idea_to_session(serial_session.id, idea1.id)

    # 阅读 paper2 后更新想法
    idea1_v2 = manager.update_idea(
        idea1.id,
        content="结合 paper2，发现注意力机制不仅是动态权重，还是一种软寻址...",
        create_new_version=True
    )

    # 并行模式示例
    print("\n=== 并行模式示例 ===")
    parallel_session = manager.start_reading_session(
        mode="parallel",
        papers=["paper3", "paper4", "paper5"],
        notes="快速浏览 BERT 系列论文"
    )

    # 快速浏览后记录初步想法
    idea2 = manager.create_idea(
        title="预训练的关键：大规模无监督数据",
        content="BERT、GPT 等都强调预训练的重要性...",
        related_papers=["paper3", "paper4", "paper5"],
        tags=["pretraining", "BERT"]
    )

    # 查看统计
    print("\n=== 统计信息 ===")
    stats = manager.get_statistics()
    print(json.dumps(stats, indent=2))

    # 查看想法演进
    print("\n=== 想法演进 ===")
    evolution = manager.get_idea_evolution(idea1.id)
    for i, idea in enumerate(evolution, 1):
        print(f"v{idea.version}: {idea.title}")
