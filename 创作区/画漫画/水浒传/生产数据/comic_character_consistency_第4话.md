# 漫画角色一致性报告 — 第4话

- 生成时间：2026-07-19T13:42:48
- 结论：warn
- 角色数：4
- 出场绑定：70
- block/warn/info：0 / 3 / 0
- 并排复核图：`生产数据/qa_previews/第4话_character_consistency_contact_sheet.jpg`

## 记录

- CCIP 动漫身份 embedding 不可用（色彩指纹只是代理，换脸同色调会漏报）。建议在独立 venv 安装 dghs-imgutils（pip install dghs-imgutils）后重跑，获得阈值化的同角色判定（threshold=0.178）。
- VLM 并排判定任务包已刷新：生产数据/comic_vlm_judge_tasks_第4话.json（裁决 0/129）；由多模态 agent 看图执行并写回 verdict 文件。
- 已生成角色一致性并排复核图：生产数据/qa_previews/第4话_character_consistency_contact_sheet.jpg

## 角色

| character | refs | panels |
|---|---:|---:|
| CHAR_DUAN_WANG | 3 | 11 |
| CHAR_GAO_QIU | 5 | 31 |
| CHAR_WANG_JIN | 3 | 20 |
| CHAR_WANG_MOTHER | 3 | 8 |

## Findings

| severity | code | character | panel | artifact | reason |
|---|---|---|---|---|---|
| warn | outfit_fingerprint_low | CHAR_WANG_JIN | P027 | 出图/第4话/panels/P027.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.394。这是色彩分布代理，需并排人审。 |
| warn | face_fingerprint_low | CHAR_WANG_JIN | P039 | 出图/第4话/panels/P039.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.495。这是色彩分布代理，需并排人审。 |
| warn | outfit_fingerprint_low | CHAR_WANG_JIN | P042 | 出图/第4话/panels/P042.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.404。这是色彩分布代理，需并排人审。 |
