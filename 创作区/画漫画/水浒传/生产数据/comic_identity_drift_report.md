# 跨话角色漂移报表

- 扫描 5 话 · 追踪 18 角色 · 有漂移 3 · 含 block 0

| 角色 | 第1话 | 第2话 | 第3话 | 第4话 | 第5话 | 首崩话 |
|---|---|---|---|---|---|---|
| CHAR_ABBOT_SHANGQING | 🟢 | 🟢 |  |  |  | — |
| CHAR_DONG_JIANGSHI |  |  | 🟢 |  |  | — |
| CHAR_DUAN_WANG |  |  | 🟢 | 🟢 |  | — |
| CHAR_EMPEROR_RENZONG | 🟢 | 🟢 |  |  |  | — |
| CHAR_FAN_ZHONGYAN | 🟢 |  |  |  |  | — |
| CHAR_GAO_QIU |  |  | 🟢 | 🟢 | 🟢 | — |
| CHAR_HONG_XIN | 🟢 | 🟢 |  |  |  | — |
| CHAR_MASTER_XUJING | 🟢 |  |  |  |  | — |
| CHAR_SHI_JIN |  |  |  |  | 🟡 | 第5话 |
| CHAR_SHI_TAIGONG |  |  |  |  | 🟢 | — |
| CHAR_SU_XUESHI |  |  | 🟢 |  |  | — |
| CHAR_WANG_DUWEI |  |  | 🟢 |  |  | — |
| CHAR_WANG_JIN |  |  |  | 🟡 | 🟡 | 第4话 |
| CHAR_WANG_MOTHER |  |  |  | 🟢 | 🟡 | 第5话 |
| CHAR_WEN_YANBO | 🟢 |  |  |  |  | — |
| CHAR_ZHAO_ZHE | 🟢 |  |  |  |  | — |
| MON_SNOW_SERPENT | 🟢 |  |  |  |  | — |
| MON_WHITE_TIGER | 🟢 |  |  |  |  | — |

## 修复建议
- CHAR_SHI_JIN：仅 第5话 单话漂移——按该话 identity report 的 rerun_targets 重抽受影响格即可，先不升重资产。
- CHAR_WANG_JIN：第4话、第5话 服装漂移——在 registry.assets 的 outfits 子注册登记该换装（描述+参考图+绝不清单），重抽换装格；锁脸锁不住领型/纽扣/花纹。
- CHAR_WANG_MOTHER：第5话 服装漂移——在 registry.assets 的 outfits 子注册登记该换装（描述+参考图+绝不清单），重抽换装格；锁脸锁不住领型/纽扣/花纹。
