# Skill 重构模式目录

每种模式包含：问题识别 → 重构方案 → 前后对比 → 适用场景。

---

## 1. Pipeline Merge（流水线合并）

**问题**: 多个 skill 在同一工作流的不同阶段被调用，用户总是连续使用它们。

**信号**:
- Skill A → Skill B → Skill C 是用户的固定调用序列
- 中间产出不独立使用

**方案**: 合并为一个 skill，内部用清晰的 phase 分阶段，每个阶段可选执行。

**Before**:
```
commit-commands:commit      # 仅做 git commit
commit-commands:commit-push-pr  # commit + push + PR（与上面大量重复）
```

**After**:
```
commit-commands:commit      # 智能检测当前阶段，支持:
                            # /commit            → 仅 commit
                            # /commit --push    → commit + push
                            # /commit --pr      → commit + push + PR
```

**注意**: 如果用户经常只做 commit（不做 PR），保留 `commit` 独立，让 `commit-push-pr` 内部调用 `commit` 的逻辑。

---

## 2. Parameterized Variant（参数化变体）

**问题**: 多个 skill 结构高度相似，只在少量步骤上有差异。

**信号**:
- 两个 skill 的 instructions 有 >60% 相同段落
- 差异是"对 A 做 X" vs "对 B 做 X"

**方案**: 合并为一个 skill，通过参数或上下文判断执行哪个变体。

**Before**:
```
deploy-staging:   检查 → 构建 → 推送到 staging → 通知
deploy-production: 检查 → 构建 → 推送到 production → 通知（多了确认步骤）
```

**After**:
```
deploy:
  1. 自动检测目标环境（从分支名 / 用户输入 / 当前目录）
  2. 统一流程: 检查 → 构建 → 推送
  3. 如果 production: 插入确认步骤
  4. 通知对应 channel
```

---

## 3. Subroutine Extraction（共享子程序提取）

**问题**: 多个 skill 包含相同的子步骤，各自内联实现。

**信号**:
- 同样的 Bash 命令块出现在 ≥3 个 skill 中
- 同样的"检查前置条件"逻辑重复出现
- 同样的输出格式模板被重复描述

**方案**: 提取到 `scripts/` （确定性逻辑）或 `references/` （知识/模板）。

**Before**:
```markdown
# skill-a.md
## Check git status
Run: `git status --porcelain` ... (20行说明)
如果 working tree 不干净...
```

```markdown
# skill-b.md
## Check git status
Run: `git status --porcelain` ... (同样20行)
```

**After**:
```markdown
# scripts/preflight_git.py  ← 一个脚本，所有 skill 共用
# skill-a.md
Run preflight check: `python scripts/preflight_git.py --check-clean`
```

**提取决策树**:
```
重复内容
├── 是确定性逻辑（每次产出相同）→ scripts/*.py 或 *.sh
├── 是格式模板                  → references/templates/
├── 是知识/参考                 → references/
└── 是指令模式                  → 保留在 SKILL.md 但引用 references/ 获取细节
```

---

## 4. Layered Split（分层拆分）

**问题**: 一个 skill 做了太多事情（God Skill）。

**信号**:
- functional_steps > 8
- complexity = "complex"
- 步骤之间没有强顺序依赖
- description 用 "and" 连接了多个不同操作

**方案**: 按功能边界拆分为 2-3 个单一职责的 skill。

**Before**:
```
maintenance:
  1. 检查系统状态
  2. 清理缓存
  3. 更新依赖
  4. 运行测试
  5. 生成报告
  6. 发送通知
```

**After**:
```
system-check:    检查系统状态 → 生成报告
cache-clean:     清理缓存（安全模式/激进模式）
dep-update:      更新依赖 + 运行测试验证
```

每个新 skill 有精确的 description，触发更准确。

---

## 5. Namespace Cleanup（命名空间整理）

**问题**: 命名不一致，难以发现和使用。

**信号**:
- 有的 skill 用 `kebab-case`，有的用 `snake_case`
- 有的有命名空间前缀（`git:commit`），有的没有（`deploy`）
- name 和 description 不匹配

**方案**: 统一命名规范，整理命名空间。

**命名规范**:
```
领域:操作              # git:commit, docker:build, k8s:deploy
工具名:操作            # gh:pr-create, npm:publish
动作-对象              # review-code, deploy-staging
```

**命名空间决策树**:
```
skill 关联的是某个工具？       → 工具名:操作
skill 关联的是某个领域？       → 领域:操作
skill 是通用操作？            → 动作-对象
```

---

## 6. Dead Skill Removal（死 skill 移除）

**问题**: skill 存在但不再使用。

**信号**:
- Skill 引用的工具已不存在
- Skill 依赖的 MCP server 已移除
- Skill 的操作已被其他 skill 覆盖
- 用户反馈说"这个 skill 没用"

**方案**: 标记为 deprecated（加 `⚠️ DEPRECATED` 到 description），一个版本后删除。

**Before**:
```markdown
---
description: Deploy to Heroku (⚠️ DEPRECATED - migrated to AWS)
---
```

---

## 7. Trigger Precision Tuning（触发精度调优）

**问题**: skill 被过度触发或从不触发。

**信号**:
- Skill 总是被触发但用户经常 dismiss
- Skill 从不被触发即使相关任务出现
- 类似任务的 skill 竞争触发

**方案**: 精确化 description，遵循"pushy but precise"原则。

**规则**:
- description 必须包含: 功能 (做什么) + 上下文 (什么时候用)
- 包含具体的文件名、工具名、领域术语
- 不要包含过于通用的词（如 "help", "fix", "improve"）
- 如果 skill 很专业，加上排除条件

**Before**:
```
description: Help with code.
```

**After**:
```
description: Review pull requests for bugs, security issues, and CLAUDE.md compliance. Use when the user asks for a code review, wants to check a PR, or says "review this".
```

---

## 重构优先级矩阵

| | 高重叠度 | 低重叠度 |
|---|---|---|
| **高使用频率** | 🔴 MERGE 优先 | 🟡 REFINE description |
| **低使用频率** | 🟡 EXTRACT 共享部分 | 🟢 低优先级 / ARCHIVE |
