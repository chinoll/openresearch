# 疑问系统完整指南

## 📖 概述

疑问系统是专门用于记录和管理阅读论文时产生的疑问，追踪问题的解决过程。

```
阅读论文 → ❓记录疑问 → 💡寻找答案 → ✅解决问题
```

---

## 🎯 为什么需要疑问系统？

### 传统方式的问题

```
阅读论文 → 产生疑问 → ❓记在哪里？
           ↓
        时间一长
           ↓
        忘记了 😞
```

### 疑问系统的解决方案

```
阅读论文 → ❓记录疑问（系统化）
    ↓
继续阅读 → 💡找到答案（记录来源）
    ↓
后续阅读 → ✅验证答案（追踪状态）
```

**核心优势**：
- ✅ **系统化管理**：所有疑问集中管理
- ✅ **状态追踪**：未解决/部分解决/已解决
- ✅ **答案记录**：保存答案和来源
- ✅ **问题关联**：发现问题之间的联系
- ✅ **统计分析**：解决率、问题类型分布

---

## 📚 核心概念

### 1. 疑问 (Question)

**定义**：阅读论文时产生的任何疑问或不理解的地方

**数据结构**：
```python
@dataclass
class Question:
    id: str                       # 问题ID
    content: str                  # 问题内容
    paper_id: str                 # 来源论文
    section: Optional[str]        # 章节
    page: Optional[int]           # 页码
    context: Optional[str]        # 问题上下文

    # 分类
    question_type: str            # 问题类型（8种）
    importance: int               # 重要性 1-5
    difficulty: int               # 难度 1-5
    tags: List[str]               # 标签

    # 状态
    status: str                   # unsolved/partial/solved
    answers: List[Answer]         # 答案列表

    # 关联
    related_papers: List[str]     # 可能包含答案的论文
    related_insights: List[str]   # 相关洞察
    related_questions: List[str]  # 相关问题
```

### 2. 问题类型

疑问系统支持8种问题类型：

#### 1️⃣ understanding（理解性问题）
```
"什么是Masked Language Model？"
"Transformer的self-attention是如何工作的？"
"为什么要用layer normalization？"
```

#### 2️⃣ method（方法问题）
```
"为什么选择这种架构设计？"
"能否用其他方法替代？"
"这个设计有什么优势？"
```

#### 3️⃣ experiment（实验问题）
```
"为什么只在WMT上测试？"
"缺少哪些消融实验？"
"为什么不对比GPT？"
```

#### 4️⃣ application（应用问题）
```
"这个方法能应用到中文吗？"
"能用于小样本学习吗？"
"如何应用到推荐系统？"
```

#### 5️⃣ limitation（局限性问题）
```
"长序列会有什么问题？"
"计算复杂度的限制是什么？"
"这个方法不适用于哪些场景？"
```

#### 6️⃣ extension（扩展问题）
```
"如何改进这个方法？"
"未来可以往哪个方向发展？"
"能否与其他技术结合？"
```

#### 7️⃣ comparison（比较问题）
```
"这个方法和LSTM有什么区别？"
"相比RNN有什么优势？"
"为什么比baseline好？"
```

#### 8️⃣ implementation（实现问题）
```
"如何实现multi-head attention？"
"位置编码是怎么加入的？"
"训练时如何处理padding？"
```

### 3. 问题状态

```python
unsolved  ❓  # 未解决
partial   🤔  # 部分解决（有答案但不确定）
solved    ✅  # 已解决（有满意的答案）
```

### 4. 答案 (Answer)

```python
@dataclass
class Answer:
    content: str              # 答案内容
    source: str               # 来源（论文ID 或 "own_thinking"）
    section: Optional[str]    # 如果来自论文，具体章节
    page: Optional[int]       # 页码
    quote: Optional[str]      # 相关引用
    confidence: float         # 置信度 0-1
```

---

## 🔧 使用指南

### 工作流 1: 基础阅读流程

```bash
# Step 1: 下载论文
python main.py --arxiv 1810.04805

# Step 2: 开始问题记录会话
python scripts/questions_cli.py --start-session --paper 1810_04805
# 输出: 会话已开始 qsession_20260217_1430

# Step 3: 阅读时记录疑问（可重复多次）
python scripts/questions_cli.py --question

# 交互示例：
# > 问题内容: 为什么BERT使用15%的mask比例？
# > 类型: method
# > 重要性 (1-5): 4
# > 难度 (1-5): 3
# > 章节: 3.1 Pre-training BERT
# ✅ 问题已创建: q_0001

# 继续记录更多问题...
python scripts/questions_cli.py --question
# > 问题内容: MLM和CBOW有什么区别？
# > 类型: comparison
# > 重要性: 3

# Step 4: 结束会话
python scripts/questions_cli.py --end-session
# 显示统计：问题数、章节覆盖等

# Step 5: 查看未解决的问题
python scripts/questions_cli.py --list --status unsolved

# Step 6: 继续阅读其他论文，找到答案
python main.py --arxiv 1706.03762  # 阅读相关论文

# Step 7: 为问题添加答案
python scripts/questions_cli.py --add-answer --question q_0001
# > 答案: 论文中通过实验发现15%是最优的
# > 来源: 1810_04805
# > 章节: 5.1 Ablation Studies
# > 置信度: 0.9
# ✅ 答案已添加，问题状态: solved
```

### 工作流 2: 快速记录模式

```bash
# 一行命令快速记录问题
python scripts/questions_cli.py --question \
  --paper 1810_04805 \
  --content "为什么需要NSP任务？" \
  --type method \
  --importance 3

# 查看特定论文的所有问题
python scripts/questions_cli.py --list --paper 1810_04805
```

### 工作流 3: 问题管理

```bash
# 查看所有未解决的高优先级问题
python scripts/questions_cli.py --list --status unsolved --min-importance 4

# 查看特定类型的问题
python scripts/questions_cli.py --list --type understanding

# 关联相关问题
python scripts/questions_cli.py --link --question1 q_0001 --question2 q_0005

# 更新问题状态
python scripts/questions_cli.py --update-status --question q_0001 --status solved

# 查看问题详情
python scripts/questions_cli.py --show --question q_0001
```

### 工作流 4: 统计和导出

```bash
# 查看统计信息
python scripts/questions_cli.py --stats
# 显示：总问题数、解决率、类型分布等

# 导出论文的所有问题
python scripts/questions_cli.py --export --paper 1810_04805 --output bert_questions.md
```

---

## 💡 实际例子

### 例子 1: 阅读 BERT 论文

```bash
# 开始阅读
python scripts/questions_cli.py --start-session --paper 1810_04805

# 阅读 Introduction，产生疑问
python scripts/questions_cli.py --question
# > 问题: 为什么说现有模型是单向的？GPT不是双向吗？
# > 类型: understanding
# > 重要性: 4
# ✅ 问题已创建: q_0001

# 阅读 Method，继续记录
python scripts/questions_cli.py --question
# > 问题: Masked LM和Cloze task有什么区别？
# > 类型: comparison
# > 重要性: 3
# ✅ 问题已创建: q_0002

python scripts/questions_cli.py --question
# > 问题: 为什么mask 15%的token，而不是10%或20%？
# > 类型: method
# > 重要性: 4
# ✅ 问题已创建: q_0003

# 阅读 Experiments，发现答案
python scripts/questions_cli.py --add-answer --question q_0003
# > 答案: 论文在5.1节的消融实验中测试了不同mask比例，15%效果最好
# > 来源: 1810_04805
# > 章节: 5.1 Effect of Pre-training Tasks
# > 引用: "We also experiment with different masking percentages..."
# > 置信度: 0.9
# ✅ 答案已添加，问题状态: solved

# 结束会话
python scripts/questions_cli.py --end-session
# 📊 会话统计：
#    问题数: 3个
#    已解决: 1个
#    未解决: 2个
```

### 例子 2: 跨论文寻找答案

```bash
# 阅读BERT时产生疑问
python scripts/questions_cli.py --question --paper 1810_04805
# > 问题: GPT为什么是单向的？有什么技术原因吗？
# > 类型: understanding
# ✅ q_0010

# 后来阅读GPT论文，找到答案
python main.py --arxiv 1910.10683

python scripts/questions_cli.py --add-answer --question q_0010
# > 答案: GPT使用的是Transformer decoder，采用causal masking，
#         只能看到前面的token，这是语言模型的标准设置
# > 来源: 1910_10683
# > 章节: 2. Approach
# ✅ 跨论文答案已添加

# 标记相关论文
# (系统会自动将答案来源加入 related_papers)
```

### 例子 3: 问题演化

```bash
# 初始疑问
python scripts/questions_cli.py --question --paper 1706_03762
# > 问题: Transformer的复杂度是O(n²)，长序列怎么办？
# > 类型: limitation
# ✅ q_0020

# 发现相关问题
python scripts/questions_cli.py --question --paper 1706_03762
# > 问题: 有没有降低self-attention复杂度的方法？
# > 类型: extension
# ✅ q_0021

# 关联这两个问题
python scripts/questions_cli.py --link --question1 q_0020 --question2 q_0021

# 后来阅读Linformer论文，找到答案
python main.py --arxiv 2006.04768

python scripts/questions_cli.py --add-answer --question q_0021
# > 答案: Linformer使用低秩分解将复杂度降到O(n)
# > 来源: 2006_04768
# ✅ q_0021 已解决

# 部分回答原始问题
python scripts/questions_cli.py --add-answer --question q_0020
# > 答案: 可以使用Linformer等线性attention方法
# > 来源: 2006_04768
# > 置信度: 0.7  # 只是部分答案
# ✅ q_0020 状态: partial
```

---

## 🎨 CLI 命令参考

### 会话管理

```bash
# 开始问题记录会话
python scripts/questions_cli.py --start-session --paper <paper_id>

# 结束当前会话
python scripts/questions_cli.py --end-session [--notes "会话笔记"]
```

### 问题创建

```bash
# 交互式创建（推荐）
python scripts/questions_cli.py --question

# 快速一行命令
python scripts/questions_cli.py --question \
  --paper <paper_id> \
  --content "问题内容" \
  --type <question_type> \
  --importance <1-5> \
  --difficulty <1-5> \
  --section "章节" \
  --tags tag1 tag2
```

### 答案管理

```bash
# 添加答案
python scripts/questions_cli.py --add-answer --question <question_id>

# 或一行命令
python scripts/questions_cli.py --add-answer \
  --question <question_id> \
  --content "答案内容" \
  --source <paper_id_or_own_thinking> \
  --confidence <0-1>
```

### 问题查看

```bash
# 列出所有问题
python scripts/questions_cli.py --list

# 筛选：特定论文
python scripts/questions_cli.py --list --paper <paper_id>

# 筛选：特定状态
python scripts/questions_cli.py --list --status unsolved

# 筛选：特定类型
python scripts/questions_cli.py --list --type understanding

# 筛选：最低重要性
python scripts/questions_cli.py --list --min-importance 4

# 筛选：关键词搜索
python scripts/questions_cli.py --list --keyword "attention"

# 筛选：标签
python scripts/questions_cli.py --list --tags transformer attention

# 查看问题详情
python scripts/questions_cli.py --show --question <question_id>
```

### 问题管理

```bash
# 更新问题状态
python scripts/questions_cli.py --update-status \
  --question <question_id> \
  --status <unsolved|partial|solved>

# 关联问题
python scripts/questions_cli.py --link \
  --question1 <id1> \
  --question2 <id2>
```

### 统计和导出

```bash
# 查看统计
python scripts/questions_cli.py --stats

# 导出论文问题
python scripts/questions_cli.py --export \
  --paper <paper_id> \
  [--format markdown|json] \
  [--output filename]
```

---

## 🔗 与其他系统的集成

### 与洞察系统的关系

```
洞察系统:  记录所有观察（包括问题）
疑问系统:  专注于问题的追踪和解决

协同使用:
阅读 → 💭记录洞察（observation, question, insight...）
     → ❓记录疑问（专门追踪未解决的问题）
     → 💡寻找答案
     → ✅解决问题
```

**区别**：
- 洞察系统：轻量级，所有类型的观察
- 疑问系统：重量级，专注问题追踪

**适用场景**：
- 简单疑问 → 用洞察系统的 question 类型
- 重要疑问 → 用疑问系统专门追踪

### 工作流集成

```bash
# 1. 下载论文
python main.py --arxiv 1810.04805

# 2. 同时开启洞察会话和问题会话
python scripts/insights_cli.py --start-reading 1810_04805
python scripts/questions_cli.py --start-session --paper 1810_04805

# 3. 阅读时：
#    - 一般观察 → 用洞察系统
python scripts/insights_cli.py --insight
# > "BERT使用MLM"

#    - 重要疑问 → 用疑问系统
python scripts/questions_cli.py --question
# > "为什么mask 15%？"

# 4. 结束会话
python scripts/insights_cli.py --end-reading
python scripts/questions_cli.py --end-session
```

---

## 💡 最佳实践

### 1. 什么时候记录问题

#### ✅ 应该记录
- 不理解的概念或方法
- 对设计选择的疑问
- 实验设置的疑问
- 想要深入了解的点
- 发现的潜在问题
- 想要验证的假设

#### ⚠️ 不必记录
- 非常基础的常识问题（先Google）
- 与主题无关的问题
- 论文中已经解答的问题（除非需要更多细节）

### 2. 如何写好问题

#### ✅ 好的问题
```
"为什么BERT选择双向预训练而不是单向？有什么技术优势？"
→ 具体、清晰、有上下文

"Transformer的self-attention复杂度是O(n²)，处理长序列时有什么解决方案？"
→ 指出问题、寻求方案

"论文中说NSP任务有用，但为什么后续的RoBERTa又去掉了？"
→ 对比、质疑、深入思考
```

#### ❌ 不好的问题
```
"这是什么？"
→ 太模糊

"看不懂"
→ 没有具体指向

"这个方法好吗？"
→ 太宽泛，缺乏焦点
```

### 3. 重要性评分指南

```
5⭐ - 核心问题，关系到整篇论文的理解
4⭐ - 重要问题，影响对方法的理解
3⭐ - 标准问题，值得了解
2⭐ - 次要问题，可选了解
1⭐ - 琐碎问题，不影响整体理解
```

### 4. 寻找答案的策略

#### 策略1: 论文内部寻找
```
产生疑问 → 标记位置 → 继续阅读
            ↓
       在后续章节找到答案（实验、讨论部分）
```

#### 策略2: 阅读相关论文
```
产生疑问 → 查看引用论文
         → 查看被引用论文（Google Scholar）
         → 阅读综述论文
```

#### 策略3: 自己思考推理
```
产生疑问 → 基于已有知识推理
         → 记录推理过程
         → 标记为"own_thinking"
         → 置信度设低（0.5-0.7）
```

#### 策略4: 实验验证
```
产生疑问 → 设计小实验验证
         → 记录实验结果
         → 更新答案和置信度
```

### 5. 问题的生命周期

```
创建问题 (unsolved)
    ↓
找到部分答案 (partial)
    ↓
继续寻找更好答案
    ↓
找到满意答案 (solved, confidence ≥ 0.8)
    ↓
[可选] 后续验证或加深理解
```

---

## 📊 使用统计示例

```bash
$ python scripts/questions_cli.py --stats

📊 疑问系统统计
────────────────────────────────────────────

总问题数: 127
总会话数: 15
解决率: 68.5%

按状态分布:
  unsolved    :  25 ( 19.7%)
  partial     :  15 ( 11.8%)
  solved      :  87 ( 68.5%)

按类型分布:
  understanding       :  45 ( 35.4%)
  method              :  32 ( 25.2%)
  experiment          :  18 ( 14.2%)
  application         :  12 (  9.4%)
  limitation          :  10 (  7.9%)
  comparison          :   8 (  6.3%)
  implementation      :   2 (  1.6%)

按论文分布:
  1810_04805          :  28 问题
  1706_03762          :  23 问题
  1910_10683          :  19 问题
  ...
```

---

## 🎯 高级用法

### 1. 问题网络

```bash
# 发现相关问题并关联
python scripts/questions_cli.py --link --question1 q_0001 --question2 q_0005

# 构建问题族
q_0001: Transformer为什么用self-attention？
  ├─ q_0002: Self-attention的复杂度问题
  ├─ q_0003: Multi-head的作用是什么？
  └─ q_0004: 位置编码为什么必要？
```

### 2. 答案的演化

```python
# 问题: Transformer能处理多长的序列？

# 答案1 (初步理解)
来源: 1706_03762
内容: 论文中最长测试了256个token
置信度: 0.5

# 答案2 (更深入)
来源: 实验验证
内容: 实际可以处理更长，但受限于内存和O(n²)复杂度
置信度: 0.7

# 答案3 (完整理解)
来源: 2006_04768 (Linformer)
内容: 标准Transformer受限于O(n²)，但线性attention可以处理更长序列
置信度: 0.9
```

### 3. 导出为学习笔记

```bash
# 导出某篇论文的所有问题和答案
python scripts/questions_cli.py --export \
  --paper 1810_04805 \
  --output bert_qa.md

# 生成的Markdown可以作为学习笔记：
# - 未解决的问题 → 后续学习重点
# - 已解决的问题 → 知识点总结
```

---

## 📝 总结

### 核心价值

1. **系统化问题管理** - 不再遗漏重要疑问
2. **追踪解决过程** - 看到自己的学习轨迹
3. **跨论文连接** - 在多篇论文中寻找答案
4. **知识沉淀** - 问题+答案形成知识库

### 与洞察系统的配合

```
洞察系统:  广度 - 记录所有观察
疑问系统:  深度 - 追踪问题解决

组合使用:  既有广度又有深度的研究工作流
```

### 适用场景

- ✅ 深度阅读重要论文
- ✅ 需要完全理解方法细节
- ✅ 准备复现论文
- ✅ 写论文需要引用支持
- ✅ 做研究遇到相关问题

---

**记住**：好的问题是深入理解的开始！不要害怕提问，每个问题都是学习的机会。🎓
