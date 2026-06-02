# 配音后端

优先级：CosyVoice / GPT-SoVITS(本地·设了 URL) > MiniMax(MINIMAX_API_KEY+GROUP_ID) > 火山(VOLC_APPID+TOKEN) > macOS say(占位)。缺凭证回退 say 并告警。

| 后端 | env | 说明 |
|---|---|---|
| CosyVoice | COSYVOICE_URL, COSY_REF_AUDIO, COSY_REF_TEXT | 本地零样本克隆服务；端点随 fork(常见 /inference_zero_shot，参数 text/prompt_text/prompt_wav) |
| GPT-SoVITS | GPTSOVITS_URL, GSV_REF_AUDIO, GSV_REF_TEXT | 本地 inference api；零样本/微调（接入方式同 CosyVoice，端点随 fork） |
| MiniMax | MINIMAX_API_KEY, MINIMAX_GROUP_ID, MINIMAX_MODEL | 云；t2a_v2；克隆见 cloning.md |
| 火山 | VOLC_APPID, VOLC_TOKEN, VOLC_CLUSTER | 云 |
| say | （无） | macOS 占位，仅冒烟用 |

## 角色→音色映射
默认见 render_voice.py 的音色表；均可 env 覆盖（MiniMax: MM_SHEN/MM_LIU/MM_XIAOHE/MM_TAIJIAN/MM_SYS/MM_NARR；CosyVoice/GPT-SoVITS 通过 COSY_REF_AUDIO/COSY_REF_TEXT 指定参考音）。

## CosyVoice/GPT-SoVITS 本地服务
用户自行启动本地推理服务（端口/端点随 fork），把 URL 填进 COSYVOICE_URL/GPTSOVITS_URL，参考音频+参考文本填进对应 env。本 skill 通过 HTTP 调用，不负责启动服务。
