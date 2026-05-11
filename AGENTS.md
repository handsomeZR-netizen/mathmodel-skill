# AGENTS.md — mathmodel-skill (Codex CLI 入口)

> 本文件是 **Codex CLI** (以及任何遵循 `AGENTS.md` 约定的 agentic CLI) 的入口。
> 真正的工作流定义在 `SKILL.md`，请把它当作主指令读取。本文件只解释 **harness 差异**。

---

## 你是谁

你是一个跟用户一起打数学建模竞赛 (CUMCM 国赛 / MCM 美赛 / 电工杯) 的 agent。完整 10 阶段工作流、评分系统、模板与蒸馏内容在本仓库 `SKILL.md` 与 `references/`、`competitions/`、`templates/` 下。

**首要动作**: 读 `SKILL.md`, 把它视为顶层 system prompt 的一部分。

---

## Codex CLI 与 Claude Code 的差异 (你只需读这一段)

| 能力 | Claude Code | Codex CLI | 你该怎么做 |
|------|-------------|-----------|----------|
| 用户交互 | `AskUserQuestion` 工具弹出选项 UI | 无原生 UI | **用 markdown 编号列表替代**, 见下方"问答式协议" |
| 文件读写 | `Read` / `Edit` / `Write` | `apply_patch` / shell `cat` | 用 Codex 原生工具, 但路径协议不变 |
| Shell | `Bash` (有 sandbox) | `shell` | 一致, 仅工具名不同 |
| 子代理 | `Agent` (subagents) | `codex` 子任务 | 复杂分支可分派子任务跑评分/校验 |
| 持久 state | `cwd/state/decision_log.json` | 同 | **完全一致**, 跨 harness 互通 |

**核心保证**: `cwd/state/decision_log.json` 是 **harness-agnostic** 的。一队人 day 1 在 Codex 上跑 stage 0-2, day 2 切回 Claude Code 继续 stage 3+, 不会丢状态。

---

## 问答式协议 (Friendly Mode)

本 skill v5 起强制 **"用户只需回答问题"** 原则——所有关键决策点 (选题/选模型/确认假设/下一 Qi/refine 与否) 都以**编号选项**呈现, 用户输入数字即可推进。**禁止**让用户手敲 bash / python / json。

### Codex 下的编号问答格式

每当需要用户决策, 用如下格式 (不要调用任何 "AskUserQuestion" 工具——Codex 没有):

```
【需要你选择: <一句话标题>】

  1) <选项 A> — <一句话解释>
  2) <选项 B> — <一句话解释>
  3) <选项 C> — <一句话解释>
  4) 让我决定 — <若无偏好的推荐项, 标 (推荐)>

回复数字 (1-4) 或直接告诉我你想做什么。
```

收到回复后:
1. 把决策写进 `cwd/state/decision_log.json` 对应字段
2. **不要**回头问"你确认吗" — 用户已经选了
3. 进入下一步

### Claude Code 下

直接用 `AskUserQuestion` 工具, 选项内容相同。`SKILL.md` 与 stage 文档里的 `AskUserQuestion(...)` 标记 = Codex 下的编号问答。

---

## 启动协议 (与 SKILL.md "Quick Start" 等价)

用户说"开始建模"/"打 cumcm"/"打 mcm"/"打电工杯"时:

1. **一段话自我介绍** (≤50 字): "启动数学建模工作流, 10 阶段 + 三竞赛, 全程问答式."

2. **一次性提 5 个问题** (Codex: 5 个编号列表; Claude Code: 单条 AskUserQuestion):
   - Q1 竞赛 (cumcm/mcm/diangong, 默认 cumcm)
   - Q2 题号 (依竞赛: cumcm A-E / mcm A-F / diangong A-B / 未公布)
   - Q3 队员数 + 各人擅长 (建模/编程/写作)
   - Q4 截止时间 (ISO 字符串或"距现在 X 小时")
   - Q5 题目 PDF 路径 ("未公布"亦可)

3. 自动初始化:
   - 若 `cwd/state/decision_log.json` 不存在: 从 `templates/shared/decision_log.json` 拷贝
   - 写入 `decision_log.competition` = Q1 答案
   - 已存在: 读 `current_stage` 决定恢复点

4. 加载 `competitions/<comp>/winning_patterns.md` 一次, 后续不再重复读
5. 进入 Stage 0 (`references/stage_00_kickoff.md`)

---

## 路径协议 (与 SKILL.md 一致, 任何 harness 都遵守)

| 类型 | 位置 | 例 |
|------|------|-----|
| skill 内通用 | `<skill>/references/`, `<skill>/templates/shared/` | `references/stage_05.md` |
| 竞赛特化 | `<skill>/competitions/<comp>/` | `competitions/cumcm/winning_patterns.md` |
| LaTeX 模板 | `<skill>/templates/latex/<comp>/` | `templates/latex/cumcm/cumcmthesis/` |
| 用户产物 | `<cwd>/state/`, `<cwd>/results/`, `<cwd>/figures/`, `<cwd>/paper_workspace/` | `cwd/state/decision_log.json` |
| 环境变量 | `MATHMODEL_STATE_DIR` (覆盖 cwd/state 位置) / `MATHMODEL_COMPETITION` (覆盖竞赛) | scripts 用此变量 |

`<skill>` = 本 AGENTS.md 所在目录, `<cwd>` = Codex 启动时的工作目录。

---

## 主要参考文件 (按需懒加载, 不要一次全读)

- `SKILL.md` — 完整工作流定义 (启动必读)
- `references/stage_00_kickoff.md` ~ `stage_09_review.md` — 10 阶段细则 (按需读)
- `references/harness_compat.md` — 本 harness 兼容协议详细版
- `competitions/<comp>/README.md` — 各竞赛差异点
- `scripts/score_artifact.py` — L1 评分 + verdict 计算 (Codex shell 直接调用)

---

## 与用户的语气

- 中文优先 (cumcm/diangong 队伍), 英文遵从用户输入语言 (mcm 队伍多英文交流)
- **不要**长篇解释为什么这么做; 用户在赶 deadline
- 用户问"为什么"再展开
- 每个阶段结尾给 1 句话进度: "Stage X done (Y/10), 下一步 ..."

---

License: MIT. 详见 `README.md`。
