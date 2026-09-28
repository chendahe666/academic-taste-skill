---
name: academic-taste
description: 为某个具体研究领域蒸馏学术品味（academic taste）：分档采样该领域近几年顶会论文（award / oral / spotlight / 高引 / 普通 poster / 被拒），盲读并拆解每篇 introduction——idea 从哪来、idea 长什么样、故事怎么讲、Figure 1 和贡献怎么写——再用各档之间的对比归纳出该领域的"品味画像"，最后拿画像去帮用户已经选定的题目定故事线、写 introduction 骨架、预判审稿反应。选题完成之后（例如 research-ideation 跑完之后）用。当用户说想学/蒸馏/提炼某领域的 taste、品味、审美、"好论文的标准"，想知道某领域顶会论文的 idea 怎么来的、故事怎么讲、introduction 怎么写，想分析 oral 和 poster 或被拒论文差在哪，或者已经有了题目、想按目标会议的口味讲好故事、写 intro、画 Figure 1 时，都应该用这个 skill，即使用户没有说出 "taste" 这个词。Use for distilling a research field's academic taste from contrasting top-venue papers and applying it to framing a chosen research idea.
---

# 学术品味蒸馏（Academic Taste Distiller）

**品味是一种判别力，要靠对比来学。** 读一万篇普通论文只会学到平均水平；要看的是同一领域里，为什么这篇拿了 oral 或 best paper、那篇只是 poster、另一篇被拒。所以本 skill 的每一步都围绕"分档对比"展开，而不是泛读。

品味拆成三层，分开归纳：
- **选题品味**：这个领域奖励什么样的问题和洞见，idea 通常从哪里来。
- **叙事品味**：introduction 怎么开头、怎么立 gap、洞见放在哪一段、Figure 1 起什么作用、贡献怎么列、话说到多满。
- **证据品味**：introduction 许诺了什么证据，审稿人认什么样的实验。

有一个前提要一直记着：**introduction 讲的是事后重构的故事，不一定是 idea 真实的来历。** idea 的真实来源要结合作者 talk、博客、Test-of-Time 演讲、以及文中点名"受到启发"的前作去推断，并标明置信度。

## 和 research-ideation 的关系

`research-ideation` 负责从领域到选题（Stage 0–8）。本 skill 接在它后面：题目已定，要学会目标领域的口味，并把题目讲成这个领域愿意买账的故事。
- 如果当前目录下有 `ideation/<slug>/`，先读 `00_profile.md`（领域、目标 venue）、`03_gap_ledger.md` 末尾的**本领域审稿画像**、`05_idea_pool.md` 或 `08_proposal.md`（用户选定的 idea），能复用的都复用，不要重复问用户。
- 用户没有跑过 research-ideation 也可以直接用；这时 Stage 0 多问一句"你的题目是什么"。

## 工作区与总规则

- 在当前目录建 `taste/<field-slug>/`（用户另有指定就听用户的）：
  `00_scope.md` → `raw/`（语料、introduction 原文、作者访谈等）→ `cards/`（每篇一张拆解卡）→ `01_taste_profile.md` → `02_apply_<idea-slug>.md` → `03_calibration.md`（可选）。
- 同一领域已有 12 个月内的 `01_taste_profile.md`，直接进入 Stage 4，不重做。
- **不编造论文，也不凭记忆拆解。** 语料里的每篇论文都来自脚本或检索结果；拆解卡只能基于实际抓到的原文。某篇抓不到原文，就标"未读"，不要用记忆补。你对著名论文的印象可以写进卡片的"背景知识"栏，但要和原文证据分开。
- **每条品味规则都必须是对比性的、带计数的**：写成"高档 a/b 篇 vs 低档 c/d 篇"，附至少 3 篇例证和 1 篇反例。说不出对比的，只算"观察"，不算规则。"写得清楚""实验充分"这种放之四海皆准的话不算这个领域的品味。
- **小样本要谦虚。** 每档 8 篇左右时，差距小于 3 篇的都算噪声。规则按强度分级（见 [references/taste_profile_template.md](references/taste_profile_template.md)）。
- **引用原文只用短句**（每处不超过约 25 个词），原文全文只留在本地 `raw/`，不要大段复制进输出。
- 输出用用户的语言，术语保留英文原词（gap、insight、teaser figure、contribution）。
- **人类检查点沿用 research-ideation 的导师模式**：给默认建议和依据、最多 3 件需要用户亲手核实的事、一行就能回复的格式。只有两处必须用户拍板：Stage 0 的范围，Stage 4 结尾选哪种故事线。

## 四种模式

- **完整模式**（默认）：Stage 0 → 4，每档约 8 篇，共 30–50 篇精读。一般一两次会话。
- **快速模式**：每档 4 篇、可以不要被拒档，约 15 篇。画像标"低置信"。用户赶时间或只想先看看时用。
- **应用模式**：已有画像，直接做 Stage 4。
- **校准模式**：只做 Stage 5，检验画像到底有没有判别力。

---

## Stage 0：定范围 ⏸（必须用户拍板）

一条消息问完，用可填表格，每项都给默认值：

| 项 | 默认值 / 说明 |
|---|---|
| 领域 | 收窄到一个子方向、一个社区，例如"LLM 推理时计算"而不是"NLP"。不同社区的品味差很多，混在一起会互相抵消。 |
| 目标 venue | 用户要投的会议，加上同社区的 1–2 个顶会 |
| 年份 | 近 3 年为主（品味会漂移；5 年以上的只取 award / test-of-time） |
| 检索词 | 2–4 个短语，给出你的建议 |
| 用户的题目 | 从 ideation 文件读取，或请用户用 3–5 句话描述：问题、洞见、方法、目前有什么结果 |
| 规模 | 完整模式 / 快速模式 |

然后根据 venue 选数据源（写进 `00_scope.md`）：

| venue 类型 | 能拿到的档 | 做法 |
|---|---|---|
| OpenReview 会议：ICLR（公开被拒稿，最适合做对比）、NeurIPS / ICML（接收论文分档，被拒稿大多不公开）、COLM、CoRL、TMLR 等 | oral / spotlight / poster / rejected / withdrawn | `build_corpus.py -t ... -v ...` |
| 非 OpenReview：CVPR / ICCV / ECCV、ACL 系、系统（OSDI/SOSP/NSDI）、安全（S&P/CCS/USENIX Sec）、HCI（CHI/UIST）、理论等 | award / oral（若有公开名单）/ 高引 / 普通接收 | 用 WebSearch 找 best paper、outstanding paper、oral 名单，用 `--add` 手动加入；`--hc-query` 取高引档；普通接收论文从会议 proceedings 页面随机挑，用 `--add poster:<标题>` 加入 |

没有被拒档时，对比就变成"award / oral / 高引 vs 普通接收"。这时要在画像里说明：学到的是"好与更好"的差别，不是"过与不过"的差别。

## Stage 1：建语料

1. 跑分档采样（Windows 上 `python` 不可用就用 `py`；脚本要跑几分钟，放后台跑）：
   ```bash
   python "<skill_dir>/scripts/build_corpus.py" -t "test-time compute" -t "inference-time scaling" \
       -v ICLR.cc/2025/Conference -v ICLR.cc/2026/Conference -v NeurIPS.cc/2025/Conference \
       --citations --per-tier 8 --hc-query "test-time compute" --from 2023 \
       --add "award:<arXiv id 或标题>" --out taste/<slug>/raw/corpus
   ```
   - 脚本输出 `corpus.md`，里面有该话题在各 venue 的**档位分布**（例如 oral 占多少）。这是本领域的基准比例，写进画像。
   - `--citations` 会查引用数，把"当年普通 poster、后来被引很多"的论文单独分成 `poster_highcite` 档。这一档能看出"社区事后认可、但审稿时没被看出来"的东西。`--hc-query` 取该话题每年被引最多的论文（`highcite` 档）。
   - 每档抽到的论文都要有 arXiv 版本；确认没有的，会自动换成同档下一篇。
   - **限流是常态。** 引用数和 arXiv id 依赖 Semantic Scholar、OpenAlex、arXiv API 三个免费服务，匿名额度按 IP 共享，很容易被限流。脚本对每个服务单独熔断，不会卡死；被限流时查不了的论文会保留，并在 `corpus.md` 末尾列为 **needs id**。处理办法：
     - 用 WebSearch 搜 `"<标题>" arxiv` 找到 id，用 Edit 填进 `corpus.json` 对应论文的 `arxiv` 字段（要核对标题一致）；或者 15 分钟后重跑。
     - 建议用户申请免费 key，设成环境变量：`SEMANTIC_SCHOLAR_API_KEY`（semanticscholar.org/product/api，CS 领域引用数最准）、`OPENALEX_API_KEY`（openalex.org）。有 key 之后基本不会被限流。
     - 引用数只拿不到时，`poster_highcite` 和 `highcite` 两档会是空的。这时用 WebSearch 找该领域的高引论文，用 `--add highcite:<id>` 手动加几篇。
2. 用 WebSearch 补 award、best paper、test-of-time 论文（`--add award:...`），这些是上限样本。
3. **idea 来源的旁证**：给 award 档和高引档的论文，各搜一下作者的 talk、博客、访谈、Test-of-Time 演讲、以及"the story behind"一类的回顾。有就把链接和要点记到 `raw/origins.md`。这是唯一能区分"真实来历"和"事后故事"的材料，找不到就算了，不要硬凑。
4. **审稿意见（强烈建议，OpenReview 会议）**：如果装了 research-ideation，用它的 `openreview_reviews.py` 抓语料里论文的评审（需要用户自己的 OpenReview 账号，设环境变量；你不能替用户输入密码或过人机验证）。评审里的 strengths 字段说明审稿人**看重**什么，meta-review 说明**决定性**的是什么，被拒稿的 weaknesses 就是反模式的一手证据。没有账号就把 forum 链接给用户，让用户自己在浏览器里看，或把几篇评审粘贴过来。

⏸ 导师卡（推荐确认）：列出各档篇数，指出哪一档偏少、偏旧或混进了离题的论文；让用户扫一眼 `corpus.md`，删掉明显不属于这个领域的论文。

## Stage 2：盲读拆解

1. 抓 introduction：
   ```bash
   python "<skill_dir>/scripts/fetch_intros.py" --corpus taste/<slug>/raw/corpus.json --out taste/<slug>/raw/intros
   ```
   每篇一个文件（`P01.md`…），包含标题、摘要、Figure 1 说明、章节目录、分段编号的 introduction。补填了 arXiv id 之后，加 `--skip-existing` 重跑，只抓还缺的（同一份语料、同一个 seed，Pxx 编号不变）。**默认是盲的**：文件打乱顺序、不显示档位，档位写在 `key.json`。**在所有卡片写完之前不要打开 `key.json`**，否则会不自觉地给 oral 找优点、给被拒稿找毛病。盲读不完美（你可能认得出名作），认出来的在卡片里标"已识别"。
2. 按 [references/dissection_card.md](references/dissection_card.md) 给每篇写一张拆解卡，存到 `cards/Pxx.md`。卡片最后要**盲猜档位**，写上理由和置信度。这些猜测会在 Stage 5 用来衡量"仅凭 introduction 能分辨到什么程度"。
3. **超过 12 篇就并行**：用 Agent 工具开多个子代理，每个分 6–8 篇。每个子代理只拿到：拆解卡文件的路径、分给它的 `Pxx.md` 路径、输出目录。明确告诉它不要读 `key.json`、不要读别人的卡片。汇总后抽 2 张卡对照原文复核，防止子代理偷懒或编造。
4. 抓取失败的论文（没有 HTML 版本），可以用 WebFetch 读 `https://arxiv.org/pdf/<id>`；读不到就在卡片里标"未读"，不要凭记忆写。

## Stage 3：对比归纳 → 品味画像 ⏸

1. 这时再打开 `key.json`，把档位合并进卡片。
2. **先计数，再下结论。** 把卡片里的分类字段（idea 来源、gap 类型、开头方式、叙事步骤序列、洞见所在段落、Figure 1 类型、贡献类型、话说得有多满……）按档位做成计数表。高档（award / oral / spotlight / 高引）和低档（普通 poster / 被拒）差距明显的，才升级为规则。
3. 再读评审意见（若有），用它确认或推翻计数得出的规则：审稿人真的在意这个吗？
4. 按 [references/taste_profile_template.md](references/taste_profile_template.md) 写 `01_taste_profile.md`：一页纸总结的 10 条规则、三层品味各自的对比证据、2–3 个本领域的标准叙事模板（附范例论文）、反模式清单、范例库（每篇写"值得偷的一招"）、时间漂移、局限与偏差。
5. 可以参照 [references/priors.md](references/priors.md) 里前人总结的写作和品味原则当"透镜"，但它们只是**待检验的假设**：语料支持的写进规则并注明"与 X 一致"，语料不支持的也要说出来（这往往就是这个领域的特殊之处）。

⏸ 导师卡（推荐确认）：给出你认为最强的 3 条规则；让用户各打开一篇例证论文的 introduction，花 5 分钟看规则描述得对不对；回复 `OK` 或指出哪条不对。用户做过审稿或在这个领域发过论文的话，请他们补充"你觉得漏了什么"。

## Stage 4：用画像打磨用户的题目 ⏸（必须用户拍板）

按 [references/apply_to_idea.md](references/apply_to_idea.md) 做，产出 `02_apply_<idea-slug>.md`：
1. **品味体检**：这个 idea 在画像里像哪一档？命中了哪些高档特征、哪些反模式？如果 idea 本身就踩了反模式（例如"A+B 但说不出为什么"），先指出来，建议回到 research-ideation 的 Stage 5/6 重塑，而不是靠包装掩盖。
2. **提炼一句话洞见**：用这个领域高档论文的写法，改写出用户 idea 的 key insight 句。
3. **3 条不同的故事线**：用不同的叙事算子，每条都给标题候选、逐段 introduction 骨架（每段的叙事步骤和必须说的话，并指明"参照范例 Pxx 的第几段"）、Figure 1 草图、贡献列表、这条故事线欠下的**证据债**（要讲这个故事必须跑哪些实验）、模拟审稿反应。
4. **诚实检查**：故事线许诺的东西，方法和实验必须撑得住。撑不住的写明"需要补什么实验"或者直接降级这条线。包装不能超过事实。
5. 两两比较后推荐一条。

⏸ 导师卡（必须用户决定）：A（推荐）/ B / C 各一句话取舍；让用户检查推荐线的证据债里，有哪些实验两周内跑不出来。用户回复 `选 A`、`A，但开头用 C 的` 等。选定后，可以按这条线写出完整 introduction 初稿，每个需要实验支持的句子标 `[需证据]`。

## Stage 5（可选）：校准——画像到底有没有用

1. 用 `build_corpus.py` 另抽一批**不在语料里**的论文（换一年或换一个同社区 venue，每档 3–5 篇），`fetch_intros.py` 盲抓。
2. 你先只凭 introduction、**不看画像**猜档位；再**对照画像**猜一次。两次准确率都记下来，再和 Stage 2 卡片里的盲猜准确率放在一起比较。画像让准确率明显变高，才说明它学到了真东西；没变高，就要回头看规则是不是太泛。
3. 也可以把盲抓的文件给用户自己猜，这是训练用户品味最直接的练习。每猜完一篇，给出画像里对应的规则。
4. 样本很小，这只是一次体检，不是统计检验。结果写进 `03_calibration.md`。

---

## 常见反模式（发现就立刻纠正）

- 把通用写作建议当成领域品味（"清晰""动机充分"）
- 规则没有对比，或只有 1–2 篇例证
- 没读原文，凭记忆拆解名作
- 写卡之前先看了档位
- 把"热门话题"当成"品味"：热点决定大家做什么，品味决定同一个热点里谁的故事更让人信服
- 把引用数当成质量：高引也可能只是因为发得早，或者是 benchmark / 工具类论文
- 故事线包装超过实验能支撑的范围
- 大段复制论文原文到输出里
