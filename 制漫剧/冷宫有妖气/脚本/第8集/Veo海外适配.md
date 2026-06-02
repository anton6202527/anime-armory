# 冷宫有妖气_第8集_Veo / 海外适配（跨平台落地样例）

> **不变（复用）**：`分镜剧本.md` / 角色卡 / 场景卡。海外投放配 `字幕_英文.srt`（已英化为 ReelShort/TikTok 口语）。
> **只换"视频生成"适配层**：Veo 等海外平台**英文优先**——英文角色锚定句必须稳定复用，镜头用英文电影术语（dolly in / pan / tracking / orbit / crane down / push-in / lock-off / pull back / overhead）。
> 一致性：先用沈念银牌态定妆照英文 prompt 出关键帧 → 作为 image-to-video 首帧。
> EN anchors: **Shen Nian (Silver Rank, training mode)** = "deposed concubine Lin Wan'er in Silver-Rank demon form, jet-black hair in a simple bun with plain silver pin, pale-cyan worn palace robe, silver-white restrained demonic patterns on her arms, golden vertical pupils, frost at her fingertips, restrained internal aura"; **ice spike** = "finger-thick translucent ice spike, sharp pointed tip glinting frost-cold light, white mist swirling around it"; **ice wall** = "three-foot tall, ten-foot wide, two-inch thick crystal-clear ice wall, fine internal crystallization patterns"; scene = "abandoned cold-palace back garden, torn red lanterns, dead trees as targets, central stone-slab clearing, dusk shifting from warm orange to cool cyan"; **Xuantian Pavilion** = "the silhouette of a towering gilt-roofed three-tiered pavilion deep within the Forbidden City, cold gilt sheen in the dusk, drifting clouds"; style = "cinematic Chinese ancient-fantasy webcomic, chiaroscuro lighting, vertical 9:16".
> **Episode 8 nature**: training + lore-drop episode, no opponent. Tension carried by **visible growth curve** (1→5→10 ice spikes, ice wall rises, fist meets wall) + **information reveal** (cheat-tier reveal + Xuantian Pavilion clue + tiger demon hook). Veo's strengths on "atmospheric solo shots + slow gradient effects + dreamlike dissolves" fit this episode perfectly.

## Shot/Clip 1 (6s) — 镜头1 (the Empress goes silent)
**Video prompt (EN, image-to-video)**: An empty dim cold-palace bedchamber, dust drifting in a shaft of slanting sunlight; Shen Nian stands in profile by the window, looking out at the deserted palace corridor — not a single eunuch in sight. Camera: locked-off establishing shot dollying gently to a profile close-up. Cold grey ambience.

## Shot 2 (6s) — 镜头2 (system EXP panel)
Close-up on Shen Nian; with a flicker of intent, a translucent jade-green system UI panel fades in before her eyes — vertical seal-script text "Myriad-Demon Bloodline LV2 (Silver Rank) · EXP 195/500 · 305 to next level" scrolling on with light. Camera: locked-off close-up.

## Shot 3 (6s) — 镜头3 (abandoned back garden — establishing)
Wide shot of the cold-palace back garden utterly abandoned post-banquet — torn fallen red lanterns, flipped low tables, shattered cups and dead leaves on the ground, a ring of dead trees framing the space, an open stone-slab clearing at center. Shen Nian, in pale-cyan worn robe, walks calmly to the center. Camera: wide establishing dolly-in to medium on her. Cool cyan with residual orange accents.

## Shot 4 (6s) — 镜头4 (single ice spike forms — **gradient strong-suit**)
Close-up on Shen Nian standing in the clearing, eyes closed, deep breath; her right hand lifts before her chest. Moisture in the air visibly draws toward her fingertip — and **a single finger-thick translucent ice spike crystallizes out of thin air**, hovers, slowly rotates, sharp pointed tip glinting with frost-cold light, white mist swirling. Camera: slow push-in to extreme close-up on the spike tip. Keyword the gradient: "ice forming from thin air, gradual crystallization, frost mist swirling".

## Shot 5 (6s) — 镜头5 (spike flies, frost spreads)
The ice spike pivots and targets a dead tree ten paces away. Shen Nian whispers "Go." The spike **streaks through the air and pierces the trunk three inches deep**, and a layer of **white frost radiates outward** from the impact point in a starburst pattern across the bark. Camera: tracking shot on the spike, 0.4s slow-mo on impact.

## Shot 6 (6s) — 镜头6 (five spikes — uneven, growth-stumble)
Medium shot. Shen Nian attempts to summon five ice spikes simultaneously — they hover before her, **uneven in size, angles wobbly**; with a flick of intent, they fly out, but only two hit the tree (muffled thumps), three veer off into the dirt or skim the trunk. She wipes sweat from her brow, brow furrowed. Camera: locked-off medium. **Important**: keep the imperfection visible — this is the growth-curve contrast point.

## Shot 7 (8s) — 镜头7 (training montage 1→5→10 — **top-tier gradient**)
Time-lapse montage:
- 0-3s: under harsh midday sun, sweat dripping, one/three spikes practice.
- 3-5s: at dusk, seven uniform spikes hovering steadily.
- 5-8s: deep dusk — **ten uniform ice spikes deploy in a fan formation, locking onto five dead trees (two per tree)**; she flicks her hand — **all ten release at once, hitting ten independent points simultaneously, ten frost-bursts blooming in unison**. She exhales, satisfied. Camera: rapid time-lapse cuts, final 2s slow push-in on the synchronized frost-bloom. **Important for Veo**: consider splitting into two 4s sub-shots to preserve gradient quality.

## Shot 8 (7s) — 镜头8 (ice wall rises — **top-tier gradient, single take**)
Medium close-up. Shen Nian half-kneels on the stone slab, both palms pressed flat. Moisture is drawn from ground and air; **frost spreads from beneath her palms outward**; then, with a crackling rise, **an ice wall surges up from the ground** — three feet tall, ten feet wide, two inches thick, crystal-clear with fine internal crystallization patterns, fused with the slab at its base, frost scattering at its foot. Camera: close-up on the palms → pull back to medium for the wall's full presence. **Critical**: must be a single uninterrupted take — splitting kills the "rise from the ground" effect.

## Shot 9 (5s) — 镜头9 (fist meets wall — validation)
Medium shot. Shen Nian raises her fist and drives it straight into the ice wall — a muffled thump, **white frost shrapnel explodes at the point of impact, the wall stands completely intact, not a single crack**. She steps back, hands behind her, nods approvingly. Camera: fist-tracking close-up, 0.3s slow-mo at impact.

## Shot 10 (6s) — 镜头10 (dusk reading)
Medium shot. Shen Nian sits beneath a dead tree at dusk; several yellowed worn ancient books on her lap; she leafs through and her gaze settles on a thin booklet. Cold-insect chirps in the distance, dead leaves rustling. Camera: medium slow push-in to a close-up on the booklet cover.

## Shot 11 (7s) — 镜头11 (the key eight characters)
Close-up on the booklet pages.
- 0-3s: cover reads "Essentials of Demon-Blood Refinement, by Xuanmingzi" in vertical archaic seal-script.
- 3-7s: pages turn — vertical small-script inscriptions glow on ("serpent blood is yin-cold — refines ice arts; tiger blood is yang — strengthens the body; fox blood is yin — refines illusion"); camera pushes in to the eight characters "**同源相生 · 异源相克**" (Same source breeds, opposite source counters), which enlarge and highlight while the rest blurs.
Camera: locked-off close-up, push-in. **Important**: keep the brush-script crisp and legible — write "crisp legible vertical brush-script Chinese characters" into the prompt.

## Shot 12 (6s) — 镜头12 (cheat-tier reveal — gradient payoff)
Close-up on Shen Nian, a faint smile tugging at her lips. The system UI panel fades in again — vertical text "**Myriad-Demon Bloodline · Blood of the Demon Progenitor · Compatible with all attributes · No counter-attribute**" glowing on. **A flash of dark-gold patterns flickers across her wrist** (hint of her cheat-tier bloodline). She closes the booklet; cold satisfaction in her eyes. Camera: locked-off close-up.

## Shot 13 (6s) — 镜头13 (the slip drops — clue)
Over-shoulder → extreme close-up. Shen Nian turns to the booklet's last page — **a yellowed folded paper slip drifts out, rotating slowly downward for 1.5 seconds**; she bends to pick it up, unfolds it slowly. Close-up on the slip: **"Xuantian Pavilion · Third Floor · Hidden Compartment · Pill Formula"** in archaic vertical small-script. Her pupils tighten. Camera: over-shoulder → close-up on the slip's text.

## Shot 14 (7s) — 镜头14 (Xuantian Pavilion vision — dissolve)
Medium shot. Shen Nian stands beneath the dusk dead tree, slip pinched between her fingers, brow tight; her gaze lifts to the far horizon — **a dreamlike dissolve fades in the silhouette of a towering gilt-roofed three-tiered pavilion**, drifting clouds around it, the cold gilt sheen of the roof glowing in the dusk light. Camera: locked medium foreground + slow dissolve-in on the distant pavilion vision.

## Shot 15 (7s) — 镜头15 (hook — overhead pull-back, sunset)
Shen Nian closes the books, tucks the slip into her sleeve, rises from beneath the dead tree. Camera **slowly pulls back and lifts to a high-angle wide shot** — she stands alone at the center of the abandoned back garden, **ten frosted dead trees behind her, the three-foot ice wall still standing nine paces away** — a clear "training crucible". She looks up at a streak of crimson sunset and murmurs about a "thousand-year tiger demon" on the border. Camera: pull back + crane up to high-angle wide, freeze on her silhouette against the sunset.

---
**English subtitle (paired)**: use `字幕_英文.srt` as-is (already timed & localized in ReelShort/TikTok-style spoken English). System lines stay game-style ("Bloodline LV2. EXP 195/500. 305 to next level.", "Myriad-Demon Bloodline · Blood of the Demon Progenitor · Compatible with all attributes · No counter-attribute"). Names fixed: **Shen Nian, Lin Wan'er, Cuiwei, the Empress, Xuantian Pavilion, Calm-Heart Pill, Xuanmingzi (the demon-blood treatise author), thousand-year tiger demon, the cold palace**. Rank terms: "Silver Rank" (银牌妖位).

**Cover image (high-CTR, EN)**: see `封面.md` English prompt — ten ice spikes fanning out before her at dusk, the ice wall still standing nine paces away, Xuantian Pavilion silhouette dissolving in on the horizon under crimson sunset, vertical 9:16.
