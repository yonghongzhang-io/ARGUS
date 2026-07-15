# Oracle-evidence 标注协议（5 篇 pilot 论文）

**目的**：直接检验论文的中心命题——ARGUS 判断错，是因为**没找到证据**（retrieval 瓶颈），
还是**找到了但理解错**（reasoning 瓶颈）。做法：把「专家指定的证据」直接喂给 adequacy
assessor，与「ARGUS 自己检索的证据」对照。

## 你要做的（预计 3–5 小时）

打开 `evidence_spans_template.csv`（55 行 = 5 篇 pilot 论文 × 11 维度，
每行已预填维度名 / assumption / expected_evidence 作提示）。对每行：

1. 在该论文 PDF 里找到**与这个识别维度最相关的证据**（支持或反驳该 assumption 的
   段落 / 表 / 图注 / 脚注 / 附录）。
2. `evidence_span_1`：**逐字粘贴**该段文字（1–4 句即可；表/图则粘贴其标题+关键数字行）。
3. `span_1_location`：位置类型，取值之一
   `text | table | figure | footnote | appendix`（可附节名，如 `text: Section 5.2`）。
4. 若有第二处重要证据，填 `evidence_span_2/…`（没有就留空）。
5. **论文里确实没有该维度的任何证据** → `no_evidence_in_paper` 填 `y`，spans 留空。
   （这个标签本身就是关键数据：它把"检索失败"与"论文真没报告"分开。）
6. 拿不准就写 `notes`。

**只标证据，不改 risk**——risk 的 gold 已在 `data/annotations/gold_labels.csv`。

## 交付后我来跑的（~$5，你不用管）

1. **Oracle assessment**：对 55 格，把你的 spans 直接喂给 adequacy 调用
   （跳过检索与 gate）→ oracle risk。
2. 三方对照：oracle risk vs ARGUS 全管线 risk vs 人工 gold：
   - oracle 下 exact agreement / over-severity 是否显著改善 → 支撑
     "reasoning 相对可靠，grounding 是主导瓶颈"；
   - 若不改善 → 说明 rubric/判断本身也有问题（同样是重要发现，如实报告）。
3. **Retrieval recall**：ARGUS 检索到的条目是否覆盖你标的 span
   （Evidence Recall@k、逐位置类型的覆盖率——图/表是否更常丢）。

产出：论文新增一节 oracle-evidence 分析 + 一张 retrieval-vs-assessment 分层表。
