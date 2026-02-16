```markdown
# 结构化学术想法系统 - 完整指南

## 🎯 核心理念

### 为什么要结构化？

**传统想法管理的问题**：
- ❌ 想法来源不明确
- ❌ 想法之间关系模糊
- ❌ 难以追溯思考过程
- ❌ 缺乏学术严谨性

**我们的解决方案**：
- ✅ **强制引用来源** - 每个想法必须引用至少一篇论文
- ✅ **章节级定位** - 精确到论文的具体章节、页码
- ✅ **想法血统追踪** - 清晰的衍生关系（谁从谁而来）
- ✅ **交叉变异** - 想法可以组合、扩展、精炼

---

## 📚 核心概念

### 1. 原子想法 (Atomic Idea)

**定义**：从论文中直接提取的单一想法，必须引用来源。

**结构**：
```json
{
  "id": "a1b2c3d4",
  "title": "注意力机制是软寻址",
  "content": "详细描述...",
  "type": "atomic",
  "sources": [
    {
      "paper_id": "1706_03762",
      "section": "Introduction",
      "page": 1,
      "quote": "原文引用..."
    }
  ],
  "category": "concept",
  "tags": ["attention", "transformer"]
}
```

**示例**：
- 从 Transformer 论文提取：**"注意力机制替代循环"**
- 从 BERT 论文提取：**"双向预训练的重要性"**
- 从 GPT-3 论文提取：**"规模定律的涌现能力"**

---

### 2. 组合想法 (Composite Idea)

**定义**：从多个想法衍生的新想法，通过交叉变异产生。

**结构**：
```json
{
  "id": "e5f6g7h8",
  "title": "注意力机制实现多视角理解",
  "content": "组合描述...",
  "type": "composite",
  "derived_from": [
    {
      "idea_id": "a1b2c3d4",
      "relationship": "extends"
    },
    {
      "idea_id": "c3d4e5f6",
      "relationship": "combines"
    }
  ],
  "sources": [...]  // 自动继承父想法的来源
}
```

**关系类型**：
- **extends** (扩展) - A 扩展了 B 的概念
- **combines** (组合) - A 结合了 B 和 C
- **contradicts** (矛盾) - A 与 B 相矛盾
- **refines** (精炼) - A 精炼了 B
- **applies** (应用) - A 应用了 B 到新场景
- **questions** (质疑) - A 质疑 B 的假设
- **supports** (支持) - A 支持 B 的观点

---

### 3. 来源 (Source)

**结构**：
```json
{
  "paper_id": "1706_03762",
  "section": "Model Architecture",
  "subsection": "Multi-Head Attention",
  "page": 5,
  "paragraph": 2,
  "quote": "Multi-head attention allows...",
  "notes": "这里提出了关键创新"
}
```

**章节定位示例**：
- `Introduction` → 引言
- `Related Work` → 相关工作
- `Method` → 方法
- `Experiments` → 实验
- `Conclusion` → 结论

---

## 🚀 使用流程

### 场景 1: 阅读单篇论文，提取原子想法

```bash
# 1. 添加论文到系统
python main.py --arxiv 1706.03762  # Attention Is All You Need

# 2. 创建第一个原子想法
python scripts/structured_ideas_cli.py --atomic 1706_03762
```

**交互过程**：
```
📝 创建原子想法（必须引用至少一篇论文）
======================================================================

想法标题: 注意力机制替代循环神经网络

想法内容（输入 'END' 结束）:
Transformer 完全基于注意力机制，不使用任何循环或卷积。
这使得模型可以并行化训练，显著提升了效率。
END

--- 来源 1 ---
论文 ID (留空结束): 1706_03762
章节 (可选): Introduction
子章节 (可选):
页码 (可选): 1
原文引用（输入 'END' 结束，可选）:
The Transformer model architecture eschews recurrence and instead
relies entirely on an attention mechanism...
END
笔记 (可选): 论文的核心创新点

添加更多来源？(y/N): n

类别 (concept/method/finding/insight): concept
标签 (逗号分隔): attention, transformer, parallelization

✓ 原子想法已创建!
  ID: a1b2c3d4
  标题: 注意力机制替代循环神经网络
  来源: 1 个
    1. 1706_03762, §Introduction, p.1
```

---

### 场景 2: 读第二篇论文，创建更多原子想法

```bash
# 添加 BERT 论文
python main.py --arxiv 1810.04805

# 创建第二个原子想法
python scripts/structured_ideas_cli.py --atomic 1810_04805
```

**输入示例**：
```
标题: 双向预训练优于单向
内容:
BERT 通过 Masked Language Model 实现双向训练，
相比 GPT 的单向训练，可以更好地理解上下文。
END

来源:
  论文 ID: 1810_04805
  章节: Introduction
  页码: 1
  引用: "...pre-train deep bidirectional representations..."
```

---

### 场景 3: 交叉变异 - 创建组合想法

```bash
# 创建组合想法
python scripts/structured_ideas_cli.py --composite
```

**交互过程**：
```
🔄 创建组合想法（交叉变异）
======================================================================

可用想法:
1. [a1b2c3d4] 注意力机制替代循环神经网络 (atomic)
2. [c3d4e5f6] 双向预训练优于单向 (atomic)
3. [e5f6g7h8] 多头注意力提供多视角 (atomic)

选择要组合的想法（至少一个）:

输入想法编号或 ID: 1

与 '注意力机制替代循环神经网络' 的关系:
1. extends (扩展)
2. combines (组合)
3. contradicts (矛盾)
4. refines (精炼)
5. applies (应用)
6. questions (质疑)
7. supports (支持)

选择关系类型 (1-7): 1

✓ 已添加: 注意力机制替代循环神经网络 (extends)

输入想法编号或 ID: 2

与 '双向预训练优于单向' 的关系:
...选择: 2 (combines)

✓ 已添加: 双向预训练优于单向 (combines)

输入想法编号或 ID: (回车结束)

新想法标题: Transformer + 双向预训练 = BERT 的强大表示能力

新想法内容（描述如何组合/扩展父想法）:
BERT 将 Transformer 的注意力机制与双向预训练结合，
创造了比单向模型更强的表示能力。
注意力机制提供了灵活的上下文建模，
而双向训练确保了完整的上下文理解。
END

类别: insight
标签: BERT, transformer, bidirectional

✓ 组合想法已创建!
  ID: i9j0k1l2
  标题: Transformer + 双向预训练 = BERT 的强大表示能力
  类型: composite
  父想法: 2 个
    - [extends] 注意力机制替代循环神经网络
    - [combines] 双向预训练优于单向
  继承来源: 2 个
```

---

## 📊 查看和管理

### 列出所有想法

```bash
# 列出所有想法
python scripts/structured_ideas_cli.py --list

# 只列出原子想法
python scripts/structured_ideas_cli.py --list atomic

# 只列出组合想法
python scripts/structured_ideas_cli.py --list composite
```

### 查看想法详情

```bash
python scripts/structured_ideas_cli.py --show <idea_id>
```

**输出示例**：
```
======================================================================
🔶 Transformer + 双向预训练 = BERT 的强大表示能力
======================================================================

ID: i9j0k1l2
类型: composite
类别: insight
状态: draft
创建: 2024-01-15

标签: BERT, transformer, bidirectional

--- 内容 ---
BERT 将 Transformer 的注意力机制与双向预训练结合，
创造了比单向模型更强的表示能力...

--- 来源 (2 个) ---
1. 1706_03762, §Introduction, p.1
   引用: The Transformer model architecture eschews recurrence...

2. 1810_04805, §Introduction, p.1
   引用: ...pre-train deep bidirectional representations...

--- 衍生自 (2 个想法) ---
  [extends] 注意力机制替代循环神经网络
  [combines] 双向预训练优于单向

--- 衍生出 (1 个想法) ---
  [applies] BERT 在下游任务的应用策略
```

### 查看想法血统

```bash
python scripts/structured_ideas_cli.py --lineage <idea_id>
```

**输出示例**：
```
🌳 想法血统: Transformer + 双向预训练 = BERT 的强大表示能力
======================================================================

=== 祖先 (2 个) ===
  ↑ [extends] 注意力机制替代循环神经网络
    类型: atomic | ID: a1b2c3d4

  ↑ [combines] 双向预训练优于单向
    类型: atomic | ID: c3d4e5f6

=== 当前想法 ===
  • Transformer + 双向预训练 = BERT 的强大表示能力
    类型: composite | 类别: insight
    来源: 2 个

=== 后代 (1 个) ===
  ↓ [applies] BERT 在下游任务的应用策略
    类型: composite | ID: m3n4o5p6
```

### 按论文查看想法

```bash
python scripts/structured_ideas_cli.py --paper 1706_03762
```

**输出示例**：
```
📄 论文 1706_03762 的相关想法 (3 个)
======================================================================
1. 注意力机制替代循环神经网络 (atomic)
    → 1706_03762, §Introduction, p.1

2. 多头注意力提供多视角 (atomic)
    → 1706_03762, §Model Architecture, §Multi-Head Attention, p.5

3. Transformer + 双向预训练 = BERT 的强大表示能力 (composite)
    → 1706_03762, §Introduction, p.1
```

### 可视化想法网络

```bash
# 显示所有想法的关系网络
python scripts/structured_ideas_cli.py --network

# 显示特定想法的网络
python scripts/structured_ideas_cli.py --network <idea_id>
```

**输出示例**：
```
🕸️  想法关系网络
======================================================================
=== Ancestors ===
  ← [extends] 注意力机制替代循环神经网络
  ← [combines] 双向预训练优于单向

=== Current ===
  • Transformer + 双向预训练 = BERT 的强大表示能力 (composite)
    Sources: 2

=== Descendants ===
  → [applies] BERT 在下游任务的应用策略
  → [refines] 改进的预训练策略
```

---

## 🎯 高级用法

### 想法类别系统

**concept** (概念)
- 理论性想法
- 新的概念定义
- 示例："注意力是软寻址"

**method** (方法)
- 技术性想法
- 具体实现方法
- 示例："多头注意力的计算方式"

**finding** (发现)
- 实验结果
- 观察到的现象
- 示例:"规模定律的涌现能力"

**insight** (洞察)
- 综合性理解
- 跨论文的发现
- 示例："Transformer 是 NLP 范式转变"

### 想法置信度

```python
# 创建时设置置信度
idea = manager.create_atomic_idea(
    title="...",
    content="...",
    sources=[...],
    confidence=0.8  # 80% 确信
)
```

**建议**：
- `1.0` - 论文中明确陈述
- `0.8` - 论文强烈暗示
- `0.6` - 合理推断
- `0.4` - 个人猜测

### 研究问题关联

```python
idea = manager.create_composite_idea(
    title="...",
    content="...",
    parent_ideas=[...],
    research_question="如何在保持效率的同时提升模型表达能力？"
)
```

---

## 📈 典型工作流

### 工作流 1: 系统化阅读某个主题

```bash
# Day 1: 读基础论文
python main.py --arxiv 1706.03762  # Transformer
python scripts/structured_ideas_cli.py --atomic 1706_03762
# 创建 3-5 个原子想法

# Day 2: 读应用论文
python main.py --arxiv 1810.04805  # BERT
python scripts/structured_ideas_cli.py --atomic 1810_04805
# 创建 3-5 个原子想法

# Day 3: 综合理解
python scripts/structured_ideas_cli.py --composite
# 创建 1-2 个组合想法，连接前两天的想法

# Day 4: 可视化
python scripts/structured_ideas_cli.py --network
python scripts/structured_ideas_cli.py --stats
```

### 工作流 2: 写文献综述

```bash
# 1. 快速添加所有论文
for paper in paper_list; do
    python main.py --arxiv $paper --quick
done

# 2. 每篇论文提取 2-3 个核心想法
for paper in paper_list; do
    python scripts/structured_ideas_cli.py --atomic $paper
done

# 3. 创建综合想法
# 按主题组合想法
python scripts/structured_ideas_cli.py --composite

# 4. 生成网络图
python scripts/structured_ideas_cli.py --network > review_structure.txt
```

### 工作流 3: 追踪研究演进

```bash
# 时间线：2017 → 2018 → 2019 → 2020

# 2017: Transformer
python scripts/structured_ideas_cli.py --atomic 1706_03762
# 想法A: "自注意力机制"

# 2018: BERT
python scripts/structured_ideas_cli.py --composite
# 想法B = extends(想法A) + 新概念"双向预训练"

# 2019: GPT-2
python scripts/structured_ideas_cli.py --composite
# 想法C = extends(想法A) + "规模化"

# 2020: GPT-3
python scripts/structured_ideas_cli.py --composite
# 想法D = extends(想法C) + "涌现能力"

# 查看演进路径
python scripts/structured_ideas_cli.py --lineage <想法D的ID>
```

---

## 📊 数据导出

### 导出为 Markdown

```python
from core.structured_ideas import StructuredIdeasManager

manager = StructuredIdeasManager(storage_dir=Path("./data/structured_research"))
ideas = manager.get_all_ideas()

with open("ideas_export.md", "w", encoding='utf-8') as f:
    for idea in ideas:
        f.write(f"# {idea.title}\n\n")
        f.write(f"**类型**: {idea.type} | **类别**: {idea.category}\n\n")
        f.write(f"{idea.content}\n\n")

        f.write(f"## 来源\n\n")
        for source in idea.sources:
            f.write(f"- {source}\n")

        if idea.derived_from:
            f.write(f"\n## 衍生自\n\n")
            for rel in idea.derived_from:
                parent = manager.get_idea(rel.idea_id)
                f.write(f"- [{rel.relationship}] {parent.title}\n")

        f.write("\n---\n\n")
```

### 导出为 BibTeX

```python
# 导出所有引用的论文
papers = set()
for idea in ideas:
    for source in idea.sources:
        papers.add(source.paper_id)

# 为每篇论文生成 BibTeX 条目
for paper_id in papers:
    print(f"@article{{{paper_id},")
    print(f"  title={{...}},")
    print(f"  author={{...}},")
    print(f"}}")
```

---

## 🎓 总结

### 核心价值

1. **学术严谨性** - 每个想法都有明确来源
2. **可追溯性** - 清晰的想法演进路径
3. **结构化** - 章节级引用，精确定位
4. **可组合** - 想法可以交叉变异产生新想法

### 与传统笔记的区别

| 特性 | 传统笔记 | 结构化想法系统 |
|------|---------|---------------|
| 来源 | 可有可无 | **必须有** |
| 精确度 | 论文级别 | **章节/页码级别** |
| 关系 | 隐式 | **显式（typed relations）** |
| 演进 | 难以追踪 | **血统清晰** |
| 组合 | 手动 | **系统化支持** |

### 适用场景

- ✅ 写文献综述
- ✅ 追踪研究演进
- ✅ 系统化阅读某主题
- ✅ 发现研究空白
- ✅ 构建知识图谱

---

开始构建你的结构化想法系统！🎓
```
