"""
Insight Agent - 研究洞察 Agent
帮助用户管理研究想法，发现想法之间的联系，提示需要更新的想法
"""

from pathlib import Path
from typing import Dict, List, Optional
import json

from core.base_agent import BaseAgent, AgentConfig, AgentResponse
from prompts.loader import load as load_prompt
from plugins.ideas.manager import IdeasManager, Idea


class InsightAgent(BaseAgent):
    """研究洞察 Agent - 纯文本记忆管理"""

    from core.registry import ModuleRegistration, ModuleType, Capability, DependencySpec, TeamExport
    REGISTRATION = ModuleRegistration(
        name="insight_agent",
        module_type=ModuleType.AGENT,
        display_name="研究洞察 Agent",
        description="管理研究想法，发现想法之间的联系，综合多个想法生成高层洞察",
        dependencies=[
            DependencySpec(name="ideas_manager"),
        ],
        capabilities=[
            Capability(name="record_idea", description="记录新想法（带 AI 增强）", tags=["idea", "record"]),
            Capability(name="find_related", description="查找相关想法", tags=["idea", "search"]),
            Capability(name="suggest_updates", description="建议需要更新的想法", tags=["idea", "suggest"]),
            Capability(name="synthesize", description="综合多个想法生成高层洞察", tags=["idea", "synthesize"]),
            Capability(name="review_session", description="回顾阅读会话", tags=["session", "review"]),
        ],
        team_export=TeamExport(default_role="insight_specialist", description="综合想法生成研究洞察"),
    )
    del ModuleRegistration, ModuleType, Capability, DependencySpec, TeamExport

    def __init__(self,
                 config: AgentConfig,
                 ideas_manager: IdeasManager):
        super().__init__(config)

        self.ideas_manager = ideas_manager

        self.log("Insight Agent initialized (text-based memory)")

    async def process(self, input_data: Dict) -> Dict:
        """
        处理洞察请求

        Args:
            input_data: {
                'command': 'record_idea' | 'find_related' | 'suggest_updates' | 'synthesize',
                ...
            }

        Returns:
            处理结果
        """
        command = input_data.get('command', 'record_idea')

        try:
            if command == 'record_idea':
                result = await self._record_idea(input_data)
            elif command == 'find_related':
                result = await self._find_related_ideas(input_data)
            elif command == 'suggest_updates':
                result = await self._suggest_updates(input_data)
            elif command == 'synthesize':
                result = await self._synthesize_ideas(input_data)
            elif command == 'review_session':
                result = await self._review_reading_session(input_data)
            else:
                return AgentResponse(
                    success=False,
                    error=f"Unknown command: {command}"
                ).to_dict()

            return AgentResponse(success=True, data=result).to_dict()

        except Exception as e:
            self.log(f"Error in insight processing: {e}", "error")
            return AgentResponse(success=False, error=str(e)).to_dict()

    async def _record_idea(self, input_data: Dict) -> Dict:
        """
        记录新想法（带 AI 增强）

        Args:
            input_data: {
                'title': 想法标题,
                'content': 想法内容,
                'paper_id': 相关论文 ID,
                'auto_enhance': 是否使用 AI 增强
            }
        """
        title = input_data.get('title')
        content = input_data.get('content')
        paper_id = input_data.get('paper_id')
        auto_enhance = input_data.get('auto_enhance', True)

        if not title or not content:
            raise ValueError("Title and content are required")

        # AI 增强：提取标签、完善内容
        if auto_enhance and self.llm_client:
            enhanced = await self._enhance_idea(title, content, paper_id)
            tags = enhanced.get('tags', [])
            refined_content = enhanced.get('refined_content', content)
        else:
            tags = []
            refined_content = content

        # 创建想法
        idea = self.ideas_manager.create_idea(
            title=title,
            content=refined_content,
            related_papers=[paper_id] if paper_id else [],
            tags=tags
        )

        # 查找相关想法
        related_ideas = await self._find_similar_ideas(idea)

        return {
            'idea': idea.to_dict(),
            'tags_extracted': tags,
            'related_ideas': [
                {
                    'id': r['id'],
                    'title': r['title'],
                    'similarity': r['similarity']
                }
                for r in related_ideas[:5]
            ]
        }

    async def _enhance_idea(self, title: str, content: str, paper_id: str = None) -> Dict:
        """使用 AI 增强想法"""
        from plugins.knowledge.schemas import ENHANCE_IDEA_SCHEMA

        prompt = load_prompt(
            "insight/enhance_idea",
            title=title,
            content=content,
            paper_id=paper_id or 'N/A',
        )

        result = self.call_llm_structured(prompt, ENHANCE_IDEA_SCHEMA,
                                          tool_name="enhance_idea",
                                          system_prompt=self._get_system_prompt())
        if not result.get('refined_content'):
            result['refined_content'] = content
        if not result.get('tags'):
            result['tags'] = []
        return result

    async def _find_related_ideas(self, input_data: Dict) -> Dict:
        """
        查找相关想法

        Args:
            input_data: {
                'idea_id': 想法 ID,
                'threshold': 相似度阈值（可选）
            }
        """
        idea_id = input_data.get('idea_id')
        threshold = input_data.get('threshold', 0.6)

        idea = self.ideas_manager.get_idea(idea_id)
        if not idea:
            raise ValueError(f"Idea not found: {idea_id}")

        # 查找相似想法
        related = await self._find_similar_ideas(idea, threshold=threshold)

        # 使用 LLM 分析关系
        if related and self.llm_client:
            analysis = await self._analyze_idea_relationships(idea, related[:3])
        else:
            analysis = "No AI analysis available"

        return {
            'idea': idea.to_dict(),
            'related_ideas': related,
            'relationship_analysis': analysis
        }

    async def _find_similar_ideas(self, idea: Idea, threshold: float = 0.6) -> List[Dict]:
        """查找与给定想法相似的其他想法"""
        # 使用向量搜索（简化版 - 基于文本相似度）
        query_text = f"{idea.title}\n{idea.content}"

        # 获取所有想法
        all_ideas = self.ideas_manager.get_all_ideas()

        # 简单的相似度计算（基于关键词重叠）
        # TODO: 集成到 vector_store 进行真正的向量相似度计算
        similar = []

        for other_idea in all_ideas:
            if other_idea.id == idea.id:
                continue

            # 简单的 Jaccard 相似度
            words1 = set(query_text.lower().split())
            words2 = set(f"{other_idea.title}\n{other_idea.content}".lower().split())

            intersection = len(words1 & words2)
            union = len(words1 | words2)

            if union > 0:
                similarity = intersection / union

                if similarity >= threshold:
                    similar.append({
                        'id': other_idea.id,
                        'title': other_idea.title,
                        'similarity': similarity,
                        'tags': other_idea.tags,
                        'version': other_idea.version
                    })

        # 按相似度排序
        similar.sort(key=lambda x: x['similarity'], reverse=True)
        return similar

    async def _analyze_idea_relationships(self, main_idea: Idea, related_ideas: List[Dict]) -> str:
        """分析想法之间的关系"""
        if not self.llm_client:
            return "LLM not available"

        related_text = "\n".join([
            f"{i+1}. {idea['title']} (相似度: {idea['similarity']:.2f})"
            for i, idea in enumerate(related_ideas)
        ])

        prompt = load_prompt(
            "insight/analyze_relationships",
            main_idea_title=main_idea.title,
            main_idea_content=main_idea.content[:300],
            related_text=related_text,
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        return response.strip()

    async def _suggest_updates(self, input_data: Dict) -> Dict:
        """
        建议需要更新的想法

        Args:
            input_data: {
                'new_paper_id': 新读的论文 ID,
                'new_paper_data': 论文数据
            }
        """
        new_paper_id = input_data.get('new_paper_id')
        new_paper_data = input_data.get('new_paper_data', {})

        # 获取所有活跃想法
        active_ideas = self.ideas_manager.get_all_ideas(status='active')

        if not active_ideas:
            return {
                'suggestions': [],
                'message': 'No active ideas to update'
            }

        # 找到与新论文相关的想法
        suggestions = []

        for idea in active_ideas:
            # 检查是否有关键词重叠
            idea_keywords = set(idea.title.lower().split() + idea.content.lower().split())
            paper_keywords = set(
                new_paper_data.get('title', '').lower().split() +
                new_paper_data.get('abstract', '').lower().split()
            )

            overlap = len(idea_keywords & paper_keywords)

            if overlap > 5:  # 简单的阈值
                # 使用 LLM 分析是否需要更新
                if self.llm_client:
                    update_analysis = await self._analyze_idea_update_need(
                        idea, new_paper_data
                    )
                else:
                    update_analysis = "建议查看新论文是否与此想法相关"

                suggestions.append({
                    'idea_id': idea.id,
                    'idea_title': idea.title,
                    'relevance_score': overlap,
                    'update_suggestion': update_analysis
                })

        # 按相关性排序
        suggestions.sort(key=lambda x: x['relevance_score'], reverse=True)

        return {
            'new_paper': new_paper_id,
            'suggestions': suggestions[:5],  # 最多返回 5 个建议
            'total_active_ideas': len(active_ideas)
        }

    async def _analyze_idea_update_need(self, idea: Idea, new_paper_data: Dict) -> str:
        """分析想法是否需要更新"""
        prompt = load_prompt(
            "insight/suggest_updates",
            idea_title=idea.title,
            idea_content=idea.content[:200],
            paper_title=new_paper_data.get('title', 'N/A'),
            paper_abstract=new_paper_data.get('abstract', 'N/A')[:300],
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        return response.strip()

    async def _synthesize_ideas(self, input_data: Dict) -> Dict:
        """
        综合多个想法，生成高层洞察

        Args:
            input_data: {
                'idea_ids': 想法 ID 列表,
                'topic': 综合主题（可选）
            }
        """
        idea_ids = input_data.get('idea_ids', [])
        topic = input_data.get('topic', '')

        if not idea_ids:
            # 获取所有活跃想法
            ideas = self.ideas_manager.get_all_ideas(status='active')[:10]
        else:
            ideas = [self.ideas_manager.get_idea(iid) for iid in idea_ids]
            ideas = [i for i in ideas if i is not None]

        if not ideas:
            return {'synthesis': 'No ideas to synthesize'}

        # 使用 LLM 综合
        if self.llm_client:
            synthesis = await self._llm_synthesize_ideas(ideas, topic)
        else:
            synthesis = self._simple_synthesis(ideas)

        return {
            'num_ideas': len(ideas),
            'synthesis': synthesis,
            'ideas_included': [{'id': i.id, 'title': i.title} for i in ideas]
        }

    async def _llm_synthesize_ideas(self, ideas: List[Idea], topic: str = "") -> str:
        """使用 LLM 综合想法"""
        ideas_text = "\n\n".join([
            f"**想法 {i+1}**: {idea.title}\n{idea.content[:200]}"
            for i, idea in enumerate(ideas)
        ])

        topic_hint = f"\n**关注主题**: {topic}\n" if topic else ""
        prompt = load_prompt(
            "insight/synthesize",
            topic_hint=topic_hint,
            ideas_text=ideas_text,
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        return response.strip()

    def _simple_synthesis(self, ideas: List[Idea]) -> str:
        """简单的想法综合（无 LLM）"""
        # 统计标签
        tag_counts = {}
        for idea in ideas:
            for tag in idea.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        synthesis = f"共有 {len(ideas)} 个想法。\n\n"
        synthesis += f"主要主题: {', '.join([tag for tag, _ in top_tags])}\n\n"
        synthesis += "建议使用 AI 功能获得更深入的综合分析。"

        return synthesis

    async def _review_reading_session(self, input_data: Dict) -> Dict:
        """
        回顾阅读会话，总结想法演进

        Args:
            input_data: {
                'session_id': 会话 ID
            }
        """
        session_id = input_data.get('session_id')

        if not session_id:
            # 获取最近的会话
            sessions = self.ideas_manager.get_recent_sessions(limit=1)
            if not sessions:
                return {'review': 'No reading sessions found'}
            session = sessions[0]
        else:
            session = self.ideas_manager._load_session(session_id)

        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # 获取会话中的所有想法
        ideas = [self.ideas_manager.get_idea(iid) for iid in session.ideas_created]
        ideas = [i for i in ideas if i is not None]

        # 生成回顾
        if self.llm_client and ideas:
            review = await self._generate_session_review(session, ideas)
        else:
            review = self._simple_session_review(session, ideas)

        return {
            'session': session.to_dict(),
            'ideas_created': len(ideas),
            'review': review
        }

    async def _generate_session_review(self, session, ideas: List[Idea]) -> str:
        """生成会话回顾"""
        mode_desc = "串行深度阅读" if session.mode == "serial" else "并行快速浏览"

        ideas_text = "\n".join([
            f"{i+1}. {idea.title} (v{idea.version})"
            for i, idea in enumerate(ideas)
        ])

        prompt = load_prompt(
            "insight/session_review",
            mode_desc=mode_desc,
            papers_count=str(len(session.papers)),
            ideas_count=str(len(ideas)),
            ideas_text=ideas_text,
        )

        response = self.call_llm(prompt, self._get_system_prompt())
        return response.strip()

    def _simple_session_review(self, session, ideas: List[Idea]) -> str:
        """简单的会话回顾"""
        mode_desc = "串行深度阅读" if session.mode == "serial" else "并行快速浏览"

        return f"""
阅读模式: {mode_desc}
阅读论文: {len(session.papers)} 篇
产生想法: {len(ideas)} 个
会话时长: {session.start_time} 至 {session.end_time or '进行中'}

建议使用 AI 功能获得更详细的回顾分析。
"""

    # 辅助方法

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return load_prompt("system/insight")

    # _parse_json_response 已统一到 BaseAgent

# 使用示例
if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    async def main():
        from plugins.ideas.manager import IdeasManager
        from plugins.knowledge.vector_store import VectorStore

        # 初始化组件
        ideas_manager = IdeasManager(storage_dir=Path("./data/research_notes"))
        vector_store = VectorStore(db_path=Path("./data/vector_db"))

        # 创建 Insight Agent
        config = AgentConfig(
            name="InsightAgent",
            model="claude-sonnet-4-5-20250929"
        )

        agent = InsightAgent(
            config=config,
            ideas_manager=ideas_manager,
            vector_store=vector_store
        )

        # 记录想法
        result = await agent.process({
            'command': 'record_idea',
            'title': '注意力机制是软寻址',
            'content': 'Attention 本质上是一种可微分的寻址机制...',
            'paper_id': 'paper1'
        })

        print(json.dumps(result, indent=2, ensure_ascii=False))

    asyncio.run(main())
