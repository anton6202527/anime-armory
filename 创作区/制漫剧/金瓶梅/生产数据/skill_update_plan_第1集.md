# skill 更新重制计划 — 第1集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅`
- 当前阶段：`image`
- 建议动作：`只重跑 gate/review` · `gate/review` → `image`
- 需要重制：否
- 重制策略：`最小`

## 当前生产缺口
- 当前待办：`出图`（出图 = `137/179`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅 第1集`

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `24`，降级 `False`
- block 摘要：[production一致性升级:重复同维度] Clip_09：角色 CHAR_WUSONG 相邻镜情绪硬跳（喜→怒/悲/惊）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=9477f3aefd25，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。 | [production一致性升级:重复同维度] Clip_09：角色 CHAR_PANJINLIAN 相邻镜情绪硬跳（喜→怒/悲/惊）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=ff50f685763a，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- 当前应停在/回退：`video` — full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video
- 建议安装：无需补装
- 报告：`/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/image_qc_第1集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：⚠️ 必需执行锚缺失 0/15 Clip；缺尾帧声明 0 Clip；缺 PNG 文件 21 个（普通镜不设默认三帧；backend=`None`）
- **图片一致性**：✅ 无硬阻断（verdict=`review`，精度 `full`）

## 备注
- 帧策略合同未达标：必需执行锚缺失 0 个 Clip，缺尾帧声明 0 个 Clip，已声明但 PNG 不存在 21 个。普通镜不设默认三帧；这里只报告 E1/R1-R3/显式 opt-in 或尾帧真缺口。回 n2d-script 跑 `anchor_planner.py <作品根> 第1集 --write` 补齐声明，再回 n2d-image 出 `_mid/_aK/_end` 帧。；缺文件样例：出图/第1集/图片/EP01_CLIP04_a1.png, 出图/第1集/图片/EP01_CLIP05_a1.png, 出图/第1集/图片/EP01_CLIP05_a2.png, 出图/第1集/图片/EP01_CLIP06_a1.png
