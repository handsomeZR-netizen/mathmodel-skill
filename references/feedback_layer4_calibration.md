# Feedback Layer 4 — 校准检查 (防 rubric 被 gamed)

> 仅 championship 模式启用。每 3 次迭代抽查 1 个 rubric 维度, 用**不同 prompt 框架**重评, 若分差 >2 则该维度被 gamed, 重置该维度。

---

## 为何需要 L4?

L1 Critic 反复迭代会让 artifact 在 rubric 上得分越来越高, 但**未必真的变好** — 可能只是学会了 rubric 的语言、关键词、结构, 而非真正提升质量。

经验法则:
- 同一 rubric prompt + 同一 artifact, 重评分差 < 0.5 = 稳定
- 不同 rubric prompt + 同一 artifact, 分差 > 2 = **rubric 被 gamed**

L4 用第二种 prompt 框架做 cross-check。

---

## 触发条件

```
if mode == "championship":
    if iteration_count[stage] % 3 == 0:  # 每 3 次迭代
        run_calibration(stage, dim=randomly_pick_one(5_dims))
```

只抽 1 个维度 (节省 token)。下次迭代抽不同维度。

---

## Calibration Prompt 模板

**关键**: 与 L1 Critic 用**完全不同的 prompt 框架**。

### L1 框架 (rubric-anchored)
```
"评分 1-10. 维度 X 满分行为是 Y..."
→ 模型容易学会用关键词 Y 来获高分
```

### L4 框架 (scenario-anchored)
```
"想象一个具体的 CUMCM 评委 张教授. 他正在评审, 已经看过 50 篇论文.
他在维度 X 上看到本论文这一段, 心里会想什么?
他给一二三等奖 stack 的依据是什么?
请给出他对本维度的口头评价 (3-5 句话), 然后给一个分数 (1-10)."
```

输出:
```json
{
  "calibration_dim": "<dim_name>",
  "calibration_iteration": <int>,
  "alt_score": <int 1-10>,
  "alt_reasoning": "<张教授的口头评价>",
  "original_score": <int>,
  "delta": <abs(alt - orig)>,
  "verdict": "stable" | "potentially_gamed" | "definitely_gamed"
}
```

---

## Verdict 阈值

```python
def calibration_verdict(delta):
    if delta < 1:
        return "stable"        # rubric 稳健
    elif 1 <= delta <= 2:
        return "potentially_gamed"  # 警告, 但不重置
    else:  # delta > 2
        return "definitely_gamed"   # 重置该维度
```

---

## 重置流程

```python
def reset_dimension(stage, dim):
    # 1. 把该维度从分数中移除 (本轮迭代不计入)
    decision_log["scores"][stage][-1][dim] = None
    
    # 2. 用 calibration prompt 替代 L1 prompt 重新评一次
    fresh_score = layer1_critic(artifact, prompt_framework="scenario_anchored")
    decision_log["scores"][stage][-1][dim] = fresh_score
    
    # 3. 检查总分是否变化, 若 verdict 因此变化 → refine
    new_verdict = compute_verdict(decision_log["scores"][stage][-1])
    if new_verdict == "refine":
        return "refine_needed"
    return "ok"
```

---

## 第二种 calibration prompt 框架 (备选)

### Adversarial 框架
```
你是国赛评委里最严苛的一位. 你的任务是给本维度 X 的论文找 reject 理由.
列 ≥3 条 reject 理由 (具体到段落或公式编号).
然后, 综合这些 reject 理由的严重程度, 你最终会给本维度多少分 (1-10)?

Output:
{
  "reject_reasons": [...],
  "calibration_score": <int>
}
```

### Story 框架
```
请编一个 50 字的小故事: "评委王教授正在审本论文的 §X 章节, 他的反应是..."
然后给一个能反映你故事的分数 (1-10).

Output:
{
  "story": "...",
  "calibration_score": <int>
}
```

3 种 prompt 框架轮换使用, 进一步减小 gaming 风险。

---

## 各维度的 calibration 抽查 (按 stage 编号轮换, 避免按 iter 累计永远只查 dim 1)

**触发条件**: `mode == "championship" and stage_id in {3, 5, 6, 8, 9}` (championship 模式 + 重要阶段, 5 次覆盖 5 个 dim)

```
stage 3 calibration: dim 3 (naming_variant) — 检测命名变体是否被 game 成空名
stage 5 calibration: dim 4 (visualization)  — 检测视觉化是否被 game 成低质图
stage 6 calibration: dim 1 (multivariate_perturbation) — 检测多变量扰动是否真做
stage 8 calibration: dim 4 (language_quality) — 检测语言质量是否被 phrase 关键词 game
stage 9 calibration: dim 3 (panel_consensus) — 检测 panel 共识是否真独立
```

每个 stage 只查一个维度 (省 token), 5 个 stage 覆盖 5 个不同 dim。

如果某 stage 触发了多次 (e.g., L1 carryover 后再触发), L4 在该 stage 只查一次 (用 `decision_log.events.log` 去重)。

**维度重复轮换** (stage 1/2/4/7 也想做 calibration, 但 standard 模式下不开):
- 仅当 championship + 用户显式要求 "重新校准 stage X", 才再触发一次, 选未查过的 dim。

**为何不按 iter 累计?** L1 cap = 3, iter 6/9/12... 永远不出现 (除非 stage 5 多 Qi, 但每 Qi 也独立 cap), 按 iter 累计实际只触发 dim 1。改按 stage 编号能保证 5 个 dim 都被独立 prompt 框架审过一次。

---

## 与 L1 的接口

```python
def L1_critic_with_L4(stage, artifact, iteration):
    score = L1_critic(stage, artifact)
    
    if mode == "championship" and iteration > 0 and iteration % 3 == 0:
        dim = pick_dim_for_calibration(iteration)
        cal_result = L4_calibrate(stage, artifact, dim)
        if cal_result["verdict"] == "definitely_gamed":
            score[dim] = cal_result["alt_score"]
            log_event("L4_reset", stage, dim, cal_result)
    
    return score
```

---

## 输出与日志

```json
{
  "type": "L4_calibration",
  "ts": "...",
  "stage": 5,
  "iteration": 6,
  "dim": "2_math_rigor",
  "framework": "scenario_anchored",
  "L1_score": 9,
  "L4_score": 6,
  "delta": 3,
  "verdict": "definitely_gamed",
  "action": "reset_to_6"
}
```

---

## 时间预算

L4 是低频触发 (championship 模式 + 每 3 次迭代):
- 每次 ~500-800 tokens (单维度)
- 整个 skill 运行下来, L4 约调用 5-10 次, 总成本 < 8k tokens

---

## 设计风险

- **过度校准**: 若 L4 频繁判定 gamed, 可能是 rubric 本身设计有问题, 而非模型在 game. 解决: 累计 ≥3 个维度被 reset → 暂停 Skill, 报告用户。
- **校准本身被 gamed**: 极端情况下, 模型也学会了 calibration prompt 的"潜规则". 解决: 3 种框架轮换。
- **预算超标**: 加 hard cap, L4 总成本不超过总预算的 5%。
