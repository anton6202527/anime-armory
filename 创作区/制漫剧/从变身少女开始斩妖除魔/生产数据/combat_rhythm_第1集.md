# 打斗剪辑节奏曲线审计（advisory-only）

- episode: 第1集 ｜ 慢阈值: 5.0s（区域档·proxy_thresholds）
- impact 型打斗镜: 2 ｜ 提示: 0（全 info·只提示不阻断）

> 节奏曲线是审美不是硬伤：阈值带 internal-heuristic provenance（无公开打斗切点基准），**不升 BLOCK**。撞点对齐硬伤走 combat_cue_apex_audit。

✅ 打斗镜切点节奏：够密 + 有起伏（无过慢/平淡提示）。
