"""
render_paper.py — markdown 中间产物 → 最终 PDF (v3.0 三竞赛版)

功能:
1. 读 stage 8 各节 markdown 产出 (cwd/paper_workspace/)
2. 按 competition 选择 LaTeX 模板与编译器:
   - cumcm:    templates/latex/cumcm/cumcmthesis/  + xelatex
   - mcm:      templates/latex/mcm/main.tex        + pdflatex
   - diangong: templates/latex/diangong/main.tex   + xelatex (中文)
3. md → tex (优先 pandoc, 失败回退手工正则)
4. 三编生成 PDF

用法:
    python scripts/render_paper.py --competition cumcm --workspace cwd/paper_workspace/
    python scripts/render_paper.py --competition mcm --workspace ws/ --output out/
    python scripts/render_paper.py --competition diangong --workspace ws/ --no-compile  (dry-run)
"""

import argparse
import json
import os
import re
import subprocess
import shutil
from pathlib import Path


_SKILL_ROOT = Path(__file__).resolve().parent.parent

TEMPLATE_MAP = {
    "cumcm": {
        "template_dir": _SKILL_ROOT / "templates" / "latex" / "cumcm" / "cumcmthesis",
        "engine": "xelatex",
        "main_filename": "paper.tex",
        "mode": "cumcm_assemble",
        "_doc": "cumcm 用 cumcmthesis.cls + 自组装 paper.tex (从 md 节生成完整 .tex 主文档)",
    },
    "mcm": {
        "template_dir": _SKILL_ROOT / "templates" / "latex" / "mcm",
        "engine": "pdflatex",
        "main_filename": "main.tex",
        "mode": "main_template",
        "_doc": "mcm 复制 main.tex 模板, md 节内容生成 sections/sectionname.tex 给 \\input{} 使用",
    },
    "diangong": {
        "template_dir": _SKILL_ROOT / "templates" / "latex" / "diangong",
        "engine": "xelatex",
        "main_filename": "main.tex",
        "mode": "main_template",
        "_doc": "diangong 同 mcm 模式, 用 ctex 中文",
    },
}


SECTION_TO_FILE = {
    "abstract": "01_abstract.md",
    "1_problem_restate": "02_problem_restate.md",
    "2_problem_analysis": "03_analysis.md",
    "3_assumptions": "04_assumptions.md",
    "4_notation": "05_notation.md",
    "5_models": "06_models.md",
    "6_sensitivity": "07_sensitivity.md",
    "7_evaluation": "08_evaluation.md",
    "8_references": "09_references.md",
    "appendix_code": "10_appendix.md",
}


# ============================================================================
# 路径与配置
# ============================================================================

def resolve_competition(cli_arg: str = None, decision_log_path: Path = None) -> str:
    """优先级: CLI > env MATHMODEL_COMPETITION > decision_log.competition > 'cumcm'"""
    if cli_arg:
        return cli_arg
    env = os.environ.get("MATHMODEL_COMPETITION")
    if env:
        return env
    if decision_log_path and decision_log_path.exists():
        try:
            with open(decision_log_path, "r", encoding="utf-8") as f:
                log = json.load(f)
            if log.get("competition"):
                return log["competition"]
        except (json.JSONDecodeError, KeyError):
            pass
    return "cumcm"


# ============================================================================
# md → tex 转换
# ============================================================================

def has_pandoc() -> bool:
    try:
        r = subprocess.run(["pandoc", "--version"], capture_output=True, text=True)
        return r.returncode == 0
    except FileNotFoundError:
        return False


def md_to_tex_pandoc(md_text: str) -> str:
    r = subprocess.run(
        ["pandoc", "-f", "markdown+tex_math_dollars+pipe_tables+raw_tex",
         "-t", "latex", "--no-highlight"],
        input=md_text, capture_output=True, text=True, encoding="utf-8"
    )
    if r.returncode != 0:
        raise RuntimeError(f"pandoc 失败: {r.stderr}")
    return r.stdout


def md_to_tex_fallback(md_text: str) -> str:
    """5 类 markdown → LaTeX 手工正则 (代码块 / 公式块 / 图片 / 表格 / 列表 / 标题 / 行内)"""
    tex = md_text

    def replace_code_block(m):
        lang = m.group(1) or "text"
        body = m.group(2)
        return f"\\begin{{lstlisting}}[language={lang}]\n{body}\n\\end{{lstlisting}}"
    tex = re.sub(r"```(\w+)?\n(.*?)\n```", replace_code_block, tex, flags=re.DOTALL)

    def replace_eq(m):
        body = m.group(1).strip()
        if "\\\\" in body or "&" in body:
            return f"\\begin{{align}}\n{body}\n\\end{{align}}"
        return f"\\begin{{equation}}\n{body}\n\\end{{equation}}"
    tex = re.sub(r"\$\$(.+?)\$\$", replace_eq, tex, flags=re.DOTALL)

    def replace_img(m):
        alt = m.group(1)
        path = m.group(2)
        return (f"\\begin{{figure}}[H]\n\\centering\n"
                f"\\includegraphics[width=0.8\\textwidth]{{{path}}}\n"
                f"\\caption{{{alt}}}\n\\end{{figure}}")
    tex = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_img, tex)

    def replace_table(m):
        rows = [r.strip() for r in m.group(0).splitlines() if r.strip()]
        if len(rows) < 2:
            return m.group(0)
        cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
        header = cells[0]
        data = cells[2:] if len(cells) > 2 else []
        n_cols = len(header)
        col_spec = "l" * n_cols
        out = [f"\\begin{{table}}[H]\n\\centering",
               f"\\begin{{tabular}}{{{col_spec}}}\n\\toprule",
               " & ".join(header) + " \\\\",
               "\\midrule"]
        for row in data:
            out.append(" & ".join(row) + " \\\\")
        out.append("\\bottomrule\n\\end{tabular}\n\\end{table}")
        return "\n".join(out)
    tex = re.sub(r"^\|.+\|\s*$\n^\|[-:\s|]+\|\s*$\n(?:^\|.+\|\s*$\n?)+",
                  replace_table, tex, flags=re.MULTILINE)

    def replace_ol(m):
        items = re.findall(r"^\s*\d+\.\s+(.+)$", m.group(0), re.MULTILINE)
        if not items:
            return m.group(0)
        body = "\n".join(f"\\item {it}" for it in items)
        return f"\\begin{{enumerate}}\n{body}\n\\end{{enumerate}}"
    tex = re.sub(r"(?:^\s*\d+\.\s+.+\n?){2,}", replace_ol, tex, flags=re.MULTILINE)

    def replace_ul(m):
        items = re.findall(r"^\s*-\s+(.+)$", m.group(0), re.MULTILINE)
        if not items:
            return m.group(0)
        body = "\n".join(f"\\item {it}" for it in items)
        return f"\\begin{{itemize}}\n{body}\n\\end{{itemize}}"
    tex = re.sub(r"(?:^\s*-\s+.+\n?){2,}", replace_ul, tex, flags=re.MULTILINE)

    tex = re.sub(r"^# (.+)$", r"\\section{\1}", tex, flags=re.MULTILINE)
    tex = re.sub(r"^## (.+)$", r"\\subsection{\1}", tex, flags=re.MULTILINE)
    tex = re.sub(r"^### (.+)$", r"\\subsubsection{\1}", tex, flags=re.MULTILINE)

    tex = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", tex)
    tex = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\\textit{\1}", tex)
    tex = re.sub(r"`([^`]+?)`", r"\\texttt{\1}", tex)
    tex = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", tex)

    return tex


def md_to_tex(md_text: str, prefer_pandoc: bool = True) -> str:
    if prefer_pandoc and has_pandoc():
        try:
            return md_to_tex_pandoc(md_text)
        except RuntimeError as e:
            print(f"[WARN] pandoc 失败 ({e}), 回退手工正则")
    return md_to_tex_fallback(md_text)


# ============================================================================
# 模板填充: 三竞赛分支
# ============================================================================

def fill_template_cumcm(workspace: Path, template_dir: Path, output_dir: Path,
                         prefer_pandoc: bool = True) -> Path:
    """cumcm: 用 cumcmthesis.cls 自组装完整 paper.tex"""
    output_dir.mkdir(parents=True, exist_ok=True)
    cls_file = template_dir / "cumcmthesis.cls"
    if cls_file.exists():
        shutil.copy(cls_file, output_dir)
    if (template_dir / "figures").exists():
        shutil.copytree(template_dir / "figures", output_dir / "figures",
                         dirs_exist_ok=True)
    if (workspace.parent / "figures").exists():
        shutil.copytree(workspace.parent / "figures", output_dir / "figures",
                         dirs_exist_ok=True)

    tex_parts = {}
    for sec, fname in SECTION_TO_FILE.items():
        md_path = workspace / fname
        if md_path.exists():
            tex_parts[sec] = md_to_tex(md_path.read_text(encoding="utf-8"), prefer_pandoc)
        else:
            print(f"[WARN] 缺失 {fname}, 该节将留空")
            tex_parts[sec] = f"% TODO: 补充 {sec} 内容"

    main_tex = f"""\\documentclass[14pt]{{cumcmthesis}}
\\usepackage{{float}}
\\usepackage{{listings}}
\\title{{论文标题}}
\\tihao{{A}}
\\baominghao{{xxx}}
\\schoolname{{xxx 大学}}
\\membera{{}}
\\memberb{{}}
\\memberc{{}}
\\begin{{document}}
\\maketitle
\\begin{{abstract}}
{tex_parts.get("abstract", "% 摘要")}
\\keywords{{关键词1; 关键词2; 关键词3}}
\\end{{abstract}}
\\tableofcontents
\\newpage

{tex_parts.get("1_problem_restate", "")}

{tex_parts.get("2_problem_analysis", "")}

{tex_parts.get("3_assumptions", "")}

{tex_parts.get("4_notation", "")}

{tex_parts.get("5_models", "")}

{tex_parts.get("6_sensitivity", "")}

{tex_parts.get("7_evaluation", "")}

\\section{{参考文献}}
{tex_parts.get("8_references", "")}

\\appendix
\\section{{程序代码}}
{tex_parts.get("appendix_code", "")}

\\end{{document}}
"""

    main_tex_path = output_dir / "paper.tex"
    main_tex_path.write_text(main_tex, encoding="utf-8")
    print(f"[OK] 已生成 {main_tex_path}")
    return main_tex_path


def fill_template_main(workspace: Path, template_dir: Path, output_dir: Path,
                       main_filename: str, prefer_pandoc: bool = True) -> Path:
    """mcm / diangong: 复制 main.tex + 把 md 节渲染到 sections/<sec>.tex 给用户 \\input{}"""
    output_dir.mkdir(parents=True, exist_ok=True)
    sections_dir = output_dir / "sections"
    sections_dir.mkdir(exist_ok=True)

    # 复制 main.tex
    main_src = template_dir / main_filename
    main_dst = output_dir / main_filename
    if not main_src.exists():
        raise FileNotFoundError(f"模板 {main_src} 不存在")
    shutil.copy(main_src, main_dst)

    # 复制其他 sty / cls 文件
    for ext in ("*.cls", "*.sty", "*.bib"):
        for f in template_dir.glob(ext):
            shutil.copy(f, output_dir)

    # 复制 figures
    if (template_dir / "figures").exists():
        shutil.copytree(template_dir / "figures", output_dir / "figures",
                         dirs_exist_ok=True)
    if (workspace.parent / "figures").exists():
        shutil.copytree(workspace.parent / "figures", output_dir / "figures",
                         dirs_exist_ok=True)

    # md → sections/<sec>.tex
    for sec, fname in SECTION_TO_FILE.items():
        md_path = workspace / fname
        sec_tex_path = sections_dir / f"{sec}.tex"
        if md_path.exists():
            tex = md_to_tex(md_path.read_text(encoding="utf-8"), prefer_pandoc)
            sec_tex_path.write_text(tex, encoding="utf-8")
        else:
            sec_tex_path.write_text(f"% TODO: 补充 {sec} 内容\n", encoding="utf-8")
            print(f"[WARN] 缺失 {fname}, sections/{sec}.tex 留 TODO")

    print(f"[OK] 已复制 {main_dst} + 渲染 {len(SECTION_TO_FILE)} 个 sections/*.tex")
    print(f"[NOTE] mcm/diangong 模式: main.tex 内 TODO 段需手动改为 \\input{{sections/<sec>}}, 或直接编辑 main.tex 把 sections 内容粘贴进去")
    return main_dst


def fill_template(competition: str, workspace: Path, output_dir: Path,
                   prefer_pandoc: bool = True) -> tuple[Path, str]:
    """竞赛分发: 返回 (main_tex_path, engine)"""
    cfg = TEMPLATE_MAP.get(competition)
    if cfg is None:
        raise ValueError(f"未知 competition: {competition}; 支持 {list(TEMPLATE_MAP.keys())}")

    template_dir = cfg["template_dir"]
    if not template_dir.exists():
        raise FileNotFoundError(f"模板目录 {template_dir} 不存在")

    if cfg["mode"] == "cumcm_assemble":
        main_tex_path = fill_template_cumcm(workspace, template_dir, output_dir, prefer_pandoc)
    elif cfg["mode"] == "main_template":
        main_tex_path = fill_template_main(workspace, template_dir, output_dir,
                                            cfg["main_filename"], prefer_pandoc)
    else:
        raise ValueError(f"未知 template mode: {cfg['mode']}")

    return main_tex_path, cfg["engine"]


# ============================================================================
# 编译
# ============================================================================

def compile_pdf(tex_path: Path, engine: str = "xelatex", runs: int = 3) -> bool:
    workdir = tex_path.parent
    for i in range(runs):
        print(f"\n--- {engine} 第 {i+1}/{runs} 次 ---")
        result = subprocess.run(
            [engine, "-interaction=nonstopmode", "-halt-on-error", str(tex_path.name)],
            cwd=workdir, capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        if result.returncode != 0:
            print(f"[FAIL] {engine} 失败 (返回码 {result.returncode})")
            print(result.stdout[-2000:])
            print("--- stderr ---")
            print(result.stderr[-1000:])
            return False
    pdf_path = tex_path.with_suffix(".pdf")
    if pdf_path.exists():
        print(f"\n[OK] PDF 已生成: {pdf_path} ({pdf_path.stat().st_size // 1024} KB)")
        return True
    print(f"[FAIL] PDF 未生成")
    return False


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=str, required=True,
                        help="cwd/paper_workspace/ 目录, 含 01..10_*.md 节文件")
    parser.add_argument("--competition", type=str, default=None,
                        help="cumcm | mcm | diangong (默认从 decision_log 读, 缺失则 cumcm)")
    parser.add_argument("--decision-log", type=str, default=None,
                        help="可选: 指定 decision_log.json 路径用于自动检测 competition")
    parser.add_argument("--output-dir", type=str, default="paper_output")
    parser.add_argument("--no-pandoc", action="store_true",
                        help="禁用 pandoc, 直接用手工正则 (调试用)")
    parser.add_argument("--no-compile", action="store_true",
                        help="只填充模板, 不调用 LaTeX 引擎 (dry-run)")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    output_dir = Path(args.output_dir)

    if not workspace.exists():
        print(f"[FAIL] workspace {workspace} 不存在")
        return 1

    decision_log_path = Path(args.decision_log) if args.decision_log else (Path.cwd() / "state" / "decision_log.json")
    competition = resolve_competition(args.competition, decision_log_path)
    print(f"competition: {competition}")

    prefer_pandoc = not args.no_pandoc
    if prefer_pandoc and not has_pandoc():
        print("[WARN] pandoc 未安装, 自动回退手工正则。建议安装: https://pandoc.org/installing.html")

    try:
        tex_path, engine = fill_template(competition, workspace, output_dir, prefer_pandoc)
    except (ValueError, FileNotFoundError) as e:
        print(f"[FAIL] {e}")
        return 1

    if args.no_compile:
        print(f"[OK] dry-run 完成 (--no-compile). engine={engine}, tex={tex_path}")
        return 0

    return 0 if compile_pdf(tex_path, engine=engine, runs=3) else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
