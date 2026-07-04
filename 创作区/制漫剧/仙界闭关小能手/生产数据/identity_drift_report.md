# 跨集角色漂移报表

- root: 创作区/制漫剧/仙界闭关小能手
- generated_at: 2026-07-04T04:14:36+00:00
- available: True


| 角色 | first_bad_episode | total_warn | total_block | episodes |
|---|---|---|---|---|
| 张老大 | - | 0 | 0 | 第1集: ok 6 / warn 0 / block 0; 第2集: ok 10 / warn 0 / block 0 |
| 贺平生 | 第1集 | 8 | 4 | 第1集: ok 49 / warn 7 / block 4; 第2集: ok 29 / warn 1 / block 0 |

## LoRA 升档建议

- **贺平生**（CHAR_HE_PINGSHENG / 常态）：2 集脸部相似度低于阈值（第1集,第2集）；first_bad_episode=第1集（出现过 block 级漂移）；LoRA status=not_needed，reference_group/原生主体未压住跨集漂移；中间档建议：先挂 face_embedding（IP-Adapter FaceID 等免训练脸嵌入锁，比 LoRA 快/省），仍漂再升 LoRA
  - next: `python3 skills/n2d-lora/scripts/lora.py init '创作区/制漫剧/仙界闭关小能手' --character-id CHAR_HE_PINGSHENG --form '常态'`
