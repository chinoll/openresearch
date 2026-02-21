"""
Structured Ideas CLI - 结构化学术想法管理工具
每个想法必须引用来源，支持想法交叉变异
"""

import asyncio
import argparse
from pathlib import Path
import sys
import json

sys.path.append(str(Path(__file__).parent.parent))

from plugins.ideas.structured import (
    StructuredIdeasManager,
    StructuredIdea,
    Source,
    RelationshipType
)


class StructuredIdeasCLI:
    """结构化想法管理 CLI"""

    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.manager = StructuredIdeasManager(storage_dir=self.storage_dir)

    def create_atomic_idea(self, paper_id: str = None):
        """创建原子想法（必须引用来源）"""
        print("\n📝 创建原子想法（必须引用至少一篇论文）")
        print("=" * 70)

        title = input("想法标题: ").strip()
        if not title:
            print("❌ 标题不能为空")
            return

        print("\n想法内容（输入 'END' 结束）:")
        content_lines = []
        while True:
            line = input()
            if line.strip() == 'END':
                break
            content_lines.append(line)

        content = '\n'.join(content_lines).strip()
        if not content:
            print("❌ 内容不能为空")
            return

        # 收集来源
        sources = []
        while True:
            print(f"\n--- 来源 {len(sources) + 1} ---")

            if not paper_id:
                paper_id_input = input("论文 ID (留空结束): ").strip()
                if not paper_id_input:
                    if len(sources) == 0:
                        print("❌ 至少需要一个来源")
                        continue
                    break
                current_paper_id = paper_id_input
            else:
                current_paper_id = paper_id
                paper_id = None  # 只用一次

            section = input("章节 (可选): ").strip() or None
            subsection = input("子章节 (可选): ").strip() or None
            page = input("页码 (可选): ").strip()
            page = int(page) if page else None

            print("原文引用（输入 'END' 结束，可选）:")
            quote_lines = []
            while True:
                line = input()
                if line.strip() == 'END':
                    break
                quote_lines.append(line)

            quote = '\n'.join(quote_lines).strip() or None

            notes = input("笔记 (可选): ").strip() or None

            source = Source(
                paper_id=current_paper_id,
                section=section,
                subsection=subsection,
                page=page,
                quote=quote,
                notes=notes
            )
            sources.append(source)

            if paper_id is None:  # 如果不是预设paper_id，询问是否继续
                more = input("\n添加更多来源？(y/N): ").strip().lower()
                if more != 'y':
                    break

        # 类别和标签
        category = input("\n类别 (concept/method/finding/insight): ").strip() or None
        tags_input = input("标签 (逗号分隔): ").strip()
        tags = [t.strip() for t in tags_input.split(',')] if tags_input else []

        # 创建想法
        try:
            idea = self.manager.create_atomic_idea(
                title=title,
                content=content,
                sources=sources,
                category=category,
                tags=tags
            )

            print(f"\n✓ 原子想法已创建!")
            print(f"  ID: {idea.id}")
            print(f"  标题: {idea.title}")
            print(f"  来源: {len(idea.sources)} 个")
            for i, src in enumerate(idea.sources, 1):
                print(f"    {i}. {src}")

        except Exception as e:
            print(f"❌ 创建失败: {e}")

        print("=" * 70)

    def create_composite_idea(self):
        """创建组合想法（从其他想法衍生）"""
        print("\n🔄 创建组合想法（交叉变异）")
        print("=" * 70)

        # 显示可用的想法
        all_ideas = self.manager.get_all_ideas()
        if len(all_ideas) < 1:
            print("❌ 需要至少一个已有想法才能创建组合想法")
            return

        print("\n可用想法:")
        for i, idea in enumerate(all_ideas[:20], 1):
            print(f"{i}. [{idea.id}] {idea.title} ({idea.type})")

        # 选择父想法
        parent_ideas = []
        print("\n选择要组合的想法（至少一个）:")

        while True:
            choice = input(f"\n输入想法编号或 ID (留空结束，已选{len(parent_ideas)}个): ").strip()

            if not choice:
                if len(parent_ideas) == 0:
                    print("❌ 至少需要一个父想法")
                    continue
                break

            # 解析选择
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(all_ideas):
                    parent_id = all_ideas[idx].id
                else:
                    parent_id = choice
            except ValueError:
                parent_id = choice

            # 验证想法存在
            parent = self.manager.get_idea(parent_id)
            if not parent:
                print(f"❌ 想法不存在: {parent_id}")
                continue

            # 选择关系类型
            print(f"\n与 '{parent.title}' 的关系:")
            print(f"1. extends (扩展)")
            print(f"2. combines (组合)")
            print(f"3. contradicts (矛盾)")
            print(f"4. refines (精炼)")
            print(f"5. applies (应用)")
            print(f"6. questions (质疑)")
            print(f"7. supports (支持)")

            rel_choice = input("选择关系类型 (1-7): ").strip()
            rel_map = {
                '1': RelationshipType.EXTENDS,
                '2': RelationshipType.COMBINES,
                '3': RelationshipType.CONTRADICTS,
                '4': RelationshipType.REFINES,
                '5': RelationshipType.APPLIES,
                '6': RelationshipType.QUESTIONS,
                '7': RelationshipType.SUPPORTS
            }

            relationship = rel_map.get(rel_choice, RelationshipType.EXTENDS)
            parent_ideas.append((parent_id, relationship))

            print(f"✓ 已添加: {parent.title} ({relationship})")

        # 输入新想法的内容
        print("\n" + "=" * 70)
        title = input("新想法标题: ").strip()
        if not title:
            print("❌ 标题不能为空")
            return

        print("\n新想法内容（描述如何组合/扩展父想法）:")
        print("输入 'END' 结束:")
        content_lines = []
        while True:
            line = input()
            if line.strip() == 'END':
                break
            content_lines.append(line)

        content = '\n'.join(content_lines).strip()
        if not content:
            print("❌ 内容不能为空")
            return

        # 重要：添加新来源（支持组合逻辑）
        print("\n" + "=" * 70)
        print("⚠️  重要提示：")
        print("组合想法建议提供新的来源来支持组合逻辑。")
        print("例如：说明'为什么这样组合'的论文章节。")
        print("=" * 70)

        print("\n是否添加新来源（支持组合逻辑）？(推荐: y/N): ")
        add_sources = input().strip().lower() == 'y'

        extra_sources = []
        if add_sources:
            print("\n请提供支持组合逻辑的来源:")
            print("（例如：综述论文、明确提到组合的后续论文）\n")

            while True:
                print(f"--- 新来源 {len(extra_sources) + 1} ---")

                paper_id_input = input("论文 ID (留空结束): ").strip()
                if not paper_id_input:
                    if len(extra_sources) == 0:
                        print("⚠️  未添加新来源，组合逻辑将缺乏明确支持")
                    break

                section = input("章节 (可选): ").strip() or None
                subsection = input("子章节 (可选): ").strip() or None
                page = input("页码 (可选): ").strip()
                page = int(page) if page else None

                print("原文引用（说明组合逻辑，输入 'END' 结束）:")
                quote_lines = []
                while True:
                    line = input()
                    if line.strip() == 'END':
                        break
                    quote_lines.append(line)

                quote = '\n'.join(quote_lines).strip() or None

                notes = input("笔记（例如：为何支持这个组合）: ").strip() or None

                source = Source(
                    paper_id=paper_id_input,
                    section=section,
                    subsection=subsection,
                    page=page,
                    quote=quote,
                    notes=notes
                )
                extra_sources.append(source)

                more = input("\n添加更多来源？(y/N): ").strip().lower()
                if more != 'y':
                    break

        # 类别和标签
        category = input("\n类别 (concept/method/finding/insight): ").strip() or None
        tags_input = input("标签 (逗号分隔): ").strip()
        tags = [t.strip() for t in tags_input.split(',')] if tags_input else []

        # 创建组合想法
        try:
            idea = self.manager.create_composite_idea(
                title=title,
                content=content,
                parent_ideas=parent_ideas,
                sources=extra_sources if extra_sources else None,
                category=category,
                tags=tags
            )

            print(f"\n✓ 组合想法已创建!")
            print(f"  ID: {idea.id}")
            print(f"  标题: {idea.title}")
            print(f"  类型: {idea.type}")
            print(f"  父想法: {len(parent_ideas)} 个")
            for pid, rel in parent_ideas:
                parent = self.manager.get_idea(pid)
                print(f"    - [{rel}] {parent.title}")
            print(f"  继承来源: {len(idea.sources)} 个")

        except Exception as e:
            print(f"❌ 创建失败: {e}")

        print("=" * 70)

    def list_ideas(self, type_filter: str = None):
        """列出想法"""
        ideas = self.manager.get_all_ideas(type_filter=type_filter)

        type_desc = {
            'atomic': '原子想法',
            'composite': '组合想法',
            None: '所有想法'
        }

        print(f"\n📚 {type_desc.get(type_filter)} ({len(ideas)} 个)")
        print("=" * 70)

        if not ideas:
            print("还没有任何想法")
            return

        for i, idea in enumerate(ideas, 1):
            icon = "🔷" if idea.type == "atomic" else "🔶"
            print(f"{i}. {icon} [{idea.id}] {idea.title}")
            print(f"   类型: {idea.type} | 类别: {idea.category or 'N/A'}")
            print(f"   来源: {len(idea.sources)} 个")

            if idea.derived_from:
                print(f"   衍生自: {len(idea.derived_from)} 个想法")
                for rel in idea.derived_from[:2]:  # 最多显示2个
                    parent = self.manager.get_idea(rel.idea_id)
                    if parent:
                        print(f"     - [{rel.relationship}] {parent.title}")

            print()

        print("=" * 70)

    def show_idea(self, idea_id: str):
        """显示想法详情"""
        idea = self.manager.get_idea(idea_id)

        if not idea:
            print(f"❌ 想法不存在: {idea_id}")
            return

        print(f"\n{'='*70}")
        print(f"{'🔷' if idea.type == 'atomic' else '🔶'} {idea.title}")
        print("=" * 70)

        print(f"\nID: {idea.id}")
        print(f"类型: {idea.type}")
        print(f"类别: {idea.category or 'N/A'}")
        print(f"状态: {idea.status}")
        print(f"创建: {idea.created_at[:10]}")

        if idea.tags:
            print(f"标签: {', '.join(idea.tags)}")

        print(f"\n--- 内容 ---")
        print(idea.content)

        print(f"\n--- 来源 ({len(idea.sources)} 个) ---")
        for i, source in enumerate(idea.sources, 1):
            print(f"{i}. {source}")
            if source.quote:
                print(f"   引用: {source.quote[:100]}...")
            if source.notes:
                print(f"   笔记: {source.notes}")

        if idea.derived_from:
            print(f"\n--- 衍生自 ({len(idea.derived_from)} 个想法) ---")
            for rel in idea.derived_from:
                parent = self.manager.get_idea(rel.idea_id)
                if parent:
                    print(f"  [{rel.relationship}] {parent.title}")

        # 显示子想法
        children = self.manager.get_children_ideas(idea.id)
        if children:
            print(f"\n--- 衍生出 ({len(children)} 个想法) ---")
            for child in children:
                # 找关系
                rel = next((r for r in child.derived_from if r.idea_id == idea.id), None)
                rel_type = rel.relationship if rel else "unknown"
                print(f"  [{rel_type}] {child.title}")

        if idea.research_question:
            print(f"\n--- 研究问题 ---")
            print(idea.research_question)

        if idea.implications:
            print(f"\n--- 影响 ---")
            print(idea.implications)

        print("=" * 70)

    def show_lineage(self, idea_id: str):
        """显示想法血统"""
        lineage = self.manager.get_idea_lineage(idea_id)

        if not lineage:
            print(f"❌ 想法不存在: {idea_id}")
            return

        print(f"\n🌳 想法血统: {lineage['self'].title}")
        print("=" * 70)

        # 祖先
        if lineage['ancestors']:
            print(f"\n=== 祖先 ({len(lineage['ancestors'])} 个) ===")
            for item in lineage['ancestors']:
                print(f"  ↑ [{item['relationship']}] {item['idea'].title}")
                print(f"    类型: {item['idea'].type} | ID: {item['idea'].id}")

        # 当前
        print(f"\n=== 当前想法 ===")
        idea = lineage['self']
        print(f"  • {idea.title}")
        print(f"    类型: {idea.type} | 类别: {idea.category}")
        print(f"    来源: {len(idea.sources)} 个")

        # 后代
        if lineage['descendants']:
            print(f"\n=== 后代 ({len(lineage['descendants'])} 个) ===")
            for item in lineage['descendants']:
                print(f"  ↓ [{item['relationship']}] {item['idea'].title}")
                print(f"    类型: {item['idea'].type} | ID: {item['idea'].id}")

        print("=" * 70)

    def show_paper_ideas(self, paper_id: str):
        """显示某论文的所有相关想法"""
        ideas = self.manager.get_ideas_by_paper(paper_id)

        print(f"\n📄 论文 {paper_id} 的相关想法 ({len(ideas)} 个)")
        print("=" * 70)

        if not ideas:
            print("没有想法引用此论文")
            return

        for i, idea in enumerate(ideas, 1):
            print(f"{i}. {idea.title} ({idea.type})")

            # 显示引用的具体章节
            relevant_sources = [s for s in idea.sources if s.paper_id == paper_id]
            for src in relevant_sources:
                parts = [f"    → {src.paper_id}"]
                if src.section:
                    parts.append(f"§{src.section}")
                if src.page:
                    parts.append(f"p.{src.page}")
                print(", ".join(parts))

            print()

        print("=" * 70)

    def visualize_network(self, root_idea_id: str = None):
        """可视化想法网络"""
        print("\n🕸️  想法关系网络")
        print("=" * 70)

        viz = self.manager.visualize_idea_network(root_idea_id)
        print(viz)

        print("=" * 70)

    def show_statistics(self):
        """显示统计"""
        stats = self.manager.get_statistics()

        print("\n📊 结构化想法统计")
        print("=" * 70)
        print(f"总想法数: {stats['total_ideas']}")
        print(f"  - 原子想法: {stats['atomic_ideas']}")
        print(f"  - 组合想法: {stats['composite_ideas']}")
        print(f"\n引用论文数: {stats['papers_referenced']}")
        print(f"引用章节数: {stats['sections_referenced']}")
        print(f"类别数: {stats['categories']}")
        print(f"\n总来源数: {stats['total_sources']}")
        print(f"平均每想法来源: {stats['avg_sources_per_idea']:.2f}")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Structured Ideas CLI - 结构化学术想法管理"
    )

    parser.add_argument('--atomic', type=str, metavar='PAPER_ID', nargs='?', const='',
                       help='创建原子想法（必须引用来源）')
    parser.add_argument('--composite', action='store_true',
                       help='创建组合想法（交叉变异）')
    parser.add_argument('--list', type=str, nargs='?', const='all',
                       help='列出想法 (all/atomic/composite)')
    parser.add_argument('--show', type=str, metavar='IDEA_ID',
                       help='显示想法详情')
    parser.add_argument('--lineage', type=str, metavar='IDEA_ID',
                       help='显示想法血统')
    parser.add_argument('--paper', type=str, metavar='PAPER_ID',
                       help='显示论文的所有相关想法')
    parser.add_argument('--network', type=str, metavar='IDEA_ID', nargs='?', const='',
                       help='可视化想法网络')
    parser.add_argument('--stats', action='store_true',
                       help='显示统计信息')

    args = parser.parse_args()

    # 初始化 CLI
    cli = StructuredIdeasCLI(storage_dir=Path("./data/structured_research"))

    # 执行命令
    if args.atomic is not None:
        cli.create_atomic_idea(paper_id=args.atomic if args.atomic else None)

    elif args.composite:
        cli.create_composite_idea()

    elif args.list:
        type_filter = None if args.list == 'all' else args.list
        cli.list_ideas(type_filter=type_filter)

    elif args.show:
        cli.show_idea(args.show)

    elif args.lineage:
        cli.show_lineage(args.lineage)

    elif args.paper:
        cli.show_paper_ideas(args.paper)

    elif args.network is not None:
        cli.visualize_network(root_idea_id=args.network if args.network else None)

    elif args.stats:
        cli.show_statistics()

    else:
        print("\n💎 结构化学术想法管理系统")
        print("=" * 70)
        print("每个想法必须引用来源，想法可以交叉变异")
        print("\n创建想法:")
        print("  python scripts/structured_ideas_cli.py --atomic [paper_id]")
        print("  python scripts/structured_ideas_cli.py --composite")
        print("\n查看想法:")
        print("  python scripts/structured_ideas_cli.py --list [all|atomic|composite]")
        print("  python scripts/structured_ideas_cli.py --show <idea_id>")
        print("  python scripts/structured_ideas_cli.py --lineage <idea_id>")
        print("\n按论文查看:")
        print("  python scripts/structured_ideas_cli.py --paper <paper_id>")
        print("\n可视化:")
        print("  python scripts/structured_ideas_cli.py --network [idea_id]")
        print("  python scripts/structured_ideas_cli.py --stats")
        print("=" * 70)


if __name__ == "__main__":
    main()
