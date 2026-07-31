# n2d adapter v2、多镜执行与交付状态

本轮把“模型能做”“本机能跑”“视频做完”“可以发布”四件事正式拆开。目标不是增加更多平行状态，而是让现有 `_进度.md`、gate、runner 和 release verdict 互相可追溯。

## 1. 执行边界

- `n2d-model-router` 负责能力与创作路线，逐 route 输出 `execution_adapter` 与 `route_executable`。
- `video_execution_adapter.py` 负责本机执行合同。状态固定为 `automated_ready / registered_missing_command / registered_incomplete / manual_required / unregistered`。
- Dreamina 使用 embedded adapter；其它渠道以作品内 `生产数据/video_execution_adapters.json` 注册 wrapper。wrapper 接收稳定 request JSON，不把 SDK、账号或密钥写进仓库。
- `video_runner.py` 统一 submit/query/cancel、幂等键、失败分类和未知付费状态保护。没有 adapter 不等于换一个后端；只能修环境、显式人工交付或导出 job package。

## 2. 实际粗剪

`video_runner accept` 在全部逻辑 Clip 齐片后调用 `post_video_proxy.py`，用真实视频像素按 `edit_target_sec` 裁尾并拼出：

- `合成/<集>/_proxy/actual_rough_cut.mp4`
- `生产数据/post_video_proxy_<集>.json`

它只回答镜序、节奏、尾巴和接点是否成立，不含正式声音、字幕、调色，因此不是成片或母版。ffmpeg 缺失时只落可恢复计划。

## 3. 多镜执行

router 只发现候选；`原生多镜生成=开启` 后 `multishot_plan.py` 才激活。adapter 还必须声明 `multishot_submit/query`。执行顺序是：

1. 每个 Clip 保留自己的 compiled prompt、hash、edit target 和 QC 单元。
2. `multishot_runner.py` 生成整组 prompt/request 并一次提交。
3. 下载一条 provider 母片。
4. 按逐镜 edit target 确定性拆回原 Clip。
5. 每个拆回 Clip 继续走既有 `video_qc`、accept、进度与生成配方。

组内接缝仍测量，但标为 `model_handled`，不套用不存在的逐镜尾帧接力；组间仍严格。这样得到原生跨镜连续性，同时保留最小重跑粒度。

## 4. 流程可观测与合同收敛

- `flow_events.jsonl` / `flow_telemetry.json`：控制面阶段、停因、缓存命中、编排耗时、adapter/验收/粗剪里程碑；不含 prompt、密钥或供应商原始响应。
- `episode_graph_<集>.json`：从现有产物派生 storyboard→route→job→media→粗剪→master→release 图；不替代 `_进度.md`。
- `blocking_bundles/latest_<集>.json`：把当前停因归一为选择、付费、合规、环境/adapter、合同/gate、创作/执行或 QC/人审，并带修复命令和 graph hash；不建立新 gate。
- report-only 前置缓存扩到各阶段；指纹覆盖脚本、合同、路由、prompt 与媒体变化。block/异常不缓存。

## 5. QC 与实验可信度

- VLM 是语义告警器，不是自动定罪器；VLM “no” 最多 WARN，需人审或确定性证据才能 BLOCK。
- 数值检测器须有 per-(维度, 后端, 风格) 生产规模金标集、混淆矩阵、区间与足够 balanced accuracy 才能自动 BLOCK。
- A/B 的 `min_samples` 按每个变体计算；结论带 Wilson 区间、两比例检验、Bonferroni 校正、分流不均和中途偷看告警。

## 6. 状态颗粒度

`release_verdict.py` 同时输出：

- `clip_delivery_complete`：逻辑镜头覆盖完成。
- `master_delivery_complete` / `production_complete`：技术母版与非发布域 QA 完成。
- `publish_ready_cn`：中国公开发行 profile 完成。
- `publish_ready_overseas`：海外发行与本地化 profile 完成。
- `publish_ready_commercial`：商业权利 profile 完成。

AI 标识、备案、本地化、平台审核可以阻断相应 `publish_ready_*`，但不能把已经完成的技术交付改写成不存在；版权、肖像和真人声音授权仍按对应边界执行。

## 7. 运维命令

```bash
python3 skills/n2d/_lib/flow_telemetry.py <作品根> --json
python3 skills/n2d/scripts/episode_graph.py <作品根> 第N集 --write --json
python3 skills/n2d/n2d-compose/scripts/post_video_proxy.py <作品根> 第N集 --render --json
python3 skills/n2d/n2d-video/scripts/multishot_plan.py <作品根> 第N集 --write --json
python3 skills/n2d/n2d-review/scripts/calibrate_thresholds.py <作品根> --calibrate --write --registry --json
python3 skills/n2d/n2d-feedback/scripts/experiments.py audit <作品根> --metrics <平台指标.csv> --write --json
python3 skills/n2d/scripts/release_verdict.py <作品根> 第N集 --profile cn_public --write --json
```
