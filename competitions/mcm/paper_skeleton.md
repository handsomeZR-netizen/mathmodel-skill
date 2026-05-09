<!-- SEED v0.1 — MCM 论文 25-40 页骨架。 -->

# MCM Paper Skeleton (SEED v0.1)

> 美赛论文的标准结构。25-35 页常见, ≤ 50 页 (超出评委疲劳扣分)。

```
[Cover Page]                                            (1 page, COMAP-provided template)
  - Problem Chosen: A / B / C / D / E / F
  - Team Control Number: #XXXX
  - Year: YYYY

[1-Page Summary]                                        (1 page, 250-350 words)
  - Problem framing
  - Approach
  - Key quantitative results (≥3 numbers)
  - Caveat / Bold takeaway
  - Keywords

[Table of Contents]                                     (~0.5 page)

§1 Introduction                                         (1.5-2 pages)
  1.1 Background / Motivation
  1.2 Problem Restatement (in own words)
  1.3 Literature Review (brief, ≤ 1/2 page)
  1.4 Our Approach (high-level overview, 1 paragraph)
  1.5 Outline of the Paper

§2 Assumptions and Justifications                       (1 page)
  - 5-10 assumptions, each with justification
  - Table format encouraged

§3 Notation                                             (0.5-1 page)
  - Symbol table: Symbol | Meaning | Unit

§4 Model Development                                    (5-10 pages)
  4.1 Model 1 / Sub-problem 1
       4.1.1 Problem formulation
       4.1.2 Mathematical model
       4.1.3 Solution approach
  4.2 Model 2 / Sub-problem 2
       ...

§5 Solution and Results                                 (4-8 pages)
  5.1 Implementation
  5.2 Results for Sub-problem 1
       - Figures with self-contained captions
       - Tables of key metrics
  5.3 Results for Sub-problem 2
       ...
  5.4 Comparison to Baseline (if applicable)

§6 Sensitivity and Robustness Analysis                  (1.5-2 pages)
  6.1 Multivariate Perturbation (LHS / Sobol)
  6.2 Tornado Plot
  6.3 Robust Interval Discussion

§7 Strengths and Weaknesses                             (1 page)
  7.1 Strengths
       - 3+ items, each with specific advantage
  7.2 Weaknesses / Limitations
       - 3+ items, each with severity + future work

§8 Conclusion                                           (0.5-1 page)
  - Recap key findings
  - Practical implications
  - Future directions

§9 References                                           (1-2 pages, IEEE/APA)
  - Minimum 12, typical 18-25

[Letter to Policymakers]                                (1-2 pages, ONLY for D/E/F)
  - Dear {stakeholder}
  - Context (plain language)
  - 3 numbered actionable recommendations
  - Caveat
  - Sincerely

[Appendix A: Code Listing]                              (any length)
  - Full listing or GitHub URL with commit hash

[Appendix B: Parameter Values]                          (≤ 1 page)
  - Single table: Parameter | Value | Unit | Source

[Appendix C: Additional Figures]                        (optional)
```

## 页数预算

| Section | 页数 | 备注 |
|---------|------|------|
| Cover + Summary + TOC | 2.5 | 硬约束 |
| Introduction | 1.5-2 | |
| Assumptions + Notation | 1.5 | |
| Model Development | 5-10 | 主体 |
| Solution + Results | 4-8 | 主体 |
| Sensitivity | 1.5-2 | 必做 |
| Strengths/Weaknesses | 1 | |
| Conclusion + References | 1.5-3 | |
| Letter (if D/E/F) | 1-2 | |
| Appendices | 2-5 | |
| **Total** | **22-37** | 推荐 25-32 |

## 必备 anchor 清单 (stage 8 / stage 9 检查)

- [ ] 1-Page Summary 在第 2 页, 单页内, ≥3 quantitative results
- [ ] Assumptions 表格化, 每条带 justification
- [ ] Notation 表完整, 符号唯一
- [ ] Model Development 至少 5 页, 含公式
- [ ] Sensitivity 单独章节, 含 multivariate (非 OAT)
- [ ] Strengths + Weaknesses 各 ≥ 3 条
- [ ] References ≥ 12 条
- [ ] Appendix Code Listing 或 GitHub 链接
- [ ] (D/E/F) Letter 1-2 页, ≥3 actionable recommendations
- [ ] PDF 总页数 25-40
