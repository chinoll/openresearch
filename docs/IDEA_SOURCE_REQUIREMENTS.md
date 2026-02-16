# 想法来源要求 - 学术严谨性指南

## 🎯 核心原则

**每个想法都必须有论文支持，包括组合想法**

---

## 📚 三种来源类型

### 1. 原子想法的来源

**要求**：直接从论文中提取的想法，必须引用具体位置

```python
原子想法："注意力机制是软寻址"

来源：
  论文: 1706.03762 (Transformer)
  章节: Introduction
  页码: 1
  引用: "...relies entirely on an attention mechanism..."
```

**标准**：
- ✅ 必须有至少一个来源
- ✅ 来源必须精确（章节/页码）
- ✅ 建议包含原文引用

---

### 2. 组合想法的来源 - 两部分

#### Part A: 继承来源（自动）

从父想法自动继承的来源：

```python
想法A来源: Transformer论文, §Introduction
想法B来源: BERT论文, §Introduction
         ↓
组合想法自动继承这两个来源
```

#### Part B: 组合逻辑来源（应该有）⭐

**关键问题**：你为什么这样组合这两个想法？

**三种情况**：

##### 情况1: 论文中明确提到组合关系

```python
组合想法："Transformer + 双向预训练 = BERT"

新来源（支持组合逻辑）：
  论文: 1810.04805 (BERT)
  章节: Introduction
  引用: "We introduce BERT...built on Transformer architecture"
  笔记: "BERT论文中明确说明使用了Transformer作为基础"
```

##### 情况2: 综述论文中的分析

```python
组合想法："规模化导致涌现能力"

新来源：
  论文: 2206.07682 (Emergent Abilities)
  章节: Related Work
  引用: "As models scale, emergent abilities appear..."
  笔记: "综述论文分析了多个模型的规模效应"
```

##### 情况3: 你自己的洞察（需要寻找支持）

```python
组合想法："注意力机制的三个优势组合起来"

# 理想情况：找到支持的综述或后续论文
新来源：
  论文: 2002.04745 (Attention Survey)
  章节: Discussion
  引用: "The combination of these properties..."

# 如果找不到：
新来源：
  论文: 1706.03762 (Transformer)
  章节: Conclusion
  引用: "Future work should explore..."
  笔记: "虽然原论文没有明确这个组合，但暗示了这个方向"
  confidence: 0.7  # 降低置信度
```

---

## 🔥 最佳实践

### 规则 1: 组合想法优先寻找新来源

**在创建组合想法前，先问自己**：
1. 有没有论文明确讨论了这个组合？
2. 有没有综述论文分析了这些想法的关系？
3. 后续论文有没有引用这些想法？

**示例**：

```bash
# 想组合：想法A（Transformer） + 想法B（BERT）

# 第1步：寻找支持
# → BERT论文的Introduction章节明确提到基于Transformer
# → 找到了！使用BERT论文作为组合逻辑的来源

# 第2步：创建组合想法
python scripts/structured_ideas_cli.py --composite

父想法: A (Transformer) + B (BERT)
新来源: BERT论文, §Introduction, "built on Transformer"
```

---

### 规则 2: 如果找不到直接支持，降低置信度

```python
组合想法:
  title: "注意力机制的多个优势综合起来"
  derived_from: [想法A, 想法B, 想法C]

  # 找不到明确支持？
  sources: [...继承的来源...]
  confidence: 0.6  # 降低置信度
  notes: "这是基于多篇论文的个人综合，未找到明确支持"
```

---

### 规则 3: 标记来源的用途

**扩展Source类**：

```python
Source(
    paper_id="1810.04805",
    section="Introduction",
    quote="...",
    purpose="combination_logic"  # 新字段：来源用途
)

# purpose可以是:
# - "primary": 原子想法的主要来源
# - "supporting": 支持性来源
# - "combination_logic": 支持组合逻辑
# - "contradicting": 提供对比观点
```

---

## 💡 实际工作流

### 工作流 1: 严格模式

```bash
# 1. 创建原子想法A
python scripts/structured_ideas_cli.py --atomic 1706_03762
# 想法A: "注意力机制替代循环"
# 来源: Transformer, §Introduction

# 2. 创建原子想法B
python scripts/structured_ideas_cli.py --atomic 1810_04805
# 想法B: "双向预训练很重要"
# 来源: BERT, §Introduction

# 3. 在创建组合想法前，先阅读BERT论文查找组合依据
python main.py --arxiv 1810.04805
# 阅读 → 发现BERT论文明确提到使用Transformer

# 4. 创建组合想法，添加新来源
python scripts/structured_ideas_cli.py --composite
# 父想法: A + B
# 新来源: BERT论文, §Introduction, "We use Transformer..."
```

---

### 工作流 2: 探索模式（允许无新来源）

```bash
# 快速探索时，可以先创建组合想法
python scripts/structured_ideas_cli.py --composite
# 父想法: A + B
# 新来源: (跳过)
# confidence: 0.5
# status: "draft"

# 后续补充来源
python scripts/structured_ideas_cli.py --update <idea_id>
# 添加新来源...
# confidence: 0.8 → 1.0
# status: "validated"
```

---

## 📊 想法质量评分

### 自动评分标准

```python
def calculate_idea_quality(idea):
    score = 0

    # 基础分
    if idea.type == "atomic":
        score += 50
        if len(idea.sources) >= 1:
            score += 30

    elif idea.type == "composite":
        score += 40

        # 继承来源
        inherited_sources = count_inherited_sources(idea)
        score += min(inherited_sources * 5, 20)

        # 新来源（关键）
        new_sources = count_new_sources(idea)
        if new_sources > 0:
            score += 30  # 有新来源，高分
        else:
            score -= 10  # 无新来源，扣分

    # 其他因素
    if idea.quote:
        score += 10
    if idea.confidence >= 0.8:
        score += 10

    return score

# 分级
# 90-100: Excellent (有明确新来源支持)
# 70-89: Good (继承来源充分)
# 50-69: Fair (基本可用)
# <50: Needs improvement (缺乏支持)
```

---

## 🎯 推荐策略

### 对于不同类型的组合

#### extends (扩展)
**推荐**：寻找后续论文作为新来源
```
想法A: "注意力机制"
     ↓ [extends]
想法B: "多头注意力"

新来源: 同一篇论文的后续章节
或: 引用原论文并扩展的后续论文
```

#### combines (组合)
**强烈推荐**：必须有新来源
```
想法A + 想法B
     ↓ [combines]
组合想法

新来源: 必须！
- 综述论文
- 或明确提到组合的论文
```

#### contradicts (矛盾)
**必须有**：对比分析的来源
```
想法A vs 想法B
     ↓ [contradicts]
对比想法

新来源: 必须！
- 对比实验的论文
- 或分析两者差异的综述
```

---

## 🔧 系统改进建议

### 建议 1: 添加来源检查

```python
def create_composite_idea(self, ..., require_new_source=True):
    """
    Args:
        require_new_source: 是否要求新来源（默认True）
    """
    if require_new_source and not sources:
        raise ValueError(
            "组合想法应该有新的来源来支持组合逻辑。\n"
            "如果是探索性想法，可以设置 require_new_source=False"
        )
```

### 建议 2: 来源用途标记

```python
Source(
    paper_id="...",
    section="...",
    purpose="combination_logic",  # 标记这个来源的作用
    confidence=0.9  # 来源的置信度
)
```

### 建议 3: 想法状态管理

```python
StructuredIdea(
    status="draft",      # 初始状态，可能缺少来源
    # ... 补充来源后 ...
    status="validated",  # 已验证，来源充分
    # ... 发表后 ...
    status="published"   # 已发表
)
```

---

## 📚 总结

### 核心要求

| 想法类型 | 来源要求 | 严格程度 |
|---------|---------|---------|
| 原子想法 | **必须有** | 强制 |
| 组合想法 - 继承来源 | 自动 | N/A |
| 组合想法 - 新来源 | **强烈推荐** | 建议强制 |

### 最佳实践

1. ✅ **创建组合想法前先寻找支持**
   - 阅读相关论文
   - 查找综述
   - 寻找后续引用

2. ✅ **标记来源用途**
   - 区分主要来源、支持来源、组合逻辑来源

3. ✅ **使用置信度**
   - 有明确支持：1.0
   - 有暗示支持：0.7-0.9
   - 个人推断：0.5-0.6

4. ✅ **状态管理**
   - draft → 探索阶段
   - validated → 有充分来源
   - published → 已用于发表

---

**记住**：学术研究中，"为什么这样组合"和"想法本身"一样重要！
