<!-- SEED v0.1 — 基于 MCM/ICM 公开 judge guidelines + Outstanding Winner 公开模式手写, 未做 PDF 烘焙。empirical 占位无统计。 -->

# MCM/ICM 美赛特化层 (SEED v0.1)

Mathematical / Interdisciplinary Contest in Modeling (COMAP)。

| 字段 | 值 |
|------|-----|
| 竞赛代码 | `mcm` |
| 官方名 | Mathematical Contest in Modeling / Interdisciplinary Contest in Modeling |
| 主办 | COMAP |
| 时长 | 96 小时 (4 天) |
| 队员 | 3 人 |
| 语言 | English |
| LaTeX 编译器 | pdflatex (亦可 xelatex) |
| LaTeX 模板 | `templates/latex/mcm/` |
| 引用格式 | IEEE / APA (任选, 内部一致即可) |
| 题号 | A / B / C (MCM) + D / E / F (ICM) |
| 默认子问题数 | 4-5 (题目通常含 3-5 个 subtask + 1 个 letter) |
| 数据状态 | **seed v0.1** — 蒸馏未完成, 阈值取自公开 judge guidelines |

## 美赛与国赛的核心差异

1. **摘要不分段**: 1-page Summary, 250-350 词, 单段或两段, 不要求 5 anchor
2. **政策建议信** (D/E/F 题): 1-2 页 Letter to Policymakers / Memo to Stakeholders, 必须有
3. **创新性 > 严谨性**: Outstanding Winner 评审反复强调 "novel approach"
4. **Communication 单独维度**: 写作清晰度被独立打分, 不与数学严谨混在一起
5. **Sensitivity 必做**: 美赛评审显式要求 "robustness analysis", 与国赛灵敏度同等重要
6. **页数无上限但有惩罚**: 通常 25-40 页, 超 50 页评委疲劳扣分
7. **Reproducibility**: code + data 附录强制要求

## 文件清单

| 文件 | 用途 | 状态 |
|------|------|------|
| `topic_specs.json` | A-F 题号体系 + 题型映射 | seed |
| `rubric_overlay.json` | MCM 评分维度 (novel/rigor/communication/letter) | seed |
| `empirical.json` | 占位 (n=0); 阈值取自 COMAP judge guidelines | seed |
| `empirical_notes.md` | 缺数据说明 + 阈值出处 | seed |
| `winning_patterns.md` | Outstanding 共性 ~10 条 | seed |
| `phrase_bank.md` | 英文学术句式 + Letter 模板 | seed |
| `anti_patterns.md` | MCM 反模式 ~15 条 | seed |
| `abstract_template.md` | 1-page Summary + Letter 双模板 | seed |
| `paper_skeleton.md` | 25-40 页骨架 | seed |

## 数据来源声明

未做真 PDF 烘焙。所有阈值与模式来自:
- COMAP 官方 judge guidelines / scoring rubric (公开)
- COMAP press release 中 Outstanding Winner 总结段落 (历年)
- 已发表的 MCM 备赛教材普遍共识 (e.g. *MCM Tutorial* by Frank Giordano)

**用户使用本目录时, 应被告知"内容为 v0.1 种子版本, 准确性低于 cumcm/"。**
后续若有团队提交 30+ 篇 Outstanding 论文, 可用 `scripts/ingest_papers.py` 重新烘焙覆盖。
