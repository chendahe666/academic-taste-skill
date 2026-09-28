# 先验透镜：前人总结过的品味与写作原则

这些是**待检验的假设**，不是结论。用法：Stage 3 归纳时拿它们去对照语料——语料支持的写进规则并注明"与 X 一致"；语料不支持的更要写出来，那往往就是这个领域的特殊之处。不要把这些原则直接当成领域品味写进画像。

| 来源 | 核心主张 | 在语料里可以检验什么 |
|---|---|---|
| Murray S. Davis, *That's Interesting!* (Philosophy of the Social Sciences, 1971) | 让人觉得"有意思"的理论，是否定了读者一部分默认假设的理论："看起来是 X，其实是非 X"。他归纳了十几类反转，如看似无序其实有序、看似局部其实普遍、看似稳定其实在变、看似独立其实相关、看似因其实是果 | 高档论文的 insight 是否更多是"反转默认假设"型？卡片 §7 记录属于哪一类 |
| Jennifer Widom, *Tips for Writing Technical Papers* (Stanford, 2006) | introduction 要回答五个问题：问题是什么；为什么有趣、重要；为什么难；为什么以前没解决；我的方法和结果的关键是什么 | 低档论文是否常缺"为什么难"或"为什么以前没解决"（对应 CHALLENGE / ROOT-CAUSE） |
| Simon Peyton Jones, *How to Write a Great Research Paper*（报告） | 一篇论文只传达一个清晰的 idea；introduction 讲清问题并明确列出贡献，贡献要写成可以被反驳的论断；用例子带出一般性 | 高档论文的贡献是否更可检验；有没有唯一明确的 insight 句 |
| Richard Hamming, *You and Your Research* (1986) | 重要的问题不是"重要的话题"，而是"重要且有可行切入点"的问题 | 高档论文是否更早讲清"为什么现在能做了"（新工具、新观察） |
| Sandberg & Alvesson, *Ways of Constructing Research Questions: Gap-Spotting or Problematization?* (Organization, 2011) | 多数论文靠补空白（gap-spotting），真正有影响的工作更常质疑已有假设（problematization） | A2（假设挑战）在高档的占比是否更高；B6（假设不现实）类 gap 的分布 |
| Michael J. Black, *Novelty in Science*（博客，2022） | 新颖不等于复杂；事后看起来显然的简单 idea 也是新颖的，审稿人不该因为"显然"而否定它 | A6（反直觉简化）在高档的表现；被拒稿的评审里是否出现"too simple / incremental"之类的批评 |
| Lipton & Steinhardt, *Troubling Trends in Machine Learning Scholarship* (2018) | 四种坏趋势：解释和猜测不分；说不清性能提升到底来自哪里；为了显得有深度堆砌数学；滥用术语和夸大的措辞 | 强度 F4（夸张）是否集中在低档；高档是否更常说明收益来源 |
| Kayvon Fatahalian, *What Makes a (Graphics) Systems Paper Beautiful*（博客） | 系统类论文要先讲清目标和约束，再说明每个设计决策怎么服务于这些目标 | 系统 / 效率类论文里，高档是否更早讲清目标和约束（SCOPE / STAKES） |

## 常见的"假设"，在具体领域里经常不成立

以下说法流传很广，但在不同领域里差异很大，一定要用语料检验：
- "一定要用具体失败例子开头"：有些领域（理论、系统）更偏爱开门见山地给出问题。
- "introduction 越短越好"：有些社区（HCI、系统）introduction 通常更长，因为要交代场景和需求。
- "不要在 introduction 放数字"：很多 ML 高档论文恰恰在 ¶1 或 Figure 1 就给出关键数字。
- "Figure 1 一定是 teaser 结果图"：视觉 / 图形学常见，理论和 NLP 常常没有首图。
