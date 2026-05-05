# Feedback Layer 2 — 跨阶段一致性回检

> 在 stage 5 / 6 / 8 末尾自动触发。读 decision_log, 检测早期假设/选型/符号是否被后续阶段事实推翻。冲突时**定向回滚**, 而非整段重来。

---

## 触发时机

```
after stage 5: backtrack(targets=[stage_2, stage_3, stage_4])
after stage 6: backtrack(targets=[stage_3, stage_4, stage_5])
after stage 8: backtrack(targets=[stage_4, stage_5, stage_6, stage_7])
```

也可由用户手动触发: "做一次 L2 回检"。

---

## 回检矩阵 (核心)

| 检查项 | 来源阶段 | 验证阶段 | 检测方法 |
|--------|---------|---------|---------|
| 选题前提 | 1 | 2-9 | rationale 是否仍成立 |
| 子问题分解 | 2 | 5, 8 | 是否所有 Qi 都覆盖? Q3 复用 Q1/Q2? |
| 模型族选择 | 3 | 5, 6 | toy demo → 实际, 是否仍可解? 灵敏度下是否仍最优? |
| 假设 | 4 | 5, 6, 7 | stage 5 引入的隐式假设是否需要补到 stage 4? stage 6 是否推翻假设? |
| 符号一致 | 4 | 5, 8 | 全文符号唯一? 单位一致? |
| 时间预算 | 0 | 5, 8 | 是否超 30%? |

---

## L2 Critic Prompt 模板

```
You are a meta-reviewer doing cross-stage consistency check.

Read decision_log (provided below).
Check the following:

1. Are stage {early}'s assumptions/decisions still valid given stage {late}'s findings?
2. Any symbol/notation drift between stages?
3. Any assumption introduced in stage {late} that should have been in stage 4?
4. Any time budget overrun?

decision_log:
{json}

OUTPUT JSON:
{
  "trigger_stage": "stage_5",  // 触发 L2 的阶段
  "checks": [
    {
      "id": "...",
      "from_stage": <int>,
      "to_stage": <int>,
      "concern": "<具体描述>",
      "severity": "critical" | "warning" | "info",
      "evidence": "<指向 decision_log 的具体字段>",
      "recommended_action": "no_revert | patch | full_revert"
    }
  ],
  "verdict": "all_consistent" | "patch_needed" | "revert_needed"
}
```

---

## Action 三档

### `no_revert` (大多数情况)
- concern 是"小漂移", 不影响主体
- 处理: 在后续 stage 7 (评价) 或 stage 8 (写作) 显式记录, 例如:
  ```
  "本模型假设 X, 在 stage 6 灵敏度中发现实际数据呈现 Y 趋势, 
  但 ±10% 内主结论不变。详细讨论见 §7.2 缺点分析。"
  ```

### `patch` (中等)
- concern 是"局部修复"
- 处理: 在涉及阶段做 diff-only 修订, 不重做整个阶段
- 例: stage 4 假设 1 加一行限定条件; stage 5 Q3 加一段 "在 X 范围内适用"

### `revert_needed` (罕见)
- concern 是"模型结构性错误"
- 处理: 暂停 Skill, 报告用户, 用户确认是否 revert 到指定阶段
- 例: stage 6 灵敏度发现 stage 3 模型在 ±5% 都失稳 → 回 stage 3 重选

---

## Patch 流程

```python
def apply_patch(target_stage, concern):
    artifact = read_decision_log(target_stage)
    diff = generate_targeted_diff(artifact, concern)
    new_artifact = apply_diff(artifact, diff)
    write_decision_log(target_stage, new_artifact)
    log_event("patch", target_stage, concern.id, concern.field)
    
    # 检查是否触发后续阶段连锁更新
    downstream = stages_after(target_stage)
    for s in downstream:
        if depends_on(s, target_stage, concern.field):
            mark_for_review(s, target_stage, concern.field)
```

### `mark_for_review` 具体动作 (P2-3 展开)

不同下游 stage 的 review 范围不同, 不是无脑全重做:

| 下游 stage | review 范围 | 触发动作 |
|----------|----------|---------|
| **stage 5 (具体某 Qi)** | 仅该 Qi 的 Step C (sanity check) + Step D (子灵敏度) | 重跑这两步, 用同一 stage 5 代码框架; 若 sanity check 失败再升级到 Step B (求解) |
| **stage 6** | 仅最受影响的 1 个参数的 LHS 扰动 (而非全 600 次) | 抽样 50 个点验证 robust_intervals 是否仍成立; 不成立则全量重跑 stage 6 |
| **stage 7** | 仅 limitations 节, 加一条新限制条件 | 在 §7.2 加一段说明 "因 stage X patch, 本模型在 Y 范围内适用性变化" |
| **stage 8** | 涉及该 concern 的章节 | 用 extract_diff.py section-level patch 修订该章节 (不重写全文) |
| **stage 9** | 重跑 anti_pattern check + 涉及 panelist 重审一次 | 不重跑 5 panelist, 只重跑 weakest_panelist |

`depends_on(s, target_stage, field)` 判断方法 (用 stage frontmatter inputs 字段): 若 `s.inputs` 含 `target_stage.field`, 则依赖。

### 行动选项再细化

`recommended_action` 字段从 3 档扩为 5 档:

- `no_revert`: stage 7/8 显式记录, 不动模型 (默认)
- `patch_local`: 仅修改 target_stage 自身一个字段
- `patch_with_review`: target_stage 修 + 1-2 个 downstream `mark_for_review`
- `revert_partial`: 回滚 target_stage 一个 sub-field (e.g., 单条假设), 触发链式 review
- `revert_full`: 回滚整个 stage 重做 (罕见, 用户确认后才执行)

---

## 常见 L2 检测案例

### 案例 1: 符号漂移
- stage 4 定义 `α` 为折扣率
- stage 5 Q2 中 `α` 被用作拉格朗日乘子
- → patch: stage 5 Q2 改用 `λ`, 更新 stage 4 符号表

### 案例 2: 假设隐式引入
- stage 5 Q3 引入了"风险中性决策者"假设, 但 stage 4 没列
- → patch: stage 4 补假设 + 支撑

### 案例 3: 模型族不一致
- stage 3 选优化族, stage 5 Q3 突然用蒙特卡罗
- → 选项: (a) 在 stage 5 显式说明触发条件 + 在 §5.3 中专门一段讲方法切换;  (b) 回 stage 3 重选 (revert_needed)

### 案例 4: 灵敏度推翻假设
- stage 6 在 ±5% 下假设 1 (泊松) 被显著推翻 (KS 检验 p<0.01)
- → revert_needed (stage 4 假设 1) 或 patch (stage 7 评价节深入讨论)

### 案例 5: 时间预算超支
- stage 5 用了 40h, 预算 30h
- → no_revert, 但触发模式降级 (championship → standard)

---

## 与 L1 的区别

| | L1 | L2 |
|---|----|----|
| 触发时机 | 每阶段结尾 | stage 5/6/8 结尾 + 用户手动 |
| 范围 | 单阶段内部 | 跨多阶段 |
| 判据 | 5 维 rubric | 一致性 + 推翻关系 |
| 行动 | refine / block | no_revert / patch / revert |
| 频率 | 阶段 1-3 次 | 全程 3-5 次 |
| 预算 | 500 tokens/次 | 1500 tokens/次 |

---

## 输出与日志

每次 L2 触发后, 写入 `decision_log.events.log`:
```json
{
  "type": "L2_backtrack",
  "ts": "...",
  "trigger_stage": 5,
  "checks_count": 7,
  "actions_taken": {"no_revert": 5, "patch": 2, "revert": 0},
  "details": [...]
}
```
