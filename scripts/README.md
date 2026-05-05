# Scripts 工具说明

本目录的 4 个脚本按"运行时" vs "离线一次性"分两类。

---

## 运行时脚本 (各 stage 调用)

### `score_artifact.py` — L1 Critic 输出处理
**调用时机**: 每个 stage 结尾
**输入**: critique JSON (Claude L1 critic 输出) + stage_id
**输出**: 写入 `cwd/state/decision_log.json` 的 scores/iterations 字段, 决定下一步 (next_stage / section_patch / carryover / halt)

```bash
python scripts/score_artifact.py --stage 5 --critique state/critique_v0.json
# 路径协议: 默认 cwd/state/decision_log.json, 可用 CUMCM_STATE_DIR env var 覆盖
```

### `extract_diff.py` — Section-level patch 生成器
**调用时机**: L1 verdict == "refine" 时
**输入**: artifact 路径 + critique JSON
**输出**: section-level patch 精修 prompt (省 60% token vs 重生成全文)

```bash
# 生成 prompt
python scripts/extract_diff.py --artifact a.md --critique c.json --mode section --output prompt.txt
# 应用 LLM 返回的 patch
python scripts/extract_diff.py --artifact a.md --apply patch.txt --mode section > a_v1.md
```

### `render_paper.py` — Markdown → cumcmthesis LaTeX → PDF
**调用时机**: stage 8 末尾 / stage 9 编译终稿
**输入**: 含 10 个 .md 章节文件的 workspace 目录
**输出**: paper.pdf (xelatex 三编)

```bash
python scripts/render_paper.py --workspace cwd/paper_workspace/ --output-dir cwd/paper_output/
# 优先用 pandoc (需独立安装), 失败回退手工正则
```

---

## 离线一次性脚本 (skill 维护期使用, 不在运行时跑)

### `ingest_papers.py` — 91 篇 PDF 离线烘焙 → empirical_distribution.md
**调用时机**: skill 安装后一次性运行 / 添加新 PDF 后增量更新
**输入**: `references/papers/` 下 91 篇真国赛 PDF
**输出**: `references/empirical_distribution.md` (字数/章节/图表/公式实测分位数)

```bash
python scripts/ingest_papers.py --papers-dir references/papers/ --output references/empirical_distribution.md
```

烘焙后的 markdown 在运行时被 L1 critic 读取, 评摘要字数等"硬阈值维度"时引用实测 p25/p50/p75 而非估计值。

---

## 路径协议总览

| 类型 | 位置 | env var 覆盖 |
|------|------|-------------|
| skill 内静态资源 | `<skill>/{references, templates, scripts}` | 无 |
| 用户 state | `cwd/state/decision_log.json` | `CUMCM_STATE_DIR` |
| 用户产物 | `cwd/{results, figures, paper_workspace}` | 无 (固定) |

`cwd` = Claude Code 启动时的工作目录 (用户的项目目录)。
`<skill>` = skill 安装目录 (即本 README 所在目录的父目录)。

---

## 单元测试 fixture

L1 critic schema 验证的测试样本在 `<skill>/tests/fixtures/`:
- `test_critique_good.json` — 应通过校验 (verdict=pass)
- `test_critique_bad_keys.json` — 应触发 dim key 白名单 FAIL

```bash
PYTHONIOENCODING=utf-8 python scripts/score_artifact.py --stage 1 \
    --critique tests/fixtures/test_critique_good.json
```
