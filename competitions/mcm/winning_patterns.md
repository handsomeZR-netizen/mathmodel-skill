<!-- SEED v0.1 — 基于 COMAP 公开 scoring rubric + Outstanding Winner press release 总结手写, 未做 PDF 烘焙。 -->

# MCM/ICM Outstanding Winner 共性 (SEED v0.1)

> 美赛 Outstanding (~1%) 与一般 Honorable Mention 的 10 个差距。每条与 stage 文件 / rubric 维度对齐。

---

## 1. **1-page Summary 抓人**

Outstanding 的 summary 几乎都包含: (a) one-sentence problem framing, (b) approach in 2-3 sentences, (c) ≥3 quantitative results with units, (d) one bold takeaway. **避免**通用的 "we built a model and got results"。

`stage 8 / rubric §8 dim1`

## 2. **Novel Approach 显式标注**

Outstanding 论文显式声明 "Our novel contribution is...", 不只是用经典模型。组合 ≥2 个学科方法 (e.g., game theory + ODE), 或对经典算法做命名扩展 ("Adaptive-Threshold k-means")。

`stage 3 / rubric §3 dim3`

## 3. **Sensitivity 是独立大节**

不是塞在 conclusion 里一句话。Outstanding 通常 1-2 页专门做 multivariate 扰动 + tornado plot + robust interval。OAT (one-at-a-time) 不够。

`stage 6 / rubric §6 dim1`

## 4. **Letter / Memo (D/E/F 题) 单独打磨**

不只把正文摘要复制到 Letter。Outstanding Letter 改用非技术语言, 提 3 个 actionable recommendations, 1 页内, 含 stakeholder 视角。

`stage 8`

## 5. **跨学科 / 创意 framing**

ICM 的 D/E/F 题 Outstanding 常引入社会学 / 经济学 / 公共政策视角。把数学建模放在更大问题语境里, 不只是数学优化。

`stage 1 / stage 7`

## 6. **Reproducibility 完整**

Appendix 含 (a) full code listing, (b) data source URL/DOI, (c) parameter values table, (d) software environment。Outstanding 论文允许任意第三方复现。

`stage 8 / stage 9`

## 7. **Strengths and Weaknesses 真实**

≥3 条具体局限 + ≥1 条改进路线 (含 alternative method 名 + 改进幅度估计 + 计算成本估计)。不写 "could be improved with more data"。

`stage 7 / rubric §7 dim2`

## 8. **Visual: 每个 model / sub-problem 有自己的图**

Outstanding 平均 14+ 图, 含: model schematic / data exploration / result main figure / sensitivity tornado / comparison to baseline。每图有 self-contained caption。

`stage 5 / stage 8`

## 9. **Quantified Comparison to Baseline**

不只声明 "our method is better"。报 "our method reduces cost by 23.4% compared to greedy baseline (Table 5), and is 1.7× faster than LP relaxation"。

`stage 5 / stage 7`

## 10. **English Writing Quality**

主谓一致 / 过去分词 / 学术 hedging ("suggests" vs "proves") 都到位。Outstanding 不一定 native English, 但 grammar error 极少且术语精确。

`stage 8 / rubric §8 dim3`

---

## 评估锚点 (L1 critic 用)

| 锚点 | 评估方式 |
|------|---------|
| Summary 含 ≥3 quantitative results | 正则: `\d+(\.\d+)?%?` 在 summary 段计数 |
| 主章节 ≥7 | markdown `^## ` 计数 |
| Sensitivity 单独大节 | 章节标题含 sensitivity / robustness |
| Letter (D/E/F) 存在 | 文档含 `## Letter` 或 `## Memo` |
| Code listing 在附录 | appendix 含 lstlisting / verbatim |
| ≥3 真实 limitations | stage 7 strengths_weaknesses 段落 ≥3 句 with specifics |

种子版本: 后续 PDF 烘焙后会用真分位替换上述阈值。
