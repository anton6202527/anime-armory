# n2d-batch 命令目录（完整用法）


> SKILL.md 只留常用命令速查；本文件是完整命令目录（排队/过滤/认领/worker/多worker 安全/findings 回流/复检/低分回流/预算）。队列与账本字段 schema 见 `schema.md`。

## 标准命令

### 1. 按 `_进度.md` 自动排队

```bash
python3 skills/n2d-batch/scripts/queue.py plan <作品根> \
  --episodes 1-5 \
  --max-concurrency 2 \
  --max-retries 1 \
  --budget 40 \
  --budget-unit work_units
```

输出：

- `生产数据/batch_queue.json`
- `生产数据/batch_queue.md`

默认会为每集只排“当前下一步”。例如第1集卡 `配音` 就排 `voice`，第2集卡 `出图` 就排 `image`。

默认写入时会**合并**到既有 `batch_queue.json`，不覆盖在跑任务；合并后会按完整 ledger 重新计算预算，而不是只看本次新增计划。若确实要丢弃旧队列：

```bash
python3 skills/n2d-batch/scripts/queue.py plan <作品根> --episodes 1-5 --replace
python3 skills/n2d-batch/scripts/queue.py plan <作品根> --episodes 1-5 --replace --force  # 队列有 running 时才允许强替换
```

### 2. 按 stage 过滤

```bash
python3 skills/n2d-batch/scripts/queue.py plan <作品根> --stage image --episodes 1-20
python3 skills/n2d-batch/scripts/queue.py plan <作品根> --stage n2d-video --episodes 8-12
```

`--stage` 接受 stage key、owner、label、进度列名：如 `image` / `n2d-image` / `出图`。

### 3. claim 并发槽

```bash
python3 skills/n2d-batch/scripts/queue.py claim <作品根> --limit 2
```

返回可执行任务。执行者按任务里的 `owner` 和 `command` 去调对应 skill。完成后必须 `mark`。

### 4. Worker 自动执行

先配置 runner 命令：

```json
{
  "commands": {
    "voice": "python3 skills/n2d-voice/render_voice.py \"{root}\" \"{ep}\" zh",
    "image": "bash skills/n2d-batch/scripts/run_n2d_image.sh \"{root}\" \"{ep}\"",
    "video": "N2D_VIDEO_RANGE=06-10 bash skills/n2d-batch/scripts/run_n2d_video.sh \"{root}\" \"{ep}\"",
    "compose": "bash skills/n2d-batch/scripts/run_n2d_compose.sh \"{root}\" \"{ep}\" zh"
  },
  "env": {
    "NO_PROXY": "127.0.0.1,localhost",
    "N2D_IMAGE_COMMAND": "python3 my_image_runner.py \"$N2D_ROOT\" \"$N2D_EPISODE\""
  }
}
```

保存到：

```text
制漫剧/<剧名>/生产数据/batch_runner.json
```

执行一轮：

```bash
python3 skills/n2d-batch/scripts/runner.py <作品根> --limit 1
```

持续跑到队列无可 claim 任务：

```bash
python3 skills/n2d-batch/scripts/runner.py <作品根> --until-empty --limit 1 --timeout-sec 3600
```

需要把“命令 exit 0”再用契约产物 + `_进度.md` 后置条件兜住时，加：

```bash
python3 skills/n2d-batch/scripts/runner.py <作品根> --until-empty --verify-outputs
```

`--verify-outputs` 会读取 `common/n2d_contract.py` 的 `output_contract`：普通阶段按 required outputs 校验；配音/合成/水印成片等存在合法替代产物的阶段按 `any_of` 组合校验，避免真实配音与占位清单、中文成片与双语成片互相误判。

runner 行为：

1. `claim` 可执行任务，尊重 `max_concurrency`。
2. 执行 `batch_runner.json.commands[stage_key]` 或 `commands[owner]`。
3. 写 `n2d-dashboard` manual event，记录 `task_id`、stage、耗时、exit_code、命令。
4. exit code `0` → `mark pass` → `done`。
5. 非 0 / timeout / 未配置命令 → `mark fail` → `retry_queued` 或 `failed`。

命令模板可用变量：`{root}`、`{episode}`/`{ep}`、`{task_id}`、`{stage_key}`、`{owner}`、`{reason}`、`{scope}`、`{affected_shots}`、`{affected_artifacts}`。runner 同时注入环境变量 `N2D_ROOT`、`N2D_EPISODE`、`N2D_TASK_ID`、`N2D_STAGE` 等。

仓库已提供标准 wrapper：

- `skills/n2d-batch/scripts/run_n2d_image.sh`：先跑 image_preflight gate；实际生图命令必须由 `N2D_IMAGE_COMMAND` 显式配置，避免 wrapper 猜后端或误花钱。
- `skills/n2d-batch/scripts/run_n2d_video.sh`：先跑 identity/router/video_preflight gate，再调用 `n2d-video/scripts/video_runner.py prepare` 生成稳定 manifest；必须显式设置 `N2D_VIDEO_RANGE=06-10`，避免自动猜付费批次。真正提交视频需再显式设置 `N2D_VIDEO_SUBMIT_ONE=Clip_06` 或 `N2D_VIDEO_AUTO_SUBMIT=1`，否则不会消耗视频积分；`video_runner.py submit` 本身也默认再跑一次 `video_preflight`，防止绕过 wrapper 直接扣费。
- `skills/n2d-batch/scripts/run_n2d_compose.sh`：先跑 compose gate，再调用 `n2d-compose/compose.sh`。

示例配置可直接复制为项目级文件后再按后端补 env：

```bash
cp skills/n2d-batch/references/batch_runner.example.json <作品根>/生产数据/batch_runner.json
```

> **stage 前置边界**：runner 不内置 image/video/compose 的业务规则，避免把阶段逻辑复制进队列层；标准 wrapper 只做可复用 gate/preflight，真正的生成仍由对应阶段脚本或显式配置的本地命令执行。

### 4.5 单机多 worker 安全（原子认领 + 租约回收 + 断点恢复）

一台机器多 GPU / 多 worker 同抢一个队列时，靠**文件锁 + 租约**保证安全，**纯本地、零后端**（多机/私有算力池需协调后端，见下「边界」）：

```bash
# 各 worker 起一个、给稳定 id；任务认领后打 lease，执行期自动心跳续租
python3 skills/n2d-batch/scripts/runner.py <作品根> --until-empty --worker w1 --lease-seconds 1800
python3 skills/n2d-batch/scripts/runner.py <作品根> --until-empty --worker w2 --lease-seconds 1800
# 某 worker 崩了重启 → --resume 先回收自己上次残留的 running，再继续认领（断点恢复）
python3 skills/n2d-batch/scripts/runner.py <作品根> --until-empty --worker w1 --resume
# 手动回收过期租约（任意 worker 死了没 mark，租约到点即可被别的 worker 接走）
python3 skills/n2d-batch/scripts/queue.py reclaim <作品根>
```

- **原子认领**：`claim/mark/reclaim/renew` 全在 `生产数据/batch_queue.lock` 的 `flock` 互斥锁内"重读最新队列 → 改 → 原子写(temp+`os.replace`)"。多进程同抢**绝不双认领、绝不互相覆盖**。
- **租约 lease**：认领即给任务 `lease_until`，runner 执行期起心跳线程按 `lease/3` 续租；崩溃后租约不再续 → 到点过期。
- **断点恢复**：`claim` 每次认领前自动回收过期租约的 running → `retry_queued`（或超重试上限 → `failed`）。`--resume` 额外强制回收**本 worker** 残留的 running（需稳定 `--worker` id）。
- **runner 不再持 stale 队列**：跑任务时不持锁，认领/标记各自锁内重读最新队列——修掉了"长任务跑完后回写整队、覆盖别的 worker 认领"的老 bug。
- **边界**：`flock` 只在**单机/本地文件系统**可靠；跨 NFS 不可靠。**多机/私有算力池**要换真正的协调后端（DB/Redis/对象存储条件写/消息队列）或单 dispatcher 拉取模型——本锁不负责跨主机。

### 5. 手动标记结果与失败重试

```bash
python3 skills/n2d-batch/scripts/queue.py mark <作品根> 002-image-progress --status pass
python3 skills/n2d-batch/scripts/queue.py mark <作品根> 002-image-progress --status fail --note "脸漂移，需重抽"
```

失败未超过重试上限时会回到 `retry_queued`；超过后变 `failed`。

### 6. 只重跑受影响镜头/Clip

```bash
python3 skills/n2d-batch/scripts/queue.py plan <作品根> \
  --episodes 2 \
  --rerun-from image \
  --scope "只重跑 Clip_03 首帧，因定妆_王敦更新" \
  --affected-shot Clip_03 \
  --affected-artifact 出图/第2集/图片/Clip_03.png \
  --max-concurrency 1 \
  --max-retries 2
```

这类任务 `reason=rerun`，不会因为该集 `_进度.md` 已显示完成而被跳过。

### 7. 承接一致性 / 人审 findings 回流

`n2d-review/scripts/consistency_audit.py` 会生成 `生产数据/consistency_findings_第N集.json`；`n2d-review-ui/scripts/review_ui.py --export-findings` 会生成 `生产数据/review_ui_findings_第N集.json`；`n2d-dashboard/scripts/dashboard.py gate ...` 会生成 `生产数据/gate_findings_<stage>_第N集.json`；`n2d-identity/scripts/voice_print_consistency.py` 会生成 `生产数据/consistency_findings_voice_print_第N集.json`。这些都是 `kind=n2d_consistency_findings`，可直接转成最小范围返工队列：

```bash
python3 skills/n2d-batch/scripts/queue.py plan <作品根> \
  --from-consistency-findings <作品根>/生产数据/review_ui_findings_第N集.json \
  --max-concurrency 1 \
  --max-retries 2
```

报告里带 `auto_return_tasks` 时优先按它排队；否则按 `(episode, return_to_stage, dim)` 聚合红黄 findings，并携带 `affected_shots` / `affected_artifacts`，避免整集重来。

**闭环复检（修复→标 resolved / 复发→reopen）**：每个返工任务带 `finding_fingerprints`（`(集×阶段×维度×最小定位)` 指纹，单一真值源 `n2d_contract.finding_fingerprint`；无镜头/产物定位时退回旧粒度）外加 `coarse_fingerprints`（`(集×阶段×维度)` 粗指纹，供回退匹配）。定位串先过 `canonical_scope_key` 归一：`Clip_03`、`Clip_03_首帧`、`镜头3`、`出图/.../Clip_03.png` 都归到同一 `clip_3`——同一镜头换写法/帧位/产物路径不再产生不同指纹，堵掉"定位粒度漂移导致已修问题被误判 resolved"。同一未解决问题**不随复审堆叠**——重排时同指纹的已结束任务 reopen、在途的跳过，而不是生成 `-2/-3` 重复任务。

**返工 pass 后门禁自动重跑**：runner mark pass 且任务有 `gate_stage` 时，自动重跑该 stage 的 `dashboard.py gate` 刷新 `gate_findings_*.json`，让随后的 `--recheck` 对的是返工 **之后** 的现状指纹，而不是返工前的陈旧 findings——这是闭环的最后一环，无需人工再敲一遍 gate。`--no-gate`（或 `batch_runner.json` 里 `"auto_gate": false`）可关闭。

```bash
# 复检：用最新 consistency_findings/review_ui_findings 的指纹回写队列
python3 skills/n2d-batch/scripts/queue.py recheck <作品根> [--episodes 1-5]
# 或让 runner 跑完自动复检（pass 后已自动刷新门禁 findings，--recheck 即对现状判定）
python3 skills/n2d-batch/scripts/runner.py <作品根> --until-empty --recheck
# 粗粒度回退：精确指纹对不上但该(集×阶段×维度)桶仍有问题则不判 resolved 而 reopen，堵漏放
python3 skills/n2d-batch/scripts/queue.py recheck <作品根> --coarse
python3 skills/n2d-batch/scripts/runner.py <作品根> --until-empty --recheck --coarse-recheck
```

复检把指纹已从最新审查消失的 done 任务标 `resolved=true`（留痕，不静默覆盖），仍在的 reopen 回 `queued`——这样"发现→返工→修复→复检确认不复现"才真正闭环，而不是只入队不回收。`--coarse` 是安全网：精确指纹归一后仍对不上（定位串大改/换成无镜头号的自由文本）但同 `(集×阶段×维度)` 桶仍有 findings 时，宁可 reopen 复核也不漏放（代价：同桶若有别的镜头未修，已修镜头会被一起召回，计入 `reopened_coarse`）。

### 8. 承接 n2d-score 低分回流

```bash
python3 skills/n2d-score/scripts/score.py <作品根> 第1集 \
  --run-checks \
  --threshold 85 \
  --enqueue-low \
  --max-concurrency 1 \
  --max-retries 1
```

`n2d-score` 会按七维低分自动生成 rerun 任务：角色/服装/场景/风格问题通常回 `image`，字幕/节奏回 `script_stage2`，音画同步回 `compose`。如果证据里能定位到 Clip 或产物路径，会写入 `affected_shots` / `affected_artifacts`，本 skill 随后按普通队列流程 `claim` / `mark` 即可。

## 预算估算

默认估算单位是 `work_units`，只用于排队前裁剪；真实成本仍由 `n2d-dashboard` 记录。

如需项目自定义成本表，写：

```json
{
  "image": {"amount": 3.0, "unit": "credits"},
  "video": {"amount": 12.0, "unit": "credits"},
  "voice": {"amount": 1.0, "unit": "credits"},
  "compose": {"amount": 0.5, "unit": "credits"}
}
```

保存到：

```text
制漫剧/<剧名>/生产数据/stage_cost_estimates.json
```

再用：

```bash
python3 skills/n2d-batch/scripts/queue.py plan <作品根> --budget 60 --budget-unit credits
```
