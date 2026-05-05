# 论文资料库 (papers)

> 本目录是**辅助参考资料**, skill 主体不依赖这里的内容运行。`references/winning_patterns.md` 已经从公开渠道一次性提炼了一等奖共性, 写入静态知识。

## 当前内容

可能包含通过 git clone 拉取的开源仓库:
- `MathModel/` (zhanwen): 历年题目分类 + 算法资料
- `Math_Model_repo/` (personqianduixue): LaTeX 模板 + 算法仓 (论文在百度云,GitHub 仅索引)

## 如何手动补充

直接下载渠道有限, 优先级如下:

### 1. 教育部"中国大学生在线"展厅 (官方公开)
- URL: https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/
- 操作: 浏览器手动进入 → 选年份 → 选题号 → 下载 PDF → 投放到本目录
- 优势: 官方权威, 都是真实一等奖
- 限制: 每年仅展出极少 (3-5 篇/题)

### 2. GitHub 公开 repo
搜索 keyword:
- "CUMCM" / "数学建模" / "国一"
- "national first prize" math modeling
- 历年获奖学校的个人 repo (如中山大学、清华、上交)

### 3. CSDN / 知乎 / B 站
质量参差, 但有汇总贴。例:
- https://blog.csdn.net/qq_37345758/article/details/134295998 (2023 国赛)
- https://blog.csdn.net/2401_86936045/article/details/141719882 (历年汇总, 国一学长整理)

CSDN 会要求注册或下载券, 注意辨别真伪。

### 4. 数模社 / 数模君 / 数学建模交流群
非官方, 但可能有更多。需付费或加群。

## 使用方法

收集到 PDF 后:
1. 投放到本目录 (任意子目录)
2. 跑 `python scripts/ingest_papers.py --papers-dir references/papers/`
3. 脚本会输出: 字数 / 章节数 / 图表 / 公式 / 摘要含定量结果比例 等统计
4. 把统计结果与 `references/winning_patterns.md` 中的预设阈值对照
5. 若实测显著不同, 手动更新 `winning_patterns.md`

## 重要提示

skill 运行时**不读**这里的 PDF (避免污染上下文 + token 浪费)。
本目录内容只在你想**手动补充/更新模式**时使用。
即使本目录为空, skill 仍可完整运行。
