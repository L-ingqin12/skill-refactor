# JSON Schemas for Skill Refactor

## analyze_skills.py Output Schema

```json
{
  "scan_paths": ["array of scanned directory paths"],
  "total_skills": "integer — total skills found",
  "skills": [
    {
      "name": "skill identifier (from frontmatter or filename)",
      "file_path": "absolute path to skill file",
      "description": "trigger description from frontmatter",
      "type": "command | skill",
      "domain": "detected domain (git|code_review|deploy|testing|docker|npm|file_ops|data|docs|search|general)",
      "trigger_keywords": ["extracted", "trigger", "words"],
      "functional_steps": ["extracted", "step", "descriptions"],
      "tools_used": ["detected", "tools"],
      "complexity": "simple | moderate | complex",
      "content_length_lines": "integer",
      "frontmatter_keys": ["keys", "in", "yaml", "frontmatter"]
    }
  ],
  "complexity_distribution": {"simple": 1, "moderate": 3, "complex": 2},
  "comparisons": [
    {
      "skill_a": "name",
      "skill_b": "name",
      "domain_a": "domain of skill A",
      "domain_b": "domain of skill B",
      "file_a": "path",
      "file_b": "path",
      "ambiguity": {
        "trigger_overlap": "0.0-1.0 — keyword Jaccard overlap",
        "domain_overlap": "0.0-1.0 — domain keyword Jaccard overlap",
        "structural_similarity": "0.0-1.0 — (tool_sim + step_sim) / 2",
        "ambiguity_score": "0.0-1.0 — 0.4*trigger + 0.3*domain + 0.3*structural"
      },
      "classification": "CONFLICT | AMBIGUOUS | NEAR | DISTINCT"
    }
  ],
  "actionable_pairs": "integer — total comparisons",
  "ambiguity_summary": {
    "conflict": "integer — pairs with ambiguity ≥ 0.7",
    "ambiguous": "integer — pairs with ambiguity 0.4-0.7",
    "near": "integer — pairs with ambiguity 0.2-0.4",
    "distinct": "integer — pairs with ambiguity < 0.2"
  },
  "complexity_flags": [
    {"name": "skill name", "complexity": "complex", "lines": 450}
  ]
}
```

## Functionality Fingerprint Schema

Saved to `fingerprints/<skill-name>.json` before refactoring:

```json
{
  "skill_name": "original-skill-name",
  "captured_at": "ISO timestamp",
  "source_file": "path/to/skill.md",
  "steps": [
    {
      "id": 1,
      "description": "what this step does",
      "inputs": ["what it needs"],
      "outputs": ["what it produces"],
      "tools_called": ["tools used"],
      "edge_cases": ["how edge cases are handled"]
    }
  ],
  "trigger_scenarios": [
    "user query that should trigger this skill"
  ],
  "cross_references": [
    {"skill": "other-skill", "relationship": "precedes | follows | alternative"}
  ]
}
```

## Routing Map Schema

```json
{
  "trigger_word_groups": {
    "review": {
      "skills": ["code-review", "security-review", "pr-review-toolkit"],
      "decision_table": [
        {
          "user_intent": "check bugs and compliance",
          "correct_skill": "code-review",
          "signals": ["review PR", "check bugs", "code review"],
          "negative_signals": ["security", "vulnerability", "comprehensive"]
        }
      ]
    }
  }
}
```

## Grader Output Schema

See `agents/grader.md` for the full grading output format.
