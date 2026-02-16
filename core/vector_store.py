"""
Vector Store - 向量数据库管理
用于论文的语义搜索和相似度计算
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
import numpy as np

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logging.warning("ChromaDB not available")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("SentenceTransformers not available")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorStore:
    """向量数据库封装"""

    def __init__(self,
                 db_path: Path,
                 collection_name: str = "research_papers",
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        初始化向量存储

        Args:
            db_path: 数据库存储路径
            collection_name: 集合名称
            embedding_model: 嵌入模型名称
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name

        # 初始化嵌入模型
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.info(f"Loading embedding model: {embedding_model}")
            self.embedding_model = SentenceTransformer(embedding_model)
        else:
            logger.warning("SentenceTransformers not available, using mock embeddings")
            self.embedding_model = None

        # 初始化 ChromaDB
        if CHROMADB_AVAILABLE:
            self.client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=Settings(anonymized_telemetry=False)
            )
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Research papers vector database"}
            )
            logger.info(f"ChromaDB initialized at {self.db_path}")
        else:
            logger.warning("ChromaDB not available, using in-memory storage")
            self.client = None
            self.collection = None
            self._memory_store = {}  # 简单的内存存储

    def add_paper(self,
                  paper_id: str,
                  title: str,
                  abstract: str,
                  full_text: str = "",
                  metadata: Dict = None) -> bool:
        """
        添加论文到向量数据库

        Args:
            paper_id: 论文唯一标识
            title: 标题
            abstract: 摘要
            full_text: 全文（可选）
            metadata: 额外元数据

        Returns:
            是否成功
        """
        try:
            # 构建要向量化的文本
            text_to_embed = f"{title}\n\n{abstract}"
            if full_text:
                # 限制全文长度，避免过长
                text_to_embed += f"\n\n{full_text[:5000]}"

            # 生成嵌入向量
            embedding = self._get_embedding(text_to_embed)

            # 准备元数据
            meta = metadata or {}
            meta.update({
                'paper_id': paper_id,
                'title': title,
                'abstract': abstract[:500]  # 限制长度
            })

            if self.collection:
                # 使用 ChromaDB
                self.collection.add(
                    ids=[paper_id],
                    embeddings=[embedding.tolist()],
                    metadatas=[meta],
                    documents=[text_to_embed]
                )
            else:
                # 使用内存存储
                self._memory_store[paper_id] = {
                    'embedding': embedding,
                    'metadata': meta,
                    'text': text_to_embed
                }

            logger.info(f"Added paper to vector store: {paper_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding paper to vector store: {e}")
            return False

    def search_similar(self,
                      query: str = None,
                      paper_id: str = None,
                      top_k: int = 5,
                      min_similarity: float = 0.0) -> List[Dict]:
        """
        搜索相似论文

        Args:
            query: 查询文本（与 paper_id 二选一）
            paper_id: 论文 ID（与 query 二选一）
            top_k: 返回结果数量
            min_similarity: 最小相似度阈值

        Returns:
            相似论文列表
        """
        try:
            # 获取查询向量
            if query:
                query_embedding = self._get_embedding(query)
            elif paper_id:
                query_embedding = self._get_paper_embedding(paper_id)
            else:
                raise ValueError("Must provide either query or paper_id")

            if self.collection:
                # 使用 ChromaDB 查询
                results = self.collection.query(
                    query_embeddings=[query_embedding.tolist()],
                    n_results=top_k
                )

                similar_papers = []
                for i in range(len(results['ids'][0])):
                    similarity = 1 - results['distances'][0][i]  # 转换距离为相似度

                    if similarity >= min_similarity:
                        similar_papers.append({
                            'paper_id': results['ids'][0][i],
                            'similarity': float(similarity),
                            'metadata': results['metadatas'][0][i],
                            'text': results['documents'][0][i][:200]
                        })

            else:
                # 使用内存存储的相似度计算
                similar_papers = []
                for pid, data in self._memory_store.items():
                    if pid == paper_id:
                        continue

                    similarity = self._cosine_similarity(
                        query_embedding,
                        data['embedding']
                    )

                    if similarity >= min_similarity:
                        similar_papers.append({
                            'paper_id': pid,
                            'similarity': float(similarity),
                            'metadata': data['metadata'],
                            'text': data['text'][:200]
                        })

                # 排序并限制数量
                similar_papers.sort(key=lambda x: x['similarity'], reverse=True)
                similar_papers = similar_papers[:top_k]

            return similar_papers

        except Exception as e:
            logger.error(f"Error searching similar papers: {e}")
            return []

    def get_paper_by_id(self, paper_id: str) -> Optional[Dict]:
        """根据 ID 获取论文"""
        try:
            if self.collection:
                result = self.collection.get(ids=[paper_id])
                if result['ids']:
                    return {
                        'paper_id': result['ids'][0],
                        'metadata': result['metadatas'][0],
                        'text': result['documents'][0]
                    }
            else:
                if paper_id in self._memory_store:
                    return {
                        'paper_id': paper_id,
                        'metadata': self._memory_store[paper_id]['metadata'],
                        'text': self._memory_store[paper_id]['text']
                    }

            return None

        except Exception as e:
            logger.error(f"Error getting paper by ID: {e}")
            return None

    def _get_embedding(self, text: str) -> np.ndarray:
        """生成文本嵌入向量"""
        if self.embedding_model:
            return self.embedding_model.encode(text, convert_to_numpy=True)
        else:
            # Mock embedding for testing
            return np.random.rand(384)

    def _get_paper_embedding(self, paper_id: str) -> np.ndarray:
        """获取已存储论文的嵌入向量"""
        if self.collection:
            result = self.collection.get(
                ids=[paper_id],
                include=['embeddings']
            )
            if result['embeddings']:
                return np.array(result['embeddings'][0])
        else:
            if paper_id in self._memory_store:
                return self._memory_store[paper_id]['embedding']

        raise ValueError(f"Paper not found: {paper_id}")

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm_a = np.linalg.norm(vec1)
        norm_b = np.linalg.norm(vec2)
        return dot_product / (norm_a * norm_b)

    def get_all_papers(self) -> List[str]:
        """获取所有论文 ID"""
        try:
            if self.collection:
                result = self.collection.get()
                return result['ids']
            else:
                return list(self._memory_store.keys())
        except Exception as e:
            logger.error(f"Error getting all papers: {e}")
            return []

    def count(self) -> int:
        """返回论文数量"""
        if self.collection:
            return self.collection.count()
        else:
            return len(self._memory_store)

    def delete_paper(self, paper_id: str) -> bool:
        """删除论文"""
        try:
            if self.collection:
                self.collection.delete(ids=[paper_id])
            else:
                if paper_id in self._memory_store:
                    del self._memory_store[paper_id]

            logger.info(f"Deleted paper: {paper_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting paper: {e}")
            return False


# 使用示例
if __name__ == "__main__":
    # 创建向量存储
    store = VectorStore(
        db_path=Path("./data/vector_db"),
        collection_name="test_papers"
    )

    # 添加论文
    store.add_paper(
        paper_id="2301.00001",
        title="Attention Is All You Need",
        abstract="The dominant sequence transduction models...",
        metadata={'year': 2017, 'venue': 'NeurIPS'}
    )

    # 搜索相似论文
    similar = store.search_similar(
        query="transformer neural networks",
        top_k=3
    )

    print(f"Found {len(similar)} similar papers")
    for paper in similar:
        print(f"  - {paper['metadata']['title']} (similarity: {paper['similarity']:.3f})")
