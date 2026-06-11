---
description: Eliminate routing ambiguity between similar skills. When multiple skills overlap in trigger conditions, agents pick the wrong one — this skill analyzes overlap, establishes decision boundaries, and rewrites descriptions so each skill has a unique, unambiguous trigger signature. Use when skills confuse the agent or the user says "the agent picked the wrong skill".
---

# Skill Refactor — Eliminate Routing Ambiguity

Your task is to analyze the user's skills and eliminate routing conflicts so agents always pick the right skill.

## Core Problem

When multiple skills share trigger keywords, the agent cannot distinguish them from descriptions alone — it picks wrong, wastes tokens going down an incorrect path.

## Process

### 1. Discover
```bash
find ~/.claude/commands ~/.claude/skills -name "*.md" 2>/dev/null
find .claude/commands .claude/skills -name "*.md" 2>/dev/null
```

### 2. Diagnose
```bash
python3 /root/.claude/skills/skill-refactor/scripts/analyze_skills.py
```
Parse the JSON output. Focus on pairs with **Ambiguity Score ≥ 40%** — these are routing risks.

### 3. Establish Decision Boundaries
For each high-ambiguity pair, establish a mutually exclusive condition:
- **Method 1: NOT clause** — add "Do NOT use for X" to each description
- **Method 2: Scope layering** — differentiate by scope/speed (fast vs comprehensive)
- **Method 3: Scene anchoring** — differentiate by user intent/phase (mid-work vs done)
- **Method 4: Merge** — if boundary is impossible, merge into one precise skill

### 4. Route Test
Mentally test with 10+ queries. Can agent pick correctly from description alone?

### 5. Execute
Present the plan → get user confirmation → backup originals → rewrite descriptions.

### 6. Output Routing Map
Generate a decision table: "When user says X → use skill Y because signal Z."

## Reference
- Full methodology: `/root/.claude/skills/skill-refactor/SKILL.md`
- Patterns catalog: `/root/.claude/skills/skill-refactor/references/refactoring_patterns.md`
- Analysis script: `/root/.claude/skills/skill-refactor/scripts/analyze_skills.py`
