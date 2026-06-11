# Skill Refactor

对 Claude Code 用户自定义 skills 进行重构整理——识别功能重叠、提取共享模式、合并相似 skill、拆分过于复杂的 skill，使每个 skill 职责单一、触发精准、结构清晰。

## 核心思想

Skill 重构的思维模型与代码重构完全一致：

| 代码重构 | Skill 重构 |
|----------|-----------|
| 重复代码 | 多个 skill 描述相同触发条件/执行相同步骤 |
| God Class | 一个 skill 做 3+ 件不相关的事 |
| 提取方法 | 重复子流程提取到 `scripts/` 或 `references/` |
| 重命名 | 修正模糊的 name/description |
| 删除死代码 | 移除不再使用的 skill |
| 单一职责 | 每个 skill 只做一件事 |

## 目录结构

```
skill-refactor/
├── SKILL.md                          # 主 skill 定义（完整方法论）
├── README.md                         # 本文件
├── scripts/
│   └── analyze_skills.py             # 自动分析脚本
└── references/
    └── refactoring_patterns.md       # 7 种重构模式目录
```

## 快速开始

### 安装

将仓库克隆到 Claude Code 的 skills 目录：

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/L-ingqin12/skill-refactor.git ~/.claude/skills/skill-refactor
```

然后注册为命令：

```bash
cp ~/.claude/skills/skill-refactor/SKILL.md ~/.claude/commands/skill-refactor.md
```

### 使用

```bash
# 扫描分析所有 skill，输出分析报告
/skill-refactor --dry-run

# 只分析不修改
/skill-refactor

# 针对特定 skill 分析
/skill-refactor --target my-skill
```

## 重构流程

```
Phase 1: Discover  →  扫描所有 skill 文件来源
Phase 2: Parse     →  提取 description/触发词/功能步骤/复杂度
Phase 3: Cluster   →  两两计算 overlap（触发35% + 工具25% + 步骤40%）
Phase 4: Plan      →  按优先级生成重构方案
Phase 5: Execute   →  逐项执行（先备份，再变换，后验证）
Phase 6: Verify    →  跑分析脚本对比 before/after
```

## 内置分析脚本

```bash
python3 scripts/analyze_skills.py ~/.claude/commands ~/.claude/skills
```

输出 JSON 格式的结构化分析报告，包括：
- 每个 skill 的触发关键词、功能步骤、复杂度、工具使用
- 两两对比的重叠率矩阵
- 分类建议（MERGE / EXTRACT / CHAIN / KEEP）

## 重构模式

详见 `references/refactoring_patterns.md`：
1. Pipeline Merge — 流水线合并
2. Parameterized Variant — 参数化变体
3. Subroutine Extraction — 共享子程序提取
4. Layered Split — 分层拆分
5. Namespace Cleanup — 命名空间整理
6. Dead Skill Removal — 死 skill 移除
7. Trigger Precision Tuning — 触发精度调优

## License

MIT
