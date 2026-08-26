# 配音后端

后端能力发现顺序：**零样本克隆组**（CosyVoice 3 > Fish Audio S2 / Fish Speech > GPT-SoVITS > IndexTTS-2.5 > VoxCPM2，按此序取第一个设了 URL 的）> MiniMax > 火山。真正执行哪个后端以 `设定库/voice_casting.json` 的角色定妆锁为准；新版名称是候选能力快照，不表示本地旧 endpoint 已自动升级，执行收据必须记录实际模型版本；混合自动路由下，选角锁与当前可用后端不一致或缺凭证时直接阻断，**不静默回退 macOS say**。
> 五个零样本后端走同一份代码路径（`render_voice.py` 的 `ZS_SPECS` 表 + `zeroshot_tts()`），只是 URL_env / 参考音前缀 / 超时不同；设了哪个 URL 就用哪个，合成结果按「后端+参考音+文本」持久缓存进 `_voicecache/`。

| 后端 | env | 说明 |
|---|---|---|
| CosyVoice 3 | COSYVOICE_URL, COSY_REF_AUDIO, COSY_REF_TEXT | 候选能力档案为 CosyVoice 3；本地 legacy endpoint 合同继续兼容常见 `/inference_zero_shot`（text/prompt_text/prompt_wav），执行收据记录服务端精确模型版本，不把旧 endpoint 名静默解释为新模型 |
| Fish Audio S2 / Fish Speech | FISHSPEECH_URL, FISH_REF_AUDIO, FISH_REF_TEXT | 候选能力档案为 Fish Audio S2（API model `s2-pro`）；旧本地 Fish Speech endpoint 可继续经 n2d_fish_server.py 暴露 `/inference_zero_shot`，不得静默宣称升级 |
| GPT-SoVITS | GPTSOVITS_URL, GSV_REF_AUDIO, GSV_REF_TEXT, GPTSOVITS_SPEED/GSV_SPEED | 本地 inference api；优先尝试官方根路径 API（`refer_wav_path` / `prompt_text` / `text_language` / `speed`），失败后自动回退 CosyVoice 3/旧 fork 兼容 `/inference_zero_shot` |
| IndexTTS-2.5 | INDEXTTS_URL, IDX_REF_AUDIO, IDX_REF_TEXT | 候选能力档案为 IndexTTS-2.5；本地 endpoint 可能仍是 2.x，保留同 CosyVoice 的 `/inference_zero_shot` 兼容合同，执行收据记录 2/2.5 精确版本；音色/情绪、速度与发音控制以实际 endpoint probe 为准 |
| VoxCPM2 | VOXCPM_URL, VOX_REF_AUDIO, VOX_REF_TEXT | 本地零样本；48kHz、~30 语、可控音色设计；要高采样率/多语时选。同 CosyVoice 3/旧 fork 兼容契约 |
| MiniMax | MINIMAX_API_KEY, MINIMAX_GROUP_ID, MINIMAX_MODEL | 云；t2a_v2；克隆见 cloning.md |
| 火山 | VOLC_APPID, VOLC_TOKEN, VOLC_CLUSTER | 云 |
| say | （无） | 仅供旧流程/显式冒烟；不得充当新项目的前期时间基准或最终声音。混合模式为空音频时直接失败，不生成静音占位 WAV |

> **情绪驱动选型（2026-08）**：voiceover 每句的 `情绪/语速/停顿/钩子` 标注**会驱动 TTS**（不是注释）。能力候选包括 IndexTTS-2.5、CosyVoice 3 与 Fish Audio S2，但只有实际 endpoint probe/执行收据证明相应控制已生效时才能使用；旧 endpoint 继续按其真实能力运行，不因文档刷新静默切模型。

> ⚠️ **前期估时不需要声音后端**：默认先跑 `voice_preflight.py prepare`，只生成 `timing_estimate.json`，不创建 WAV。可见口型镜头需要已批准表演/guide 轨；旁白、口外音、动作、空镜和蒙太奇可先按文本估时或画面推进。最终音色定妆通过后才批量渲染 final 音轨。

## 其它可调 env
- 配音质检适配器：`N2D_VOICE_ASR_CMD` / `N2D_VOICE_SPEAKER_CMD` / `N2D_VOICE_PROSODY_CMD`。命令模板可使用 `{audio}`、`{text}`、`{role}`，必须在 stdout 输出 JSON；未配置明确记 `unmeasured`，非零退出或无效 JSON 记 error。ASR JSON 至少含 `transcript`，流水线据参考台词计算 CER；阈值默认 `N2D_VOICE_CER_MAX=0.12`。
- 句间留拍：`LINE_GAP`(0.4) / `GAP_HOOK`(0.6) / `GAP_CLIMAX`(0.7) / `GAP_END`(1.0)。
- 零样本后端基础语速：`ZS_SPEED` 通用；也可按后端设 `<PREFIX>_SPEED`，例如 `GSV_SPEED=4.0`，或 `GPTSOVITS_SPEED=4.0`。GPT-SoVITS 官方 `api.py` 对慢速参考音/模型组合常需显式 speed；不要把“说快一点”写进台词 prompt。
- 系统音"机械感"FX：`SYS_AUDIO_FX`（默认 `asetrate=44100*0.9,aresample=44100,atempo=1.111,aecho=0.6:0.5:24:0.35,`）——设 `SYS_AUDIO_FX=''` 可禁用，或自定义滤镜链。仅作用于含「系统」的角色。

## 角色→音色映射
**优先级：`<作品根>/设定库/voicemap.json`（持久·跨集稳定）> 内置 demo 音色表 > env 覆盖（MiniMax: MM_SHEN/…）。**

### voicemap.json（新剧必建·治跨集音色漂）
内置音色表的角色名是 demo 写死的（柳娘子/小禾/太监/沈念）——**新剧的新角色会全部掉进默认嗓互相撞**，且跨集一致只靠每次手动 export 同一串 env，不持久化就漂。建 `设定库/voicemap.json` 一次绑定：
```json
{
  "沈念":   {"key":"SHEN",   "mm":"female-yujie",     "volc":"BV700_streaming", "speed":1.0,  "pitch":0,  "emo":"neutral"},
  "柳娘子": {"key":"LIU",    "mm":"female-chengshu",  "volc":"BV700_streaming", "speed":0.96, "pitch":-2, "emo":"serious"},
  "新角色": {"key":"HERO",   "mm":"male-qn-jingying", "speed":1.05, "pitch":2}
}
```
- 匹配=角色名**子串包含**（`"沈念"` 命中 `沈念旁白`）；命中即返回该配置，缺字段回退合理默认。
- `key` 同时决定零样本后端的参考音 env 名（`<PREFIX>_REF_<key>`），所以自定义角色也能各喂各的参考音。
- 缺 voicemap.json = 回退下面的内置 demo 映射（老作品零改动）。
- manifest 每句落 `音色键`/`voice_id`/`情绪_已应用`；`n2d-review` 机检跨集核对同角色音色一致性。
- **火山后端不逐句驱动情绪**（只用角色固定情绪/voicemap 的 `emo`）；需要逐句情绪时使用已被当前 endpoint probe 证明支持的 MiniMax/IndexTTS-2.5/CosyVoice 3/Fish Audio S2 路径。

### 内置 demo 音色表（缺 voicemap.json 时的回退）
默认见 render_voice.py 的音色表；均可 env 覆盖（MiniMax: MM_SHEN/MM_LIU/MM_XIAOHE/MM_TAIJIAN/MM_SYS/MM_NARR）。

### 零样本克隆 按角色分音色（CosyVoice 3/Fish Audio S2 或旧 Fish Speech/GPT-SoVITS/IndexTTS-2.5/VoxCPM2 通用）
`role_key(role)` 把角色名归到音色键：`SYS`(系统) / `LIU`(柳娘子) / `XIAOHE`(小禾) / `TAIJIAN`(太监) / `YAO`(含「妖」) / `NARR`(纯「旁白」) / `SHEN`(沈念·沈念旁白·默认)。
每个键各取参考音：优先 `<PREFIX>_REF_<KEY>` / `<PREFIX>_REF_<KEY>_TEXT`，缺则回退全局 `<PREFIX>_REF_AUDIO` / `<PREFIX>_REF_TEXT`，再缺则无参考(默认嗓)。`PREFIX` = 选中后端对应前缀：`COSY` / `FISH` / `GSV` / `IDX` / `VOX`（即上表 env 列里 `*_REF_*` 的前缀）。
例：`export FISH_REF_SHEN=.../SHEN.wav FISH_REF_SHEN_TEXT="<逐字文本>" FISH_REF_YAO=.../YAO.wav FISH_REF_YAO_TEXT="..."` → 沈念用 SHEN 嗓、妖用 YAO 嗓。⚠️ 参考音仅限本人嗓/已授权/纯合成。
**音色库便捷生成**：`创作区/制漫剧/<剧名>/设定库/voicebank/build_voicebank.sh` 用本机中文 say(Tingting/Meijia/Sinji) + ffmpeg 变调派生 7 个区分音色，产出 `*.wav` + 可 `source` 的 `_refs.env`。

## CosyVoice 3/GPT-SoVITS 本地服务
用户自行启动本地推理服务（端口/端点随 fork），把 URL 填进 COSYVOICE_URL/GPTSOVITS_URL，参考音频+参考文本填进对应 env。本 skill 通过 HTTP 调用，不负责启动服务。GPT-SoVITS 官方 `api.py` 可直接设 `GPTSOVITS_URL=http://127.0.0.1:9880`；无需另包 `/inference_zero_shot`。如果生成音轨显著超长，先调 `GPTSOVITS_SPEED`/`GSV_SPEED` 并重跑，缓存键会包含 speed，不会误复用旧慢音频。

## Fish Audio S2 / 旧 Fish Speech 本地服务
`~/fish-speech/n2d_fish_server.py`（conda env `fish-speech`）可继续暴露兼容的 `GET /inference_zero_shot?text=&prompt_text=&prompt_wav=`。`FISHSPEECH_URL` 指向的实际模型可能是旧 openaudio-s1-mini，也可能是新 S2 服务；启动和 env 合同保持兼容，但必须以 endpoint probe/执行收据记录实际模型（Fish Audio API 的 S2 候选 model id 为 `s2-pro`），不得因变量名未变就假定版本。
