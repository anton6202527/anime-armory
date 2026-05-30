# 冷宫有妖气_第7集_Veo / 海外适配（跨平台落地样例）

> **不变（复用）**：`分镜剧本.md` / 角色卡 / 场景卡。海外投放配 `字幕_英文.srt`（已英化为 ReelShort/TikTok 口语）。
> **只换"视频生成"适配层**：Veo 等海外平台**英文优先**——英文角色锚定句必须稳定复用（人名统一音译），镜头用英文电影术语（dolly in / pan / tracking / orbit / push-in / lock-off / whip-pan），运动写进 prompt（多数版本无独立负面框，负面改为正向描述或省略）。
> 一致性：先用各角色定妆照英文 prompt（**Cuiwei 三态：disguised / true-demon / death-smoke**）出关键帧 → 作为 image-to-video 首帧。
> EN anchors: **Shen Nian (bait-level aura)** = "barely visible faint dark-gold sheen across her body, intentionally restrained"; **Shen Nian (Silver-Rank full burst)** = "dark-gold totem patterns surging across her body in an instant, golden vertical pupils, silver-white demonic shockwave bursting from her body, candles blown out, window paper sent flying"; **Cuiwei (disguised)** = "jade-green narrow-sleeved palace maid robe, low chignon, slim oval face, demure phoenix eyes, cold-pale skin"; **Cuiwei (true demon form)** = "blood-red pupils, mouth torn open at both corners with two rows of long sharp fangs, ten fingernails extended three inches into icy claws like daggers, cold-cyan skin with faint veins, dark-green stinking aura, hoarse growl"; **Cuiwei (death)** = "body bursts into black smoke and dissipates outward, leaving a pool of foul blood and a heap of scattered jade-green robe, last flicker of blood-red pupils in the smoke"; scenes = "cold-palace bedchamber dim and candlelit / cold-palace well in afternoon shadow"; style = "cinematic Chinese ancient-fantasy webcomic, chiaroscuro lighting, vertical 9:16".
> **Episode 7 structure**: front half (Shots 1-8) is bait-and-test, locked-off / slow-tracking, micro-expression heavy; back half (Shots 9-14) is reveal-fight-execute, fast tracking, motion-heavy, gradient-effect heavy. Veo's strength on "atmospheric acting + dramatic light" fits both halves well.

## Shot/Clip 1 (6s) — 镜头1 (the plot)
**Video prompt (EN, image-to-video)**: In a dim cold-palace bedchamber, Shen Nian sits at an old table and lowers her voice to instruct Xiao He, the young maid; in the wall crack behind them, a tiny pair of eyes briefly glints (the rat-spirit eavesdropping). Camera: locked-off medium two-shot, almost no movement, conspiratorial mood. Sparse warm candlelight in cool grey ambience.

## Shot 2 (6s) — 镜头2 (well-side casual chat)
By the worn cold-palace well in the afternoon, Xiao He cranks the wooden bucket up on a rough hemp rope while Cuiwei, in a jade-green maid robe, crouches at the stone laundry slab scrubbing cloth — they trade casual chatter. Camera: medium slow dolly, slanting afternoon sun cut by tall walls into half-warm-half-cold-cyan.

## Shot 3 (5s) — 镜头3 (the tell — **micro-expression critical**)
Close-up on Cuiwei: mid-scrub her washing hand **freezes for half a second**; she glances up — a barely perceptible flash of unease in her eyes, less than half a second — then she lowers her gaze and resumes scrubbing, her knuckles whitening around the cloth. Camera: locked-off close-up, the last second slowly pushing in on her trembling knuckles. **Important**: keep the flash subtle — under-act it.

## Shot 4 (5s) — 镜头4 (paper window peek)
Deep night. Close-up on the bedchamber's paper window: a single fingertip silently punches through from outside, leaving a small hole; an eye presses up to the hole, pupil faintly glowing green in the dark. Camera: locked-off macro on the paper; last half second cuts to her shadowed face outside in side light.

## Shot 5 (6s) — 镜头5 (the bait — gradient strong-suit)
Inside the dim bedchamber, Shen Nian sits cross-legged on the worn bed, eyes closed; **a barely-there dark-gold sheen gradually appears across her body — only just visible, intentionally restrained at "bait" intensity, NOT the full awakened glow**. Cut to the outside POV through the hole: Cuiwei's pupil flashes blood-red for an instant then returns to black. Camera: slow push-in on Shen Nian → cut to extreme close-up on the eye at the hole.

## Shot 6 (6s) — 镜头6+7 (Cuiwei retreats, rat-spirit reports)
Shen Nian's eyes snap open with a faint smile; a small shadow drops down from the roof beams — the rat-spirit lands trembling at her feet, half-human half-rat, pointed snout, grey-brown fur, and reports in a thin shaky voice that Cuiwei's eyes "went red, like a starving wolf looking at meat". Shen Nian nods coldly. Camera: close-up on Shen Nian → medium two-shot.

## Shot 7 (7s) — 镜头8 (next morning — the act)
Morning light slants into the bedchamber doorway. Cuiwei, demure and respectful, "dares" to ask what art Shen Nian was practicing last night. Shen Nian first flashes wariness, then sighs in feigned resignation and casually claims it's "health exercises a wandering Taoist once taught her — nothing big". Camera: locked-off two-shot medium.

## Shot 8 (6s) — 镜头9 (Cuiwei walks away faster — Shen Nian's verdict)
Close-up on Cuiwei: a flicker of disappointment in her eyes, then a polite smile and a faster-than-arrival exit. Reverse to Shen Nian, hands clasped behind her back, telling Xiao He quietly: "She thinks I'm a mortal who grew demonic power. Tonight, she strikes." Xiao He's face goes pale, she gasps. Camera: close-up → reverse shot.

## Shot 9 (6s) — 镜头10 (midnight bowl)
Past midnight. The wooden door creaks open; Cuiwei walks in smiling, holding a porcelain bowl of broth, and gently sets it on the bedside table. She slowly raises her head and locks eyes with Shen Nian. The candle pops once. Camera: tracking-in through the door → locked medium on the eye-lock.

## Shot 10 (5s) — 镜头11 (the transformation — **gradient strong-suit, hardest shot**)
Close-up on Cuiwei. In the moment their eyes meet: **her pupils flash blood-red (~0.3s), the corners of her mouth tear open to reveal two rows of long sharp fangs (~0.5s), her ten fingernails extend three inches into icy claws like daggers (~1s), her skin goes cold-cyan with faint veins showing**; a dark-green stinking aura billows at the frame edges; a hoarse growl. Camera: locked close-up, 0.4s slow-mo on completion of the transformation. **Critical for Veo**: write the transformation in time-order ("first pupils, then mouth, then nails, then skin"); consider splitting into two short shots.

## Shot 11 (6s) — 镜头12 (Shen Nian erupts — gradient top-tier)
Shen Nian rises from the edge of the bed with a soft sigh. **Dark-gold ancient totem patterns surge from her wrists across her entire body in an instant, her pupils turn into beast-like golden vertical pupils, and a burst of silver-white demonic aura erupts from her body** — the shockwave snuffs every candle in the room and sends all the paper-window panels flying; Cuiwei stumbles back two steps. Camera: close-up slow push-in → pull back to medium for the shockwave impact. Cold silver-white burst against warm dark-gold pattern light — color layering matters.

## Shot 12 (7s) — 镜头13 (brief brutal scuffle)
Cuiwei attacks like a phantom — her claws sweep at Shen Nian's throat; Shen Nian steps back half a pace and the claws part air three inches in front of her throat. Cuiwei's claw shadows shred the wooden screen and bed frame, paper-window shrapnel filling the air. Shen Nian dodges while studying her, smile fading into mild disinterest. Camera: handheld tracking with whip-pans, one 0.4s slow-mo on the claws missing her throat.

## Shot 13 (7s) — 镜头14 (crush + pin + interrogate)
Shen Nian stops dodging, meets a claw head-on, **grabs Cuiwei's wrist and crushes it with an audible bone-crack** (0.3s slow-mo); her other hand closes around Cuiwei's throat and slams her against the brick wall, dust falling, Cuiwei's feet leaving the ground in a piercing scream. Shen Nian leans in, voice ice-cold, demanding who sent her; her fingers tighten, neck bones cracking — Cuiwei finally breaks and gasps out: **"The Empress sent us! One more in the imperial kitchen — 'Madam Liu' — the strongest of us three!"** Camera: close-up, swaying candle shadow.

## Shot 14 (7s) — 镜头15 (execution + system + hook)
Shen Nian lets go; Cuiwei collapses onto the floor begging. Shen Nian asks coldly: "Have you ever eaten anyone?" Cuiwei opens her mouth but doesn't deny it. A single punch — **Cuiwei's body bursts into black smoke and dissipates outward** (0.3s slow-mo on the moment of impact), leaving only a pool of foul blood and a heap of scattered jade-green robe; in the smoke her blood-red pupils flicker one last time and vanish. A translucent jade-green UI panel flickers into view with vertical seal-script text; camera pulls back into a wide shot — Shen Nian stands at the center of the wrecked bedchamber, hair slightly disheveled, silver-white patterns lingering on her arms, sighing softly. Camera: close-up → slow pull to wide, freeze.

---
**English subtitle (paired)**: use `字幕_英文.srt` as-is (already timed & localized in ReelShort/TikTok-style spoken English). System line stays game-style ("Lesser demon Cuiwei slain. EXP +10. 195/500."). Names fixed: **Shen Nian, Lin Wan'er, Cuiwei, Xiao He, Madam Liu, the Empress, the cold palace, imperial kitchen**. Rank terms: "Mid Jade-Rank" (青玉妖位中期) / "Silver Rank" (银牌妖位).

**Cover image (high-CTR, EN)**: see `封面.md` English prompt — Silver-Rank Shen Nian crushing demon-form Cuiwei's wrist against the wall, silver-white vs blood-red and dark-green collision, wrecked bedchamber background.
