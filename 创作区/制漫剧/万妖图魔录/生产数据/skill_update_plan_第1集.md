# skill 更新重制计划 — 第1集

- 作品根：`/Users/lalala/learn/anime-armory/创作区/制漫剧/万妖图魔录`
- 当前阶段：`image_prompt`
- 建议动作：`只重跑 gate/review` · `gate/review` → `image_prompt`
- 需要重制：否
- 重制策略：`最小`

## 当前生产缺口
- 当前待办：`出图prompt`（出图prompt = `⬜`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/lalala/learn/anime-armory/创作区/制漫剧/万妖图魔录 第1集`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：⚠️ 必需执行锚缺失 0/10 Clip；缺尾帧声明 0 Clip；缺 PNG 文件 18 个（普通镜不设默认三帧；backend=`deferred`）

## 备注
- 帧策略合同未达标：必需执行锚缺失 0 个 Clip，缺尾帧声明 0 个 Clip，已声明但 PNG 不存在 18 个。普通镜不设默认三帧；这里只报告 E1/R1-R3/显式 opt-in 或尾帧真缺口。回 n2d-script 跑 `anchor_planner.py <作品根> 第1集 --write` 补齐声明，再回 n2d-image 出 `_mid/_aK/_end` 帧。；缺文件样例：出图/第1集/图片/EP01_CLIP01_a1.png, 出图/第1集/图片/EP01_CLIP04_a1.png, 出图/第1集/图片/EP01_CLIP05_a1.png, 出图/第1集/图片/EP01_CLIP06_a1.png
