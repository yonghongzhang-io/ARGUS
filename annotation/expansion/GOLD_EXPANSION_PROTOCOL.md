# Gold 扩容协议：5 → 15 篇，两阶段标注

**目的**：把 human gold 从"诊断性 pilot"升级为能支撑准确性结论的评测集，
并用两阶段标签解决 pilot 中暴露的核心问题——专家分歧大多来自
**维度是否适用**（continuous-shock / event-study 等非标准设计），而非严重度本身。

## 第 1 步：选论文（30 分钟）

打开 `candidate_papers.csv`（22 篇候选 = 27 篇语料减去 5 篇 pilot，
**env/energy 5 篇排最前**）。在 `selected` 列标 `y` 选 10 篇，原则：

- **5 篇 env/energy 全选**（气候定位 + 论文的 env-vs-other 对比就有对称样本）；
- 其余 5 篇跨领域挑（finance / health / education / trade / labour 各 ~1）；
- 有意识包含**非标准设计**（event-study、continuous exposure）——两阶段标签的
  价值恰恰在这些论文上；
- 优先挑你判断**可能存在 high risk 维度**的论文（pilot 只有 2 个 high cell，
  是统计效力的最大短板）。

选好后运行 `python3 annotation/expansion/make_template.py` 生成
`gold_expansion_template.csv`（10 篇 × 11 维 = 110 行）。

## 第 2 步：两阶段标注（每人每篇 ~1.5–2.5 小时 × 10 篇，双标注）

每格先标 **Stage A（适用性）**，仅当 applicable 才标 **Stage B（证据风险）**：

| 字段 | 取值 | 说明 |
|---|---|---|
| `applicability` | `applicable / not_applicable / unclear` | 该维度对这个设计是否有意义（如非交错设计 → staggered timing 常为 n/a） |
| `evidence_risk` | `low / medium / high`（仅 applicable 时） | 论文报告的证据支撑该 assumption 的充分度 |
| `evidence_span` | 逐字粘贴 | 支撑你判断的最关键证据（顺带完成 oracle 扩容） |
| `evidence_location` | `text/table/figure/footnote/appendix/none` | |
| `confidence` | `high / low` | |
| `notes` | 自由 | 分歧点、边界情况 |

**双人独立标注**（沿用 pilot 的第二标注人，brief 在
`annotation/second_annotator_brief.md` 基础上加 Stage A 定义即可），
分歧走一轮 adjudication，**保留 adjudication rationale**（写进 notes）。

## 第 3 步：交付后我来算的

- applicability-aware κ（分歧按两阶段分解：适用性分歧 vs 严重度分歧）；
- 更新 vs-gold 全套表（over-severity、exact、weighted κ、high P/R——high cell
  变多后这些指标才有统计意义）；
- calibration 层在新 gold 上重新拟合与验证（当前规则是否过拟合 5 篇 pilot）；
- env/energy vs other 的 gold 层面对比（此前只有系统输出层面）；
- oracle-evidence 实验自动扩展到 15 篇。

## 时间预算

- 你 + 第二标注人：各 ~15–25 小时，可分 2 周做完；
- 我这边全部计算 + 论文改写：结果到手后 1 天内完成；
- 这是从 workshop 论文走向 Findings/期刊版本的**核心增量**（外部评审与我一致的判断）。
