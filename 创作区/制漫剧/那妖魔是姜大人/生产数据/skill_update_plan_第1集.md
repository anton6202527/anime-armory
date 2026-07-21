# skill 更新重制计划 — 第1集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`script_stage2`
- 建议动作：`只重跑 gate/review` · `gate/review` → `script_stage2`
- 需要重制：否
- 重制策略：`最小`
- 新纳入范围（不计变更）：n2d-voice

## 当前生产缺口
- 当前待办：`阶段2·分镜设计`（字幕中 = `⬜`）
- 建议 skill：`n2d-script`
- 建议命令：`n2d-script /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集  (配音后定稿)`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：⚠️ 必需执行锚缺失 0/8 Clip；缺尾帧声明 0 Clip；缺 PNG 文件 13 个（普通镜不设默认三帧；backend=`None`）

## 备注
- 基线为 check 自动建立的临时基线（bootstrap）：从这一刻起能检测变更，但看不到此前已用过的更早 skill 版本所致的差异。确认当前产物可接受后，请 `record` 固化为正式基线（清除临时标记）。
- n2d-voice 因阶段推进首次纳入相关范围，本次不计为变更；该阶段完成后请 record 刷新基线。
- 帧策略合同未达标：必需执行锚缺失 0 个 Clip，缺尾帧声明 0 个 Clip，已声明但 PNG 不存在 13 个。普通镜不设默认三帧；这里只报告 E1/R1-R3/显式 opt-in 或尾帧真缺口。回 n2d-script 跑 `anchor_planner.py <作品根> 第1集 --write` 补齐声明，再回 n2d-image 出 `_mid/_aK/_end` 帧。；缺文件样例：出图/第1集/图片/EP01_CLIP01_a1.png, 出图/第1集/图片/EP01_CLIP02_a1.png, 出图/第1集/图片/EP01_CLIP03_a1.png, 出图/第1集/图片/EP01_CLIP04_a1.png
