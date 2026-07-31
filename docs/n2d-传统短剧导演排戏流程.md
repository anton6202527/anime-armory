# n2d 传统短剧导演排戏流程与 P-2 落地

> 记录日期：2026-07-02  
> 目的：把“专业导演拿到剧本后如何排戏、调度、设计运镜和镜头衔接”沉淀为 n2d 的可执行前置层。完整的编剧/导演/制片/后期全流程落地见 [`n2d-传统短剧制作全流程落地方案.md`](n2d-传统短剧制作全流程落地方案.md)。

## 1. 问题

用户问：审查 n2d，模拟传统短剧制作过程。假如你是专业导演，拿到剧本后会怎么排？是否要考虑每个镜头的衔接、运镜手法、层层递进？结合专业知识和实时搜索，给出详细答案和项目落地方案。

## 2. 传统导演会先做什么

专业导演不会直接把剧本逐句翻译成分镜。第一步是“排戏”：

- 读出每场戏的戏剧目的：这一场到底让观众知道什么、期待什么、担心什么。
- 确定人物欲望和阻碍：主角此刻想要什么，谁或什么挡住他。
- 画情绪变化：从压迫到爆发、从怀疑到确认、从误判到反转。
- 决定人物调度：谁在前景/中景/后景，谁靠近、谁后退，谁掌握权力。
- 锁轴线和视线：正反打、过肩、动作方向、看向道具/人/出口的方向要连续。
- 设计景别进程：定场镜建立空间，中景建立关系，近景/特写打情绪和信息峰值。
- 设计衔接：动作接、视线接、声音桥、J cut、L cut、空镜缓冲、尾帧接力。
- 决定运镜动机：镜头运动不是为了“炫”，而是为了压迫、揭示、追随、释放或制造信息落点。

传统剧组分工也支持这个判断：导演会和摄影指导确定拍摄风格、镜头与剧本调整；摄影指导会把演员移动和摄影机移动精确化；一副导演拆解角色、场景、道具、设备与排期；场记/剧本监督负责轴线、视线、动作、服化道和剪辑连续性。

## 3. 竖屏短剧的额外要求

竖屏短剧不是把横屏戏裁成 9:16。它有额外导演规则：

- 前 3-6 秒必须有钩子：冲突、危机、反差、欲望、真相半露或强视觉信息。
- 9:16 里脸要可读：多人并排会挤脸，更适合前后景纵深和反打。
- 用 Z 轴调度：人物靠近/后退、前景遮挡、纵深压迫，比横向站排更适合手机屏。
- 广角大远景要克制：可定场，但不能让观众看不清人物表情。
- 反应镜很重要：短剧爽点不只拍“事件”，还要拍“别人被打脸/被震住/意识到”的反应。
- 中段要持续给信息增量：不只是快切，而是每 10-20 秒让观众多知道一点或多担心一点。

## 4. 运镜口径

运镜要有动机：

- 固定机位：适合对白、压迫、审讯、系统面板、表演稳定。
- 缓慢推镜：适合意识到真相、压力逼近、情绪收紧。
- 拉镜头：适合孤立感、余韵、退场、关系破裂。
- 跟拍/移镜：适合追逐、行动、空间方向明确的动作。
- 升降/俯仰：适合揭示权力关系、空间层级、人物抬头/坠落。
- 短促冲击变焦/甩镜：只用于爆点瞬间，不能整镜乱动。
- 环绕/复杂飞行镜：高风险，除非是仪式感、高光展示或有后端能力证据，否则优先降级。

## 5. n2d 当前能力与缺口

n2d 已有基础：

- `skills/n2d/n2d-script/references/分镜语法.md`：景别、轴线、30 度规则、视线方向、转场、运镜克制。
- `skills/n2d/references/导演节奏.md`：黄金 3 秒、前 15 秒立钩、中段钩子、集尾 cliffhanger。
- `skills/n2d/n2d-script/scripts/director_camera_plan.py`：storyboard 定稿后生成运镜建议和 prompt 注入。
- `skills/n2d/n2d-script/scripts/shot_grammar_audit.py`：审查连续同景别、缺定场、爆点不近景、转场单调等问题。
- `n2d-review` gate 已有导演一致性、轴线视线、运镜消费收据等后置审查。

主要缺口：

- 导演层以前偏“分镜后审查”，不是“分镜前排戏”。
- `director_camera_plan.py` 是 storyboard 后的建议，不是 storyboard 前的设计输入。
- 缺少统一的 blocking/floorplan/axis map/transition map/shot progression plan。
- 竖屏构图、Z 轴纵深、字幕/overlay 安全区没有作为分镜前硬输入。
- 剪辑可用性不够前置：J/L cut、反应镜、空镜缓冲、首尾帧接力应该先锁。

## 6. 已落地的 P-2 导演排戏包

P-2 放在 Stage 1 台词之后、Stage 2 分镜之前：

```text
小说进入
→ P-1 开发包：这部戏值不值得、怎么改
→ 阶段1 剧本改编：voiceover / bgm / 封面 / 角色场景卡
→ P-2 导演排戏包：这一集怎么排、怎么拍、怎么剪
→ 阶段2 分镜设计
→ 出图 / 出视频 / 合成 / review
```

脚本：

```bash
python3 skills/n2d/n2d-script/scripts/director_blocking_pack.py <作品根> 第1集 scaffold --write
python3 skills/n2d/n2d-script/scripts/director_blocking_pack.py <作品根> 第1集 check --json --write-missing
```

必填文件：

- `脚本/第N集/director_beat_sheet.json`
- `脚本/第N集/axis_blocking_map.json`
- `脚本/第N集/shot_progression_plan.json`
- `脚本/第N集/transition_map.json`
- `脚本/第N集/vertical_composition_plan.json`
- `脚本/第N集/edit_rhythm_map.json`

汇总与检查：

- `生产数据/director_blocking_pack_第N集.md`
- `生产数据/director_blocking_pack_check_第N集.json`

签收口径：六个 JSON 默认 `"status": "draft"`。补完、删掉 `待补/TODO` 后，全部改为 `"status": "confirmed"` 才能进入正式分镜。`run.py next|enter` 在 `script_stage2` 前会自动检查，未确认时返回 `prework_failed`。

## 6.1 已落地的 P-3 制片拆解包

导演排戏和 Stage 2 分镜之后，`n2d` 还新增一层制片交接，放在出图 prompt 之前：

```text
P-2 导演排戏包
→ 阶段2 分镜设计
→ P-3 制片拆解包：逐镜生产拆解 + 连续性拆解 + AI 拍摄通告单
→ 出图 prompt / 出图 / 出视频
```

脚本：

```bash
python3 skills/n2d/n2d-script/scripts/production_breakdown.py <作品根> 第1集 scaffold --write
python3 skills/n2d/n2d-script/scripts/production_breakdown.py <作品根> 第1集 check --json --write-missing
```

必填文件：

- `脚本/第N集/production_breakdown.json`
- `脚本/第N集/continuity_breakdown.json`
- `脚本/第N集/ai_call_sheet.md`

签收口径：三个文件都必须 `status=confirmed` 且不含 `待补/TODO`。`run.py next` 在 `image_prompt` 前自动检查，未确认时阻断出图 prompt。

## 7. 来源

- ScreenSkills Director: https://www.screenskills.com/job-profiles/browse/film-and-tv-drama/development-film-and-tv-drama-job-profiles/director-film-and-tv-drama/
- ScreenSkills Director of Photography: https://www.screenskills.com/job-profiles/browse/film-and-tv-drama/technical/director-of-photography-dop/
- ScreenSkills First Assistant Director: https://www.screenskills.com/job-profiles/browse/film-and-tv-drama/production-management/assistant-director/
- ScreenSkills Script Supervisor: https://www.screenskills.com/job-profiles/browse/film-and-tv-drama/technical/script-supervisor-film-and-tv-drama/
- TikTok Creative Best Practices: https://ads.tiktok.com/help/article/creative-best-practices
- Filmustage Vertical Drama Breakdown: https://filmustage.com/blog/how-to-break-down-a-vertical-drama-script-for-production/
- Amo Pictures Vertical Drama Production: https://www.amopictures.com/blog/vertical-drama-production-how-short-form-fiction-is-made-for-mobile-audiences
