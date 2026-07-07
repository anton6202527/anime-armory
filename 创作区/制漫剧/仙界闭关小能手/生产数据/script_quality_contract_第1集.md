# 剧本质量交接合同

- episode: 第1集
- status: pass
- blocks: 0
- warnings: 1
- clips: 6

## 可签收字段

- core_attraction: category 底层压迫到机缘悬念 why_watch 观众想看一个被仙门当废物的十四岁少年，如何在最苦杂役活里撞见改命入口。 audience_payoff 本集不急着开挂，先把羞辱、苦活和主动求生拍足，最后用黑陶破盆微光留下追更问题。
- first_3s_visual_hook: visual_hook 黑暗杂役大殿里，瘦小的贺平生被一圈杂役围住，张老大从高位俯视审问。 content_promise 这个少年为什么刚入门就被当成废物？他会怎样活下去？ onscreen_text 五行灵根？ muted_readable True expected_metric primary retention_3s target 0.72
- retention_promise_ledger: 3
- pacing_allocation: declared total_target_sec 60 primary_runtime_focus EP01_CLIP01 EP01_CLIP02 EP01_CLIP04 EP01_CLIP05 EP01_CLIP06 compressed_clip_ids EP01_CLIP03 strategy 主时长给黑殿羞辱、挑水死令、主动提前认路、挑水压迫和夜潭
- audience_question_ledger: 16
- performance_cues: 0

## Clip 戏剧功能与时长角色

| Clip | Duration | Pacing Role | Priority | Dramatic Function | Audience Effect | Spectacle Function |
|---|---:|---|---|---|---|---|
| EP01_CLIP01 | 19.573 | 冷开场主钩 | primary | 用围审和嘲笑把主角的低位、五行灵根劣势和杂役阶层压迫一次打出。 | 观众立刻知道主角被羞辱，并等待他如何在仙门底层活下去。 | 无；本镜靠表演压迫和镜头调度，而不是奇观。 |
| EP01_CLIP02 | 9.76 | 主线任务落点 | primary | 把口头羞辱转成会压垮身体的具体苦差，建立夜潭破盆的因果。 | 观众知道主角不是随便去水边，而是被迫进入高强度挑水行动线。 | 无；本镜是任务压迫。 |
| EP01_CLIP03 | 3.003 | 背景一笔带过 | low | 补足贺平生为什么无路可退，但不占用主时长。 | 观众获得最低限度背景理解，然后立刻回到行动线。 | 无；本镜是压缩背景。 |
| EP01_CLIP04 | 2.96 | 主角主动性 | primary | 用动作表现主角谨慎和韧性，避免用长心理旁白解释。 | 观众开始站到主角一边，知道他不是只会挨打。 | 无；本镜是行动选择。 |
| EP01_CLIP05 | 7.099 | 身体压迫高光 | highlight | 兑现二十趟挑水的体力压迫，让破盆机缘显得是苦活尽头撞出的结果。 | 观众感到他真的撑到极限，愿意继续看他发现异常。 | 无；本镜不是打斗奇观，而是身体代价高光。 |
| EP01_CLIP06 | 16.572 | 集尾钩子高光 | highlight | 把本集苦活转成金手指入口，留下第2集必须兑现的破盆异常。 | 观众知道这不是普通破盆，会追问它能带来什么变化。 | 破盆微光是剧情悬念，不是大法术爆发；光效必须克制，服务神秘感。 |

## Findings

| Severity | Code | Clip | Message |
|---|---|---|---|
| warn | spectacle_clip_too_short_without_beat | EP01_CLIP04 | 奇观 Clip 仅 2.96s；若是打斗/爆发主看点，建议给足起手-命中-反应节拍；若只是一笔带过，补 compression_plan。 |
