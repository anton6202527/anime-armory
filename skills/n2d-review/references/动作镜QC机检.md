# 动作镜成片 QC 八维 + 高光流帧采样（out-of-repo 重模型桥接）

`spectacle_video_qc.py` 是**纯标准库证据聚合器**——它只组织证据、判 `verified/unverified`，不自己跑光流/姿态/VLM。
真正的像素级机检在 out-of-repo conda 环境（同 `lipsync_measure.py` 模式）。本文件是这层的契约。

## 八维（单一真值源：`n2d_spectacle.SPECTACLE_QC_DIMENSIONS`）

| 维度 | 证据来源 runner | 已有/新增 | 关键实测字段(evidence_keys) |
|---|---|---|---|
| 光流方向↔意图对账 | 动作-artifact runner | **新增** | `optical_flow_direction` / `flow_intent_match` / `flow_direction_error` |
| 肢体畸变/多手多脚 | 动作-artifact runner(HADM类) | **新增** | `limb_artifact_score` / `extra_limbs` / `deformation_score` |
| 运动平滑/动作完成度 | `motion_quality_consistency.py`(MOT1) | 已有 | `motion_smoothness` / `jerk` / `dynamic_degree` / `action_completion` |
| 运动模糊合理性 | 动作-artifact runner | **新增** | `motion_blur_plausibility` / `imaging_quality` / `blur_score` |
| 首尾 match-on-action 衔接 | `temporal_consistency.py` | 已有 | `endframe_match` / `seam_action_match` / `match_on_action` |
| 跨镜动作连续+180°轴线 | `camera_trajectory_consistency.py`(CAM1) | 已有 | `trajectory_error` / `axis_consistency` / `crossing_line` |
| 主体身份保持 | `subject_video_consistency.py`(S2V) | 已有 | `subject_fidelity` / `identity_drift` / `subject_swap` |
| 时序闪烁 | `temporal_consistency.py` | 已有 | `temporal_flicker` / `tci` / `flicker_score` |

任一 evidence_key 在该镜 sidecar 行里非空 → 该维记 `verified`，否则 `unverified`。
`production` 一致性严格度下，SPECV/MOT1/CAM1/S2V 的未实测会在 compose/review 交付边界由 gate 升 BLOCK。

## 高光流帧重点采样（`n2d_spectacle.high_flow_sampling_plan`）

动作峰值处（高光流）最容易出 artifact（FMG-DFS）。每镜 `sampling_plan` 给：
- `base_uniform_frames`：均匀基底（≈1 帧/秒，封顶 24）
- `peak_density`：动作峰值段每 0.2s 一帧加密
- `boundary_frames`：首/尾帧（喂 match-on-action 对账）

runner 应**先用光流定位 motion-salient 段，再在峰值帧加密抽帧**检肢体畸变/身份漂/运动模糊，
而非全片均匀抽——均匀抽会把最易崩的动作峰值漏过。

## 新增维的动作-artifact runner（已实现：`scripts/spectacle_motion_measure.py`）

重模型只能在装好的 conda 环境跑（本机 = facefusion；cv2+numpy 必需做光流/锐度，mediapipe 可选做肢体）：

```bash
conda run -n facefusion python skills/n2d-review/scripts/spectacle_motion_measure.py <作品根> 第N集 --json
```

它读每条高动态 Clip 的 `出视频/第N集/video/*.mp4`，按 `high_flow_sampling_plan` 抽帧，
跑 Farneback 光流→主运动方向 vs `template_contract.camera_path`、Laplacian 锐度×光流→运动模糊合理性、
（有 mediapipe 时）逐帧人数→肢体/多人异常，写 `生产数据/spectacle_motion_artifacts_第N集.json`。
缺 cv2/numpy 不崩、给安装提示、`ok=False`；缺 mediapipe 时肢体维留空（unverified，绝不臆造）。
纯逻辑函数（方向判定/意图对账/模糊/肢体/采样）无重依赖，`test_spectacle_motion_measure.py` 直跑。

写出的 sidecar shape：

```json
{
  "kind": "n2d_spectacle_motion_artifacts",
  "checks": [
    {"clip": "Clip_01",
     "optical_flow_direction": "matches camera_path:left_to_right",
     "flow_direction_error": 0.08,
     "limb_artifact_score": 0.03,
     "extra_limbs": 0,
     "motion_blur_plausibility": 0.9}
  ]
}
```

建议实现：
- 光流：`conda run -n facefusion` 下 RAFT/Farneback 光流 → 主运动方向 vs route `camera_path`/动作方向。
- 肢体畸变：HADM 或 pose 检测器在 `sampling_plan.peak_density` 帧上数肢体/手数异常。
- 运动模糊：高光流段该糊（合理）、低光流段不该糊（崩坏）→ 边缘锐度 vs 光流幅度相关性。

写好后 `spectacle_video_qc.py --write` 会自动把这三维并入八维核验状态；缺该 sidecar 时
三维保持 `unverified` 并由 SPECV warn 提示（production 交付边界升 BLOCK）。绝不臆造分。
