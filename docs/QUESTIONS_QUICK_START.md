# 疑问系统快速入门

## 🚀 5分钟快速开始

### 最简工作流

```bash
# 1️⃣ 下载论文
python main.py --arxiv 1810.04805

# 2️⃣ 开始问题记录
python scripts/questions_cli.py --start-session --paper 1810_04805

# 3️⃣ 记录疑问（边读边记）
python scripts/questions_cli.py --question
# 输入: "为什么BERT使用15%的mask比例？"
# 类型: method
# 重要性: 4

# 4️⃣ 继续记录更多疑问...
python scripts/questions_cli.py --question

# 5️⃣ 结束会话
python scripts/questions_cli.py --end-session

# 6️⃣ 查看未解决的问题
python scripts/questions_cli.py --list --status unsolved

# 7️⃣ 找到答案后添加
python scripts/questions_cli.py --add-answer --question q_0001
# 输入答案内容和来源
```

---

## 💡 核心概念（30秒理解）

```
阅读论文 → ❓记录疑问 → 💡找到答案 → ✅解决问题
```

**疑问系统 vs 洞察系统**：
- **洞察系统**：记录所有观察（observation, insight, question...）
- **疑问系统**：专注问题追踪，记录答案和解决状态

---

## 📝 8种问题类型

### 1. understanding（理解）
```
"什么是Masked Language Model？"
"Self-attention如何工作？"
```

### 2. method（方法）
```
"为什么这样设计？"
"能否用其他方法？"
```

### 3. experiment（实验）
```
"为什么只在WMT上测试？"
"缺少哪些实验？"
```

### 4. application（应用）
```
"能应用到中文吗？"
"如何用于推荐系统？"
```

### 5. limitation（局限）
```
"长序列会有问题吗？"
"不适用于哪些场景？"
```

### 6. extension（扩展）
```
"如何改进？"
"未来方向是什么？"
```

### 7. comparison（比较）
```
"和LSTM有什么区别？"
"为什么比baseline好？"
```

### 8. implementation（实现）
```
"如何实现multi-head？"
"训练时如何处理padding？"
```

---

## 🎯 常用命令速查

### 会话管理
```bash
# 开始会话
python scripts/questions_cli.py --start-session --paper <paper_id>

# 结束会话
python scripts/questions_cli.py --end-session
```

### 记录问题
```bash
# 交互式记录（推荐）
python scripts/questions_cli.py --question

# 快速一行命令
python scripts/questions_cli.py --question \
  --paper <paper_id> \
  --content "问题内容" \
  --type understanding \
  --importance 3
```

### 添加答案
```bash
# 交互式添加
python scripts/questions_cli.py --add-answer --question q_0001

# 快速命令
python scripts/questions_cli.py --add-answer \
  --question q_0001 \
  --content "答案内容" \
  --source <paper_id>
```

### 查看问题
```bash
# 查看所有
python scripts/questions_cli.py --list

# 未解决的
python scripts/questions_cli.py --list --status unsolved

# 特定论文
python scripts/questions_cli.py --list --paper 1810_04805

# 高优先级
python scripts/questions_cli.py --list --min-importance 4

# 问题详情
python scripts/questions_cli.py --show --question q_0001
```

### 统计
```bash
# 查看统计
python scripts/questions_cli.py --stats
```

---

## 💪 实战练习

### 练习 1：第一次使用

```bash
# Step 1: 下载BERT论文
python main.py --arxiv 1810.04805

# Step 2: 开始问题记录
python scripts/questions_cli.py --start-session --paper 1810_04805

# Step 3: 记录你的第一个疑问
python scripts/questions_cli.py --question
# 试着输入你读BERT时的任何疑问

# Step 4: 再记录2-3个疑问

# Step 5: 结束会话
python scripts/questions_cli.py --end-session

# Step 6: 查看你记录的所有疑问
python scripts/questions_cli.py --list --paper 1810_04805
```

### 练习 2：跨论文寻找答案

```bash
# 阅读BERT，产生疑问
python scripts/questions_cli.py --start-session --paper 1810_04805
python scripts/questions_cli.py --question
# > "GPT为什么是单向的？"
python scripts/questions_cli.py --end-session

# 阅读GPT论文，找到答案
python main.py --arxiv 1910.10683
# (阅读后...)

# 添加答案
python scripts/questions_cli.py --add-answer --question q_0001
# > 答案: GPT使用decoder，采用causal masking
# > 来源: 1910_10683
```

---

## ⚡ 效率技巧

### 技巧 1：快速记录
```bash
# 阅读时遇到疑问，一行命令快速记录
python scripts/questions_cli.py --question \
  --paper 1810_04805 \
  --content "为什么mask 15%？" \
  --type method \
  --importance 4
```

### 技巧 2：重要性评分
```
5⭐ - 核心问题，必须理解
4⭐ - 重要问题，影响理解
3⭐ - 标准问题，值得了解
2⭐ - 次要问题
1⭐ - 琐碎问题
```

### 技巧 3：定期回顾
```bash
# 每周查看未解决的高优先级问题
python scripts/questions_cli.py --list \
  --status unsolved \
  --min-importance 4

# 集中寻找答案
```

### 技巧 4：导出学习笔记
```bash
# 导出某篇论文的Q&A
python scripts/questions_cli.py --export \
  --paper 1810_04805 \
  --output bert_questions.md

# 可以作为学习笔记复习
```

---

## ❓ 常见问题

### Q: 疑问系统和洞察系统有什么区别？

**洞察系统**：
- 记录所有类型的观察
- 包括observation, question, connection等
- 轻量级，快速记录

**疑问系统**：
- 专注于问题的追踪
- 记录答案和解决过程
- 重量级，深度管理

**使用建议**：
- 简单疑问 → 洞察系统的question类型
- 重要疑问需要追踪 → 疑问系统

### Q: 每篇论文要记录多少问题？

**没有固定数量，取决于**：
- 论文的复杂度
- 阅读的深度
- 你的背景知识

**经验值**：
- 快速浏览：2-3个关键疑问
- 正常阅读：5-10个
- 深度研读：15-25个

### Q: 什么时候添加答案？

**建议时机**：
1. 阅读同一篇论文的后续章节时找到答案
2. 阅读其他相关论文时发现答案
3. 通过实验或推理得出答案
4. 查阅资料后获得答案

### Q: 答案的置信度如何设置？

```
0.9-1.0  完全确定，有明确引用支持
0.7-0.8  比较确定，有一定依据
0.5-0.6  不太确定，需要进一步验证
0.3-0.4  猜测性质，缺乏依据
```

### Q: 可以修改已记录的问题吗？

目前CLI不直接支持修改，但可以：
1. 添加新的更准确的答案
2. 通过notes字段补充说明
3. 或直接编辑JSON文件

---

## 🎓 下一步

掌握基础后，可以学习：

1. **高级功能**
   - 查看 [完整系统指南](QUESTIONS_SYSTEM_GUIDE.md)

2. **与其他系统配合**
   - 洞察系统 + 疑问系统
   - 形成完整的研究工作流

3. **问题网络**
   - 关联相关问题
   - 构建知识图谱

---

## 🎉 开始你的第一个疑问记录！

```bash
# 选择一篇你正在读的论文
python main.py --arxiv <paper_id>

# 开始记录疑问
python scripts/questions_cli.py --start-session --paper <paper_id>

# 不要害怕提问，每个问题都是学习的机会！
```

**记住**：好的问题是深入理解的开始！❓→💡→✅
