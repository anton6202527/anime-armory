# skill 更新重制计划 — 第1集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`video`
- 建议动作：`重制` · `video_prompt` → `video`
- 需要重制：是
- 重制策略：`最小`
- 变动 skill：n2d-video

## 变动文件
- `skills/n2d-video/scripts/video_runner.py`

## 当前生产缺口
- 当前待办：`图生视频`（视频 = `⬜`）
- 建议 skill：`n2d-video`
- 建议命令：`n2d-video /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集`

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `42`，降级 `False`
- block 摘要：发型(H1): 图片/Clip02_first.png | 发型(H1): 图片/Clip05_first.png
- 当前应停在/回退：`video` — full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video
- 建议安装：无需补装
- 报告：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/image_qc_第1集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：✅ 达标（需执行锚 8 Clip；普通镜模式=risk_only）
- **图片一致性**：✅ 无硬阻断（verdict=`review`，精度 `full`）
- **契约继承**：✅ 已继承（verdict=`pass`）

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" --episodes 1 --rerun-from video_prompt --scope "skill 更新后重制到 video" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-video /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集`

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
