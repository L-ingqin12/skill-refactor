---
name: skill-refactor
description: Diagnose and fix routing conflicts between user-created skills. Use ONLY when the user explicitly asks to refactor, reorganize, merge, or audit their skills (e.g. "refactor my skills", "整理 skills", "merge duplicate skills", "why did the agent pick the wrong skill"). Do NOT self-trigger — if the user is not directly requesting skill reorganization, do not use this skill.
---

# Skill Refactor

**三重目标**:

| 目标 | 含义 | 衡量标准 |
|------|------|---------|
| 🎯 **精准路由** | 相似 skill 之间建立互斥的决策边界，agent 一次命中正确 skill | 歧义评分 < 20%，正样本触发率 ≥ 90% |
| 📐 **精简完备** | 每个 skill 职责单一、零 filler、结构最小、覆盖完整。每个字都必须有用——删掉不影响执行的立即删除 | 无 God Skill，无重复指令，无死代码，无常识解释，无鼓励语 |
| 🔒 **功能保持** | 重构前后功能完全一致，所有原场景 100% 覆盖，零行为偏差 | 原 skill 的所有 functional_steps 在新结构中可追溯 |

**三者关系**: 精准路由和精简完备是优化目标，功能保持是**硬约束**——任何重构操作不能以丢失功能为代价。如果无法在保持功能的前提下消除歧义，宁可保留冗余。

## 问题模型

```
用户请求: "review 一下我的代码改动"
                │
                ▼
    ┌───────────────────────┐
    │   Agent 看到 3 个     │
    │   相似的 skill:        │
    │                       │
    │   code-review         │ ← 检查 bugs + compliance
    │   security-review     │ ← 只做安全检查
    │   pr-review-toolkit   │ ← 多个 agent 并行 review
    │                       │
    │   触发词都含 "review" │
    │   结构都是审查代码     │
    │   → 选哪个？          │
    └───────────────────────┘
                │
         ┌──────┴──────┐
         ▼              ▼
    选对了 ✅        选错了 ❌
                    agent 走上错误路径
                    浪费 token + 时间
                    用户得到错误结果
```

**根本原因**: 多个 skill 的 `description` 存在歧义交集——agent 无法从 description 区分它们。

**解决方案**: 为每个 skill 建立**决策边界** (Decision Boundary)——不仅是「我做什么」，更重要的是「我和相邻 skill 的区别是什么」。

## 核心概念：决策边界 (Decision Boundary)

```
Skill A                Skill B
  │                      │
  │   ┌──────────────┐   │
  │   │  歧义区域     │   │   ← 需要消除
  │   │  (两个 skill  │   │
  │   │   都能触发)    │   │
  │   └──────────────┘   │
  │                      │
  ◄────── 边界线 ────────►
  
边界线 = 明确的区分条件，agent 可以据此决策
```

**好的决策边界**:
- 互斥条件：skill A 用于场景 X，skill B 用于场景 Y，X 和 Y 不重叠
- 信号明确：agent 只需看用户请求中的 1-2 个特征词即可判定
- 边界清晰：不存在「两个都行」的灰色地带

**坏的决策边界**:
- 两个 skill 的 description 都用「review code」作为触发词
- 依赖 agent 读取 skill body 才能区分（太晚了，已经触发）
- 用模糊的程度副词区分（「深度 review」 vs 「浅度 review」）

## ⚠️ 自排除规则

- **不得重构自身**: 如果 analyzer 报告 `skill-refactor` 自身存在歧义，跳过它。本 skill 的双重注册（command + SKILL.md）是设计如此——command.md 是快速入口，SKILL.md 是完整方法论文档。
- **不得递归触发**: 如果用户没有明确要求整理/重构/审计 skill，不要因为看到多个相似 skill 而主动触发本 skill。

## 重构流程

### Phase 1: 发现 — Discover

扫描所有 skill 来源：

```
用户 Skills 来源:
├── ~/.claude/commands/*.md           # 用户自定义 commands
├── ~/.claude/skills/*/SKILL.md       # 用户创建的 skills
├── 项目级 .claude/commands/*.md       # 项目 commands
├── 项目级 .claude/skills/*/SKILL.md   # 项目 skills
└── ~/.claude/plugins/cache/*/        # 已安装插件 commands
```

### Phase 2: 解析 & 诊断 — Parse & Diagnose

运行自动分析：

```bash
python3 scripts/analyze_skills.py
```

诊断分为两个维度：

#### 2.1 歧义评分 (Ambiguity Score)
对每对 skill，计算「agent 选错的概率」：

| 维度 | 权重 | 含义 |
|------|------|------|
| Trigger Word Overlap | 40% | description 中的关键词重叠率 |
| Domain Overlap | 30% | 是否属于同一领域（都用 git、都做 review、都处理文件） |
| Structural Similarity | 30% | 指令结构、工具链、输出格式的相似度 |

**Ambiguity Score > 50% → 高歧义风险，agent 可能选错。**

#### 2.2 诊断分类

根据分析结果，将每对 skill 的关系标记为：

```
Ambiguity ≥ 70%:  🔴 CONFLICT  — 两个 skill 几乎无法区分，必须合并或用条件拆分
Ambiguity 40-70%: 🟡 AMBIGUOUS — 有重叠但可建立边界，需重写 description 添加互斥条件
Ambiguity 20-40%: 🟢 NEAR      — 相邻但不冲突，需添加区分提示
Ambiguity < 20%:  ✅ DISTINCT  — 互不干扰
```

#### ⏸️ DEFAULT STOP POINT

**Present the diagnosis to the user and STOP.** Summarize:
- X CONFLICT pairs (must fix)
- Y AMBIGUOUS pairs (should fix)
- Z complex skills flagged

Ask: "Proceed with refactoring, or is this enough?" Only continue to Phase 3 if the user explicitly asks.

### Phase 3: 建立决策边界 — Establish Boundaries

这是核心步骤。对每个 🔴 CONFLICT 和 🟡 AMBIGUOUS 对，建立明确的边界：

#### 方法 1: 互斥条件拆分

```
Before (歧义):
  skill-A: description: "Code review for pull requests"
  skill-B: description: "Security review for code changes"
  → agent 看到 "review the PR" 时两个都可能触发

After (互斥):
  skill-A: description: >
    General code review for bugs and CLAUDE.md compliance.
    Use for: "review this PR", "code review", "check my changes".
    Do NOT use for: security-only assessments — use security-review for that.
  skill-B: description: >
    Security-focused review: injection risks, auth bypass, data leaks.
    Use for: "security review", "check for vulnerabilities", "is this safe".
    Do NOT use for: general bug review or CLAUDE.md checks — use code-review for that.
  → agent 看到 "check for SQL injection" 明确触发 security-review
  → agent 看到 "review my PR for bugs" 明确触发 code-review
```

**关键技巧**: description 中加入 **NOT 子句**——明确告诉 agent 什么情况下不要触发自己。

#### 方法 2: 粒度分层

```
Before (歧义):
  skill-A: "Run tests"
  skill-B: "Run full CI pipeline"

After (分层):
  skill-A: "Run unit tests quickly (single command, <30s)"
  skill-B: "Run full CI pipeline (build + test + lint + deploy check, ~10min)"
  → agent 根据用户对速度/范围的期望选择
```

#### 方法 3: 场景锚定

```
Before (歧义):
  skill-A: "Create a git commit"
  skill-B: "Commit and create PR"

After (场景锚定):
  skill-A: "Create a git commit during active development. Use when you're mid-work and want to checkpoint."
  skill-B: "Complete workflow: commit + push + open PR. Use when work is done and ready for review."
  → agent 根据用户所处阶段选择
```

#### 方法 4: 合并消除

如果两个 skill 的决策边界无法建立（本质上做的是同一件事），合并为最精确的一个：

```
Before: 三个 commit 相关 skill
  commit-commands:commit
  commit-commands:commit-push-pr
  commit-commands:clean_gone

问题: commit 和 commit-push-pr 的边界模糊

After:
  commit-commands:commit          # 统一入口，自动检测阶段
                                   # 只有暂存区有改动 → commit
                                   # commit 已在 feature branch → commit + push + PR
  commit-commands:clean_gone      # 保持独立（操作完全不同）
```

### Phase 4: 路由验证 — Route Test

建立边界后，**必须**用一组测试 query 验证 agent 的正确路由率：

```
测试集（至少 10 条 query）:
├── 正样本: 应该触发 skill A 的 query（5 条）
├── 正样本: 应该触发 skill B 的 query（5 条）
├── 边界样本: 同时含 A 和 B 关键词的 query（3 条）
└── 负样本: 不应触发任何 skill 的 query（2 条）

通过标准:
  ✅ 正样本正确触发率 ≥ 90%
  ✅ 边界样本: 如果 query 真的模糊，agent 应询问用户而非随意选择
  ✅ 负样本: 不触发
```

**验证方式**: 对每条 query，人工判断「agent 看到这些 description 时，会选哪个 skill？」。不需要真正运行，只需基于 description 做路由判断。

### Phase 5: 执行 — Execute

用户确认边界方案后，修改 skill 文件。**每个操作必须遵循功能保持约束**。

#### 功能保持约束 (Hard Constraint)

在执行任何重构操作前，必须先提取「功能指纹」：

```
功能指纹 = 原 skill 的完整功能清单:
├── 每个 functional_step 及其输入/输出
├── 每个工具调用的目的和参数范围
├── 每个边界情况的处理方式
└── 与其他 skill 的交互点（被调用、调用别人）
```

**合并操作的功能保持检查**:
```
Before: skill-a (3 steps) + skill-b (4 steps)
After:  skill-merged

检查项:
□ skill-a 的每个 step 在 skill-merged 中可找到对应 → 逐条 trace
□ skill-b 的每个 step 在 skill-merged 中可找到对应 → 逐条 trace
□ skill-a 的每个触发场景在 skill-merged 的 description 中有覆盖
□ skill-b 的每个触发场景在 skill-merged 的 description 中有覆盖
□ 共同的步骤只出现一次（不重复）
□ 差异步骤用条件清晰区分（不模糊）
```

**拆分操作的功能保持检查**:
```
Before: skill-god (8 steps)
After:  skill-x (3 steps) + skill-y (3 steps) + skill-z (2 steps)

检查项:
□ 原 8 steps 全部分配到新 skill 中（无遗漏）
□ 每个新 skill 的 description 覆盖了分配给它的场景
□ 如果原 skill 中有步骤顺序依赖，新 skill 间有交叉引用
□ 用户可以独立调用每个新 skill（不需要知道内部拆分细节）
```

**提取操作的功能保持检查**:
```
Before: skill-a (inline 重复步骤 S)
After:  skill-a (引用 scripts/shared_s.py)

检查项:
□ 脚本的行为与原内联步骤完全一致（参数、输出、错误处理）
□ Skill body 中的引用方式清晰且包含回退说明
```

#### 执行步骤

1. **提取功能指纹** → 记录到 `.claude/skills/skill-refactor/fingerprints/<skill-name>.json`
2. **备份原文件** → `.claude/backups/<skill-name>.<timestamp>.md`
3. **执行变换** → 重写 description + body
4. **功能 trace** → 对着指纹逐条验证，确认无遗漏
5. **更新其他 skill 的交叉引用** → 如果 skill 名字变了，更新所有引用它的 skill

### Phase 6: 验证 — Verify (三层检查)

重构完成后，执行三层验证：

#### Layer 1: 功能等价性 (Must Pass)
对着 Phase 5 提取的功能指纹，逐条 trace：
```
原件: skill-a, step 2: "运行 git diff 检查改动"
新件: skill-merged, step 3: "运行 git diff --staged 检查暂存区改动"
→ ⚠️ 差异: 原检查所有改动，新只检查暂存区 → 功能偏差！需修正。
```

**通过标准**: 100% trace 通过，0 偏差。

#### Layer 2: 路由精准性 (Should Pass)
用 10+ 条测试 query 验证：
- 每条 query 应触发且仅触发正确的 skill
- 不应出现「两个 skill 都合适」的灰色地带
- 边界 query 应触发 agent 询问用户而非随意选择

**通过标准**: 正样本命中率 ≥ 90%，无误触发。

#### Layer 3: 精简完备性 (Nice to Pass)
- 每个 skill body ≤ 500 行
- 无重复段落（跨 skill 比较）
- 每个 skill 职责单一（可用一句话描述它做什么）

#### 验证失败回滚
如果 Layer 1 验证失败 → 回滚到备份，调整方案后重试。
如果 Layer 2 验证失败 → 调整 description，重新做路由测试。
如果 Layer 3 验证失败 → 提取/拆分，但必须重新过 Layer 1。

### Phase 7: 输出路由地图 — Routing Map

重构完成后，生成一份**路由地图**供用户确认：

```markdown
# Skill Routing Map

## 当用户说 "review" 时:
| 用户实际意图 | 正确 Skill | 识别信号 |
|-------------|-----------|---------|
| 检查 bugs + 规范 | code-review | "review PR", "check bugs", "code review" |
| 只做安全检查 | security-review | "security", "vulnerability", "safe", "injection" |
| 全面多维度审查 | pr-review-toolkit | "comprehensive", "full review", "all aspects" |

## 当用户说 "commit" 时:
| 用户实际意图 | 正确 Skill | 识别信号 |
|-------------|-----------|---------|
| 开发中存档 | commit | 只有暂存改动，没说 PR |
| 完成工作提交 | commit-push-pr | "create PR", "push", "open a PR" |
| 清理本地分支 | clean_gone | "clean", "stale", "gone", "cleanup" |
```

#### ⏸️ STOP POINT

Present the routing map to the user. Phase 8 (lean check) is optional — only run it if the user asks for a deeper cleanup or if the analysis flagged skills > 300 lines.

---

### Phase 8: 精简完备检查 — Lean & Complete (OPTIONAL)

精准路由解决且功能等价验证通过后，对每个 skill 做精简完备审查：

#### 8.1 冗余检测
```
检查项:
├── 两个 skill 有相同的 instruction 段落（>3 行相同）？ → 提取到 scripts/ 或 references/
├── Skill body 中重复了 description 的内容？ → 删除 body 中的重复
├── 多个 skill 定义了相同的输出模板？ → 提取到 references/templates/
└── Skill body 超过 500 行？ → 拆分或把细节移到 references/
```

#### 8.2 完备性检测
```
检查项:
├── 用户场景覆盖率: 这个 skill 覆盖了该领域的所有常见用户需求吗？
├── 错误处理: 前置条件不满足时，skill 是否给出明确指引而非静默失败？
├── 边界情况: 空输入、异常输入、权限不足等情况有处理说明吗？
└── 交叉引用: 与其他 skill 的关系是否在 body 中明确（"如果需要 X，应该用 skill Y"）？
```

#### 8.3 复杂度阈值
```
复杂度      Step 数    处理方式
simple      1-2        ✅ 保留，检查 description 是否足够精确
moderate    3-5        ✅ 保留
complex     6-8        ⚠️ 检查是否可以拆分
complex     9+         🔴 必须拆分（除非是编排型 skill 如 code-review）
```

#### 8.4 无意义内容清除 (Ruthless Cut)

这是最容易被忽略但最关键的一步。Skill 的每一个字都在消耗 agent 的上下文窗口——无意义内容不仅浪费 token，还会稀释关键指令的注意力。

**必须删除的内容**:

```
🔴 必须删除:
├── 显而易见的常识说明（如 "git 是一个版本控制工具"、"代码审查很重要"）
├── 重复 description 的内容（description 已在 metadata 中，body 不要再解释一遍）
├── 空洞的鼓励语（"Good luck!"、"Make sure to do your best!"、"Remember to be careful!"）
├── 过度详细的示例（1 个典型示例足够，不需要 3 个变体说明同一件事）
├── "你可以这样做，也可以那样做" 的模糊指引 → 给一条最优路径
├── 大段背景介绍 → 移到 references/，按需加载
└── 和触发条件无关的通用建议（如 "写代码时注意性能"）
```

**必须精简的内容**:
```
🟡 必须精简:
├── 超过 4 行的代码块（agent 不需要看完整的实现，只需要知道调用方式）
├── 重复出现的相同指令块 → 提取为一句引用
├── "Step 1: ... Step 2: ... Step 3: ..." 后跟重复的 summary → 删掉 summary
└── 多种备选方案 → 只保留最佳方案，其他删掉
```

**判断标准 — "删掉它，agent 还能正确执行吗？"**:
```
如果能 → 删掉
如果不能 → 保留，但检查是否可以写得更短
```

#### 8.5 死代码检测
```
标记为 DEPRECATED 的信号:
├── 引用的脚本/工具已不存在
├── 已在路由地图中被其他 skill 完全覆盖
├── description 中包含 "deprecated"、"不再使用"、"replaced by"
└── 用户反馈 "这个 skill 没用过"
```

## 关键原则

### 🎯 精准路由三原则

**1. 决策边界优先**
重构的第一目标不是「减少 skill 数量」，而是「让每个 skill 的触发条件互斥」。如果两个 skill 能建立清晰的决策边界，它们可以（也应该）独立存在。

**2. Description 承载路由信息**
- description 必须告诉 agent：**什么时候用我 + 什么时候不要用我**
- 宁可用 NOT 子句多写 10 个字，不要让 agent 猜
- 不要写「Help with X」——写「Use when user asks for X with Y context. Do NOT use for Z.」

**3. 相似的 body 可以共存，相似的 description 不行**
两个 skill 的内部步骤相似是可以的（比如都用 git 命令），但它们的 description 必须互斥。Agent 只看 description 做路由决策。

### 📐 精简完备三原则

**4. 单一职责**
每个 skill 应该只做一件事。"做 git 提交 + 做 PR + 清理分支"应该是一个 skill 吗？可能不是——它们服务于不同的用户意图。

**判断标准**: 如果用户在不同时间点、出于不同目的调用这些功能，它们应该是独立的 skill。

**5. 零 filler（最小完备）**
Skill 里每个字都在消耗 agent 上下文。无意义内容不止浪费 token——它稀释关键指令的注意力密度。

- **只写 agent 不知道的**: 不解释常识（agent 知道 git 是什么），不写鼓励语，不写重复内容
- **一条最优路径**: 不给多种备选方案让 agent 选，直接给最优路径
- **测试标准**: "删掉这句话，agent 还能正确执行吗？" → 能就删
- SKILL.md body 上限: ≤500 行（接近时拆分到 references/）
- 确定性操作 → `scripts/`（不占 body）
- 知识/模板 → `references/`（按需加载，不在触发时占用上下文）

**6. 场景完备**
Lean ≠ incomplete。每个 skill 必须覆盖其领域内的所有常见场景：
- 正常路径（happy path）✅
- 前置条件不满足时的处理 ✅
- 与其他 skill 的切换指引 ✅

### 综合原则

**7. 从「我能做什么」到「用户什么情况下需要我」**
Bad description 描述的是 skill 自身的能力。Good description 描述的是用户的场景和意图。

```
❌ Bad:  "This skill creates git commits with auto-generated messages."
✅ Good: "Create a git commit when the user has staged changes and wants to checkpoint.
          Do NOT use for pushing or creating PRs — use commit-push-pr for that."
```

**8. 精准与精简互相成就**
- 精准路由迫使 skill 职责清晰 → 自然精简
- 精简的 skill 容易写出互斥的 description → 自然精准
- 如果发现某个 skill 的 description 很难写得互斥 → 说明它职责不单一，该拆分了

## 常见重构模式

详见 `references/refactoring_patterns.md`，重点模式：

- **互斥条件拆分** — 同一领域、不同 focus → NOT 子句
- **粒度分层** — 同一操作、不同范围 → 时间/步骤数区分
- **场景锚定** — 同一工具、不同阶段 → 用户意图区分
- **合并消除** — 无法建立边界 → 合并为最精准版本

## 使用方法

```
/skill-refactor                    # 扫描分析，输出歧义诊断 + 路由地图
/skill-refactor --dry-run          # 只分析，不修改任何文件
/skill-refactor --target <name>    # 只分析与指定 skill 相关的歧义
```

首次使用建议先 `--dry-run`，确认诊断和路由地图后再执行。

---

## Reference files

The agents/ directory contains instructions for specialized subagents. Read them when spawning the relevant subagent:

- `agents/analyzer.md` — How to analyze ambiguity results and produce actionable findings
- `agents/grader.md` — How to grade whether skill descriptions produce correct routing decisions

The references/ directory has additional documentation:

- `references/refactoring_patterns.md` — 7 refactoring patterns with before/after examples
- `references/schemas.md` — JSON structures for analysis output, functionality fingerprints, routing maps, and grader results
