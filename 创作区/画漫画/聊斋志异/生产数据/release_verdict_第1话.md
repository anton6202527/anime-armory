# 漫画发布裁决 — 第1话

- profile: internal
- verdict: pass

## 机检结论（review gate 真相区块——任何「验收通过」叙事必须引用本区块，不得只写 pass）

- review receipt verdict: **warn**（block 0 / warn 101 / info 9）

## Delivery states

- technical_complete: True
- production_complete: True
- publish_ready_internal: True
- publish_ready_digital: False
- publish_ready_print: False
- publish_ready_commercial: False

## Issues

- platform_profile_unverified: 自定义(红果式移动端节奏内审，不作为发布平台规格) 平台规格未有当前可机检的一手尺寸证据。 修复：发布/商用前在平台后台或官方文档核验宽度、高度、格式、文件大小，并更新 platform profile。
- release_acceptance_missing: 发布候选缺 SHA 绑定的人工签收。
- source_status_unverified: source_status=original_or_user_provided；公开/印刷/商用交付必须显式声明原创、自有、公版、已授权、开源许可或不适用。
- font_status_unverified: font_status=pending_before_publish；公开/印刷/商用交付必须显式声明原创、自有、公版、已授权、开源许可或不适用。
- asset_status_unverified: asset_status=pending_before_publish；公开/印刷/商用交付必须显式声明原创、自有、公版、已授权、开源许可或不适用。
