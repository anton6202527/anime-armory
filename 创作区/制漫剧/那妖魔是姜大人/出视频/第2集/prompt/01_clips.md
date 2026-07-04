# 逐 Clip 视频 prompt

本文件由 n2d-video 阶段A按 storyboard/video_model_routes/identity/director sidecars 生成；每段含提交前检查与生成后自检。视频调用策略为无声视频流，不启动付费视频生成。

### 剧本可看性合同（全局签收）
**core_attraction**：category=规则反杀+系统成长；viewer_question=她能不能活着吃下这场残酷收益，下一批赶到的人又会怎么判她？；why_watch=姜月初把误杀同袍换来的二十年道行压成一刀反杀虎山神，再用百妖谱把一百年道行兑换成长期战力。
**first_3s_visual_hook**：content_promise=杀人后的道行奖励马上兑现，系统规则比道德更冷。；content_proposition=姜月初刚杀错人，百妖谱为什么先奖励她二十年道行，规则比道德更冷。；expected_metric={"primary": "retention_3s", "target": 0.82}；hook_type=危机/悬念/信息；muted_readable=True；muted_safe=True；muted_safe_proof=关声仍能从胸口长刀、裴长青失焦眼神、姜月初惊住、百妖谱金光与烧屏疑问读懂危机。；onscreen_text=她刚杀的人还没死，系统为什么奖励她？；onscreen_text_duration_sec=3.0；silent_readable=True；viewer_question=她杀错人了吗，系统为什么奖励？；visual_hook=她刚杀的人还没咽气，长刀仍插在裴长青胸口；百妖谱却先亮起到账疑问。
**retention_promise_ledger**：
- bait_risk=low；hook_id=EP01_TAIL_PAYOFF；opened_at=EP01_CLIP11；payoff_clip=EP02_CLIP01；payoff_due=第2集 EP02_CLIP01；payoff_evidence=Clip01 立刻出现二十年到账，杀裴后的残酷规则首屏兑现。；payoff_status=paid；promise=第1集尾声姜月初刀入裴长青胸口，会不会触发系统、能不能活。；promise_type=opening_hook
- bait_risk=low；hook_id=EP02_MID_FIGHT；opened_at=EP02_CLIP03；payoff_clip=EP02_CLIP04；payoff_due=第2集 EP02_CLIP04；payoff_evidence=Clip04 以错身刀光和虎头落地轮廓兑现一刀反杀。；payoff_status=paid；promise=二十年道行全压进一刀，够不够杀虎山神。；promise_type=mid_hook
- bait_risk=low；hook_id=EP02_SYSTEM_RULE；opened_at=EP02_CLIP05；payoff_clip=EP02_CLIP07；payoff_due=第2集 EP02_CLIP07；payoff_evidence=Clip07 获得猛虎快刀圆满、闻弦初境和虎山神摹影，说明收录是长期买卖。；payoff_status=paid；promise=收录虎山神会消耗一百年道行，亏还是赚。；promise_type=info_hook
- bait_risk=low；delayed_payoff_ep=第3集；hook_id=EP02_TAIL_HOOK；opened_at=EP02_CLIP10；payoff_due=第3集 EP03_CLIP01；payoff_status=open；promise=官道火把和马蹄声逼近尸场，来者会如何判断姜月初。；promise_type=tail_hook
**audience_question_ledger**：
- expected_next_handling=本集兑现/推进；question_context=·骤冷·快] 她刚杀的人还没咽气，长刀还插在裴长青胸口；为什么百妖谱先亮了？ ⚡钩子 [镜头2·裴长青·错愕·短促]；question_id=Q01；signal=为什么；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=镜头2·裴长青·错愕·短促] 你...... [镜头3·系统·冷静·慢] 击杀闻弦境生物，获得其道行二十年。 ⚡钩；question_id=Q02；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=活......下来了？|| 代价也来了。 [镜头15·系统·冷静·慢] 击杀闻弦境生物，获得其道行一百年。 💥爽；question_id=Q03；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=杀闻弦境生物，获得其道行一百年。 💥爽点 [镜头16·系统·冷静·慢] 检测到未收录妖物，是否消耗道行收录？ [镜；question_id=Q04；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=八十......最后停在二十五。 ⚡钩子 [镜头20·系统·冷静·慢] 成功摹影虎山神，获得妖物馈赠。 [镜头21；question_id=Q05；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=冷静·慢] 成功摹影虎山神，获得妖物馈赠。 [镜头21·系统·冷静·慢] 猛虎快刀（圆满）。 💥爽点 [镜头22·；question_id=Q06；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=身体。她再握住横刀，像握住自己天生的骨头。 [镜头23·系统·冷静·慢] 宿主：姜月初。境界：闻弦初境。武学：猛虎快；question_id=Q07；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=演总意图 - 首屏直接兑现第1集刀入裴长青胸口：杀人后系统到账，不解释、不铺垫。 - 中段动作只拍一刀反杀：二十年；question_id=Q08；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=年道行全压进横刀，起手、冲撞、错身、落点必须清楚。 - 系统信息全部后期叠字：百妖谱只画空面板/金色古卷/虎形摹影，；question_id=Q09；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=白｜骤冷｜快｜她刚杀的人还没咽气，长刀还插在裴长青胸口；为什么百妖谱先亮了？ - 画面：长刀仍插在裴长青胸口，刀柄轻颤；question_id=Q10；signal=为什么；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=横刀 ### 镜头3｜7.491s-10.331s｜系统面板特写 - 配音行：系统｜冷静｜慢｜击杀闻弦境生物，获；question_id=Q11；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=7.491s-10.331s｜系统面板特写 - 配音行：系统｜冷静｜慢｜击杀闻弦境生物，获得其道行二十年。 - 画面；question_id=Q12；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=古卷。 - 实体：CHAR_01/血尘战损态, VFX_系统面板/百妖谱 ### 镜头4｜10.331s-12.5；question_id=Q13；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=刀 ### 镜头15｜51.334s-54.237s｜系统面板特写 - 配音行：系统｜冷静｜慢｜击杀闻弦境生物，获；question_id=Q14；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=1.334s-54.237s｜系统面板特写 - 配音行：系统｜冷静｜慢｜击杀闻弦境生物，获得其道行一百年。 - 画面；question_id=Q15；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=面不烤字。 - 实体：CHAR_01/脱力态, VFX_系统面板/百妖谱 ### 镜头16｜54.237s-56.；question_id=Q16；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=.237s-56.954s｜CU 古卷问询 - 配音行：系统｜冷静｜慢｜检测到未收录妖物，是否消耗道行收录？ - 画；question_id=Q17；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=_01/脱力态, CHAR_03/摹影挣扎态, VFX_系统面板/百妖谱 ### 镜头17｜56.954s-57.；question_id=Q18；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=AR_03/摹影挣扎态, VFX_虎山神摹影, VFX_系统面板/百妖谱 ### 镜头19｜63.519s-69.；question_id=Q19；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=在二十五。 - 实体：CHAR_01/脱力态, VFX_系统面板/道行计数overlay ### 镜头20｜69.；question_id=Q20；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=y ### 镜头20｜69.224s-71.511s｜系统面板特写 - 配音行：系统｜冷静｜慢｜成功摹影虎山神，获；question_id=Q21；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=9.224s-71.511s｜系统面板特写 - 配音行：系统｜冷静｜慢｜成功摹影虎山神，获得妖物馈赠。 - 画面：古；question_id=Q22；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=AR_01/脱力态, CHAR_03/摹影态, VFX_系统面板/百妖谱 ### 镜头21｜71.511s-73.；question_id=Q23；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=1s-73.233s｜INSERT 技能名 - 配音行：系统｜冷静｜慢｜猛虎快刀（圆满）。 - 画面：横刀刀脊浮现短；question_id=Q24；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=刀 ### 镜头23｜78.783s-85.716s｜系统状态面板+人物半身 - 配音行：系统｜冷静｜慢｜宿主：姜；question_id=Q25；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=s-85.716s｜系统状态面板+人物半身 - 配音行：系统｜冷静｜慢｜宿主：姜月初。境界：闻弦初境。武学：猛虎快刀；question_id=Q26；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=1/猛虎快刀圆满态, CHAR_03/摹影态, VFX_系统面板/百妖谱 ### 镜头24｜85.716s-91.；question_id=Q27；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=酷规则打到首屏。 | 观众先震惊姜月初杀了人，再立刻追问系统为何奖励。 | | EP02_CLIP02 虎妖嘲讽与转；question_id=Q28；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=则打到首屏。 | 观众先震惊姜月初杀了人，再立刻追问系统为何奖励。 | | EP02_CLIP02 虎妖嘲讽与转刀；question_id=Q29；signal=为何；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=el | 从“活下来”马上转到“代价和选择”，把爽点推向系统玩法。 | 观众追问一百年道行会带来什么，以及收录会不会；question_id=Q30；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=值：技能圆满、境界落档、虎山神进入百妖谱。 | 观众获得系统成长爽点，并理解后续刷妖升级的长期玩法。 | | EP0；question_id=Q31；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=生进入主动计算，明确道行要留作命。 | 观众相信她开始懂系统，不是只靠运气。 | | EP02_CLIP09 替裴合；question_id=Q32；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=n": { "category": "规则反杀+系统成长", "why_watch": "姜月初把误；question_id=Q33；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=t_proposition": "姜月初刚杀错人，百妖谱为什么先奖励她二十年道行，规则比道德更冷。", "co；question_id=Q34；signal=为什么；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=ent_promise": "杀人后的道行奖励马上兑现，系统规则比道德更冷。", "onscreen_tex；question_id=Q35；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="onscreen_text": "她刚杀的人还没死，系统为什么奖励她？", "onscreen_text；question_id=Q36；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=onscreen_text": "她刚杀的人还没死，系统为什么奖励她？", "onscreen_text_du；question_id=Q37；signal=为什么；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="viewer_question": "她杀错人了吗，系统为什么奖励？", "muted_readable；question_id=Q38；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=viewer_question": "她杀错人了吗，系统为什么奖励？", "muted_readable":；question_id=Q39；signal=为什么；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=ise": "第1集尾声姜月初刀入裴长青胸口，会不会触发系统、能不能活。", "payoff_due":；question_id=Q40；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="question": "姜月初杀裴长青到底是恶还是被系统逼出的生路？", "status": "；question_id=Q41；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=ct": { "色调基线": "冷青灰夜色为主，系统/百妖谱只用克制暖金点亮；动作高潮不转成满屏金色。",；question_id=Q42；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=" }, "景别阶梯": "首屏ECU/系统插入，转MCU反打，动作段WIDE+侧移，系统段INSE；question_id=Q43；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=屏ECU/系统插入，转MCU反打，动作段WIDE+侧移，系统段INSERT/MCU，结尾ELS远景火把。" },；question_id=Q44；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="镜头与构图": "9:16竖屏，人物大脸情绪与系统面板负空间并重；动作镜头优先清楚力线。", "光；question_id=Q45；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="WEAPON_01 横刀", "VFX_系统面板/百妖谱", "VFX_虎山神摹影",；question_id=Q46；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=_effect": "观众先震惊姜月初杀了人，再立刻追问系统为何奖励。", "character_ids；question_id=Q47；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=ffect": "观众先震惊姜月初杀了人，再立刻追问系统为何奖励。", "character_ids":；question_id=Q48；signal=为何；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=WEAPON_01 横刀", "VFX_系统面板/百妖谱", "VFX_系统面板",；question_id=Q49；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=VFX_系统面板/百妖谱", "VFX_系统面板", "百妖谱" ],；question_id=Q50；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=APON_01 横刀", "VFX_系统面板/百妖谱", "VFX_系统面板；question_id=Q51；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=X_系统面板/百妖谱", "VFX_系统面板", "百妖谱"；question_id=Q52；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=APON_01 横刀", "VFX_系统面板/百妖谱", "VFX_系统面板；question_id=Q53；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=X_系统面板/百妖谱", "VFX_系统面板", "百妖谱",；question_id=Q54；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="reason": "三帧契约：锁住人物状态、系统面板或情绪转折的中段锚。" },；question_id=Q55；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="entry_exit": "出画/画外保留：VFX_系统面板、百妖谱" }, "shot；question_id=Q56；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=_01 横刀", "VFX_系统面板/百妖谱", "VFX_；question_id=Q57；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=面板/百妖谱", "VFX_系统面板", "百妖谱"；question_id=Q58；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=_01 横刀", "VFX_系统面板/百妖谱", "VFX_；question_id=Q59；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=面板/百妖谱", "VFX_系统面板", "百妖谱"；question_id=Q60；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=": 2.84, "lens": "系统面板特写", "desc": "百妖；question_id=Q61；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=_01 横刀", "VFX_系统面板/百妖谱", "VFX_；question_id=Q62；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=面板/百妖谱", "VFX_系统面板", "百妖谱"；question_id=Q63；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=_01 横刀", "VFX_系统面板/百妖谱", "VFX_；question_id=Q64；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=面板/百妖谱", "VFX_系统面板", "百妖谱"；question_id=Q65；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=], "blocking": "百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 com；question_id=Q66；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=谱变成现代手机UI", "不要加入新系统人格" ], "stor；question_id=Q67；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="story_function": "把系统规则和收益用可读 overlay 交接给 compose；question_id=Q68；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="motif_id": "MOTIF_百妖谱系统面板", "vfx_asset": "V；question_id=Q69；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=, "vfx_asset": "VFX_系统面板/百妖谱", "text_layer；question_id=Q70；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=presence": [ "VFX_系统面板", "百妖谱"；question_id=Q71；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="reason": "三帧契约：锁住人物状态、系统面板或情绪转折的中段锚。" },；question_id=Q72；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="entry_exit": "出画/画外保留：VFX_系统面板、百妖谱；出画/画外保留：CHAR_02"；question_id=Q73；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=presence": [ "VFX_系统面板", "百妖谱"；question_id=Q74；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="entry_exit": "入画/现身：VFX_系统面板、百妖谱" }, "shot；question_id=Q75；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=战场/冷灰夜/外", "rhythm": "系统爽点", "dramatic_functio；question_id=Q76；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=n": "从“活下来”马上转到“代价和选择”，把爽点推向系统玩法。", "audience_effect；question_id=Q77；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=WEAPON_01 横刀", "VFX_系统面板/百妖谱", "VFX_系统面板",；question_id=Q78；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=VFX_系统面板/百妖谱", "VFX_系统面板", "百妖谱" ],；question_id=Q79；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=APON_01 横刀", "VFX_系统面板/百妖谱", "VFX_系统面板；question_id=Q80；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=X_系统面板/百妖谱", "VFX_系统面板", "百妖谱"；question_id=Q81；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=APON_01 横刀", "VFX_系统面板/百妖谱", "VFX_系统面板；question_id=Q82；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=X_系统面板/百妖谱", "VFX_系统面板", "百妖谱",；question_id=Q83；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="reason": "三帧契约：锁住人物状态、系统面板或情绪转折的中段锚。" },；question_id=Q84；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="entry_exit": "入画/现身：VFX_系统面板、百妖谱；出画/画外保留：WEAPON_01 横刀；；question_id=Q85；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=_01 横刀", "VFX_系统面板/百妖谱", "VFX_；question_id=Q86；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=面板/百妖谱", "VFX_系统面板", "百妖谱"；question_id=Q87；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=: 2.903, "lens": "系统面板特写", "desc": "百妖；question_id=Q88；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=_01 横刀", "VFX_系统面板/百妖谱", "VFX_；question_id=Q89；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=面板/百妖谱", "VFX_系统面板", "百妖谱"；question_id=Q90；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=_01 横刀", "VFX_系统面板/百妖谱", "VFX_；question_id=Q91；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=面板/百妖谱", "VFX_系统面板", "百妖谱"；question_id=Q92；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=_01 横刀", "VFX_系统面板/百妖谱", "VFX_；question_id=Q93；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=面板/百妖谱", "VFX_系统面板", "百妖谱"；question_id=Q94；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=], "blocking": "百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 com；question_id=Q95；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=谱变成现代手机UI", "不要加入新系统人格" ], "stor；question_id=Q96；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="story_function": "把系统规则和收益用可读 overlay 交接给 compose；question_id=Q97；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="motif_id": "MOTIF_百妖谱系统面板", "vfx_asset": "V；question_id=Q98；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=, "vfx_asset": "VFX_系统面板/百妖谱", "text_layer；question_id=Q99；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=战场/冷灰夜/外", "rhythm": "系统爽点", "dramatic_functio；question_id=Q100；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="VFX_虎山神摹影", "VFX_系统面板/百妖谱", "VFX_系统面板",；question_id=Q101；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=VFX_系统面板/百妖谱", "VFX_系统面板", "百妖谱",；question_id=Q102；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="百妖谱", "VFX_系统面板/道行计数overlay", "道行；question_id=Q103；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="VFX_虎山神摹影", "VFX_系统面板/百妖谱", "VFX_系统面板；question_id=Q104；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=X_系统面板/百妖谱", "VFX_系统面板", "百妖谱",；question_id=Q105；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="百妖谱", "VFX_系统面板/道行计数overlay", "；question_id=Q106；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="VFX_虎山神摹影", "VFX_系统面板/百妖谱", "VFX_系统面板；question_id=Q107；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=X_系统面板/百妖谱", "VFX_系统面板", "百妖谱",；question_id=Q108；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="百妖谱", "VFX_系统面板/道行计数overlay", "；question_id=Q109；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="reason": "三帧契约：锁住人物状态、系统面板或情绪转折的中段锚。" },；question_id=Q110；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=_虎山神摹影", "VFX_系统面板/百妖谱", "VFX_；question_id=Q111；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=面板/百妖谱", "VFX_系统面板", "百妖谱",；question_id=Q112；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="百妖谱", "VFX_系统面板/道行计数overlay",；question_id=Q113；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=_虎山神摹影", "VFX_系统面板/百妖谱", "VFX_；question_id=Q114；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=面板/百妖谱", "VFX_系统面板", "百妖谱",；question_id=Q115；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="百妖谱", "VFX_系统面板/道行计数overlay",；question_id=Q116；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=], "blocking": "百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 com；question_id=Q117；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=谱变成现代手机UI", "不要加入新系统人格" ], "stor；question_id=Q118；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="story_function": "把系统规则和收益用可读 overlay 交接给 compose；question_id=Q119；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="motif_id": "MOTIF_百妖谱系统面板", "vfx_asset": "V；question_id=Q120；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=, "vfx_asset": "VFX_系统面板/百妖谱", "text_layer；question_id=Q121；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=战场/冷灰夜/外", "rhythm": "系统爽点", "dramatic_functio；question_id=Q122；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="audience_effect": "观众获得系统成长爽点，并理解后续刷妖升级的长期玩法。",；question_id=Q123；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=object_ids": [ "VFX_系统面板/百妖谱", "VFX_系统面板",；question_id=Q124；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=VFX_系统面板/百妖谱", "VFX_系统面板", "百妖谱",；question_id=Q125；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="objects": [ "VFX_系统面板/百妖谱", "VFX_系统面板；question_id=Q126；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=X_系统面板/百妖谱", "VFX_系统面板", "百妖谱",；question_id=Q127；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=01/猛虎快刀圆满态", "VFX_系统面板/百妖谱", "VFX_系统面板；question_id=Q128；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=X_系统面板/百妖谱", "VFX_系统面板", "百妖谱",；question_id=Q129；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=火把。", "shot_size": "系统面板特写→系统状态面板+人物半身", "；question_id=Q130；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="shot_size": "系统面板特写→系统状态面板+人物半身", "express；question_id=Q131；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="reason": "三帧契约：锁住人物状态、系统面板或情绪转折的中段锚。" },；question_id=Q132；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=N_01 横刀；出画/画外保留：CHAR_03、VFX_系统面板、百妖谱" }, "shot；question_id=Q133；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=: 2.287, "lens": "系统面板特写", "desc": "古卷；question_id=Q134；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=ects": [ "VFX_系统面板/百妖谱", "VFX_；question_id=Q135；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=面板/百妖谱", "VFX_系统面板", "百妖谱",；question_id=Q136；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=ects": [ "VFX_系统面板/百妖谱", "VFX_；question_id=Q137；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=面板/百妖谱", "VFX_系统面板", "百妖谱",；question_id=Q138；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=ects": [ "VFX_系统面板/百妖谱", "VFX_；question_id=Q139；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=面板/百妖谱", "VFX_系统面板", "百妖谱",；question_id=Q140；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=: 6.933, "lens": "系统状态面板+人物半身", "desc"；question_id=Q141；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=ects": [ "VFX_系统面板/百妖谱", "VFX_；question_id=Q142；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=面板/百妖谱", "VFX_系统面板", "百妖谱",；question_id=Q143；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=], "blocking": "百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 com；question_id=Q144；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=谱变成现代手机UI", "不要加入新系统人格" ], "stor；question_id=Q145；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="story_function": "把系统规则和收益用可读 overlay 交接给 compose；question_id=Q146；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="motif_id": "MOTIF_百妖谱系统面板", "vfx_asset": "V；question_id=Q147；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=, "vfx_asset": "VFX_系统面板/百妖谱", "text_layer；question_id=Q148；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="audience_effect": "观众相信她开始懂系统，不是只靠运气。", "character_；question_id=Q149；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="CHAR_03", "VFX_系统面板", "百妖谱",；question_id=Q150；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="reason": "三帧契约：锁住人物状态、系统面板或情绪转折的中段锚。" },；question_id=Q151；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context=exit": "出画/画外保留：CHAR_03、VFX_系统面板、百妖谱；入画/现身：CHAR_02"；question_id=Q152；signal=系统；status=paid_or_progressed
- expected_next_handling=本集兑现/推进；question_context="reason": "三帧契约：锁住人物状态、系统面板或情绪转折的中段锚。" },；question_id=Q153；signal=系统；status=paid_or_progressed

## Clip 01（时长 12.582s · EP02_CLIP01 · 杀裴后的二十年到账）　**节奏**：冷开爆点
**剧本可看性合同**：clip_id=EP02_CLIP01；dramatic_function=兑现第1集刀入胸口悬念，并把“杀同袍也能到账”的残酷规则打到首屏。；audience_effect=观众先震惊姜月初杀了人，再立刻追问系统为何奖励。；spectacle_story_function=把系统规则和收益用可读 overlay 交接给 compose，使成长爽点清楚可签收。。
**表演签名**：CHAR_01/囚犯初醒态: freeform=先缩肩屏息、迅速扫视逃路；紧张时嘴上吐槽，真做决定时声音压低。；CHAR_02/濒死战损态: freeform=抬眼压人，字少；用断刀或眼神先控场。；CHAR_03/诈死复苏态: freeform=咧嘴笑、舔掌、慢慢扭颈，喜欢先说话再动手。

**首帧**：`出图/第2集/图片/Clip01_first.png`
**中段锚帧**（6.291s · keyframe · 三帧契约：锁住人物状态、系统面板或情绪转折的中段锚。）：`出图/第2集/图片/Clip01_mid.png`
**尾帧**：`出图/第2集/图片/Clip01_end.png`
**场景**：LOC_01 荒野尸骸战场/冷灰夜/外; location_id=LOC_01; 资产：LOC_01, WEAPON_01
**导演意图**：兑现第1集刀入胸口悬念，并把“杀同袍也能到账”的残酷规则打到首屏。
**起幅**：继承首帧构图、光位、轴线、角色状态和物料位置，不重定视觉设定。
**落幅**：落在ECU 固定→CU 手部到眼神，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 compose overlay 渲染。
**表演节拍**：[0s-6.84s] 长刀仍插在裴长青胸口，刀柄轻颤；姜月初半跪在冷灰尸场，百妖谱金光从她瞳孔里亮起。; [6.84s-7.491s] 裴长青失焦的眼睛短暂回光，嘴角只剩半个字，背景虎妖巨影模糊压来。; [7.491s-10.331s] 百妖谱空白古卷在黑背景上展开，留出干净金色面板区，文字全部后期叠加。; [10.331s-12.582s] 姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。
**运动精修**：幅度=小/中；能量=冷开爆点；身体守卫=重心、手部/武器归属、遮挡层级、脸部轮廓和发髻稳定；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：camera/detail moves from embedded blade and dying face to CHAR_01 hand/eye response；minimal force: hilt tremble and CHAR_01 grip tightening; no new stab motion
**动作编排契约 / Action Choreography**：{"body_part_ownership": {"CHAR_01": ["right_hand", "left_hand", "eyes"], "CHAR_02": ["chest", "eyes", "mouth"], "CHAR_03": ["background_silhouette", "tiger_head"], "WEAPON_01": ["hilt", "blade"]}, "contact_points": ["WEAPON_01 blade remains embedded in CHAR_02 chest at start", "CHAR_01 right/both hands close around WEAPON_01 hilt at end", "百妖谱 gold light stays separated as VFX layer near CHAR_01 eyeline"], "force_direction": "minimal force: hilt tremble and CHAR_01 grip tightening; no new stab motion", "holder_state": {"VFX_系统面板/百妖谱": "no physical holder; overlay/VFX layer only", "WEAPON_01": "start embedded in CHAR_02; end controlled by CHAR_01 hands, no handoff from CHAR_02"}, "motion_vector": "camera/detail moves from embedded blade and dying face to CHAR_01 hand/eye response", "notes": "Separates corpse, sword, tiger shadow and system panel so video prompt cannot merge body parts.", "occlusion_order": ["WEAPON_01 hilt and CHAR_01 fingers foreground", "CHAR_02 body midground", "CHAR_03 giant shadow background", "百妖谱 VFX above character layer, text compose overlay only"], "participants": ["CHAR_01", "CHAR_02", "CHAR_03", "WEAPON_01", "VFX_系统面板/百妖谱"], "release_frame": "none; WEAPON_01 stays visible and controlled, not dropped", "schema": "n2d.interaction_graph.v1", "transfer_event": "none"}
**专项镜头模板**：template_id=system_panel; {"beats": ["触发/弹出", "数值或选择展示", "角色反应"], "blocking": "百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 compose overlay 渲染。", "camera_rule": "先角色反应再切面板，面板留干净负空间，不让视频模型生成可读文字。", "continuity_must": ["百妖谱金色古卷样式统一", "面板文字只走 screen_text_lines overlay", "姜月初脸和战损状态连续"], "growth_ref": "screen_text_lines[1] + motif_registry progression；具体文字由 compose overlay 渲染", "motif_id": "MOTIF_百妖谱系统面板", "negative": ["不要烤字进视频画面", "不要随机生成乱码汉字", "不要把百妖谱变成现代手机UI", "不要加入新系统人格"], "panel_tier": "gold_scroll_bestiary", "story_function": "把系统规则和收益用可读 overlay 交接给 compose，使成长爽点清楚可签收。", "template_id": "system_panel", "text_layer": "compose_overlay_only", "vfx_asset": "VFX_系统面板/百妖谱"}
**模型路由**：shot_type=general_motion；template=system_panel；primary_backend=dreamina；fallback_backends=seedance；mode=image2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=reference_group；quality_tier=fast；risk_flags=native_multiframe,seam_relay；degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=cost_quality_tier
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "none", "requires_voice_track": false, "speech_policy": "no_native_speech", "video_generation_audio_policy": "无声视频流"}, "backend": "dreamina", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "If action or identity fails twice, reroute to the nearest specialized shot type.", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "image2video", "quality_tier": "fast", "reference_inputs": {"assets": ["LOC_01"], "characters": [{"binding": "reference_group", "character_id": "CHAR_01", "form": ""}, {"binding": "reference_group", "character_id": "CHAR_02", "form": ""}, {"binding": "reference_group", "character_id": "CHAR_03", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败。
**角色身份注册层**：CHAR_01/囚犯初醒态；identity_requirement=reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态；identity_requirement=reference_group；reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态；identity_requirement=reference_group；reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：长刀仍插在裴长青胸口，刀柄轻颤；姜月初半跪在冷灰尸场，百妖谱金光从她瞳孔里亮起。 → 止：姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。；表情幅度=中；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=无声视频流，禁止模型生成台词、旁白、哼唱、系统音或环境人声，不使用音频输入。
**在场链约束**：required_presence=['CHAR_01/血尘战损态', 'CHAR_02/死亡态', 'CHAR_03/复苏战斗态', 'WEAPON_01 横刀', 'VFX_系统面板/百妖谱', 'VFX_系统面板', '百妖谱', 'LOC_01']；offscreen_presence=[]；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：VFX_系统面板、百妖谱；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：长刀仍插在裴长青胸口，刀柄轻颤；姜月初半跪在冷灰尸场，百妖谱金光从她瞳孔里亮起。
- 出点：姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。
- 转场：cut
- 连贯性：eyeline=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。; shot_size=ECU 固定→CU 手部到眼神; need_endframe=True

**continuity**：
- start_state：长刀仍插在裴长青胸口，刀柄轻颤；姜月初半跪在冷灰尸场，百妖谱金光从她瞳孔里亮起。
- action：触发/弹出；数值或选择展示；角色反应
- end_state：姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01, WEAPON_01；保持 CHAR_01, CHAR_02, CHAR_03 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 长刀仍插在裴长青胸口，刀柄轻颤；姜月初半跪在冷灰尸场，百妖谱金光从她瞳孔里亮起。
  action: 触发/弹出；数值或选择展示；角色反应
  end_state: 姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。
  constraints: 保持 LOC_01、LOC_01, WEAPON_01、CHAR_01, CHAR_02, CHAR_03 的视觉连续；轴线=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：兑现第1集刀入胸口悬念，并把“杀同袍也能到账”的残酷规则打到首屏。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定;
落幅：落在ECU 固定→CU 手部到眼神，动作/表情在最后 0.3-0.5 秒稳定住; 
场面调度：百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 compose overlay 渲染。;
表演节拍：[0s-6.84s] 长刀仍插在裴长青胸口，刀柄轻颤；姜月初半跪在冷灰尸场，百妖谱金光从她瞳孔里亮起。; [6.84s-7.491s] 裴长青失焦的眼睛短暂回光，嘴角只剩半个字，背景虎妖巨影模糊压来。; [7.491s-10.331s] 百妖谱空白古卷在黑背景上展开，留出干净金色面板区，文字全部后期叠加。; [10.331s-12.582s] 姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。;
运动精修约束：幅度小到中，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：camera/detail moves from embedded blade and dying face to CHAR_01 hand/eye response；minimal force: hilt tremble and CHAR_01 grip tightening; no new stab motion;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：{"body_part_ownership": {"CHAR_01": ["right_hand", "left_hand", "eyes"], "CHAR_02": ["chest", "eyes", "mouth"], "CHAR_03": ["background_silhouette", "tiger_head"], "WEAPON_01": ["hilt", "blade"]}, "contact_points": ["WEAPON_01 blade remains embedded in CHAR_02 chest at start", "CHAR_01 right/both hands close around WEAPON_01 hilt at end", "百妖谱 gold light stays separated as VFX layer near CHAR_01 eyeline"], "force_direction": "minimal force: hilt tremble and CHAR_01 grip tightening; no new stab motion", "holder_state": {"VFX_系统面板/百妖谱": "no physical holder; overlay/VFX layer only", "WEAPON_01": "start embedded in CHAR_02; end controlled by CHAR_01 hands, no handoff from CHAR_02"}, "motion_vector": "camera/detail moves from embedded blade and dying face to CHAR_01 hand/eye response", "notes": "Separates corpse, sword, tiger shadow and system panel so video prompt cannot merge body parts.", "occlusion_order": ["WEAPON_01 hilt and CHAR_01 fingers foreground", "CHAR_02 body midground", "CHAR_03 giant shadow background", "百妖谱 VFX above character layer, text compose overlay only"], "participants": ["CHAR_01", "CHAR_02", "CHAR_03", "WEAPON_01", "VFX_系统面板/百妖谱"], "release_frame": "none; WEAPON_01 stays visible and controlled, not dropped", "schema": "n2d.interaction_graph.v1", "transfer_event": "none"};
专项模板约束：template_id=system_panel，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=general_motion；template=system_panel；primary_backend=dreamina；fallback_backends=seedance；mode=image2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=reference_group；quality_tier=fast；risk_flags=native_multiframe,seam_relay；degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=cost_quality_tier; prompt 只使用 primary_backend 真实支持的无声视频能力，失败按 degrade_plan/fallback 执行;
物理交互约束：无；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败。;
身份锁定约束：CHAR_01/囚犯初醒态；identity_requirement=reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态；identity_requirement=reference_group；reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态；identity_requirement=reference_group；reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：长刀仍插在裴长青胸口，刀柄轻颤；姜月初半跪在冷灰尸场，百妖谱金光从她瞳孔里亮起。 → 止：姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。；表情幅度=中；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01/血尘战损态', 'CHAR_02/死亡态', 'CHAR_03/复苏战斗态', 'WEAPON_01 横刀', 'VFX_系统面板/百妖谱', 'VFX_系统面板', '百妖谱', 'LOC_01']；offscreen_presence=[]；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：VFX_系统面板、百妖谱；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；视频生成音频策略=无声视频流；不要使用音频输入；禁止原生人声、台词、旁白、哼唱、系统音和字幕文字;
人物运动：触发/弹出；数值或选择展示；角色反应；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：先角色反应再切面板，面板留干净负空间，不让视频模型生成可读文字。;
情绪节奏：[0-终点] 长刀仍插在裴长青胸口，刀柄轻颤；姜月初半跪在冷灰尸场，百妖谱金光从她瞳孔里亮起。 -> 姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 constraints，避开 negative，按cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；视频-only silent stream；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: execute only this clip beat; do not add story events;
opening frame state: 长刀仍插在裴长青胸口，刀柄轻颤；姜月初半跪在冷灰尸场，百妖谱金光从她瞳孔里亮起。;
ending frame state: 姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。;
blocking: 百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 compose overlay 渲染。;
performance beats: [0s-6.84s] 长刀仍插在裴长青胸口，刀柄轻颤；姜月初半跪在冷灰尸场，百妖谱金光从她瞳孔里亮起。; [6.84s-7.491s] 裴长青失焦的眼睛短暂回光，嘴角只剩半个字，背景虎妖巨影模糊压来。; [7.491s-10.331s] 百妖谱空白古卷在黑背景上展开，留出干净金色面板区，文字全部后期叠加。; [10.331s-12.582s] 姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。;
motion refinement: low-to-medium amplitude, stable body balance, clear hand and weapon ownership, no face stretching;
close-up identity lock: use reference_group, face close-up, expression references; lock face not emotion; keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01/血尘战损态', 'CHAR_02/死亡态', 'CHAR_03/复苏战斗态', 'WEAPON_01 横刀', 'VFX_系统面板/百妖谱', 'VFX_系统面板', '百妖谱', 'LOC_01']；offscreen_presence=[]；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：VFX_系统面板、百妖谱；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 触发/弹出；数值或选择展示；角色反应;
camera motion: 先角色反应再切面板，面板留干净负空间，不让视频模型生成可读文字。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative;
audio constraint: silent video stream only, no generated speech, no narration, no native voice, no humming, no subtitles; do not use audio input; discard any forced backend audio later.
```

### 平台参数
- primary_backend=dreamina; fallback_backends=['seedance']; mode=image2video; quality_tier=fast; duration=12.582s; aspect=9:16; native_audio_policy=none; video_generation_audio_policy=无声视频流; identity adapter=reference_group; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全，FeatureMelting/特征融化判失败
5. ✅ ②镜头运动：推/拉/摇/移/固定/跟拍等结构化词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气/火把随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：已登记角色ID/形态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; speech_policy=no_native_speech; compose_policy=丢弃; 无声视频流; 不使用音频输入
14. ✅ Motion Control：按本镜 route/control manifest 或 degrade_plan 执行

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜

## Clip 02（时长 12.349s · EP02_CLIP02 · 虎妖嘲讽与转刀）　**节奏**：情绪/叙事推进
**剧本可看性合同**：clip_id=EP02_CLIP02；dramatic_function=把道德压力转成求生选择，完成从崩溃到反击的情绪转弯。；audience_effect=观众看到她不是变善或变坏，而是被逼到只剩活路。；spectacle_story_function=通过嘲讽逼出主角求生宣言，完成情绪转向。。
**表演签名**：CHAR_01/囚犯初醒态: freeform=先缩肩屏息、迅速扫视逃路；紧张时嘴上吐槽，真做决定时声音压低。；CHAR_02/濒死战损态: freeform=抬眼压人，字少；用断刀或眼神先控场。；CHAR_03/诈死复苏态: freeform=咧嘴笑、舔掌、慢慢扭颈，喜欢先说话再动手。

**首帧**：`出图/第2集/图片/Clip02_first.png`
**中段锚帧**（6.175s · keyframe · 三帧契约：锁住人物状态、系统面板或情绪转折的中段锚。）：`出图/第2集/图片/Clip02_mid.png`
**尾帧**：`出图/第2集/图片/Clip02_end.png`
**场景**：LOC_01 荒野尸骸战场/冷灰夜/外; location_id=LOC_01; 资产：LOC_01, WEAPON_01
**导演意图**：把道德压力转成求生选择，完成从崩溃到反击的情绪转弯。
**起幅**：继承首帧构图、光位、轴线、角色状态和物料位置，不重定视觉设定。
**落幅**：落在MCU 横移→CU 正反打，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：虎山神高位压画右，姜月初低位在画左；裴长青尸身只作前景/背景压力，不参与对白。
**表演节拍**：[0s-4.061s] 姜月初背对裴长青尸身站起，前景刀刃带血，远处虎山神仍未倒下。; [4.061s-8.273s] 虎山神俯视姜月初，金黄兽眼讥讽，胸口黑血窟窿还在滴落。; [8.273s-12.349s] 姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。
**运动精修**：幅度=小/中；能量=情绪/叙事推进；身体守卫=重心、手部/武器归属、遮挡层级、脸部轮廓和发髻稳定；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：CHAR_01 rises/sets stance; blade direction rotates from corpse-side to tiger-side；psychological pressure only; CHAR_03 shadow presses downward, CHAR_01 raises blade line upward
**动作编排契约 / Action Choreography**：{"body_part_ownership": {"CHAR_01": ["hands", "eyes", "shoulders"], "CHAR_02": ["corpse_body"], "CHAR_03": ["claws", "chest_wound", "tiger_head"], "WEAPON_01": ["hilt", "blade_tip"]}, "contact_points": ["CHAR_01 holds WEAPON_01; blade tip rotates away from CHAR_02 direction toward CHAR_03", "CHAR_03 claw shadow lowers without touching CHAR_01 in this clip", "CHAR_02 remains corpse/background pressure only"], "force_direction": "psychological pressure only; CHAR_03 shadow presses downward, CHAR_01 raises blade line upward", "holder_state": {"CHAR_02": "not holder, remains death state", "WEAPON_01": "held by CHAR_01 throughout; no hand switch"}, "motion_vector": "CHAR_01 rises/sets stance; blade direction rotates from corpse-side to tiger-side", "notes": "Keeps dead body non-participating and prevents tiger/hero contact before the fight beat.", "occlusion_order": ["foreground blade edge", "CHAR_01 low left position", "CHAR_03 high right position/shadow", "CHAR_02 body behind/edge of frame"], "participants": ["CHAR_01", "CHAR_02", "CHAR_03", "WEAPON_01"], "release_frame": "none", "schema": "n2d.interaction_graph.v1", "transfer_event": "none"}
**专项镜头模板**：template_id=dialogue_shot_reverse; {"axis": "LOC_01 荒野尸骸战场/冷灰夜/外 左右轴线；反打不越轴", "beats": ["虎妖道德嘲讽", "姜月初压住崩溃", "刀尖转向虎妖"], "blocking": "虎山神高位压画右，姜月初低位在画左；裴长青尸身只作前景/背景压力，不参与对白。", "camera_rule": "保持同一视线轴和高低差，反打不越轴；虎妖镜头压迫，姜月初镜头收紧。", "continuity_must": ["虎妖胸口伤洞不消失", "姜月初手里横刀方向从裴长青转向虎山神", "裴长青保持死亡态"], "eyeline": "姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。", "negative": ["不要把对白拍成轻松斗嘴", "不要让裴长青复活插话", "不要新增旁观者"], "shot_pairing": "压迫方反打 ↔ 受压方反打；按 blocking 保持高低位和左右关系", "story_function": "通过嘲讽逼出主角求生宣言，完成情绪转向。", "template_id": "dialogue_shot_reverse"}
**模型路由**：shot_type=dialogue_shot_reverse；template=dialogue_shot_reverse；primary_backend=seedance；fallback_backends=dreamina；mode=image2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=character_id_or_reference_group；quality_tier=high；risk_flags=mouth_visible,native_multiframe,seam_relay；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=cost_quality_tier
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "none", "requires_voice_track": false, "speech_policy": "no_native_speech", "video_generation_audio_policy": "无声视频流"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "image2video", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01"], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_01", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_02", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_03", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败。
**角色身份注册层**：CHAR_01/囚犯初醒态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。 → 止：姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=medium_no_native_speech; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=无声视频流，禁止模型生成台词、旁白、哼唱、系统音或环境人声，不使用音频输入。
**在场链约束**：required_presence=['CHAR_01/血尘战损态', 'CHAR_02/死亡态', 'CHAR_03/复苏战斗态', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['VFX_系统面板', '百妖谱']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：VFX_系统面板、百妖谱；出画/画外保留：CHAR_02；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。
- 出点：姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。
- 转场：cut
- 连贯性：eyeline=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。; shot_size=MCU 横移→CU 正反打; need_endframe=True

**continuity**：
- start_state：姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。
- action：虎妖道德嘲讽；姜月初压住崩溃；刀尖转向虎妖
- end_state：姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01, WEAPON_01；保持 CHAR_01, CHAR_02, CHAR_03 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。
  action: 虎妖道德嘲讽；姜月初压住崩溃；刀尖转向虎妖
  end_state: 姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。
  constraints: 保持 LOC_01、LOC_01, WEAPON_01、CHAR_01, CHAR_02, CHAR_03 的视觉连续；轴线=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：把道德压力转成求生选择，完成从崩溃到反击的情绪转弯。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定;
落幅：落在MCU 横移→CU 正反打，动作/表情在最后 0.3-0.5 秒稳定住; 
场面调度：虎山神高位压画右，姜月初低位在画左；裴长青尸身只作前景/背景压力，不参与对白。;
表演节拍：[0s-4.061s] 姜月初背对裴长青尸身站起，前景刀刃带血，远处虎山神仍未倒下。; [4.061s-8.273s] 虎山神俯视姜月初，金黄兽眼讥讽，胸口黑血窟窿还在滴落。; [8.273s-12.349s] 姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。;
运动精修约束：幅度小到中，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：CHAR_01 rises/sets stance; blade direction rotates from corpse-side to tiger-side；psychological pressure only; CHAR_03 shadow presses downward, CHAR_01 raises blade line upward;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：{"body_part_ownership": {"CHAR_01": ["hands", "eyes", "shoulders"], "CHAR_02": ["corpse_body"], "CHAR_03": ["claws", "chest_wound", "tiger_head"], "WEAPON_01": ["hilt", "blade_tip"]}, "contact_points": ["CHAR_01 holds WEAPON_01; blade tip rotates away from CHAR_02 direction toward CHAR_03", "CHAR_03 claw shadow lowers without touching CHAR_01 in this clip", "CHAR_02 remains corpse/background pressure only"], "force_direction": "psychological pressure only; CHAR_03 shadow presses downward, CHAR_01 raises blade line upward", "holder_state": {"CHAR_02": "not holder, remains death state", "WEAPON_01": "held by CHAR_01 throughout; no hand switch"}, "motion_vector": "CHAR_01 rises/sets stance; blade direction rotates from corpse-side to tiger-side", "notes": "Keeps dead body non-participating and prevents tiger/hero contact before the fight beat.", "occlusion_order": ["foreground blade edge", "CHAR_01 low left position", "CHAR_03 high right position/shadow", "CHAR_02 body behind/edge of frame"], "participants": ["CHAR_01", "CHAR_02", "CHAR_03", "WEAPON_01"], "release_frame": "none", "schema": "n2d.interaction_graph.v1", "transfer_event": "none"};
专项模板约束：template_id=dialogue_shot_reverse，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=dialogue_shot_reverse；template=dialogue_shot_reverse；primary_backend=seedance；fallback_backends=dreamina；mode=image2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=character_id_or_reference_group；quality_tier=high；risk_flags=mouth_visible,native_multiframe,seam_relay；degrade_plan=Switch to over-shoulder, side-face, hands, or reaction inserts if mouth motion fails.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=cost_quality_tier; prompt 只使用 primary_backend 真实支持的无声视频能力，失败按 degrade_plan/fallback 执行;
物理交互约束：无；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败。;
身份锁定约束：CHAR_01/囚犯初醒态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗；CHAR_03/诈死复苏态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。 → 止：姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01/血尘战损态', 'CHAR_02/死亡态', 'CHAR_03/复苏战斗态', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['VFX_系统面板', '百妖谱']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：VFX_系统面板、百妖谱；出画/画外保留：CHAR_02；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=medium_no_native_speech; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃；视频生成音频策略=无声视频流；不要使用音频输入；禁止原生人声、台词、旁白、哼唱、系统音和字幕文字;
人物运动：虎妖道德嘲讽；姜月初压住崩溃；刀尖转向虎妖；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：保持同一视线轴和高低差，反打不越轴；虎妖镜头压迫，姜月初镜头收紧。;
情绪节奏：[0-终点] 姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。 -> 姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 constraints，避开 negative，按cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；视频-only silent stream；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: execute only this clip beat; do not add story events;
opening frame state: 姜月初沾血的手指攥紧刀柄，眼里的金光映出“二十年”的虚影。;
ending frame state: 姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。;
blocking: 虎山神高位压画右，姜月初低位在画左；裴长青尸身只作前景/背景压力，不参与对白。;
performance beats: [0s-4.061s] 姜月初背对裴长青尸身站起，前景刀刃带血，远处虎山神仍未倒下。; [4.061s-8.273s] 虎山神俯视姜月初，金黄兽眼讥讽，胸口黑血窟窿还在滴落。; [8.273s-12.349s] 姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。;
motion refinement: low-to-medium amplitude, stable body balance, clear hand and weapon ownership, no face stretching;
close-up identity lock: use reference_group, face close-up, expression references; lock face not emotion; keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01/血尘战损态', 'CHAR_02/死亡态', 'CHAR_03/复苏战斗态', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['VFX_系统面板', '百妖谱']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：VFX_系统面板、百妖谱；出画/画外保留：CHAR_02；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 虎妖道德嘲讽；姜月初压住崩溃；刀尖转向虎妖;
camera motion: 保持同一视线轴和高低差，反打不越轴；虎妖镜头压迫，姜月初镜头收紧。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative;
audio constraint: silent video stream only, no generated speech, no narration, no native voice, no humming, no subtitles; do not use audio input; discard any forced backend audio later.
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=image2video; quality_tier=high; duration=12.349s; aspect=9:16; native_audio_policy=none; video_generation_audio_policy=无声视频流; identity adapter=character_id_or_reference_group; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全，FeatureMelting/特征融化判失败
5. ✅ ②镜头运动：推/拉/摇/移/固定/跟拍等结构化词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气/火把随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：已登记角色ID/形态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; speech_policy=no_native_speech; compose_policy=丢弃; 无声视频流; 不使用音频输入
14. ✅ Motion Control：按本镜 route/control manifest 或 degrade_plan 执行

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜

## Clip 03（时长 11.477s · EP02_CLIP03 · 二十年尽压一刀）　**节奏**：动作高潮
**剧本可看性合同**：clip_id=EP02_CLIP03；dramatic_function=把刚到手的二十年道行当成一次性赌注，制造“够不够”的悬念。；audience_effect=观众获得蓄力爽感，同时担心她把唯一筹码烧光。；spectacle_story_function=动作奇观服务“二十年赌一刀”的生死兑现，不为炫技扩写。。
**表演签名**：CHAR_01/囚犯初醒态: freeform=先缩肩屏息、迅速扫视逃路；紧张时嘴上吐槽，真做决定时声音压低。；CHAR_03/诈死复苏态: freeform=咧嘴笑、舔掌、慢慢扭颈，喜欢先说话再动手。

**首帧**：`出图/第2集/图片/Clip03_first.png`
**锚帧1**（4.2s · split · 起手蓄力：二十年道行灌入横刀，姜月初压低肩线。）：`出图/第2集/图片/Clip03_a1.png`
**锚帧2**（8.6s · keyframe · 逼近冲撞前：虎山神巨爪打开，双方轴线固定。）：`出图/第2集/图片/Clip03_a2.png`
**尾帧**：`出图/第2集/图片/Clip03_end.png`
**场景**：LOC_01 荒野尸骸战场/冷灰夜/外; location_id=LOC_01; 资产：LOC_01, WEAPON_01
**导演意图**：把刚到手的二十年道行当成一次性赌注，制造“够不够”的悬念。
**起幅**：继承首帧构图、光位、轴线、角色状态和物料位置，不重定视觉设定。
**落幅**：落在MS→CU 推近→LS 对峙，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：姜月初始终由画左低位向画右斜线推进；虎山神由画右高位向画左压下，双方轴线不跳。
**表演节拍**：[0s-5.719s] 二十年道行化作细金纹灌入横刀，刀身从暗银变成短暂暖金。; [5.719s-8.052s] 姜月初双手持刀，肩线压低，刀锋贴着草尖抬起。; [8.052s-11.477s] 虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。
**运动精修**：幅度=小/中；能量=动作高潮；身体守卫=重心、手部/武器归属、遮挡层级、脸部轮廓和发髻稳定；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：CHAR_01 advances left-to-right; CHAR_03 descends right-to-left; apex near center-right at 8.6s；CHAR_03 force vector: screen right/high to left/low; CHAR_01 sword vector: screen left/low to right/high；禁止慢动作中肢体穿模；人物比例和接触方向必须与锚帧一致。；尸场中央枯草带作为冲撞路径，巨岩在背景画右固定。
**动作编排契约 / Action Choreography**：{"body_part_ownership": {"CHAR_01": ["left_hand", "right_hand", "forearms", "shoulders"], "CHAR_03": ["right_claw", "tiger_head", "torso"], "WEAPON_01": ["hilt", "blade", "spine"]}, "contact_points": ["CHAR_01 both hands grip WEAPON_01 hilt", "CHAR_03 claw presses toward WEAPON_01 blade without body fusion", "gold cultivation lines run along CHAR_01 arm into blade"], "force_direction": "CHAR_03 force vector: screen right/high to left/low; CHAR_01 sword vector: screen left/low to right/high", "holder_state": {"CHAR_03 claws": "owned by CHAR_03 only; never become extra human hands", "WEAPON_01": "two-hand grip by CHAR_01 from start to end"}, "motion_vector": "CHAR_01 advances left-to-right; CHAR_03 descends right-to-left; apex near center-right at 8.6s", "notes": "Fight contact is claw-to-blade, not claw-to-face/body.", "occlusion_order": ["WEAPON_01 blade/light at collision line", "CHAR_01 low-left body behind blade", "CHAR_03 claw/head high-right", "dust/VFX behind contact line"], "participants": ["CHAR_01", "CHAR_03", "WEAPON_01"], "release_frame": "none", "schema": "n2d.interaction_graph.v1", "transfer_event": "none"}
**专项镜头模板**：template_id=fight_exchange; {"action_scope": "两主体近身一击，不扩展成群战或长追逐。", "apex_light": "8.6s 接触点短白金闪，不铺满全屏，保留人物轮廓。", "attack_path": "虎爪自画右上压向画左下；横刀自画左下挑向画右上，交点锁在画面中线偏右。", "beats": ["起手蓄力", "爪刀相撞", "错身斩断", "反应/收势"], "blocking": "姜月初始终由画左低位向画右斜线推进；虎山神由画右高位向画左压下，双方轴线不跳。", "camera_path": "低角度推近→侧移跟拍→静止落点。", "camera_rule": "先给完整动作线，再给一处刀光特写，最后反应静止；不做连续乱切和旋转镜头。", "clash_frame": "兵器/爪风相交 8.6s：刀锋与虎爪妖风硬碰，接触点迸出短促金灰火星。", "combat_micro_expression": "8.6s 姜月初咬紧牙关、眉心压低；虎山神兽眼暴怒，嘴角讥笑消失。", "contact_points": ["虎爪压近刀锋", "刀光切开妖风和颈侧妖气", "姜月初双手握刀保持同一姿势"], "continuity_must": ["横刀在姜月初手中不换手", "虎山神体型约成人2.8倍", "刀光方向从画左下到画右上", "斩首只给轮廓和尘土，避免猎奇"], "degrade_plan": "若一段内动作不稳，拆为起手/冲撞/错身/落点四张锚帧。", "force_direction": "虎妖向下压，姜月初向上斜挑，力线清楚相反。", "impact_frame": "命中/apex 8.6s：虎山神巨爪与姜月初横刀力线在画面中线压到最近，尚未展示结果。", "keyframe_plan": ["first=蓄力或冲撞前", "anchor=命中/错身", "end=结果落定"], "negative": ["不要多出第三名参战者", "不要把虎山神画成普通老虎", "不要出现血腥断面特写", "不要让姜月初换制服或换脸"], "physics_guard": "禁止慢动作中肢体穿模；人物比例和接触方向必须与锚帧一致。", "post_cue_points": ["4.2s 金纹灌刀低频起", "8.6s hit-stop/impact_sfx/微震屏", "10.8s 环境风声压低切入下一镜"], "readability_beats": ["谁先动", "力量如何相撞", "刀光切过哪里", "结果是谁倒下"], "recovery_beat": "姜月初背影僵住，虎山神妖气塌落，给观众半秒确认。", "risk_flags": ["high_action", "contact_motion", "physics"], "screen_direction": "姜月初左到右，虎山神右到左；镜头不越轴。", "secondary_motion": "枯草向同一方向压倒，姜月初发梢和衣摆被妖风向后拉，刀身金纹震颤。", "spatial_path": "尸场中央枯草带作为冲撞路径，巨岩在背景画右固定。", "spectacle_story_function": "动作奇观服务“二十年赌一刀”的生死兑现，不为炫技扩写。", "speed_curve": "蓄力慢半拍，冲撞极快，错身后骤停。", "template_id": "fight_exchange"}
**模型路由**：shot_type=fight_exchange；template=fight_exchange；primary_backend=seedance；fallback_backends=dreamina；mode=frames2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=character_id_or_reference_group；quality_tier=high；risk_flags=action_choreography_required,contact_motion,feature_melting_risk,identity_drift_risk,motion_reference_candidate,mouth_visible,native_multiframe,physical_interaction,seam_relay；degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=motion_control_required
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "none", "requires_voice_track": false, "speech_policy": "no_native_speech", "video_generation_audio_policy": "无声视频流"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": true}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第2集/control/Clip_03/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks", "contact_map", "camera_path"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "Split into setup and impact clips; keep the hit frame as the end frame.", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 2, "native_timeline_frames": 4, "reference_only": false, "requires_split_relay": false}, "mode": "frames2video", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01"], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_01", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_03", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_02", "form": ""}], "identity_preservation_plan": {"applies_to": "fight_exchange", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "character_id_or_reference_group", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": true, "library_path": "生产数据/motion_reference_library.json", "policy": "use same sequence/shot_type approved reference when available"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：required=true；manifest_path=出视频/第2集/control/Clip_03/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、接触漂移、武器归属错都判失败。
**角色身份注册层**：CHAR_01/囚犯初醒态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_03/诈死复苏态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。 → 止：虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=medium_no_native_speech; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=无声视频流，禁止模型生成台词、旁白、哼唱、系统音或环境人声，不使用音频输入。
**在场链约束**：required_presence=['CHAR_01/血尘战损态', 'CHAR_03/复苏战斗态', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['CHAR_02']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：CHAR_02；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。
- 出点：虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。
- 转场：cut
- 连贯性：eyeline=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。; shot_size=MS→CU 推近→LS 对峙; need_endframe=True

**continuity**：
- start_state：姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。
- action：起手蓄力；爪刀相撞；错身斩断；反应/收势
- end_state：虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01, WEAPON_01；保持 CHAR_01, CHAR_03 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。
  action: 起手蓄力；爪刀相撞；错身斩断；反应/收势
  end_state: 虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。
  constraints: 保持 LOC_01、LOC_01, WEAPON_01、CHAR_01, CHAR_03 的视觉连续；轴线=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：把刚到手的二十年道行当成一次性赌注，制造“够不够”的悬念。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定;
落幅：落在MS→CU 推近→LS 对峙，动作/表情在最后 0.3-0.5 秒稳定住; 
场面调度：姜月初始终由画左低位向画右斜线推进；虎山神由画右高位向画左压下，双方轴线不跳。;
表演节拍：[0s-5.719s] 二十年道行化作细金纹灌入横刀，刀身从暗银变成短暂暖金。; [5.719s-8.052s] 姜月初双手持刀，肩线压低，刀锋贴着草尖抬起。; [8.052s-11.477s] 虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。;
运动精修约束：幅度小到中，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：CHAR_01 advances left-to-right; CHAR_03 descends right-to-left; apex near center-right at 8.6s；CHAR_03 force vector: screen right/high to left/low; CHAR_01 sword vector: screen left/low to right/high；禁止慢动作中肢体穿模；人物比例和接触方向必须与锚帧一致。；尸场中央枯草带作为冲撞路径，巨岩在背景画右固定。;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：{"body_part_ownership": {"CHAR_01": ["left_hand", "right_hand", "forearms", "shoulders"], "CHAR_03": ["right_claw", "tiger_head", "torso"], "WEAPON_01": ["hilt", "blade", "spine"]}, "contact_points": ["CHAR_01 both hands grip WEAPON_01 hilt", "CHAR_03 claw presses toward WEAPON_01 blade without body fusion", "gold cultivation lines run along CHAR_01 arm into blade"], "force_direction": "CHAR_03 force vector: screen right/high to left/low; CHAR_01 sword vector: screen left/low to right/high", "holder_state": {"CHAR_03 claws": "owned by CHAR_03 only; never become extra human hands", "WEAPON_01": "two-hand grip by CHAR_01 from start to end"}, "motion_vector": "CHAR_01 advances left-to-right; CHAR_03 descends right-to-left; apex near center-right at 8.6s", "notes": "Fight contact is claw-to-blade, not claw-to-face/body.", "occlusion_order": ["WEAPON_01 blade/light at collision line", "CHAR_01 low-left body behind blade", "CHAR_03 claw/head high-right", "dust/VFX behind contact line"], "participants": ["CHAR_01", "CHAR_03", "WEAPON_01"], "release_frame": "none", "schema": "n2d.interaction_graph.v1", "transfer_event": "none"};
专项模板约束：template_id=fight_exchange，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=fight_exchange；template=fight_exchange；primary_backend=seedance；fallback_backends=dreamina；mode=frames2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=character_id_or_reference_group；quality_tier=high；risk_flags=action_choreography_required,contact_motion,feature_melting_risk,identity_drift_risk,motion_reference_candidate,mouth_visible,native_multiframe,physical_interaction,seam_relay；degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=motion_control_required; prompt 只使用 primary_backend 真实支持的无声视频能力，失败按 degrade_plan/fallback 执行;
物理交互约束：required=true；manifest_path=出视频/第2集/control/Clip_03/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、接触漂移、武器归属错都判失败。;
身份锁定约束：CHAR_01/囚犯初醒态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_03/诈死复苏态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。 → 止：虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01/血尘战损态', 'CHAR_03/复苏战斗态', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['CHAR_02']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：CHAR_02；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=medium_no_native_speech; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃；视频生成音频策略=无声视频流；不要使用音频输入；禁止原生人声、台词、旁白、哼唱、系统音和字幕文字;
人物运动：起手蓄力；爪刀相撞；错身斩断；反应/收势；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：先给完整动作线，再给一处刀光特写，最后反应静止；不做连续乱切和旋转镜头。;
情绪节奏：[0-终点] 姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。 -> 虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 constraints，避开 negative，按cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；视频-only silent stream；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: execute only this clip beat; do not add story events;
opening frame state: 姜月初抬眼，泪痕被血尘盖住，恐惧收进眼底，只剩求生狠意。;
ending frame state: 虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。;
blocking: 姜月初始终由画左低位向画右斜线推进；虎山神由画右高位向画左压下，双方轴线不跳。;
performance beats: [0s-5.719s] 二十年道行化作细金纹灌入横刀，刀身从暗银变成短暂暖金。; [5.719s-8.052s] 姜月初双手持刀，肩线压低，刀锋贴着草尖抬起。; [8.052s-11.477s] 虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。;
motion refinement: low-to-medium amplitude, stable body balance, clear hand and weapon ownership, no face stretching;
close-up identity lock: use reference_group, face close-up, expression references; lock face not emotion; keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01/血尘战损态', 'CHAR_03/复苏战斗态', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['CHAR_02']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：CHAR_02；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 起手蓄力；爪刀相撞；错身斩断；反应/收势;
camera motion: 先给完整动作线，再给一处刀光特写，最后反应静止；不做连续乱切和旋转镜头。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative;
audio constraint: silent video stream only, no generated speech, no narration, no native voice, no humming, no subtitles; do not use audio input; discard any forced backend audio later.
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=frames2video; quality_tier=high; duration=11.477s; aspect=9:16; native_audio_policy=none; video_generation_audio_policy=无声视频流; identity adapter=character_id_or_reference_group; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 2, "native_timeline_frames": 4, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全，FeatureMelting/特征融化判失败
5. ✅ ②镜头运动：推/拉/摇/移/固定/跟拍等结构化词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气/火把随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：已登记角色ID/形态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; speech_policy=no_native_speech; compose_policy=丢弃; 无声视频流; 不使用音频输入
14. ✅ Motion Control：按本镜 route/control manifest 或 degrade_plan 执行

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜

## Clip 04（时长 11.995s · EP02_CLIP04 · 一刀斩虎山神）　**节奏**：动作高潮
**剧本可看性合同**：clip_id=EP02_CLIP04；dramatic_function=兑现二十年赌刀的动作高潮，用短促清晰的一刀完成反杀。；audience_effect=观众看到弱者以规则和狠劲翻盘，获得本集第一大爽点。；spectacle_story_function=动作奇观服务“二十年赌一刀”的生死兑现，不为炫技扩写。。
**表演签名**：CHAR_01/囚犯初醒态: freeform=先缩肩屏息、迅速扫视逃路；紧张时嘴上吐槽，真做决定时声音压低。；CHAR_03/诈死复苏态: freeform=咧嘴笑、舔掌、慢慢扭颈，喜欢先说话再动手。

**首帧**：`出图/第2集/图片/Clip04_first.png`
**锚帧1**（3.8s · split · 冲撞起手：虎爪压下，刀光迎上，动作线完整可读。）：`出图/第2集/图片/Clip04_a1.png`
**锚帧2**（7.8s · keyframe · 命中/错身：刀光切过妖风，结果尚未落地。）：`出图/第2集/图片/Clip04_a2.png`
**锚帧3**（10.4s · split · 反应收势：虎头落地轮廓，姜月初背影僵住。）：`出图/第2集/图片/Clip04_a3.png`
**尾帧**：`出图/第2集/图片/Clip04_end.png`
**场景**：LOC_01 荒野尸骸战场/冷灰夜/外; location_id=LOC_01; 资产：LOC_01, WEAPON_01
**导演意图**：兑现二十年赌刀的动作高潮，用短促清晰的一刀完成反杀。
**起幅**：继承首帧构图、光位、轴线、角色状态和物料位置，不重定视觉设定。
**落幅**：落在WIDE 动作全景→LOW 静止，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：姜月初始终由画左低位向画右斜线推进；虎山神由画右高位向画左压下，双方轴线不跳。
**表演节拍**：[0s-4.826s] 虎爪压下，刀光迎上，荒草被妖风刮成同一方向。; [4.826s-9.689s] 人与妖错身而过，刀光只亮一瞬，虎妖胸颈处出现冷亮切线。; [9.689s-11.995s] 虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。
**运动精修**：幅度=小/中；能量=动作高潮；身体守卫=重心、手部/武器归属、遮挡层级、脸部轮廓和发髻稳定；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：start collision at 3.8s, cross-body apex at 7.8s, recovery/landing at 10.4s；CHAR_03 downward/right-to-left pressure opposed by CHAR_01 upward/left-to-right slash；禁止慢动作中肢体穿模；人物比例和接触方向必须与锚帧一致。；尸场中央枯草带作为冲撞路径，巨岩在背景画右固定。
**动作编排契约 / Action Choreography**：{"body_part_ownership": {"CHAR_01": ["hands", "back", "shoulders"], "CHAR_03": ["claws", "neck_side_aura", "tiger_head", "torso"], "VFX_妖气": ["black_gray_aura", "dust"], "WEAPON_01": ["blade", "hilt"]}, "contact_points": ["WEAPON_01 blade line intersects CHAR_03 neck-side demonic aura at apex", "CHAR_03 claw passes over/near blade without grabbing it", "CHAR_01 body and tiger body cross paths but stay separate silhouettes"], "force_direction": "CHAR_03 downward/right-to-left pressure opposed by CHAR_01 upward/left-to-right slash", "holder_state": {"CHAR_03 head/body": "after apex becomes separate shadow silhouette only, non-gory", "WEAPON_01": "CHAR_01 keeps two-hand/firm grip; no drop after impact"}, "motion_vector": "start collision at 3.8s, cross-body apex at 7.8s, recovery/landing at 10.4s", "notes": "Occlusion uses dust/VFX to avoid graphic anatomy while preserving action readability.", "occlusion_order": ["dust/aura foreground masks impact", "WEAPON_01 cold light line", "CHAR_01 silhouette", "CHAR_03 giant silhouette/head outline"], "participants": ["CHAR_01", "CHAR_03", "WEAPON_01", "VFX_妖气"], "release_frame": "CHAR_03 head outline separates into dust/grass after 9.689s; avoid gore detail", "schema": "n2d.interaction_graph.v1", "transfer_event": "state transfer: CHAR_03 from 复苏战斗态 to 斩首后妖气态 after apex; no physical handoff"}
**专项镜头模板**：template_id=fight_exchange; {"action_scope": "两主体近身一击，不扩展成群战或长追逐。", "apex_light": "7.8s 白金刀光只亮一瞬，之后迅速回冷灰，避免页游爆屏。", "attack_path": "虎爪自画右上压向画左下；横刀自画左下挑向画右上，交点锁在画面中线偏右。", "beats": ["起手蓄力", "爪刀相撞", "错身斩断", "反应/收势"], "blocking": "姜月初始终由画左低位向画右斜线推进；虎山神由画右高位向画左压下，双方轴线不跳。", "camera_path": "低角度推近→侧移跟拍→静止落点。", "camera_rule": "先给完整动作线，再给一处刀光特写，最后反应静止；不做连续乱切和旋转镜头。", "clash_frame": "刀光相交 7.8s：横刀轨迹和虎爪妖风交叉成 X 形，短促白金闪作撞点。", "combat_micro_expression": "7.8s 姜月初眼神从赌命转为狠绝；虎山神兽眼第一次露出错愕。", "contact_points": ["虎爪压近刀锋", "刀光切开妖风和颈侧妖气", "姜月初双手握刀保持同一姿势"], "continuity_must": ["横刀在姜月初手中不换手", "虎山神体型约成人2.8倍", "刀光方向从画左下到画右上", "斩首只给轮廓和尘土，避免猎奇"], "degrade_plan": "若一段内动作不稳，拆为起手/冲撞/错身/落点四张锚帧。", "force_direction": "虎妖向下压，姜月初向上斜挑，力线清楚相反。", "impact_frame": "命中 7.8s：人与妖错身，刀光切开虎山神颈侧妖气，接触点在画面中线偏右。", "keyframe_plan": ["first=蓄力或冲撞前", "anchor=命中/错身", "end=结果落定"], "negative": ["不要多出第三名参战者", "不要把虎山神画成普通老虎", "不要出现血腥断面特写", "不要让姜月初换制服或换脸"], "physics_guard": "禁止慢动作中肢体穿模；人物比例和接触方向必须与锚帧一致。", "post_cue_points": ["3.8s 冲撞前鼓点收束", "7.8s hit-stop/impact_sfx/短闪白", "10.4s 静音落点确认虎首轮廓"], "readability_beats": ["谁先动", "力量如何相撞", "刀光切过哪里", "结果是谁倒下"], "recovery_beat": "姜月初背影僵住，虎山神妖气塌落，给观众半秒确认。", "risk_flags": ["high_action", "contact_motion", "physics"], "screen_direction": "姜月初左到右，虎山神右到左；镜头不越轴。", "secondary_motion": "刀光过后枯草反向弹起，黑灰妖气被切线分开，尘土延迟半拍落下。", "spatial_path": "尸场中央枯草带作为冲撞路径，巨岩在背景画右固定。", "spectacle_story_function": "动作奇观服务“二十年赌一刀”的生死兑现，不为炫技扩写。", "speed_curve": "蓄力慢半拍，冲撞极快，错身后骤停。", "template_id": "fight_exchange"}
**模型路由**：shot_type=fight_exchange；template=fight_exchange；primary_backend=seedance；fallback_backends=dreamina；mode=frames2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=character_id_or_reference_group；quality_tier=high；risk_flags=action_choreography_required,contact_motion,feature_melting_risk,identity_drift_risk,motion_reference_candidate,native_multiframe,physical_interaction,seam_relay；degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=motion_control_required
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "none", "requires_voice_track": false, "speech_policy": "no_native_speech", "video_generation_audio_policy": "无声视频流"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": true}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第2集/control/Clip_04/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks", "contact_map", "camera_path"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "Split into setup and impact clips; keep the hit frame as the end frame.", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 3, "native_timeline_frames": 5, "reference_only": false, "requires_split_relay": false}, "mode": "frames2video", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01"], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_01", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_03", "form": ""}], "identity_preservation_plan": {"applies_to": "fight_exchange", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "character_id_or_reference_group", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": true, "library_path": "生产数据/motion_reference_library.json", "policy": "use same sequence/shot_type approved reference when available"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：required=true；manifest_path=出视频/第2集/control/Clip_04/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、接触漂移、武器归属错都判失败。
**角色身份注册层**：CHAR_01/囚犯初醒态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_03/诈死复苏态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。 → 止：虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=无声视频流，禁止模型生成台词、旁白、哼唱、系统音或环境人声，不使用音频输入。
**在场链约束**：required_presence=['CHAR_01/血尘战损态', 'CHAR_03/复苏战斗态', 'CHAR_03/斩首后妖气态', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['VFX_系统面板', '百妖谱']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=入画/现身：VFX_系统面板、百妖谱；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。
- 出点：虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。
- 转场：cut
- 连贯性：eyeline=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。; shot_size=WIDE 动作全景→LOW 静止; need_endframe=True

**continuity**：
- start_state：虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。
- action：起手蓄力；爪刀相撞；错身斩断；反应/收势
- end_state：虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01, WEAPON_01；保持 CHAR_01, CHAR_03 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。
  action: 起手蓄力；爪刀相撞；错身斩断；反应/收势
  end_state: 虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。
  constraints: 保持 LOC_01、LOC_01, WEAPON_01、CHAR_01, CHAR_03 的视觉连续；轴线=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：兑现二十年赌刀的动作高潮，用短促清晰的一刀完成反杀。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定;
落幅：落在WIDE 动作全景→LOW 静止，动作/表情在最后 0.3-0.5 秒稳定住; 
场面调度：姜月初始终由画左低位向画右斜线推进；虎山神由画右高位向画左压下，双方轴线不跳。;
表演节拍：[0s-4.826s] 虎爪压下，刀光迎上，荒草被妖风刮成同一方向。; [4.826s-9.689s] 人与妖错身而过，刀光只亮一瞬，虎妖胸颈处出现冷亮切线。; [9.689s-11.995s] 虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。;
运动精修约束：幅度小到中，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：start collision at 3.8s, cross-body apex at 7.8s, recovery/landing at 10.4s；CHAR_03 downward/right-to-left pressure opposed by CHAR_01 upward/left-to-right slash；禁止慢动作中肢体穿模；人物比例和接触方向必须与锚帧一致。；尸场中央枯草带作为冲撞路径，巨岩在背景画右固定。;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：{"body_part_ownership": {"CHAR_01": ["hands", "back", "shoulders"], "CHAR_03": ["claws", "neck_side_aura", "tiger_head", "torso"], "VFX_妖气": ["black_gray_aura", "dust"], "WEAPON_01": ["blade", "hilt"]}, "contact_points": ["WEAPON_01 blade line intersects CHAR_03 neck-side demonic aura at apex", "CHAR_03 claw passes over/near blade without grabbing it", "CHAR_01 body and tiger body cross paths but stay separate silhouettes"], "force_direction": "CHAR_03 downward/right-to-left pressure opposed by CHAR_01 upward/left-to-right slash", "holder_state": {"CHAR_03 head/body": "after apex becomes separate shadow silhouette only, non-gory", "WEAPON_01": "CHAR_01 keeps two-hand/firm grip; no drop after impact"}, "motion_vector": "start collision at 3.8s, cross-body apex at 7.8s, recovery/landing at 10.4s", "notes": "Occlusion uses dust/VFX to avoid graphic anatomy while preserving action readability.", "occlusion_order": ["dust/aura foreground masks impact", "WEAPON_01 cold light line", "CHAR_01 silhouette", "CHAR_03 giant silhouette/head outline"], "participants": ["CHAR_01", "CHAR_03", "WEAPON_01", "VFX_妖气"], "release_frame": "CHAR_03 head outline separates into dust/grass after 9.689s; avoid gore detail", "schema": "n2d.interaction_graph.v1", "transfer_event": "state transfer: CHAR_03 from 复苏战斗态 to 斩首后妖气态 after apex; no physical handoff"};
专项模板约束：template_id=fight_exchange，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=fight_exchange；template=fight_exchange；primary_backend=seedance；fallback_backends=dreamina；mode=frames2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=character_id_or_reference_group；quality_tier=high；risk_flags=action_choreography_required,contact_motion,feature_melting_risk,identity_drift_risk,motion_reference_candidate,native_multiframe,physical_interaction,seam_relay；degrade_plan=Split into setup and impact clips; keep the hit frame as the end frame.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=motion_control_required; prompt 只使用 primary_backend 真实支持的无声视频能力，失败按 degrade_plan/fallback 执行;
物理交互约束：required=true；manifest_path=出视频/第2集/control/Clip_04/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map,camera_path；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、接触漂移、武器归属错都判失败。;
身份锁定约束：CHAR_01/囚犯初醒态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_03/诈死复苏态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。 → 止：虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01/血尘战损态', 'CHAR_03/复苏战斗态', 'CHAR_03/斩首后妖气态', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['VFX_系统面板', '百妖谱']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=入画/现身：VFX_系统面板、百妖谱；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；视频生成音频策略=无声视频流；不要使用音频输入；禁止原生人声、台词、旁白、哼唱、系统音和字幕文字;
人物运动：起手蓄力；爪刀相撞；错身斩断；反应/收势；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：先给完整动作线，再给一处刀光特写，最后反应静止；不做连续乱切和旋转镜头。;
情绪节奏：[0-终点] 虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。 -> 虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 constraints，避开 negative，按cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；视频-only silent stream；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: execute only this clip beat; do not add story events;
opening frame state: 虎山神怒吼，巨爪撑开黑灰妖风，人与妖比例悬殊。;
ending frame state: 虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。;
blocking: 姜月初始终由画左低位向画右斜线推进；虎山神由画右高位向画左压下，双方轴线不跳。;
performance beats: [0s-4.826s] 虎爪压下，刀光迎上，荒草被妖风刮成同一方向。; [4.826s-9.689s] 人与妖错身而过，刀光只亮一瞬，虎妖胸颈处出现冷亮切线。; [9.689s-11.995s] 虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。;
motion refinement: low-to-medium amplitude, stable body balance, clear hand and weapon ownership, no face stretching;
close-up identity lock: use reference_group, face close-up, expression references; lock face not emotion; keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01/血尘战损态', 'CHAR_03/复苏战斗态', 'CHAR_03/斩首后妖气态', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['VFX_系统面板', '百妖谱']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=入画/现身：VFX_系统面板、百妖谱；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 起手蓄力；爪刀相撞；错身斩断；反应/收势;
camera motion: 先给完整动作线，再给一处刀光特写，最后反应静止；不做连续乱切和旋转镜头。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative;
audio constraint: silent video stream only, no generated speech, no narration, no native voice, no humming, no subtitles; do not use audio input; discard any forced backend audio later.
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=frames2video; quality_tier=high; duration=11.995s; aspect=9:16; native_audio_policy=none; video_generation_audio_policy=无声视频流; identity adapter=character_id_or_reference_group; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 3, "native_timeline_frames": 5, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全，FeatureMelting/特征融化判失败
5. ✅ ②镜头运动：推/拉/摇/移/固定/跟拍等结构化词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气/火把随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：已登记角色ID/形态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; speech_policy=no_native_speech; compose_policy=丢弃; 无声视频流; 不使用音频输入
14. ✅ Motion Control：按本镜 route/control manifest 或 degrade_plan 执行

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜

## Clip 05（时长 9.451s · EP02_CLIP05 · 一百年到账与收录选择）　**节奏**：系统爽点
**剧本可看性合同**：clip_id=EP02_CLIP05；dramatic_function=从“活下来”马上转到“代价和选择”，把爽点推向系统玩法。；audience_effect=观众追问一百年道行会带来什么，以及收录会不会亏。；spectacle_story_function=把系统规则和收益用可读 overlay 交接给 compose，使成长爽点清楚可签收。。
**表演签名**：CHAR_01/囚犯初醒态: freeform=先缩肩屏息、迅速扫视逃路；紧张时嘴上吐槽，真做决定时声音压低。；CHAR_03/诈死复苏态: freeform=咧嘴笑、舔掌、慢慢扭颈，喜欢先说话再动手。

**首帧**：`出图/第2集/图片/Clip05_first.png`
**锚帧1**（4.726s · keyframe · 三帧契约：锁住人物状态、系统面板或情绪转折的中段锚。）：`出图/第2集/图片/Clip05_mid.png`
**尾帧**：`出图/第2集/图片/Clip05_end.png`
**场景**：LOC_01 荒野尸骸战场/冷灰夜/外; location_id=LOC_01; 资产：LOC_01, WEAPON_01
**导演意图**：从“活下来”马上转到“代价和选择”，把爽点推向系统玩法。
**起幅**：继承首帧构图、光位、轴线、角色状态和物料位置，不重定视觉设定。
**落幅**：落在MCU 脱力→CU 唇形/手指，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 compose overlay 渲染。
**表演节拍**：[0s-2.931s] 姜月初跪倒，刀尖撑地，背后虎山神庞大身体化作黑雾塌落。; [2.931s-5.834s] 百妖谱再亮，古卷边缘被虎形黑影撞出波纹，文字后期叠加。; [5.834s-8.551s] 金色古卷半开，虎山神残影在卷外挣扎，留出“是否收录”空面板。; [8.551s-9.451s] 姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。
**运动精修**：幅度=小/中；能量=系统爽点；身体守卫=重心、手部/武器归属、遮挡层级、脸部轮廓和发髻稳定；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：kneel/downbeat -> panel pulse -> fingertip press -> verbal accept；CHAR_01 downward collapse to ground; 百妖谱 pulls tiger remnant inward
**动作编排契约 / Action Choreography**：{"beats": ["跪落撑刀", "百妖谱面板脉冲", "虎山神摹影被卷入古卷", "染血手指按下确认收录"], "body_part_ownership": {"CHAR_01": ["knees", "right_hand", "left_hand", "lips"], "CHAR_03": ["shadow_remnant"], "VFX_系统面板/百妖谱": ["scroll_surface", "gold_edge"], "WEAPON_01": ["hilt", "tip"]}, "camera_path": "先给姜月初脱力反应，再切百妖谱/摹影平面，最后切手指按下的近景；不做自由乱甩。", "contact_points": ["CHAR_01 knee/feet contact ground as she kneels", "WEAPON_01 tip braces against ground beside CHAR_01, not through body", "CHAR_01 bloodied fingertip presses/selects 百妖谱 light surface", "CHAR_03 remnant contacts only VFX scroll boundary"], "degrade_plan": "若角色、面板、摹影同镜不稳，拆为姜月初反应、百妖谱/摹影VFX、手指按下三个短镜；文字只走 compose overlay。", "distance_curve": "角色与百妖谱保持半臂以上距离；摹影从远/卷外逐步贴近卷面，最后被卷入，不与姜月初身体接触。", "force_direction": "CHAR_01 downward collapse to ground; 百妖谱 pulls tiger remnant inward", "holder_state": {"VFX_虎山神摹影": "attached to scroll VFX, no physical body", "WEAPON_01": "held/braced by CHAR_01 or leaning within reach; not abandoned"}, "keyframe_plan": [{"at_sec": 0.5, "frame": "Clip05_first", "purpose": "跪倒撑刀与战场低位"}, {"at_sec": 4.7, "frame": "Clip05_mid", "purpose": "百妖谱面板与摹影拉扯"}, {"at_sec": 8.9, "frame": "Clip05_end", "purpose": "手指按下确认收录"}], "light_shadow_lock": "主画面冷灰月夜不跳光；百妖谱只给局部金色边光和手指高光，不把整场改成暖光。", "motion_vector": "kneel/downbeat -> panel pulse -> fingertip press -> verbal accept", "notes": "System panel is a VFX surface; text remains compose overlay.", "occlusion_layers": ["CHAR_01手指/刀柄前景", "百妖谱金色光面中景", "虎山神摹影卷外/卷内后层", "冷灰尸场背景"], "occlusion_order": ["CHAR_01 hand/finger foreground when selecting", "百妖谱 light plane midground", "CHAR_03 shadow remnant behind/inside scroll edge", "fallen tiger body/black mist background"], "parallax_layers": ["前景手指/横刀微动", "中景百妖谱光面固定", "后层虎山神摹影向卷内滑动", "背景尸场雾气小幅横移"], "participants": ["CHAR_01", "CHAR_03", "WEAPON_01", "VFX_系统面板/百妖谱", "VFX_虎山神摹影"], "physics_guard": "百妖谱是VFX平面，文字由compose overlay渲染；手指只接触光面，不穿进卷轴；虎山神摹影只进入卷面，不生成新实体或额外肢体。", "post_cue_points": [{"at_sec": 2.9, "cue": "面板金光第一次脉冲"}, {"at_sec": 5.8, "cue": "虎山神摹影触碰卷面边缘"}, {"at_sec": 8.6, "cue": "手指按下前半拍停顿"}], "readability_beats": ["先读姜月初跪倒撑刀", "再读百妖谱弹出留白", "再读虎山神摹影被卷入", "最后读染血手指确认收录"], "release_frame": "WEAPON_01 remains within reach; no loss of weapon continuity", "reveal_or_hide_beat": "只揭示收录选择和虎山神摹影被卷入，不烤入可读面板文字，不揭示后续技能细节。", "schema": "n2d.interaction_graph.v1", "screen_direction": "姜月初低位偏前，百妖谱位于她视线前方，摹影由后景/卷外向卷内收束；轴线不翻转。", "spatial_path": "姜月初在战场中心低位跪落；百妖谱悬在她视线前方半臂外；虎山神摹影从后景/卷外向古卷平面内收束，不穿过人体。", "speed_curve": "跪倒慢半拍，面板金光逐步增强，摹影拉扯加快，手指按下时短促停顿。", "transfer_event": "VFX transfer: tiger remnant begins moving from battlefield aura into 百妖谱 scroll"}
**专项镜头模板**：template_id=system_panel; {"beats": ["触发/弹出", "数值或选择展示", "角色反应"], "blocking": "百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 compose overlay 渲染。", "camera_rule": "先角色反应再切面板，面板留干净负空间，不让视频模型生成可读文字。", "continuity_must": ["百妖谱金色古卷样式统一", "面板文字只走 screen_text_lines overlay", "姜月初脸和战损状态连续"], "growth_ref": "screen_text_lines[2] + motif_registry progression；具体文字由 compose overlay 渲染", "motif_id": "MOTIF_百妖谱系统面板", "negative": ["不要烤字进视频画面", "不要随机生成乱码汉字", "不要把百妖谱变成现代手机UI", "不要加入新系统人格"], "panel_tier": "gold_scroll_bestiary", "story_function": "把系统规则和收益用可读 overlay 交接给 compose，使成长爽点清楚可签收。", "template_id": "system_panel", "text_layer": "compose_overlay_only", "vfx_asset": "VFX_系统面板/百妖谱"}
**模型路由**：shot_type=stealth_stalk；template=system_panel；primary_backend=seedance；fallback_backends=dreamina；mode=image2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=face_lock_or_reference_group；quality_tier=high；risk_flags=action_choreography_required,high_speed_motion,identity_drift_risk,motion_reference_candidate,mouth_visible,native_multiframe,pose_drift_risk,seam_relay,spatial_path_risk；degrade_plan=Cut to front/back reaction shots or split into approach, pass-by, and exit clips.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=motion_control_required
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "none", "requires_voice_track": false, "speech_policy": "no_native_speech", "video_generation_audio_policy": "无声视频流"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": true}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第2集/control/Clip_05/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "camera_path", "spatial_path", "parallax_layers"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "Cut to front/back reaction shots or split into approach, pass-by, and exit clips.", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "image2video", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01", "WEAPON_01"], "characters": [{"binding": "face_lock_or_reference_group", "character_id": "CHAR_01", "form": ""}, {"binding": "face_lock_or_reference_group", "character_id": "CHAR_03", "form": ""}], "identity_preservation_plan": {"applies_to": "stealth_stalk", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "face_lock_or_reference_group", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": true, "library_path": "生产数据/motion_reference_library.json", "policy": "use same sequence/shot_type approved reference when available"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：required=true；manifest_path=出视频/第2集/control/Clip_05/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,camera_path,spatial_path,parallax_layers；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、接触漂移、武器归属错都判失败。
**角色身份注册层**：CHAR_01/囚犯初醒态；identity_requirement=face_lock_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_03/诈死复苏态；identity_requirement=face_lock_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。 → 止：姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=medium_no_native_speech; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=无声视频流，禁止模型生成台词、旁白、哼唱、系统音或环境人声，不使用音频输入。
**在场链约束**：required_presence=['CHAR_01/脱力态', 'CHAR_03/溃散态', 'CHAR_03/摹影挣扎态', 'WEAPON_01 横刀', 'VFX_系统面板/百妖谱', 'VFX_系统面板', '百妖谱', 'LOC_01']；offscreen_presence=['VFX_虎山神摹影', '道行计数overlay']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=入画/现身：VFX_系统面板、百妖谱；出画/画外保留：WEAPON_01 横刀；入画/现身：VFX_虎山神摹影、道行计数overlay；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。
- 出点：姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。
- 转场：cut
- 连贯性：eyeline=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。; shot_size=MCU 脱力→CU 唇形/手指; need_endframe=True

**continuity**：
- start_state：虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。
- action：触发/弹出；数值或选择展示；角色反应
- end_state：姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01, WEAPON_01；保持 CHAR_01, CHAR_03 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。
  action: 触发/弹出；数值或选择展示；角色反应
  end_state: 姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。
  constraints: 保持 LOC_01、LOC_01, WEAPON_01、CHAR_01, CHAR_03 的视觉连续；轴线=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：从“活下来”马上转到“代价和选择”，把爽点推向系统玩法。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定;
落幅：落在MCU 脱力→CU 唇形/手指，动作/表情在最后 0.3-0.5 秒稳定住; 
场面调度：百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 compose overlay 渲染。;
表演节拍：[0s-2.931s] 姜月初跪倒，刀尖撑地，背后虎山神庞大身体化作黑雾塌落。; [2.931s-5.834s] 百妖谱再亮，古卷边缘被虎形黑影撞出波纹，文字后期叠加。; [5.834s-8.551s] 金色古卷半开，虎山神残影在卷外挣扎，留出“是否收录”空面板。; [8.551s-9.451s] 姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。;
运动精修约束：幅度小到中，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：kneel/downbeat -> panel pulse -> fingertip press -> verbal accept；CHAR_01 downward collapse to ground; 百妖谱 pulls tiger remnant inward;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：{"body_part_ownership": {"CHAR_01": ["knees", "right_hand", "left_hand", "lips"], "CHAR_03": ["shadow_remnant"], "VFX_系统面板/百妖谱": ["scroll_surface", "gold_edge"], "WEAPON_01": ["hilt", "tip"]}, "contact_points": ["CHAR_01 knee/feet contact ground as she kneels", "WEAPON_01 tip braces against ground beside CHAR_01, not through body", "CHAR_01 bloodied fingertip presses/selects 百妖谱 light surface", "CHAR_03 remnant contacts only VFX scroll boundary"], "force_direction": "CHAR_01 downward collapse to ground; 百妖谱 pulls tiger remnant inward", "holder_state": {"VFX_虎山神摹影": "attached to scroll VFX, no physical body", "WEAPON_01": "held/braced by CHAR_01 or leaning within reach; not abandoned"}, "motion_vector": "kneel/downbeat -> panel pulse -> fingertip press -> verbal accept", "notes": "System panel is a VFX surface; text remains compose overlay.", "occlusion_order": ["CHAR_01 hand/finger foreground when selecting", "百妖谱 light plane midground", "CHAR_03 shadow remnant behind/inside scroll edge", "fallen tiger body/black mist background"], "participants": ["CHAR_01", "CHAR_03", "WEAPON_01", "VFX_系统面板/百妖谱", "VFX_虎山神摹影"], "release_frame": "WEAPON_01 remains within reach; no loss of weapon continuity", "schema": "n2d.interaction_graph.v1", "transfer_event": "VFX transfer: tiger remnant begins moving from battlefield aura into 百妖谱 scroll"};
专项模板约束：template_id=system_panel，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=stealth_stalk；template=system_panel；primary_backend=seedance；fallback_backends=dreamina；mode=image2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=face_lock_or_reference_group；quality_tier=high；risk_flags=action_choreography_required,high_speed_motion,identity_drift_risk,motion_reference_candidate,mouth_visible,native_multiframe,pose_drift_risk,seam_relay,spatial_path_risk；degrade_plan=Cut to front/back reaction shots or split into approach, pass-by, and exit clips.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=motion_control_required; prompt 只使用 primary_backend 真实支持的无声视频能力，失败按 degrade_plan/fallback 执行;
物理交互约束：required=true；manifest_path=出视频/第2集/control/Clip_05/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,camera_path,spatial_path,parallax_layers；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、接触漂移、武器归属错都判失败。;
身份锁定约束：CHAR_01/囚犯初醒态；identity_requirement=face_lock_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_03/诈死复苏态；identity_requirement=face_lock_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。 → 止：姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01/脱力态', 'CHAR_03/溃散态', 'CHAR_03/摹影挣扎态', 'WEAPON_01 横刀', 'VFX_系统面板/百妖谱', 'VFX_系统面板', '百妖谱', 'LOC_01']；offscreen_presence=['VFX_虎山神摹影', '道行计数overlay']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=入画/现身：VFX_系统面板、百妖谱；出画/画外保留：WEAPON_01 横刀；入画/现身：VFX_虎山神摹影、道行计数overlay；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=medium_no_native_speech; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃；视频生成音频策略=无声视频流；不要使用音频输入；禁止原生人声、台词、旁白、哼唱、系统音和字幕文字;
人物运动：触发/弹出；数值或选择展示；角色反应；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：先角色反应再切面板，面板留干净负空间，不让视频模型生成可读文字。;
情绪节奏：[0-终点] 虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。 -> 姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 constraints，避开 negative，按cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；视频-only silent stream；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: execute only this clip beat; do not add story events;
opening frame state: 虎首从暗影里滚落到枯草边，黑灰妖气散开，姜月初背影僵立。;
ending frame state: 姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。;
blocking: 百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 compose overlay 渲染。;
performance beats: [0s-2.931s] 姜月初跪倒，刀尖撑地，背后虎山神庞大身体化作黑雾塌落。; [2.931s-5.834s] 百妖谱再亮，古卷边缘被虎形黑影撞出波纹，文字后期叠加。; [5.834s-8.551s] 金色古卷半开，虎山神残影在卷外挣扎，留出“是否收录”空面板。; [8.551s-9.451s] 姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。;
motion refinement: low-to-medium amplitude, stable body balance, clear hand and weapon ownership, no face stretching;
close-up identity lock: use reference_group, face close-up, expression references; lock face not emotion; keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01/脱力态', 'CHAR_03/溃散态', 'CHAR_03/摹影挣扎态', 'WEAPON_01 横刀', 'VFX_系统面板/百妖谱', 'VFX_系统面板', '百妖谱', 'LOC_01']；offscreen_presence=['VFX_虎山神摹影', '道行计数overlay']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=入画/现身：VFX_系统面板、百妖谱；出画/画外保留：WEAPON_01 横刀；入画/现身：VFX_虎山神摹影、道行计数overlay；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 触发/弹出；数值或选择展示；角色反应;
camera motion: 先角色反应再切面板，面板留干净负空间，不让视频模型生成可读文字。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative;
audio constraint: silent video stream only, no generated speech, no narration, no native voice, no humming, no subtitles; do not use audio input; discard any forced backend audio later.
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=image2video; quality_tier=high; duration=9.451s; aspect=9:16; native_audio_policy=none; video_generation_audio_policy=无声视频流; identity adapter=face_lock_or_reference_group; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全，FeatureMelting/特征融化判失败
5. ✅ ②镜头运动：推/拉/摇/移/固定/跟拍等结构化词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气/火把随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：已登记角色ID/形态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; speech_policy=no_native_speech; compose_policy=丢弃; 无声视频流; 不使用音频输入
14. ✅ Motion Control：按本镜 route/control manifest 或 degrade_plan 执行

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜

## Clip 06（时长 11.37s · EP02_CLIP06 · 古卷收虎与道行流逝）　**节奏**：系统爽点
**剧本可看性合同**：clip_id=EP02_CLIP06；dramatic_function=把收录做成可视化成本账，让力量获取有价格而不是白送。；audience_effect=观众看见一百年迅速缩水，紧张点重新建立。；spectacle_story_function=把系统规则和收益用可读 overlay 交接给 compose，使成长爽点清楚可签收。。
**表演签名**：CHAR_01/囚犯初醒态: freeform=先缩肩屏息、迅速扫视逃路；紧张时嘴上吐槽，真做决定时声音压低。；CHAR_03/诈死复苏态: freeform=咧嘴笑、舔掌、慢慢扭颈，喜欢先说话再动手。

**首帧**：`出图/第2集/图片/Clip06_first.png`
**中段锚帧**（5.685s · keyframe · 三帧契约：锁住人物状态、系统面板或情绪转折的中段锚。）：`出图/第2集/图片/Clip06_mid.png`
**尾帧**：`出图/第2集/图片/Clip06_end.png`
**场景**：LOC_01 荒野尸骸战场/冷灰夜/外; location_id=LOC_01; 资产：LOC_01
**导演意图**：把收录做成可视化成本账，让力量获取有价格而不是白送。
**起幅**：继承首帧构图、光位、轴线、角色状态和物料位置，不重定视觉设定。
**落幅**：落在WIDE 奇异仪式→INSERT 道行流逝，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 compose overlay 渲染。
**表演节拍**：[0s-5.665s] 金色古卷在尸场上空展开，虎山神残影被一笔一笔拖进画中。; [5.665s-11.37s] 姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。
**运动精修**：幅度=小/中；能量=系统爽点；身体守卫=重心、手部/武器归属、遮挡层级、脸部轮廓和发髻稳定；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：wide ritual pull-in -> insert cultivation count falling -> CHAR_01 pallor reaction；百妖谱 pull vector inward/upward; tiger remnant resists outward; CHAR_01 only reacts physically
**动作编排契约 / Action Choreography**：{"body_part_ownership": {"CHAR_01": ["forearm", "face", "eyes"], "CHAR_03": ["tiger_shadow_silhouette"], "VFX_系统面板/百妖谱": ["scroll_pages", "binding_lines"], "VFX_道行计数overlay": ["numeric_overlay"]}, "contact_points": ["gold lines bind CHAR_03 tiger-shadow silhouette to 百妖谱 scroll", "CHAR_01 arm gold纹 flickers on skin surface without becoming extra limbs", "道行计数 stays overlay layer near CHAR_01 eyeline"], "force_direction": "百妖谱 pull vector inward/upward; tiger remnant resists outward; CHAR_01 only reacts physically", "holder_state": {"VFX_虎山神摹影": "held by 百妖谱 binding lines; not held by CHAR_01 hands", "WEAPON_01": "offscreen/nearby per continuity, no new holder"}, "motion_vector": "wide ritual pull-in -> insert cultivation count falling -> CHAR_01 pallor reaction", "notes": "Defines VFX-only contact so model does not invent hand wrestling or extra bodies.", "occlusion_order": ["百妖谱 gold scroll VFX foreground/upper layer", "CHAR_03 shadow pulled into page plane", "CHAR_01 face/arm reaction layer", "battlefield background"], "participants": ["CHAR_01", "CHAR_03", "VFX_系统面板/百妖谱", "VFX_虎山神摹影", "VFX_道行计数overlay"], "release_frame": "after count settles, tiger remnant no longer free in battlefield layer", "schema": "n2d.interaction_graph.v1", "transfer_event": "CHAR_03 remnant is transferred into 百妖谱 page by VFX binding lines"}
**专项镜头模板**：template_id=system_panel; {"beats": ["触发/弹出", "数值或选择展示", "角色反应"], "blocking": "百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 compose overlay 渲染。", "camera_rule": "先角色反应再切面板，面板留干净负空间，不让视频模型生成可读文字。", "continuity_must": ["百妖谱金色古卷样式统一", "面板文字只走 screen_text_lines overlay", "姜月初脸和战损状态连续"], "growth_ref": "screen_text_lines[0] + motif_registry progression；具体文字由 compose overlay 渲染", "motif_id": "MOTIF_百妖谱系统面板", "negative": ["不要烤字进视频画面", "不要随机生成乱码汉字", "不要把百妖谱变成现代手机UI", "不要加入新系统人格"], "panel_tier": "gold_scroll_bestiary", "story_function": "把系统规则和收益用可读 overlay 交接给 compose，使成长爽点清楚可签收。", "template_id": "system_panel", "text_layer": "compose_overlay_only", "vfx_asset": "VFX_系统面板/百妖谱"}
**模型路由**：shot_type=general_motion；template=system_panel；primary_backend=dreamina；fallback_backends=seedance；mode=image2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=reference_group；quality_tier=fast；risk_flags=mouth_visible,multishot_reroute_candidate,native_multiframe,seam_relay；degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=cost_quality_tier
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "none", "requires_voice_track": false, "speech_policy": "no_native_speech", "video_generation_audio_policy": "无声视频流"}, "backend": "dreamina", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "If action or identity fails twice, reroute to the nearest specialized shot type.", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "image2video", "quality_tier": "fast", "reference_inputs": {"assets": ["LOC_01", "WEAPON_01"], "characters": [{"binding": "reference_group", "character_id": "CHAR_01", "form": ""}, {"binding": "reference_group", "character_id": "CHAR_03", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败。
**角色身份注册层**：CHAR_01/囚犯初醒态；identity_requirement=reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_03/诈死复苏态；identity_requirement=reference_group；reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。 → 止：姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。；表情幅度=中；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=medium_no_native_speech; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃; review=无声视频流，禁止模型生成台词、旁白、哼唱、系统音或环境人声，不使用音频输入。
**在场链约束**：required_presence=['CHAR_01/脱力态', 'CHAR_03/摹影挣扎态', 'VFX_虎山神摹影', 'VFX_系统面板/百妖谱', 'VFX_系统面板', '百妖谱', 'VFX_系统面板/道行计数overlay', '道行计数overlay', 'LOC_01']；offscreen_presence=['WEAPON_01 横刀']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：WEAPON_01 横刀；入画/现身：VFX_虎山神摹影、道行计数overlay；出画/画外保留：VFX_虎山神摹影、道行计数overlay；入画/现身：WEAPON_01 横刀；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。
- 出点：姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。
- 转场：cut
- 连贯性：eyeline=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。; shot_size=WIDE 奇异仪式→INSERT 道行流逝; need_endframe=True

**continuity**：
- start_state：姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。
- action：触发/弹出；数值或选择展示；角色反应
- end_state：姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01；保持 CHAR_01, CHAR_03 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。
  action: 触发/弹出；数值或选择展示；角色反应
  end_state: 姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。
  constraints: 保持 LOC_01、LOC_01、CHAR_01, CHAR_03 的视觉连续；轴线=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：把收录做成可视化成本账，让力量获取有价格而不是白送。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定;
落幅：落在WIDE 奇异仪式→INSERT 道行流逝，动作/表情在最后 0.3-0.5 秒稳定住; 
场面调度：百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 compose overlay 渲染。;
表演节拍：[0s-5.665s] 金色古卷在尸场上空展开，虎山神残影被一笔一笔拖进画中。; [5.665s-11.37s] 姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。;
运动精修约束：幅度小到中，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：wide ritual pull-in -> insert cultivation count falling -> CHAR_01 pallor reaction；百妖谱 pull vector inward/upward; tiger remnant resists outward; CHAR_01 only reacts physically;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：{"body_part_ownership": {"CHAR_01": ["forearm", "face", "eyes"], "CHAR_03": ["tiger_shadow_silhouette"], "VFX_系统面板/百妖谱": ["scroll_pages", "binding_lines"], "VFX_道行计数overlay": ["numeric_overlay"]}, "contact_points": ["gold lines bind CHAR_03 tiger-shadow silhouette to 百妖谱 scroll", "CHAR_01 arm gold纹 flickers on skin surface without becoming extra limbs", "道行计数 stays overlay layer near CHAR_01 eyeline"], "force_direction": "百妖谱 pull vector inward/upward; tiger remnant resists outward; CHAR_01 only reacts physically", "holder_state": {"VFX_虎山神摹影": "held by 百妖谱 binding lines; not held by CHAR_01 hands", "WEAPON_01": "offscreen/nearby per continuity, no new holder"}, "motion_vector": "wide ritual pull-in -> insert cultivation count falling -> CHAR_01 pallor reaction", "notes": "Defines VFX-only contact so model does not invent hand wrestling or extra bodies.", "occlusion_order": ["百妖谱 gold scroll VFX foreground/upper layer", "CHAR_03 shadow pulled into page plane", "CHAR_01 face/arm reaction layer", "battlefield background"], "participants": ["CHAR_01", "CHAR_03", "VFX_系统面板/百妖谱", "VFX_虎山神摹影", "VFX_道行计数overlay"], "release_frame": "after count settles, tiger remnant no longer free in battlefield layer", "schema": "n2d.interaction_graph.v1", "transfer_event": "CHAR_03 remnant is transferred into 百妖谱 page by VFX binding lines"};
专项模板约束：template_id=system_panel，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=general_motion；template=system_panel；primary_backend=dreamina；fallback_backends=seedance；mode=image2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=reference_group；quality_tier=fast；risk_flags=mouth_visible,multishot_reroute_candidate,native_multiframe,seam_relay；degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=cost_quality_tier; prompt 只使用 primary_backend 真实支持的无声视频能力，失败按 degrade_plan/fallback 执行;
物理交互约束：无；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败。;
身份锁定约束：CHAR_01/囚犯初醒态；identity_requirement=reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_03/诈死复苏态；identity_requirement=reference_group；reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。 → 止：姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。；表情幅度=中；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01/脱力态', 'CHAR_03/摹影挣扎态', 'VFX_虎山神摹影', 'VFX_系统面板/百妖谱', 'VFX_系统面板', '百妖谱', 'VFX_系统面板/道行计数overlay', '道行计数overlay', 'LOC_01']；offscreen_presence=['WEAPON_01 横刀']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：WEAPON_01 横刀；入画/现身：VFX_虎山神摹影、道行计数overlay；出画/画外保留：VFX_虎山神摹影、道行计数overlay；入画/现身：WEAPON_01 横刀；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=medium_no_native_speech; mouth_visible=yes; speech_policy=no_native_speech; compose_policy=丢弃；视频生成音频策略=无声视频流；不要使用音频输入；禁止原生人声、台词、旁白、哼唱、系统音和字幕文字;
人物运动：触发/弹出；数值或选择展示；角色反应；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：先角色反应再切面板，面板留干净负空间，不让视频模型生成可读文字。;
情绪节奏：[0-终点] 姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。 -> 姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 constraints，避开 negative，按cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；视频-only silent stream；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: execute only this clip beat; do not add story events;
opening frame state: 姜月初抬起染血手指按在古卷光面上，嘴唇只吐出两个字。;
ending frame state: 姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。;
blocking: 百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 compose overlay 渲染。;
performance beats: [0s-5.665s] 金色古卷在尸场上空展开，虎山神残影被一笔一笔拖进画中。; [5.665s-11.37s] 姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。;
motion refinement: low-to-medium amplitude, stable body balance, clear hand and weapon ownership, no face stretching;
close-up identity lock: use reference_group, face close-up, expression references; lock face not emotion; keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01/脱力态', 'CHAR_03/摹影挣扎态', 'VFX_虎山神摹影', 'VFX_系统面板/百妖谱', 'VFX_系统面板', '百妖谱', 'VFX_系统面板/道行计数overlay', '道行计数overlay', 'LOC_01']；offscreen_presence=['WEAPON_01 横刀']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：WEAPON_01 横刀；入画/现身：VFX_虎山神摹影、道行计数overlay；出画/画外保留：VFX_虎山神摹影、道行计数overlay；入画/现身：WEAPON_01 横刀；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 触发/弹出；数值或选择展示；角色反应;
camera motion: 先角色反应再切面板，面板留干净负空间，不让视频模型生成可读文字。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative;
audio constraint: silent video stream only, no generated speech, no narration, no native voice, no humming, no subtitles; do not use audio input; discard any forced backend audio later.
```

### 平台参数
- primary_backend=dreamina; fallback_backends=['seedance']; mode=image2video; quality_tier=fast; duration=11.37s; aspect=9:16; native_audio_policy=none; video_generation_audio_policy=无声视频流; identity adapter=reference_group; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全，FeatureMelting/特征融化判失败
5. ✅ ②镜头运动：推/拉/摇/移/固定/跟拍等结构化词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气/火把随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：已登记角色ID/形态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; speech_policy=no_native_speech; compose_policy=丢弃; 无声视频流; 不使用音频输入
14. ✅ Motion Control：按本镜 route/control manifest 或 degrade_plan 执行

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜

## Clip 07（时长 16.492s · EP02_CLIP07 · 猛虎快刀圆满与状态面板）　**节奏**：系统爽点
**剧本可看性合同**：clip_id=EP02_CLIP07；dramatic_function=兑现收录价值：技能圆满、境界落档、虎山神进入百妖谱。；audience_effect=观众获得系统成长爽点，并理解后续刷妖升级的长期玩法。；spectacle_story_function=把系统规则和收益用可读 overlay 交接给 compose，使成长爽点清楚可签收。。
**表演签名**：CHAR_01/囚犯初醒态: freeform=先缩肩屏息、迅速扫视逃路；紧张时嘴上吐槽，真做决定时声音压低。；CHAR_03/诈死复苏态: freeform=咧嘴笑、舔掌、慢慢扭颈，喜欢先说话再动手。

**首帧**：`出图/第2集/图片/Clip07_first.png`
**中段锚帧**（8.246s · keyframe · 三帧契约：锁住人物状态、系统面板或情绪转折的中段锚。）：`出图/第2集/图片/Clip07_mid.png`
**尾帧**：`出图/第2集/图片/Clip07_end.png`
**场景**：LOC_01 荒野尸骸战场/冷灰夜/外; location_id=LOC_01; 资产：LOC_01, WEAPON_01
**导演意图**：兑现收录价值：技能圆满、境界落档、虎山神进入百妖谱。
**起幅**：继承首帧构图、光位、轴线、角色状态和物料位置，不重定视觉设定。
**落幅**：落在系统面板特写→系统状态面板+人物半身，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 compose overlay 渲染。
**表演节拍**：[0s-2.287s] 古卷合拢前，虎山神摹影定格在卷页一角；文字后期叠加。; [2.287s-4.009s] 横刀刀脊浮现短暂虎纹，姜月初掌心金光回流。; [4.009s-9.559s] 力量倒灌回身体，姜月初扶刀起身，血尘囚服仍破旧，但站姿像换了一把骨头。; [9.559s-16.492s] 姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。
**运动精修**：幅度=小/中；能量=系统爽点；身体守卫=重心、手部/武器归属、遮挡层级、脸部轮廓和发髻稳定；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：panel close -> blade tiger纹 insert -> CHAR_01 stands and stabilizes；energy vector returns from panel to CHAR_01 palm/body; no external impact force
**动作编排契约 / Action Choreography**：{"body_part_ownership": {"CHAR_01": ["palm", "hands", "torso", "eyes"], "CHAR_03": ["page_silhouette_only"], "VFX_系统面板/百妖谱": ["page_corner", "status_panel"], "WEAPON_01": ["hilt", "blade_spine"]}, "contact_points": ["CHAR_03 motif freezes as ink-gold silhouette on scroll corner", "CHAR_01 palm receives gold light回流", "WEAPON_01 hilt/blade remains in CHAR_01 grip with brief tiger纹 on blade spine"], "force_direction": "energy vector returns from panel to CHAR_01 palm/body; no external impact force", "holder_state": {"CHAR_03": "held only as page motif, no physical body in scene", "WEAPON_01": "returned to stable CHAR_01 grip as she rises"}, "motion_vector": "panel close -> blade tiger纹 insert -> CHAR_01 stands and stabilizes", "notes": "Prevents tiger remnant from reappearing as a full body during reward beat.", "occlusion_order": ["gold panel/page VFX beside CHAR_01", "CHAR_01 upper body foreground", "WEAPON_01 blade/hilt crossing lower foreground", "background battlefield"], "participants": ["CHAR_01", "CHAR_03", "WEAPON_01", "VFX_系统面板/百妖谱"], "release_frame": "CHAR_03 free body absent; only registered motif remains on page", "schema": "n2d.interaction_graph.v1", "transfer_event": "skill/energy transfer from 百妖谱 registration into CHAR_01 palm and WEAPON_01 tiger纹"}
**专项镜头模板**：template_id=system_panel; {"beats": ["触发/弹出", "数值或选择展示", "角色反应"], "blocking": "百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 compose overlay 渲染。", "camera_rule": "先角色反应再切面板，面板留干净负空间，不让视频模型生成可读文字。", "continuity_must": ["百妖谱金色古卷样式统一", "面板文字只走 screen_text_lines overlay", "姜月初脸和战损状态连续"], "growth_ref": "screen_text_lines[3] + motif_registry progression；具体文字由 compose overlay 渲染", "motif_id": "MOTIF_百妖谱系统面板", "negative": ["不要烤字进视频画面", "不要随机生成乱码汉字", "不要把百妖谱变成现代手机UI", "不要加入新系统人格"], "panel_tier": "gold_scroll_bestiary", "story_function": "把系统规则和收益用可读 overlay 交接给 compose，使成长爽点清楚可签收。", "template_id": "system_panel", "text_layer": "compose_overlay_only", "vfx_asset": "VFX_系统面板/百妖谱"}
**模型路由**：shot_type=general_motion；template=system_panel；primary_backend=dreamina；fallback_backends=seedance；mode=image2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=reference_group；quality_tier=fast；risk_flags=duration_segment_relay,multishot_reroute_candidate,native_multiframe,seam_relay；degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=cost_quality_tier
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "none", "requires_voice_track": false, "speech_policy": "no_native_speech", "video_generation_audio_policy": "无声视频流"}, "backend": "dreamina", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "If action or identity fails twice, reroute to the nearest specialized shot type.", "fallback_backends": ["seedance"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "image2video", "quality_tier": "fast", "reference_inputs": {"assets": ["LOC_01", "WEAPON_01"], "characters": [{"binding": "reference_group", "character_id": "CHAR_01", "form": ""}, {"binding": "reference_group", "character_id": "CHAR_03", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime", "video_segments": {"max_clip_seconds": 15, "max_segment_seconds": 8.246, "mode": "first_last_relay", "reason": "split paid generation into first/mid/end relay segments under backend cap", "required": true, "segments": [{"duration_sec": 8.246, "end_sec": 8.246, "from_frame": "first_frame", "segment_id": "Clip_07_seg01", "start_sec": 0.0, "submit_mode": "first_last_relay", "to_frame": "mid_anchor_1"}, {"duration_sec": 8.246, "end_sec": 16.492, "from_frame": "mid_anchor_1", "segment_id": "Clip_07_seg02", "start_sec": 8.246, "submit_mode": "first_last_relay", "to_frame": "end_frame"}]}}
**Motion Control / 物理交互控制**：无；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败。
**角色身份注册层**：CHAR_01/囚犯初醒态；identity_requirement=reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_03/诈死复苏态；identity_requirement=reference_group；reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。 → 止：姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。；表情幅度=中；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=无声视频流，禁止模型生成台词、旁白、哼唱、系统音或环境人声，不使用音频输入。
**在场链约束**：required_presence=['CHAR_01/脱力态', 'CHAR_03/摹影态', 'CHAR_01/猛虎快刀圆满态', 'VFX_系统面板/百妖谱', 'VFX_系统面板', '百妖谱', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['VFX_虎山神摹影', '道行计数overlay']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：VFX_虎山神摹影、道行计数overlay；入画/现身：WEAPON_01 横刀；出画/画外保留：CHAR_03、VFX_系统面板、百妖谱；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。
- 出点：姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。
- 转场：cut
- 连贯性：eyeline=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。; shot_size=系统面板特写→系统状态面板+人物半身; need_endframe=True

**continuity**：
- start_state：姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。
- action：触发/弹出；数值或选择展示；角色反应
- end_state：姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01, WEAPON_01；保持 CHAR_01, CHAR_03 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。
  action: 触发/弹出；数值或选择展示；角色反应
  end_state: 姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。
  constraints: 保持 LOC_01、LOC_01, WEAPON_01、CHAR_01, CHAR_03 的视觉连续；轴线=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：兑现收录价值：技能圆满、境界落档、虎山神进入百妖谱。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定;
落幅：落在系统面板特写→系统状态面板+人物半身，动作/表情在最后 0.3-0.5 秒稳定住; 
场面调度：百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 compose overlay 渲染。;
表演节拍：[0s-2.287s] 古卷合拢前，虎山神摹影定格在卷页一角；文字后期叠加。; [2.287s-4.009s] 横刀刀脊浮现短暂虎纹，姜月初掌心金光回流。; [4.009s-9.559s] 力量倒灌回身体，姜月初扶刀起身，血尘囚服仍破旧，但站姿像换了一把骨头。; [9.559s-16.492s] 姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。;
运动精修约束：幅度小到中，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：panel close -> blade tiger纹 insert -> CHAR_01 stands and stabilizes；energy vector returns from panel to CHAR_01 palm/body; no external impact force;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：{"body_part_ownership": {"CHAR_01": ["palm", "hands", "torso", "eyes"], "CHAR_03": ["page_silhouette_only"], "VFX_系统面板/百妖谱": ["page_corner", "status_panel"], "WEAPON_01": ["hilt", "blade_spine"]}, "contact_points": ["CHAR_03 motif freezes as ink-gold silhouette on scroll corner", "CHAR_01 palm receives gold light回流", "WEAPON_01 hilt/blade remains in CHAR_01 grip with brief tiger纹 on blade spine"], "force_direction": "energy vector returns from panel to CHAR_01 palm/body; no external impact force", "holder_state": {"CHAR_03": "held only as page motif, no physical body in scene", "WEAPON_01": "returned to stable CHAR_01 grip as she rises"}, "motion_vector": "panel close -> blade tiger纹 insert -> CHAR_01 stands and stabilizes", "notes": "Prevents tiger remnant from reappearing as a full body during reward beat.", "occlusion_order": ["gold panel/page VFX beside CHAR_01", "CHAR_01 upper body foreground", "WEAPON_01 blade/hilt crossing lower foreground", "background battlefield"], "participants": ["CHAR_01", "CHAR_03", "WEAPON_01", "VFX_系统面板/百妖谱"], "release_frame": "CHAR_03 free body absent; only registered motif remains on page", "schema": "n2d.interaction_graph.v1", "transfer_event": "skill/energy transfer from 百妖谱 registration into CHAR_01 palm and WEAPON_01 tiger纹"};
专项模板约束：template_id=system_panel，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=general_motion；template=system_panel；primary_backend=dreamina；fallback_backends=seedance；mode=image2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=reference_group；quality_tier=fast；risk_flags=duration_segment_relay,multishot_reroute_candidate,native_multiframe,seam_relay；degrade_plan=If action or identity fails twice, reroute to the nearest specialized shot type.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=cost_quality_tier; prompt 只使用 primary_backend 真实支持的无声视频能力，失败按 degrade_plan/fallback 执行;
物理交互约束：无；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败。;
身份锁定约束：CHAR_01/囚犯初醒态；identity_requirement=reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_03/诈死复苏态；identity_requirement=reference_group；reference_group=出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=虎首人身·巨型如山·黄黑虎纹·胸口黑血窟窿·金黄凶眼;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。 → 止：姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。；表情幅度=中；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01/脱力态', 'CHAR_03/摹影态', 'CHAR_01/猛虎快刀圆满态', 'VFX_系统面板/百妖谱', 'VFX_系统面板', '百妖谱', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['VFX_虎山神摹影', '道行计数overlay']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：VFX_虎山神摹影、道行计数overlay；入画/现身：WEAPON_01 横刀；出画/画外保留：CHAR_03、VFX_系统面板、百妖谱；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；视频生成音频策略=无声视频流；不要使用音频输入；禁止原生人声、台词、旁白、哼唱、系统音和字幕文字;
人物运动：触发/弹出；数值或选择展示；角色反应；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：先角色反应再切面板，面板留干净负空间，不让视频模型生成可读文字。;
情绪节奏：[0-终点] 姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。 -> 姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 constraints，避开 negative，按cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；视频-only silent stream；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: execute only this clip beat; do not add story events;
opening frame state: 姜月初眼前的金色刻度急速回落，手臂金纹忽明忽暗，脸色越来越白。;
ending frame state: 姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。;
blocking: 百妖谱/系统面板悬在角色视线附近，人物与面板分层；文字全部由 compose overlay 渲染。;
performance beats: [0s-2.287s] 古卷合拢前，虎山神摹影定格在卷页一角；文字后期叠加。; [2.287s-4.009s] 横刀刀脊浮现短暂虎纹，姜月初掌心金光回流。; [4.009s-9.559s] 力量倒灌回身体，姜月初扶刀起身，血尘囚服仍破旧，但站姿像换了一把骨头。; [9.559s-16.492s] 姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。;
motion refinement: low-to-medium amplitude, stable body balance, clear hand and weapon ownership, no face stretching;
close-up identity lock: use reference_group, face close-up, expression references; lock face not emotion; keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01/脱力态', 'CHAR_03/摹影态', 'CHAR_01/猛虎快刀圆满态', 'VFX_系统面板/百妖谱', 'VFX_系统面板', '百妖谱', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['VFX_虎山神摹影', '道行计数overlay']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：VFX_虎山神摹影、道行计数overlay；入画/现身：WEAPON_01 横刀；出画/画外保留：CHAR_03、VFX_系统面板、百妖谱；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 触发/弹出；数值或选择展示；角色反应;
camera motion: 先角色反应再切面板，面板留干净负空间，不让视频模型生成可读文字。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative;
audio constraint: silent video stream only, no generated speech, no narration, no native voice, no humming, no subtitles; do not use audio input; discard any forced backend audio later.
```

### 平台参数
- primary_backend=dreamina; fallback_backends=['seedance']; mode=image2video; quality_tier=fast; duration=16.492s; aspect=9:16; native_audio_policy=none; video_generation_audio_policy=无声视频流; identity adapter=reference_group; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全，FeatureMelting/特征融化判失败
5. ✅ ②镜头运动：推/拉/摇/移/固定/跟拍等结构化词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气/火把随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：已登记角色ID/形态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; speech_policy=no_native_speech; compose_policy=丢弃; 无声视频流; 不使用音频输入
14. ✅ Motion Control：按本镜 route/control manifest 或 degrade_plan 执行

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜

## Clip 08（时长 8.812s · EP02_CLIP08 · 姜月初读懂长久买卖）　**节奏**：情绪/叙事推进
**剧本可看性合同**：clip_id=EP02_CLIP08；dramatic_function=让主角从被动求生进入主动计算，明确道行要留作命。；audience_effect=观众相信她开始懂系统，不是只靠运气。；spectacle_story_function=无。
**表演签名**：CHAR_01/囚犯初醒态: freeform=先缩肩屏息、迅速扫视逃路；紧张时嘴上吐槽，真做决定时声音压低。

**首帧**：`出图/第2集/图片/Clip08_first.png`
**中段锚帧**（4.406s · keyframe · 三帧契约：锁住人物状态、系统面板或情绪转折的中段锚。）：`出图/第2集/图片/Clip08_mid.png`
**尾帧**：`出图/第2集/图片/Clip08_end.png`
**场景**：LOC_01 荒野尸骸战场/冷灰夜/外; location_id=LOC_01; 资产：LOC_01, WEAPON_01
**导演意图**：让主角从被动求生进入主动计算，明确道行要留作命。
**起幅**：继承首帧构图、光位、轴线、角色状态和物料位置，不重定视觉设定。
**落幅**：落在CU 低声盘算→INSERT 横刀与掌心，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：姜月初单人占画面主体，横刀在手部/下方前景；百妖谱面板已经消散，只保留她视线落点和微弱金纹。
**表演节拍**：[0s-5.836s] 姜月初盯着空面板消散的位置，眼神从惊惧转为计算。; [5.836s-8.812s] 她把仅剩的金纹按回掌心，横刀归于暗银。
**运动精修**：幅度=小/中；能量=情绪/叙事推进；身体守卫=重心、手部/武器归属、遮挡层级、脸部轮廓和发髻稳定；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：gaze calculation -> thumb wipe -> palm press -> gold light fades；controlled inward pressure from CHAR_01 palm; no combat force
**动作编排契约 / Action Choreography**：{"body_part_ownership": {"CHAR_01": ["thumb", "palm", "eyes", "breath"], "VFX_残余金纹": ["palm_surface", "blade_glint"], "WEAPON_01": ["hilt", "blade"]}, "contact_points": ["CHAR_01 thumb wipes blood on WEAPON_01 hilt", "CHAR_01 palm presses residual gold纹 back under skin", "WEAPON_01 returns to dark silver resting state"], "force_direction": "controlled inward pressure from CHAR_01 palm; no combat force", "holder_state": {"VFX_残余金纹": "owned by CHAR_01 palm and fades inward", "WEAPON_01": "held by CHAR_01 throughout; hilt contact stays thumb/palm only"}, "motion_vector": "gaze calculation -> thumb wipe -> palm press -> gold light fades", "notes": "Clarifies this is a standing/controlled hand insert, not a buried body pose.", "occlusion_order": ["CHAR_01 thumb/palm foreground insert", "WEAPON_01 hilt/blade plane", "CHAR_01 face/eyes behind or adjacent", "battlefield background"], "participants": ["CHAR_01", "WEAPON_01", "VFX_残余金纹"], "release_frame": "gold纹 disappears into CHAR_01 palm by end; weapon not dropped", "schema": "n2d.interaction_graph.v1", "transfer_event": "none"}
**专项镜头模板**：template_id=reveal_reaction_chain; {"beats": ["空面板消散", "眼神由惊惧转计算", "擦净刀柄血", "金纹按回掌心"], "blocking": "姜月初单人占画面主体，横刀在手部/下方前景；百妖谱面板已经消散，只保留她视线落点和微弱金纹。", "camera_rule": "先给低声盘算 CU，再切横刀与掌心 INSERT；保持身体完整地站/半身在地面上，不做埋入地面构图。", "continuity_must": ["姜月初仍为猛虎快刀圆满态", "WEAPON_01 横刀由她持有", "金纹只在掌心/刀脊残留并向内收束", "百妖谱文字不烤进画面"], "cut_point": "金纹完全压回掌心、横刀归暗银后切向悼别镜。", "knowledge_order": ["观众先看到面板已消散", "再读到姜月初仍在计算代价", "最后看到她主动压住外泄金纹"], "negative": ["不要新增敌人", "不要让虎山神复活", "不要把金纹扩成大爆炸", "不要把人物下半身埋入地面", "不要生成乱码文字"], "reaction_beats": ["惊惧余波", "眼神收束成计算", "呼吸稳定", "把力量藏回掌心"], "reveal_object": "百妖谱空面板消散后的缺席位置 + 掌心残余金纹", "template_id": "reveal_reaction_chain"}
**模型路由**：shot_type=reveal_reaction_chain；template=reveal_reaction_chain；primary_backend=seedance；fallback_backends=dreamina；mode=image2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=character_id_or_reference_group；quality_tier=high；risk_flags=identity_drift_risk,native_multiframe,seam_relay；degrade_plan=Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=cost_quality_tier
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "none", "requires_voice_track": false, "speech_policy": "no_native_speech", "video_generation_audio_policy": "无声视频流"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "not_required", "manifest_path": "", "required": false, "required_inputs": []}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "image2video", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01", "WEAPON_01"], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_01", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_03", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_02", "form": ""}], "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：无；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败。
**角色身份注册层**：CHAR_01/囚犯初醒态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。 → 止：她把仅剩的金纹按回掌心，横刀归于暗银。；表情幅度=中；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=无声视频流，禁止模型生成台词、旁白、哼唱、系统音或环境人声，不使用音频输入。
**在场链约束**：required_presence=['CHAR_01/猛虎快刀圆满态', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['CHAR_03', 'VFX_系统面板', '百妖谱', 'CHAR_02']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：CHAR_03、VFX_系统面板、百妖谱；入画/现身：CHAR_02；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。
- 出点：她把仅剩的金纹按回掌心，横刀归于暗银。
- 转场：cut
- 连贯性：eyeline=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。; shot_size=CU 低声盘算→INSERT 横刀与掌心; need_endframe=True

**continuity**：
- start_state：姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。
- action：空面板消散；眼神由惊惧转计算；擦净刀柄血；金纹按回掌心
- end_state：她把仅剩的金纹按回掌心，横刀归于暗银。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01, WEAPON_01；保持 CHAR_01 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。
  action: 空面板消散；眼神由惊惧转计算；擦净刀柄血；金纹按回掌心
  end_state: 她把仅剩的金纹按回掌心，横刀归于暗银。
  constraints: 保持 LOC_01、LOC_01, WEAPON_01、CHAR_01 的视觉连续；轴线=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：让主角从被动求生进入主动计算，明确道行要留作命。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定;
落幅：落在CU 低声盘算→INSERT 横刀与掌心，动作/表情在最后 0.3-0.5 秒稳定住; 
场面调度：姜月初单人占画面主体，横刀在手部/下方前景；百妖谱面板已经消散，只保留她视线落点和微弱金纹。;
表演节拍：[0s-5.836s] 姜月初盯着空面板消散的位置，眼神从惊惧转为计算。; [5.836s-8.812s] 她把仅剩的金纹按回掌心，横刀归于暗银。;
运动精修约束：幅度小到中，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：gaze calculation -> thumb wipe -> palm press -> gold light fades；controlled inward pressure from CHAR_01 palm; no combat force;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：{"body_part_ownership": {"CHAR_01": ["thumb", "palm", "eyes", "breath"], "VFX_残余金纹": ["palm_surface", "blade_glint"], "WEAPON_01": ["hilt", "blade"]}, "contact_points": ["CHAR_01 thumb wipes blood on WEAPON_01 hilt", "CHAR_01 palm presses residual gold纹 back under skin", "WEAPON_01 returns to dark silver resting state"], "force_direction": "controlled inward pressure from CHAR_01 palm; no combat force", "holder_state": {"VFX_残余金纹": "owned by CHAR_01 palm and fades inward", "WEAPON_01": "held by CHAR_01 throughout; hilt contact stays thumb/palm only"}, "motion_vector": "gaze calculation -> thumb wipe -> palm press -> gold light fades", "notes": "Clarifies this is a standing/controlled hand insert, not a buried body pose.", "occlusion_order": ["CHAR_01 thumb/palm foreground insert", "WEAPON_01 hilt/blade plane", "CHAR_01 face/eyes behind or adjacent", "battlefield background"], "participants": ["CHAR_01", "WEAPON_01", "VFX_残余金纹"], "release_frame": "gold纹 disappears into CHAR_01 palm by end; weapon not dropped", "schema": "n2d.interaction_graph.v1", "transfer_event": "none"};
专项模板约束：template_id=reveal_reaction_chain，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=reveal_reaction_chain；template=reveal_reaction_chain；primary_backend=seedance；fallback_backends=dreamina；mode=image2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=character_id_or_reference_group；quality_tier=high；risk_flags=identity_drift_risk,native_multiframe,seam_relay；degrade_plan=Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=cost_quality_tier; prompt 只使用 primary_backend 真实支持的无声视频能力，失败按 degrade_plan/fallback 执行;
物理交互约束：无；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、武器接触漂移都判失败。;
身份锁定约束：CHAR_01/囚犯初醒态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。 → 止：她把仅剩的金纹按回掌心，横刀归于暗银。；表情幅度=中；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01/猛虎快刀圆满态', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['CHAR_03', 'VFX_系统面板', '百妖谱', 'CHAR_02']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：CHAR_03、VFX_系统面板、百妖谱；入画/现身：CHAR_02；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；视频生成音频策略=无声视频流；不要使用音频输入；禁止原生人声、台词、旁白、哼唱、系统音和字幕文字;
人物运动：空面板消散；眼神由惊惧转计算；擦净刀柄血；金纹按回掌心；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：先给低声盘算 CU，再切横刀与掌心 INSERT；保持身体完整地站/半身在地面上，不做埋入地面构图。;
情绪节奏：[0-终点] 姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。 -> 她把仅剩的金纹按回掌心，横刀归于暗银。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 constraints，避开 negative，按cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；视频-only silent stream；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: execute only this clip beat; do not add story events;
opening frame state: 姜月初半身侧对镜头，百妖谱面板悬在她身侧，面板文字全部后期叠加。;
ending frame state: 她把仅剩的金纹按回掌心，横刀归于暗银。;
blocking: 姜月初单人占画面主体，横刀在手部/下方前景；百妖谱面板已经消散，只保留她视线落点和微弱金纹。;
performance beats: [0s-5.836s] 姜月初盯着空面板消散的位置，眼神从惊惧转为计算。; [5.836s-8.812s] 她把仅剩的金纹按回掌心，横刀归于暗银。;
motion refinement: low-to-medium amplitude, stable body balance, clear hand and weapon ownership, no face stretching;
close-up identity lock: use reference_group, face close-up, expression references; lock face not emotion; keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01/猛虎快刀圆满态', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['CHAR_03', 'VFX_系统面板', '百妖谱', 'CHAR_02']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：CHAR_03、VFX_系统面板、百妖谱；入画/现身：CHAR_02；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 空面板消散；眼神由惊惧转计算；擦净刀柄血；金纹按回掌心;
camera motion: 先给低声盘算 CU，再切横刀与掌心 INSERT；保持身体完整地站/半身在地面上，不做埋入地面构图。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative;
audio constraint: silent video stream only, no generated speech, no narration, no native voice, no humming, no subtitles; do not use audio input; discard any forced backend audio later.
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=image2video; quality_tier=high; duration=8.812s; aspect=9:16; native_audio_policy=none; video_generation_audio_policy=无声视频流; identity adapter=character_id_or_reference_group; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全，FeatureMelting/特征融化判失败
5. ✅ ②镜头运动：推/拉/摇/移/固定/跟拍等结构化词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气/火把随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：已登记角色ID/形态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; speech_policy=no_native_speech; compose_policy=丢弃; 无声视频流; 不使用音频输入
14. ✅ Motion Control：按本镜 route/control manifest 或 degrade_plan 执行

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜

## Clip 09（时长 13.207s · EP02_CLIP09 · 替裴合眼与欠命账）　**节奏**：情绪/叙事推进
**剧本可看性合同**：clip_id=EP02_CLIP09；dramatic_function=把杀裴的残酷账留在人物心里，避免纯爽无代价。；audience_effect=观众感到她仍有底线，同时好奇“还你一命”是否会成后续伏笔。；spectacle_story_function=接触动作只服务欠命账和人物代价，禁止转成亲密戏。。
**表演签名**：CHAR_01/囚犯初醒态: freeform=先缩肩屏息、迅速扫视逃路；紧张时嘴上吐槽，真做决定时声音压低。；CHAR_02/濒死战损态: freeform=抬眼压人，字少；用断刀或眼神先控场。

**首帧**：`出图/第2集/图片/Clip09_first.png`
**锚帧1**（3.2s · keyframe · 起手：姜月初走回裴长青遗体旁蹲下，距离和人物状态清楚。）：`出图/第2集/图片/Clip09_a1.png`
**锚帧2**（6.4s · keyframe · 接触点：手掌只合上双眼，裴长青无回应，非亲密边界明确。）：`出图/第2集/图片/Clip09_a2.png`
**锚帧3**（10.0s · keyframe · 反应收势：姜月初低声记账后握紧横刀，准备应对下一危机。）：`出图/第2集/图片/Clip09_a3.png`
**尾帧**：`出图/第2集/图片/Clip09_end.png`
**场景**：LOC_01 荒野尸骸战场/冷灰夜/外; location_id=LOC_01; 资产：LOC_01, WEAPON_01
**导演意图**：把杀裴的残酷账留在人物心里，避免纯爽无代价。
**起幅**：继承首帧构图、光位、轴线、角色状态和物料位置，不重定视觉设定。
**落幅**：落在MS 俯拍→CU 侧脸，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：姜月初蹲在裴长青遗体侧面，手掌只接触眼睑/额前区域；裴长青保持死亡态，不产生回应。
**表演节拍**：[0s-5.198s] 姜月初走回裴长青身边，尸场恢复冷灰，她蹲下替他合眼。; [5.198s-13.207s] 姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。
**运动精修**：幅度=小/中；能量=情绪/叙事推进；身体守卫=重心、手部/武器归属、遮挡层级、脸部轮廓和发髻稳定；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：walk back -> crouch/kneel beside body -> close eyelids -> withdraw hand and tighten sword grip；gentle downward/covering motion only; no forceful impact, no embrace
**动作编排契约 / Action Choreography**：{"body_part_ownership": {"CHAR_01": ["right_hand", "left_hand", "side_face", "knees"], "CHAR_02": ["closed_eyes", "forehead", "corpse_body"], "WEAPON_01": ["hilt", "blade"]}, "contact_points": ["CHAR_01 hand briefly covers CHAR_02 eyelids/forehead to close eyes", "CHAR_01 other hand holds or stays near WEAPON_01 at safe distance", "CHAR_02 remains still death state with no reciprocal touch"], "force_direction": "gentle downward/covering motion only; no forceful impact, no embrace", "holder_state": {"CHAR_02": "no holder state; corpse remains passive", "WEAPON_01": "within CHAR_01 reach/hand, never held by CHAR_02"}, "motion_vector": "walk back -> crouch/kneel beside body -> close eyelids -> withdraw hand and tighten sword grip", "notes": "Non-intimate mourning contact; blocks hug/kiss/body overlap misread.", "occlusion_order": ["CHAR_01 hand foreground briefly occludes CHAR_02 eyes", "CHAR_02 face/body midground passive", "CHAR_01 side face above/aside with half-arm distance", "WEAPON_01 lower/side frame"], "participants": ["CHAR_01", "CHAR_02", "WEAPON_01"], "release_frame": "CHAR_01 hand withdraws after eyelids close; CHAR_02 remains still", "schema": "n2d.interaction_graph.v1", "transfer_event": "none; no handoff and no revival response"}
**专项镜头模板**：template_id=intimate_interaction; {"beats": ["走回遗体", "伸手合眼", "低声记账", "握刀起身"], "blocking": "姜月初蹲在裴长青遗体侧面，手掌只接触眼睑/额前区域；裴长青保持死亡态，不产生回应。", "body_overlap_limit": "无拥抱、无贴脸、无身体覆盖；只允许手部短接触", "body_part_ownership": "姜月初=手掌/侧脸/握刀手；裴长青=闭眼遗体", "camera_rule": "中景交代距离，特写只给手掌合眼和姜月初侧脸；避免身体贴靠或暧昧角度。", "consent_boundary": "非亲密悼别/照护动作；接触目的明确，禁止暧昧化", "contact_points": ["手掌轻合眼睑/额前区域", "另一手握刀或撑地保持距离"], "continuity_must": ["裴长青保持死亡遗体状态", "姜月初仍穿破旧囚服和血尘战损", "横刀留在她可够到的位置", "接触目的明确为合眼悼别"], "degrade_plan": "若接触动作误判为暧昧，降级为手部特写 + 姜月初单人侧脸反应", "distance_boundary": "保持半臂以上距离，只拍合眼与侧脸反应", "negative": ["不要生成拥抱、亲吻、暧昧贴脸", "不要让裴长青睁眼复活", "不要出现浪漫光效", "不要增加新对白"], "occlusion_order": "姜月初手掌短暂遮住裴长青眼部；裴长青遗体不主动回应", "readability_beats": ["走回遗体", "伸手合眼", "低声记账", "握刀起身"], "relationship_state": "欠命账与悼别，不是爱情亲密", "story_function": "用非亲密的悼别接触承接杀裴代价，让人物仍有欠账和底线。", "template_id": "intimate_interaction"}
**模型路由**：shot_type=intimate_interaction；template=intimate_interaction；primary_backend=seedance；fallback_backends=dreamina；mode=frames2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=character_id_or_reference_group；quality_tier=high；risk_flags=contact_motion,feature_melting_risk,identity_drift_risk,native_multiframe,physical_interaction,seam_relay；degrade_plan=Replace full contact with reaction close-up, hand insert, or shot/reverse-shot.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=motion_control_required
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "none", "requires_voice_track": false, "speech_policy": "no_native_speech", "video_generation_audio_policy": "无声视频流"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": false}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第2集/control/Clip_09/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "Replace full contact with reaction close-up, hand insert, or shot/reverse-shot.", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 3, "native_timeline_frames": 5, "reference_only": false, "requires_split_relay": false}, "mode": "frames2video", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01", "WEAPON_01"], "characters": [{"binding": "character_id_or_reference_group", "character_id": "CHAR_01", "form": ""}, {"binding": "character_id_or_reference_group", "character_id": "CHAR_02", "form": ""}], "identity_preservation_plan": {"applies_to": "intimate_interaction", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "character_id_or_reference_group", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": false, "library_path": "生产数据/motion_reference_library.json", "policy": "not_supported_or_not_needed"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：required=true；manifest_path=出视频/第2集/control/Clip_09/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、接触漂移、武器归属错都判失败。
**角色身份注册层**：CHAR_01/囚犯初醒态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：她把仅剩的金纹按回掌心，横刀归于暗银。 → 止：姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=无声视频流，禁止模型生成台词、旁白、哼唱、系统音或环境人声，不使用音频输入。
**在场链约束**：required_presence=['CHAR_01/克制哀悼态', 'CHAR_02/遗体态', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['AMBIENT_官道马蹄火把']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=入画/现身：CHAR_02；出画/画外保留：CHAR_02/死亡态-遗体画外保留不复活、WEAPON_01 横刀；入画/现身：AMBIENT_官道马蹄火把；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：她把仅剩的金纹按回掌心，横刀归于暗银。
- 出点：姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。
- 转场：cut
- 连贯性：eyeline=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。; shot_size=MS 俯拍→CU 侧脸; need_endframe=True

**continuity**：
- start_state：她把仅剩的金纹按回掌心，横刀归于暗银。
- action：走回遗体；伸手合眼；低声记账；握刀起身
- end_state：姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01, WEAPON_01；保持 CHAR_01, CHAR_02 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 她把仅剩的金纹按回掌心，横刀归于暗银。
  action: 走回遗体；伸手合眼；低声记账；握刀起身
  end_state: 姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。
  constraints: 保持 LOC_01、LOC_01, WEAPON_01、CHAR_01, CHAR_02 的视觉连续；轴线=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：把杀裴的残酷账留在人物心里，避免纯爽无代价。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定;
落幅：落在MS 俯拍→CU 侧脸，动作/表情在最后 0.3-0.5 秒稳定住; 
场面调度：姜月初蹲在裴长青遗体侧面，手掌只接触眼睑/额前区域；裴长青保持死亡态，不产生回应。;
表演节拍：[0s-5.198s] 姜月初走回裴长青身边，尸场恢复冷灰，她蹲下替他合眼。; [5.198s-13.207s] 姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。;
运动精修约束：幅度小到中，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：walk back -> crouch/kneel beside body -> close eyelids -> withdraw hand and tighten sword grip；gentle downward/covering motion only; no forceful impact, no embrace;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：{"body_part_ownership": {"CHAR_01": ["right_hand", "left_hand", "side_face", "knees"], "CHAR_02": ["closed_eyes", "forehead", "corpse_body"], "WEAPON_01": ["hilt", "blade"]}, "contact_points": ["CHAR_01 hand briefly covers CHAR_02 eyelids/forehead to close eyes", "CHAR_01 other hand holds or stays near WEAPON_01 at safe distance", "CHAR_02 remains still death state with no reciprocal touch"], "force_direction": "gentle downward/covering motion only; no forceful impact, no embrace", "holder_state": {"CHAR_02": "no holder state; corpse remains passive", "WEAPON_01": "within CHAR_01 reach/hand, never held by CHAR_02"}, "motion_vector": "walk back -> crouch/kneel beside body -> close eyelids -> withdraw hand and tighten sword grip", "notes": "Non-intimate mourning contact; blocks hug/kiss/body overlap misread.", "occlusion_order": ["CHAR_01 hand foreground briefly occludes CHAR_02 eyes", "CHAR_02 face/body midground passive", "CHAR_01 side face above/aside with half-arm distance", "WEAPON_01 lower/side frame"], "participants": ["CHAR_01", "CHAR_02", "WEAPON_01"], "release_frame": "CHAR_01 hand withdraws after eyelids close; CHAR_02 remains still", "schema": "n2d.interaction_graph.v1", "transfer_event": "none; no handoff and no revival response"};
专项模板约束：template_id=intimate_interaction，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=intimate_interaction；template=intimate_interaction；primary_backend=seedance；fallback_backends=dreamina；mode=frames2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=character_id_or_reference_group；quality_tier=high；risk_flags=contact_motion,feature_melting_risk,identity_drift_risk,native_multiframe,physical_interaction,seam_relay；degrade_plan=Replace full contact with reaction close-up, hand insert, or shot/reverse-shot.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=motion_control_required; prompt 只使用 primary_backend 真实支持的无声视频能力，失败按 degrade_plan/fallback 执行;
物理交互约束：required=true；manifest_path=出视频/第2集/control/Clip_09/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、接触漂移、武器归属错都判失败。;
身份锁定约束：CHAR_01/囚犯初醒态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态；CHAR_02/濒死战损态；identity_requirement=character_id_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_02__濒死战损态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png、出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑衣赤纹镇魔司·年轻锐利眉眼·左臂重伤·断刀·惨白冷汗;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：她把仅剩的金纹按回掌心，横刀归于暗银。 → 止：姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01/克制哀悼态', 'CHAR_02/遗体态', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['AMBIENT_官道马蹄火把']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=入画/现身：CHAR_02；出画/画外保留：CHAR_02/死亡态-遗体画外保留不复活、WEAPON_01 横刀；入画/现身：AMBIENT_官道马蹄火把；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；视频生成音频策略=无声视频流；不要使用音频输入；禁止原生人声、台词、旁白、哼唱、系统音和字幕文字;
人物运动：走回遗体；伸手合眼；低声记账；握刀起身；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：中景交代距离，特写只给手掌合眼和姜月初侧脸；避免身体贴靠或暧昧角度。;
情绪节奏：[0-终点] 她把仅剩的金纹按回掌心，横刀归于暗银。 -> 姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 constraints，避开 negative，按cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；视频-only silent stream；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: execute only this clip beat; do not add story events;
opening frame state: 她把仅剩的金纹按回掌心，横刀归于暗银。;
ending frame state: 姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。;
blocking: 姜月初蹲在裴长青遗体侧面，手掌只接触眼睑/额前区域；裴长青保持死亡态，不产生回应。;
performance beats: [0s-5.198s] 姜月初走回裴长青身边，尸场恢复冷灰，她蹲下替他合眼。; [5.198s-13.207s] 姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。;
motion refinement: low-to-medium amplitude, stable body balance, clear hand and weapon ownership, no face stretching;
close-up identity lock: use reference_group, face close-up, expression references; lock face not emotion; keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01/克制哀悼态', 'CHAR_02/遗体态', 'WEAPON_01 横刀', 'LOC_01']；offscreen_presence=['AMBIENT_官道马蹄火把']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=入画/现身：CHAR_02；出画/画外保留：CHAR_02/死亡态-遗体画外保留不复活、WEAPON_01 横刀；入画/现身：AMBIENT_官道马蹄火把；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 走回遗体；伸手合眼；低声记账；握刀起身;
camera motion: 中景交代距离，特写只给手掌合眼和姜月初侧脸；避免身体贴靠或暧昧角度。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative;
audio constraint: silent video stream only, no generated speech, no narration, no native voice, no humming, no subtitles; do not use audio input; discard any forced backend audio later.
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=frames2video; quality_tier=high; duration=13.207s; aspect=9:16; native_audio_policy=none; video_generation_audio_policy=无声视频流; identity adapter=character_id_or_reference_group; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 3, "native_timeline_frames": 5, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全，FeatureMelting/特征融化判失败
5. ✅ ②镜头运动：推/拉/摇/移/固定/跟拍等结构化词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气/火把随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：已登记角色ID/形态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; speech_policy=no_native_speech; compose_policy=丢弃; 无声视频流; 不使用音频输入
14. ✅ Motion Control：按本镜 route/control manifest 或 degrade_plan 执行

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜

## Clip 10（时长 5.494s · EP02_CLIP10 · 官道火把马蹄逼近）　**节奏**：集尾钩
**剧本可看性合同**：clip_id=EP02_CLIP10；dramatic_function=用外部势力逼近切出新危机，给第3集镇魔司/飞鹰门误认线入口。；audience_effect=观众带着“来的是救兵还是敌人”进入下一集。；spectacle_story_function=火把点阵与马蹄逼近只服务集尾外部势力入场和误认危机，不提前揭示身份、不升级成新打斗。。
**表演签名**：CHAR_01/囚犯初醒态: freeform=先缩肩屏息、迅速扫视逃路；紧张时嘴上吐槽，真做决定时声音压低。

**首帧**：`出图/第2集/图片/Clip10_first.png`
**锚帧1**（2.747s · keyframe · 逼近中段：火把点阵变亮，马蹄尘影仍在远景，姜月初开始转头。）：`出图/第2集/图片/Clip10_mid.png`
**尾帧**：`出图/第2集/图片/Clip10_end.png`
**场景**：LOC_01 荒野尸骸战场/冷灰夜/外; location_id=LOC_01; 资产：LOC_01
**导演意图**：用外部势力逼近切出新危机，给第3集镇魔司/飞鹰门误认线入口。
**起幅**：继承首帧构图、光位、轴线、角色状态和物料位置，不重定视觉设定。
**落幅**：落在ELS 官道远景→ELS 官道远景，动作/表情在最后 0.3-0.5 秒稳定住，方便接缝。
**场面调度**：姜月初背影在尸场前景偏低，官道火把线在远景高处/画面深处；两者保持明确距离，不提前同框接触。
**表演节拍**：[0s-5.494s] 远处官道忽然亮起一排火把，马蹄尘影朝尸场逼近，姜月初背影在前景转头。
**运动精修**：幅度=小/中；能量=集尾钩；身体守卫=重心、手部/武器归属、遮挡层级、脸部轮廓和发髻稳定；镜头运动只服务情绪，不追加未声明的旋转、漂浮、急甩。
**环境交互**：torch line grows brighter/far-to-near while CHAR_01 pivots attention, then cliffhanger cut；incoming force is environmental approach from far road toward battlefield; CHAR_01 only turns head；火把/马蹄是远景环境运动，不与前景角色发生接触；距离、光位和遮挡层连续。；主画面冷灰月夜，火把只提供远处暖点光，不改变姜月初面部主光。
**动作编排契约 / Action Choreography**：{"body_part_ownership": {"AMBIENT_官道马蹄火把": ["torch_line", "dust_shadow"], "CHAR_01": ["feet", "back", "head", "shoulders"], "LOC_01": ["battlefield_ground", "official_road"]}, "contact_points": ["CHAR_01 feet/body remain grounded in battlefield foreground", "distant torches/horses stay far background with no physical contact", "CHAR_01 head/shoulders rotate toward incoming torch line"], "force_direction": "incoming force is environmental approach from far road toward battlefield; CHAR_01 only turns head", "holder_state": {"AMBIENT_官道马蹄火把": "environmental actors, no holder assignment", "WEAPON_01": "offscreen/within CHAR_01 continuity from previous clip; not transferred"}, "motion_vector": "torch line grows brighter/far-to-near while CHAR_01 pivots attention, then cliffhanger cut", "notes": "Keeps cliffhanger threat spatially distant so no accidental contact/crowd appears in frame.", "occlusion_order": ["CHAR_01 back/shoulder foreground silhouette", "battlefield ground midground", "torch line and hoof dust background", "night sky/fog rear layer"], "participants": ["CHAR_01", "AMBIENT_官道马蹄火把", "LOC_01"], "release_frame": "none; no object drop before cut to black", "schema": "n2d.interaction_graph.v1", "transfer_event": "none"}
**专项镜头模板**：template_id=stealth_stalk; {"beats": ["远处官道亮起火把", "马蹄尘影由远逼近", "姜月初背影转头", "切黑留尾钩"], "blocking": "姜月初背影在尸场前景偏低，官道火把线在远景高处/画面深处；两者保持明确距离，不提前同框接触。", "camera_path": "远景固定/极慢推近，结尾可轻微压暗切黑。", "camera_rule": "ELS 远景固定或极慢推，利用雾、枯草、巨岩和夜色做遮挡层；火把只由远到近变亮，不让骑手近身露脸。", "continuity_must": ["LOC_01 冷灰夜色不跳", "姜月初仍为警觉态和破旧囚服", "CHAR_02 可画外保留，WEAPON_01 横刀也可画外保留；二者不是角色形态绑定", "官道火把是外部势力入口"], "degrade_plan": "若远景逼近不稳，降级为火把点阵远景 + 姜月初背影反应两个拆镜。", "distance_curve": "0s 远景极远火点；2.7s 火把变亮但仍在远景；5.4s 马蹄声压近后切黑，物理距离仍未接触。", "keyframe_plan": [{"at_sec": 0.4, "frame": "Clip10_first", "purpose": "远处火把初亮"}, {"at_sec": 2.747, "frame": "Clip10_mid", "purpose": "火把变亮、姜月初开始转头"}, {"at_sec": 5.1, "frame": "Clip10_end", "purpose": "切黑前威胁压近"}], "light_shadow_lock": "主画面冷灰月夜，火把只提供远处暖点光，不改变姜月初面部主光。", "negative": ["不要新增近身打斗", "不要让骑手瞬移到前景", "不要把火把变成系统面板", "不要让裴长青复活", "不要生成现代车辆"], "occlusion_layers": ["前景姜月初背影/荒草", "中景尸场雾气与枯草", "远景官道火把与尘影", "背景巨岩和夜雾"], "parallax_layers": ["前景荒草轻动", "中景低雾横移", "远景火把点阵靠近", "背景巨岩固定"], "physics_guard": "火把/马蹄是远景环境运动，不与前景角色发生接触；距离、光位和遮挡层连续。", "post_cue_points": [{"at_sec": 0.4, "cue": "远处第一排火把声画入"}, {"at_sec": 4.9, "cue": "马蹄声压过风声后切黑"}], "readability_beats": ["观众先读到远处有火", "听到马蹄逼近", "看到姜月初警觉转头", "切黑制造下一集问题"], "reveal_or_hide_beat": "只揭示外部势力逼近，不揭示身份；第3集再兑现镇魔司/飞鹰门误认线。", "screen_direction": "威胁从远处官道/画面深处向尸场前景逼近，姜月初由前景转头看向官道。", "spatial_path": "官道火把沿 LOC_01 远处道路向尸场方向推进；不穿越到姜月初身边。", "speed_curve": "火把移动由慢到快的听觉压迫，画面运动克制，最后一拍切黑。", "template_id": "stealth_stalk"}
**模型路由**：shot_type=stealth_stalk；template=stealth_stalk；primary_backend=seedance；fallback_backends=dreamina；mode=image2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=face_lock_or_reference_group；quality_tier=high；risk_flags=action_choreography_required,high_speed_motion,identity_drift_risk,motion_reference_candidate,native_multiframe,pose_drift_risk,seam_relay,spatial_path_risk；degrade_plan=Cut to front/back reaction shots or split into approach, pass-by, and exit clips.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=motion_control_required
**执行配方 / Execution Recipe**：{"audio_inputs": {"fallback_production_mode": "", "native_audio_policy": "none", "requires_voice_track": false, "speech_policy": "no_native_speech", "video_generation_audio_policy": "无声视频流"}, "backend": "seedance", "capability_match": {"frame_contract_supported": true, "motion_control_level": "medium", "motion_reference_supported": true}, "control_inputs": {"gate_policy": "block_without_ready_manifest_or_degrade_only_manifest", "manifest_path": "出视频/第2集/control/Clip_10/motion_control_manifest.json", "required": true, "required_inputs": ["pose_sequence", "depth_sequence", "camera_path", "spatial_path", "parallax_layers"]}, "execution_backend": "dreamina", "fallback": {"degrade_plan": "Cut to front/back reaction shots or split into approach, pass-by, and exit clips.", "fallback_backends": ["dreamina"]}, "frame_inputs": {"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}, "mode": "image2video", "quality_tier": "high", "reference_inputs": {"assets": ["LOC_01", "WEAPON_01"], "characters": [{"binding": "face_lock_or_reference_group", "character_id": "CHAR_01", "form": ""}, {"binding": "face_lock_or_reference_group", "character_id": "CHAR_02", "form": ""}], "identity_preservation_plan": {"applies_to": "stealth_stalk", "fallback_plan": "If identity drifts, split into identity closeup/reaction shot plus action wide/detail shot; do not silently swap backend or drop the story beat.", "motion_readability_allowances": ["prefer MCU/OTS/side/back/reaction inserts over forcing unstable full-body closeups", "allow wider framing or reduced facial detail during complex motion, but preserve costume silhouette and screen slot", "keep first/end frame and registered reference group as identity truth when motion control needs simpler movement"], "reference_strategy": "face_lock_or_reference_group", "required_identity_anchors": ["face_shape", "hairstyle", "age_read", "outfit_palette", "named_character_screen_slot"]}, "max_reference_images": 0, "motion_reference": {"allowed": true, "library_path": "生产数据/motion_reference_library.json", "policy": "use same sequence/shot_type approved reference when available"}}, "urgency_tier": "realtime"}
**Motion Control / 物理交互控制**：required=true；manifest_path=出视频/第2集/control/Clip_10/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,camera_path,spatial_path,parallax_layers；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、接触漂移、武器归属错都判失败。
**角色身份注册层**：CHAR_01/囚犯初醒态；identity_requirement=face_lock_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态
**本镜状态锁**：CHAR_01=警觉迎新危机；CHAR_02=濒死回光→死亡遗体→欠命账象征，画外保留、不复活、不参与动作。
**近景/反打身份锁定**：主焦点=CHAR_01；表情锚=起：姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。 → 止：远处官道忽然亮起一排火把，马蹄尘影朝尸场逼近，姜月初背影在前景转头。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。
**原生音画策略**：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; review=无声视频流，禁止模型生成台词、旁白、哼唱、系统音或环境人声，不使用音频输入。
**在场链约束**：required_presence=['CHAR_01/警觉态', 'AMBIENT_官道马蹄火把', 'LOC_01']；offscreen_presence=['CHAR_02/死亡态-遗体画外保留不复活', 'WEAPON_01 横刀']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：CHAR_02/死亡态-遗体画外保留不复活、WEAPON_01 横刀；入画/现身：AMBIENT_官道马蹄火把；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。
**衔接设计**：
- 入点：姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。
- 出点：远处官道忽然亮起一排火把，马蹄尘影朝尸场逼近，姜月初背影在前景转头。
- 转场：cliffhanger_cut
- 连贯性：eyeline=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。; shot_size=ELS 官道远景→ELS 官道远景; need_endframe=True

**continuity**：
- start_state：姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。
- action：远处官道亮起火把；马蹄尘影由远逼近；姜月初背影转头；切黑留尾钩
- end_state：远处官道忽然亮起一排火把，马蹄尘影朝尸场逼近，姜月初背影在前景转头。
- constraints：保持 LOC_01 光位锚/轴线/景别阶梯；保持 LOC_01；保持 CHAR_01 的脸型、五官比例、发型发髻、服装配色和当前伤势状态。
- negative：不要换脸、不要换衣、不要新增人物/路人/妖群、不要改变场景、不要改变发型、不要生成文字/logo/水印；表情变化时不要改变脸型/五官比例/眼距/鼻梁/下颌/痣疤，锁脸不锁情。

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。
  action: 远处官道亮起火把；马蹄尘影由远逼近；姜月初背影转头；切黑留尾钩
  end_state: 远处官道忽然亮起一排火把，马蹄尘影朝尸场逼近，姜月初背影在前景转头。
  constraints: 保持 LOC_01、LOC_01、CHAR_01 的视觉连续；轴线=姜月初视线优先锁画右虎山神/百妖谱面板；结尾转向官道火把。。
  negative: 不换脸、不换衣、不新增未登记人物/道具/背景路人、不改场景、不生成文字/logo/水印；锁脸不锁情。
导演意图：用外部势力逼近切出新危机，给第3集镇魔司/飞鹰门误认线入口。;
起幅：继承首帧构图、光位、轴线和角色状态，不重定视觉设定;
落幅：落在ELS 官道远景→ELS 官道远景，动作/表情在最后 0.3-0.5 秒稳定住; 
场面调度：姜月初背影在尸场前景偏低，官道火把线在远景高处/画面深处；两者保持明确距离，不提前同框接触。;
表演节拍：[0s-5.494s] 远处官道忽然亮起一排火把，马蹄尘影朝尸场逼近，姜月初背影在前景转头。;
运动精修约束：幅度小到中，身体守卫=重心稳定、手部/武器归属清楚、遮挡顺序清楚、脸部轮廓和发髻不拉伸;
环境交互约束：torch line grows brighter/far-to-near while CHAR_01 pivots attention, then cliffhanger cut；incoming force is environmental approach from far road toward battlefield; CHAR_01 only turns head；火把/马蹄是远景环境运动，不与前景角色发生接触；距离、光位和遮挡层连续。；主画面冷灰月夜，火把只提供远处暖点光，不改变姜月初面部主光。;
首帧保持：只保持首帧已锁定的人物身份、服装、场景、光位、道具位置和画面重心，不重定外貌、场景或画风;
动作编排约束：{"body_part_ownership": {"AMBIENT_官道马蹄火把": ["torch_line", "dust_shadow"], "CHAR_01": ["feet", "back", "head", "shoulders"], "LOC_01": ["battlefield_ground", "official_road"]}, "contact_points": ["CHAR_01 feet/body remain grounded in battlefield foreground", "distant torches/horses stay far background with no physical contact", "CHAR_01 head/shoulders rotate toward incoming torch line"], "force_direction": "incoming force is environmental approach from far road toward battlefield; CHAR_01 only turns head", "holder_state": {"AMBIENT_官道马蹄火把": "environmental actors, no holder assignment", "WEAPON_01": "offscreen/within CHAR_01 continuity from previous clip; not transferred"}, "motion_vector": "torch line grows brighter/far-to-near while CHAR_01 pivots attention, then cliffhanger cut", "notes": "Keeps cliffhanger threat spatially distant so no accidental contact/crowd appears in frame.", "occlusion_order": ["CHAR_01 back/shoulder foreground silhouette", "battlefield ground midground", "torch line and hoof dust background", "night sky/fog rear layer"], "participants": ["CHAR_01", "AMBIENT_官道马蹄火把", "LOC_01"], "release_frame": "none; no object drop before cut to black", "schema": "n2d.interaction_graph.v1", "transfer_event": "none"};
专项模板约束：template_id=stealth_stalk，遵守 beats/blocking/camera_rule/continuity_must/negative;
模型路由约束：shot_type=stealth_stalk；template=stealth_stalk；primary_backend=seedance；fallback_backends=dreamina；mode=image2video；video_generation_audio_policy=无声视频流；native_audio_policy=none；identity_requirement=face_lock_or_reference_group；quality_tier=high；risk_flags=action_choreography_required,high_speed_motion,identity_drift_risk,motion_reference_candidate,native_multiframe,pose_drift_risk,seam_relay,spatial_path_risk；degrade_plan=Cut to front/back reaction shots or split into approach, pass-by, and exit clips.；audio_override=无声视频流；speech_policy=no_native_speech；do_not_use_audio_inputs=true；native speech forbidden；policy_resolution.winner=motion_control_required; prompt 只使用 primary_backend 真实支持的无声视频能力，失败按 degrade_plan/fallback 执行;
物理交互约束：required=true；manifest_path=出视频/第2集/control/Clip_10/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,camera_path,spatial_path,parallax_layers；failure_modes=feature_melting,limb_fusion,contact_drift,weapon_owner_swap,occlusion_order_error,spatial_path_drift；FeatureMelting/特征融化、肢体融合、接触漂移、武器归属错都判失败。;
身份锁定约束：CHAR_01/囚犯初醒态；identity_requirement=face_lock_or_reference_group；reference_group=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png；Character ID / Face Lock / reference controls: fallback_reference_group；脸部特写=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png；expressions=出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png；身份不变量=脸型/五官比例/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色；锚点句=黑色半散长发·冷艳东方少女脸·纤细高挑身形·灰褐粗布囚服·惊惧压狠眼神·百妖谱金光能力态;
近景身份锁定约束：主焦点=CHAR_01；表情锚=起：姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。 → 止：远处官道忽然亮起一排火把，马蹄尘影朝尸场逼近，姜月初背影在前景转头。；表情幅度=大；引用同源 expressions/表情参考，锁脸不锁情：表情只动面部肌肉，脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色不变；CU/MCU/反打/说话镜限制低幅转头和低强度运镜，配角近景不稳则改 MCU/OTS/侧脸/手部/物件反应镜。;
在场链约束：required_presence=['CHAR_01/警觉态', 'AMBIENT_官道马蹄火把', 'LOC_01']；offscreen_presence=['CHAR_02/死亡态-遗体画外保留不复活', 'WEAPON_01 横刀']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：CHAR_02/死亡态-遗体画外保留不复活、WEAPON_01 横刀；入画/现身：AMBIENT_官道马蹄火把；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
原生音画约束：audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃；视频生成音频策略=无声视频流；不要使用音频输入；禁止原生人声、台词、旁白、哼唱、系统音和字幕文字;
人物运动：远处官道亮起火把；马蹄尘影由远逼近；姜月初背影转头；切黑留尾钩；表情按表情锚起→止，幅度不超封顶，锁脸不锁情;
镜头运动：ELS 远景固定或极慢推，利用雾、枯草、巨岩和夜色做遮挡层；火把只由远到近变亮，不让骑手近身露脸。;
情绪节奏：[0-终点] 姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。 -> 远处官道忽然亮起一排火把，马蹄尘影朝尸场逼近，姜月初背影在前景转头。;
动态细节：人物运动、服饰/发丝/尘雾/光效按本镜动作小幅响应，背景不闪烁、不重构;
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 constraints，避开 negative，按cliffhanger_cut服务下一镜;
禁止：不换脸、不换衣、不改变发型/五官比例/服装配色、不新增未登记人物/道具/背景路人、不改场景光位、不生成文字/logo/水印；no_native_speech，禁止原生人声/台词/旁白/哼唱;
声音约束：no_native_speech；无对白、无旁白、不要生成原生人声；视频-only silent stream；若平台强出声音，后期丢弃。
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
director intent: execute only this clip beat; do not add story events;
opening frame state: 姜月初侧脸贴近裴长青，眼底没有哭出来，只有欠账记住后的冷静。;
ending frame state: 远处官道忽然亮起一排火把，马蹄尘影朝尸场逼近，姜月初背影在前景转头。;
blocking: 姜月初背影在尸场前景偏低，官道火把线在远景高处/画面深处；两者保持明确距离，不提前同框接触。;
performance beats: [0s-5.494s] 远处官道忽然亮起一排火把，马蹄尘影朝尸场逼近，姜月初背影在前景转头。;
motion refinement: low-to-medium amplitude, stable body balance, clear hand and weapon ownership, no face stretching;
close-up identity lock: use reference_group, face close-up, expression references; lock face not emotion; keep face shape, facial proportions, eye spacing, nose bridge, jawline, hairstyle, accessories and costume palette unchanged;
presence lock: required_presence=['CHAR_01/警觉态', 'AMBIENT_官道马蹄火把', 'LOC_01']；offscreen_presence=['CHAR_02/死亡态-遗体画外保留不复活', 'WEAPON_01 横刀']；forbidden_presence=['未登记路人', '新增妖群', '现代物件', '字幕文字', '随机汉字', 'logo', '水印']；entry_exit=出画/画外保留：CHAR_02/死亡态-遗体画外保留不复活、WEAPON_01 横刀；入画/现身：AMBIENT_官道马蹄火把；required_presence 必须可见，offscreen_presence 只能画外/虚焦/反打外，forbidden_presence 严格禁止。;
character motion: 远处官道亮起火把；马蹄尘影由远逼近；姜月初背影转头；切黑留尾钩;
camera motion: ELS 远景固定或极慢推，利用雾、枯草、巨岩和夜色做遮挡层；火把只由远到近变亮，不让骑手近身露脸。;
continuity constraint: begin from start_state, perform only action, end on end_state, preserve constraints, avoid negative;
audio constraint: silent video stream only, no generated speech, no narration, no native voice, no humming, no subtitles; do not use audio input; discard any forced backend audio later.
```

### 平台参数
- primary_backend=seedance; fallback_backends=['dreamina']; mode=image2video; quality_tier=high; duration=5.494s; aspect=9:16; native_audio_policy=none; video_generation_audio_policy=无声视频流; identity adapter=face_lock_or_reference_group; frame_inputs={"consumption_mode": "native_multiframe", "first_frame": true, "last_frame": true, "mid_anchors": 1, "native_timeline_frames": 3, "reference_only": false, "requires_split_relay": false}

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍 / 运动精修 / 环境交互齐全
3. ✅ ④人物运动：动作链明确、幅度与能量可控、可由首帧自然推出
4. ✅ 物理守卫：重心、锁定部位、遮挡层级、不穿模/不拉脸约束齐全，FeatureMelting/特征融化判失败
5. ✅ ②镜头运动：推/拉/摇/移/固定/跟拍等结构化词明确，速度和方向明确
6. ✅ 动态细节 & 环境交互：尘雾/衣袂/发丝/金光/黑血妖气/火把随动作反馈，不改首帧设定
7. ✅ ⑦张力：运镜与节奏/张力一致
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全
9. ✅ 在场链：required/offscreen/forbidden 与 entry_exit 已写入正负约束
10. ✅ 模型路由：primary/fallback/mode/native_audio_policy/identity_requirement/degrade_plan 已继承
11. ✅ 角色身份注册层：已登记角色ID/形态、reference_group、脸型/五官比例/发型发髻/标志配饰/服装配色已锁
12. ✅ 近景身份锁定：脸部特写/expressions、表情锚、表情幅度、锁脸不锁情已写；不稳则 MCU/OTS/侧脸/手部/物件反应镜
13. ✅ 原生音画策略：audio_intent=none; speech_policy=no_native_speech; compose_policy=丢弃; 无声视频流; 不使用音频输入
14. ✅ Motion Control：按本镜 route/control manifest 或 degrade_plan 执行

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：开头画面与首帧 PNG 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度与能量符合 prompt，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 在场链：没有凭空新增人物/路人/道具；画外角色没有被模型拉到主体位置
- [ ] 物理守卫：禁动部位、接触点、手部归属、脸部轮廓和发髻稳定，无穿模、拉脸或特征融化 FeatureMelting
- [ ] 镜头运动：符合 prompt 的结构化运镜，无突兀乱甩或无意义缩放
- [ ] 动态细节 & 环境交互：动作对光影/粒子/道具/背景的反馈成立，无现代物件/文字/logo/水印
- [ ] 原生音画：确认无原生人声、旁白、哼唱或多余人声；若后端强制产出音轨，后期丢弃
- [ ] 近景身份：检查脸型、五官比例、发型发髻、标志配饰、服装配色；配角漂移则废料重跑或改 MCU/OTS/侧脸/手部/物件反应镜
