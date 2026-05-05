"""
render_paper.py — 把 markdown 中间产物 + cumcmthesis 模板 → 最终 PDF

功能:
1. 读取 stage 8 各节 markdown 产出
2. 用 pandoc 转 LaTeX (优先), 失败回退手工正则
3. 写入 cumcmthesis 模板对应位置
4. 调用 xelatex 三编

修复点 (vs 原版):
- 原 md_to_tex 只处理 5 类 markdown 标记, 国赛必备的表格/数学公式块/图片/列表/代码块完全漏处理
- 现优先用 pandoc (覆盖完整 markdown spec), 备用模式补全 5 类正则

用法:
    python scripts/render_paper.py --workspace cwd/paper_workspace/ --output cwd/paper_output/
"""

import argparse
import re
import subprocess
import shutil
from pathlib import Path


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


def has_pandoc() -> bool:
    try:
        r = subprocess.run(["pandoc", "--version"], capture_output=True, text=True)
        return r.returncode == 0
    except FileNotFoundError:
        return False


def md_to_tex_pandoc(md_text: str) -> str:
    """
    优先方案: pandoc 处理完整 markdown (含表格/数学公式/图片/列表/代码块)
    """
    r = subprocess.run(
        ["pandoc", "-f", "markdown+tex_math_dollars+pipe_tables+raw_tex",
         "-t", "latex", "--no-highlight"],
        input=md_text, capture_output=True, text=True, encoding="utf-8"
    )
    if r.returncode != 0:
        raise RuntimeError(f"pandoc 失败: {r.stderr}")
    return r.stdout


def md_to_tex_fallback(md_text: str) -> str:
    """
    回退方案: 手工正则补全 5 类 markdown → LaTeX 转换
    """
    tex = md_text

    # 1. 代码块 ```lang ... ``` → lstlisting (要先于其他, 避免内部被改)
    def replace_code_block(m):
        lang = m.group(1) or "text"
        body = m.group(2)
        return f"\\begin{{lstlisting}}[language={lang}]\n{body}\n\\end{{lstlisting}}"
    tex = re.sub(r"```(\w+)?\n(.*?)\n```", replace_code_block, tex, flags=re.DOTALL)

    # 2. 数学公式块 $$...$$ → equation/align
    def replace_eq(m):
        body = m.group(1).strip()
        if "\\\\" in body or "&" in body:
            return f"\\begin{{align}}\n{body}\n\\end{{align}}"
        return f"\\begin{{equation}}\n{body}\n\\end{{equation}}"
    tex = re.sub(r"\$\$(.+?)\$\$", replace_eq, tex, flags=re.DOTALL)

    # 3. 图片 ![alt](path) → figure
    def replace_img(m):
        alt = m.group(1)
        path = m.group(2)
        return (f"\\begin{{figure}}[H]\n\\centering\n"
                f"\\includegraphics[width=0.8\\textwidth]{{{path}}}\n"
                f"\\caption{{{alt}}}\n\\end{{figure}}")
    tex = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_img, tex)

    # 4. 表格 (markdown pipe table) → booktabs
    def replace_table(m):
        rows = [r.strip() for r in m.group(0).splitlines() if r.strip()]
        if len(rows) < 2:
            return m.group(0)
        # 第一行 header, 第二行 separator (---), 其余 data
        cells = [r.strip("|").split("|") for r in rows]
        cells = [[c.strip() for c in row] for row in cells]
        header = cells[0]
        data = cells[2:] if len(cells) > 2 else []
        n_cols = len(header)
        col_spec = "l" * n_cols
        out = [f"\\begin{{table}}[H]\n\\centering"]
        out.append(f"\\begin{{tabular}}{{{col_spec}}}\n\\toprule")
        out.append(" & ".join(header) + " \\\\")
        out.append("\\midrule")
        for row in data:
            out.append(" & ".join(row) + " \\\\")
        out.append("\\bottomrule\n\\end{tabular}\n\\end{table}")
        return "\n".join(out)
    tex = re.sub(r"^\|.+\|\s*$\n^\|[-:\s|]+\|\s*$\n(?:^\|.+\|\s*$\n?)+",
                  replace_table, tex, flags=re.MULTILINE)

    # 5. 列表 (numbered + bulleted)
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

    # 6. 标题 (放最后, 避免误伤其他)
    tex = re.sub(r"^# (.+)$", r"\\section{\1}", tex, flags=re.MULTILINE)
    tex = re.sub(r"^## (.+)$", r"\\subsection{\1}", tex, flags=re.MULTILINE)
    tex = re.sub(r"^### (.+)$", r"\\subsubsection{\1}", tex, flags=re.MULTILINE)

    # 7. 行内格式
    tex = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", tex)
    tex = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\\textit{\1}", tex)
    tex = re.sub(r"`([^`]+?)`", r"\\texttt{\1}", tex)
    tex = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", tex)

    return tex


def md_to_tex(md_text: str, prefer_pandoc: bool = True) -> str:
    """选择转换器 — 优先 pandoc, 失败回退手工正则"""
    if prefer_pandoc and has_pandoc():
        try:
            return md_to_tex_pandoc(md_text)
        except RuntimeError as e:
            print(f"⚠ pandoc 失败 ({e}), 回退手工正则")
    return md_to_tex_fallback(md_text)


def fill_template(workspace: Path, template_dir: Path, output_dir: Path,
                   prefer_pandoc: bool = True) -> Path:
    """组装最终 .tex"""
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(template_dir / "cumcmthesis.cls", output_dir)
    if (template_dir / "figures").exists():
        shutil.copytree(template_dir / "figures", output_dir / "figures",
                         dirs_exist_ok=True)
    # 复制用户工作目录的 figures (如果有)
    if (workspace.parent / "figures").exists():
        shutil.copytree(workspace.parent / "figures", output_dir / "figures",
                         dirs_exist_ok=True)

    tex_parts = {}
    for sec, fname in SECTION_TO_FILE.items():
        md_path = workspace / fname
        if md_path.exists():
            tex_parts[sec] = md_to_tex(md_path.read_text(encoding="utf-8"), prefer_pandoc)
        else:
            print(f"⚠ 缺失 {fname}, 该节将留空")
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
    print(f"✅ 已生成 {main_tex_path}")
    return main_tex_path


def compile_pdf(tex_path: Path, runs: int = 3) -> bool:
    """xelatex 三编"""
    workdir = tex_path.parent
    for i in range(runs):
        print(f"\n--- xelatex 第 {i+1}/{runs} 次 ---")
        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", str(tex_path.name)],
            cwd=workdir, capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        if result.returncode != 0:
            print(f"❌ xelatex 失败 (返回码 {result.returncode})")
            print(result.stdout[-2000:])
            print("--- stderr ---")
            print(result.stderr[-1000:])
            return False
    pdf_path = tex_path.with_suffix(".pdf")
    if pdf_path.exists():
        print(f"\n✅ PDF 已生成: {pdf_path} ({pdf_path.stat().st_size // 1024} KB)")
        return True
    print(f"❌ PDF 未生成")
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=str, required=True)
    parser.add_argument("--template-dir", type=str, default="templates/cumcmthesis")
    parser.add_argument("--output-dir", type=str, default="paper_output")
    parser.add_argument("--no-pandoc", action="store_true",
                        help="禁用 pandoc, 直接用手工正则 (调试用)")
    parser.add_argument("--no-compile", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    template_dir = Path(args.template_dir)
    output_dir = Path(args.output_dir)

    if not workspace.exists():
        print(f"❌ workspace {workspace} 不存在")
        return 1
    if not template_dir.exists():
        print(f"❌ template_dir {template_dir} 不存在 (先 git clone latexstudio/cumcmthesis)")
        return 1

    prefer_pandoc = not args.no_pandoc
    if prefer_pandoc and not has_pandoc():
        print("⚠ pandoc 未安装, 自动回退手工正则。建议安装: https://pandoc.org/installing.html")

    tex_path = fill_template(workspace, template_dir, output_dir, prefer_pandoc)

    if args.no_compile:
        print("跳过编译 (--no-compile)")
        return 0

    return 0 if compile_pdf(tex_path, runs=3) else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
