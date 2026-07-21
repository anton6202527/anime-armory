# 高动态/大场景制作计划

- episode: 第1集
- spectacle_clips: 2

| Clip | 类型 | 缺契约字段 | 控制输入 | 回退/保真实现方案 |
|---|---|---|---|---|
| Clip_06 | fight_exchange | - | pose_sequence, depth_sequence, instance_masks, contact_map, camera_path | 拆成拾刀、冲锋、接触、落地、威胁、反应六个短镜；接触帧用定格关键帧，不做端到端三人同框生成。 |
| Clip_08 | fight_exchange | - | pose_sequence, depth_sequence, instance_masks, contact_map, camera_path | 手部、闭眼反应、错愕、血点落衣拆镜替代。 |
