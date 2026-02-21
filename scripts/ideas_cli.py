"""
Ideas CLI - 想法管理命令行工具
纯文本化记忆管理，支持串行和并行阅读模式
"""

import asyncio
import argparse
from pathlib import Path
import sys
import json

sys.path.append(str(Path(__file__).parent.parent))

from plugins.ideas.manager import IdeasManager
from plugins.ideas.agent import InsightAgent
from core.base_agent import AgentConfig


class IdeasCLI:
    """想法管理命令行界面"""

    def __init__(self, storage_dir: Path, config: dict = None):
        self.storage_dir = Path(storage_dir)

        # 初始化想法管理器
        self.ideas_manager = IdeasManager(storage_dir=self.storage_dir)

        # 初始化 Insight Agent
        llm_config = config.get('llm', {}) if config else {}
        agent_config = AgentConfig(
            name="InsightAgent",
            model=llm_config.get('model', 'claude-sonnet-4-5-20250929'),
            api_key=llm_config.get('api_key', ''),
            temperature=0.7
        )

        self.insight_agent = InsightAgent(
            config=agent_config,
            ideas_manager=self.ideas_manager
        )

        # 当前活动会话
        self.current_session = None

    async def start_session(self, mode: str, papers: list = None):
        """开始阅读会话"""
        mode_name = "串行深度阅读" if mode == "serial" else "并行快速浏览"

        print(f"\n📖 开始新的阅读会话: {mode_name}")
        print("=" * 70)

        notes = input("📝 会话笔记（可选，按回车跳过）: ").strip()

        self.current_session = self.ideas_manager.start_reading_session(
            mode=mode,
            papers=papers or [],
            notes=notes or f"{mode_name}模式"
        )

        print(f"\n✓ 会话已开始 (ID: {self.current_session.id})")

        if mode == "serial":
            print("\n💡 串行模式建议:")
            print("  - 每读完一篇论文就记录想法")
            print("  - 深入思考，详细记录")
            print("  - 如果有新的理解，更新之前的想法")
        else:
            print("\n💡 并行模式建议:")
            print("  - 快速浏览多篇论文")
            print("  - 记录初步印象和想法")
            print("  - 后续可以回顾和深化")

        print("=" * 70)

    async def record_idea(self, paper_id: str = None):
        """记录新想法"""
        print("\n💭 记录新想法")
        print("=" * 70)

        title = input("标题: ").strip()
        if not title:
            print("❌ 标题不能为空")
            return

        print("\n内容（输入完成后输入 'END' 结束，或按 Ctrl+D）:")
        content_lines = []
        try:
            while True:
                line = input()
                if line.strip() == 'END':
                    break
                content_lines.append(line)
        except EOFError:
            pass

        content = '\n'.join(content_lines).strip()

        if not content:
            print("❌ 内容不能为空")
            return

        # 使用 Insight Agent 记录想法
        result = await self.insight_agent.process({
            'command': 'record_idea',
            'title': title,
            'content': content,
            'paper_id': paper_id,
            'auto_enhance': True
        })

        if result.get('success'):
            data = result['data']
            idea = data['idea']

            print("\n✓ 想法已记录!")
            print(f"  ID: {idea['id']}")

            if data.get('tags_extracted'):
                print(f"  标签: {', '.join(data['tags_extracted'])}")

            related = data.get('related_ideas', [])
            if related:
                print(f"\n🔗 发现 {len(related)} 个相关想法:")
                for r in related[:3]:
                    print(f"  - {r['title']} (相似度: {r['similarity']:.2f})")

            # 如果有活动会话，添加到会话
            if self.current_session:
                self.ideas_manager.add_idea_to_session(
                    self.current_session.id,
                    idea['id']
                )

        else:
            print(f"❌ 记录失败: {result.get('error')}")

        print("=" * 70)

    async def update_idea(self, idea_id: str = None):
        """更新想法"""
        if not idea_id:
            # 列出最近的想法供选择
            recent_ideas = self.ideas_manager.get_all_ideas()[:10]

            if not recent_ideas:
                print("\n还没有任何想法")
                return

            print("\n📝 最近的想法:")
            for i, idea in enumerate(recent_ideas, 1):
                print(f"{i}. [{idea.id}] {idea.title} (v{idea.version})")

            choice = input("\n选择想法编号（或输入 ID）: ").strip()

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(recent_ideas):
                    idea_id = recent_ideas[idx].id
                else:
                    idea_id = choice
            except ValueError:
                idea_id = choice

        idea = self.ideas_manager.get_idea(idea_id)
        if not idea:
            print(f"❌ 想法不存在: {idea_id}")
            return

        print(f"\n📝 更新想法: {idea.title}")
        print("=" * 70)
        print(f"当前版本: v{idea.version}")
        print(f"内容: {idea.content[:200]}...")
        print("=" * 70)

        print("\n选择操作:")
        print("1. 直接编辑（覆盖当前版本）")
        print("2. 创建新版本（保留历史）")

        choice = input("选择 (1/2): ").strip()

        new_content = input("\n新内容（留空保持不变）:\n").strip()

        if choice == "2":
            # 创建新版本
            new_idea = self.ideas_manager.update_idea(
                idea_id=idea_id,
                content=new_content or idea.content,
                create_new_version=True
            )
            print(f"\n✓ 已创建新版本 v{new_idea.version}")

        else:
            # 直接编辑
            self.ideas_manager.update_idea(
                idea_id=idea_id,
                content=new_content if new_content else None,
                create_new_version=False
            )
            print("\n✓ 想法已更新")

    async def list_ideas(self, filter_by: str = None):
        """列出想法"""
        if filter_by:
            if filter_by.startswith('tag:'):
                tag = filter_by[4:]
                ideas = self.ideas_manager.get_ideas_by_tag(tag)
                title = f"标签 '{tag}' 的想法"
            elif filter_by.startswith('paper:'):
                paper_id = filter_by[6:]
                ideas = self.ideas_manager.get_ideas_by_paper(paper_id)
                title = f"论文 '{paper_id}' 的想法"
            else:
                ideas = self.ideas_manager.search_ideas(filter_by)
                title = f"搜索 '{filter_by}' 的结果"
        else:
            ideas = self.ideas_manager.get_all_ideas()
            title = "所有想法"

        print(f"\n💭 {title} ({len(ideas)} 个)")
        print("=" * 70)

        if not ideas:
            print("还没有任何想法")
            return

        for i, idea in enumerate(ideas[:20], 1):  # 最多显示 20 个
            status_icon = "🟢" if idea.status == "active" else "🔵"
            print(f"{i}. {status_icon} [{idea.id}] {idea.title} (v{idea.version})")
            print(f"   创建: {idea.created_at[:10]}")
            if idea.tags:
                print(f"   标签: {', '.join(idea.tags)}")
            print()

        print("=" * 70)

    async def show_idea(self, idea_id: str):
        """显示想法详情"""
        idea = self.ideas_manager.get_idea(idea_id)

        if not idea:
            print(f"❌ 想法不存在: {idea_id}")
            return

        print(f"\n💭 {idea.title}")
        print("=" * 70)
        print(f"ID: {idea.id}")
        print(f"版本: v{idea.version}")
        print(f"状态: {idea.status}")
        print(f"创建: {idea.created_at}")
        print(f"更新: {idea.updated_at}")

        if idea.tags:
            print(f"标签: {', '.join(idea.tags)}")

        if idea.related_papers:
            print(f"相关论文: {', '.join(idea.related_papers)}")

        print(f"\n内容:\n{idea.content}")
        print("=" * 70)

        # 显示演进历史
        evolution = self.ideas_manager.get_idea_evolution(idea_id)
        if len(evolution) > 1:
            print(f"\n📜 演进历史 ({len(evolution)} 个版本):")
            for v in evolution:
                print(f"  v{v.version}: {v.created_at[:10]} - {v.title}")

    async def find_related(self, idea_id: str):
        """查找相关想法"""
        result = await self.insight_agent.process({
            'command': 'find_related',
            'idea_id': idea_id,
            'threshold': 0.3
        })

        if not result.get('success'):
            print(f"❌ 查找失败: {result.get('error')}")
            return

        data = result['data']
        idea = data['idea']
        related = data['related_ideas']

        print(f"\n🔗 与 '{idea['title']}' 相关的想法:")
        print("=" * 70)

        if not related:
            print("没有找到相关想法")
        else:
            for r in related[:10]:
                print(f"• {r['title']} (相似度: {r['similarity']:.2f})")
                if r.get('tags'):
                    print(f"  标签: {', '.join(r['tags'])}")

        if data.get('relationship_analysis'):
            print(f"\n💡 关系分析:\n{data['relationship_analysis']}")

        print("=" * 70)

    async def synthesize_ideas(self, topic: str = ""):
        """综合想法"""
        print("\n🧠 综合想法...")
        print("=" * 70)

        result = await self.insight_agent.process({
            'command': 'synthesize',
            'topic': topic
        })

        if not result.get('success'):
            print(f"❌ 综合失败: {result.get('error')}")
            return

        data = result['data']

        print(f"基于 {data['num_ideas']} 个想法的综合分析:\n")
        print(data['synthesis'])
        print("\n" + "=" * 70)

    async def show_statistics(self):
        """显示统计"""
        stats = self.ideas_manager.get_statistics()

        print("\n📊 想法管理统计")
        print("=" * 70)
        print(f"总想法数: {stats['total_ideas']}")
        print(f"  - 活跃: {stats['active_ideas']}")
        print(f"  - 已精炼: {stats['refined_ideas']}")
        print(f"总标签数: {stats['total_tags']}")
        print(f"关联论文数: {stats['papers_with_ideas']}")
        print(f"阅读会话数: {stats['total_sessions']}")
        print("=" * 70)

    async def end_session(self):
        """结束阅读会话"""
        if not self.current_session:
            print("\n没有活动的阅读会话")
            return

        print(f"\n📖 结束阅读会话 (ID: {self.current_session.id})")
        print("=" * 70)

        notes = input("📝 会话总结（可选）: ").strip()

        session = self.ideas_manager.end_reading_session(
            self.current_session.id,
            notes=notes
        )

        # 生成会话回顾
        result = await self.insight_agent.process({
            'command': 'review_session',
            'session_id': session.id
        })

        if result.get('success'):
            data = result['data']
            print(f"\n✓ 会话已结束")
            print(f"  论文数: {len(session.papers)}")
            print(f"  想法数: {data['ideas_created']}")

            if data.get('review'):
                print(f"\n📝 会话回顾:\n{data['review']}")

        self.current_session = None
        print("=" * 70)


async def main():
    parser = argparse.ArgumentParser(
        description="Ideas CLI - 研究想法管理工具"
    )

    parser.add_argument('--start-serial', action='store_true',
                       help='开始串行阅读会话')
    parser.add_argument('--start-parallel', action='store_true',
                       help='开始并行阅读会话')
    parser.add_argument('--record', type=str, metavar='PAPER_ID',
                       help='记录新想法')
    parser.add_argument('--update', type=str, metavar='IDEA_ID',
                       help='更新想法')
    parser.add_argument('--list', action='store_true',
                       help='列出所有想法')
    parser.add_argument('--show', type=str, metavar='IDEA_ID',
                       help='显示想法详情')
    parser.add_argument('--related', type=str, metavar='IDEA_ID',
                       help='查找相关想法')
    parser.add_argument('--synthesize', action='store_true',
                       help='综合所有想法')
    parser.add_argument('--stats', action='store_true',
                       help='显示统计信息')
    parser.add_argument('--end', action='store_true',
                       help='结束当前阅读会话')

    args = parser.parse_args()

    # 初始化 CLI
    cli = IdeasCLI(storage_dir=Path("./data/research_notes"))

    # 执行命令
    if args.start_serial:
        await cli.start_session(mode='serial')

    elif args.start_parallel:
        await cli.start_session(mode='parallel')

    elif args.record:
        await cli.record_idea(paper_id=args.record)

    elif args.update:
        await cli.update_idea(idea_id=args.update)

    elif args.list:
        await cli.list_ideas()

    elif args.show:
        await cli.show_idea(args.show)

    elif args.related:
        await cli.find_related(args.related)

    elif args.synthesize:
        await cli.synthesize_ideas()

    elif args.stats:
        await cli.show_statistics()

    elif args.end:
        await cli.end_session()

    else:
        print("\n💭 研究想法管理系统")
        print("=" * 70)
        print("串行模式（深度优先）：")
        print("  python scripts/ideas_cli.py --start-serial")
        print("  python scripts/ideas_cli.py --record <paper_id>")
        print("  python scripts/ideas_cli.py --end")
        print("\n并行模式（广度优先）：")
        print("  python scripts/ideas_cli.py --start-parallel")
        print("  python scripts/ideas_cli.py --record <paper_id>")
        print("  python scripts/ideas_cli.py --synthesize")
        print("\n管理想法：")
        print("  python scripts/ideas_cli.py --list")
        print("  python scripts/ideas_cli.py --show <idea_id>")
        print("  python scripts/ideas_cli.py --update <idea_id>")
        print("  python scripts/ideas_cli.py --related <idea_id>")
        print("  python scripts/ideas_cli.py --stats")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
