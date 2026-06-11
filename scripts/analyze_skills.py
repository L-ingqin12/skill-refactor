#!/usr/bin/env python3
"""
Skill Analyzer — 自动解析 skill 文件，提取结构化信息用于相似度分析。

Usage:
    python scripts/analyze_skills.py <path1> <path2> ...
    python scripts/analyze_skills.py ~/.claude/commands ~/.claude/skills

Output: JSON to stdout — skill 列表及结构化分析结果
"""

import os
import re
import json
import sys
import yaml
from pathlib import Path
from collections import Counter


def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown content."""
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def extract_trigger_keywords(description: str) -> list[str]:
    """Extract meaningful trigger keywords from a skill description."""
    if not description:
        return []

    # Normalize: lowercase, remove punctuation
    text = re.sub(r'[^\w\s]', ' ', description.lower())

    # Common stop words to exclude
    stops = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'can', 'shall',
        'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
        'and', 'or', 'but', 'not', 'no', 'if', 'then', 'else', 'when',
        'this', 'that', 'these', 'those', 'it', 'its', 'use', 'using',
        'used', 'user', 'users', 'want', 'wants', 'need', 'needs',
        'skill', 'skills', 'make', 'sure', 'also', 'just', 'like',
        'the', 'how', 'what', 'where', 'which', 'who', 'whom', 'why',
    }

    words = text.split()
    keywords = [w for w in words if w not in stops and len(w) > 2]
    return list(dict.fromkeys(keywords))  # dedupe preserving order


def extract_functional_steps(content: str) -> list[str]:
    """Extract a high-level summary of what the skill does by examining its structure."""
    steps = []

    # Look for numbered lists, bullet points with action verbs
    action_patterns = [
        r'^\d+\.\s\*\*(.*?)\*\*',         # 1. **Step title**
        r'^\d+\.\s+(Analyze|Create|Run|Execute|Check|Review|Commit|Push|Open|Generate|Read|Write|Test|Build|Deploy|Install|Configure|Start|Stop|Fetch|Scan|Search|Find|Extract|Compare|Merge|Split|Validate|Verify|Clean|Remove|Delete|Update|Add|Set|Get|List|Show)',  # 1. Action verb
        r'^###\s+(.*)',                     # ### Subsection titles
        r'^\*\*(.*?)\*\*',                  # **Bold headers**
    ]

    for line in content.split('\n'):
        for pat in action_patterns:
            m = re.match(pat, line.strip(), re.IGNORECASE)
            if m:
                step = m.group(1).strip()
                if len(step) < 100 and step not in steps:
                    steps.append(step)

    return steps[:15]  # Cap at 15 steps


def detect_complexity(content: str) -> str:
    """Classify skill complexity."""
    step_count = len(extract_functional_steps(content))

    # Check for subagent usage
    has_subagents = bool(re.search(r'subagent|agent\s*\(|parallel\s*agent|spawn', content, re.IGNORECASE))
    has_scripts = bool(re.search(r'```(bash|python|sh|zsh)', content))

    if step_count >= 8 or has_subagents:
        return "complex"
    elif step_count >= 3 or has_scripts:
        return "moderate"
    else:
        return "simple"


def detect_tool_usage(content: str, frontmatter: dict) -> list[str]:
    """Detect what tools/external deps the skill uses."""
    tools = set()

    if 'allowed-tools' in frontmatter:
        tools.add('declared_allowed_tools')

    patterns = {
        'git': r'\bgit\b',
        'github_cli': r'\bgh\b',
        'docker': r'\bdocker\b',
        'npm': r'\bnpm\b',
        'python': r'\bpython[3]?\b',
        'curl': r'\bcurl\b',
        'mcp': r'\bmcp\b|MCP',
        'subagent': r'subagent|agent\s*\(|launch.*agent|spawn.*agent',
        'web_search': r'WebSearch|web.search',
        'web_fetch': r'WebFetch|web.fetch',
        'lsp': r'\bLSP\b|language.server',
        'jq': r'\bjq\b',
        'grep': r'\bgrep\b|Grep',
        'find': r'\bfind\b|Glob',
    }

    for tool, pattern in patterns.items():
        if re.search(pattern, content, re.IGNORECASE):
            tools.add(tool)

    return sorted(tools)


def detect_domain(description: str, steps: list[str], tools: list[str]) -> str:
    """Detect the functional domain a skill belongs to."""
    domain_keywords = {
        'git': ['git', 'commit', 'push', 'branch', 'pr', 'pull request', 'merge', 'rebase'],
        'code_review': ['review', 'code review', 'bug', 'compliance', 'security review', 'inspection'],
        'deploy': ['deploy', 'release', 'publish', 'ship', 'production', 'staging'],
        'testing': ['test', 'unittest', 'pytest', 'coverage', 'assert', 'mock', 'e2e'],
        'docker': ['docker', 'container', 'image', 'compose', 'kubernetes', 'k8s'],
        'npm': ['npm', 'package', 'node', 'javascript', 'typescript', 'install'],
        'file_ops': ['file', 'read', 'write', 'copy', 'move', 'delete', 'rename'],
        'data': ['data', 'csv', 'json', 'parse', 'transform', 'extract'],
        'docs': ['doc', 'readme', 'documentation', 'wiki', 'markdown', 'md'],
        'search': ['search', 'find', 'grep', 'locate', 'query', 'lookup'],
    }

    text = (description + ' ' + ' '.join(steps) + ' ' + ' '.join(tools)).lower()
    scores = {domain: sum(1 for kw in kws if kw in text) for domain, kws in domain_keywords.items()}
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else 'general'


def compute_ambiguity_score(skill_a: dict, skill_b: dict) -> dict:
    """Compute ambiguity score between two skills — how likely agent picks wrong.

    This is the core metric. High ambiguity = agent will confuse these two skills.
    Weights tuned for routing accuracy: trigger words matter most (agent decides
    from description), domain overlap second, structural similarity third.
    """
    # 1. Trigger Word Overlap (40%) — most important for routing
    kw_a = set(skill_a.get('trigger_keywords', []))
    kw_b = set(skill_b.get('trigger_keywords', []))
    union = kw_a | kw_b
    intersection = kw_a & kw_b
    trigger_overlap = len(intersection) / len(union) if union else 0

    # 2. Domain Overlap (30%) — same domain = higher confusion risk
    domain_a = skill_a.get('domain', 'general')
    domain_b = skill_b.get('domain', 'general')
    domain_match = 1.0 if domain_a == domain_b else 0.0

    # 3. Structural Similarity (30%) — similar tools + steps
    tools_a = set(skill_a.get('tools_used', []))
    tools_b = set(skill_b.get('tools_used', []))
    tool_union = tools_a | tools_b
    tool_intersection = tools_a & tools_b
    tool_sim = len(tool_intersection) / len(tool_union) if tool_union else 0

    steps_a = set(' '.join(skill_a.get('functional_steps', [])).lower().split())
    steps_b = set(' '.join(skill_b.get('functional_steps', [])).lower().split())
    step_union = steps_a | steps_b
    step_intersection = steps_a & steps_b
    step_sim = len(step_intersection) / len(step_union) if step_union else 0

    structural = (tool_sim + step_sim) / 2

    # Weighted composite — routing ambiguity score
    ambiguity = (trigger_overlap * 0.40 + domain_match * 0.30 + structural * 0.30)

    return {
        'trigger_overlap': round(trigger_overlap, 3),
        'domain_match': domain_match,
        'domain_a': domain_a,
        'domain_b': domain_b,
        'structural_similarity': round(structural, 3),
        'ambiguity_score': round(ambiguity, 3),
    }


def classify_ambiguity(ambiguity: float) -> str:
    """Classify the routing risk between two skills.

    CONFLICT:  agent cannot distinguish — must merge or add NOT clauses
    AMBIGUOUS: overlapping but boundary can be drawn
    NEAR:      adjacent domains, low risk
    DISTINCT:  clearly different, no action needed
    """
    if ambiguity >= 0.7:
        return "CONFLICT"
    elif ambiguity >= 0.4:
        return "AMBIGUOUS"
    elif ambiguity >= 0.2:
        return "NEAR"
    else:
        return "DISTINCT"


def analyze_file(filepath: str) -> dict | None:
    """Parse a single skill file and return structured analysis."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except Exception as e:
        return {'file_path': filepath, 'error': str(e)}

    if not content.strip():
        return None

    fm = parse_frontmatter(content)

    description = fm.get('description', '')
    name = fm.get('name', os.path.splitext(os.path.basename(filepath))[0])

    trigger_kw = extract_trigger_keywords(description)
    steps = extract_functional_steps(content)
    complexity = detect_complexity(content)
    tools = detect_tool_usage(content, fm)
    domain = detect_domain(description, steps, tools)

    # Detect if this is a command (single file) or part of a skill directory
    is_command = os.path.basename(os.path.dirname(filepath)) == 'commands'

    return {
        'name': name,
        'file_path': filepath,
        'description': description,
        'type': 'command' if is_command else 'skill',
        'domain': domain,
        'trigger_keywords': trigger_kw,
        'functional_steps': steps,
        'tools_used': tools,
        'complexity': complexity,
        'content_length_lines': len(content.split('\n')),
        'frontmatter_keys': list(fm.keys()),
    }


def scan_directories(paths: list[str]) -> list[str]:
    """Recursively find all .md skill files in given paths."""
    files = []
    for p in paths:
        path = Path(os.path.expanduser(p))
        if not path.exists():
            continue
        if path.is_file() and path.suffix == '.md':
            files.append(str(path))
        elif path.is_dir():
            for md in path.rglob('*.md'):
                # Skip README files, skip non-skill markdown
                if md.name == 'README.md':
                    continue
                if md.name == 'SKILL.md' or md.parent.name in ('commands', 'skills'):
                    files.append(str(md))
                elif md.parent.parent.name in ('commands', 'skills'):
                    files.append(str(md))
    return sorted(set(files))


def build_comparison_matrix(skills: list[dict]) -> list[dict]:
    """Build pairwise comparison matrix for all skills — routing ambiguity focus."""
    comparisons = []
    for i in range(len(skills)):
        for j in range(i + 1, len(skills)):
            a, b = skills[i], skills[j]
            if a.get('error') or b.get('error'):
                continue
            ambiguity = compute_ambiguity_score(a, b)
            classification = classify_ambiguity(ambiguity['ambiguity_score'])
            comparisons.append({
                'skill_a': a['name'],
                'skill_b': b['name'],
                'domain_a': a.get('domain', ''),
                'domain_b': b.get('domain', ''),
                'file_a': a['file_path'],
                'file_b': b['file_path'],
                'ambiguity': ambiguity,
                'classification': classification,
            })
    return sorted(comparisons, key=lambda x: x['ambiguity']['ambiguity_score'], reverse=True)


def main():
    if len(sys.argv) < 2:
        # Default scan paths
        scan_paths = [
            os.path.expanduser('~/.claude/commands'),
            os.path.expanduser('~/.claude/skills'),
            '.claude/commands',
            '.claude/skills',
        ]
    else:
        scan_paths = sys.argv[1:]

    files = scan_directories(scan_paths)

    if not files:
        print(json.dumps({'error': 'No skill files found', 'scan_paths': scan_paths}, indent=2))
        return

    skills = []
    for f in files:
        result = analyze_file(f)
        if result:
            skills.append(result)

    comparisons = build_comparison_matrix(skills)

    # Complexity stats
    complexity_dist = Counter(s['complexity'] for s in skills)

    output = {
        'scan_paths': scan_paths,
        'total_skills': len(skills),
        'skills': skills,
        'complexity_distribution': dict(complexity_dist),
        'comparisons': comparisons,
        'actionable_pairs': len(comparisons),
        'ambiguity_summary': {
            'conflict': len([c for c in comparisons if c['classification'] == 'CONFLICT']),
            'ambiguous': len([c for c in comparisons if c['classification'] == 'AMBIGUOUS']),
            'near': len([c for c in comparisons if c['classification'] == 'NEAR']),
            'distinct': len([c for c in comparisons if c['classification'] == 'DISTINCT']),
        },
        'complexity_flags': [
            {'name': s['name'], 'complexity': s['complexity'], 'lines': s['content_length_lines']}
            for s in skills if s['complexity'] == 'complex' or s['content_length_lines'] > 300
        ]
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
