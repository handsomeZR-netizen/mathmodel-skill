---
stage: 4
name: foundation
duration_h: 1
inputs: [stage.2.key_variables, stage.3.selected_per_subproblem]
outputs: [stage.4.{assumptions, symbols, terminology, consistency_check}]
loads_reference: [rubrics.md§Stage_4, anti_patterns.md§B]
loads_template: [assumption_table.md, notation_table.md]
feedback: [L1]
next: stage_05_subproblem_loop
---

# Stage 4 — Foundation (假设 + 符号 + 术语 一体化)

**时长**: 1h | **反馈层**: L1 | **特点**: 短但关键,任何下游不一致都从这里溯源

---

## 目标

把假设 / 符号 / 术语**一次性**系统化成正式的论文章节素材,确保 stage 5-9 不会出现 "符号变了"、"假设忘了"、"术语没定义" 等基础失分。

---

## 输入

- stage 2 全局变量表
- stage 3 选定模型 (隐含一些假设)

## 产出

- 假设清单 (3-7 条,每条带支撑) → 论文 §3
- 符号说明表 (含单位、类型) → 论文 §4
- 术语表 (专业词、缩写) → 论文 §4 附录或脚注
- 写入 `decision_log.stages.4`

---

## 操作流程

### Step 1: 假设挖掘 (20 min)

从三个维度提问:

**a) 模型隐含假设** (来自 stage 3 选型):
- 选 LP → 暗含线性关系假设
- 选 蒙特卡罗 → 暗含分布假设
- 选 SIR → 暗含均匀混合假设

**b) 数据假设** (来自附件扫描):
- 附件数据无系统偏差
- 缺失值机制 MCAR (随机缺失)
- 时间序列平稳

**c) 环境假设** (来自题目语境):
- 短期内市场/政策/物理环境不变
- 决策者理性
- 无外部冲击

3 维度合计 5-15 条 → 筛留 3-7 条核心。

### Step 2: 假设支撑(每条必须有) (15 min)

每条假设附 1 个支撑,三选一:

```
假设 1: 短期内市场需求服从泊松分布。
依据: 文献 [3] 在零售行业类似场景下采用相同假设, 
      且对附件 1 数据 χ² 检验 p=0.34, 不拒绝泊松假设。

假设 2: 运输车辆匀速行驶。
依据: 附件 2 显示 95% 行程的速度方差 <5km/h, 平均速度变异系数 <8%。

假设 3: 不同产品的生产线可独立排产 (无共享资源)。
依据: 题目附件 4 流程图显示生产线物理隔离。
```

**反模式 B1 (假设无支撑)** 自动检测: 如有 "假设 X" 后无 "依据" 字样 → block。

### Step 3: 符号表正式化 (15 min)

复制 stage 2 全局变量表,补全:

| 符号 | 含义 | 单位 | 类型 | 取值范围 |
|------|-----|------|------|---------|
| x_i | 第 i 个产品产量 | 件 | 决策变量 | x_i ∈ Z, [0, 100] |
| p_i | 第 i 个产品单价 | 元/件 | 参数 | 附件 1 |
| d_i | 第 i 个产品需求 | 件 | 随机变量 | d_i ~ Pois(λ_i) |
| α | 折扣率 | 无量纲 | 参数 | [0, 1] |
| **总数** | ≥10 |

**反模式 B5 (无单位)** 自动检测: 单位列空 → block (除非 "无量纲" 显式标注)。
**反模式 B4 (符号重复)** 自动检测: 同一符号不同行 → block。

下标约定:
- i: 产品索引, i = 1, ..., n
- t: 时间索引, t = 1, ..., T
- s: 场景索引, s = 1, ..., S

### Step 4: 术语表 (5 min)

专业术语 + 中英对照:

| 中文 | 英文 | 缩写 | 首次出现章节 |
|------|------|------|------------|
| 拉格朗日松弛 | Lagrangian Relaxation | LR | §5.1.2 |
| 拉丁超立方抽样 | Latin Hypercube Sampling | LHS | §6.1 |
| 鲁棒优化 | Robust Optimization | RO | §5.3 |

### Step 5: 一致性预检 (5 min)

回扫 stage 2-3 的所有产出,对照本文:
- 任何 stage 2 提到的变量,本文表中都有?
- stage 3 选模型时提到的 "假设 ABC",本文都列了?

如有不一致 → 立即修正,不要拖到 stage 5 才发现。

### Step 6: 输出 (5 min)

写入 `decision_log.stages.4`:
```json
{
  "assumptions": [
    {"id": "A1", "content": "...", "support": "...", "support_type": "literature|data|physical"},
    ...
  ],
  "symbols": [
    {"symbol": "x_i", "meaning": "...", "unit": "...", "type": "decision|parameter|state|random", "range": "..."},
    ...
  ],
  "terminology": [
    {"zh": "...", "en": "...", "abbrev": "...", "first_appearance": "§5.1"}
  ],
  "consistency_check": {"with_stage2": "pass", "with_stage3": "pass"}
}
```

---

## L1 Rubric

| 维度 | 满分行为 |
|------|---------|
| 1. 假设数量 | 3-7 条 |
| 2. 假设支撑 | 每条必须有 |
| 3. 符号唯一性 | 无重复 + 全有单位 |
| 4. 与模型一致性 | 与 stage 3 无矛盾 |
| 5. 术语规范 | ≥3 专业词,中英对照 |

## 常见坑

- B1 假设无支撑 → Step 2 强制
- B2/B3 假设过多/过少 → 3-7 硬约束
- B4 符号重复 → Step 3 自动检
- B5 无单位 → Step 3 自动检
- 与 stage 5 不一致 → Step 5 预检 + L2 后续回检

## 退出条件

1. 假设 3-7 条,每条有支撑
2. 符号表 ≥10 项, 全有单位与类型
3. 术语 ≥3 项 (若适用)
4. 一致性预检通过
5. L1 全维 ≥7

→ 跳转 `stage_05_subproblem_loop.md`

---

## 与 stage 5/8 的衔接

stage 5 建模时,任何用到的符号必须先在本文表中。
stage 8 写论文 §3 §4 时,直接复用本文产出 (winning_patterns §6 加分点)。
