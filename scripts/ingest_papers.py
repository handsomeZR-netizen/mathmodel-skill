"""
papers 已蒸馏, 本脚本归档不再使用; 需重新蒸馏请用 git 历史里的 papers/ 目录。

ingest_papers.py — 离线烘焙: 从 references/papers/ 下的 91 篇真国赛获奖论文 PDF
                    抽取定量统计, 生成 references/empirical_distribution.md.

这是 skill 维护期的一次性脚本, 不在运行时调用。
烘焙后的 markdown 在 L1 critic 评分时作为"硬阈值维度"的实测分位数依据。

依赖: pdfplumber (pip install pdfplumber)

用法:
    python scripts/ingest_papers.py --papers-dir references/papers/ \\
                                     --output references/empirical_distribution.md
"""

import argparse
import re
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def extract_pdf_text(pdf_path: Path) -> str:
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("需 pip install pdfplumber (见 templates/requirements.txt)")
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
    except Exception as e:
        print(f"⚠ 无法读取 {pdf_path.name}: {e}")
    return text


def parse_filename_year(name: str) -> int | None:
    m = re.match(r"^(20\d{2})", name)
    return int(m.group(1)) if m else None


def parse_filename_letter(name: str) -> str | None:
    m = re.match(r"^20\d{2}-([A-F])", name)
    return m.group(1) if m else None


def analyze_paper(text: str, filename: str) -> dict:
    if not text:
        return {}
    chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
    english_words = len(re.findall(r"\b[A-Za-z]+\b", text))
    total_chars = chinese_chars + english_words

    section_pattern = re.compile(r"^\s*(\d+)[\.、]\s+\S", re.MULTILINE)
    sections = sorted(set(int(m.group(1)) for m in section_pattern.finditer(text)))
    n_sections = len(sections)

    subsection_pattern = re.compile(r"^\s*(\d+\.\d+)\s+\S", re.MULTILINE)
    subsections = sorted(set(m.group(1) for m in subsection_pattern.finditer(text)))
    n_subsections = len(subsections)

    n_figures = len(set(re.findall(r"图\s*(\d+)", text)))
    n_tables = len(set(re.findall(r"表\s*(\d+)", text)))
    formulas = re.findall(r"\(\d+\.\d+\)|\(\d+\)", text)
    n_formulas = len(set(formulas))

    # 摘要提取 — OR 多模式 (V3 P3-1 修复, 原版只匹配少数论文)
    abstract = ""
    abstract_patterns = [
        # 中文摘要
        r"摘\s*要\s*[::\s\n]+(.{100,1800}?)(?=关\s*键\s*词|关\s*键\s*字|\n\s*\d+[、.]\s+\S)",
        # 英文 Abstract
        r"Abstract\s*[::\s\n]+(.{100,1800}?)(?=Keywords|Key\s*words|关键词)",
        # "摘要 一、" 数字小标题前
        r"摘\s*要(.{100,1800}?)(?=关键词|一[、.]|\n1[、.]\s)",
    ]
    for pat in abstract_patterns:
        m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
        if m:
            abstract = m.group(1).strip()[:1500]
            break

    # Fallback: 取前 1500 字符 (大概率包含摘要 + 关键词 + 引言开头)
    if not abstract or len(abstract) < 100:
        abstract = text[:1500]

    keywords_match = re.search(r"关键词?\s*[::]?\s*([^\n]{5,150})", text)
    keywords = keywords_match.group(1).strip() if keywords_match else ""
    n_keywords = len([k for k in re.split(r"[,、;\s]+", keywords) if k.strip()])

    n_refs = len(re.findall(r"\[\s*\d+\s*\]", text))

    has_quant_results = bool(re.search(
        r"\d+\.?\d*\s*(?:%|元|件|km|kg|m/s|分钟|小时|倍|x|百分点|个|次|台)", abstract))

    abstract_word_count = sum(1 for c in abstract if '一' <= c <= '鿿')

    five_para_signals = sum([
        bool(re.search(r"针对.{0,30}问题", abstract)),
        bool(re.search(r"问题一|问题二|问题三", abstract)),
        bool(re.search(r"灵敏度|稳健性|鲁棒", abstract)),
        bool(re.search(r"创新|首次|可推广", abstract)),
        bool(re.search(r"得到|求解|结果", abstract)),
    ])

    return {
        "filename": filename,
        "year": parse_filename_year(filename),
        "letter": parse_filename_letter(filename),
        "total_chars": total_chars,
        "chinese_chars": chinese_chars,
        "english_words": english_words,
        "n_sections": n_sections,
        "sections_present": sections,
        "n_subsections": n_subsections,
        "n_figures": n_figures,
        "n_tables": n_tables,
        "n_formulas": n_formulas,
        "abstract_chinese_chars": abstract_word_count,
        "abstract_quant_results": has_quant_results,
        "abstract_5para_signals": five_para_signals,
        "n_keywords": n_keywords,
        "n_refs": n_refs,
    }


def percentiles(values: list, qs=(25, 50, 75)) -> dict:
    if not values:
        return {}
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    out = {}
    for q in qs:
        idx = max(0, min(n - 1, int(n * q / 100)))
        out[f"p{q}"] = sorted_vals[idx]
    out["min"] = sorted_vals[0]
    out["max"] = sorted_vals[-1]
    out["mean"] = round(sum(sorted_vals) / n, 1)
    return out


def aggregate(stats_list: list) -> dict:
    keys = ["total_chars", "chinese_chars", "n_sections", "n_subsections",
            "n_figures", "n_tables", "n_formulas",
            "abstract_chinese_chars", "abstract_5para_signals", "n_keywords", "n_refs"]
    agg = {k: percentiles([s[k] for s in stats_list if k in s]) for k in keys}
    n = len(stats_list)
    agg["pct_with_quantitative_abstract"] = round(
        sum(1 for s in stats_list if s.get("abstract_quant_results")) / n * 100, 1)
    agg["pct_5para_full"] = round(
        sum(1 for s in stats_list if s.get("abstract_5para_signals", 0) >= 4) / n * 100, 1)
    agg["pct_5para_partial"] = round(
        sum(1 for s in stats_list if s.get("abstract_5para_signals", 0) >= 3) / n * 100, 1)
    return agg


def split_by_year(stats_list: list) -> dict:
    groups = defaultdict(list)
    for s in stats_list:
        if s.get("year"):
            groups[s["year"]].append(s)
    return {y: aggregate(g) for y, g in sorted(groups.items())}


def split_by_letter(stats_list: list) -> dict:
    groups = defaultdict(list)
    for s in stats_list:
        if s.get("letter"):
            groups[s["letter"]].append(s)
    return {L: aggregate(g) for L, g in sorted(groups.items())}


def render_markdown(overall: dict, by_year: dict, by_letter: dict, n_total: int) -> str:
    lines = []
    lines.append("# 国赛获奖论文实测分布 (empirical_distribution)")
    lines.append("")
    lines.append(f"> 从 `references/papers/` 下 {n_total} 篇真国赛获奖论文 (2023-2025) 自动烘焙。")
    lines.append(f"> 烘焙时间: {datetime.now().isoformat(timespec='seconds')}.")
    lines.append("> 由 `scripts/ingest_papers.py` 生成。L1 critic 评摘要字数等硬阈值维度时引用本文件 p 分位。")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 1. 整体分布 (全部 {} 篇)".format(n_total))
    lines.append("")
    lines.append("| 指标 | min | p25 | p50 (median) | p75 | max | mean |")
    lines.append("|------|-----|-----|---------|-----|-----|------|")
    metric_names = {
        "total_chars": "全文字符总数 (中+英)",
        "chinese_chars": "全文中文字符",
        "n_sections": "主章节数",
        "n_subsections": "子章节数",
        "n_figures": "图数",
        "n_tables": "表数",
        "n_formulas": "公式数",
        "abstract_chinese_chars": "摘要中文字数",
        "abstract_5para_signals": "摘要 5 段 anchor 命中数",
        "n_keywords": "关键词数",
        "n_refs": "参考文献数",
    }
    for key, name in metric_names.items():
        if key in overall and overall[key]:
            d = overall[key]
            lines.append(f"| {name} | {d.get('min')} | {d.get('p25')} | {d.get('p50')} | {d.get('p75')} | {d.get('max')} | {d.get('mean')} |")
    lines.append("")

    lines.append("## 2. 摘要质量信号")
    lines.append("")
    lines.append(f"- **含定量结果比例**: {overall['pct_with_quantitative_abstract']}% (anti_pattern A1 阈值 — 一等奖应 ≥80%)")
    lines.append(f"- **5 段式完整命中 (≥4 anchor)**: {overall['pct_5para_full']}%")
    lines.append(f"- **5 段式部分命中 (≥3 anchor)**: {overall['pct_5para_partial']}%")
    lines.append("")

    lines.append("## 3. 按年份分布")
    lines.append("")
    for year, agg in by_year.items():
        lines.append(f"### {year} 年 ({agg.get('pct_with_quantitative_abstract', 0)}% 含定量)")
        lines.append("")
        lines.append("| 指标 | p25 | p50 | p75 |")
        lines.append("|------|-----|-----|-----|")
        for key in ["chinese_chars", "n_sections", "n_figures", "n_tables", "n_formulas", "abstract_chinese_chars"]:
            if key in agg and agg[key]:
                d = agg[key]
                lines.append(f"| {metric_names[key]} | {d.get('p25')} | {d.get('p50')} | {d.get('p75')} |")
        lines.append("")

    lines.append("## 4. 按题号分布")
    lines.append("")
    for letter, agg in by_letter.items():
        lines.append(f"### {letter} 题")
        lines.append("")
        lines.append("| 指标 | p25 | p50 | p75 |")
        lines.append("|------|-----|-----|-----|")
        for key in ["chinese_chars", "n_sections", "n_figures", "n_tables", "n_formulas"]:
            if key in agg and agg[key]:
                d = agg[key]
                lines.append(f"| {metric_names[key]} | {d.get('p25')} | {d.get('p50')} | {d.get('p75')} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 与 winning_patterns.md 阈值的对照")
    lines.append("")
    lines.append("`winning_patterns.md` 当前的预设阈值 (estimate) vs 本文件的实测分位 (empirical):")
    lines.append("")
    if "abstract_chinese_chars" in overall and overall["abstract_chinese_chars"]:
        d = overall["abstract_chinese_chars"]
        lines.append(f"- 摘要字数: estimate=600-900 vs empirical=p25-p75 [{d.get('p25')}, {d.get('p75')}], median={d.get('p50')}")
    if "n_figures" in overall and overall["n_figures"]:
        d = overall["n_figures"]
        lines.append(f"- 图数: estimate=18-25 vs empirical=p25-p75 [{d.get('p25')}, {d.get('p75')}], median={d.get('p50')}")
    if "n_formulas" in overall and overall["n_formulas"]:
        d = overall["n_formulas"]
        lines.append(f"- 公式数: estimate=60-100 vs empirical=p25-p75 [{d.get('p25')}, {d.get('p75')}], median={d.get('p50')}")
    if "n_refs" in overall and overall["n_refs"]:
        d = overall["n_refs"]
        lines.append(f"- 引用数: estimate=≥10 vs empirical=p25-p75 [{d.get('p25')}, {d.get('p75')}], median={d.get('p50')}")
    lines.append("")
    lines.append("如 estimate 与 empirical 偏差 >20%, 建议手动更新 `winning_patterns.md` 对应阈值。")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--papers-dir", type=str, default="references/papers/")
    parser.add_argument("--output", type=str, default=None,
                        help="输出 markdown 路径; 不指定则 stdout 简短统计")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    papers_dir = Path(args.papers_dir)
    if not papers_dir.exists():
        print(f"❌ {papers_dir} 不存在")
        return 1

    pdfs = list(papers_dir.glob("**/*.pdf"))
    if not pdfs:
        print(f"⚠ {papers_dir} 下未找到 PDF")
        return 0

    print(f"扫描 {len(pdfs)} 篇 PDF...")
    stats_list = []
    for i, pdf in enumerate(pdfs):
        if not args.quiet and (i + 1) % 10 == 0:
            print(f"  已处理 {i+1}/{len(pdfs)}")
        text = extract_pdf_text(pdf)
        s = analyze_paper(text, pdf.name)
        if s:
            stats_list.append(s)

    print(f"\n成功解析 {len(stats_list)}/{len(pdfs)} 篇")

    # 过滤掉图片型 PDF (pdfplumber 提取不到文字, total_chars 过低)
    text_extractable = [s for s in stats_list if s.get("total_chars", 0) > 500]
    print(f"其中文本可提取的 (total_chars>500): {len(text_extractable)} 篇 (image-only PDFs 被过滤)")
    stats_list = text_extractable

    overall = aggregate(stats_list)
    by_year = split_by_year(stats_list)
    by_letter = split_by_letter(stats_list)

    if args.output:
        md = render_markdown(overall, by_year, by_letter, len(stats_list))
        Path(args.output).write_text(md, encoding="utf-8")
        print(f"✅ 已写入 {args.output} ({len(md) // 1024} KB)")
    else:
        print("\n=== 简短摘要 ===")
        print(f"摘要中文字数 p25/p50/p75: {overall['abstract_chinese_chars']}")
        print(f"图数 p25/p50/p75: {overall['n_figures']}")
        print(f"含定量结果比例: {overall['pct_with_quantitative_abstract']}%")
        print(f"\n用 --output references/empirical_distribution.md 写入完整 markdown")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
