# 同场景 batch-as-video-frames 规划 · 第2集（默认路径·P2b）

- min_group=2 · 4 个 batch · 20 镜成组 · 7 镜独立出
- 说明：同场景连续 ≥min_group 镜默认走时空一致性 batch（共享场景/光位/风格+同源种子）；身份仍按 identity_registry 两层定妆库锁，跨场景切换必断组。

## batch「贺平生杂役小屋/清晨/内」× 6 镜
- clips：Clip_01、Clip_02、Clip_03、Clip_04、Clip_05、Clip_06
- 共享锁：scene_dna、场景光位锚、style_contract、shared_seed
- 同场景连续 6 镜走时空一致性 batch（共享场景/光位/风格+同源种子，一段连贯场景 pass 出这组首帧再拆镜）；身份仍按 identity_registry 锁，不在此 batch 内处理。

## batch「贺平生杂役小屋/清晨/内」× 2 镜
- clips：Clip_08、Clip_09
- 共享锁：scene_dna、场景光位锚、style_contract、shared_seed
- 同场景连续 2 镜走时空一致性 batch（共享场景/光位/风格+同源种子，一段连贯场景 pass 出这组首帧再拆镜）；身份仍按 identity_registry 锁，不在此 batch 内处理。

## batch「杂役饭棚/早晨/外」× 3 镜
- clips：Clip_13、Clip_14、Clip_15
- 共享锁：scene_dna、场景光位锚、style_contract、shared_seed
- 同场景连续 3 镜走时空一致性 batch（共享场景/光位/风格+同源种子，一段连贯场景 pass 出这组首帧再拆镜）；身份仍按 identity_registry 锁，不在此 batch 内处理。

## batch「贺平生杂役小屋/深夜/内」× 9 镜
- clips：Clip_19、Clip_20、Clip_21、Clip_22、Clip_23、Clip_24、Clip_25、Clip_26、Clip_27
- 共享锁：scene_dna、场景光位锚、style_contract、shared_seed
- 同场景连续 9 镜走时空一致性 batch（共享场景/光位/风格+同源种子，一段连贯场景 pass 出这组首帧再拆镜）；身份仍按 identity_registry 锁，不在此 batch 内处理。

## 独立出图（不成组）
- Clip_07（同场景连续镜不足 min_group）
- Clip_10（同场景连续镜不足 min_group）
- Clip_11（同场景连续镜不足 min_group）
- Clip_12（同场景连续镜不足 min_group）
- Clip_16（同场景连续镜不足 min_group）
- Clip_17（同场景连续镜不足 min_group）
- Clip_18（同场景连续镜不足 min_group）
