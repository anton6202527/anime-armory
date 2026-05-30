# 冷宫有妖气_第9集_Veo / 海外适配（跨平台落地样例）

> **不变（复用）**：`分镜剧本.md` / 角色卡 / 场景卡。海外投放配 `字幕_英文.srt`（已英化为 ReelShort/TikTok 口语）。
> **只换"视频生成"适配层**：Veo 等海外平台**英文优先**——英文角色锚定句必须稳定复用（人名统一音译），镜头用英文电影术语（dolly in / pan / tracking / orbit / push-in / lock-off / pull back / crane / dissolve / cross-fade / whip-pan）。
> 一致性：先用各角色定妆照英文 prompt（**Emperor Lin Yuan, Zhao An, 16-year-old Lin Wan'er, present-day Shen Nian, Empress Dowager silhouette**）出关键帧 → 作为 image-to-video 首帧。
> EN anchors: **Emperor Yongning (Lin Yuan)** = "33-year-old Emperor of the Great Zhou, imperial-yellow stand-collar wide-sleeved imperial casual robe with dark-gold five-clawed dragon patterns, gold-jade 'yishan' crown with twin upturned wings, sword brows, deep eyes, high nose bridge, sharp thin lips, clean-shaven jaw, cold-pale skin, brow lightly furrowed with weary worry"; **Zhao An** = "35-40-year-old chief shadow-agent, lean upright build, jet-black headcloth, deep-black stand-collar narrow-sleeved combat robe with silver-thread hidden waves, impassive flat-lip face, eyes lowered, soft black boots"; **16-year-old Lin Wan'er (memory)** = "round youthful face with baby fat, double-bun hair with pink pearl flower, vivid pink embroidered new-entry palace robe, shy blush, two faint dimples when she smiles, warm gold filter with yellowed vignetted memory feel"; **present-day Shen Nian** = "worn pale-cyan palace robe, jet-black hair in simple bun with plain silver pin, eyes calm as still water, a faint guileless cold smile, cold sharp filter"; **Empress Dowager silhouette** = "deep-purple phoenix robe and gold-filigree nine-tailed phoenix coronet, hands clasped behind her back, side-silhouette only, never facing camera, gilded soft-glow filter"; scene = "imperial study (Yushufang) with redwood desk, gilt five-clawed dragon screen, sandalwood incense, candle and high-window light, side-wall hidden compartment disguised as carved paneling"; style = "cinematic Chinese ancient-fantasy webcomic, chiaroscuro lighting, vertical 9:16".
> **Episode 9 nature**: male-lead introduction + psychological court intrigue. No combat. Tension carried by **imperial study oppression + warm/cold flashback contrast + vermilion brush writing + hidden compartment mechanism**. Veo's strengths on "atmospheric dialogue scenes + cinematic dissolves + crisp text rendering" fit this episode perfectly.

## Shot/Clip 1 (7s) — 镜头1 (establishing — dynastic burden)
**Video prompt (EN, image-to-video)**: Towering gilt-roof silhouettes of the Forbidden City under heavy dusk; the frame edges dissolve in a vast map of the Great Zhou with red-circled border regions and a thin line of smoke rising from the frontier; the camera slowly cranes forward, passing over palace rooftops toward the high windows of the imperial study. Epic dark-gold tone with faint red smoke accent. Vertical 9:16.

## Shot 2 (6s) — 镜头2 (emperor reads the report)
Behind a redwood imperial desk, Emperor Yongning (Lin Yuan), 33, in imperial-yellow dragon-patterned casual robe with gold-jade crown, sits leafing through a scroll of secret-investigator's report, brow lightly knit; the desk piled with memorials and a cooled cup of tea, the massive gilt coiled-dragon screen behind him, sandalwood smoke catching shafts of late light. Camera: medium slow push-in to a close-up on his face.

## Shot 3 (6s) — 镜头3 (Zhao An kneels and reports)
The chief shadow-agent Zhao An, in deep-black stand-collar combat robe with silver-thread hidden waves at sleeve and hem, kneels on one knee before the desk and presents the report with both hands, eyes lowered, impassive flat-lip face. Camera: locked two-shot medium.

## Shot 4 (6s) — 镜头4 (the emperor massages his temple)
Close-up on the emperor: he sets the report down and lifts his right hand to massage his temple, brow furrowed, a flicker of loneliness and weariness in his eyes, lips tight, a sand-hourglass trickling on the desk behind him. Camera: locked-off close-up.

## Shot 5 (7s) — 镜头5 (the dangerous line)
Close-up over-shoulder. Zhao An hesitates for half a second — eyes flickering — then lowers his voice and speaks. Mid-line cut to the emperor's profile, his lips tightening. As Zhao An reaches the final phrase — "I suspect — she is not the Lady Lin who entered this palace" — a candle pops, the camera lands on the emperor's mouth pressed thin. Camera: over-shoulder → reverse shot. **Critical**: leave 0.5s of dead silence after the line.

## Shot 6 (5s) — 镜头6 (eyelid twitch — micro-expression critical)
Extreme facial close-up on the emperor. His right eyelid **barely twitches** (under 0.3 second), his pupil **subtly contracts**, his lip line tightens; cold realization dawning behind his eyes. Camera: locked extreme close-up, 0.3s slow-mo on the twitch. **Critical for Veo**: write "barely perceptible eyelid twitch, less than 0.3 second, pupil only slightly contracts" — Veo defaults to over-acting facial cues.

## Shot 7 (6s) — 镜头7 (Zhao An's softer cover-line)
Close-up on Zhao An, a small shake of his head, offering a rationalization: her father Lin Huaiyuan once traveled south, encountered "strange people" — perhaps left a survival means to his daughter; in the background, the emperor's brow eases by a fraction. Camera: close-up.

## Shot 8 (7s) — 镜头8 (memory — 16-year-old with dimples)
**Warm gold filter, dream-like with yellowed vignetted edges.** A 16-year-old Lin Wan'er stands in a sunlit imperial palace corridor with her back to camera; she turns slowly, shyly lowers her head, then lifts her eyes toward the camera (the emperor's POV) — **a soft smile breaks, two faint dimples appear**, her cheeks flush pink. Camera: close-up freeze, last 2s slow push-in on the dimples. **Critical**: warm gold filter + yellowed vignetted edges + the two dimples are non-negotiable consistency anchors.

## Shot 9 (6s) — 镜头9 (cut back — the blade reforged)
**Cold sharp filter.** Cut to present-day Shen Nian, in worn pale-cyan palace robe with a plain silver pin, rising from a bow — eyes calm as still water, a faint guileless smile at her lips — utterly unshaken before the empress's presence (in soft-focus background). Camera: close-up freeze, last 2s slow push-in. **Critical**: the Shot 8 → 9 transition is the episode's most important emotional beat — the warm gold must hard-cut to cold sharp with a 0.3s clean cut and a single cold violin note. The color temperature swing carries the meaning.

## Shot 10 (6s) — 镜头10 (the verdict — three knuckle taps)
Medium shot. The emperor sits silent for a long beat; his right index-finger middle knuckle taps the redwood desk in rhythm — **once, twice, three times** — candle light splitting his face half-warm half-cold; then he speaks: keep watching her, don't startle her, daily reports. Zhao An bows in compliance. Camera: locked-off medium. The three knuckle taps must be **rhythmically clear and distinct**.

## Shot 11 (5s) — 镜头11 (the doors close — silence)
The hall doors are silently closed by two pages; Zhao An's figure disappears beyond them; the camera pulls back into the chamber, leaving the emperor alone in the throne, a single candle pop in dead silence. Camera: tracking the doors → pull back to the emperor in wide shot. Use full silence except for door + footstep + candle pop.

## Shot 12 (7s) — 镜头12 (Empress Dowager — golden dissolve)
Close-up on the emperor → a **golden dissolve-vision** fades in over his shoulder: a quiet corner of Cining Palace; the silhouette of the Empress Dowager in deep-purple phoenix robe and gold-filigree nine-tailed phoenix coronet stands with hands clasped behind her back; she **turns her head a fraction** (still not facing camera), her lips just beginning to move, in a gilded soft-glow memory filter. Camera: cross-fade from study close-up to gold-tinted Cining silhouette. **Critical**: silhouette only — never reveal her face this episode; reserve full design for a future episode.

## Shot 13 (5s) — 镜头13 (long sigh, soft murmur)
Close-up on the emperor: a long sigh; his gaze drifts to the closed report on the desk; his fingertip lightly traces the desk surface; he murmurs to himself. Camera: locked-off close-up.

## Shot 14 (7s) — 镜头14 (vermilion brush — the kill-order)
Extreme close-up on the imperial desk. The emperor wields a wolf-hair brush dipped in vermilion ink and writes vertical small-script onto an imperial-yellow silk slip — **"If Lady Lin shows treasonous intent — Captain of the Imperial Guard is to execute on the spot"** — each character appearing crisply over 4-5 seconds; then he lifts an imperial seal and **stamps it down with a heavy "thump"**, leaving a vermilion mark; cut to a half-profile of his face, cold resolve in his eyes. Camera: extreme close-up on the silk → reverse-shot half-profile. **Critical for Veo**: write "crisp legible vertical Chinese brush-script characters, each clearly readable, rich saturated vermilion ink" — Veo defaults to abstract text smudges.

## Shot 15 (8s) — 镜头15 (hidden compartment — the hook)
Extreme close-up on a side wall of the imperial study. The emperor presses a hidden mechanism on what looks like an ordinary carved wooden panel; **the panel silently slides open** to reveal a long narrow hidden compartment, already holding several older vermilion-wax-sealed edicts and a jade casket; he solemnly places the newly sealed imperial-yellow edict inside; the mechanism **silently closes again**, restoring the panel — no outward sign. Pull back to medium: the emperor stands before the now-closed panel, candle shadow flickering half-warm half-cold across his face, murmuring his closing line. Camera: extreme close-up on the mechanism → pull back to medium. **Critical**: "silently slides open and closes, no audible click — the mechanism operates in absolute silence" — Veo defaults to adding click/snap sounds.

---
**English subtitle (paired)**: use `字幕_英文.srt` as-is (already timed & localized in ReelShort/TikTok-style spoken English). Names fixed: **Emperor Yongning, Lin Yuan, Zhao An, Lin Wan'er, Shen Nian, Lin Huaiyuan (her father), the Empress (= Empress Wang from earlier eps), the Empress Dowager, the Imperial Guard, Yushufang (the imperial study), the cold palace, the Forbidden City**. Keep "two dimples", "blade reforged", "a way to survive" as memorable English phrases (they're the episode's emotional payload).

**Cover image (high-CTR, EN)**: see `封面.md` English prompt — the emperor wielding the vermilion brush over the kill-order, with a two-panel flashback overlay on the right (warm 16-year-old with dimples vs cold present-day Shen Nian), three-color collision of dragon-gold / vermilion / warm-pink / cold-cyan, vertical 9:16.
