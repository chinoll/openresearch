"""
Structured Ideas System - 结构化学术想法系统
每个想法必须引用来源，支持想法交叉变异
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
class Source:
    """想法来源（论文引用）"""
    paper_id: str                    # 论文 ID
    section: Optional[str] = None    # 章节名称（如 "Introduction", "Method"）
    subsection: Optional[str] = None # 子章节
    page: Optional[int] = None       # 页码
    paragraph: Optional[int] = None  # 段落号
    quote: Optional[str] = None      # 原文引用
    notes: Optional[str] = None      # 笔记

    def to_dict(self) -> Dict:
        return asdict(self)

    def __str__(self) -> str:
        parts = [self.paper_id]
        if self.section:
            parts.append(f"§{self.section}")
        if self.subsection:
            parts.append(f"§{self.subsection}")
        if self.page:
            parts.append(f"p.{self.page}")
        return ", ".join(parts)


@dataclass
class IdeaRelation:
    """想法关系（用于交叉变异）"""
    idea_id: str                     # 相关想法 ID
    relationship: str                # 关系类型
    description: Optional[str] = None # 关系描述

    def to_dict(self) -> Dict:
        return asdict(self)


class RelationshipType:
    """想法关系类型"""
    EXTENDS = "extends"              # 扩展（A 扩展了 B）
    COMBINES = "combines"            # 组合（A 和 B 组合）
    CONTRADICTS = "contradicts"      # 矛盾（A 与 B 矛盾）
    REFINES = "refines"              # 精炼（A 精炼了 B）
    APPLIES = "applies"              # 应用（A 应用了 B）
    QUESTIONS = "questions"          # 质疑（A 质疑 B）
    SUPPORTS = "supports"            # 支持（A 支持 B）


@dataclass
class StructuredIdea:
    """结构化学术想法"""
    id: str
    title: str
    content: str
    type: str                        # "atomic" 原子想法 或 "composite" 组合想法
    sources: List[Source]            # 必须有来源（至少一个）
    created_at: str
    updated_at: str

    # 想法派生关系
    derived_from: List[IdeaRelation] = field(default_factory=list)  # 从哪些想法衍生

    # 分类和标签
    category: Optional[str] = None   # 类别（如 "concept", "method", "finding"）
    tags: List[str] = field(default_factory=list)

    # 状态
    status: str = "draft"            # draft, validated, published
    confidence: float = 1.0          # 置信度 (0-1)

    # 可选元数据
    research_question: Optional[str] = None  # 相关的研究问题
    implications: Optional[str] = None       # 影响和意义
    limitations: Optional[str] = None        # 局限性

    def to_dict(self) -> Dict:
        data = {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'type': self.type,
            'sources': [s.to_dict() for s in self.sources],
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'derived_from': [r.to_dict() for r in self.derived_from],
            'category': self.category,
            'tags': self.tags,
            'status': self.status,
            'confidence': self.confidence,
            'research_question': self.research_question,
            'implications': self.implications,
            'limitations': self.limitations
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'StructuredIdea':
        sources = [Source(**s) for s in data.get('sources', [])]
        derived_from = [IdeaRelation(**r) for r in data.get('derived_from', [])]

        return cls(
            id=data['id'],
            title=data['title'],
            content=data['content'],
            type=data['type'],
            sources=sources,
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            derived_from=derived_from,
            category=data.get('category'),
            tags=data.get('tags', []),
            status=data.get('status', 'draft'),
            confidence=data.get('confidence', 1.0),
            research_question=data.get('research_question'),
            implications=data.get('implications'),
            limitations=data.get('limitations')
        )


class StructuredIdeasManager:
    """结构化想法管理器"""

    from core.registry import ModuleRegistration, ModuleType, Capability, ConstructorParam
    REGISTRATION = ModuleRegistration(
        name="structured_ideas_manager",
        module_type=ModuleType.MANAGER,
        display_name="结构化想法管理器",
        description="管理结构化学术想法，支持引用来源和想法交叉变异",
        constructor_params=[
            ConstructorParam(name="storage_dir", from_config="storage.structured_ideas", default="knowledge/structured_ideas"),
        ],
        capabilities=[
            Capability(name="create_atomic_idea", description="创建原子想法", tags=["idea", "structured", "create"]),
            Capability(name="create_composite_idea", description="创建组合想法", tags=["idea", "structured", "create"]),
            Capability(name="get_idea_lineage", description="获取想法谱系", tags=["idea", "structured", "lineage"]),
        ],
    )
    del ModuleRegistration, ModuleType, Capability, ConstructorParam

    def __init__(self, storage_dir: Path):
        """
        初始化管理器

        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.ideas_dir = self.storage_dir / "structured_ideas"
        self.ideas_dir.mkdir(parents=True, exist_ok=True)

        # 索引文件
        self.index_file = self.storage_dir / "ideas_index.json"
        self.index = self._load_index()

        logger.info("Structured Ideas Manager initialized")

    def _load_index(self) -> Dict:
        """加载索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'ideas': {},
            'paper_to_ideas': {},      # 论文 → 想法
            'section_to_ideas': {},    # 章节 → 想法
            'tag_to_ideas': {},        # 标签 → 想法
            'category_to_ideas': {},   # 类别 → 想法
            'idea_graph': {}           # 想法关系图（邻接表）
        }

    def _save_index(self):
        """保存索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)

    def create_atomic_idea(self,
                          title: str,
                          content: str,
                          sources: List[Source],
                          category: str = None,
                          tags: List[str] = None,
                          **kwargs) -> StructuredIdea:
        """
        创建原子想法（必须有来源）

        Args:
            title: 想法标题
            content: 想法内容
            sources: 来源列表（至少一个）
            category: 类别
            tags: 标签
            **kwargs: 其他可选字段

        Returns:
            创建的想法
        """
        if not sources or len(sources) == 0:
            raise ValueError("Atomic idea must have at least one source")

        idea_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        idea = StructuredIdea(
            id=idea_id,
            title=title,
            content=content,
            type="atomic",
            sources=sources,
            created_at=now,
            updated_at=now,
            category=category,
            tags=tags or [],
            **kwargs
        )

        self._save_idea(idea)
        self._update_index(idea)

        logger.info(f"Created atomic idea: {idea_id} - {title}")
        return idea

    def create_composite_idea(self,
                             title: str,
                             content: str,
                             parent_ideas: List[Tuple[str, str]],  # [(idea_id, relationship), ...]
                             sources: List[Source] = None,
                             category: str = None,
                             tags: List[str] = None,
                             require_new_source: bool = False,  # 是否要求新来源
                             **kwargs) -> StructuredIdea:
        """
        创建组合想法（从其他想法衍生）

        Args:
            title: 想法标题
            content: 想法内容
            parent_ideas: 父想法列表 [(idea_id, relationship), ...]
            sources: 额外的来源（可选，会继承父想法的来源）
            category: 类别
            tags: 标签
            require_new_source: 是否要求提供新来源（支持组合逻辑）
            **kwargs: 其他可选字段

        Returns:
            创建的想法

        Note:
            建议为组合想法提供新的来源来支持组合逻辑。
            例如：如果组合了想法A和想法B，应该提供说明"为什么这样组合"的论文来源。
        """
        if not parent_ideas or len(parent_ideas) == 0:
            raise ValueError("Composite idea must have at least one parent idea")

        # 验证父想法存在
        for parent_id, _ in parent_ideas:
            if not self.get_idea(parent_id):
                raise ValueError(f"Parent idea not found: {parent_id}")

        # 检查是否需要新来源
        if require_new_source and (not sources or len(sources) == 0):
            logger.warning(
                "组合想法建议提供新的来源来支持组合逻辑。\n"
                "例如：说明'为什么这样组合'的论文章节。\n"
                "如果是探索性想法，可以设置 require_new_source=False"
            )

        idea_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        # 构建派生关系
        derived_from = [
            IdeaRelation(idea_id=pid, relationship=rel)
            for pid, rel in parent_ideas
        ]

        # 继承父想法的来源
        inherited_sources = []
        for parent_id, _ in parent_ideas:
            parent = self.get_idea(parent_id)
            if parent:
                inherited_sources.extend(parent.sources)

        # 合并来源（去重）
        all_sources = inherited_sources + (sources or [])
        unique_sources = self._deduplicate_sources(all_sources)

        idea = StructuredIdea(
            id=idea_id,
            title=title,
            content=content,
            type="composite",
            sources=unique_sources,
            created_at=now,
            updated_at=now,
            derived_from=derived_from,
            category=category,
            tags=tags or [],
            **kwargs
        )

        self._save_idea(idea)
        self._update_index(idea)
        self._update_idea_graph(idea)

        logger.info(f"Created composite idea: {idea_id} - {title}")
        return idea

    def get_idea(self, idea_id: str) -> Optional[StructuredIdea]:
        """获取想法"""
        idea_file = self.ideas_dir / f"{idea_id}.json"
        if not idea_file.exists():
            return None

        with open(idea_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return StructuredIdea.from_dict(data)

    def update_idea(self,
                   idea_id: str,
                   title: str = None,
                   content: str = None,
                   sources: List[Source] = None,
                   category: str = None,
                   tags: List[str] = None,
                   **kwargs) -> StructuredIdea:
        """更新想法"""
        idea = self.get_idea(idea_id)
        if not idea:
            raise ValueError(f"Idea not found: {idea_id}")

        if title:
            idea.title = title
        if content:
            idea.content = content
        if sources is not None:
            idea.sources = sources
        if category:
            idea.category = category
        if tags is not None:
            idea.tags = tags

        # 更新可选字段
        for key, value in kwargs.items():
            if hasattr(idea, key):
                setattr(idea, key, value)

        idea.updated_at = datetime.now().isoformat()

        self._save_idea(idea)
        self._update_index(idea)

        return idea

    def get_ideas_by_paper(self, paper_id: str) -> List[StructuredIdea]:
        """获取引用某篇论文的所有想法"""
        idea_ids = self.index['paper_to_ideas'].get(paper_id, [])
        return [self.get_idea(iid) for iid in idea_ids if self.get_idea(iid)]

    def get_ideas_by_section(self, paper_id: str, section: str) -> List[StructuredIdea]:
        """获取引用某论文特定章节的想法"""
        key = f"{paper_id}::{section}"
        idea_ids = self.index['section_to_ideas'].get(key, [])
        return [self.get_idea(iid) for iid in idea_ids if self.get_idea(iid)]

    def get_ideas_by_category(self, category: str) -> List[StructuredIdea]:
        """获取某类别的所有想法"""
        idea_ids = self.index['category_to_ideas'].get(category, [])
        return [self.get_idea(iid) for iid in idea_ids if self.get_idea(iid)]

    def get_children_ideas(self, idea_id: str) -> List[StructuredIdea]:
        """获取某想法的所有子想法（衍生想法）"""
        children_ids = self.index['idea_graph'].get(idea_id, [])
        return [self.get_idea(cid) for cid in children_ids if self.get_idea(cid)]

    def get_idea_lineage(self, idea_id: str) -> Dict:
        """
        获取想法的完整血统

        Returns:
            {
                'ancestors': [...],  # 祖先想法
                'self': idea,
                'descendants': [...]  # 后代想法
            }
        """
        idea = self.get_idea(idea_id)
        if not idea:
            return None

        # 获取祖先（递归向上）
        ancestors = []
        def get_ancestors(current_idea):
            for relation in current_idea.derived_from:
                parent = self.get_idea(relation.idea_id)
                if parent:
                    ancestors.append({
                        'idea': parent,
                        'relationship': relation.relationship
                    })
                    get_ancestors(parent)

        get_ancestors(idea)

        # 获取后代（递归向下）
        descendants = []
        def get_descendants(current_id):
            children = self.get_children_ideas(current_id)
            for child in children:
                # 找到关系类型
                rel_type = None
                for rel in child.derived_from:
                    if rel.idea_id == current_id:
                        rel_type = rel.relationship
                        break

                descendants.append({
                    'idea': child,
                    'relationship': rel_type
                })
                get_descendants(child.id)

        get_descendants(idea_id)

        return {
            'ancestors': ancestors,
            'self': idea,
            'descendants': descendants
        }

    def visualize_idea_network(self, root_idea_id: str = None) -> str:
        """
        可视化想法网络（文本形式）

        Args:
            root_idea_id: 根想法 ID（如果为 None，显示所有）

        Returns:
            文本形式的网络图
        """
        if root_idea_id:
            lineage = self.get_idea_lineage(root_idea_id)
            if not lineage:
                return f"Idea not found: {root_idea_id}"

            result = []

            # 显示祖先
            if lineage['ancestors']:
                result.append("=== Ancestors ===")
                for item in lineage['ancestors']:
                    result.append(f"  ← [{item['relationship']}] {item['idea'].title}")

            # 显示当前
            result.append(f"\n=== Current ===")
            result.append(f"  • {lineage['self'].title} ({lineage['self'].type})")
            result.append(f"    Sources: {len(lineage['self'].sources)}")

            # 显示后代
            if lineage['descendants']:
                result.append("\n=== Descendants ===")
                for item in lineage['descendants']:
                    result.append(f"  → [{item['relationship']}] {item['idea'].title}")

            return "\n".join(result)

        else:
            # 显示所有想法的网络
            all_ideas = self.get_all_ideas()
            result = ["=== Idea Network ===\n"]

            for idea in all_ideas:
                result.append(f"• {idea.title} ({idea.type})")
                if idea.derived_from:
                    for rel in idea.derived_from:
                        parent = self.get_idea(rel.idea_id)
                        if parent:
                            result.append(f"  ← [{rel.relationship}] {parent.title}")

            return "\n".join(result)

    def get_all_ideas(self, type_filter: str = None) -> List[StructuredIdea]:
        """获取所有想法"""
        ideas = []
        for idea_file in self.ideas_dir.glob("*.json"):
            idea = self.get_idea(idea_file.stem)
            if idea and (type_filter is None or idea.type == type_filter):
                ideas.append(idea)

        ideas.sort(key=lambda x: x.created_at, reverse=True)
        return ideas

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        all_ideas = self.get_all_ideas()
        atomic = [i for i in all_ideas if i.type == "atomic"]
        composite = [i for i in all_ideas if i.type == "composite"]

        return {
            'total_ideas': len(all_ideas),
            'atomic_ideas': len(atomic),
            'composite_ideas': len(composite),
            'papers_referenced': len(self.index['paper_to_ideas']),
            'sections_referenced': len(self.index['section_to_ideas']),
            'categories': len(self.index['category_to_ideas']),
            'total_sources': sum(len(i.sources) for i in all_ideas),
            'avg_sources_per_idea': sum(len(i.sources) for i in all_ideas) / max(len(all_ideas), 1)
        }

    # 内部方法

    def _save_idea(self, idea: StructuredIdea):
        """保存想法到文件"""
        idea_file = self.ideas_dir / f"{idea.id}.json"
        with open(idea_file, 'w', encoding='utf-8') as f:
            json.dump(idea.to_dict(), f, indent=2, ensure_ascii=False)

    def _update_index(self, idea: StructuredIdea):
        """更新索引"""
        # 主索引
        self.index['ideas'][idea.id] = {
            'title': idea.title,
            'type': idea.type,
            'category': idea.category,
            'created_at': idea.created_at
        }

        # 论文索引
        for source in idea.sources:
            if source.paper_id not in self.index['paper_to_ideas']:
                self.index['paper_to_ideas'][source.paper_id] = []
            if idea.id not in self.index['paper_to_ideas'][source.paper_id]:
                self.index['paper_to_ideas'][source.paper_id].append(idea.id)

            # 章节索引
            if source.section:
                key = f"{source.paper_id}::{source.section}"
                if key not in self.index['section_to_ideas']:
                    self.index['section_to_ideas'][key] = []
                if idea.id not in self.index['section_to_ideas'][key]:
                    self.index['section_to_ideas'][key].append(idea.id)

        # 标签索引
        for tag in idea.tags:
            if tag not in self.index['tag_to_ideas']:
                self.index['tag_to_ideas'][tag] = []
            if idea.id not in self.index['tag_to_ideas'][tag]:
                self.index['tag_to_ideas'][tag].append(idea.id)

        # 类别索引
        if idea.category:
            if idea.category not in self.index['category_to_ideas']:
                self.index['category_to_ideas'][idea.category] = []
            if idea.id not in self.index['category_to_ideas'][idea.category]:
                self.index['category_to_ideas'][idea.category].append(idea.id)

        self._save_index()

    def _update_idea_graph(self, idea: StructuredIdea):
        """更新想法关系图"""
        for relation in idea.derived_from:
            parent_id = relation.idea_id
            if parent_id not in self.index['idea_graph']:
                self.index['idea_graph'][parent_id] = []
            if idea.id not in self.index['idea_graph'][parent_id]:
                self.index['idea_graph'][parent_id].append(idea.id)

        self._save_index()

    def _deduplicate_sources(self, sources: List[Source]) -> List[Source]:
        """去重来源"""
        seen = set()
        unique = []

        for source in sources:
            key = (source.paper_id, source.section, source.page)
            if key not in seen:
                seen.add(key)
                unique.append(source)

        return unique


# 使用示例
if __name__ == "__main__":
    manager = StructuredIdeasManager(storage_dir=Path("./data/structured_research"))

    # 创建原子想法 1
    idea1 = manager.create_atomic_idea(
        title="注意力机制是软寻址",
        content="Attention 本质上是一种可微分的寻址机制...",
        sources=[
            Source(
                paper_id="1706_03762",
                section="Introduction",
                page=1,
                quote="We propose a new simple network architecture, the Transformer..."
            )
        ],
        category="concept",
        tags=["attention", "transformer"]
    )

    # 创建原子想法 2
    idea2 = manager.create_atomic_idea(
        title="多头注意力提供多个表示子空间",
        content="Multi-head attention allows the model to jointly attend...",
        sources=[
            Source(
                paper_id="1706_03762",
                section="Model Architecture",
                subsection="Multi-Head Attention",
                page=5,
                quote="Multi-head attention allows the model to jointly attend to information..."
            )
        ],
        category="method",
        tags=["multi-head", "attention"]
    )

    # 创建组合想法（扩展）
    idea3 = manager.create_composite_idea(
        title="注意力机制通过多头实现多视角理解",
        content="结合软寻址和多头机制，Transformer 可以从多个角度理解序列...",
        parent_ideas=[
            (idea1.id, RelationshipType.EXTENDS),
            (idea2.id, RelationshipType.COMBINES)
        ],
        category="insight",
        tags=["transformer", "synthesis"]
    )

    # 查看想法网络
    print(manager.visualize_idea_network(idea3.id))

    # 统计
    print("\n" + "="*60)
    stats = manager.get_statistics()
    print(json.dumps(stats, indent=2))
