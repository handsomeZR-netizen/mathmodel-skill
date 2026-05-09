<!-- SEED v0.1 — 英文学术句式 + Letter 模板。基于 MCM Outstanding 公开评语 + COMAP 备赛教材共识手写。 -->

# MCM Phrase Bank (SEED v0.1)

> 英文学术句式库, 按论文位置分组。L1 critic 评 stage 8 时, anchor 命中数 ≥ N 触发 pass 锚定。

---

## 1. Summary (1-page) Anchors

### Problem framing (1 sentence)
- "We address the problem of {what}, which arises in the context of {why}."
- "This study investigates {phenomenon} under the constraint that {constraint}."
- "Given {data/setup}, we seek to {goal}."

### Approach (2-3 sentences)
- "We develop a {model class} model that combines {method A} with {method B}."
- "Our approach extends the classical {model name} by introducing {modification}."
- "We solve the resulting {problem type} via {algorithm} and validate against {baseline}."

### Key results (≥3 quantitative)
- "On {scenario}, our method achieves {metric} of {value}, a {percent}% improvement over {baseline}."
- "Sensitivity analysis confirms robust performance within ±{percent}% perturbation of {parameter}."
- "The optimal {decision variable} is {value}, yielding {outcome metric} = {value}."

### Bold takeaway (1 sentence)
- "Our results suggest that {actionable insight}."
- "This finding has direct implications for {stakeholder/decision}."

---

## 2. Introduction Anchors

- "In recent years, {topic} has received considerable attention due to {motivation}."
- "Existing approaches to {problem} typically assume {assumption}, which limits their applicability when {condition}."
- "The contributions of this paper are threefold: (1) {what}, (2) {what}, and (3) {what}."
- "The remainder of the paper is organized as follows. Section 2 ... Section 3 ..."

## 3. Assumptions and Notation

- "We make the following assumptions, which are justified by {reason}:"
- "Throughout the paper, we use {symbol} to denote {meaning}."
- "Without loss of generality, we assume {assumption}."

## 4. Model Setup

- "Let {variable} ∈ {domain} denote {meaning}."
- "We formulate the problem as the following optimization:"
- "Subject to the constraints (3)-(7), the model captures {phenomenon}."

## 5. Solution / Algorithm

- "Algorithm 1 outlines our approach. The complexity is O({expression})."
- "We use {solver/library} to solve the resulting {problem class}."
- "Convergence is guaranteed under {condition}."

## 6. Sensitivity / Robustness

- "We perform a multivariate sensitivity analysis varying {p1}, {p2}, {p3} simultaneously over a Latin Hypercube design."
- "The output {metric} remains within {value}±{tolerance} for {percent}% of perturbations (Figure X)."
- "The model is most sensitive to {parameter}, with elasticity {value}."

## 7. Strengths / Weaknesses

### Strengths
- "Our approach {advantage}, which is critical for {application}."
- "Compared to {baseline}, our method offers {specific gain}."

### Weaknesses
- "The model assumes {assumption}, which may not hold when {condition}."
- "Computational cost scales as O({expression}), limiting applicability for {scale}."
- "Future work should incorporate {missing element} to address this limitation."

## 8. Conclusion

- "We have presented {summary in one sentence}."
- "Our results indicate that {finding}."
- "Practical implications include {action 1}, {action 2}."

---

## 9. Letter to Policymakers (D/E/F 题)

### Opening
- "Dear {Stakeholder Title},"
- "We are writing to share findings from a recent analysis of {issue} that may inform {decision}."

### Context (1 paragraph, plain language)
- "Our analysis examined {problem} under {key conditions}. Without simplifying technical detail, the central question was: {question in plain terms}."

### Three actionable recommendations
1. **{Action 1}**. {1 sentence rationale + expected impact in plain terms}.
2. **{Action 2}**. {...}.
3. **{Action 3}**. {...}.

### Caveat / Closing
- "We note that these recommendations rest on {assumption}; they should be revisited if {condition} changes."
- "We are happy to discuss the technical details further if useful."
- "Sincerely, Team #{XXXX}"

**长度目标**: 1-2 页 (350-700 词)。**避免**: 公式 / 算法名 / 章节编号 / 引文。

---

## 10. Hedging / Academic Tone

- "suggests" / "indicates" / "is consistent with" — softer than "proves" / "shows"
- "may" / "could" / "tends to" — for predictions
- "to our knowledge" — for novelty claims (avoid "first ever")
- "We note that" / "It should be observed that" — caveats

## 11. Avoid (anti-pattern phrasing)

- ❌ "obviously / clearly / it is well known that" — without citation
- ❌ "very / really / quite" — vague intensifiers
- ❌ "perfect / ideal / optimal" — without proof of optimality
- ❌ Long sentences (>40 words) — split

---

## 锚点命中目标 (L1 critic)

| Stage | 类别 | 命中数 ≥ |
|-------|------|---------|
| 8 (summary) | Summary anchors | 4 (problem + approach + ≥2 quant + takeaway) |
| 8 (intro) | Intro anchors | 3 |
| 8 (model) | Model setup | 3 |
| 8 (sens) | Sensitivity anchors | 2 |
| 8 (S/W) | Strengths + Weaknesses | 各 ≥ 1 |
| 8 (letter, 仅 D/E/F) | Letter anchors | opening + 3 actions + closing = 5 |
