# 冷宫有妖气_第6集_Veo / 海外适配（跨平台落地样例）

> **不变（复用）**：`分镜剧本.md` / 角色卡 / 场景卡。海外投放配 `字幕_英文.srt`（已英化为 ReelShort/TikTok 口语）。
> **只换"视频生成"适配层**：Veo 等海外平台**英文优先**——英文角色锚定句必须稳定复用（人名统一音译），镜头用英文电影术语（dolly in / pan / tracking / orbit / crane / push-in / lock-off），运动写进 prompt（多数版本无独立负面框，负面改为正向描述或省略）。
> 一致性：先用各角色定妆照英文 prompt（皇后/李尚宫/翠微首次必出）出关键帧 → 作为 image-to-video 首帧。
> EN anchors: **Shen Nian / Lin Wan'er (presentable form)** = "worn but dignified pale-cyan robe, simple bun with a plain silver pin, calm and cold, no demonic aura"; **Empress Wang** = "nine-tailed gold-phoenix coronet, deep-crimson gold-phoenix-embroidered robe, gold nail guards, phoenix-screen behind her"; **Senior Matron Li** = "deep-purple First-Rank matron's robe, square jet-black bun with a plain gold pin, matron's waist token and brass keys"; **Cuiwei (disguised)** = "jade-green narrow-sleeved maid robe, low chignon with a jade-green band, demure phoenix eyes, cold-pale skin"; **Cuiwei (aura-visible)** = "faint dark-green demonic aura coiling like smoke around her body, pupils faintly glowing green in the shadow"; scenes = "long imperial corridor / Kunning Palace main hall with phoenix-screen / dim cold-palace bedchamber"; style = "cinematic Chinese ancient-fantasy webcomic, chiaroscuro lighting, vertical 9:16".
> **Episode 6 is dialogue-driven** — minimal action; tension is carried by gaze, micro-expressions, costume contrast, and one big beat (teacup smash). Default camera = locked-off or slow dolly. Veo's strength on "atmosphere + acting" fits this episode well.

## Shot/Clip 1 (8s) — 镜头1+2
**Video prompt (EN, image-to-video)**: Outside the heavy iron gate of a derelict cold palace, Senior Matron Li in a deep-purple First-Rank robe stands solemnly at the front, four maids and two eunuchs lined up behind her in stiff formation; she half-unfurls an imperial-yellow silk edict from her wide sleeve and speaks. Camera: low-angle medium shot, slow dolly in. Wind catches a sleeve corner. Cinematic chiaroscuro, vertical 9:16.

## Shot 2 (6s) — 镜头3
Inside the dim cold-palace bedchamber, a young maid Xiao He, tear-rimmed eyes and pale face, secretly clutches Shen Nian's sleeve and whispers urgently; Shen Nian, half-profile, presses her lips and answers in a calm low voice. Camera: two-shot, slight handheld, almost still. Dim candlelight.

## Shot 3 (6s) — 镜头4 (mirror transformation, gradient strong-suit)
At an old bronze mirror, Shen Nian sheds her coarse-cloth robe and dons a worn but dignified pale-cyan palace robe, ties her long black hair into a simple bun and slides in a plain silver pin; the reflection in the bronze mirror transforms from a haggard deposed concubine to a composed, presentable lady with a faint cold smile. Camera: slow push-in on the mirror.

## Shot 4 (8s) — 镜头5
A long imperial palace corridor stretching deep — towering vermilion walls with imperial-yellow tiles, the near end worn and bleak, the far end (toward Kunning Palace) clean and imposing with yellow lantern poles; the procession walks through — Matron Li in deep-purple leading, Shen Nian in pale-cyan in the middle, Xiao He in green at the back. Camera: long-lens deep wide shot, gentle tracking from the side. Slanting afternoon light, deep shadows from the walls.

## Shot 5 (6s) — 镜头6 (forbidden-art omen)
Shen Nian steps through the gilded threshold of Kunning Palace; sandalwood smoke curls in shafts of light; a translucent jade-green UI panel flickers before her eyes for one second with vertical seal-script glyphs reading "Forbidden-art residue detected — nature unknown — marked"; in the shadowed corners of the hall, barely-visible grey-black sinister wisps creep along the wall base. Camera: first-person POV → close over-shoulder. Keep the wisps subtle, almost imperceptible.

## Shot 6 (6s) — 镜头7 (first meeting the Empress)
Deep inside the main hall — Empress Wang, 28, seated on a redwood phoenix throne, wears a nine-tailed gold-phoenix coronet with pearl tassels, a deep-crimson cross-collar robe embroidered with gold phoenixes, a massive gilt nine-tailed phoenix-screen behind her, sandalwood smoke catching the light; Shen Nian walks in and kneels in salute, wide sleeve sweeping the floor. The Empress wears a faint knowing smile. Camera: wide shot slowly dollying in to a medium on the Empress.

## Shot 7 (6s) — 镜头8+9 (teacup smash, emotional peak)
The Empress sips from a white porcelain teacup, gold nail guards clinking softly against the rim, and speaks with a faint smile that hides a knife; then her eyes go knife-cold and she slams the teacup down onto the redwood table — the porcelain cracks with a sharp burst, tea splashes, her wide sleeve and pearl tassels sway from the force. Camera: medium on the Empress, 0.4s slow-motion at the moment of impact. Crimson-gold lighting with a sharp cold accent.

## Shot 8 (6s) — 镜头10+11 (riposte → fake smile, the twist)
Shen Nian tilts her head ever so slightly, her eyes calm as still water, the faintest guileless smile at her lips — completely unreadable; the Empress holds her gaze for a long beat, then suddenly breaks into a beautiful smile — more terrifying than her anger — and gestures for Matron Li. Camera: shot-reverse-shot, then medium on the Empress for the smile transition. Make the smile arrival visibly unnatural.

## Shot 9 (7s) — 镜头12 (Cuiwei + aura reveal, gradient strong-suit)
Outside the gilt phoenix doors of Kunning Palace, Matron Li steps aside and a young palace maid, Cuiwei, in a jade-green narrow-sleeved robe, slim oval face and demure phoenix eyes, curtsies with downcast gaze; Shen Nian glances back — the frame dissolves into a semi-transparent "aura vision": a faint dark-green demonic aura coils around Cuiwei's body like wisps of smoke, her pupils faintly glowing green in the shadow. A small knowing smile crosses Shen Nian's lips. Camera: medium → close-up cross-dissolve.

## Shot 10 (7s) — 镜头13
Back in the cold-palace bedchamber at dusk, Shen Nian quietly shuts the door and lowers her voice to Xiao He; through a window we can see Cuiwei's back disappearing into a side room. Xiao He's eyes go wide, she inhales sharply. Shen Nian stays composed. Camera: locked-off two-shot.

## Shot 11 (8s) — 镜头14 (the night sentinel — eerie stillness, **anti-motion shot**)
Deep night outside the bedchamber door — Cuiwei stands utterly motionless, like a wooden post, moonlight cutting her in half (one side in shadow, one side cold-pale); her hair and robe are completely still; **no audible breath, no blinking**; her pupils faintly glow green in the shadow. She just listens. After a long beat, she silently turns and walks away. Camera: locked-off medium, an almost imperceptible slow creep-in. **Critical for Veo**: write "motionless, no breath, no blinking, hair and robe completely still, no swaying" into the prompt to suppress Veo's default tendency to animate. A single autumn leaf drifts past in the distance — that is the only motion.

## Shot 12 (7s) — 镜头15 (hook)
Inside the bed-canopy: Shen Nian, through the gauze, watches the motionless silhouette at the door — her eyes narrow, a faint cold smile at the corner of her lips; the silhouette finally turns and silently leaves. She rolls over to face the wall and closes her eyes, freezing on her profile. Camera: over-shoulder from inside the canopy → close-up on her face, slow push-in then freeze. Eerie cold-string single note as outro.

---
**English subtitle (paired)**: use `字幕_英文.srt` as-is (already timed & localized in ReelShort/TikTok-style spoken English). System line stays game-style ("Forbidden-art residue detected. Nature unknown. Marked."). Names fixed: **Shen Nian, Lin Wan'er, the Empress, Matron Li, Cuiwei, Madam Liu (from ep.1)**. Cold palace = "cold palace" (literal); Kunning Palace = "Kunning Palace" (keep as proper noun).

**Cover image (high-CTR, EN)**: see `封面.md` English prompt — Empress smashing the teacup vs Shen Nian kneeling with a hidden cold smile, opulent red-gold vs cold pale-cyan contrast, vertical 9:16.
