# Scene-Sequel 场景双拍工艺（Swain 结构 + MRU 反应顺序 + McKee 价值转变）

传统类型小说最经受过验证的场景级工艺。场景卡（`scene_cards.py`）的字段就是按这套结构设计的；
本文说明**怎么用**，以及机检（`manuscript_map.detect_sequel_gaps`）在盯什么。

## 一、Scene（高压拍）：goal → conflict → disaster

对应场景卡字段：`desire`（本场 POV 要什么）→ `obstacle`/`conflict`（谁/什么拦着）→
`turn`（结果转折——**最好比"失败"更糟：得到了但代价意外，或失败且局面恶化**）。

- 铁律：**turn 不能是"顺利拿到"**。顺利=没戏。价值符号要翻（`value_shift`：如 安全→危险、
  信任→怀疑）。McKee 口径：一场戏结束时至少一个价值维度的正负号变了，否则这场戏删掉或合并。
- 网文特化：爽点场景的 turn 可以是正向翻转（碾压/打脸），但**代价或新麻烦要跟上**
  （打脸引来靠山、夺宝引来追杀），否则下一场没有燃料。

## 二、Sequel（落地拍）：reaction → dilemma → decision

对应场景卡字段：`aftermath`。三步（可压缩到几句话，不必成场）：

1. **反应（reaction）**：情绪先落地——turn 砸下来后 POV 的第一感受。这里是读者"记得疼"的
   地方；跳过它，前面的高压白打。
2. **两难（dilemma）**：摆选项，每个选项都有代价（好选项=没有两难=删掉）。
3. **决定（decision）**：POV 选一个 → 直接构成下一场的 `desire`。**这就是章间衔接的天然
   钩子**：sequel 的 decision 喂下一场的 goal，链条永不断。

- **可以留空**：高压续压（cliffhanger 直切下一场）是合法手法，尤其网文断章。但**连续 ≥3 章
  全是 turn 无 aftermath** 会触发 `SEQUEL-GAP-RUN` 提示——连打不喘读者会麻木，爽点边际递减。
- 节奏权衡：商业爽文 sequel 压短（几句内心+一个决定）；品质向可以放大成整场。

## 三、MRU（Motivation-Reaction Unit）：句级因果顺序

写 sequel 和动作场时的句级手艺——**刺激在前，反应在后**；反应内部按生理本能 → 动作 → 言语排序：

> ❌ 「滚。」他握紧刀，后背一凉，因为门后传来了脚步声。
> ✅ 门后传来脚步声。他后背一凉，握紧了刀：「滚。」

倒序（先反应后刺激、先台词后本能）会让读者产生"哪来的？"的半秒眩晕；全书累积就是"读着累"。
自查法：找"因为/原来是"引出的刺激——多数就是顺序写反了。

## 四、与本线其它工艺的接口

- `turn`/`value_shift` 缺失 → `manuscript_map` lint（review 链 advisory / author_workflow 结构闸）。
- sequel 的 decision → 下一章 `desire` → `chapter_transition.py` 的承接检查天然通过。
- 情绪落地拍写法：忌"心脏一紧"复读（`prose_craft_audit` 的 emotion_translation 指纹）——
  反应可以是直陈（他怕了）、动作（把杯子放稳了才开口）或留白（他没说话）。
- 爽点节拍与 sequel 的关系：`plot_variety_audit` 的 payoff_gap 管"多久没爽"，本工艺管
  "爽完落不落地"——两者正交。
