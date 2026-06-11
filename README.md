# Skill Refactor

对 Claude Code 用户自定义 skills 进行重构整理——**三重目标**：精准路由 + 精简完备 + 功能保持。

## 核心问题

当多个 skill 共享触发关键词时，agent 无法从 description 区分它们，导致选错 skill、浪费 token 走上错误路径。

```
用户说 "review 代码"
  → Agent 看到: code-review / security-review / pr-review-toolkit
  → 三个都含 "review"，触发了错误的那个
  → ❌ 浪费时间 + 错误结果
```

## 三重目标

| 目标 | 含义 | 标准 |
|------|------|------|
| 🎯 **精准路由** | 相似 skill 建立互斥决策边界 | 歧义评分 < 20% |
| 📐 **精简完备** | 职责单一、结构最小、覆盖完整 | ≤5 step，无冗余 |
| 🔒 **功能保持** | 重构前后功能完全一致 | 100% trace 通过 |

## 目录结构

```
skill-refactor/
├── SKILL.md                          # 完整 8 阶段方法论
├── command.md                        # 斜杠命令入口
├── README.md
├── scripts/
│   └── analyze_skills.py             # 自动歧义分析脚本
└── references/
    └── refactoring_patterns.md       # 7 种重构模式目录
```

## 快速开始

### 安装

```bash
git clone https://github.com/L-ingqin12/skill-refactor.git ~/.claude/skills/skill-refactor
cp ~/.claude/skills/skill-refactor/command.md ~/.claude/commands/skill-refactor.md
```

### 使用

```bash
/skill-refactor --dry-run    # 只分析不修改，输出歧义诊断报告
/skill-refactor              # 完整重构流程
/skill-refactor --target X   # 只分析与指定 skill 相关的歧义
```

## 重构流程 (8 Phases)

```
Phase 1: Discover      扫描所有 skill 文件
Phase 2: Diagnose      运行 analyze_skills.py，计算歧义评分
Phase 3: Boundaries    建立决策边界（NOT 子句 / 粒度分层 / 场景锚定 / 合并）
Phase 4: Route Test    用测试 query 验证路由准确性
Phase 5: Execute       提取功能指纹 → 备份 → 变换 → trace 验证
Phase 6: Verify        三层检查（功能等价性 → 路由精准性 → 精简完备性）
Phase 7: Routing Map   输出路由决策表
Phase 8: Lean Check    冗余检测 + 完备性检测 + 复杂度阈值 + 死代码检测
```

## 歧义评分算法

```python
# 40% 触发词重叠 + 30% 领域匹配 + 30% 结构相似度
ambiguity = trigger_overlap * 0.40 + domain_match * 0.30 + structural * 0.30

≥ 70% → 🔴 CONFLICT  (必须合并或加 NOT 子句)
40-70% → 🟡 AMBIGUOUS (可建立边界)
20-40% → 🟢 NEAR      (低风险)
< 20% → ✅ DISTINCT   (无冲突)
```

## License

MIT
