# formal upgrade plan

用于把当前 demo excerpt 升级为正式整首 MV。先补上游真值，再重跑下游；不要直接扩剪 demo 成片。

## 1. 正式歌入库
替换 `歌/song.wav` 为完整定稿歌曲，并确认 `_meta.is_demo=false`、`分镜/clip_plan.json` 不再是 demo_excerpt。

## 2. 重跑真实卡点
用正式整首歌重算 BPM、beats/downbeats 与段落能量。

```bash
conda run -n cosyvoice python skills/mv-beat/scripts/beat_detect.py "/Users/wesley/learn/anime-armory/创作区/制MV/仗剑下山"
```

## 3. 重拆正式 timeline
按正式歌结构重拆 clip/timeline，不沿用 20s demo 的 5 镜头。

```bash
python3 skills/mv-plan/scripts/plan_clips.py "/Users/wesley/learn/anime-armory/创作区/制MV/仗剑下山" --granularity 标准 --strategy 副歌强卡点 --visual-style 国风写意
```

## 4. 补语义镜头设计
让每个 clip 都有动作、景别、运镜、身份合约和参考输入。

```bash
python3 skills/mv-plan/scripts/compose_prompts.py "/Users/wesley/learn/anime-armory/创作区/制MV/仗剑下山"
```

## 5. 刷新身份/资产/参考需求
重建 reference pack 缺口；当前未 ready：9/9。

```bash
python3 skills/mv-craft/scripts/identity_registry.py "/Users/wesley/learn/anime-armory/创作区/制MV/仗剑下山"
```

## 6. 补正式 reference pack
按 `设定/reference_requirements.md` 补主角多角度、成年态、青锋剑、关键场景和剑光/VFX 参考图；补完后重跑第 5 步确认 ready。

## 7. 出图后立即 QC
正式首帧/尾帧落档后先过 image_qc，再进入图生视频。

```bash
python3 skills/mv-image/scripts/image_qc.py "/Users/wesley/learn/anime-armory/创作区/制MV/仗剑下山" --strict
```

## 8. 视频登记与挑版
为每个 clip 登记图生视频 take，按动作/身份/卡点/清晰度评分并 selected。

```bash
python3 skills/mv-video/scripts/video_jobs.py "/Users/wesley/learn/anime-armory/创作区/制MV/仗剑下山"
```

## 9. 继承合约与视频 QC
检查首帧到视频是否继承身份/场景/道具，并抽 start/mid/end 帧看接缝与崩坏。

```bash
python3 skills/mv-video/scripts/inherit_contract.py "/Users/wesley/learn/anime-armory/创作区/制MV/仗剑下山" --no-fail && python3 skills/mv-video/scripts/video_qc.py "/Users/wesley/learn/anime-armory/创作区/制MV/仗剑下山" --no-fail
```

## 10. 字幕、合成、总审
重做全曲卡拉 OK 字幕，合成正式成片，再跑 mv-review。

```bash
bash skills/mv-compose/mv_compose.sh "/Users/wesley/learn/anime-armory/创作区/制MV/仗剑下山" 9:16 && python3 skills/mv-review/scripts/mv_check.py "/Users/wesley/learn/anime-armory/创作区/制MV/仗剑下山"
```
