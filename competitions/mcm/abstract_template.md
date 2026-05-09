<!-- SEED v0.1 — MCM 1-page Summary + Letter to Policymakers 双模板。 -->

# MCM Abstract Templates (SEED v0.1)

MCM 的"摘要"实际是 **1-page Summary** (250-350 词, 单页内放完)。D/E/F 题额外要 **Letter / Memo**。

---

## A. 1-Page Summary Template

> 占位: `{...}`。目标 250-330 词, 单页 pdflatex 渲染后核对。

```
{Problem framing — 1 sentence: "We address the problem of {what}, which arises in {context}."}

{Approach — 2-3 sentences: "We develop a {model class} that combines {method A} with {method B}.
Our novel contribution is {specific extension}. We solve via {algorithm} and validate
against {baseline}."}

{Key results — 3-4 sentences with quantitative numbers:
"On {scenario 1}, our method achieves {metric} = {value}, a {X}% improvement over {baseline}.
Multivariate sensitivity analysis confirms robustness within ±{Y}% of key parameters {p1, p2, p3}.
For {scenario 2}, the optimal {decision variable} is {value}, yielding {outcome} = {value}.
Counterfactual experiments show that {finding}."}

{Caveat / scope — 1 sentence: "These results assume {assumption}; we discuss limitations in §X."}

{Bold takeaway — 1 sentence: "Our analysis suggests that {actionable insight for decision-maker}."}

Keywords: {3-5 keywords, comma-separated}
```

### Filled example (A 题, optimization)

```
We address the problem of optimizing renewable energy dispatch in a regional grid under
stochastic demand, motivated by the 2024 ICM problem A.

We develop a stochastic dynamic programming model that combines Markov decision processes
with chance-constrained optimization. Our novel contribution is a Time-Aware Bellman update
that exploits diurnal demand patterns. We solve via approximate dynamic programming and
validate against a deterministic LP baseline.

On a 90-day test horizon, our method reduces total cost by 23.4% compared to LP (Table 5)
and meets the 99% reliability constraint in 96.7% of Monte Carlo runs. Sensitivity analysis
across demand variance, fuel price, and storage efficiency (LHS, n=500) confirms robust
performance within ±15% perturbation. Counterfactual analysis shows that doubling storage
capacity yields diminishing returns above 1.4× current size.

These results assume perfect short-term demand forecasts; real-world forecast error of
~5% is discussed in §7. Our analysis suggests that grid operators can reduce dispatch
cost by 20%+ with modest investment in storage and updated control policy.

Keywords: stochastic optimization, energy dispatch, dynamic programming, sensitivity analysis
```

(约 230 词。可加 1-2 句到 280 词左右。)

---

## B. Letter to Policymakers Template (D/E/F 题强制)

```
Dear {Stakeholder Title — e.g. "Mayor of {City}", "Director of {Agency}"},

We are writing to share findings from our analysis of {issue}, which we believe may
inform your upcoming decision on {decision}.

Our team examined {problem in plain language, 2-3 sentences, no jargon}. The central
question we addressed is: {question}. {Briefly: what data / what scope, in plain terms}.

Based on our analysis, we offer three actionable recommendations:

1. **{Action 1}**. {1 sentence rationale}. {Expected impact in plain terms}.

2. **{Action 2}**. {...}.

3. **{Action 3}**. {...}.

We note that these recommendations rest on the assumption that {assumption}.
They should be revisited if {condition} changes — most importantly, {specific
trigger that would invalidate the recommendation}.

Our team would be happy to discuss the technical details with your staff if useful.

Sincerely,

Team #{Control Number}
```

### 长度目标
- 1-2 页 (350-700 词)
- 无公式 / 无算法名 / 无章节编号
- 无引文 (引文留正文)

### 强制 anchor (5 个)
1. ✅ 称呼 (Dear ...)
2. ✅ Context 段
3. ✅ ≥3 numbered recommendations with action verbs
4. ✅ Caveat 段 (assumption + when to revisit)
5. ✅ Closing (Sincerely + Team #)

L1 critic 检查这 5 个 anchor 的命中数; ≥ 4 才 pass。
