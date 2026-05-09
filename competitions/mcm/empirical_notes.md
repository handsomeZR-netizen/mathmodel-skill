# MCM/ICM 实测分布 (SEED v0.1)

> **此目录数据为种子版本 (seed_v0.1), 未做真 PDF 烘焙。**
> 阈值取自 COMAP 公开 scoring rubric + 已发表 MCM 备赛教材共识。
> 后续若提交 30+ 篇 Outstanding Winner PDF, 可用 `scripts/ingest_papers.py` 重新烘焙覆盖。

## 数据缺口提示

`empirical.json` 中所有 `min` / `max` / `mean` 字段填的是估算值, 不是真实样本统计。score_artifact.py 在评分时, evidence 字段会自动标 `[seed: 阈值无实测分位]` 避免误导。

## 阈值出处

| 阈值 | 来源 | 备注 |
|------|------|------|
| Summary 250-350 词 | COMAP scoring sheet "1-page summary" | 历年规则一致 |
| 论文页数 25-35 页 | Outstanding 评审讲解 | 超 50 页扣分 |
| Figure 8-22 | 经验估算 | Outstanding 普遍图多 |
| Reference 12-25 | 经验估算 | IEEE 引用 |
| Letter 350-700 词 | F 题历年 Memo 长度 | 1-2 页正常 |

## 与 cumcm/ 的差异

国赛 91 篇 PDF 烘焙了 11 个维度的 p25/p50/p75。本目录只手填 8 个维度的估值。MCM 缺数据：
- Outstanding Winner PDF 不公开下载
- COMAP 只发布每年 outstanding 论文的 ~30 字摘要描述, 无全文
- GitHub 上零散 MCM 论文版权状态不一

## 推荐使用方式

1. **优先使用模式定性**: `winning_patterns.md` 列的 Outstanding 共性是更可靠的 anchor
2. **数值阈值仅作参考**: L1 critic 见到 `seed` 标记后弱化数值评判, 强化模式匹配
3. **若用户能提供历年 Outstanding 论文**: 跑 `scripts/ingest_papers.py --competition mcm`, 覆盖本 JSON
