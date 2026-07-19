# 跨话角色漂移报表

- 扫描 6 话 · 追踪 18 角色 · 有漂移 4 · 含 block 0

| 角色 | 第1话 | 第2话 | 第3话 | 第4话 | 第5话 | 第6话 | 首崩话 |
|---|---|---|---|---|---|---|---|
| CHAR_ABBOT_SHANGQING | 🟢 | 🟢 |  |  |  |  | — |
| CHAR_DONG_JIANGSHI |  |  | 🟢 |  |  |  | — |
| CHAR_DUAN_WANG |  |  | 🟢 | 🟢 |  |  | — |
| CHAR_EMPEROR_RENZONG | 🟢 | 🟢 |  |  |  |  | — |
| CHAR_FAN_ZHONGYAN | 🟢 |  |  |  |  |  | — |
| CHAR_GAO_QIU |  |  | 🟢 | 🟢 | 🟢 |  | — |
| CHAR_HONG_XIN | 🟢 | 🟢 |  |  |  |  | — |
| CHAR_MASTER_XUJING | 🟢 |  |  |  |  |  | — |
| CHAR_SHI_JIN |  |  |  |  | 🟡 | 🟡 | 第5话 |
| CHAR_SHI_TAIGONG |  |  |  |  | 🟢 | 🟡 | 第6话 |
| CHAR_SU_XUESHI |  |  | 🟢 |  |  |  | — |
| CHAR_WANG_DUWEI |  |  | 🟢 |  |  |  | — |
| CHAR_WANG_JIN |  |  |  | 🟡 | 🟡 | 🟡 | 第4话 |
| CHAR_WANG_MOTHER |  |  |  | 🟢 | 🟡 | 🟢 | 第5话 |
| CHAR_WEN_YANBO | 🟢 |  |  |  |  |  | — |
| CHAR_ZHAO_ZHE | 🟢 |  |  |  |  |  | — |
| MON_SNOW_SERPENT | 🟢 |  |  |  |  |  | — |
| MON_WHITE_TIGER | 🟢 |  |  |  |  |  | — |

## 修复建议
- CHAR_SHI_JIN：跨 2 话反复漂移（第5话、第6话）——补专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可本线外训练后把产出登记为 registry 参考。
- CHAR_SHI_TAIGONG：第6话 服装漂移——在 registry.assets 的 outfits 子注册登记该换装（描述+参考图+绝不清单），重抽换装格；锁脸锁不住领型/纽扣/花纹。
- CHAR_WANG_JIN：第4话、第5话、第6话 服装漂移——在 registry.assets 的 outfits 子注册登记该换装（描述+参考图+绝不清单），重抽换装格；锁脸锁不住领型/纽扣/花纹。
- CHAR_WANG_MOTHER：第5话 服装漂移——在 registry.assets 的 outfits 子注册登记该换装（描述+参考图+绝不清单），重抽换装格；锁脸锁不住领型/纽扣/花纹。
