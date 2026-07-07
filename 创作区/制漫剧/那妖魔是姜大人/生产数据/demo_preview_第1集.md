# 第1集 Demo 预览包

- 状态：ready_for_human_demo_preview
- 用途：自用 demo / 学习预览；不是正式验收，不回写验收通过。
- 最终母版：`合成/第1集/成片_第1集_zh.mp4`
- 时长/画幅：120.1s / 1080x1920
- SHA256：`aa6392dcc6fc030ee1d887da388fa2fd7b84b860f7843b2ea92dcfb8464b8ccb`
- 抽帧目录：`生产数据/demo_preview_frames/第1集`
- contact sheet：`生产数据/demo_preview_contact_sheet_第1集.jpg`

## 现有账本只作参考

- release_verdict：blocked / profile=demo / summary={"block": 5, "pass": 11, "warn": 2}
- score：80/85 / fail
- final_timeline_probe：pass

## 人工观看清单

- [ ] 完整观看最终母版，不跳看，记录影响理解或观感的 timecode。
- [ ] 前 15 秒能否看懂冲突、身份悬念和继续看的理由。
- [ ] 旁白/对白是否清楚；是否有双人声、爆音、突然变声或明显环境噪声。
- [ ] 字幕不挡脸、不挡关键动作，节奏上来得及读。
- [ ] 主角、核心妖魔、飞鹰门人是否出现一眼可见的换脸/换装/形体跳变。
- [ ] 近景脸不像同一角色时，记录 timecode，并用 `video_face_drift_watch.py` 生成密集抽帧拼版，不只依赖逐 Clip 中点抽样。
- [ ] Clip06/Clip10 等动作爽点是否能看清出手、命中、反馈。
- [ ] 相邻 clip 接缝是否突兀闪切，时间/空间关系是否能顺着看。
- [ ] 结尾是否留出继续看第2集的疑问或爽点承诺。

## 人工观感记录

- 2026-07-07：部分镜头有重复生成感；表达内心戏/心理反应时，不必继续清晰展示其他人、妖魔或道具。后续若返工，优先把这类镜头改成主焦点 CU/MCU、眼神/手部/光影符号，其他实体转画外、虚焦剪影、记忆符号或禁入。
- 2026-07-07：00:01:19.25-00:01:21.50（Clip_06 尾段）出现主角近景脸漂；证据见 `生产数据/video_face_drift_watch_第1集_78.00_82.75s.jpg`。若修样片，回 `n2d-image` 补同源近景锚帧/表情参考或改成保真反应镜，再只重跑受影响视频与合成。

## 抽帧点

- opening: 0.8s (start hook)
- EP01_CLIP01_mid / EP01_CLIP01: 4.602s (clip midpoint)
- EP01_CLIP02_mid / EP01_CLIP02: 17.461s (clip midpoint)
- EP01_CLIP03_mid / EP01_CLIP03: 35.061s (clip midpoint)
- EP01_CLIP04_mid / EP01_CLIP04: 49.392s (clip midpoint)
- EP01_CLIP05_mid / EP01_CLIP05: 60.856s (clip midpoint)
- EP01_CLIP06_mid / EP01_CLIP06: 74.598s (clip midpoint)
- EP01_CLIP07_mid / EP01_CLIP07: 87.446s (clip midpoint)
- EP01_CLIP08_mid / EP01_CLIP08: 97.304s (clip midpoint)
- EP01_CLIP09_mid / EP01_CLIP09: 106.56s (clip midpoint)
- EP01_CLIP10_mid / EP01_CLIP10: 114.795s (clip midpoint)
- EP01_CLIP11_mid / EP01_CLIP11: 119.078s (clip midpoint)
- tail: 119.5s (ending hook)

## 生产/公开发布债务

- 当前包按 internal_only / demo 学习用途生成，不要求公开发布或付费投放级通过。
- 若转 production / 公开发布 / 付费投放，再补 DINOv2+SyncNet、scene_embed DINOv2、resident_presence OWLv2、VLM video judge。
- 若转公开发布，再补显式 AI 标签、目标平台审核/备案/本地化合规，并重跑 gate、score、ledger、review-ui、release_verdict。
- 本包不是 n2d-review 正式验收，不回写验收通过。
