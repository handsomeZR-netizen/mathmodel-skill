---
stage: 0
name: kickoff
duration_h: 1
inputs: [user_inputs.{problem_id, team_size, deadline, pdf_path}]
outputs: [stage.0.{team_roles, tools_ready, problem_scan, time_budget_h, collab_protocol, checklist_completed}]
loads_reference: [winning_patterns.md]
loads_template: [decision_log.json, requirements.txt]
feedback: [L1]
next: stage_01_problem_selection
---

# Stage 0 — 团队启动与资料预扫

**时长**: 1h | **反馈层**: L1 | **触发**: skill 首次启动 / 用户说"开始建模"

---

## 目标

在题目正式公布前(或公布后立即),把队伍状态调到"上手即可执行",避免后续阶段因协作/工具/角色问题反复返工。

---

## 输入

- 用户提供: 队员数 (默认 3) / 截止时间 / 模式偏好
- (若题目已发布) 题目 PDF 文件路径

## 产出

- `state/decision_log.json` 初始化,问题元信息填好
- 角色分工表 (写入 `decision_log.stages.0.team_roles`)
- 工具就绪 checklist
- 初步问题域识别 (优化 / 预测 / 评价 / 分类 / 仿真 / 综合) → 影响 stage 3

---

## 操作流程

### Step 1: 元信息收集 (5 min)

询问用户:
1. 题号 (A/B/C/D/E,等公布)
2. 队员数与各人擅长 (建模 / 编程 / 写作 / 数学 / 算法)
3. 截止时间 (UTC+8 ISO 字符串)
4. 模式偏好 (默认 standard)

写入 `decision_log.problem_meta`。

### Step 2: 角色分工 (10 min)

强制 3 主责 + 互备:

| 角色 | 主责内容 | 互备 |
|------|---------|------|
| **建模主** | stage 2/3/4/5 主导,数学公式 | 编程主 |
| **编程主** | stage 5 求解、stage 6 灵敏度 | 建模主 |
| **写作主** | stage 8 主导,stage 1/9 协助 | 全员 |

**反模式 J1** (anti_patterns.md): "三人都全栈但都不深" — 拒绝。
强制每人写一句"我对这道题/这个角色的最大顾虑是什么"。

### Step 3: 工具就绪 checklist (15 min)

逐项确认 (bash 验证):

```bash
python --version           # ≥ 3.9

# 完整依赖检查 (一次性安装见 templates/requirements.txt)
python -c "import numpy, scipy, sklearn, cvxpy, matplotlib, pandas, statsmodels, seaborn, SALib, pdfplumber, imblearn"

# 关键 solver 检查 (优化类必备)
python -c "import cvxpy; assert 'GLPK_MI' in cvxpy.installed_solvers(), '需 pip install cvxopt'"

# LaTeX 必备
xelatex --version          # cumcmthesis 用 xelatex (非 pdflatex)

which git
```

如缺依赖, 一键安装:
```bash
pip install -r <skill>/templates/requirements.txt
```

**目录初始化** (路径协议: cwd 相对):
```bash
mkdir -p cwd/state cwd/results cwd/figures cwd/paper_workspace
cp <skill>/templates/decision_log.json cwd/state/decision_log.json   # 仅当不存在时
```

确认:
- `<skill>/templates/cumcmthesis/cumcmthesis.cls` 存在 (LaTeX 模板)
- `<skill>/references/papers/` 已含 91 篇真题 PDF (静态资料, 不读)

### Step 4: 题目预扫 (题目公布后,15 min)

用户提供题目 PDF 后,Claude 用 Read 工具读 PDF (前 5 页) 做快速识别:

输出格式:
```json
{
  "problem_id": "2024-A",
  "domain_keywords": ["调度", "最优化", "时变"],
  "data_attachments": ["附件1: ...", "附件2: ..."],
  "subproblem_count": 3,
  "primary_problem_type": "优化类",
  "secondary_types": ["仿真类"],
  "estimated_difficulty": "medium",
  "data_size_signal": "中等 (附件 ≤ 50MB)"
}
```

写入 `decision_log.events.log`,作为 stage 1 输入。

### Step 5: 时间预算分配 (10 min)

根据 deadline 倒推 (h):

| 阶段 | 默认配额 | 调整建议 |
|-----|---------|---------|
| 0 | 1 | 固定 |
| 1 | 3 | 选题难度大可加 1h |
| 2 | 3 | 多子问题可加 1h |
| 3 | 3 | 不熟悉的领域可加 1h |
| 4 | 1 | 固定 |
| 5 | 30 (10/子问题) | 主体,保大头 |
| 6 | 3 | 固定 |
| 7 | 2 | 固定 |
| 8 | 20 | 主体,保大头 |
| 9 | 4 | 固定 |
| **buffer** | **2** | 应急 |
| **合计** | **72** | 国赛 3 天 |

如总剩余 < 72h,按比例压缩,但 stage 5/8 不低于 60% 的默认值。

### Step 6: 协作约定 (5 min)

写入 `decision_log.stages.0.notes`:
- 命名规范: 文件 / 变量 / Python 模块
- 版本控制: git 提交频率 (每 2h 一次)
- 沟通节奏: 每 4h 5 分钟同步
- 求助升级: 卡住超 1h 必须群内 broadcast

---

## L1 Rubric (5 维 × 1-10)

参考 `rubrics.md` Stage 0 节。每维必须 ≥7 才通过。

```json
{
  "stage_id": 0,
  "scores": {
    "1_role_clarity": {...},
    "2_tools_ready": {...},
    "3_time_planning": {...},
    "4_problem_scan": {...},
    "5_collab_protocol": {...}
  }
}
```

## 常见坑 (anti_patterns)

- **J1**: 三人都全栈不深 → 强制角色主责
- **J2**: 选题摇摆 (跳到 stage 1 才出现)
- **J3**: 写作留到最后 → time budget 把 stage 8 提前到 day 2

## 退出条件

1. `decision_log.stages.0.checklist_completed == true`
2. 团队角色明确,工具全员 ready
3. (若题目已发布) 题目预扫完成
4. L1 rubric 全维 ≥7

→ 跳转 `stage_01_problem_selection.md`

---

## 与 Stage 1 的衔接

把 Step 4 的题目预扫 JSON 作为 stage 1 的"上下文输入"传过去,避免重新读题。
