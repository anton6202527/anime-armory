# 漫画角色一致性报告 — 第1话

- 生成时间：2026-07-16T01:33:07
- 结论：pass
- 角色数：3
- 出场绑定：55
- block/warn/info：0 / 0 / 0
- 并排复核图：`生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg`

## 记录

- CCIP 动漫身份 embedding 不可用（色彩指纹只是代理，换脸同色调会漏报）。建议在独立 venv 安装 dghs-imgutils（pip install dghs-imgutils）后重跑，获得阈值化的同角色判定（threshold=0.178）。
- VLM 并排判定任务包已刷新：生产数据/comic_vlm_judge_tasks_第1话.json（裁决 0/93）；由多模态 agent 看图执行并写回 verdict 文件。
- 已生成角色一致性并排复核图：生产数据/qa_previews/第1话_character_consistency_contact_sheet.jpg

## 角色

| character | refs | panels |
|---|---:|---:|
| CHAR_JIANG_YUECHU | 6 | 25 |
| CHAR_PEI_CHANGQING | 3 | 21 |
| MON_TIGER_SHANSHEN | 5 | 9 |

## Findings

- 未发现角色一致性阻断或警告。
