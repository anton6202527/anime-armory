# 调用规范
默认双语字幕 + 中文配音：
    bash <skill>/compose.sh <作品根> 第N集 bilingual
单语出海/国内：
    bash <skill>/compose.sh <作品根> 第N集 zh    # 国内：中字+中配
    bash <skill>/compose.sh <作品根> 第N集 en    # 出海：英字+英配
真实 BGM：
    BGMFILE=/path/to/music.mp3 bash <skill>/compose.sh <作品根> 第N集 zh
产物：<作品根>/出视频/第N集/成片_第N集_{mode}.mp4

## 输入约定
- clips：<作品根>/出视频/第N集/视频/*.mp4（n2d-video 产物）
- 配音轨：<作品根>/出视频/第N集/配音/voice_{zh,en}.wav（n2d-voice 产物，可选）
- 字幕：<作品根>/脚本/第N集/字幕_{中文,英文}.srt

## BGM 来源（提示用户给丰富选项 + 鉴定可行）
ⓐ Suno 生成给文件 ⓑ 素材库 ⓒ 本地文件(BGMFILE) ⓓ 占位。用户自由描述需求 → 鉴定(存在/格式/时长够循环/版权)→ 可行照办，不可行说明并给替代。

## 转场音效（可选）
用户给 2~5 个 SFX 文件 → 在 clip 边界铺；不给跳过。

## 行业参考（决定音频时展示）
90 秒一集漫剧工作室标配：1 条循环 BGM + 2~5 个转场音效 + AI 角色配音。

## 进度回写
完成后把 <作品根>/common/_进度.md 该集「成片」列改 ✅（列若不存在，在表头末尾追加「成片」列）。

## 字幕字号微调
render_subs.py 支持 env：ZH_SIZE(默认50) / EN_SIZE(默认34)。
