"""
Deep Research Agent - 主入口文件
论文深度研究系统
"""

import asyncio
import argparse
from pathlib import Path
import json
import sys

from core.base_agent import AgentConfig
from core.config import load_app_config
from core.orchestrator import OrchestratorAgent
from core.registry import get_registry


class DeepResearchSystem:
    """深度研究系统主控制器"""

    def __init__(self, config_path: Path = None):
        """
        初始化系统

        Args:
            config_path: 配置文件路径
        """
        self.config = load_app_config(config_path)

        # 初始化主控 Agent
        self._init_agents()

    def _init_agents(self):
        """初始化主控 Agent"""
        # 自动发现并注册所有模块
        registry = get_registry()
        registry.auto_discover(['plugins', 'core'])

        llm_config = self.config.get('llm', {})

        agent_config = AgentConfig(
            name="Orchestrator",
            model=llm_config.get('model', 'claude-sonnet-4-5-20250929'),
            temperature=llm_config.get('temperature', 0.7),
            max_tokens=llm_config.get('max_tokens', 4096),
            api_key=llm_config.get('api_key'),
            provider=llm_config.get('provider'),
            base_url=llm_config.get('base_url'),
        )

        self.orchestrator = OrchestratorAgent(
            config=agent_config,
            app_config=self.config,
        )

    async def add_paper_from_arxiv(self, arxiv_id: str, full_analysis: bool = True) -> dict:
        """
        从 arXiv 添加论文

        Args:
            arxiv_id: arXiv ID 或 URL
            full_analysis: 是否进行完整分析

        Returns:
            处理结果
        """
        print(f"\n📥 正在添加并分析论文: {arxiv_id}")
        print("=" * 70)

        result = await self.orchestrator.add_paper(
            source='arxiv',
            identifier=arxiv_id,
            full_analysis=full_analysis
        )

        if result.get('success'):
            data = result.get('data', {})
            complete_analysis = data.get('complete_analysis', {})
            paper_info = complete_analysis.get('paper_info', {})
            knowledge = complete_analysis.get('knowledge', {})
            relations = complete_analysis.get('relations', {})

            print(f"\n✓ 论文处理成功!")
            print(f"\n📄 论文信息:")
            print(f"  ID: {paper_info.get('id', 'N/A')}")
            print(f"  标题: {paper_info.get('title', 'N/A')}")
            print(f"  作者: {', '.join(paper_info.get('authors', [])[:3])}")
            print(f"  来源: {paper_info.get('source_type', 'N/A').upper()}")

            if knowledge:
                print(f"\n💡 知识提取:")
                contributions = knowledge.get('contributions', [])
                print(f"  核心贡献: {len(contributions)} 项")
                for i, contrib in enumerate(contributions[:3], 1):
                    print(f"    {i}. {contrib.get('title', 'N/A')}")

                keywords = knowledge.get('keywords', [])
                if keywords:
                    print(f"  关键词: {', '.join(keywords[:8])}")

                methodology = knowledge.get('methodology', {})
                if methodology:
                    print(f"  方法: {methodology.get('approach', 'N/A')[:80]}...")

            if relations:
                print(f"\n🔗 关系分析:")
                citation_analysis = relations.get('citation_analysis', {})
                print(f"  引用了: {citation_analysis.get('num_references', 0)} 篇论文")
                print(f"  被引用: {citation_analysis.get('num_citing_this', 0)} 次")

                similarity_analysis = relations.get('similarity_analysis', {})
                num_similar = similarity_analysis.get('num_similar_papers', 0)
                print(f"  发现: {num_similar} 篇相似论文")

                if num_similar > 0:
                    top_similar = similarity_analysis.get('top_similar', [])
                    print(f"  最相似论文:")
                    for sim in top_similar[:3]:
                        print(f"    - {sim.get('title', 'Unknown')} (相似度: {sim.get('similarity', 0):.2f})")

                topic_analysis = relations.get('topic_analysis', {})
                if topic_analysis:
                    print(f"  研究领域: {topic_analysis.get('primary_field', 'N/A')}")

                impact = relations.get('impact_analysis', {})
                if impact:
                    print(f"  影响力: {impact.get('impact_level', 'Unknown')}")

        else:
            print(f"\n✗ 处理失败: {result.get('error')}")

        print("=" * 70)
        return result

    async def add_paper_from_local(self, file_path: str, full_analysis: bool = True) -> dict:
        """
        从本地文件添加论文

        Args:
            file_path: 文件路径
            full_analysis: 是否进行完整分析

        Returns:
            处理结果
        """
        print(f"\n📄 正在处理本地文件: {file_path}")
        print("=" * 70)

        result = await self.orchestrator.add_paper(
            source='local',
            identifier=file_path,
            full_analysis=full_analysis
        )

        if result.get('success'):
            print(f"\n✓ 文件处理成功!")
            # 显示类似于 add_paper_from_arxiv 的详细信息
            data = result.get('data', {})
            complete_analysis = data.get('complete_analysis', {})
            if complete_analysis:
                paper_info = complete_analysis.get('paper_info', {})
                print(f"  标题: {paper_info.get('title', 'N/A')}")
                print(f"  来源类型: {paper_info.get('source_type', 'N/A').upper()}")

        else:
            print(f"\n✗ 处理失败: {result.get('error')}")

        print("=" * 70)
        return result

    async def list_papers(self):
        """列出所有已添加的论文"""
        # 从向量存储获取所有论文
        all_paper_ids = self.orchestrator.vector_store.get_all_papers()

        if not all_paper_ids:
            print("\n还没有添加任何论文")
            return

        print(f"\n📚 已添加的论文 ({len(all_paper_ids)} 篇):")
        print("=" * 70)

        for i, paper_id in enumerate(all_paper_ids, 1):
            paper = self.orchestrator.vector_store.get_paper_by_id(paper_id)
            if paper:
                metadata = paper.get('metadata', {})
                print(f"\n{i}. {metadata.get('title', 'N/A')}")
                print(f"   ID: {paper_id}")
                print(f"   作者: {metadata.get('authors', 'N/A')}")
                print(f"   类型: {metadata.get('source_type', 'N/A').upper()}")
                if metadata.get('year'):
                    print(f"   年份: {metadata.get('year')}")

        print("=" * 70)

    async def show_statistics(self):
        """显示系统统计信息"""
        stats = self.orchestrator.get_statistics()

        print(f"\n📊 系统统计:")
        print("=" * 70)

        vector_stats = stats.get('vector_store', {})
        print(f"\n向量数据库:")
        print(f"  论文数量: {vector_stats.get('num_papers', 0)}")

        graph_stats = stats.get('knowledge_graph', {})
        print(f"\n知识图谱:")
        print(f"  节点数: {graph_stats.get('num_papers', 0)}")
        print(f"  边数: {graph_stats.get('num_edges', 0)}")
        print(f"  引用关系: {graph_stats.get('num_citations', 0)}")
        print(f"  相似度边: {graph_stats.get('num_similarity_edges', 0)}")

        influential = stats.get('influential_papers', [])
        if influential:
            print(f"\n最有影响力的论文 (Top 5):")
            for i, paper in enumerate(influential, 1):
                print(f"  {i}. {paper.get('title', 'Unknown')} ({paper.get('citations', 0)} 次引用)")

        print("=" * 70)

    async def search_papers(self, query: str, top_k: int = 5):
        """搜索论文"""
        print(f"\n🔍 搜索: '{query}'")
        print("=" * 70)

        results = self.orchestrator.search_papers(query, top_k=top_k)

        if not results:
            print("\n没有找到相关论文")
            return

        print(f"\n找到 {len(results)} 篇相关论文:\n")

        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            similarity = result.get('similarity', 0)
            print(f"{i}. {metadata.get('title', 'Unknown')} (相似度: {similarity:.3f})")
            print(f"   ID: {result.get('paper_id', 'N/A')}")
            print(f"   作者: {metadata.get('authors', 'N/A')}")
            print()

        print("=" * 70)

    def start_web_interface(self):
        """启动 Web 界面"""
        print("\n🌐 启动 Web 界面...")
        print("=" * 60)
        print("功能开发中...")
        print("=" * 60)
        # TODO: 实现 Web 界面


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Deep Research Agent - 论文深度研究系统"
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config/config.yaml',
        help='配置文件路径'
    )

    parser.add_argument(
        '--arxiv',
        type=str,
        help='添加 arXiv 论文 (ID 或 URL)'
    )

    parser.add_argument(
        '--local',
        type=str,
        help='添加本地论文文件'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='列出所有已添加的论文'
    )

    parser.add_argument(
        '--stats',
        action='store_true',
        help='显示系统统计信息'
    )

    parser.add_argument(
        '--search',
        type=str,
        help='搜索论文'
    )

    parser.add_argument(
        '--quick',
        action='store_true',
        help='快速模式（仅摄入，不进行深度分析）'
    )

    parser.add_argument(
        '--web',
        action='store_true',
        help='启动 Web 界面'
    )

    args = parser.parse_args()

    # 检查配置文件
    config_path = Path(args.config)
    if not config_path.exists() and config_path.name != 'config.yaml':
        print(f"⚠️  配置文件不存在: {config_path}")
        print(f"将使用默认配置")
        config_path = None

    # 初始化系统
    system = DeepResearchSystem(config_path)

    # 执行命令
    if args.arxiv:
        full_analysis = not args.quick
        await system.add_paper_from_arxiv(args.arxiv, full_analysis=full_analysis)

    elif args.local:
        full_analysis = not args.quick
        await system.add_paper_from_local(args.local, full_analysis=full_analysis)

    elif args.list:
        await system.list_papers()

    elif args.stats:
        await system.show_statistics()

    elif args.search:
        await system.search_papers(args.search)

    elif args.web:
        system.start_web_interface()

    else:
        # 交互模式
        print("\n🚀 Deep Research Agent - 论文深度研究系统")
        print("=" * 70)
        print("欢迎使用基于多 Agent 协作的智能论文管理系统!")
        print("\n✨ 核心特性:")
        print("  • TeX 源文件优先解析（更准确的结构化信息）")
        print("  • AI 驱动的知识提取和关系分析")
        print("  • 自动构建知识图谱和引用网络")
        print("  • 语义搜索和相似论文发现")
        print("\n📖 可用命令:")
        print("  python main.py --arxiv <ID>        # 添加 arXiv 论文（完整分析）")
        print("  python main.py --arxiv <ID> --quick # 快速添加（仅摄入）")
        print("  python main.py --local <file>      # 添加本地论文")
        print("  python main.py --list              # 列出所有论文")
        print("  python main.py --stats             # 查看系统统计")
        print("  python main.py --search <query>    # 搜索论文")
        print("  python main.py --web               # 启动 Web 界面")
        print("\n💡 示例:")
        print("  python main.py --arxiv 2301.00001")
        print("  python main.py --arxiv https://arxiv.org/abs/2401.12345")
        print("  python main.py --search 'transformer attention mechanism'")
        print("  python main.py --stats")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
