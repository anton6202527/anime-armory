# 跨集角色漂移报表

- root: .
- generated_at: 2026-07-26T08:48:03+00:00
- available: True


| 角色 | first_bad_episode | total_warn | total_block | episodes |
|---|---|---|---|---|
| CHAR_01__囚途残损态 | 第2集 | 20 | 3 | 第1集: ok 14 / warn 15 / block 0; 第2集: ok 18 / warn 5 / block 3 |
| CHAR_02__濒死重伤态 | 第1集 | 0 | 3 | 第1集: ok 0 / warn 0 / block 3; 第2集: ok 0 / warn 0 / block 0 |

## 跨集 embedding 漂移（质心 vs 锚点，逐集偏离）

> 即使每集各自过 floor，整体相对建立集的脸质心若逐集下滑也是跨集漂移；high=掉幅≥0.15 或本集均值<0.45。

| 角色 | 从 | 到 | from_mean | to_mean | 掉幅 | 严重度 |
|---|---|---|---|---|---|---|
| CHAR_02__濒死重伤态 | 第1集 | 第2集 | 0.4432 | 0.596 | -0.1528 | medium |

## LoRA 升档建议

- **姜月初**（CHAR_01 / “囚途残损态”）：2 集脸部相似度低于阈值（第1集,第2集）；first_bad_episode=第2集（出现过 block 级漂移）；LoRA status=not_needed，reference_group/原生主体未压住跨集漂移；中间档建议：先挂 face_embedding（IP-Adapter FaceID 等免训练脸嵌入锁，比 LoRA 快/省），仍漂再升 LoRA
  - next: `python3 skills/n2d-lora/scripts/lora.py init '.' --character-id CHAR_01 --form '“囚途残损态”'`
- **裴长青**（CHAR_02 / “濒死重伤态”）：first_bad_episode=第1集（出现过 block 级漂移）；LoRA status=not_needed，reference_group/原生主体未压住跨集漂移；中间档建议：先挂 face_embedding（IP-Adapter FaceID 等免训练脸嵌入锁，比 LoRA 快/省），仍漂再升 LoRA
  - next: `python3 skills/n2d-lora/scripts/lora.py init '.' --character-id CHAR_02 --form '“濒死重伤态”'`
