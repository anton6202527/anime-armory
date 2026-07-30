# novel Q&A

跨 novel-* 家族的判断标准与重复问题。每条来自实际对话，含**来源**与**适用范围**便于回溯。

新增请按四段结构：
```
## Q<n>: <问题>
**A**：<答案>
**来源**：<什么对话 / 什么场景引发>
**适用范围**：<哪个 / 哪些 skill>
```

记录原则见 `SKILL.md` 的"持续改进（meta-capability）"段。

---

## 目录

- [Q1：续写 / 扩写 / 视角续写 三者怎么分？](#q1)
- [Q2：当代受版权网文能不能做派生作品？](#q2)
- [Q3：大原作（>1000 章 / 配角 >200 章涉及）的锚点全本精筛怎么避免？](#q3)
- [Q4：Demo 章自检看什么？](#q4)
- [Q5：原创机制（任务系统 / 卡片 / 隐藏能力 等）使用密度怎么把握？](#q5)
- [Q6：主角 vs 配角怎么甄别？](#q6)
- [Q7：用户已给暂定书名时怎么处理？](#q7)
- [Q8：这套"持续改进"机制本身怎么用？](#q8)
- [Q9：agent 可以是 skill 形式吗？supervisor skill 和 runner 状态机怎么分？](#q9)
- [Q10：2026-07 外部调研沉淀——评估怎么更可信、哪些路线已证伪、长期储备做什么？](#q10)
- [Q11：2026-07 第三轮传统工艺调研沉淀——对白/弧线/节奏/修订纪律的机检化依据？](#q11)
- [Q12：2026-07 第四轮传统工艺调研沉淀——伏笔养护/信息策略/场景极性/开场与支线的机检化依据？](#q12)
- [Q13：2026-07 第五轮传统工艺调研沉淀——对白归属/场景落地/命名工艺/巧合纪律/正犯法的机检化依据？](#q13)

---

## Q1：续写 / 扩写 / 视角续写 三者怎么分？<a id="q1"></a>

**A**：
- **续写** = 加**新章节**（时间向前推） → `novel-continue`
- **扩写** = 加**章节内细节**（时间不动 / 既有内容加厚） → `novel-expand`
- **视角续写** = **换 POV** 写同一段时间 → `novel-spinoff`

**来源**：用户主动提议拆分 skill 时强调"续写章节"与"扩写"要区分。

**适用范围**：`novel` 路由表 ⚠️ 警示框 + `novel-expand` / `novel-continue` / `novel-spinoff` 各自 SKILL.md 顶部已并入。

---

## Q2：当代受版权网文能不能做派生作品？<a id="q2"></a>

**A**：**默认拒做**。即便用户本地有 .txt 文件，**阅读权 ≠ 改编权**。除非用户用 `--i-have-rights` 显式声明授权（自有 IP / 作者授权 / 出版方授权），并在 provenance 中记录：
- `rights_status = user-declared`
- `rights_declared_at = YYYY-MM-DD`
- 凭据细节（如有）

仅 `novel-fetch`（抓公版）和 `novel-title`（起原创书名）对版权状态可宽松；其他派生 skill（spinoff / expand / continue / condense）严格执行。

**来源**：用户初次给当代付费网文要做配角外传 → 被铁律拒；后续用户声明授权 → 走 `--i-have-rights` 路径。

**适用范围**：novel 合法性筛查 + 所有派生 skill 铁律段。

---

## Q3：大原作（>1000 章 / 配角 >200 章涉及）的锚点全本精筛怎么避免？<a id="q3"></a>

**A**：**不要在 Step 2 全本精筛**。改为"采样精筛 + blueprint anchors"：

1. 读**首次出场** + **中段几个高密度章节** + **末段**，建 3-7 个 blueprint anchors，覆盖人物弧线骨架（出场 / 中段身份转折 / 高潮 / 终局）。
2. 其余 candidates 标 `status = needs_review`，挂在表里不动。
3. 章纲编织时按 `assigned_chapter` 倒推哪些候选需要补精读。
4. 续写每章前再针对该章涉及的源章节做精读补充。

**关键判断**：blueprint anchors **覆盖弧线骨架**即可；不必"每个出场都对齐"。

**来源**：王敦外传项目（原作 1179 章 / 472 候选 / 王敦在 248 章涉及，全本精筛不现实）。

**适用范围**：`novel-spinoff/references/timeline-anchoring.md` + `novel-continue` 主线骨架建模 + `novel-expand` 事件骨架提取。

---

## Q4：Demo 章自检看什么？<a id="q4"></a>

**A**：六项硬清单 + 三项软评估：

**硬清单**：
- [ ] 视角全程限定（第三人称限定下无穿帮）
- [ ] 锚点事件骨架对齐（不是文本搬运）
- [ ] 未照搬原作原文（标志短句 ≤ 10 字可保留）
- [ ] 未让视角角色"知道"原作后文才揭示的事
- [ ] 章末有钩子
- [ ] 标题和首行 H1 一致

**软评估三件套（必须同时达标，缺一不过）**：
- 时间线契合 ✓
- 扩写丰富度 ✓（环境 / 内心戏 / 对话细节 / 留白填补）
- 人物厚度 ✓（多面 / 层次 / 镜像对照 等）

仅对齐不够；仅原创扩写不够。三者同时才过。

**来源**：王敦外传 Demo 后用户明确补的标准——"契合原著时间线的同时，记得自己扩写剧情、丰富人物"。

**适用范围**：`novel-craft/references/chapter.md` 写完自检「软评估三件套」（已并入）+ 所有 skill 第 5 步 Demo gate。

---

## Q5：原创机制（任务系统 / 卡片 / 隐藏能力 等）使用密度怎么把握？<a id="q5"></a>

**A**：**每章 1-2 次为佳**；超过 3 次显得机制反客为主。

具体节奏：
- **第 1 章建立机制**（让读者知道它存在）—— 可以 2-3 次
- **中段章节** 1-2 次（克制 + 在关键决策点点睛）
- **高潮章节** 1-2 次（机制反应作为反转点的"放大器"）

机制不能取代人物戏。要给"**人物如何对这条机制做反应**"留空间。

**来源**：王敦外传 Demo 自检——Ch 2 系统出现 5 次过频，Ch 3 改回 2 次密度，可读性显著提升。

**适用范围**：`novel-craft/references/chapter.md`「原创机制使用克制」段（已并入）+ 所有派生 skill 的 Demo 自检。

---

## Q6：主角 vs 配角怎么甄别？<a id="q6"></a>

**A**：粗筛阶段，用 `grep -c` 看角色名 literal 命中次数 + 看章节分布：

| 角色类型 | 命中数（典型） | 章节分布 | 首次出场位置 |
|---|---|---|---|
| 主角 | > 10000 | 全本 ≥ 90% 章节 | 第 1-3 章必直接命中 |
| 重要支线 / 长期配角 | 1000–5000 | 20%–50% 章节 | 第 5-50 章首次出现 |
| 次要配角 | 100–1000 | < 20% | 中段 |
| 路人 | < 100 | 散点 | 不重要 |

**注意 false positive**：双字组合可能与他人名 / 复合词碰撞（如"王敦"匹配"王敦厚"）。挑高密度章节实读 1-2 章验证。

**来源**：王敦外传—初看 1795 hits 一度怀疑是主角，验证开篇章节确认主角是贺平生，王敦是 248 章涉及的重要支线。

**适用范围**：`novel-spinoff` 第 1 步配角确认 + `novel` 路由决策（防止误把主角当配角做 spinoff）。

---

## Q7：用户已给暂定书名时怎么处理？<a id="q7"></a>

**A**：把暂定名作为**候选 #0** 一并打分，明确指出它相对其他候选的弱势（例如：历史向命名 → 漫剧平台契合度低），让用户在表格里直接看到"沿用 vs 换名"的对照。**不要直接采用、也不要直接弃用**。

候选 #0 也按 5 维评分；如果它真的总分最高，用户可选它保留——这是合法路径，不是强行换名。

**来源**：王敦外传—用户暂定名"王敦传"，作为 #0 在历史向平台契合度评分 1/5；用户对照后选了 #3《我，王敦，藏拙修真界》。

**适用范围**：`novel-title/references/title-patterns.md`（已并入）。

---

## Q8：这套"持续改进"机制本身怎么用？<a id="q8"></a>

**A**：见 `SKILL.md` 的"持续改进（meta-capability）"段。两条最重要的实操：

1. **写之前看落点表**——单 skill 的工艺写 references；跨 skill 的 Q 写本文件；项目特有写项目本地 `设定/`。
2. **节奏要克制**——清晰 / 可重用 / 跨场景适用三条都满足才写；用户叫停就停。

**来源**：用户在王敦外传 Demo 后明确请求—"如果发现有一些好的点可以写进 skill 里，这项能力也要写进 novel 里，并记录个 Q&A.md"。

**适用范围**：novel 自身 + 所有 novel-* skill 在跑流水线时的副产品累积。

---

## Q9：agent 可以是 skill 形式吗？supervisor skill 和 runner 状态机怎么分？<a id="q9"></a>

**A**：可以。**agent 可以用 skill 的形式承载**，但 skill 和 agent 不是同一层概念。

- **Skill 是包装 / 分发 / 路由形式**：`SKILL.md + scripts + references`，描述遇到某类任务时怎么做。
- **Agent 是运行时角色 / 行为模式**：是否有目标、是否能自主选择下一步、循环调用工具、handoff、处理开放判断。
- **Runner / 状态机是确定性流程真值**：维护 run_id、stage status、retry、lock、resume、artifact graph、gate、provenance。

所以类似 `*-supervisor` 这种写法并不矛盾：它是**用 skill 形式表达的 supervisor agent 指令包**。它可以说自己是 agent，因为它要求当前执行者扮演上层编排角色；但它不应替代生产状态机，除非它自己维护一套明确的 run state / stage status / artifact lineage。

novel 若新增 `novel-supervisor`，定位应写成：

> `novel-supervisor` 是 novel 的上层 agent 编排 skill，不替代 `novel_pipeline.py` / `pipeline_runner.py`，不拥有生产状态真值；它读取 plan/run/job/provenance，选择下一步、创建或领取 semantic job，必要时 handoff 给 specialist agent。

边界铁律：
- 不自己维护另一套 `_进度` 或 pipeline 状态。
- 不绕过 runner / gate。
- 不直接把“我认为完成了”写成完成；完成必须有声明产物、schema 校验或 runner 阶段更新。
- 不替代 `semantic_job.py` 的 schema 校验。
- 不把所有子 skill 变成 agent。

最稳的层次是：

```text
skill 作为载体
agent 作为运行角色
runner/state machine 作为确定性流程真值
artifact/provenance 作为可审计状态
```

**来源**：用户询问某条生产线的 supervisor skill 是上层 agent 编排层、仍保留 skill 作为领域知识/工具/契约，但它说自己是 agent 是否矛盾。

**适用范围**：`novel` / 未来可能的 `novel-supervisor` / `novel-craft` workflow runner / 所有 specialist handoff 设计。

## Q10：2026-07 外部调研沉淀——评估怎么更可信、哪些路线已证伪、长期储备做什么？<a id="q10"></a>

**背景**：2026-07 对长篇 AI 小说生产做过一轮深度外部调研（30+ 来源逐一打开验证 + 对抗性复核）。
可立即落地的已接线（premise 差异化机检 + VS 采样口径、plot_variety/章间承接/行为式读者度量、
热点自适应回扫、AI 腔账单回灌等）；本条记录**评估方法结论**与**长期路线**，防止重复调研。

### 评分/评审可信度（novel-score / critic-loop 执行时的口径）

- **零样本 LLM judge 与人类偏好一致率天花板约 73%**（LitBench，arXiv 2507.00769）。评分结论
  一律 advisory 的纪律有实证依据；judge_protocol 的 position-swap/家族多样性是必要不充分。
- **评审团 > 单大模型**：2-3 个**不同家族**小模型组成评审团取中位数，优于 GPT-4 级单 judge
  且便宜 7 倍（PoLL，arXiv 2404.18796）；写作模型与评审模型必须不同家族（score 已有
  judge_debias 家族检查，`meets_recommended=false` 时结论只作参考）。
- **实例专属 rubric**：先由 LLM 根据**本章**的章纲承诺/伏笔清单/读者契约生成 5 条本章专属
  检查准则再打分，与人类一致率 83%（WritingBench，arXiv 2503.05244）——比全书通用 rubric 强，
  且天然对接本线的读者契约/伏笔台账（critic-loop 的 checklist-grounded 原则同源）。
- **主观维度用 pairwise 换序**（vs 上一版/锚点范文双向各判一次），客观维度才用 rubric 直评。
- **长篇整体评估**：摘要式管全局 + 关键章节聚合式管细节 双轨（LongStoryEval，arXiv 2512.12839）；
  分数尺度漂移可用"相对真实网文分布的百分位"消除（WebNovelBench，arXiv 2505.14818）。

### 已证伪路线（别再试）

- ❌ **整本塞长上下文让 LLM 直判矛盾**：最强模型书级矛盾判别仅 55.8%（人类 97%）——必须走
  声明分解 + 定向检索证据的路（NoCha，EMNLP 2024）。本线的状态账本/检索式一致性闸方向正确。
- ❌ **LLM auto-rater 当忠实性终审**：检出"不忠实声明"很弱（FABLES，COLM 2024）——机检只能当
  高召回初筛，最终仲裁留给确定性闸 + 人判。
- ❌ **Save the Cat/英雄之旅自动校验有现成方案**：学术空白（多轮确认），要做只能自研节拍标注器。

### 长期储备（收益大、成本高，需要时再启动）

1. **自有偏好对奖励模型**：积累"编辑二选一"偏好对（哪版章节留/弃），几千对起步训练小型
   Bradley-Terry 排序模型——突破 73% judge 天花板的唯一已验证路径（LitBench 78%）；
   LLM judge 降级为解释性反馈生成器。
2. **NoCha 式 gate 回归测试集**：从已完结作品造"真声明/单点篡改"最小对 ~100 对，定期测
   一致性闸的真实召回——防机检空转（兄弟线踩过的同款坑）。
3. **Creativity Index 中文化**（ICLR 2025）：对外部存量语料的可拼接率查重（管"像不像别人"），
  与文风指纹（管"像不像自己"）互补；需自建中文网文 n-gram 索引，投入大。
4. **MiniCheck 式中文小检查器蒸馏**（EMNLP 2024 架构）：声明分解→检索账本证据→小模型逐对
   打分，成本 ~1/400——"回扫从抽查变全量"的关键。
5. **FACTTRACK 式账本时间区间化**（arXiv 2407.16347）：状态账本条目升级为
   `原子事实+[生效章,失效章)`，写入前对撞——world_fact_interval_conflict 已是雏形，可扩全量。

**来源**：2026-07 调研会话（多代理网搜 + 逐源验证）。**适用范围**：novel-score / novel-simulate /
novel-supervisor critic-loop / qa_gate 演进规划。

## Q11：2026-07 第三轮传统工艺调研沉淀——对白/弧线/节奏/修订纪律的机检化依据？<a id="q11"></a>

**背景**：第三轮审计（前两轮见 Q10 与 novel-review SKILL 检测器清单）聚焦**传统小说创作
流程与手法**里尚未机检化的部分。原则同前：机检只逮确定性形态、恒 advisory，工艺判断归人/LLM。

### 本轮机检化的传统手艺（已接线）

- **微张力（Donald Maass, Writing the Breakout Novel）**：张力三层（情节/场景/line 级），
  line 级来自对话中的抵抗（withhold/misread/push back）与矛盾情绪并存，"tension on every
  page"。落地：`dialogue_craft_audit.py` 的 frictionless_dialogue（整章零摩擦标记）；
  工艺文档 `novel-craft/references/dialogue.md` 第五节。
- **on-the-nose 对白（编剧工艺共识）**：角色把情绪与动机原样说出口=潜台词为零；判据取
  "情绪自陈+因果连词同句"的保守共现（单独直陈情绪不算——StoryScope 实证人类反而更常直写
  "他很害怕"）。落地：同上 on_the_nose_dialogue。
- **弧线内构（K.M. Weiland：Ghost→Wound→Lie→Want vs Need）**：Want=情节目标、Need=主题
  真值、Lie(misbelief) 须被付代价的选择反复挑战。scene_cards 字段早已齐（want/need/misbelief/
  choice_cost…），缺的是**时间性对账**。落地：`character_arc_audit.py`（want==need 塌缩/
  misbelief 无代价 run/引擎填充率衰减）。
- **句子节奏（Gary Provost "This sentence has five words"）**：句长长短交替=行文音乐性，
  纯数值可测（变异系数+同档 run）。落地：prose_craft_audit C 组。
- **echo/crutch words（传统 line-edit 第一刀）**：近窗实词复读（ProWritingAid 类工具的 echo
  检测口径：20-100 词窗）+ 作者惯用拐杖短语清单。落地：C 组 echo_words（统计侧）+
  crutch_phrases（词表侧，`keyword_banks.CRUTCH_PHRASE_KW`）。
- **心理距离/POV 纪律（John Gardner, The Art of Fiction 五级心理距离）**：head-hopping=
  同场景多角色内心直读；确定性代理=内心动词归属主体 ≥2 人。落地：C 组 head_hopping。
- **cover-the-names 测试（角色语声区分度）**：遮名读对白应能认人；Elmore Leonard 式每角色
  专属词表/禁用词表。确定性代理=角色两两台词 2-gram Jaccard。落地：voice_drift 的
  voice_homogeneity（补齐"纵向漂移之外的横向同质化"）。
- **连载张弛节奏（网文工艺共识）**：每章强钩=疲劳（1 强 2 缓交替）、平路 >3 章掉追读。
  落地：hook_endings 序列层（hook_fatigue_run / weak_ending_run）。
- **macro-before-micro 修订顺序（编辑行业共识）**：结构未锁前不做行文级修补（否则移场景/
  并章时行文功夫白费）；红黄绿 triage。落地：revision_planner 的 tier 三层
  （structure/scene/line）+ 结构级未决时行文级任务缓办标记。

### 有意未做（评估过、按住）

- **潜台词质量正向评估**：机检只能逮"subtext 被逐字说破"（负向），"潜台词好不好"无确定性
  信号，强行做=假阳性风暴。
- **Promise-Progress-Payoff 全量台账**（Sanderson）：承诺追踪与 foreshadow_ledger/
  tension_ledger（钩子过期/承诺违约）/reader_contract 已三处覆盖，再建一本账=台账过密，
  收益边际递减。
- **五感覆盖率统计**：SENSORY-ANCHOR-DROPPED 已管"计划意象被丢弃"；全文五感配比无公认
  基准，且嗅觉桶已有 StoryScope 信号，重复建设。

**适用范围**：novel-review / novel-craft / novel-edit；阈值全部 env 可标定（见各脚本头部）。

## Q12：2026-07 第四轮传统工艺调研沉淀——伏笔养护/信息策略/场景极性/开场与支线的机检化依据？<a id="q12"></a>

**背景**：第四轮审计（前三轮见 Q10/Q11）继续从传统小说创作手法里挖尚未机检化的部分，
调研覆盖中国评点派（金圣叹/毛宗岗/脂砚斋）、网文实战方法论（阅文作家专区/番茄公开口径）、
西方场景工艺与编辑实务（16+ 来源）。原则不变：机检只逮确定性形态、恒 advisory，工艺判断归人/LLM。
本轮特点：**全部新信号挂在已注册检测器或写作端任务包上，零新增注册面**。

### 本轮机检化的传统手艺（已接线）

- **草蛇灰线 / rule of three（金圣叹《读第五才子书法》；编剧 setup-reminder-payoff 工艺）**：
  伏笔要"骤看之如无物"地**多次低强度复现**，回收才"拽之通体俱动"。台账此前只管头尾
  （overdue/never_fired），中拍失明。落地：`foreshadow_ledger` 内容级三信号
  （foreshadow_reminder_gap / foreshadow_overexposed / payoff_without_setup 反向契诃夫），
  写作端 `draft_packets` 伏笔注入增"该补提醒"第三桶。
- **希区柯克炸弹论（surprise 15 秒 vs suspense 15 分钟；Truffaut 访谈）**：knowledge_ledger
  的 reader_knows_since/public_since 字段早就够算——irony_window_untouched（读者先知窗口
  内正文零触碰=炸弹旁没人说话）、reveal_burst（同章倾泻）、surprise_heavy（全书无 suspense 型）。
  零新台账，纯字段复用。
- **try/fail cycles，yes-but/no-and（Swain；Writing Excuses 16.41）**：scene_cards 增
  `outcome` 枚举（yes/yes-but/no-and/no-but）+ `plotline` 自由标签；manuscript_map 对账
  OUTCOME-YES-RUN（连胜无阻力）/OUTCOME-NO-COST-CLIMB（yes 占比 >60%）。
- **横云断山 / 獭尾法（金圣叹）**：PLOTLINE-LONG-RUN（同线连续 ≥6 场景无间笔）；
  CLIMAX-NO-AFTERWAVE（张力 top-2 峰值章末场景无 aftermath 且次章开新冲突=
  "大文字后寂然便住"，弧线级，区别于场景级 SEQUEL-GAP-RUN）。
- **欲扬先抑（脂批"未扬先抑"；网文打脸三拍：反派抬高→主角受压→反转）**：
  plot_variety payoff_without_suppression——爽点密集章回溯窗口（含本章）零受挫命中=打空气；
  词表 `keyword_banks.SETBACK_KW`。反派抬高段检测（valence 归因）误报重，有意不做。
- **配角失踪（braided-stories 实务，Wrede/Houghton："Reminding ≠ moving"）**：
  minor_characters major_character_absent，open_threads 持有者加重；结构化退场登记豁免。
- **悬念真空（MDQ 开闭管理）**：logic_sentry scan_tension 第四规则 suspense_vacuum——
  活跃钩子+承诺数连续 ≥2 章为 0（≠张力分低，是"账面上没有未决问题吊着读者"）。
- **行业滥调开场（agent slush pile 退稿统计：梦醒/起床/天气/照镜）+ 段首同型**：
  prose_craft slush_opening_cliche / paragraph_opening_monotony；与"开篇同型"互补
  （那查自我重复，这查行业黑名单）。
- **黄金三章硬对表（阅文作家专区口径）**：demo_readiness 增 DEMO-OPENING-CONFLICT-HOLLOW
  （前 3 章场景卡 conflict 半数为空）/ DEMO-SELLING-POINT-LATE（reader_promises 词面前
  3 章正文零命中）。
- **beta reader 标准六问（Jane Friedman/FoxPrint 口径）**：novel-simulate 问卷协议
  `评分/reader_survey_第NN章.json`（bored/confused/disbelief/favorite/prediction/recall），
  behavioral_signals 聚合出 reader_bored_run / reader_confusion_spike / reader_disbelief /
  recall_failure（复述留存=2-gram 包含度，防长度稀释同 surprise 口径）。
- **"扔掉第一想法"（brainstorm 实务：first idea = lowest-hanging cliché）**：
  `draft_packets.predicted_plot_section`——把上一章模拟读者预测注入写章包当负面约束
  （"读者已猜到的走向禁止照写，或抵达同一终点前加拐弯"）。事后意外度检测搬到生成期当筛子，
  与 AI 腔账单同属"下游检测搬上游"闭环：账单管怎么写，这个管写什么。

### 有意未做（评估过、按住）

- **期待感/DQ 第四本账**：网文"期待单元"台账与 tension_ledger 的 hooks/promises 语义重合
  （open/close/超期贬值三规则全部同构）——Q11 已按"台账过密"原则否掉 PPP 全量账，同理不建；
  suspense_vacuum 已把"活跃期待数=0"的关键判据挂在现有账上。
- **书内日历约束求解（时间指示词抽取→区间代数对撞：星期矛盾/耗时矛盾/旅行时长）**：
  收益大但需 LLM 逐章结构化抽取+距离/速度表，属长期储备（与 Q10 FACTTRACK 区间化同族）；
  timeline_check 已覆盖绝对年+季节倒退的纯文本可判部分。
- **避犯/犯中求避的四维变奏检测（毛宗岗：三打祝家庄合法，前提每打不同）**：需场景结构
  指纹（goal 型+对手型+结局型三元组）+ 四维差异比对，plot_variety 的 beat_cycle 已覆盖
  主形态，增量判据不干净。
- **背面敷粉（借他人之口写主角）/打脸三拍的"反派抬高段"检测**：都需 valence 归因
  （这句夸的是谁、贬的是谁），词表级判不干净=假阳性风暴。
- **midpoint 极性翻转/pinch points 结构点检测（Weiland 37%/50%/62%）**：结构点位是统计
  倾向非铁律，且"主动 goal 占比时序变化点检测"对 scene_cards 填充质量要求高；
  tension_fatigue + post_write 40-60% 中段加密回扫已覆盖 sagging middle 主信号。
- **MICE 括号嵌套检查（Card/Kowal）**：长篇多线本就不必严格嵌套，误报率高价值低。

**适用范围**：novel-review / novel-craft / novel-wiki / novel-simulate / novel-create；
阈值全部 env 可标定（见各脚本头部）。

## Q13：2026-07 第五轮传统工艺调研沉淀——对白归属/场景落地/命名工艺/巧合纪律/正犯法的机检化依据？<a id="q13"></a>

**背景**：第五轮审计（前四轮见 Q10–Q12）继续挖传统小说创作手法中未机检化的部分。本轮
特殊性：**首次有生产实锤对照**——git 历史里的王敦外传（20 章全流程跑通的原创项目）第 20 章
实测出「3-5 轮无归属对白」「轻度 white-room」「单句成段碎句体」「归属标签模板化」，与外部
调研候选精确对上，判据按实锤病灶标定。原则不变：机检只逮确定性形态、恒 advisory
（唯 scene_cards 枚举校验是既有 warning 面）、零新增检测器注册面（全部挂在已注册检测器上）。

### 本轮机检化的传统手艺（已接线）

- **对白归属三件套（Elmore Leonard《10 Rules》第 3/4 条；Browne & King《Self-Editing for
  Fiction Writers》第 5 章 checklist；Savannah Gilbo"3-4 exchanges 须重新锚定"口径）**：
  `dialogue_craft_audit` 增 ① said_bookism（华丽说话动词密度；中文口径校准：说/道/笑道/
  叹道等白话惯用**合法**——金庸满篇笑道，只逮词表内华丽形态，词表 `keyword_banks.
  SAID_BOOKISM_KW` 全收 X…道 复合形、词面即 tag 零歧义）② untagged_dialogue_run
  （连续 ≥8 行纯引语=引号外零字，读者数不清谁在说）③ talking_heads_run（连续 ≥12 行
  对话每行引号外叙述 <6 字——裸 tag 不算 beat；Weiland talking heads/white-room）。
  ②命中时同章不再报③（同病更重形态优先）。副词粘 tag 第二轮已做（adverb_dialogue_tag），
  本轮不重复。
- **段落极端形态（编辑口径：约半页不分段即墙——Editor World；碎句体是生产实锤病）**：
  `prose_craft` E 组 wall_of_text（单段 ≥400 字）+ fragmented_paragraph_run（连续 ≥8 个
  叙述段每段 <12 字=短剧碎句腔；**只数叙述段，对话行跳过且不断 run**——碎句病灶在叙述侧）。
- **命名混淆矩阵（Fictionary/K.M. Weiland 编辑检查表：列全员名单查近形名；水浒张青/张清
  是行业经典教训）**：`minor_characters` 增 confusable_character_names——角色卡名∪高频
  配角候选两两比：等长且编辑距离 ≤1，或双方 ≥3 字同姓且名部共字。别名归一后同角色不比、
  互为子串（简称）不比；亲属/系列名有意同构人工豁免。
- **开篇人物过载（DearEditor 行业口径：第 1 章主角+1-2 配角为宜，12 个必然过载；"命名即
  承诺"）**：同检测器 opening_cast_overload——第 1 章具名 >6 或前 3 章累计 >12。与
  major_character_absent 互补：那查出场后消失，这查入口拥塞。群像流按 env 调参。
- **场景落地对账（Writers Helping Writers"换场前两段锚定 who/where/when"口径）**：
  `manuscript_map` 增 SCENE-GROUNDING-DROPPED——场景卡登记 pov+location(/time)，章首
  250 字 pov 与地点/时间词段（拆 2-gram 命中，误判方向=压告警保守安全）**双双**零命中才报。
  与 SENSORY-ANCHOR-DROPPED 同构（计划字段 vs 正文对账）。
- **巧合纪律（Pixar 第 19 条/Emma Coats："巧合送人进麻烦是好戏，捞人出麻烦是作弊"）**：
  scene_cards 增可选枚举字段 `turn_source`（主角行动/对手行动/盟友援手/伏笔兑现/巧合），
  manuscript_map 增 TURN-COINCIDENCE-RESCUE——turn_source=巧合 且 outcome 有利
  （yes/yes-but）→ 提示；巧合+失败合法不报。纯文本判"巧合"不可行（因果语义），枚举
  自证是唯一确定性路径——本轮唯一的新增字段面（1 字段）。
- **正犯法/犯中求避（金圣叹《读第五才子书法》"正犯"；毛宗岗"同树异枝、同枝异叶"——
  重复不是罪，重复而不变化才是罪，正是 AI 长篇头号病）**：manuscript_map 增
  SCENE-REPEAT-NO-VARIATION——跨章两场景同 pov、同 location、同 outcome（均非空）且
  desire+obstacle char-2gram Jaccard ≥0.6。与 Q12 否掉的"四维变奏检测"不同：那需要
  场景语义分型（判据不干净），这是**纯字段对字段**的保守窄版，只逮"照原样重打一遍"。
- **早期闪回闸（Jane Friedman"读者未投资当前场景前禁止闪回"；Maass"backstory 推迟
  100 页"；编辑退稿实务）**：`demo_readiness` 增 DEMO-EARLY-FLASHBACK——前 3 章单章
  ≥2 段命中强闪回引导（`keyword_banks.FLASHBACK_MARKERS` + "N年前"数量词型；单个
  "想起"不算）。倒叙框架结构人工豁免；只报最早一章。
- **倒序审校（Writer's Digest/ALLi："backwards editing"破坏叙事惯性防顺读催眠）**：
  novel-edit SKILL 增 copyedit 层倒序纪律（批次任务按章号降序派发，零成本流程化）；
  line_edit 层不倒序（行文节奏需顺读语境）。

### 有意未做（评估过，按住）

- **章末软着陆位置几何**（张力峰值偏移 <85% 且末段收束词）：需**章内** beat 位置数据，
  emotional_progression 只有章级张力分；hook_endings 的 weak_chapter_ending 词面打分已覆盖
  尾段平淡主形态，增量不干净。
- **章字数带宽**：mechanical_check 字数维度已有；平台完读率/留存硬指标的具体数值只取项目
  `评分/market_baseline_*.json` 或 `资料/research_sources.json`，作为平台侧数据留给 novel-promote/feedback 回灌。
- **read-aloud 拗口代理**（同音连缀等）：假阳性高，判不可行；若未来接 TTS 有声化，停顿
  异常可当免费信号（机会主义储备）。
- **笙箫夹鼓张力交替**（连续高张力无间歇）：logic_sentry tension_fatigue 已覆盖主形态。
- **留白类评点手法**（不写之写/背面敷粉扩展）、**移堂就树**：语义判断，确定性不可行
  （Q12 同结论，本轮复核维持）。
- **三五聚散/近山浓抹**（人物聚散节奏/主次详略比）：可判但阈值无出处支撑、收益证据薄。
- **断更/全勤节奏**：属发布调度器逻辑，不是文本机检。

### 生产实锤复核清单（本轮判据的事实依据）

王敦外传（已归档生产样本，版本快照 5a609465 的前一版）：第 01 章工艺扎实 vs 第 20 章滑向短剧碎句体——
①大量单句成段（"一声。/又一声。"）→ fragmented_paragraph_run 判据来源；②3-5 轮无标签
问答靠上下文辨认说话人 → untagged_dialogue_run 阈值参照（生产 3-5 轮尚可追踪，阈取 8 保守）；
③屏风偷听场大段纯对白+内心、靠两处物件锚定救场 → talking_heads_run 的 beat 判据（物件
锚定=beat，合法）；④"贺平生道"×12 模板化归属 → mechanical 句式模板已覆盖，said_bookism
管的是另一极（华丽动词），两头都有闸。另：tension_ledger/world_state_ledger 双空壳、
伏笔 confirmed 全 false、读者问卷从未实跑——**流程空转病**（非本轮工艺范围）已有既存闸
（foreshadow_ledger 空账显式报缺、suspense_vacuum、taxonomy 覆盖表 degraded 标记），
待项目重启时按 Q10 长期储备推进。

**来源**：2026-07-24 第五轮审计会话（外部调研代理 30+ 来源 + 生产数据取证代理 git 历史
复原 + 机检体系全景比对）。**适用范围**：novel-review / novel-craft / novel-wiki /
novel-edit；阈值全部 env 可标定（见各脚本头部）。
