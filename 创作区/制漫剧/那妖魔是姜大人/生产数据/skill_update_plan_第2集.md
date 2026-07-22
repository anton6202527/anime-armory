# skill 更新重制计划 — 第2集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`image_prompt`
- 建议动作：`只重跑 gate/review` · `gate/review` → `image_prompt`
- 需要重制：否
- 重制策略：`最小`

## 当前生产缺口
- 当前待办：`出图prompt`（出图prompt = `⬜`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第2集`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：⚠️ 必需执行锚缺失 0/7 Clip；缺尾帧声明 0 Clip；缺 PNG 文件 14 个（普通镜不设默认三帧；backend=`None`）

## 备注
- 帧策略合同未达标：必需执行锚缺失 0 个 Clip，缺尾帧声明 0 个 Clip，已声明但 PNG 不存在 14 个。普通镜不设默认三帧；这里只报告 E1/R1-R3/显式 opt-in 或尾帧真缺口。回 n2d-script 跑 `anchor_planner.py <作品根> 第2集 --write` 补齐声明，再回 n2d-image 出 `_mid/_aK/_end` 帧。；缺文件样例：出图/第2集/图片/EP02_CLIP01_start_a1.png, 出图/第2集/图片/EP02_CLIP01_start_a2.png, 出图/第2集/图片/EP02_CLIP01_start_a3.png, 出图/第2集/图片/EP02_CLIP02_start_a1.png
