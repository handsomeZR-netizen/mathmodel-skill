<!-- SEED v0.1 — 美赛反模式。基于 COMAP press release 总结评语 + 教材共识手写, 未做 PDF 烘焙。 -->

# MCM/ICM Anti-Patterns (SEED v0.1)

> 美赛 Outstanding 评审显著扣分的反模式。stage 9 终审逐条对照。15 条 (国赛 32 条更细; 美赛此处只列高频)。

---

## A. Summary (1-page) 类

### A1. Summary 没有 quantitative results
**症状**: Summary 只描述方法过程, 不报具体数值结果。
**修复**: 至少 3 个数值 (with units) 关键结论。

### A2. Summary 超 350 词或不足 200 词
**症状**: 1 page 是硬约束, 超出会刷掉。
**修复**: 控制在 250-330 词, pdflatex 渲染后核对单页。

### A3. Summary = 抽象 abstract 复制
**症状**: 与 Introduction 第一段重复。
**修复**: Summary 必须含 takeaway / actionable insight, 是 selling pitch 不是综述。

---

## B. Letter / Memo (D/E/F) 类

### B1. Letter 含技术术语
**症状**: Letter 里出现 "Lagrangian / convergence / eigenvalue"。
**修复**: 全部替换为 plain English; 数学全部回到 main paper。

### B2. Letter 没有 actionable recommendations
**症状**: 只总结研究, 不给 decision-maker 建议。
**修复**: 强制 ≥3 条 numbered recommendations, 每条 1 句行动 + 1 句 rationale。

### B3. Letter 缺 caveat
**症状**: 推荐听起来绝对。
**修复**: 加 "These recommendations assume {X}; should be revisited if {Y}"。

---

## C. 创新性 / Novelty 类

### C1. 直接套用 textbook 模型, 无任何扩展
**症状**: "We use linear regression to ..." — 没改进 / 没组合 / 没起新名。
**修复**: 命名变体 (e.g. "Time-Aware Linear Regression with Holiday Dummies"), 或组合 2 个方法。

### C2. Approach 段不声明 novel contribution
**症状**: Outstanding 评语高频出现 "novel approach"; 反过来普通论文是 "applied X to Y"。
**修复**: 显式 1 句 "Our novel contribution is {specific extension/combination}"。

---

## D. Sensitivity / Robustness 类

### D1. 只做 OAT (one-at-a-time) 灵敏度
**症状**: Tornado plot 单参数, 不做联合扰动。
**修复**: Latin Hypercube / Sobol indices ≥ 3 参数同时变化。

### D2. 没有 robust interval 报告
**症状**: 只有 figure, 没说清 "我们的解在 ±X% 扰动下保持 Y 性质"。
**修复**: 给出量化 robust interval。

---

## E. Reproducibility 类

### E1. Appendix 没有完整 code listing
**症状**: 只贴关键函数。
**修复**: full listing or GitHub URL with commit hash。

### E2. Parameter values 散落各处, 无单表
**症状**: 评委要 verify 时翻不到。
**修复**: Appendix 单一 "Parameter Values Used" 表。

### E3. Data source 未声明 / 未引用
**症状**: 用了 dataset 但没说从哪来。
**修复**: dataset name + URL + access date + license。

---

## F. 写作 / Presentation 类

### F1. Figure 无 self-contained caption
**症状**: caption "Figure 3: Results"。
**修复**: caption 含 axes meaning + key takeaway in 1 sentence。

### F2. Mixed person (we / I / one)
**症状**: 同一论文混用第一人称 / 被动 / 第三人称。
**修复**: 统一 "We" (MCM 推荐, COMAP 教材范例都用 we)。

### F3. 主谓不一致 / 时态飘 (典型非母语错)
**症状**: "The model give result" / "We solved and analyze"。
**修复**: 提交前 grammarly / language model 全文 pass。

---

## 评估协议 (stage 9)

| 反模式 | 检测方式 | 命中后行为 |
|--------|---------|-----------|
| A1 | 正则 `\d+%?` 在 summary 段, count < 3 | block + 强制重写 |
| A2 | summary 词数 not in [200, 400] | refine |
| B2 | Letter 段含 numbered list with action verb count < 3 | refine |
| C1 | model section 不含 novel/extend/combine 类词 | warn |
| D1 | sensitivity 段不含 LHS/Sobol/multivariate | refine |
| E1 | appendix 不含 lstlisting / verbatim 块 | refine |
| F1 | figure caption 词数 < 10 | warn each |
| F3 | grammar error rate (lt 工具) > 1% | refine |

**Outstanding 阈值** (seed): ≤ 2 条触发为良, ≤ 4 条为可接受, > 4 条标 carryover。
