---
description: Eliminate routing ambiguity between similar skills. When multiple skills overlap in trigger conditions, agents pick the wrong one — this skill analyzes overlap, establishes decision boundaries, and rewrites descriptions so each skill has a unique, unambiguous trigger signature. Use when skills confuse the agent or the user says "the agent picked the wrong skill".
---

# Skill Refactor

Your task: eliminate routing conflicts so agents always pick the right skill, while keeping each skill lean and functionally intact.

## Process

Read the full methodology first:
```
Read ~/.claude/skills/skill-refactor/SKILL.md
```

### Phase 1: Discover
```bash
find ~/.claude/commands ~/.claude/skills -name "*.md" 2>/dev/null
find .claude/commands .claude/skills -name "*.md" 2>/dev/null
```

### Phase 2: Diagnose
```bash
python3 ~/.claude/skills/skill-refactor/scripts/analyze_skills.py
```
Focus on pairs with **Ambiguity Score ≥ 40%**.

### Phase 3: Establish Decision Boundaries
For each high-ambiguity pair, establish mutually exclusive conditions:
- NOT clause, scope layering, scene anchoring, or merge

### Phase 4: Route Test
Mentally test 10+ queries. Can agent pick correctly from description alone?

### Phase 5: Execute (with functionality preservation)
1. Extract functionality fingerprint from original skills
2. Backup originals to `~/.claude/backups/`
3. Rewrite descriptions + body
4. Trace every original step against the new version
5. Update cross-references in other skills

### Phase 6: Verify (3-layer check)
- Layer 1 (Must): Functionality equivalence — 100% trace pass
- Layer 2 (Should): Routing precision — ≥90% hit rate
- Layer 3 (Nice): Lean completeness — no filler, no duplication

### Phase 7: Output Routing Map
Decision table: "When user says X → use skill Y because signal Z."

### Phase 8: Lean & Complete Check
Redundancy detection, completeness check, complexity threshold, ruthless cut, dead code removal.

## Reference
- Methodology: `~/.claude/skills/skill-refactor/SKILL.md`
- Patterns: `~/.claude/skills/skill-refactor/references/refactoring_patterns.md`
- Analyzer: `~/.claude/skills/skill-refactor/scripts/analyze_skills.py`
