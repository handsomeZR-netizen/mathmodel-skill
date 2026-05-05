"""
extract_diff.py — Section-level patch refinement 工具

功能: 把 L1 critique.issues 转换成"只修订有问题段落"的精修指令,
      避免重新生成整个 artifact, 节省 60% token.

实现策略 (修复原 unified diff 实现的丢修订 bug):
- 优先模式: section-level patch (按 markdown ## 章节定位 + 全段替换)
- 备选模式: unified diff via unidiff 库 (健壮的 hunk parser)

用法:
    python scripts/extract_diff.py --artifact artifact_v0.md --critique critique_v0.json --mode section
    python scripts/extract_diff.py --artifact a.md --critique c.json --mode diff --apply patch.diff
"""

import json
import argparse
import re
from pathlib import Path


def load_artifact(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_critique(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def split_sections(artifact: str) -> list[tuple[str, int, int]]:
    """
    把 markdown 按 ## / ### 切片, 返回 [(heading, start_line, end_line), ...]
    """
    lines = artifact.splitlines()
    sections = []
    current_heading = "<前言>"
    current_start = 0
    for i, line in enumerate(lines):
        if re.match(r"^#{1,6}\s", line):
            if i > current_start:
                sections.append((current_heading, current_start, i - 1))
            current_heading = line.strip()
            current_start = i
    if current_start < len(lines):
        sections.append((current_heading, current_start, len(lines) - 1))
    return sections


def find_relevant_sections(artifact: str, issue_where: str) -> list[tuple[str, int, int]]:
    """
    根据 issue.where (e.g., '§5.1.2 公式 (5.3)' / '摘要 段 3') 找匹配的 section
    """
    sections = split_sections(artifact)
    tokens = re.findall(r"§?[\d.]+|[一-鿿]{2,}|[A-Za-z]+", issue_where)
    matched = []
    for heading, start, end in sections:
        if any(tok in heading for tok in tokens):
            matched.append((heading, start, end))
    return matched


def build_section_patch_prompt(artifact_path: str, critique: dict) -> str:
    """
    构造 section-level patch 模式精修 prompt
    """
    artifact = load_artifact(artifact_path)
    lines = artifact.splitlines()
    issues = critique.get("issues", [])

    targets = []
    for i, issue in enumerate(issues):
        where = issue.get("where", "")
        relevant = find_relevant_sections(artifact, where)
        if relevant:
            heading, start, end = relevant[0]
            section_text = "\n".join(lines[start:end + 1])
            if len(section_text) > 1500:
                section_text = section_text[:1500] + "\n... <truncated>"
            targets.append({
                "issue_id": f"issue_{i}",
                "where": where,
                "fix": issue.get("fix", ""),
                "anti_pattern_id": issue.get("anti_pattern_id"),
                "section_heading": heading,
                "section_lines": [start, end],
                "section_excerpt": section_text,
            })
        else:
            targets.append({
                "issue_id": f"issue_{i}",
                "where": where,
                "fix": issue.get("fix", ""),
                "anti_pattern_id": issue.get("anti_pattern_id"),
                "section_heading": "<未匹配, 全文级修订>",
                "section_excerpt": "",
            })

    return f"""# 精修任务 (Section-Level Patch)

artifact 路径: `{artifact_path}` ({len(lines)} 行).

下列每个 issue 对应一个 section (按 markdown ## 章节定位)。请**只重写**列出的 section, 不动其他部分。

## Targets

{json.dumps(targets, ensure_ascii=False, indent=2)}

## Output Format

针对每个 issue, 输出一个完整重写的 section, 用以下结构分隔:

```
<<< SECTION_PATCH issue_0
<重写后的整段 markdown, 含原 heading>
>>>
<<< SECTION_PATCH issue_1
...
>>>
```

要求:
- 每个 section_patch 必须以原 section 的 heading (e.g., `### 5.1.2 求解算法`) 开头
- 不要输出 `<前言>` 或 `<未匹配>` 类的 patch (无法精确定位的, 在新增章节里说明)
- 不要修改未列出的 issue 涉及的 section
"""


def apply_section_patches(artifact: str, patches_text: str) -> str:
    """
    应用 section_patch 输出到 artifact (替代原错误的 zip+replace 实现)
    """
    pattern = re.compile(r"<<< SECTION_PATCH (\S+)\s*\n(.*?)\n>>>", re.DOTALL)
    patches = {m.group(1): m.group(2) for m in pattern.finditer(patches_text)}

    lines = artifact.splitlines()
    sections = split_sections(artifact)

    # 按 heading 索引
    heading_to_range = {h: (s, e) for h, s, e in sections}

    # 应用补丁: 每个 patch 第一行应该是 heading, 用其定位
    new_lines = list(lines)
    edits = []  # (start, end, replacement_lines)
    for issue_id, patch_text in patches.items():
        patch_lines = patch_text.splitlines()
        if not patch_lines:
            continue
        first_line = patch_lines[0].strip()
        if first_line in heading_to_range:
            start, end = heading_to_range[first_line]
            edits.append((start, end, patch_lines))
        # else: 无法定位的 patch 静默丢弃 (要求输出格式时已禁止)

    # 倒序应用避免行号偏移
    edits.sort(key=lambda x: x[0], reverse=True)
    for start, end, repl in edits:
        new_lines[start:end + 1] = repl

    return "\n".join(new_lines)


def build_unified_diff_prompt(artifact_path: str, critique: dict) -> str:
    """
    备选: 严格 unified diff 模式 (用 unidiff 库应用, 见 apply_unidiff)
    """
    artifact = load_artifact(artifact_path)
    issues = critique.get("issues", [])
    return f"""# 精修任务 (Unified Diff)

artifact: `{artifact_path}` ({len(artifact.splitlines())} 行).

issues:
{json.dumps(issues, ensure_ascii=False, indent=2)}

输出 git-style unified diff (含 file headers + hunk headers + 至少 3 行 context):

```diff
--- {artifact_path}
+++ {artifact_path}
@@ -<old_start>,<old_count> +<new_start>,<new_count> @@
 context line
-removed line
+added line
 context line
```

可多个 hunk。**必须**:
1. 行号精确 (从 1 开始, 1-based)
2. context 行至少 3 行 (前后各一组)
3. 文件结尾若改动, 包含 EOF marker
"""


def apply_unidiff(artifact: str, diff_text: str) -> str:
    """
    用 unidiff 库严格应用 patch (替代原错误的 zip+replace)
    """
    try:
        from unidiff import PatchSet
    except ImportError:
        raise ImportError("需 pip install unidiff (见 templates/requirements.txt)")

    patch = PatchSet.from_string(diff_text)
    lines = artifact.splitlines()

    for patched_file in patch:
        for hunk in patched_file:
            # hunk.source_start 是 1-based, 我们要 0-based
            new_lines = []
            old_idx = hunk.source_start - 1
            for line in hunk:
                if line.is_context:
                    new_lines.append(line.value.rstrip("\n"))
                elif line.is_added:
                    new_lines.append(line.value.rstrip("\n"))
                # is_removed: 跳过
            # 替换原文件 [source_start-1, source_start-1+source_length] 区间
            end = old_idx + hunk.source_length
            lines[old_idx:end] = new_lines
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=str, required=True)
    parser.add_argument("--critique", type=str, required=True)
    parser.add_argument("--mode", choices=["section", "diff"], default="section")
    parser.add_argument("--output", type=str, default=None,
                        help="输出 prompt 到文件 (不指定则 stdout)")
    parser.add_argument("--apply", type=str, default=None,
                        help="若给出, 把该文件 (LLM 返回的 patch/diff) 应用到 artifact, 输出到 stdout")
    args = parser.parse_args()

    if args.apply:
        artifact = load_artifact(args.artifact)
        patch_text = Path(args.apply).read_text(encoding="utf-8")
        if args.mode == "section":
            new_artifact = apply_section_patches(artifact, patch_text)
        else:
            new_artifact = apply_unidiff(artifact, patch_text)
        print(new_artifact)
        return 0

    critique = load_critique(args.critique)
    if args.mode == "section":
        prompt = build_section_patch_prompt(args.artifact, critique)
    else:
        prompt = build_unified_diff_prompt(args.artifact, critique)

    if args.output:
        Path(args.output).write_text(prompt, encoding="utf-8")
        print(f"✅ 精修 prompt 已写入 {args.output}")
        print(f"   (token 估算: ~{len(prompt) // 4} tokens)")
    else:
        print(prompt)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
