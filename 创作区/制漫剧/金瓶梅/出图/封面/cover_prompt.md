# 作品封面 prompt 包 — 金瓶梅

- 竖版比例：9:16（可接受 5:7）
- 生图模型（C5 生成者）：GPT Image 2
- 生图渠道 / 访问入口（access path）：Codex CLI / Codex
- 输出路径：出图/封面/cover.png
- 当前 _meta.cover：None

## 身份锚（B7/B9）

- 承载角色：CHAR_WUSONG/28岁打虎态（武松）
- 同源脸锚：`出图/共享/图片/定妆_CHAR_WUSONG__28岁打虎态.png` · ready=False
- reference_group：`出图/共享/identity_registry.json#characters[CHAR_WUSONG]/forms/28岁打虎态/reference_group`
- ⚠ render 前置缺口：missing_ready_face_anchor（渲染前须由出图 runner 先补 ready 脸锚）

## Prompt（中文）

竖版作品封面（9:16，可接受 5:7），高点击率短剧封面。主角 武松（CHAR_WUSONG/28岁打虎态）清晰正脸、强情绪，脸型/眼距/发型/服装配色严格同源锚：`浓直眉深目·方颌短髭·宽肩精壮·深靛都头窄袖·旧皮护腕`。画面承载本剧核心卖点：一桩被钱权压下的命案，撬开清河县豪门百回兴亡：每一次欲望都变成交易，每一次交易都留下终将反噬的债。。构图为标题预留上/下安全留白，主体不顶格；电影级布光、强对比、情绪张力拉满。严禁任何文字、字幕、水印、Logo、平台角标（标题由排版层后叠）。继承本剧 style_contract / identity_registry / asset_registry 视觉锚，不得漂移。

## Prompt（English）

Vertical key-visual cover (9:16, 5:7 acceptable), high-CTR short-drama poster. Protagonist clear frontal face, strong emotion, identity locked to the registered face anchor (same face/hair/wardrobe).Carries the show's core hook: 一桩被钱权压下的命案，撬开清河县豪门百回兴亡：每一次欲望都变成交易，每一次交易都留下终将反噬的债。. Leave title-safe margins top/bottom, cinematic lighting, high contrast, strong emotion. No text, no subtitles, no watermark, no logo, no platform badge. Inherit the show's style_contract / identity anchors; no drift.

## 负向

文字/字幕/水印/Logo/角标/多余肢体/崩脸/串脸/风格漂移

## 合规 / 降级留痕

无成本 writer：本包只产 prompt/job + 留痕，未生成 PNG、未调后端。在装好生图后端/凭证的机器上，用既有 n2d 出图 runner 按本包 prompt 渲染竖版封面；渲染并人审通过后跑 `cover_pack.py <root> --backfill-cover` 回填 _meta.json 的 cover。_meta.json 的 cover 在真正渲染出 PNG 前保持 null（C4/B4）。
