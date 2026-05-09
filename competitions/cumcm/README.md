# CUMCM 国赛特化层

全国大学生数学建模竞赛专用资源。

| 字段 | 值 |
|------|-----|
| 竞赛代码 | `cumcm` |
| 官方名 | 全国大学生数学建模竞赛 |
| 时长 | 72 小时 (3 天) |
| 队员 | 3 人 (建模 / 编程 / 写作) |
| 语言 | 中文 |
| LaTeX 编译器 | xelatex |
| LaTeX 模板 | `templates/latex/cumcm/cumcmthesis/` |
| 引用格式 | GB/T 7714 |
| 题号 | A / B / C / D / E (近年 F 并入 B) |
| 默认子问题数 | 4 (IQR [3, 5]) |
| 数据状态 | **stable** — 91 篇真烘焙 (2023-2025) |

## 文件清单

| 文件 | 用途 | 加载阶段 |
|------|------|---------|
| `topic_specs.json` | 题号体系 + 题型→task_type 映射 | stage 1 |
| `rubric_overlay.json` | 国赛特化评分维度 overlay | stage 8/9, score_artifact |
| `empirical.json` | 91 篇 p25/p50/p75 实测分位 | feedback_layer1_critic, score_artifact |
| `empirical_notes.md` | 实测数据人读说明 + 91 篇出处 | 文档参考 |
| `winning_patterns.md` | 一等奖共性 10 条 | stage 8 (anchor) |
| `phrase_bank.md` | 中文学术句式库 | stage 8 |
| `anti_patterns.md` | 32 条反模式 | stage 9 (逐条对照) |
| `distilled_phrases.md` | 段落模板 | stage 8 |
| `distilled_naming.md` | 命名变体 | stage 3 |
| `distilled_structures.md` | 章节结构模板 | stage 8 |
| `distilled_formats.md` | 格式细节 | stage 8/9 |
| `abstract_template.md` | 5 段式摘要模板 + 完整示例 | stage 8 |
| `paper_skeleton.md` | 22-25 页 LaTeX 骨架 | stage 8 |

## 数据来源

- 教育部"中国大学生在线"数学建模论文展廊 (2023-2025, 32 篇)
- GitHub `zhanwen/MathModel/国赛论文/2023年优秀论文/` (58 篇, A-F 全)
- GitHub `Jackyleo-Zhao/cumcm-2025` (1 篇国二 C 题)

烘焙时间 2026-05-05; 烘焙脚本已存档于 `scripts/ingest_papers.py`。

## 与 references/ 通用层的关系

- `references/stage_NN_*.md` 在加载本目录文件时, 通过 `decision_log.competition` 字段 dispatch
- 通用模型清单 `references/model_catalog.md` 跨竞赛复用
- 反馈层 `references/feedback_layer*.md` 通用; L1 critic prompt 在评硬阈值维度时拉本目录的 `empirical.json`
