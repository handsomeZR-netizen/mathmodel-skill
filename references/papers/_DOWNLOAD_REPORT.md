# CUMCM Papers Download Report

**总计**: 91 篇真国赛获奖论文 PDF (~432MB)

| 来源 | 数量 | 备注 |
|------|------|------|
| 教育部"中国大学生在线"展廊 (2023) | 9 | Playwright 渲染详情页 + 图片重建 PDF (image-only) |
| 教育部展廊 (2024) | 16 | 同上 |
| 教育部展廊 (2025) | 7 | A 题验证为 2025 真题 (无人机烟幕) |
| GitHub `zhanwen/MathModel/国赛论文/2023年优秀论文/` | 58 | 直接公开 PDF, A-F 题号齐全 |
| GitHub `Jackyleo-Zhao/cumcm-2025` (国二) | 1 | 2025 C 题 NIPT |

## 抽检验证

随机抽 3 篇官方展廊 PDF (2023-B226 / 2024-B195 / 2024-E218) 第一页确认年份与文件名一致。
2025-A196 第一页含"多情形下无人机烟幕遮蔽策略", 与 2025 A 题真题匹配。

## 已知限制

- 33 篇展廊重建 PDF 是图片型, pdfplumber 提取不到文字 → `ingest_papers.py` 自动过滤, 仅 59 篇参与 `empirical_distribution.md` 烘焙。
- 题号覆盖: 2023 A/B/C/D/E/F, 2024 A/B/C/D/E, 2025 A/B/C/D/E (含 1 篇国二)。

## 重新下载方式

`scripts/download_cumcm_papers.py` 已存档, 不在运行时调用。需补充 PDF 时手动跑该脚本或用 codex 子代理 (见 git log)。
