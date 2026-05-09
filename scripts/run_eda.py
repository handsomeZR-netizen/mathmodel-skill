"""
run_eda.py — Stage 2 强制 EDA 报告生成器 (P1-10)

功能:
  扫描 cwd/data/ 下的 .xlsx / .csv / .xls / .tsv, 生成 5 板块 EDA 报告
  (Schema / 缺失 / 分布与异常 / 相关性 / 数据-假设对账), 摘要回写
  decision_log.stages.2.eda_findings。

依赖: pandas, numpy, matplotlib, scipy.stats (skew/kurtosis/anderson)。
matplotlib 与 scipy 缺失时会跳过对应板块, 不会硬失败。

退出码:
  0 = 报告已写, eda_findings 已注入 decision_log
  1 = 数据目录为空 (题目无附件); 写空报告框架, 让 stage 2 用户手填
  2 = 数据目录不存在或不可读

用法:
  python scripts/run_eda.py --data-dir cwd/data/ --out cwd/eda_report.md \
        --decision-log cwd/state/decision_log.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def _require_pandas():
    try:
        import pandas as pd  # noqa: F401
    except ImportError:
        sys.stderr.write(
            "[FAIL] 需要 pandas. 请安装: pip install -r templates/requirements.txt\n"
            "       或: pip install pandas numpy scipy matplotlib\n"
        )
        sys.exit(2)


def load_dataframe(path: Path):
    import pandas as pd
    suf = path.suffix.lower()
    if suf in (".xlsx", ".xls"):
        return pd.read_excel(path)
    if suf == ".csv":
        return pd.read_csv(path)
    if suf == ".tsv":
        return pd.read_csv(path, sep="\t")
    return None


def scan_data_dir(data_dir: Path):
    """yield (path, df) for each readable tabular file"""
    if not data_dir.exists():
        return
    exts = (".xlsx", ".xls", ".csv", ".tsv")
    for p in sorted(data_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in exts:
            try:
                df = load_dataframe(p)
                if df is not None and len(df.columns) > 0:
                    yield p, df
            except Exception as e:
                print(f"[WARN] 无法读取 {p}: {e}", file=sys.stderr)


def schema_block(name: str, df) -> str:
    lines = [f"### 附件 `{name}`",
             f"- 行数: {len(df)}, 列数: {len(df.columns)}",
             f"- 列名: {list(df.columns)}",
             f"- dtypes:"]
    for col, dt in df.dtypes.items():
        lines.append(f"  - `{col}`: {dt}")
    return "\n".join(lines)


def missing_block(name: str, df, findings: dict) -> str:
    miss = df.isnull().sum()
    pct = (miss / max(len(df), 1)).round(4)
    lines = [f"### 附件 `{name}`"]
    head = "| 列 | 缺失数 | 缺失率 | 提议处理 |\n|---|---|---|---|"
    lines.append(head)
    for col in df.columns:
        p = float(pct[col])
        if p == 0:
            sugg = "—"
        elif p < 0.05:
            sugg = "行删除或前向填充"
        elif p < 0.30:
            sugg = "均值/中位数/KNN 插补"
        else:
            sugg = "⚠ 列删除或外部数据补"
        lines.append(f"| {col} | {int(miss[col])} | {p:.2%} | {sugg} |")
        findings.setdefault("missing_pct_per_col", {})[f"{name}.{col}"] = p
    return "\n".join(lines)


def distribution_block(name: str, df, findings: dict) -> str:
    import numpy as np
    try:
        from scipy.stats import skew, kurtosis, anderson
        have_scipy = True
    except Exception:
        have_scipy = False

    lines = [f"### 附件 `{name}`",
             "| 列 | mean | std | min | p25 | p50 | p75 | max | skew | kurt | 异常>3σ | 分布备注 |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]

    num = df.select_dtypes(include=["number"])
    for col in num.columns:
        s = num[col].dropna()
        if len(s) == 0:
            continue
        mu = float(s.mean()); sd = float(s.std()); mn = float(s.min()); mx = float(s.max())
        q25, q50, q75 = (float(s.quantile(q)) for q in (0.25, 0.5, 0.75))
        sk = float(skew(s)) if have_scipy else float("nan")
        kt = float(kurtosis(s)) if have_scipy else float("nan")
        out = int(((s - mu).abs() > 3 * sd).sum()) if sd > 0 else 0
        note = ""
        if have_scipy and len(s) >= 8:
            try:
                try:
                    ad = anderson(s, dist="norm", method="interpolate")
                except TypeError:
                    ad = anderson(s, dist="norm")
                note = "近似正态" if ad.statistic < ad.critical_values[2] else "非正态"
            except Exception:
                note = ""
        if abs(sk) > 1:
            note = (note + " 重偏" if note else "重偏")
        if abs(kt) > 3:
            note = (note + " 重尾" if note else "重尾")

        lines.append(
            f"| {col} | {mu:.3g} | {sd:.3g} | {mn:.3g} | {q25:.3g} | {q50:.3g} | "
            f"{q75:.3g} | {mx:.3g} | {sk:.2f} | {kt:.2f} | {out} | {note} |"
        )
        findings.setdefault("outliers_count_per_col", {})[f"{name}.{col}"] = out
        findings.setdefault("distribution_summary", {})[f"{name}.{col}"] = (
            f"mean={mu:.3g}, std={sd:.3g}, skew={sk:.2f}, kurt={kt:.2f}, {note}"
        )

    if not have_scipy:
        lines.append("\n> scipy 缺失, 跳过 skew/kurtosis/AD 检验。")
    return "\n".join(lines)


def correlation_block(name: str, df, findings: dict, fig_dir: Path) -> str:
    num = df.select_dtypes(include=["number"])
    if num.shape[1] < 2:
        return f"### 附件 `{name}`\n- 数值列 < 2, 跳过相关性。"
    corr_p = num.corr(method="pearson")
    corr_s = num.corr(method="spearman")

    lines = [f"### 附件 `{name}`",
             "高相关对 (|Pearson| > 0.7):"]
    pairs = []
    cols = list(num.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = float(corr_p.iloc[i, j])
            if abs(r) >= 0.7:
                pairs.append((cols[i], cols[j], r))
                findings.setdefault("key_correlations", []).append(
                    {"file": name, "a": cols[i], "b": cols[j], "r": round(r, 3),
                     "method": "pearson"}
                )
    if not pairs:
        lines.append("- 无 (|r|<0.7), 多重共线性风险低")
    else:
        for a, b, r in pairs:
            lines.append(f"- `{a}` ↔ `{b}`: r = {r:+.2f}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig_dir.mkdir(parents=True, exist_ok=True)
        fig_path = fig_dir / f"corr_heatmap_{Path(name).stem}.png"
        fig, ax = plt.subplots(figsize=(min(1 + 0.3 * len(cols), 12),
                                        min(1 + 0.3 * len(cols), 12)))
        im = ax.imshow(corr_p.values, vmin=-1, vmax=1, cmap="RdBu_r")
        ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, rotation=60, ha="right", fontsize=7)
        ax.set_yticks(range(len(cols))); ax.set_yticklabels(cols, fontsize=7)
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        ax.set_title(f"{name} — Pearson")
        plt.tight_layout()
        fig.savefig(fig_path, dpi=150)
        plt.close(fig)
        lines.append(f"\n热力图: `{fig_path}`")
    except Exception as e:
        lines.append(f"\n> matplotlib 不可用, 跳过热力图: {e}")

    return "\n".join(lines)


def alignment_block(findings: dict) -> str:
    """生成空对账表 (用户手填), 只列出发现的列"""
    cols = sorted(findings.get("missing_pct_per_col", {}).keys())
    lines = [
        "对账每个 stage 2 全局变量表中的变量, 标注来源。**用户手填**:",
        "",
        "| 变量 (stage 2 符号) | 来源类型 | 数据列 / 假设 / 外部参考 | 完整性 / 缺失率 | 备注 |",
        "|---|---|---|---|---|",
        "| _x_i_ | 决策变量 | 无需数据 | n/a | |",
    ]
    for c in cols[:5]:
        lines.append(f"| (待映射) | 数据 | `{c}` | 见上表 | |")
    lines.append("| _α_ | 假设 | 文献 [?] | n/a | 需要 stage 4 假设支撑 |")
    lines.append("")
    lines.append("> ⚠ stage 2 退出条件: 此表所有变量必须三分类 (数据 / 假设 / 外部参考), 无未归类。")
    return "\n".join(lines)


def update_decision_log(log_path: Path, findings: dict, report_path: Path):
    if not log_path.exists():
        print(f"[WARN] {log_path} 不存在, 跳过 decision_log 注入", file=sys.stderr)
        return False
    with open(log_path, "r", encoding="utf-8") as f:
        log = json.load(f)
    s2 = log.setdefault("stages", {}).setdefault("2", {})
    s2["eda_report_path"] = str(report_path)
    s2["eda_findings"] = {
        **{k: v for k, v in s2.get("eda_findings", {}).items() if k.startswith("_")},
        **findings,
        "_ts": datetime.now().isoformat(),
    }
    log.setdefault("events", {}).setdefault("log", []).append({
        "type": "eda_done",
        "ts": datetime.now().isoformat(),
        "report_path": str(report_path),
        "files_scanned": len(findings.get("missing_pct_per_col", {})),
    })
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, help="cwd/data/")
    parser.add_argument("--out", required=True, help="EDA 报告 markdown 输出路径")
    parser.add_argument("--decision-log", default=None,
                        help="cwd/state/decision_log.json; 不写则按 CUMCM_STATE_DIR / cwd 推断")
    parser.add_argument("--fig-dir", default=None,
                        help="图表输出目录, 默认 <out 同目录>/eda_figures/")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out_path = Path(args.out)
    fig_dir = Path(args.fig_dir) if args.fig_dir else out_path.parent / "eda_figures"

    if args.decision_log:
        log_path = Path(args.decision_log)
    elif os.environ.get("CUMCM_STATE_DIR"):
        log_path = Path(os.environ["CUMCM_STATE_DIR"]) / "decision_log.json"
    else:
        log_path = Path.cwd() / "state" / "decision_log.json"

    if not data_dir.exists():
        print(f"[FAIL] data 目录 {data_dir} 不存在", file=sys.stderr)
        return 2

    _require_pandas()
    files = list(scan_data_dir(data_dir))
    findings: dict = {
        "missing_pct_per_col": {},
        "outliers_count_per_col": {},
        "key_correlations": [],
        "distribution_summary": {},
        "data_assumption_alignment": {},
    }

    sections = ["# EDA 报告 (stage 2)",
                f"- 生成时间: {datetime.now().isoformat()}",
                f"- 扫描目录: `{data_dir}`",
                f"- 文件数: {len(files)}",
                ""]

    if not files:
        sections += [
            "## ⚠ 题目无表格附件",
            "",
            "本题在 data/ 下未发现 .xlsx/.csv/.xls/.tsv。仍需提交 EDA 简版:",
            "- 题面常数表 (含单位)",
            "- 几何参数表 (若几何题)",
            "- 与 stage 2 全局变量表对账",
            "",
            "请手填本节, 至少 1 页。",
        ]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(sections) + "\n", encoding="utf-8")
        update_decision_log(log_path, findings, out_path)
        return 1

    sec_schema = ["## 1. Schema"]
    sec_missing = ["## 2. 缺失值"]
    sec_dist = ["## 3. 分布与异常"]
    sec_corr = ["## 4. 相关性 / 多重共线性"]

    for path, df in files:
        name = path.name
        sec_schema.append(schema_block(name, df))
        sec_missing.append(missing_block(name, df, findings))
        sec_dist.append(distribution_block(name, df, findings))
        sec_corr.append(correlation_block(name, df, findings, fig_dir))

    sec_align = ["## 5. 数据 ↔ 变量/假设 对账", alignment_block(findings)]

    sections += sec_schema + [""] + sec_missing + [""] + sec_dist + [""]
    sections += sec_corr + [""] + sec_align + [""]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(sections) + "\n", encoding="utf-8")
    print(f"[OK] EDA 报告已写: {out_path}")

    if update_decision_log(log_path, findings, out_path):
        print(f"[OK] decision_log.stages.2.eda_findings 已注入: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
