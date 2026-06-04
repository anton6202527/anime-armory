# 配音后端

优先级：CosyVoice > FishSpeech > GPT-SoVITS(本地·设了 URL) > MiniMax(MINIMAX_API_KEY+GROUP_ID) > 火山(VOLC_APPID+TOKEN) > macOS say(占位)。缺凭证回退 say 并告警。

| 后端 | env | 说明 |
|---|---|---|
| CosyVoice | COSYVOICE_URL, COSY_REF_AUDIO, COSY_REF_TEXT | 本地零样本克隆服务；端点随 fork(常见 /inference_zero_shot，参数 text/prompt_text/prompt_wav) |
| FishSpeech | FISHSPEECH_URL, FISH_REF_AUDIO, FISH_REF_TEXT | 本地零样本克隆；用 n2d_fish_server.py 包一层 /inference_zero_shot(同 CosyVoice 契约)，内部走官方 TTSInferenceEngine(openaudio-s1-mini) |
| GPT-SoVITS | GPTSOVITS_URL, GSV_REF_AUDIO, GSV_REF_TEXT | 本地 inference api；零样本/微调（接入方式同 CosyVoice，端点随 fork） |
| MiniMax | MINIMAX_API_KEY, MINIMAX_GROUP_ID, MINIMAX_MODEL | 云；t2a_v2；克隆见 cloning.md |
| 火山 | VOLC_APPID, VOLC_TOKEN, VOLC_CLUSTER | 云 |
| say | （无） | macOS 占位，仅冒烟用 |

## 角色→音色映射
默认见 render_voice.py 的音色表；均可 env 覆盖（MiniMax: MM_SHEN/MM_LIU/MM_XIAOHE/MM_TAIJIAN/MM_SYS/MM_NARR；CosyVoice/GPT-SoVITS 通过 COSY_REF_AUDIO/COSY_REF_TEXT 指定参考音）。

## CosyVoice/GPT-SoVITS 本地服务
用户自行启动本地推理服务（端口/端点随 fork），把 URL 填进 COSYVOICE_URL/GPTSOVITS_URL，参考音频+参考文本填进对应 env。本 skill 通过 HTTP 调用，不负责启动服务。

## FishSpeech 本地服务
`~/fish-speech/n2d_fish_server.py`（conda env `fish-speech`，模型 openaudio-s1-mini）暴露与 CosyVoice 相同的 `GET /inference_zero_shot?text=&prompt_text=&prompt_wav=`。启动 `bash ~/fish-speech/start_n2d_fish.sh`(默认 :8081)，再 `export FISHSPEECH_URL=http://localhost:8081 FISH_REF_AUDIO=<参考音wav> FISH_REF_TEXT=<逐字文本>`。mac 为 MPS/CPU，较慢；16GB 机用 mini 模型。
