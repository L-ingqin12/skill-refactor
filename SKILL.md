---
name: skill-refactor
description: Refactor and reorganize user-created skills. Use when the user has multiple skills that may overlap, wants to consolidate similar skills, clean up skill descriptions, extract shared patterns, or optimize skill triggering accuracy. Triggers on phrases like "refactor skills", "reorganize skills", "merge skills", "clean up skills", "skill 重构", "整理 skills".
---

# Skill Refactor

对用户已有的 skills/commands 进行重构整理——识别功能重叠、提取共享模式、合并相似 skill、拆分过于复杂的 skill，使每个 skill 职责单一、触发精准、结构清晰。

## 核心思想

Skill 重构的思维模型与代码重构完全一致：

| 代码重构 | Skill 重构 |
|----------|-----------|
| 重复代码 | 多个 skill 描述相同的触发条件，或执行相同步骤 |
| God Class | 一个 skill 做 3+ 件不相关的事 |
| 提取方法 | 将重复子流程提取到 `scripts/` 或 `references/` |
| 重命名 | 修正模糊的 name/description |
| 删除死代码 | 移除不再使用的 skill |
| 单一职责 | 每个 skill 只做一件事，做好一件事 |
| 接口隔离 | 精确的 description 让 agent 在正确的时机触发 |

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

**执行方式**:
```bash
find ~/.claude/commands ~/.claude/skills -name "*.md" 2>/dev/null
find .claude/commands .claude/skills -name "*.md" 2>/dev/null
```

对每个 skill 文件，读取完整内容并提取结构化信息。

### Phase 2: 解析 — Parse

对每个 skill 提取以下维度的结构化信息。写入分析临时文件以避免重复读取：

```
分析维度 per skill:
├── name:           skill 标识符
├── description:    触发条件描述（最关键字段）
├── allowed-tools:  需要的工具权限
├── trigger_keywords: 从 description 中提取的关键触发词
├── functional_steps: 实际执行的步骤列表（用 2-3 句话概括）
├── inputs:         需要什么输入（文件、参数、git 状态等）
├── outputs:        产出什么（文件修改、PR、报告等）
├── dependencies:   依赖的 MCP、脚本、外部工具
├── complexity:     simple(单步) | moderate(2-4步) | complex(5+步或多 agent)
└── file_path:      文件位置
```

**分析脚本**: 运行 `python scripts/analyze_skills.py <skill目录列表>` 自动提取以上信息，输出 JSON。

### Phase 3: 聚类 — Cluster

按以下维度对 skills 进行两两比较，计算重叠度：

#### 3.1 触发重叠 (Trigger Overlap)
比较两个 skill 的 `description` 字段。以下情况视为高度重叠：
- 关键词交集 > 60%（如 "commit" + "git" + "push"）
- 用户说出同一句话时，两个 skill 都可能被触发
- 一个 description 的场景描述包含另一个

#### 3.2 功能重叠 (Functional Overlap)
比较 `functional_steps`：
- 执行相同或高度相似的操作序列（如都做 commit→push→PR）
- 使用相同的工具组合
- 产出的输出类型相同

#### 3.3 互补关系 (Complementary)
- Skill A 的输出是 Skill B 的输入
- 两个 skill 在同一工作流的不同阶段被调用
- 用户经常连续调用它们

#### 3.4 分类判断

对每对 skill，归入以下类别之一：

```
重叠度 ≥ 70% → MERGE（合并为一个）
重叠度 40-70% → EXTRACT（提取共享部分到 scripts/references）
互补关系明确 → CHAIN（添加交叉引用，保留为独立 skill）
重叠度 < 40% → KEEP（各自独立）
复杂度 complex 且有多类功能 → SPLIT（按功能拆分为多个 skill）
trigger_keywords 与行为不符 → RENAME（修正 name/description）
```

### Phase 4: 规划 — Plan

生成重构计划，按优先级排序：

```markdown
# Skill Refactoring Plan

## 🔴 Critical — Merge (消除重复)
1. **`skill-a` + `skill-b` → `new-skill`**
   - 原因: 触发条件重叠 85%，功能步骤重叠 80%
   - 方案: 合并为一个 skill，用参数区分变体

## 🟡 Important — Extract/Split
2. **从 `skill-c`, `skill-d`, `skill-e` 提取共享脚本**
   - 原因: 三个 skill 都执行"生成 commit message"这个子步骤
   - 方案: 提取到 `scripts/generate_commit_msg.py`

## 🟢 Nice-to-have — Rename/Chain
3. **`skill-f` 改名**
   - 原因: description 写的是"审查代码"但实际只做安全检查
   - 方案: 修正为 security-review，精确描述触发条件
```

在继续之前，**必须将重构计划呈现给用户确认**。这是破坏性操作——合并后原 skill 会被修改或删除。

### Phase 5: 执行 — Execute

用户确认后，逐个执行重构操作：

#### MERGE 操作
```
输入: skill_a.md, skill_b.md（两个待合并的 skill）
输出: skill_merged.md（合并后的 skill）

步骤:
1. 分析两个 skill 的共同点和差异点
2. 共同部分 → 作为主干
3. 差异部分 → 用清晰的参数或条件分支区分
4. 重写 description，覆盖两个原 skill 的所有触发场景
5. 如果合适，提取共享子流程到 scripts/
6. 备份原文件 → 写新文件 → 删除原文件（或标记 deprecated）
```

#### EXTRACT 操作
```
输入: 多个有共享子步骤的 skill
输出: scripts/shared_xxx.py 或 references/shared_xxx.md

步骤:
1. 精确定位重复的步骤/指令段落
2. 评估：适合脚本化（确定性逻辑）还是适合 reference（知识/指导）
3. 写出共享资源
4. 修改各 skill，改为引用共享资源而非内联重复内容
```

#### SPLIT 操作
```
输入: 一个过于复杂的 skill
输出: 2-3 个单一职责的 skill

步骤:
1. 识别 skill 中的独立功能边界
2. 为每个独立功能写新的 skill 文件
3. 每个新 skill 有精确的 description
4. 如果它们之间有顺序依赖，添加交叉引用
```

#### RENAME 操作
```
输入: 一个 description 不准确的 skill
输出: 修正后的 skill

步骤:
1. 读取 skill 实际指令内容
2. 提取真正的功能和触发条件
3. 重写 description，遵循"pushy"原则（稍微主动触发）
4. 更新 name（如有必要）
```

### Phase 6: 验证 — Verify

重构完成后，对每个修改过的 skill 做快速检查：

1. **触发测试**: 用 2-3 个典型用户 query 在脑中模拟——这个 skill 会被正确触发吗？会被错误触发吗？
2. **功能完整性**: 原 skill 的所有功能场景在新结构中是否都有覆盖？
3. **无遗漏**: 检查是否有任何原 skill 的功能在新结构中被遗漏

将验证结果呈现给用户。

## 关键原则

### 单一职责
每个 skill 应该只做一件事。"做 git 提交 + 做 PR + 清理分支"应该是一个 skill 吗？可能不是——它们服务于不同的用户意图。

**判断标准**: 如果用户在不同时间点、出于不同目的调用这些功能，它们应该是独立的 skill。如果它们总是一起使用（如 commit→push→PR），可以合并但用清晰的步骤指引。

### Description 是 Skill 的接口
description 是 agent 决定是否触发 skill 的唯一依据。重构时：
- description 必须精确描述"用户什么情况下需要这个 skill"
- 宁可稍微 pushy（过度触发由 agent 自行判断），不可太保守（skill 从不被触发）
- 命名空间前缀（如 `commit-commands:commit`）应与功能一致

### 保持 lean
- SKILL.md 正文 < 500 行
- 超过 300 行的 reference 文件需要目录
- 确定性操作 → 写成脚本放 `scripts/`
- 知识/指导 → 写成 reference 放 `references/`

### 渐进式加载
遵循 skill 系统的三级加载：
1. **Metadata** (name + description) — 总是在 agent 上下文中
2. **SKILL.md body** — skill 触发时加载
3. **Bundled resources** — 按需加载

重构时要确保 description 承载了足够的触发信息，body 不重复 description 内容。

## 常见重构模式

详见 `references/refactoring_patterns.md`，包括：
- 流水线合并 (Pipeline Merge)
- 参数化变体 (Parameterized Variant)
- 共享子程序提取 (Subroutine Extraction)
- 分层拆分 (Layered Split)
- 命名空间整理 (Namespace Cleanup)

## 使用方法

```
/skill-refactor                    # 扫描并分析所有 skill，输出分析报告和建议
/skill-refactor --auto             # 自动执行低风险重构（rename, extract scripts）
/skill-refactor --dry-run          # 只分析，不修改任何文件
/skill-refactor --target <name>    # 只分析指定 skill 及其相关 skill
```

首次使用建议先 `--dry-run`，确认计划后再执行。
