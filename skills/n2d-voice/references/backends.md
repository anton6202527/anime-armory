# 配音后端

优先级：**零样本克隆组**（CosyVoice > FishSpeech > GPT-SoVITS > IndexTTS-2 > VoxCPM2，按此序取**第一个设了 URL 的**）> MiniMax(MINIMAX_API_KEY+GROUP_ID) > 火山(VOLC_APPID+TOKEN) > macOS say(占位)。缺凭证回退 say 并告警。
> 五个零样本后端走同一份代码路径（`render_voice.py` 的 `ZS_SPECS` 表 + `zeroshot_tts()`），只是 URL_env / 参考音前缀 / 超时不同；设了哪个 URL 就用哪个，合成结果按「后端+参考音+文本」持久缓存进 `_voicecache/`。

| 后端 | env | 说明 |
|---|---|---|
| CosyVoice | COSYVOICE_URL, COSY_REF_AUDIO, COSY_REF_TEXT | 本地零样本克隆服务；端点随 fork(常见 /inference_zero_shot，参数 text/prompt_text/prompt_wav) |
| FishSpeech | FISHSPEECH_URL, FISH_REF_AUDIO, FISH_REF_TEXT | 本地零样本克隆；用 n2d_fish_server.py 包一层 /inference_zero_shot(同 CosyVoice 契约)，内部走官方 TTSInferenceEngine(openaudio-s1-mini) |
| GPT-SoVITS | GPTSOVITS_URL, GSV_REF_AUDIO, GSV_REF_TEXT | 本地 inference api；零样本/微调（接入方式同 CosyVoice，端点随 fork） |
| IndexTTS-2 | INDEXTTS_URL, IDX_REF_AUDIO, IDX_REF_TEXT | 本地零样本；**音色/情绪解耦**——可借 A 的音色配 B 的情绪，情绪保真/相似度领先。**voiceover 情绪/语速标注吃重的集优先用它**（念白表演驱动更准，见下「情绪驱动选型」）。同 CosyVoice 契约包一层 /inference_zero_shot |
| VoxCPM2 | VOXCPM_URL, VOX_REF_AUDIO, VOX_REF_TEXT | 本地零样本；48kHz、~30 语、可控音色设计；要高采样率/多语时选。同 CosyVoice 契约 |
| MiniMax | MINIMAX_API_KEY, MINIMAX_GROUP_ID, MINIMAX_MODEL | 云；t2a_v2；克隆见 cloning.md |
| 火山 | VOLC_APPID, VOLC_TOKEN, VOLC_CLUSTER | 云 |
| say | （无） | macOS 占位，仅冒烟用；中文语音若输出空音频，脚本会自动生成静音占位时长轨并写 `_占位说明.md` |

> **情绪驱动选型（2026-06）**：voiceover 每句的 `情绪/语速/停顿/钩子` 标注**会驱动 TTS**（不是注释）。情绪起伏大的集（强反转/哭戏/爆发）——**IndexTTS-2** 的音色/情绪解耦最贴这套标注；日常对白 CosyVoice/FishSpeech 已够。能力/版本会变，以 `novel2drama/references/模型矩阵.md` 配音行为准。新后端只进档案，默认优先级不变（情绪要求高时按集临时指定）。

> ⚠️ **重要**：静音占位时长轨不是有声朗读，只能用于出图前 rough timing / 字幕初定时。跨过出图前必须换真实配音重跑，否则真实音色时长变化会导致镜头和字幕重切。

## 其它可调 env
- 句间留拍：`LINE_GAP`(0.4) / `GAP_HOOK`(0.6) / `GAP_CLIMAX`(0.7) / `GAP_END`(1.0)。
- 系统音"机械感"FX：`SYS_AUDIO_FX`（默认 `asetrate=44100*0.9,aresample=44100,atempo=1.111,aecho=0.6:0.5:24:0.35,`）——设 `SYS_AUDIO_FX=''` 可禁用，或自定义滤镜链。仅作用于含「系统」的角色。

## 角色→音色映射
默认见 render_voice.py 的音色表；均可 env 覆盖（MiniMax: MM_SHEN/MM_LIU/MM_XIAOHE/MM_TAIJIAN/MM_SYS/MM_NARR）。

### 零样本克隆 按角色分音色（CosyVoice/FishSpeech/GPT-SoVITS/IndexTTS-2/VoxCPM2 通用）
`role_key(role)` 把角色名归到音色键：`SYS`(系统) / `LIU`(柳娘子) / `XIAOHE`(小禾) / `TAIJIAN`(太监) / `YAO`(含「妖」) / `NARR`(纯「旁白」) / `SHEN`(沈念·沈念旁白·默认)。
每个键各取参考音：优先 `<PREFIX>_REF_<KEY>` / `<PREFIX>_REF_<KEY>_TEXT`，缺则回退全局 `<PREFIX>_REF_AUDIO` / `<PREFIX>_REF_TEXT`，再缺则无参考(默认嗓)。`PREFIX` = 选中后端对应前缀：`COSY` / `FISH` / `GSV` / `IDX` / `VOX`（即上表 env 列里 `*_REF_*` 的前缀）。
例：`export FISH_REF_SHEN=.../SHEN.wav FISH_REF_SHEN_TEXT="<逐字文本>" FISH_REF_YAO=.../YAO.wav FISH_REF_YAO_TEXT="..."` → 沈念用 SHEN 嗓、妖用 YAO 嗓。⚠️ 参考音仅限本人嗓/已授权/纯合成。
**音色库便捷生成**：`制漫剧/<剧名>/设定库/voicebank/build_voicebank.sh` 用本机中文 say(Tingting/Meijia/Sinji) + ffmpeg 变调派生 7 个区分音色，产出 `*.wav` + 可 `source` 的 `_refs.env`。

## CosyVoice/GPT-SoVITS 本地服务
用户自行启动本地推理服务（端口/端点随 fork），把 URL 填进 COSYVOICE_URL/GPTSOVITS_URL，参考音频+参考文本填进对应 env。本 skill 通过 HTTP 调用，不负责启动服务。

## FishSpeech 本地服务
`~/fish-speech/n2d_fish_server.py`（conda env `fish-speech`，模型 openaudio-s1-mini）暴露与 CosyVoice 相同的 `GET /inference_zero_shot?text=&prompt_text=&prompt_wav=`。启动 `bash ~/fish-speech/start_n2d_fish.sh`(默认 :8081)，再 `export FISHSPEECH_URL=http://localhost:8081 FISH_REF_AUDIO=<参考音wav> FISH_REF_TEXT=<逐字文本>`。mac 为 MPS/CPU，较慢；16GB 机用 mini 模型。
