"""
Knowledge Graph - 知识图谱管理
构建和维护论文之间的关系网络
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
import json
import pickle

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logging.warning("NetworkX not available")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PaperNode:
    """论文节点"""

    def __init__(self, paper_id: str, title: str, authors: List[str],
                 year: int = None, venue: str = None, **kwargs):
        self.paper_id = paper_id
        self.title = title
        self.authors = authors
        self.year = year
        self.venue = venue
        self.metadata = kwargs

    def to_dict(self) -> Dict:
        return {
            'paper_id': self.paper_id,
            'title': self.title,
            'authors': self.authors,
            'year': self.year,
            'venue': self.venue,
            **self.metadata
        }


class KnowledgeGraph:
    """论文知识图谱"""

    def __init__(self, graph_path: Path = None):
        """
        初始化知识图谱

        Args:
            graph_path: 图谱存储路径
        """
        if not NETWORKX_AVAILABLE:
            raise ImportError("NetworkX is required for KnowledgeGraph")

        self.graph = nx.DiGraph()  # 有向图（引用关系有方向性）
        self.graph_path = Path(graph_path) if graph_path else None

        if self.graph_path and self.graph_path.exists():
            self.load()

        logger.info("Knowledge graph initialized")

    def add_paper(self, paper_id: str, title: str, authors: List[str],
                  abstract: str = "", year: int = None, venue: str = None,
                  keywords: List[str] = None, **kwargs) -> bool:
        """
        添加论文节点

        Args:
            paper_id: 论文 ID
            title: 标题
            authors: 作者列表
            abstract: 摘要
            year: 发表年份
            venue: 发表会议/期刊
            keywords: 关键词
            **kwargs: 其他元数据

        Returns:
            是否成功
        """
        try:
            node_attrs = {
                'title': title,
                'authors': authors,
                'abstract': abstract[:500] if abstract else "",
                'year': year,
                'venue': venue,
                'keywords': keywords or [],
                'node_type': 'paper',
                **kwargs
            }

            self.graph.add_node(paper_id, **node_attrs)
            logger.info(f"Added paper node: {paper_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding paper node: {e}")
            return False

    def add_citation(self, citing_paper: str, cited_paper: str,
                    context: str = "") -> bool:
        """
        添加引用关系

        Args:
            citing_paper: 引用论文 ID
            cited_paper: 被引论文 ID
            context: 引用上下文

        Returns:
            是否成功
        """
        try:
            # 确保两个节点都存在
            if citing_paper not in self.graph:
                logger.warning(f"Citing paper not in graph: {citing_paper}")
                return False

            if cited_paper not in self.graph:
                # 可以添加一个占位符节点
                self.graph.add_node(cited_paper, node_type='paper', title='Unknown')

            self.graph.add_edge(
                citing_paper,
                cited_paper,
                relation='cites',
                context=context
            )

            logger.debug(f"Added citation: {citing_paper} -> {cited_paper}")
            return True

        except Exception as e:
            logger.error(f"Error adding citation: {e}")
            return False

    def add_similarity_edge(self, paper1: str, paper2: str,
                           similarity: float, similarity_type: str = "semantic") -> bool:
        """
        添加相似性边（无向）

        Args:
            paper1: 论文1 ID
            paper2: 论文2 ID
            similarity: 相似度分数
            similarity_type: 相似度类型（semantic, methodological, etc.）

        Returns:
            是否成功
        """
        try:
            # 检查节点是否存在
            if paper1 not in self.graph or paper2 not in self.graph:
                logger.warning(f"One or both papers not in graph: {paper1}, {paper2}")
                return False

            # 添加双向边表示相似性
            self.graph.add_edge(
                paper1, paper2,
                relation='similar',
                similarity=similarity,
                similarity_type=similarity_type
            )
            self.graph.add_edge(
                paper2, paper1,
                relation='similar',
                similarity=similarity,
                similarity_type=similarity_type
            )

            logger.debug(f"Added similarity edge: {paper1} <-> {paper2} ({similarity:.3f})")
            return True

        except Exception as e:
            logger.error(f"Error adding similarity edge: {e}")
            return False

    def get_paper(self, paper_id: str) -> Optional[Dict]:
        """获取论文节点信息"""
        if paper_id in self.graph:
            return dict(self.graph.nodes[paper_id])
        return None

    def get_citations(self, paper_id: str, direction: str = 'out') -> List[str]:
        """
        获取引用关系

        Args:
            paper_id: 论文 ID
            direction: 'out' (此论文引用了谁), 'in' (谁引用了此论文), 'both'

        Returns:
            相关论文 ID 列表
        """
        if paper_id not in self.graph:
            return []

        citations = []

        if direction in ['out', 'both']:
            # 此论文引用的其他论文
            for _, target in self.graph.out_edges(paper_id):
                if self.graph[paper_id][target].get('relation') == 'cites':
                    citations.append(target)

        if direction in ['in', 'both']:
            # 引用此论文的其他论文
            for source, _ in self.graph.in_edges(paper_id):
                if self.graph[source][paper_id].get('relation') == 'cites':
                    citations.append(source)

        return citations

    def get_similar_papers(self, paper_id: str, min_similarity: float = 0.7) -> List[Dict]:
        """
        获取相似论文

        Args:
            paper_id: 论文 ID
            min_similarity: 最小相似度阈值

        Returns:
            相似论文列表，包含 ID 和相似度
        """
        if paper_id not in self.graph:
            return []

        similar_papers = []

        for neighbor in self.graph.neighbors(paper_id):
            edge_data = self.graph[paper_id][neighbor]
            if edge_data.get('relation') == 'similar':
                similarity = edge_data.get('similarity', 0)
                if similarity >= min_similarity:
                    similar_papers.append({
                        'paper_id': neighbor,
                        'similarity': similarity,
                        'similarity_type': edge_data.get('similarity_type', 'unknown')
                    })

        # 按相似度排序
        similar_papers.sort(key=lambda x: x['similarity'], reverse=True)
        return similar_papers

    def find_research_path(self, start_paper: str, end_paper: str,
                          max_depth: int = 5) -> Optional[List[str]]:
        """
        查找两篇论文之间的研究路径

        Args:
            start_paper: 起始论文
            end_paper: 目标论文
            max_depth: 最大搜索深度

        Returns:
            路径（论文 ID 列表）或 None
        """
        try:
            if start_paper not in self.graph or end_paper not in self.graph:
                return None

            # 使用最短路径算法
            path = nx.shortest_path(
                self.graph.to_undirected(),
                source=start_paper,
                target=end_paper
            )
            return path if len(path) <= max_depth + 1 else None

        except nx.NetworkXNoPath:
            logger.debug(f"No path found between {start_paper} and {end_paper}")
            return None
        except Exception as e:
            logger.error(f"Error finding research path: {e}")
            return None

    def get_citation_network(self, paper_id: str, depth: int = 2) -> Dict:
        """
        获取引用网络

        Args:
            paper_id: 论文 ID
            depth: 引用深度

        Returns:
            引用网络子图信息
        """
        if paper_id not in self.graph:
            return {'nodes': [], 'edges': []}

        # BFS 遍历引用网络
        visited = set()
        queue = [(paper_id, 0)]
        nodes = []
        edges = []

        while queue:
            current, current_depth = queue.pop(0)

            if current in visited or current_depth > depth:
                continue

            visited.add(current)

            # 添加节点信息
            if current in self.graph:
                node_data = self.graph.nodes[current]
                nodes.append({
                    'id': current,
                    'title': node_data.get('title', 'Unknown'),
                    'year': node_data.get('year'),
                    'depth': current_depth
                })

            if current_depth < depth:
                # 添加出边（此论文引用的）
                for _, target in self.graph.out_edges(current):
                    if self.graph[current][target].get('relation') == 'cites':
                        edges.append({
                            'source': current,
                            'target': target,
                            'type': 'cites'
                        })
                        queue.append((target, current_depth + 1))

                # 添加入边（引用此论文的）
                for source, _ in self.graph.in_edges(current):
                    if self.graph[source][current].get('relation') == 'cites':
                        edges.append({
                            'source': source,
                            'target': current,
                            'type': 'cites'
                        })
                        queue.append((source, current_depth + 1))

        return {'nodes': nodes, 'edges': edges}

    def get_statistics(self) -> Dict:
        """获取图谱统计信息"""
        return {
            'num_papers': self.graph.number_of_nodes(),
            'num_edges': self.graph.number_of_edges(),
            'num_citations': sum(1 for _, _, d in self.graph.edges(data=True)
                                if d.get('relation') == 'cites'),
            'num_similarity_edges': sum(1 for _, _, d in self.graph.edges(data=True)
                                       if d.get('relation') == 'similar') // 2,
            'avg_degree': sum(dict(self.graph.degree()).values()) / max(self.graph.number_of_nodes(), 1)
        }

    def get_influential_papers(self, top_k: int = 10) -> List[Dict]:
        """
        获取最有影响力的论文（基于引用次数）

        Args:
            top_k: 返回数量

        Returns:
            影响力论文列表
        """
        # 计算每篇论文的被引次数
        citation_counts = {}
        for paper_id in self.graph.nodes():
            in_citations = sum(1 for _, _, d in self.graph.in_edges(paper_id, data=True)
                             if d.get('relation') == 'cites')
            citation_counts[paper_id] = in_citations

        # 排序
        sorted_papers = sorted(citation_counts.items(), key=lambda x: x[1], reverse=True)

        # 构建结果
        influential = []
        for paper_id, citations in sorted_papers[:top_k]:
            paper_data = self.graph.nodes[paper_id]
            influential.append({
                'paper_id': paper_id,
                'title': paper_data.get('title', 'Unknown'),
                'citations': citations,
                'year': paper_data.get('year')
            })

        return influential

    def save(self, path: Path = None):
        """保存图谱到文件"""
        save_path = path or self.graph_path

        if not save_path:
            logger.warning("No save path specified")
            return

        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 保存为 pickle 格式（保留所有属性）
            with open(save_path, 'wb') as f:
                pickle.dump(self.graph, f)

            # 同时保存 JSON 格式（便于查看）
            json_path = save_path.with_suffix('.json')
            graph_data = nx.node_link_data(self.graph)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Graph saved to {save_path}")

        except Exception as e:
            logger.error(f"Error saving graph: {e}")

    def load(self, path: Path = None):
        """从文件加载图谱"""
        load_path = path or self.graph_path

        if not load_path or not Path(load_path).exists():
            logger.warning(f"Graph file not found: {load_path}")
            return

        try:
            with open(load_path, 'rb') as f:
                self.graph = pickle.load(f)

            logger.info(f"Graph loaded from {load_path}")
            logger.info(f"Statistics: {self.get_statistics()}")

        except Exception as e:
            logger.error(f"Error loading graph: {e}")


# 使用示例
if __name__ == "__main__":
    # 创建知识图谱
    kg = KnowledgeGraph(graph_path=Path("./data/knowledge_graph.pkl"))

    # 添加论文
    kg.add_paper(
        paper_id="paper1",
        title="Attention Is All You Need",
        authors=["Vaswani et al."],
        year=2017,
        keywords=["transformer", "attention"]
    )

    kg.add_paper(
        paper_id="paper2",
        title="BERT: Pre-training of Deep Bidirectional Transformers",
        authors=["Devlin et al."],
        year=2018,
        keywords=["BERT", "pre-training"]
    )

    # 添加引用关系
    kg.add_citation("paper2", "paper1", context="builds on transformer architecture")

    # 添加相似性
    kg.add_similarity_edge("paper1", "paper2", similarity=0.85)

    # 查询
    citations = kg.get_citations("paper2")
    print(f"Paper2 cites: {citations}")

    similar = kg.get_similar_papers("paper1")
    print(f"Similar to Paper1: {similar}")

    # 保存
    kg.save()
