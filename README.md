# mathmodel-skill

> 面向 CUMCM (国赛) / MCM·ICM (美赛) / 电工杯 三类数学建模竞赛的 10 阶段工程化流程。带 4 层反馈、跨阶段一致性回检、终局多视角评审、题型差异化加权、实测分位锚定打分。Claude Code skill 形式分发。

[![Skill](https://img.shields.io/badge/Claude%20Code-Skill-FF6B35)](https://docs.claude.com/en/docs/claude-code/overview)
[![Stages](https://img.shields.io/badge/stages-10-blue)](./SKILL.md)
[![Feedback Layers](https://img.shields.io/badge/feedback%20layers-4-green)](./references/feedback_layer1_critic.md)
[![Modes](https://img.shields.io/badge/modes-fast%20%7C%20standard%20%7C%20championship-9cf)](./SKILL.md)
[![Competitions](https://img.shields.io/badge/competitions-CUMCM%20%7C%20MCM%20%7C%20Diangong-orange)](./competitions/)
[![Distilled From](https://img.shields.io/badge/CUMCM%20baked-91%20papers%20%282023--2025%29-orange)](./competitions/cumcm/empirical.json)
[![MCM Diangong](https://img.shields.io/badge/MCM%20%26%20Diangong-seed%20v0.1-yellow)](./competitions/mcm/README.md)
[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](./templates/shared/requirements.txt)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](#license)

---

## 这是什么

数学建模竞赛是 3-4 天完成 1 篇 25-40 页论文的紧迫工程, 流程从选题、建模、求解、灵敏度到写作很容易在某一环悄悄崩。这套 Claude Code skill 把每个阶段的检查项、典型反模式、跨阶段一致性约束固化下来, 让大模型按固定流程跟使用者一起走, 减少返工。

它不替选题、不替建模、不保证拿奖。**作用是把节奏卡住, 把容易忘的细节固化, 把别人论文里反复出现的句式与命名提取出来供模仿。**

蒸馏内容来源:
- CUMCM: 91 篇真国赛 2023-2025 获奖论文自动烘焙 (`empirical.json` 含 11 维 p25/p50/p75 实测分位)
- MCM/ICM: 基于 COMAP 公开 scoring rubric + Outstanding Winner 公开模式手写, **seed v0.1**
- 电工杯: 基于历年题量 + 公开评审标准估算, **seed v0.1**

---

## 支持的竞赛

| 竞赛 | 时长 | 语言 | LaTeX | 子问数 | 数据状态 |
|------|------|------|-------|--------|---------|
| **CUMCM 国赛** | 72h | 中文 | xelatex / cumcmthesis | 3-5 | stable (91 篇真烘焙) |
| **MCM/ICM 美赛** | 96h | English | pdflatex | 3-6 | seed v0.1 (公开评审标准 + 教材共识) |
| **电工杯** | 72h | 中文 | xelatex / ctex | 6-8 | seed v0.1 (历年题量估算) |

切换方式: stage 0 kickoff 第一问选竞赛 → 自动写入 `decision_log.competition` → 后续阶段从 `competitions/<comp>/` 加载对应 winning_patterns / phrase_bank / anti_patterns / abstract_template / paper_skeleton。

---

## 怎么用

放到 Claude Code 的 skill 目录下:

```bash
git clone https://github.com/handsomeZR-netizen/mathmodel-skill.git ~/.claude/skills/mathmodel-skill
pip install -r ~/.claude/skills/mathmodel-skill/templates/shared/requirements.txt
```

跟 Claude 说"开始建模"或"打 mcm"。第一次会问 5 个问题 (竞赛、题号、队员、截止、PDF), 然后从 Stage 0 开始走。

---

## 结构

```
SKILL.md                       # 入口, 三竞赛矩阵 + 加载协议 + verdict 定义
README.md                      # 当前文件
competitions/                  # 竞赛特化层
  cumcm/                       # 91 篇真烘焙: empirical.json + 蒸馏 markdown
    winning_patterns.md
    phrase_bank.md
    anti_patterns.md            # 32 条
    distilled_*.md              # 4 份蒸馏: 段落 / 命名 / 结构 / 格式
    empirical.json              # p25/p50/p75 进入 L1 critic prompt
    abstract_template.md        # 5 段式 + 完整示例
    paper_skeleton.md           # 22-25 页骨架
    rubric_overlay.json         # 国赛特化 dim
    topic_specs.json            # A-E + task_type 映射
  mcm/                         # SEED v0.1 - 1-page summary + Letter
    (同结构, 加 SEED 标记)
  diangong/                    # SEED v0.1 - 工程导向, 6-8 子问
    (同结构, 加 SEED 标记)
references/                    # 通用层 (跨竞赛共享)
  stage_00 ~ stage_09           # 10 阶段细则 (含 YAML frontmatter)
  feedback_layer1 ~ 4           # 自评 / 跨阶段回检 / 5 视角 panel / 防 gaming
  rubrics.md                    # 评分量表 (与 SKILL.md verdict 三处统一)
  model_catalog.md              # 60+ 模型按 10 类 + 历年题速查
templates/
  latex/{cumcm,mcm,diangong}/   # 各竞赛 LaTeX 模板
  shared/                       # 跨竞赛通用
    decision_log.json           # 跨阶段状态 schema (含 v3.0 三新字段)
    assumption_table.md
    notation_table.md
    sensitivity_table.md
    code_starter/               # Python 起手代码 (优化/预测/评价/分类/仿真)
    requirements.txt
config/
  dim_weights.json              # 三竞赛 × 题型 × stage × dim → 权重表
scripts/
  score_artifact.py             # L1 评分 + verdict 重算 + empirical 注入 + per-Qi 聚合 + 题型加权
  extract_diff.py               # section-level patch 精修 (省 60% token)
  render_paper.py               # md → tex → pdf 三竞赛分支 (xelatex/pdflatex)
  ingest_papers.py              # PDF 烘焙 (cumcm 蒸馏后已存档; 后续 mcm/diangong 可用)
tests/fixtures/                 # score_artifact 单元测试样本
```

---

## 设计选择

- **10 阶段 / 4 反馈层 / 3 模式 / 3 竞赛 正交组合**: 每个轴向独立, 组合矩阵 ≥ 36 种行为. 三竞赛切换不影响 mode, 反之亦然.
- **评分锚定实测分位** (cumcm): 91 篇 p25/p50/p75 直接进入 L1 Critic prompt 的 evidence 字段, 而非"推荐 600-900 字"这种估计值
- **Stage 5 per-Qi 加权聚合** (v3.0): 单 Qi 弱不再被全 stage 平均掩盖. `pass_with_review` 与 `refine_partial` 两个新 verdict 实现差异化降级 — Q2 单独 refine 不重做 Q1/Q3, 节省 ~60% 时间
- **题型 dim 权重**: A 优化题强化模型 dim, C 数据题强化统计/灵敏度, MCM 全题型强化 communication, F 政策题加权 Letter. 权重 clamp [0.7, 1.5] 防过激.
- **路径协议严格**: `<skill>/` 内文件用 skill 相对路径, 用户产物 (state/results/figures/paper_workspace) 用 cwd 相对路径, 三竞赛特化文件用 `competitions/<comp>/` 通配
- **token 纪律**: section-level patch 精修, references/competitions 懒加载, decision_log 持久化, 早退阈值 (iter-1 全维 ≥9 即跳)

## 不做的事

不替选题、不替建模、不保证拿奖。蒸馏内容仅作模仿模板, MCM 与电工杯 seed v0.1 准确性低于 cumcm, 文件头部均有 SEED 标记。

---

## 实测

| 模式 | Token | 耗时 | 适用 |
|------|-------|------|------|
| fast | ≤ 50k | ~30 min | 选题试跑 / sanity check |
| standard (默认) | ≤ 200k | ~6h | 主流程 |
| championship | ≤ 500k | ~12h | 提交前最后冲刺 (含 L3 panel + L4 校准 + red-team) |

实测 cumcm fast 模式跑通一次约 30 min, 含 cwd/state/decision_log.json 写入和 panel 串行 5 视角. mcm 模式 1-page summary 与 Letter 部分需手工打磨, 自动产出仅作骨架.

---

## 数据来源

**CUMCM 91 篇真烘焙**:
- 教育部"中国大学生在线"数学建模论文展廊 (2023-2025, 32 篇)
- GitHub `zhanwen/MathModel/国赛论文/2023年优秀论文/` (58 篇, A-F 全)
- GitHub `Jackyleo-Zhao/cumcm-2025` (1 篇国二 C 题)
- 烘焙时间 2026-05-05; 91 篇 PDF 已存档不读, 仅蒸馏 markdown 与 `empirical.json`

**MCM/ICM seed v0.1**:
- COMAP 官方 scoring rubric (公开) + Outstanding Winner press release 总结段落
- *MCM Tutorial* (Frank Giordano) 等已发表备赛教材共识

**电工杯 seed v0.1**:
- 电工杯官网历年题目题量分析
- 中国电机工程学会公开论文评审标准 (工程类)

---

## 开发日志

- V1: 初次搭建, 10 阶段 + 4 反馈层
- V2: 审计修了 20 条 (协议矛盾、schema 漂移、脚本 bug)
- V3: 模板瘦身 + 91 篇 PDF 蒸馏成 4 份 markdown 后删除 PDF (释放 494MB)
- **V4 (current)**: 三竞赛通用化 (`competitions/{cumcm,mcm,diangong}/`); 评分系统升级 — empirical 真正进入 L1 prompt; Stage 5 per-Qi 加权聚合 + 差异化降级 (`pass_with_review` / `refine_partial` 两个新 verdict); 题型 dim 权重 (`config/dim_weights.json`); SKILL.md 由 9k 字节瘦身到 ≤ 6k.

---

## License

MIT. 蒸馏出的 markdown 是从公开论文统计模式与改写而来, 不含原文。

---

学生作品, 发现 bug / 建议欢迎开 issue。
