# skill 更新重制计划 — 第1集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔`
- 当前阶段：`script_stage2`
- 建议动作：`重制` · `script_stage1` → `script_stage2`
- 需要重制：是
- 重制策略：`最小`
- 变动 skill：n2d, n2d-script

## 变动文件
- `skills/n2d-script/scripts/motif_detector.py`
- `skills/n2d/SKILL.md`

## 当前生产缺口
- 当前待办：`阶段2·分镜设计`（分镜设计 = `⬜`）
- 建议 skill：`n2d-script`
- 建议命令：`n2d-script /Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔 第1集  (配音后定稿)`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：⚠️ 必需执行锚缺失 0/13 Clip；缺尾帧声明 0 Clip；缺 PNG 文件 24 个（普通镜不设默认三帧；backend=`None`）

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔" --episodes 1 --rerun-from script_stage1 --scope "skill 更新后重制到 script_stage2" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-script /Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔 第1集`

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
- 帧策略合同未达标：必需执行锚缺失 0 个 Clip，缺尾帧声明 0 个 Clip，已声明但 PNG 不存在 24 个。普通镜不设默认三帧；这里只报告 E1/R1-R3/显式 opt-in 或尾帧真缺口。回 n2d-script 跑 `anchor_planner.py <作品根> 第1集 --write` 补齐声明，再回 n2d-image 出 `_mid/_aK/_end` 帧。；缺文件样例：出图/第1集/图片/EP01_CLIP01_a1.png, 出图/第1集/图片/EP01_CLIP02_a1.png, 出图/第1集/图片/EP01_CLIP03_a1.png, 出图/第1集/图片/EP01_CLIP04_a1.png
