# 行业通用视频 Prompt 规范（n2d-video）

> 核验日期：2026-07-10。本文把多家官方指南的稳定共识转成 n2d 可执行规范；平台能力、参数名和限制仍须在付费前按本项目的 backend evidence 复核。

## 结论

行业里没有一份跨厂商、强制统一的“视频 Prompt ISO 标准”。真正稳定的共同结构是：**主体/首帧真值 → 可见动作 → 镜头运动 → 时序/节奏 → 环境响应 → 落幅**；参考图、首尾帧、角色 ID、控制图、音频和 negative prompt 属于请求参数或独立输入，不应伪装成长篇自然语言。

n2d 因此采用两层对象：

1. **完整生产合同**：导演意图、continuity、在场链、身份、接缝、执行配方、Motion Control、音频、QC 全量保留并严格机检。
2. **后端编译提交 prompt**：只保留该后端需要的运动指令。runner 只能提交这一层，不能把完整合同直接交给模型。

## 官方证据与可迁移规则

- Runway 的 Image-to-Video 指南要求把重点放在运动上，避免重复描述输入图；Gen-4 指南强调简单、直接、正向措辞。落地为 `runway_motion_positive`：英文 motion-first，禁止负向命令和独立 negative prompt。[Runway Image-to-Video Prompting Guide](https://help.runwayml.com/hc/en-us/articles/48324313115155-Image-to-Video-Prompting-Guide)、[Runway Gen-4 Video Prompting Guide](https://help.runwayml.com/hc/en-us/articles/39789879462419-Gen-4-Video-Prompting-Guide)
- Google 的 Veo 指南把 prompt 拆成 cinematography、subject、action、context、style/ambience，并建议 negative prompt 描述不希望出现的元素，而不是写“don't/no”命令句。落地为 `veo_cinematography`：英文主 prompt + 单独元素列表。[Google Cloud Veo 3.1 Prompting Guide](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1/)、[Veo Video Generation Prompt Guide](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/video-gen-prompt-guide?hl=zh-CN)
- BytePlus/Seedance 的官方材料把图片/视频/音频引用作为多模态请求输入，并对 prompt 给出独立长度约束。落地为：参考资产走 `frame_inputs/reference_inputs/control_inputs/audio_inputs`，不在文本里堆路径和审计字段。[Seedance 2.0 Multimodal Video Generation](https://docs.byteplus.com/en/docs/modelark/1520757)、[Seedance API Reference](https://docs.byteplus.com/api/docs/ModelArk/2222480)
- Luma 的 API 以 keyframes 与 camera motion 分离表达。落地为 `english_motion_keyframe`：首尾/关键帧走请求参数，文本写动作与运镜。[Luma Video Generation](https://docs.lumalabs.ai/docs/video-generation)
- Adobe 的官方指南同样强调 shot type、subject、action、location 与 aesthetic，不支持把制作管线元数据整段塞入 prompt。[Adobe Firefly: Writing Effective Text Prompts for Video Generation](https://helpx.adobe.com/uk/firefly/web/work-with-audio-and-video/work-with-video/writing-effective-text-prompts-for-video-generation.html)

这些来源支持的是**结构原则**，不代表各平台参数永远不变。付费前仍按 `n2d-video` 的 backend evidence / smoke gate 核验当前 API 或 CLI。

## Canonical contract → compiler

`skills/n2d/_lib/video_prompt_compiler.py` 接受下列 canonical 字段：

```json
{
  "clip_id": "Clip_01",
  "backend": "seedance",
  "mode": "frames2video",
  "native_audio_policy": "none",
  "story_span_sec": 5.0,
  "edit_target_sec": 3.2,
  "frame_strategy": "first_last",
  "subject": ["CHAR_01"],
  "scene": "LOC_01",
  "primary_action": "角色抬眼并握紧刀柄",
  "camera_motion": "缓慢推近，尾端固定",
  "environment_motion": "衣袖只随抬手轻动",
  "rhythm": "克制推进，尾端留半拍",
  "end_state": "眼神定住，刀柄成为画面重心",
  "must_hold": ["身份、服装、轴线、光位"],
  "must_avoid": ["face drift", "extra characters", "text", "watermark"],
  "frame_inputs": ["first.png", "last.png"],
  "reference_inputs": ["CHAR_01/reference_group"],
  "control_inputs": [],
  "audio_inputs": []
}
```

输出固定为：

```json
{
  "kind": "n2d_compiled_video_prompt",
  "version": 2,
  "profile_version": "2026-07-10.2",
  "clip_id": "Clip_01",
  "backend": "seedance",
  "profile": "zh_motion_first",
  "mode": "frames2video",
  "language": "zh",
  "native_audio_policy": "none",
  "frame_strategy": "first_last",
  "duration_plan": {
    "story_span_sec": 5.0,
    "edit_target_sec": 3.2,
    "backend_request_sec": 4.0,
    "action_start_sec": 0.25,
    "action_end_sec": 2.7,
    "hold_end_sec": 3.2,
    "trim_mode": "trim_tail",
    "requires_split": false
  },
  "prompt": "从首帧连续运动到尾帧。主动作：……镜头：……时间：0.25-2.70秒完成主动作，保持落幅到3.20秒；其余只保持供裁切。",
  "negative_prompt": "",
  "request_controls": {
    "frame_inputs": [],
    "reference_inputs": [],
    "control_inputs": [],
    "audio_inputs": []
  },
  "source_contract_sha256": "...",
  "lint": {"errors": [], "warnings": []}
}
```

## Profile 规则

| profile | 后端 | 主语言 | 主 prompt | negative |
|---|---|---|---|---|
| `zh_motion_first` | Dreamina/即梦、Seedance、Kling/可灵、Wan、generic | 中文 | I2V：主动作 + 运镜 + 可选环境响应 + 节奏 + 落幅 + 最短正向保持；T2V 才补主体/场景 | 必要的短保持句可内联；不复制完整 negative 合同 |
| `runway_motion_positive` | Runway Gen-4 | 英文 | 只描述希望发生的运动；不重复输入图；不用否定命令 | 必须为空 |
| `veo_cinematography` | Veo/Gemini | 英文 | subject/action/camera/context/rhythm/end hold | 单独的元素列表，不拼入主 prompt |
| `english_motion_keyframe` | Luma/Pika | 英文 | keyframe-aware action + camera motion | 单独字段 |

后端切换不是翻译动作，而是**重新编译**。如果 route 由 Seedance 切到 Runway/Veo，必须重跑 compiler；gate/runner 发现 backend/profile 不匹配时停止，不偷偷沿用。

英文 profile 不做词典式伪翻译。canonical contract 可提供 `primary_action_en/camera_motion_en/environment_motion_en/end_state_en/subject_en/scene_en/rhythm_en`；若只提供中文，compiler 保留事实原文、把 `language` 标成 `mixed` 并 WARN，避免自动错译人物动作或剧情事实。正式海外投递应补齐这些 `*_en` 字段后重新编译。

## 帧策略与三套时钟

`frame_strategy` 不是“默认塞几张图”，而是由分镜语法与后端能力共同决定：

- `first_only`：低风险单拍、后端只收首帧；
- `first_last`：一个连续动作，需要锁定起落状态；这是最常用的跨后端稳定公约数；
- `native_multiframe`：高风险连续动作且后端单次请求原生消费 3+ 时间轴帧；
- `split_relay`：高风险连续动作，但后端只收首尾两帧，需显式拆段接力；
- `edit_cut`：`shots[]` 已声明景别/机位变化；每个 shot 是独立 take，不能把多个镜位误当成一条连续插值视频；
- `edit_cut_pending_assets` / `reroute_required`：缺分镜边界图或后端能力不足，付费前 BLOCK。

“至少三帧”不是行业统一要求。普通单拍不默认生产中帧；中段锚只服务高风险连续动作、明确 opt-in 或编辑切点。`use=qc/reference` 的图只参与验收，runner 不得偷偷当时间轴帧提交。

时长必须分成三套互不覆盖的时钟：

1. `story_span_sec`：父剧情段覆盖的叙事/对白跨度；
2. `edit_target_sec`：本条物理 take 在成片中真正要占的时长；
3. `backend_request_sec`：后端允许提交的离散档位或区间。

例如剪辑只要 2.1s，而后端最短只能请求 4s：动作必须在 2.1s 内完成，2.1-4s 只保持落幅，compose 默认裁尾到 2.1s。不得把 4s 原片用 `setpts` 整段压回 2.1s，也不得反过来把 2.1s 情节拉长成 4s。只有创作明确要求慢动作/加速时才显式使用 time-warp。

## 模式规则

- `image2video`：不重述角色、服装、场景、光位和画风；从首帧真值出发，只写怎么动。
- `frames2video` / first-last：写“从首帧连续运动到尾帧”，动作与落幅不能抵触真实尾帧。
- `multiframe`：写按关键帧顺序连续运动；每段 transition prompt 只描述该段到达动作，不重复父 Clip 全合同。
- `text2video`：无视觉锚时才补主体、场景、镜头、动作、氛围和风格。
- `native_av`：主 prompt 必须明确“只生成已登记画内台词与口型，不添加旁白或额外台词”；runner 付费前追加本 Clip 的 dialogue fact contract。

## 硬闸与建议项

确定性 BLOCK：

- compiled block 或 metadata 缺失；
- 缺主动作或缺镜头运动；
- compiler backend/mode/native_audio_policy 与 route 不一致；
- I2V/frames2video 的执行配方没有 frame inputs；
- Runway 主 prompt 出现 `no/don't/avoid/不要/禁止` 等负向命令，或带独立 negative prompt；
- `native_speech` 没有“只允许已登记画内台词”的守卫，或和 `no_native_speech` 同时出现；
- 来源合同 SHA 非法，无法追溯。
- v2 缺 `frame_strategy` 或 `duration_plan`，或后端请求短于剪辑目标却未声明拆段；
- `edit_cut_pending_assets` / `reroute_required` 仍未解决。

只 WARN：

- 字符数超过 profile 建议值；
- 分句过多；
- 动作/运镜虽存在但仍偏抽象。

字符阈值不能直接决定好坏：某些高动作镜确实需要稍长的时序描述。gate 只把冗长当优化提示，不因任意长度阈值烧掉一条本可用的 prompt。

## 禁止回退到旧做法

- 不再维护“中文详细版 + 英文兜底版”两套执行真值。
- 不把 `video_model_routes.json`、identity registry、在场链、接缝包、执行配方、文件路径或 QC 清单整段复制到主 prompt。
- 不为所有场景硬注入月光、火把、低雾、尘土、衣袂等动态细节；storyboard 没登记就保持背景稳定。
- 不把普通镜统一写成 `audio_intent=none`：native_speech / ambience / lipsync condition 必须按 route 分支生成。
- 不用长 prompt 代替首尾帧、reference group、角色 ID、Face Lock、control manifest 或拆镜。
