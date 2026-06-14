# n2d-video Quickstart

Prerequisites:
- `出图` column is complete
- `脚本/第N集/storyboard.json` exists
- Shot PNGs and any required tail-frame PNGs exist

Gate:
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage video_preflight
```

Required outputs:
- `出视频/第N集/prompt/00_总览.md`
- `出视频/第N集/prompt/01_clips.md`
- `出视频/第N集/视频/ClipK_*.mp4`
- `生产数据/video_batch_第N集_XX_YY.json`
- `生产数据/video_qc/第N集/XX_YY/`

Batch runner:
```bash
python3 skills/n2d-video/scripts/video_runner.py prepare <作品根> 第N集 --range 01-05
python3 skills/n2d-video/scripts/video_runner.py submit <作品根> <manifest.json> --clip Clip_01
python3 skills/n2d-video/scripts/video_runner.py query <作品根> <manifest.json> --clip Clip_01
python3 skills/n2d-video/scripts/video_runner.py accept <作品根> <manifest.json> --clip Clip_01
python3 skills/n2d-video/scripts/video_runner.py qc <作品根> <manifest.json>
```
`video_runner.py submit` runs `video_preflight` by default before calling the backend; use `--skip-preflight` only for an already-checked controlled rerun. After MP4s are accepted, run `dashboard.py gate <作品根> 第N集 --stage video` for post-generation verification.

**后端范围（C2·适配不了就停下报缺口）**：`submit`/`query` 只内置了**即梦/Dreamina CLI** 的自动化契约（`prepare --backend` 默认 `dreamina`，别名 `即梦`）。路由到 **Kling/Veo/Seedance 等没有内置 CLI 契约的后端，或 `--backend manual`** 时，runner **不会静默改用即梦顶替**（那会换错路、按即梦记错账）——它会停下报缺口，让你按 SKILL.md「一步步指导手动跑」在对应渠道出片，把 MP4 放进 `出视频/第N集/视频/`，再直接 `accept` 登记验收（`accept` 不依赖 submit）。要给某后端加自动化，在 `video_runner.py` 的 `VIDEO_BACKEND_ADAPTERS` 注册一个 adapter（`submit_args`/`query_args`/`provider`）。

Progress:
```bash
python3 skills/n2d/progress.py ensure-col <作品根> 视频prompt ⬜
python3 skills/n2d/progress.py set <作品根> 第N集 视频prompt ✅
```
`video_runner.py accept` handles dashboard record + `视频 X/Y` progress update.

Notes:
- Keep platform-native clip audio in the original MP4; `n2d-compose` decides whether to discard or mix it.
- Every Clip prompt must include `原生音画策略`; only low-risk ambience/SFX clips can opt in, and native speech remains forbidden by default.
- Use backend-specific single-clip duration limits from `references/platforms.md`.
