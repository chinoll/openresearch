"""
Insights CLI - 洞察驱动的想法生成系统
阅读论文 → 记录洞察 → 提炼想法
"""

import asyncio
import argparse
from pathlib import Path
import sys
import json

sys.path.append(str(Path(__file__).parent.parent))

from core.insights_system import (
    InsightsManager,
    Insight,
    InsightType,
    IdeaFromInsights
)


class InsightsCLI:
    """洞察管理 CLI"""

    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.manager = InsightsManager(storage_dir=self.storage_dir)
        self.current_session = None

    # ==================== 阅读会话 ====================

    def start_reading(self, paper_id: str):
        """开始阅读会话"""
        print(f"\n📖 开始阅读论文: {paper_id}")
        print("=" * 70)

        notes = input("阅读笔记（可选）: ").strip()

        self.current_session = self.manager.start_reading_session(
            paper_id=paper_id,
            notes=notes or f"阅读论文 {paper_id}"
        )

        print(f"\n✓ 阅读会话已开始 (ID: {self.current_session})")
        print("\n💡 阅读时请随时记录洞察:")
        print("  python scripts/insights_cli.py --insight")
        print("\n结束阅读:")
        print("  python scripts/insights_cli.py --end-reading")
        print("=" * 70)

    def end_reading(self):
        """结束阅读会话"""
        if not self.current_session:
            # 尝试找到最近的未结束会话
            sessions = self.manager.index.get('reading_sessions', [])
            active_sessions = [s for s in sessions if s.get('end_time') is None]

            if not active_sessions:
                print("\n没有活动的阅读会话")
                return

            self.current_session = active_sessions[-1]['id']

        print(f"\n📖 结束阅读会话")
        print("=" * 70)

        session = self.manager.end_reading_session(self.current_session)
        summary = self.manager.get_session_summary(self.current_session)

        print(f"\n✓ 会话已结束")
        print(f"  论文: {session['paper_id']}")
        print(f"  时长: {session['start_time'][:16]} → {session['end_time'][:16]}")
        print(f"  洞察数: {summary['num_insights']}")

        if summary['insights_by_type']:
            print(f"\n  洞察类型分布:")
            for itype, count in summary['insights_by_type'].items():
                print(f"    - {itype}: {count}")

        if summary['unconverted_insights'] > 0:
            print(f"\n💡 提示: 有 {summary['unconverted_insights']} 个洞察未转化为想法")
            print(f"  python scripts/insights_cli.py --gen-ideas {session['paper_id']}")

        print("=" * 70)
        self.current_session = None

    # ==================== 洞察记录 ====================

    def record_insight(self, paper_id: str = None):
        """快速记录洞察"""
        print("\n💡 记录洞察（阅读时的即时理解）")
        print("=" * 70)

        # 确定论文
        if not paper_id and self.current_session:
            sessions = self.manager.index.get('reading_sessions', [])
            for s in sessions:
                if s['id'] == self.current_session:
                    paper_id = s['paper_id']
                    break

        if not paper_id:
            paper_id = input("论文 ID: ").strip()
            if not paper_id:
                print("❌ 论文 ID 不能为空")
                return

        # 洞察内容（一句话即可）
        content = input("\n洞察内容（一句话）: ").strip()
        if not content:
            print("❌ 内容不能为空")
            return

        # 可选信息
        section = input("章节（可选）: ").strip() or None
        page = input("页码（可选）: ").strip()
        page = int(page) if page else None

        print("\n触发洞察的原文（可选，输入 'END' 结束）:")
        quote_lines = []
        while True:
            line = input()
            if line.strip() == 'END' or line.strip() == '':
                break
            quote_lines.append(line)
        quote = '\n'.join(quote_lines).strip() or None

        # 洞察类型
        print("\n洞察类型:")
        print("1. observation (观察)")
        print("2. question (疑问)")
        print("3. connection (联系)")
        print("4. surprise (惊讶)")
        print("5. critique (批评)")
        print("6. insight (顿悟)")

        type_choice = input("选择 (1-6, 默认1): ").strip() or "1"
        type_map = {
            "1": InsightType.OBSERVATION,
            "2": InsightType.QUESTION,
            "3": InsightType.CONNECTION,
            "4": InsightType.SURPRISE,
            "5": InsightType.CRITIQUE,
            "6": InsightType.INSIGHT
        }
        insight_type = type_map.get(type_choice, InsightType.OBSERVATION)

        # 重要性
        importance = input("重要性 (1-5, 默认3): ").strip() or "3"
        importance = int(importance)

        # 创建洞察
        insight = self.manager.create_insight(
            content=content,
            paper_id=paper_id,
            section=section,
            page=page,
            quote=quote,
            insight_type=insight_type,
            importance=importance
        )

        # 添加到会话
        if self.current_session:
            self.manager.add_insight_to_session(self.current_session, insight.id)

        # 显示
        print(f"\n✓ 洞察已记录!")
        print(f"  ID: {insight.id}")
        print(f"  类型: {insight.insight_type}")
        print(f"  重要性: {'⭐' * insight.importance}")
        if insight.section:
            print(f"  位置: {paper_id}, §{insight.section}")
            if insight.page:
                print(f"        p.{insight.page}")

        print("\n继续记录洞察？")
        print("  python scripts/insights_cli.py --insight")
        print("=" * 70)

    # ==================== 查看洞察 ====================

    def list_insights(self, paper_id: str = None, show_type: str = None):
        """列出洞察"""
        if paper_id:
            insights = self.manager.get_insights_by_paper(paper_id)
            title = f"论文 {paper_id} 的洞察"
        elif show_type:
            insights = self.manager.get_insights_by_type(show_type)
            title = f"类型为 {show_type} 的洞察"
        else:
            insights = self.manager.get_all_insights()
            title = "所有洞察"

        print(f"\n💡 {title} ({len(insights)} 个)")
        print("=" * 70)

        if not insights:
            print("还没有任何洞察")
            return

        for i, insight in enumerate(insights[:30], 1):  # 最多显示30个
            icon = self._get_insight_icon(insight.insight_type)
            converted = "✅" if insight.converted_to_idea else "  "

            print(f"{i}. {converted} {icon} [{insight.id}] {insight.content[:60]}")
            print(f"   {insight.paper_id}", end="")
            if insight.section:
                print(f", §{insight.section}", end="")
            if insight.page:
                print(f", p.{insight.page}", end="")
            print(f" | {'⭐' * insight.importance}")

            if insight.converted_to_idea:
                print(f"   → 已转化为想法: {', '.join(insight.idea_ids)}")

            print()

        print("=" * 70)

    def show_insight(self, insight_id: str):
        """显示洞察详情"""
        insight = self.manager.get_insight(insight_id)

        if not insight:
            print(f"❌ 洞察不存在: {insight_id}")
            return

        icon = self._get_insight_icon(insight.insight_type)

        print(f"\n{icon} {insight.content}")
        print("=" * 70)

        print(f"ID: {insight.id}")
        print(f"类型: {insight.insight_type}")
        print(f"重要性: {'⭐' * insight.importance}")
        print(f"时间: {insight.created_at[:16]}")

        print(f"\n位置:")
        print(f"  论文: {insight.paper_id}")
        if insight.section:
            print(f"  章节: {insight.section}")
        if insight.page:
            print(f"  页码: {insight.page}")

        if insight.quote:
            print(f"\n原文:")
            print(f"  {insight.quote}")

        if insight.converted_to_idea:
            print(f"\n已转化为想法:")
            for idea_id in insight.idea_ids:
                idea = self.manager.get_idea(idea_id)
                if idea:
                    print(f"  - [{idea_id}] {idea.title}")

        print("=" * 70)

    # ==================== 想法生成 ====================

    def generate_ideas(self, paper_id: str = None):
        """从洞察生成想法"""
        print("\n🎯 从洞察生成想法")
        print("=" * 70)

        # 获取未转化的洞察
        unconverted = self.manager.get_unconverted_insights(paper_id)

        if not unconverted:
            print("没有未转化的洞察")
            return

        print(f"\n未转化的洞察 ({len(unconverted)} 个):")
        for i, insight in enumerate(unconverted, 1):
            icon = self._get_insight_icon(insight.insight_type)
            print(f"{i}. {icon} [{insight.id}] {insight.content[:60]}")
            print(f"   {'⭐' * insight.importance} | {insight.paper_id}")

        # 查看建议
        suggestions = self.manager.suggest_ideas_from_insights(paper_id)
        if suggestions:
            print(f"\n💡 建议（基于章节分组）:")
            for i, sugg in enumerate(suggestions, 1):
                print(f"{i}. 章节 '{sugg['section']}' 有 {sugg['num_insights']} 个洞察")
                for preview in sugg['preview']:
                    print(f"   - {preview}...")

        # 选择洞察
        print("\n" + "=" * 70)
        print("选择要组合的洞察（输入编号，逗号分隔）:")

        choice = input("编号（如 1,2,3）: ").strip()
        if not choice:
            print("取消")
            return

        try:
            indices = [int(x.strip()) - 1 for x in choice.split(',')]
            selected_insights = [unconverted[i] for i in indices if 0 <= i < len(unconverted)]

            if not selected_insights:
                print("❌ 无效的选择")
                return

        except (ValueError, IndexError):
            print("❌ 无效的输入")
            return

        # 显示选择的洞察
        print(f"\n已选择 {len(selected_insights)} 个洞察:")
        for insight in selected_insights:
            print(f"  - {insight.content[:60]}")

        # 输入想法
        print("\n" + "=" * 70)
        title = input("想法标题: ").strip()
        if not title:
            print("❌ 标题不能为空")
            return

        print("\n想法内容（基于洞察的综合）:")
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

        # 类别和标签
        category = input("\n类别 (concept/method/finding/insight): ").strip() or None
        tags_input = input("标签 (逗号分隔): ").strip()
        tags = [t.strip() for t in tags_input.split(',')] if tags_input else []

        # 创建想法
        try:
            idea = self.manager.create_idea_from_insights(
                title=title,
                content=content,
                insight_ids=[i.id for i in selected_insights],
                category=category,
                tags=tags
            )

            print(f"\n✓ 想法已创建!")
            print(f"  ID: {idea.id}")
            print(f"  标题: {idea.title}")
            print(f"  基于洞察: {len(idea.source_insights)} 个")

            print(f"\n源洞察:")
            for ins in selected_insights:
                print(f"  - {ins.content[:60]}")

        except Exception as e:
            print(f"❌ 创建失败: {e}")

        print("=" * 70)

    def list_ideas(self):
        """列出所有想法"""
        ideas = self.manager.get_all_ideas()

        print(f"\n🎯 想法列表 ({len(ideas)} 个)")
        print("=" * 70)

        if not ideas:
            print("还没有任何想法")
            return

        for i, idea in enumerate(ideas, 1):
            print(f"{i}. [{idea.id}] {idea.title}")
            print(f"   类别: {idea.category or 'N/A'} | 基于 {len(idea.source_insights)} 个洞察")
            print(f"   论文: {idea.paper_id}")
            print()

        print("=" * 70)

    def show_idea(self, idea_id: str):
        """显示想法详情"""
        idea = self.manager.get_idea(idea_id)

        if not idea:
            print(f"❌ 想法不存在: {idea_id}")
            return

        print(f"\n🎯 {idea.title}")
        print("=" * 70)

        print(f"ID: {idea.id}")
        print(f"类别: {idea.category or 'N/A'}")
        print(f"状态: {idea.status}")
        print(f"置信度: {idea.confidence}")
        print(f"时间: {idea.created_at[:16]}")

        if idea.tags:
            print(f"标签: {', '.join(idea.tags)}")

        print(f"\n内容:")
        print(idea.content)

        print(f"\n源洞察 ({len(idea.source_insights)} 个):")
        for insight_id in idea.source_insights:
            insight = self.manager.get_insight(insight_id)
            if insight:
                icon = self._get_insight_icon(insight.insight_type)
                print(f"  {icon} {insight.content}")
                print(f"     {insight.paper_id}, §{insight.section or 'N/A'}")

        print("=" * 70)

    # ==================== 统计 ====================

    def show_statistics(self):
        """显示统计"""
        stats = self.manager.get_statistics()

        print("\n📊 洞察系统统计")
        print("=" * 70)

        print(f"洞察总数: {stats['total_insights']}")
        print(f"  - 已转化: {stats['converted_insights']}")
        print(f"  - 未转化: {stats['unconverted_insights']}")

        if stats['insights_by_type']:
            print(f"\n洞察类型分布:")
            for itype, count in stats['insights_by_type'].items():
                icon = self._get_insight_icon(itype)
                print(f"  {icon} {itype}: {count}")

        print(f"\n想法总数: {stats['total_ideas']}")
        print(f"论文数: {stats['papers_with_insights']}")
        print(f"平均每篇论文洞察: {stats['avg_insights_per_paper']:.1f}")

        print("=" * 70)

    # ==================== 辅助方法 ====================

    def _get_insight_icon(self, insight_type: str) -> str:
        """获取洞察类型图标"""
        icons = {
            InsightType.OBSERVATION: "👁️",
            InsightType.QUESTION: "❓",
            InsightType.CONNECTION: "🔗",
            InsightType.SURPRISE: "😲",
            InsightType.CRITIQUE: "🤔",
            InsightType.INSIGHT: "💡"
        }
        return icons.get(insight_type, "📝")


def main():
    parser = argparse.ArgumentParser(
        description="Insights CLI - 洞察驱动的想法生成"
    )

    parser.add_argument('--start-reading', type=str, metavar='PAPER_ID',
                       help='开始阅读会话')
    parser.add_argument('--end-reading', action='store_true',
                       help='结束阅读会话')

    parser.add_argument('--insight', type=str, metavar='PAPER_ID', nargs='?', const='',
                       help='记录洞察')

    parser.add_argument('--list-insights', type=str, metavar='PAPER_ID', nargs='?', const='all',
                       help='列出洞察')
    parser.add_argument('--show-insight', type=str, metavar='INSIGHT_ID',
                       help='显示洞察详情')

    parser.add_argument('--gen-ideas', type=str, metavar='PAPER_ID', nargs='?', const='',
                       help='从洞察生成想法')
    parser.add_argument('--list-ideas', action='store_true',
                       help='列出想法')
    parser.add_argument('--show-idea', type=str, metavar='IDEA_ID',
                       help='显示想法详情')

    parser.add_argument('--stats', action='store_true',
                       help='显示统计')

    args = parser.parse_args()

    # 初始化 CLI
    cli = InsightsCLI(storage_dir=Path("./data/insights_research"))

    # 执行命令
    if args.start_reading:
        cli.start_reading(paper_id=args.start_reading)

    elif args.end_reading:
        cli.end_reading()

    elif args.insight is not None:
        cli.record_insight(paper_id=args.insight if args.insight else None)

    elif args.list_insights:
        paper_id = None if args.list_insights == 'all' else args.list_insights
        cli.list_insights(paper_id=paper_id)

    elif args.show_insight:
        cli.show_insight(args.show_insight)

    elif args.gen_ideas is not None:
        cli.generate_ideas(paper_id=args.gen_ideas if args.gen_ideas else None)

    elif args.list_ideas:
        cli.list_ideas()

    elif args.show_idea:
        cli.show_idea(args.show_idea)

    elif args.stats:
        cli.show_statistics()

    else:
        print("\n💡 洞察驱动的想法生成系统")
        print("=" * 70)
        print("工作流: 阅读论文 → 记录洞察 → 生成想法")
        print("\n阅读会话:")
        print("  python scripts/insights_cli.py --start-reading <paper_id>")
        print("  python scripts/insights_cli.py --insight")
        print("  python scripts/insights_cli.py --end-reading")
        print("\n查看洞察:")
        print("  python scripts/insights_cli.py --list-insights [paper_id]")
        print("  python scripts/insights_cli.py --show-insight <insight_id>")
        print("\n生成想法:")
        print("  python scripts/insights_cli.py --gen-ideas [paper_id]")
        print("  python scripts/insights_cli.py --list-ideas")
        print("  python scripts/insights_cli.py --show-idea <idea_id>")
        print("\n统计:")
        print("  python scripts/insights_cli.py --stats")
        print("=" * 70)


if __name__ == "__main__":
    main()
