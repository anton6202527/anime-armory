# n2d-image Quickstart

Prerequisites:
- `分镜设计 ✅`
- `脚本/第N集/storyboard.json` exists
- `脚本/第N集/素材清单.md` exists

Gate:
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image_preflight
```

Required outputs:
- `出图/共享/prompt/00_索引.md`
- shared reference PNGs in `出图/共享/图片/`
- `出图/第N集/prompt/00_总览.md`
- `出图/第N集/prompt/01_分镜出图.md`
- shot PNGs in `出图/第N集/图片/`
- required tail-frame PNGs when `storyboard.json continuity.need_endframe=true`

Progress:
```bash
python3 skills/n2d/progress.py set <作品根> 第N集 出图prompt ✅
python3 skills/n2d/progress.py set <作品根> 第N集 出图 X/Y
```

Notes:
- `生图AI` defaults to Codex / GPT Image 2 and should stay there unless the user explicitly signs an exception. Non-Codex/OpenAI image backends (including Dreamina/即梦官方 CLI, Seedream, Kling 主体库, Nano Banana, Sora Cameo) require `<作品根>/合规/image_backend_override.json` before any paid image run. The gate still blocks backend mixing and reverse-engineered/unauthorized image paths.
- Shared reference assets must satisfy each character's `library_tier` plus the actual shot needs before episode PNGs: every named character needs front + half/full-body outfit + a same-source face anchor; `core_full` adds 45°/side/back/turnaround, `recurring_standard` adds 45°, `named_minimal` adds extra angles only when a real shot needs them, and `restricted_partial` stays local/ faceless. Referenced scene / prop / accessory / weapon / VFX assets still need images and registry constraints. This shared-first order is non-waivable: `--skip-preflight`, P0 vertical slices, and partial `--shots Clip_XX` runs cannot generate Clip PNGs before the tier/shot requirements are ready.
- Every shared makeup prompt and every shot prompt must include both pre-submit checklist and post-generation self-check; missing either is a preflight block.
- After PNGs are landed, run `dashboard.py gate <作品根> 第N集 --stage image` for the post-generation image gate.
