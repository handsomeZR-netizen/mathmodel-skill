---
stage: 9
name: review
duration_h: 2-6
inputs: [paper.tex, decision_log_full, decision_log.competition]
outputs: [stage.9.{anti_patterns_check, panel_scores, weakest_section, redo_log, red_team_record, final_pdf_path, submission_ready}]
loads_reference: [competitions/<competition>/anti_patterns.md, competitions/<competition>/rubric_overlay.json, feedback_layer3_panel.md]
loads_template: [templates/latex/<competition>/]
feedback: [L1, L3_5_panel, red_team_in_championship]
next: SUBMIT
---

# Stage 9 — 终稿审核 + 视觉化润色 + Panel 多视角评审

**时长**: 2-6h (cumcm 2-4 / mcm 4-6 / diangong 2-4) | **反馈层**: L1 + L3 panel | **冲刺最后一步**

---

## 目标

把 stage 8 的论文从 "完整可读" 推到 "评委想给最高奖"。核心是**多视角对抗审查 + 反模式逐条对照** (按 competition 切换 anti_patterns 与 panel personas)。

---

## 输入

- `paper.tex` (stage 8 产出)
- 全部 figures/ tables/
- decision_log 全部
- **按 competition 加载** (路径: `<skill>/competitions/<decision_log.competition>/`):
  - `anti_patterns.md` (逐条对照 — cumcm 32 条 / mcm seed 15 条 / diangong seed 10 条)
  - `rubric_overlay.json` 的 `panel_personas` (panel 5 视角 — 三竞赛各异)

## 产出

- 最终 `paper.pdf` (xelatex 编译完成)
- L3 panel 5 视角评分 + 瓶颈段一次重做
- (championship) red-team 攻击与回应记录

---

## 操作流程

### Step 1: 反模式逐条对照 (45 min) ⭐

**强制读** `references/anti_patterns.md`, 32 条逐项打勾:

```
A. 摘要类 (5 条)
[ ] A1. 摘要无定量结果? → 数 ≥3 个
[ ] A2. 摘要不分段? → 5 段
[ ] A3. 摘要与论文不符? → 交叉对照
[ ] A4. 关键词低质量? → 检查
[ ] A5. 摘要过短/长? → 600-900

B. 假设与符号 (6 条)
[ ] B1. 假设无支撑? → 全有
[ ] B2. 假设过多? → ≤7
[ ] ...

C. 模型选型 (5 条)
[ ] ...

D. 求解 (5 条)
[ ] D1. 代码无注释? → 中文注释
[ ] ...

(E-J 共 16 条同样)

E. 结果分析 (4 条)
F. 灵敏度 (4 条)
G. 子问题协调 (2 条)
H. 评价 (3 条)
I. 写作呈现 (5 条)
J. 流程协作 (3 条)
```

每条:
- 命中 high-severity → 立即修
- 命中 medium → 标记, panel 后再决定是否修
- 通过 → ✅

### Step 2: 视觉化润色 (45 min)

**图**:
- 字号 ≥9pt? (anti_pattern E3)
- 配色统一 (matplotlib + seaborn-deep, 不要默认 tableau)
- 标题简短信息密度高 (e.g., "图 5: 多变量 LHS 灵敏度散点矩阵")
- 横纵轴标签 + 单位
- legend 位置不遮挡

**表**:
- LaTeX booktabs (`\toprule \midrule \bottomrule`)
- 数值对齐 (千分位、小数位统一)
- 单位放在表头或单独列

**公式**:
- 编号格式统一 ((5.1) 还是 (5.1.1)?)
- 长公式分行, 用 `align`
- 关键公式给文字解释

**全文一致性**:
- 字体: 西文 Times / 中文宋体 / 标题黑体 (cumcmthesis 默认)
- 段间距: 1.0 倍
- 双倍行距 / 1.5 倍 (按官方要求)

### Step 3: L3 5 视角 Panel (1h) ⭐ 核心

完整 5 视角定义、JSON schema、聚合器、定向重跑逻辑见 **`references/feedback_layer3_panel.md`** (单一权威源, 不在此重复)。

**调用范式** (Claude 在此 stage 实际操作):

```
单条消息内并发 5 个 Agent 子代理 (subagent_type=general-purpose):

Agent 1 → prompt: "<feedback_layer3_panel.md §Panelist 1 数学严谨视角的 prompt + paper.tex 内容>"
Agent 2 → prompt: "<§Panelist 2 模型创新视角>"
Agent 3 → prompt: "<§Panelist 3 代码正确视角>"
Agent 4 → prompt: "<§Panelist 4 写作呈现视角>"
Agent 5 → prompt: "<§Panelist 5 评委视角 — 最关键>"

每个 Agent 独立返回一份 JSON (按 layer3 schema), 主流程聚合。
```

**降级方案**: 若环境不允许并发子代理, 改为串行但**每个 panelist 单独 conversation**:
- 每个 panelist 起新 conversation, 加载自己的 prompt + paper, 输出 JSON 文件
- 不同 panelist 之间不共享 context (避免互相污染)
- 主进程读 5 个 JSON 文件做聚合

不论并发还是串行, **聚合逻辑** 见 `feedback_layer3_panel.md` "聚合器" 节。

#### 聚合: 找瓶颈段

```python
panelist_scores = [...]  # 5 份
overall_min = min(panelist_scores, key=lambda p: p["mean_score"])
weakest_panelist = overall_min["panelist"]
weakest_concerns = overall_min["must_fix"]

# 把 must_fix 映射回阶段
mapped_stages = map_concerns_to_stages(weakest_concerns)
# e.g., "代码注释" → stage 8 §附录
# e.g., "灵敏度仅 2 参数" → stage 6
```

### Step 4: 定向重跑瓶颈段 (45 min)

只针对 panel 找出的 must_fix 修, 不重做整个阶段:

```
def targeted_redo(weakest_concerns, paper_tex):
    for concern in weakest_concerns:
        if concern.severity == "high":
            # diff-only 修订
            patch = generate_patch(concern, paper_tex)
            paper_tex = apply_patch(paper_tex, patch)
        elif concern.severity == "medium":
            log(concern)  # 记录但暂不修, 时间紧时跳过
    return paper_tex
```

### Step 5: 二次 Panel (15 min)

重做后再跑一次 panel (只对修订段落):
- 若 panelist 5 (评委视角) 评分上升 → 收工
- 若仍未达标且时间预算用尽 → 提交当前版本

### Step 6: (championship) Red-team 终极攻击 (30 min)

```
你是国赛历史上最严苛的评委, 你的任务是给这篇论文找出 ≥3 个 reject 理由,
并模拟你会写在评分表上的批注。然后, 论文作者(你扮演)给出 100 字以内的反驳。
```

输出:
```json
{
  "attacks": [
    {"point": "...", "reviewer_note": "...", "rebuttal": "..."},
    ...
  ]
}
```

如反驳力弱 → 修, 如反驳有力 → 在 §7 评价节加一条"潜在质疑回应"。

### Step 7: xelatex 编译 + PDF 输出 (15 min)

```bash
cd D:\desktop\paper-workspace\
xelatex paper.tex
xelatex paper.tex   # 二编以解决目录与交叉引用
xelatex paper.tex   # 三编 (保险)
```

检查:
- [ ] PDF 总页数 22-25 (排除附录)
- [ ] 无未解决的 `??` 交叉引用
- [ ] 无 underfull/overfull 大量警告
- [ ] PDF 可正常打开

### Step 8: 最终输出 (5 min)

写入 `decision_log.stages.9`:
```json
{
  "anti_patterns_check": {"total": 32, "passed": 30, "fixed": 2, "deferred": 0},
  "panel_scores": {
    "panelist_1_math": {...},
    "panelist_2_innovation": {...},
    "panelist_3_code": {...},
    "panelist_4_writing": {...},
    "panelist_5_judge": {...}
  },
  "weakest_section": "...",
  "redo_log": [...],
  "red_team_record": [...],
  "final_pdf_path": "paper.pdf",
  "submission_ready": true
}
```

---

## L3 Panel 退出条件

- panelist 5 (评委视角) verdict ∈ {"first", "second"} → 提交
- 若 "third" 但时间预算耗尽 → 提交 + 标记 (没办法)
- 若 "first" 且 mean ≥ 9.0 → 庆祝 🎉

## L1 Stage Rubric

| 维度 | 满分 |
|------|-----|
| 1. 反模式覆盖 | 32/32 通过或 ≥30 |
| 2. 视觉一致性 | 字号/配色/字体全统一 |
| 3. Panel 一致性 | 5 视角 mean ≥ 8 |
| 4. 瓶颈处理 | weakest must_fix 已修 |
| 5. PDF 编译 | 无错误, 22-25 页 |

## 退出条件 (整个 skill 终点)

1. 反模式 32 条全部通过
2. L3 panel mean ≥ 8, panelist 5 verdict ≥ "second" (理想 "first")
3. PDF 编译成功
4. (championship) red-team 攻击全部有可信回应
5. decision_log.stages.9.submission_ready == true

→ **提交!**
