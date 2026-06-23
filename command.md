---
description: Diagnose and fix routing conflicts between user-created skills. Use only when user explicitly asks to refactor, reorganize, merge or audit skills.
---

# Skill Refactor — Quick Diagnosis

**⚠️ GUARD: Only proceed if the user explicitly asked to audit/refactor/reorganize skills. If unsure, ask the user first. Do NOT trigger on general confusion about which skill to use.**

## Minimal Path (default — stop after Phase 2 unless user asks for more)

### Step 1: Scan
```bash
find ~/.claude/commands ~/.claude/skills -name "*.md" 2>/dev/null
```

### Step 2: Run Analyzer
```bash
python3 ~/.claude/skills/skill-refactor/scripts/analyze_skills.py
```

### Step 3: Report & STOP
Parse the JSON. Present only the critical findings:
- 🔴 CONFLICT pairs (ambiguity ≥ 70%)
- 🟡 AMBIGUOUS pairs (40-70%)
- Skills flagged as complex (≥6 steps) or >300 lines

**STOP HERE unless the user explicitly asks to proceed with refactoring.** Do NOT automatically continue to rewrite skills.

## If user asks to proceed

Read `~/.claude/skills/skill-refactor/SKILL.md` for the full methodology (decision boundaries, functionality fingerprints, route testing).

## Reference
- Full methodology: `~/.claude/skills/skill-refactor/SKILL.md`
- Patterns: `~/.claude/skills/skill-refactor/references/refactoring_patterns.md`
