# 跨集角色漂移报表

- root: 创作区/制漫剧/那妖魔是姜大人
- generated_at: 2026-07-29T12:48:48+00:00
- available: True


| 角色 | first_bad_episode | total_warn | total_block | episodes |
|---|---|---|---|---|
| CHAR_01__囚途残损态 | - | 15 | 0 | 第1集: ok 14 / warn 15 / block 0; 第2集: ok 26 / warn 0 / block 0; 第3集: ok 3 / warn 0 / block 0 |
| CHAR_01__镇魔司制服态 | - | 0 | 0 | 第3集: ok 14 / warn 0 / block 0 |
| CHAR_02__濒死重伤态 | - | 0 | 0 | 第1集: ok 3 / warn 0 / block 0; 第2集: ok 0 / warn 0 / block 0 |
| CHAR_03__常态 | - | 0 | 0 | 第3集: ok 3 / warn 0 / block 0 |

## 跨集 embedding 漂移（质心 vs 锚点，逐集偏离）

> 即使每集各自过 floor，整体相对建立集的脸质心若逐集下滑也是跨集漂移；high=掉幅≥0.15 或本集均值<0.45。

| 角色 | 从 | 到 | from_mean | to_mean | 掉幅 | 严重度 |
|---|---|---|---|---|---|---|
| CHAR_02__濒死重伤态 | 第1集 | 第2集 | 0.4424 | 0.5944 | -0.152 | medium |
