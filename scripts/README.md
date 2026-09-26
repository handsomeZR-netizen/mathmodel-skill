# Scripts 工具说明

这里的脚本分为两组：比赛过程中使用的运行时工具，以及维护资料库时才使用的离线工具。下列命令均假设当前目录是 skill 根目录；用户项目中的动态文件统一放在项目工作目录，不写回 skill。

## 运行时工具

### `init_workspace.py` — 工作区初始化（只创建、不覆盖）

Stage 0 拿到启动字段后由 agent 调用。它创建 `state/`、`results/`、`figures/`、`paper_workspace/`、`paper_output/`、`support_materials/`，从 `templates/shared/decision_log.json` 生成新状态，并写入竞赛、题号、队员数、截止时间、`started_at` 与一条 `workspace_init` 事件。

```bash
python scripts/init_workspace.py --competition cumcm --workspace /path/to/project
python scripts/init_workspace.py --competition mcm --workspace /path/to/project \
  --problem C --team-size 3 --hours-left 96 --problem-pdf /path/to/2027_MCM_C.pdf
python scripts/init_workspace.py --competition diangong --workspace /path/to/project \
  --problem 未公布 --deadline 2027-05-24T08:00+08:00 --json
```

- `state/decision_log.json` 已存在时**不写入任何内容**，只报告已保存的竞赛、阶段和模式；竞赛不一致或文件无法解析时以非零退出码失败。
- 题号按 `competitions/<comp>/topic_specs.json` 校验；题目未公布时传 `未公布`，保持 `letter=null`。
- `--deadline` 与 `--hours-left` 二选一；未传 `--year` 时取截止时间所在年份。
- 输出按剩余时间给出模式建议，但不会自动修改 `mode`；需要团队确认后再写入 events。

### `status.py` — 只读进度看板（“看进度”）

读取项目状态并输出：当前阶段、10 个阶段的最新 verdict 与分数、Stage 5 per-Qi 状态、规则/AI 台账/终审合规门、截止倒计时、按 SKILL.md 规则计算的模式建议，以及一条确定性的下一步。它从不修改状态文件。

```bash
python scripts/status.py --workspace /path/to/project             # 终端看板
python scripts/status.py --workspace /path/to/project --markdown  # 适合贴进对话
python scripts/status.py --decision-log /path/to/state/decision_log.json --json
```

未传路径时按 `MATHMODEL_STATE_DIR`、`CUMCM_STATE_DIR`、`<cwd>/state/decision_log.json` 的顺序解析。状态不存在或 `current_stage` 非法时以退出码 1 失败。

### `doctor.py` — 环境与包结构预检

在启动工作流或切换竞赛时运行。默认同时检查 skill 结构、竞赛包、JSON 配置和本地渲染工具；`--skip-tools` 适合 CI 或只做静态检查。

```bash
python scripts/doctor.py --competition cumcm --workspace /path/to/project
python scripts/doctor.py --competition mcm --skip-tools --json
python scripts/doctor.py --competition diangong --require-renderer --require-modeling
```

### `score_artifact.py` — L1 Critic 结果处理

校验 critique JSON、计算实际 verdict，并把阶段分数与迭代记录写入项目的 `state/decision_log.json`。

```bash
python scripts/score_artifact.py \
  --stage 5 \
  --critique /path/to/project/state/critique_v0.json \
  --decision-log /path/to/project/state/decision_log.json
```

不传 `--decision-log` 时，脚本按 `MATHMODEL_STATE_DIR`、兼容变量 `CUMCM_STATE_DIR`、最后 `<cwd>/state/decision_log.json` 的顺序解析路径。

所有子问完成后，可聚合 per-Qi 结果并把 `qi_status`、`review_qis`、`refine_qis` 与最终 verdict 原子写回 Stage 5：

```bash
python scripts/score_artifact.py \
  --mode aggregate_qi \
  --qi-results /path/to/project/state/qi_results.json \
  --decision-log /path/to/project/state/decision_log.json
```

### `extract_diff.py` — 定向修补辅助器

根据 Critic 指出的问题生成 section patch prompt，或应用已经生成的 section patch / unified diff。它的价值是缩小修改范围并保留已通过章节；实际节省量取决于论文和修补范围，不设固定比例。

```bash
# 生成定向修补 prompt
python scripts/extract_diff.py \
  --artifact /path/to/project/paper_workspace/06_models.md \
  --critique /path/to/project/state/critique_v0.json \
  --mode section \
  --output /path/to/project/state/refine_prompt.md

# 应用模型返回的 patch；--apply 模式不需要 --critique
python scripts/extract_diff.py \
  --artifact /path/to/project/paper_workspace/06_models.md \
  --apply /path/to/project/state/refine_patch.md \
  --mode section \
  > /path/to/project/paper_workspace/06_models_v1.md
```

### `render_paper.py` — Markdown 章节装配与 LaTeX 编译

把 `paper_workspace/` 中的编号 Markdown 章节装入所选竞赛的 `main.tex`。三类模板统一使用显式 section marker；正式编译要求 Pandoc 和对应 LaTeX 引擎，并在必需的 `01`–`10` 章节缺失、为空，或 marker 缺失、重复、未知时停止。内置简化转换器只用于 `--no-compile` 结构预检。

正式渲染还会检查提交元数据：CUMCM 要求最终题目和关键词，MCM/ICM 要求控制号、题号、题目和关键词，电工杯要求报名序号、题号、题目和关键词。CLI 参数优先于 `decision_log.paper_metadata`；`XXXX`、`X`、`keyword1` 等占位值会阻断编译。只有显式组合 `--allow-placeholders --no-compile` 才会生成带醒目标记的结构预览。

CUMCM 模板按 2026 电子论文基线提供 A4、四边 2.5 cm、第一页摘要、无目录、正文最多 30 页和匿名字段最小化等 guard；它是仓库原创装配模板，不是官方模板，仍须在 Stage 0 与 Stage 9 重新核对当届通知。

```bash
python scripts/render_paper.py \
  --workspace /path/to/project/paper_workspace \
  --competition cumcm \
  --decision-log /path/to/project/state/decision_log.json \
  --output-dir /path/to/project/paper_output

# 只检查模板装配，不编译 PDF
python scripts/render_paper.py \
  --workspace /path/to/project/paper_workspace \
  --competition mcm \
  --output-dir /path/to/project/paper_output \
  --no-compile \
  --allow-placeholders
```

### `render_ai_usage.py` — AI 使用记录导出

从 `decision_log.compliance.ai_usage` 生成竞赛要求的披露材料，并直接放到渲染器约定的位置。CUMCM 使用 AI 时输出到 `support_materials/AI工具使用详情.{md,pdf}`；显式未使用时只输出 `paper_workspace/AI工具未使用声明.md`，渲染器把它接在参考文献后。MCM 输出 `paper_workspace/11_ai_use_report.md`，且不重复模板提供的标题。CUMCM 的 PDF 生成依赖 ReportLab。

```bash
python scripts/render_ai_usage.py \
  --decision-log /path/to/project/state/decision_log.json \
  --competition cumcm \
  --paper-workspace /path/to/project/paper_workspace \
  --support-dir /path/to/project/support_materials

# 先只检查 Markdown 内容
python scripts/render_ai_usage.py \
  --decision-log /path/to/project/state/decision_log.json \
  --competition cumcm \
  --paper-workspace /path/to/project/paper_workspace \
  --support-dir /path/to/project/support_materials \
  --markdown-only
```

每条 AI 使用记录都必须含 `use_stage`，并完整记录 `query` + `output`，或为代码补全等非对话式工具提供 `disclosure`。`ai_usage: []` 只在团队明确核对“未使用”后填写；缺失或 `null` 会报错。

## 离线维护工具

这两个脚本用于维护样本资料，不应在比赛主流程中自动运行。先安装精简维护依赖：

```bash
python -m pip install -r scripts/requirements-maintenance.txt
python -m playwright install chromium  # 仅下载官方展廊页面时需要
```

### `download_cumcm_papers.py` — 官方展廊下载与 PDF 重建

当前下载器覆盖脚本内登记的 2023、2024 官方展廊页面。页面以图片形式展示论文，因此脚本使用 Playwright 发现详情页，再用 Pillow 重建 PDF。

```bash
python scripts/download_cumcm_papers.py \
  --papers-dir /path/to/cumcm-papers \
  --years 2023 2024
```

下载内容可能受站点结构、网络和来源授权影响；运行前应确认使用范围，并保留脚本生成的下载报告。

### `ingest_papers.py` — 可提取 PDF 的统计蒸馏

扫描指定目录中的 PDF，过滤无法提取足够文字的图片型文件，再生成描述性统计 Markdown。仓库记录了 91 份来源文件，其中 59 份满足当前提取条件；重新运行时以命令输出的“成功解析 / 文本可提取”计数为准。

```bash
python scripts/ingest_papers.py \
  --papers-dir /path/to/cumcm-papers \
  --output /path/to/empirical_distribution.md
```

生成值是样本子集的观察结果，不是官方评分线，也不会自动覆盖 `competitions/cumcm/empirical.json`。采用任何阈值前仍需人工审阅样本构成、提取误差和当年规则。

## 路径协议

| 类型 | 位置 | 覆盖方式 |
|---|---|---|
| skill 静态资源 | `<skill>/{references,templates,scripts,competitions}` | 不覆盖 |
| 项目状态 | `<project>/state/decision_log.json` | `--decision-log` 或 `MATHMODEL_STATE_DIR` |
| 项目产物 | `<project>/{results,figures,paper_workspace,paper_output}` | 通过各脚本参数指定 |

`<cwd>` 只是命令启动时的当前目录，不是一个应当原样创建的文件夹名。

## 测试 fixture

Critic schema 样本位于 `tests/fixtures/`：

- `test_critique_good.json`：有效的 stage-level critique。
- `test_critique_bad_keys.json`：包含不在白名单中的维度键，预期校验失败。

在临时项目目录运行写入型示例，避免修改仓库内的模板状态：

```bash
python scripts/score_artifact.py \
  --stage 1 \
  --critique tests/fixtures/test_critique_good.json \
  --decision-log /tmp/mathmodel-test/state/decision_log.json
```
