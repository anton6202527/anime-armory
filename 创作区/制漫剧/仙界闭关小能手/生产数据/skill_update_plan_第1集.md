# skill 更新重制计划 — 第1集

- 作品根：`/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手`
- 当前阶段：`image`
- 建议动作：`只重跑 gate/review` · `gate/review` → `image`
- 需要重制：否
- 重制策略：`最小`

## 当前生产缺口
- 当前待办：`出图返修`（出图 = `36/51`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手 第1集`
- 备注：image_qc=block，hard_blocks=3；先修复报告阻断并重跑 image_qc：/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/image_qc_第1集.md

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniconda/base/bin/python3`
- 当前 image_qc：`verdict=block`，硬阻断 `3`，非阻断初筛 `11`，降级 `False`
- block 摘要：prompt lint:  脸部锚弱信噪比 CHAR_01/本集为14岁杂役常态「face_anchor」（出图/共享/图片/定妆_CHAR_01__本集为14岁杂役常态_表情_六联表.png）：脸占画面仅 2%（建议 ≥30%，核心角教头线 ≥20%）；裁切短边 941px（建议 ≥1024px，核心角教头线 ≥1024px）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。 | prompt lint:  脸部锚弱信噪比 CHAR_01/本集为14岁杂役常态「face_anchor」（出图/共享/图片/定妆_CHAR_01__本集为14岁杂役常态_表情_六联表.png）：脸占画面仅 2%（建议 ≥30%，核心角教头线 ≥20%）；裁切短边 941px（建议 ≥1024px，核心角教头线 ≥1024px）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。 | prompt lint:  脸部锚弱信噪比 CHAR_01/本集为14岁杂役常态「六联表」（出图/共享/图片/定妆_CHAR_01__本集为14岁杂役常态_表情_六联表.png）：脸占画面仅 2%（建议 ≥30%，核心角教头线 ≥20%）；裁切短边 941px（建议 ≥1024px，核心角教头线 ≥1024px）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
- 当前应停在/回退：`image` — image_qc 有硬阻断，需修复/重抽受影响镜头后重跑
- 建议安装：无需补装
- 报告：`/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/image_qc_第1集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：⚠️ 必需执行锚缺失 0/7 Clip；缺尾帧声明 0 Clip；缺 PNG 文件 9 个（普通镜不设默认三帧；backend=`seedance-2.0`）
- **图片一致性**：⚠️ hard_blocks=3（verdict=`block`，精度 `full`）

## 备注
- 帧策略合同未达标：必需执行锚缺失 0 个 Clip，缺尾帧声明 0 个 Clip，已声明但 PNG 不存在 9 个。普通镜不设默认三帧；这里只报告 E1/R1-R3/显式 opt-in 或尾帧真缺口。回 n2d-script 跑 `anchor_planner.py <作品根> 第1集 --write` 补齐声明，再回 n2d-image 出 `_mid/_aK/_end` 帧。；缺文件样例：出图/第1集/图片/EP01_CLIP02_a1.png, 出图/第1集/图片/EP01_CLIP02_a2.png, 出图/第1集/图片/EP01_CLIP03_a1.png, 出图/第1集/图片/EP01_CLIP04_a1.png
- 图片一致性存在硬阻断（image_qc verdict=block，hard_blocks=3）：见 `/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/image_qc_第1集.md`，崩脸/服装/场景/接缝需重出受影响镜。
