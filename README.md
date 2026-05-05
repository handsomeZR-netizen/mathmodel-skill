# cumcm-modeling-skill

> 自己写的数学建模工作流, 顺手做成了 Claude Code skill, 自用为主, 公开出来供同样要打国赛的同学参考。

[![Skill](https://img.shields.io/badge/Claude%20Code-Skill-FF6B35)](https://docs.claude.com/en/docs/claude-code/overview)
[![Stages](https://img.shields.io/badge/stages-10-blue)](./SKILL.md)
[![Feedback Layers](https://img.shields.io/badge/feedback%20layers-4-green)](./references/feedback_layer1_critic.md)
[![Modes](https://img.shields.io/badge/modes-fast%20%7C%20standard%20%7C%20championship-9cf)](./SKILL.md)
[![Distilled From](https://img.shields.io/badge/distilled%20from-91%20CUMCM%20papers%20%282023--2025%29-orange)](./references/distilled_phrases.md)
[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](./templates/requirements.txt)
[![LaTeX](https://img.shields.io/badge/LaTeX-cumcmthesis-008080?logo=latex&logoColor=white)](./templates/cumcmthesis)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](#license)

---

## 这是什么

国赛 (CUMCM) 是 3 天完成 1 篇 25 页论文的比赛, 流程从选题、建模、求解、灵敏度到写作很容易乱掉。我把自己每个阶段的检查项和踩过的坑整理成一套 Claude Code skill, 让大模型按固定流程跟我一起走, 减少返工。

不是"开箱拿一等奖"的工具 — 论文还得人写, 模型还得人想。这套 skill 的作用是:
- 把节奏卡住, 不让某一阶段悄悄崩 (rubric 自评 + 跨阶段一致性回检)
- 把容易忘的细节固化下来 (摘要 5 段式、命名变体、复用链、灵敏度做法)
- 把别人论文里反复出现的句式和命名提取出来供模仿 (蒸馏自 91 篇真国赛 2023-2025 获奖论文)

## 怎么用

放到 Claude Code 的 skill 目录下:

```bash
git clone https://github.com/handsomeZR-netizen/cumcm-modeling-skill.git ~/.claude/skills/cumcm-modeling
```

之后跟 Claude 说"开始建模"或者打开题目时会自动触发。第一次会问你 4 个问题 (题号、队员、截止时间、题目 PDF 路径), 然后从 Stage 0 开始走。

依赖:
```bash
pip install -r templates/requirements.txt
```

## 结构

```
SKILL.md                    入口, 模式选择 + 阶段索引
references/
  stage_00 ~ stage_09       10 阶段细则 (含 YAML frontmatter)
  feedback_layer1 ~ 4       自评 / 跨阶段回检 / 5 视角 panel / 防 gaming 校准
  winning_patterns          一等奖共性观察
  rubrics                   评分量表 (与 SKILL.md verdict 三处统一)
  anti_patterns             32 条反模式
  phrase_bank               中文学术句式 + L1 anchor
  model_catalog             60+ 模型按 10 类索引 + 2023-2025 历年题速查
  empirical_distribution    从 59 篇可提取 PDF 烘焙的实测分位数
  distilled_*               4 份蒸馏 markdown (段落模板 / 命名变体 / 结构 / 格式)
templates/
  paper_skeleton            22-25 页 LaTeX 骨架占位符
  abstract_template         5 段式摘要 + 完整示例
  assumption / notation / sensitivity_table   快速参考卡
  code_starter/             Python 起手代码 (优化/预测/评价/分类/仿真)
  cumcmthesis/              国赛官方 LaTeX 模板
  decision_log.json         跨阶段状态 schema
scripts/
  score_artifact.py         L1 评分校验 + verdict 重算
  extract_diff.py           section-level patch 精修 (省 60% token)
  render_paper.py           md → cumcmthesis tex → xelatex 三编
  ingest_papers.py          PDF 烘焙 (已存档, 蒸馏后不再用)
tests/fixtures/             score_artifact 单元测试样本
```

## 一些设计选择

- **3 模式**: fast (~50k tokens, 单次过) / standard (默认 ~200k, L1+L2) / championship (~500k, 含红队对抗 + 校准)
- **路径协议**: skill 内文件用 skill-相对路径, 用户产物 (state/results/figures/paper_workspace) 用 cwd 相对路径
- **token 纪律**: section-level patch 精修, references 懒加载, decision_log 持久化, 早退阈值 (iter-1 全维 ≥9 即跳)
- **不做**的事: 不替你建模, 不替你求解, 不保证拿奖

## 开发日志

写这套东西的时候用了 Plan 模式做了 3 轮迭代:
- V1: 初次搭建, 10 阶段 + 4 反馈层
- V2: 审计修了 20 条 (协议矛盾、schema 漂移、脚本 bug)
- V3: 模板瘦身 + 91 篇 PDF 蒸馏成 4 份 markdown 后删除 PDF (释放 494MB)

实测 fast 模式跑通一次约 30 min, 含 cwd/state/decision_log.json 写入和 panel 串行 5 视角。

## 来源

PDF 来源 (蒸馏后已删):
- 教育部"中国大学生在线"数学建模论文展廊 (2023-2025, 32 篇)
- GitHub `zhanwen/MathModel/国赛论文/2023年优秀论文/` (58 篇, A-F 题号齐全)
- GitHub `Jackyleo-Zhao/cumcm-2025` (1 篇国二 C 题)

参考资料:
- 国赛官网 https://www.mcm.edu.cn/
- 教育部展廊 https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/
- `personqianduixue/Math_Model`
- `datawhalechina/intro-mathmodel`

## License

MIT. 蒸馏出的 markdown 是从公开论文统计模式与改写而来, 不含原文。

---

学生作品, 发现 bug / 建议欢迎开 issue。我国赛后再补维护。
