"""
run_solver.py — Stage 5 子问题求解器自动跑 + 量级 sanity check (P1-11)

模式 1 — 直接跑代码 + 比对结果 JSON:
  python scripts/run_solver.py \
      --qi Q1 \
      --code cwd/results/Q1_solve.py \
      --expected cwd/state/Q1_expected.json \
      --results cwd/results/Q1_results.json \
      --timeout 120

  expected.json schema:
  {
    "objective":  {"min": 1e3, "max": 1e6, "unit": "元"},
    "x_star":     {"shape": [100], "dtype": "int", "min": 0, "max": 50},
    "solve_time_s": {"max": 120}
  }

  results.json (求解脚本必须写出, 可被本工具读):
  {
    "objective": 87234.5,
    "x_star":    [12, 0, 25, ...],
    "solve_time_s": 4.2
  }

模式 2 — 仅校验已有 results.json:
  python scripts/run_solver.py --qi Q1 --expected ... --results ...
  (--code 缺省时不执行代码, 仅做 range check)

退出码:
  0 = 全部 in-range, 写 issues=[] 入 decision_log
  1 = 有 out-of-range / shape 不符, 写 high-severity issues
  2 = 代码崩溃 / timeout (block)
  3 = 文件 / schema 错误

输出: 把 issues + actual 摘要写进
  decision_log.stages.5.sub_problems.<Qi>.actual_results
  decision_log.stages.5.sub_problems.<Qi>.sanity_check_status
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def shape_of(x):
    """递归测形状 (近似 numpy.shape)"""
    if isinstance(x, list):
        if not x:
            return [0]
        head = shape_of(x[0])
        return [len(x)] + head if isinstance(head, list) else [len(x)]
    return []


def check_field(name: str, expected: dict, actual) -> list[dict]:
    """
    单个字段 expected (dict) vs actual (任意), 返回 issues list (high-severity 表示 block)
    """
    issues: list[dict] = []

    # min / max (适用于 scalar 或 list 元素)
    lo = expected.get("min")
    hi = expected.get("max")
    if isinstance(actual, (int, float)):
        if lo is not None and actual < lo:
            issues.append({"severity": "high", "where": name,
                           "anti_pattern_id": "D3",
                           "fix": f"实际 {actual} < 下界 {lo}, 量级离谱, 重审建模或求解"})
        if hi is not None and actual > hi:
            issues.append({"severity": "high", "where": name,
                           "anti_pattern_id": "D3",
                           "fix": f"实际 {actual} > 上界 {hi}, 量级离谱, 重审建模或求解"})
    elif isinstance(actual, list):
        flat: list = []
        stack = [actual]
        while stack:
            t = stack.pop()
            for x in t:
                if isinstance(x, list):
                    stack.append(x)
                elif isinstance(x, (int, float)):
                    flat.append(x)
        if flat:
            mn, mx = min(flat), max(flat)
            if lo is not None and mn < lo:
                issues.append({"severity": "high", "where": name,
                               "anti_pattern_id": "D2",
                               "fix": f"min(elem)={mn} < {lo}, 越下界"})
            if hi is not None and mx > hi:
                issues.append({"severity": "high", "where": name,
                               "anti_pattern_id": "D2",
                               "fix": f"max(elem)={mx} > {hi}, 越上界"})

    # shape
    exp_shape = expected.get("shape")
    if exp_shape is not None:
        act_shape = shape_of(actual)
        if act_shape != exp_shape:
            issues.append({"severity": "high", "where": name,
                           "anti_pattern_id": "D2",
                           "fix": f"shape 实际 {act_shape}, 期望 {exp_shape}"})

    # dtype (best-effort, 仅 int / float / str)
    exp_dtype = expected.get("dtype")
    if exp_dtype is not None and isinstance(actual, (int, float)):
        if exp_dtype == "int" and not isinstance(actual, int):
            issues.append({"severity": "medium", "where": name,
                           "anti_pattern_id": "D2",
                           "fix": f"dtype 期望 int, 实际 {type(actual).__name__}"})

    return issues


def compare(expected: dict, actual: dict) -> tuple[list[dict], dict]:
    issues: list[dict] = []
    summary: dict = {}
    for k, exp in expected.items():
        if k.startswith("_"):
            continue
        if k not in actual:
            issues.append({"severity": "high", "where": k,
                           "anti_pattern_id": "D2",
                           "fix": f"results 缺少字段 {k}"})
            continue
        v = actual[k]
        issues.extend(check_field(k, exp, v))
        if isinstance(v, (int, float, str)):
            summary[k] = v
        else:
            summary[k] = {"shape": shape_of(v),
                          "preview": (v[:3] if isinstance(v, list) else str(v)[:100])}
    return issues, summary


def run_code(code_path: Path, timeout: int) -> tuple[int, str, str]:
    """跑求解器代码, 返回 (returncode, stdout, stderr)"""
    try:
        proc = subprocess.run(
            [sys.executable, str(code_path)],
            capture_output=True, text=True, timeout=timeout,
            cwd=code_path.parent,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"TIMEOUT after {timeout}s"


def update_decision_log(log_path: Path, qi: str, summary: dict,
                        issues: list[dict], status: str):
    if not log_path.exists():
        print(f"[WARN] {log_path} 不存在, 跳过 decision_log 注入", file=sys.stderr)
        return
    log = load_json(log_path)
    s5 = log.setdefault("stages", {}).setdefault("5", {})
    sub = s5.setdefault("sub_problems", {}).setdefault(qi, {})
    sub["actual_results"] = summary
    sub["sanity_check_status"] = status
    sub["sanity_issues"] = issues
    sub["sanity_ts"] = datetime.now().isoformat()
    log.setdefault("events", {}).setdefault("log", []).append({
        "type": "solver_sanity",
        "ts": datetime.now().isoformat(),
        "qi": qi,
        "status": status,
        "issues_count": len(issues),
    })
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qi", required=True, help="子问题 id, e.g. Q1")
    parser.add_argument("--code", default=None, help="求解脚本; 缺省则只校验 results")
    parser.add_argument("--expected", required=True, help="expected_range JSON 路径")
    parser.add_argument("--results", required=True, help="求解器写出的 results JSON")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--decision-log", default=None,
                        help="cwd/state/decision_log.json")
    args = parser.parse_args()

    expected_path = Path(args.expected)
    results_path = Path(args.results)

    if args.decision_log:
        log_path = Path(args.decision_log)
    elif os.environ.get("CUMCM_STATE_DIR"):
        log_path = Path(os.environ["CUMCM_STATE_DIR"]) / "decision_log.json"
    else:
        log_path = Path.cwd() / "state" / "decision_log.json"

    if not expected_path.exists():
        print(f"[FAIL] expected 文件不存在: {expected_path}")
        return 3

    expected = load_json(expected_path)

    if args.code:
        code_path = Path(args.code)
        if not code_path.exists():
            print(f"[FAIL] 代码不存在: {code_path}")
            return 3
        print(f"[RUN] {code_path} (timeout={args.timeout}s)")
        rc, out, err = run_code(code_path, args.timeout)
        print("--- stdout ---"); print(out[-2000:])
        if err:
            print("--- stderr ---"); print(err[-2000:])
        if rc == -1:
            update_decision_log(log_path, args.qi, {}, [{
                "severity": "high", "where": f"{args.qi} solver",
                "anti_pattern_id": "J3",
                "fix": f"求解超时 (>{args.timeout}s), 切换 fallback 模型或减规模"
            }], "timeout")
            return 2
        if rc != 0:
            update_decision_log(log_path, args.qi, {}, [{
                "severity": "high", "where": f"{args.qi} solver",
                "anti_pattern_id": "D2",
                "fix": f"求解器 returncode={rc}, 修复 stderr 报错再跑"
            }], "crashed")
            return 2

    if not results_path.exists():
        update_decision_log(log_path, args.qi, {}, [{
            "severity": "high", "where": f"{args.qi} results",
            "anti_pattern_id": "D2",
            "fix": f"求解器未写 results JSON ({results_path}), 加 json.dump 落盘"
        }], "no_results_file")
        print(f"[FAIL] results 不存在: {results_path}")
        return 1

    actual = load_json(results_path)
    issues, summary = compare(expected, actual)
    high = [i for i in issues if i.get("severity") == "high"]
    status = "ok" if not issues else ("block" if high else "warn")

    update_decision_log(log_path, args.qi, summary, issues, status)

    print(f"\n[{args.qi}] sanity status: {status}")
    print(f"  actual summary: {json.dumps(summary, ensure_ascii=False)[:500]}")
    if issues:
        for it in issues:
            print(f"  - [{it['severity']}] {it['where']}: {it['fix']}")
        return 0 if not high else 1
    print("  [OK] 全部字段命中 expected_range")
    return 0


if __name__ == "__main__":
    sys.exit(main())
