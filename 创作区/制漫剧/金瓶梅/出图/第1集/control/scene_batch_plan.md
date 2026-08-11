# 同场景 batch-as-video-frames 规划 · 第1集（默认路径·P2b）

- min_group=2 · 3 个 batch · 11 镜成组 · 4 镜独立出
- 说明：同场景连续 ≥min_group 镜默认走时空一致性 batch（共享场景/光位/风格+同源种子）；身份仍按 identity_registry 两层定妆库锁，跨场景切换必断组。

## batch「景阳冈夜间空地」× 3 镜
- clips：Clip_01、Clip_02、Clip_03
- 共享锁：scene_dna、场景光位锚、style_contract、shared_seed
- 同场景连续 3 镜走时空一致性 batch（共享场景/光位/风格+同源种子，一段连贯场景 pass 出这组首帧再拆镜）；身份仍按 identity_registry 锁，不在此 batch 内处理。

## batch「阳谷街面与武大家楼窗」× 2 镜
- clips：Clip_04、Clip_05
- 共享锁：scene_dna、场景光位锚、style_contract、shared_seed
- 同场景连续 2 镜走时空一致性 batch（共享场景/光位/风格+同源种子，一段连贯场景 pass 出这组首帧再拆镜）；身份仍按 identity_registry 锁，不在此 batch 内处理。

## batch「武大家楼屋雪夜」× 6 镜
- clips：Clip_06、Clip_07、Clip_08、Clip_09、Clip_10、Clip_11
- 共享锁：scene_dna、场景光位锚、style_contract、shared_seed
- 同场景连续 6 镜走时空一致性 batch（共享场景/光位/风格+同源种子，一段连贯场景 pass 出这组首帧再拆镜）；身份仍按 identity_registry 锁，不在此 batch 内处理。

## 独立出图（不成组）
- Clip_12（同场景连续镜不足 min_group）
- Clip_13（同场景连续镜不足 min_group）
- Clip_14（同场景连续镜不足 min_group）
- Clip_15（同场景连续镜不足 min_group）
