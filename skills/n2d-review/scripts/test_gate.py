import json
from pathlib import Path

import gate


GOOD_SHOT = """## 镜头 1（冷开场）🔑关键镜

**目标存档**：`出图/第1集/图片/镜头1_冷开场.png`
**参考图**（多图参考派生铁律）：
- `出图/共享/图片/定妆_沈念.png`（正脸主参考，强度 0.8）
- `出图/共享/图片/定妆_沈念_侧.png`（角度锚，强度 0.55）
- `出图/共享/图片/定妆_沈念_半身.png`（服装锚，强度 0.5）
- `出图/共享/图片/定妆_冷宫寝殿.png`（场景定妆，强度 0.45）

**视线方向**：画右（与反打镜 Clip 2 对位，守本场轴线）
**光位锚**：继承本场光位锚（主光：画左前烛光顶侧光 / 3000K 暖 / 动机=残烛），本镜不改光
**起幅·运动余量**：本镜为 Clip 1 首帧=起幅（顶点交尾帧），按缓慢推近预留构图余量、上下留 lead room
**专项镜头模板**：dialogue_shot_reverse；blocking=沈念画左，柳娘子画右；camera_rule=守轴线；continuity_must=脸型发型不漂；negative=不要换脸。
**资产身份注册层**：`CHAR_SHEN/常态`；reference_group=正/侧/半身/三视图；angle_policy=front/three_quarter allowed；drift_forbidden=face_shape/hairstyle/outfit_palette
**资产引用注册层**：`LOC_01` 冷宫寝殿；从 `出图/共享/asset_registry.json` 继承 reference_group / constraints / drift_forbidden；锁本场 layout/axis/light_anchor。
**近景/反打身份锁定**：本镜是 CU 近景，必须引用 `定妆_沈念_脸部特写.png` 或表情参考；锁脸型、五官比例、发型发髻、标志配饰和服装配色，不得换脸。
**尾帧接力生成方式**：正反打/表情尾帧必须以同镜首帧或上一张成图 image2image 图生图为母图，不得纯文生图；只改表情/眼神/嘴角，不重画演员脸、发髻、配饰和服装。

**导演视角八维**
| 维度 | 本镜填什么 |
|---|---|
| ① 镜头 | CU + 浅景深 |
| ② 机位 | 微俯视 |
| ③ 人物 | 锚点句：凤眼薄唇·乌黑半披发带·月白旧宫装 |
| ④ 动作 | 抬眼 |
| ⑤ 场景 | 冷宫寝殿 |
| ⑥ 光影 | 侧逆光 |
| ⑦ 情绪 | 克制紧张 |
| ⑧ 画质 | 9:16 cinematic |

### 正向 prompt（中文）
```text
CU 微俯视，沈念带锚点句，凤眼薄唇·乌黑半披发带·月白旧宫装，服装配色一致。
```

### 正向 prompt（英文）
```text
Close-up, slight high angle, same face and costume, anchor phrase preserved.
```

### 负向 prompt
```text
不要换脸、不要换衣、不要改发型、不要文字/logo。风格禁忌（继承本集基础视觉风格契约）：照片皮肤、3D塑料、风格跳变。
```

### 检查清单（八维自查·最易漏②机位/⑥光影/⑦张力）
1. ✅ 脸型与定妆一致（③人物锚点句已拼）
2. ✅ 服装配色一致 + 此刻状态对（③）
3. ✅ 景别符合分镜要求 + 机位有理由非默认正面平视（①②）
4. ✅ 光影在叙事非均匀打亮（⑥）
5. ✅ 表情符合本镜情绪 + 张力/色调一致（⑦）

### 自检（生成后逐张过 · 落档闸门）
**自检**（轻微偏差放行，只命中硬伤才重抽）：
- [ ] 核心人/物/场景无错位
- [ ] 角色脸/妆造未漂移（对照 定妆_沈念.png 主参考；主要人物零漂移容忍）
- [ ] 无硬性禁忌
- 重抽预算：预算充足档，主要人物/关键镜严格自检，出到满意为止 ｜ 实抽__次 → ⬜过 ⬜重抽 ⬜满意落档
"""

GOOD_VIDEO_CLIP = """## Clip 1（时长 5.0s · 镜头1） **节奏**：铺垫·长镜 **张力**：克制

**首帧**：`出图/第1集/图片/镜头1_冷开场.png`
**尾帧**：`出图/第1集/图片/镜头1_end.png`
**场景**：冷宫寝殿 / 夜 / 内
**导演意图**：这条镜头不是展示人物漂亮，而是让观众感到沈念正在压住恐惧，镜头慢慢逼近她的眼神。
**起幅**：承接上一 Clip 的 end_state，沈念半坐在床榻阴影里，柳娘子在画面右后方虚焦，鸩酒托盘在前景画左。
**落幅**：结尾停在沈念压住呼吸后的眼神，画面重心落到左腕疤，可接下一镜铜镜或手部特写。
**场面调度**：沈念保持画面左前，柳娘子保持右后虚焦，镜头不越轴，烛火在画面左前，床幔在右侧形成压迫。
**表演节拍**：[0-2s] 沈念急促呼吸；[2-4s] 缓慢抬眼；[4-5s] 呼吸压住，眼神定住。
**运动精修**：幅度=极小；能量=克制蓄压；身体守卫=肩颈和下巴不大幅扭动，脸部轮廓不拉伸，手部不穿过衣襟。
**环境交互**：残烛光在眼下轻轻跳动，床幔阴影随呼吸微动，前景托盘保持不位移。
**模型路由**：shot_type=dialogue_closeup；primary_backend=dreamina；fallback_backends=seedance,kling；mode=image2video；native_audio_policy=none；identity_requirement=reference_group；risk_flags=mouth_visible；rationale=普通近景先用项目默认后端，失败切身份/运动更强后端；degrade_plan=改侧脸或反应镜，必要时切 seedance/kling 重跑
**角色身份注册层**：`CHAR_SHEN/常态`；目标后端 dreamina=fallback_reference_group；fallback reference_group=出图/共享/图片/定妆_沈念.png + 侧面/半身参考；高危角度=deep_shadow；禁漂项=face_shape/hairstyle/outfit_palette
**近景/反打身份锁定**：本镜是说话近景；优先引用 expressions/脸部特写，缺脸部特写时用正脸 front + 侧面 + 半身 reference_group；锁脸型、五官比例、发型发髻、标志配饰、服装配色；只允许眼神和嘴角小幅变化，脸漂则降级 MCU/侧脸/反应镜。
**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=no_native_speech；compose_policy=丢弃；review=生成后确认无原生人声
**衔接设计**：
- 入点：承接上一 Clip 的动作和视线方向
- 出点：停在沈念左腕疤和眼神
- 转场：eyeline cut
- 连贯性：轴线、人物左右站位、光线和服装保持一致

**continuity**：
- start_state：上一 Clip 的 end_state
- action：沈念只做急促呼吸到缓慢抬眼这一条动作链
- end_state：沈念压住呼吸，眼神定住，画面重心落在左腕疤
- constraints：服装发型、人物左右站位、轴线方向、烛火光线、冷宫背景布局保持一致
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要生成原生人声

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
```text
continuity:
  start_state: 上一 Clip 的 end_state
  action: 沈念只做急促呼吸到缓慢抬眼这一条动作链
  end_state: 沈念压住呼吸，眼神定住，画面重心落在左腕疤
  constraints: 服装发型、人物左右站位、轴线方向、烛火光线、冷宫背景布局保持一致
  negative: 不要换脸、不要换衣、不要新增人物、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要生成原生人声
运动精修约束：幅度极小，能量克制，脸部轮廓和发髻不拉伸，手部不穿模；
环境交互约束：残烛光在眼下轻跳，床幔阴影随呼吸微动；
模型路由约束：读取 video_model_routes.json；本镜 primary_backend=dreamina，fallback=seedance,kling，mode=image2video，native_audio_policy=none，identity_requirement=reference_group；prompt 只使用 dreamina 支持的 image2video 能力；失败按 degrade_plan 改侧脸或切 fallback 重跑；
身份锁定约束：读取 identity_registry.json；dreamina 回退首帧+尾帧+reference_group；保持 drift_forbidden=face_shape/hairstyle/outfit_palette；
近景身份锁定约束：近景优先脸部特写/表情参考；缺 reference_controls 时只做低幅度眼神和嘴角变化，不大幅转头，不重绘五官，配角近景不稳则降级 MCU/OTS/侧脸；
原生音画约束：默认禁止原生人声，不生成对白/旁白/哼唱；本镜 compose_policy=丢弃；
人物运动：沈念急促呼吸后缓慢抬眼，表情从惊惧压成克制；
镜头运动：略俯 MCU 缓慢推近 0.5x，结尾稳定停住；
动态细节：残烛火光在脸侧跳动，床幔阴影轻颤，冷雾贴地流动；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按 eyeline cut 服务下一镜；
声音约束：无对白、无旁白、不要生成原生人声；
```

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
```text
continuity:
  start_state: previous end_state
  action: controlled breathing into a slow eye raise
  end_state: eyes held still, wrist scar becomes the visual focus
  constraints: preserve face, costume, screen direction, lighting, and room layout
  negative: no face change, no costume change, no new characters, no text, no native voice
character motion: Shen Nian breathes sharply, slowly raises her eyes, then holds a restrained stare;
camera motion: slight high-angle MCU, slow 0.5x dolly in, then hold;
dynamic detail: candle flicker, bed curtain shadow tremble, low cold mist;
continuity constraint: begin from continuity.start_state, perform only continuity.action, end on continuity.end_state, preserve continuity.constraints, avoid continuity.negative;
audio constraint: no dialogue, no narration, no generated native voice;
```

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 导演意图/起幅/落幅/场面调度/表演节拍齐全
2. ✅ ④人物运动：动作链明确、幅度可控、可由首帧自然推出
3. ✅ ②镜头运动：推/拉/跟/环绕/固定等词明确，速度词明确
4. ✅ 动态细节 ≥1 条，且不改首帧设定
5. ✅ ⑦张力：运镜与节奏一致

### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性
- [ ] 人物运动自然
- [ ] 镜头运动符合 prompt
- [ ] 衔接落点可接下一 Clip
"""


def setup_function():
    gate.findings.clear()


def test_preflight_gate_stages_are_registered():
    assert "image_preflight" in gate.GATE_STAGES
    assert "video_preflight" in gate.GATE_STAGES


def test_image_preflight_reuses_image_checks(monkeypatch, tmp_path):
    root = tmp_path / "work"
    root.mkdir()
    calls = []

    def mark(name):
        def _inner(*args, **kwargs):
            calls.append((name, args))

        return _inner

    monkeypatch.setattr(gate, "is_native_av_production", lambda _root: False)
    for name in [
        "check_compliance_manifest",
        "require_progress",
        "check_progress_artifact_signoff",
        "check_placeholder_policy",
        "check_voiceover_fingerprint",
        "check_image_ai_policy",
        "check_identity_registry",
        "check_costume_registry_reconcile",
        "check_asset_reference_registry",
        "check_storyboard_contract",
        "check_storyboard_visual_contract",
        "check_storyboard_style_contract",
        "check_cross_episode_style",
        "check_storyboard_special_templates",
        "check_image_prompt_overview",
        "check_prompt_checklists",
        "check_semantic_lineage",
        "check_state_continuity",
        "check_shared_image_index",
        "check_common_image_prompts",
        "check_cinematic_optical_continuity",
        "check_shot_scale_progression",
        "check_physical_scale_audit",
    ]:
        monkeypatch.setattr(gate, name, mark(name))

    gate.run(str(root), "第1集", "image_preflight")

    assert [name for name, _ in calls[:3]] == [
        "check_compliance_manifest",
        "require_progress",
        "check_progress_artifact_signoff",
    ]
    assert ("check_placeholder_policy", (str(root), "第1集", "image")) in calls
    assert ("check_prompt_checklists", (str(root), "第1集", "image")) in calls


def test_video_preflight_reuses_video_checks(monkeypatch, tmp_path):
    root = tmp_path / "work"
    root.mkdir()
    calls = []

    def mark(name):
        def _inner(*args, **kwargs):
            calls.append((name, args))

        return _inner

    monkeypatch.setattr(gate, "is_native_av_production", lambda _root: False)
    for name in [
        "check_compliance_manifest",
        "require_progress",
        "check_progress_artifact_signoff",
        "check_placeholder_policy",
        "check_voiceover_fingerprint",
        "check_identity_registry",
        "check_asset_reference_registry",
        "check_identity_adapter_matrix",
        "check_route_identity_readiness",
        "check_storyboard_contract",
        "check_storyboard_style_contract",
        "check_storyboard_special_templates",
        "check_image_assets",
        "check_input_frame_qc",
        "check_video_prompt_frames",
        "check_multimodal_continuity",
        "check_prompt_checklists",
        "check_video_stage_raw_output_policy",
        "check_contract_inheritance",
        "check_semantic_lineage",
        "check_state_continuity",
    ]:
        monkeypatch.setattr(gate, name, mark(name))

    gate.run(str(root), "第1集", "video_preflight")

    assert [name for name, _ in calls[:3]] == [
        "check_compliance_manifest",
        "require_progress",
        "check_progress_artifact_signoff",
    ]
    assert ("check_placeholder_policy", (str(root), "第1集", "video")) in calls
    assert "check_image_assets" in [name for name, _ in calls]
    assert "check_video_stage_raw_output_policy" in [name for name, _ in calls]


def test_video_gate_runs_multimodal_p2_before_video_prompt(monkeypatch, tmp_path):
    root = tmp_path / "work"
    root.mkdir()
    calls = []

    def mark(name):
        def _inner(*args, **kwargs):
            calls.append(name)

        return _inner

    for name in [
        "check_compliance_manifest",
        "require_progress",
        "check_placeholder_policy",
        "check_identity_registry",
        "check_asset_reference_registry",
        "check_identity_adapter_matrix",
        "check_storyboard_contract",
        "check_storyboard_style_contract",
        "check_storyboard_special_templates",
        "check_image_assets",
        "check_input_frame_qc",
        "check_video_prompt_frames",
        "check_multimodal_continuity",
        "check_prompt_checklists",
        "check_video_stage_raw_output_policy",
        "check_semantic_lineage",
        "check_state_continuity",
    ]:
        monkeypatch.setattr(gate, name, mark(name))

    gate.run(str(root), "第1集", "video")

    assert "check_multimodal_continuity" in calls
    assert calls.index("check_image_assets") < calls.index("check_multimodal_continuity")
    assert calls.index("check_multimodal_continuity") < calls.index("check_prompt_checklists")
    assert calls.index("check_prompt_checklists") < calls.index("check_video_stage_raw_output_policy")


def test_good_character_shot_prompt_passes_strict_structure():
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, GOOD_SHOT)
    assert gate.findings == []


def test_character_shot_missing_anchor_is_blocked():
    shot = GOOD_SHOT.replace("锚点句：", "").replace("锚点句已拼", "人物已拼")
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "角色一致性" and "锚点句" in f["msg"] for f in gate.findings)


def test_shot_without_reference_block_is_blocked_as_text2image():
    shot = GOOD_SHOT.replace("**参考图**（多图参考派生铁律）：\n- `出图/共享/图片/定妆_沈念.png`（正脸主参考，强度 0.8）\n- `出图/共享/图片/定妆_沈念_侧.png`（角度锚，强度 0.55）\n- `出图/共享/图片/定妆_沈念_半身.png`（服装锚，强度 0.5）\n- `出图/共享/图片/定妆_冷宫寝殿.png`（场景定妆，强度 0.45）\n", "")
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert any(f["sev"] == gate.BLOCK and "参考图" in f["msg"] for f in gate.findings)


def test_character_shot_missing_sightline_is_blocked():
    shot = GOOD_SHOT.replace("**视线方向**：画右（与反打镜 Clip 2 对位，守本场轴线）\n", "")
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "轴线一致性" and "视线方向" in f["msg"] for f in gate.findings)


def test_shot_missing_light_anchor_is_blocked():
    shot = GOOD_SHOT.replace(
        "**光位锚**：继承本场光位锚（主光：画左前烛光顶侧光 / 3000K 暖 / 动机=残烛），本镜不改光\n", ""
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "光影一致性" and "光位锚" in f["msg"] for f in gate.findings)


def test_shot_missing_motion_room_is_blocked():
    shot = GOOD_SHOT.replace(
        "**起幅·运动余量**：本镜为 Clip 1 首帧=起幅（顶点交尾帧），按缓慢推近预留构图余量、上下留 lead room\n", ""
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "首帧起幅" and "运动余量" in f["msg"] for f in gate.findings)


def test_character_shot_missing_identity_registry_constraint_is_blocked():
    shot = GOOD_SHOT.replace(
        "**资产身份注册层**：`CHAR_SHEN/常态`；reference_group=正/侧/半身/三视图；angle_policy=front/three_quarter allowed；drift_forbidden=face_shape/hairstyle/outfit_palette\n",
        "",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "reference_group" in f["msg"] for f in gate.findings)


def test_character_shot_missing_character_id_binding_is_blocked():
    shot = GOOD_SHOT.replace("`CHAR_SHEN/常态`；", "")
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "角色 ID" in f["msg"] for f in gate.findings)


def test_shot_missing_scene_asset_id_binding_is_blocked():
    shot = GOOD_SHOT.replace(
        "**资产引用注册层**：`LOC_01` 冷宫寝殿；从 `出图/共享/asset_registry.json` 继承 reference_group / constraints / drift_forbidden；锁本场 layout/axis/light_anchor。\n",
        "",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产引用注册层" and "LOC_xx" in f["msg"] for f in gate.findings)


def test_shot_missing_prop_asset_id_binding_is_blocked():
    shot = GOOD_SHOT.replace(
        "- `出图/共享/图片/定妆_冷宫寝殿.png`（场景定妆，强度 0.45）\n",
        "- `出图/共享/图片/定妆_冷宫寝殿.png`（场景定妆，强度 0.45）\n- `出图/共享/图片/定妆_斑驳铜镜.png`（道具锚，强度 0.45）\n",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产引用注册层" and "PROP_xx" in f["msg"] for f in gate.findings)


def test_generic_scene_prop_anchor_phrase_does_not_require_prop_id():
    shot = GOOD_SHOT.replace(
        "**资产引用注册层**：`LOC_01` 冷宫寝殿；从 `出图/共享/asset_registry.json` 继承 reference_group / constraints / drift_forbidden；锁本场 layout/axis/light_anchor。\n",
        "**资产引用注册层**：`LOC_01` 冷宫寝殿；从 `出图/共享/asset_registry.json` 继承 reference_group / constraints / drift_forbidden；锁本场 layout/axis/light_anchor。\n锚点句：无人物或人物不露脸：以场景/道具锚为主\n",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "资产引用注册层" and "PROP_xx" in f["msg"] for f in gate.findings)


def test_closeup_character_shot_missing_fine_identity_lock_is_blocked():
    shot = GOOD_SHOT.replace(
        "**近景/反打身份锁定**：本镜是 CU 近景，必须引用 `定妆_沈念_脸部特写.png` 或表情参考；锁脸型、五官比例、发型发髻、标志配饰和服装配色，不得换脸。\n",
        "",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "角色一致性" and "近景身份锁定" in f["msg"] for f in gate.findings)


def test_closeup_character_tail_missing_i2i_continuity_lock_is_blocked():
    shot = GOOD_SHOT.replace(
        "**尾帧接力生成方式**：正反打/表情尾帧必须以同镜首帧或上一张成图 image2image 图生图为母图，不得纯文生图；只改表情/眼神/嘴角，不重画演员脸、发髻、配饰和服装。\n",
        "",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "角色一致性" and "图生图接力" in f["msg"] for f in gate.findings)


def test_shot_negative_missing_style_forbidden_is_blocked():
    # 负向 prompt 不继承 style_contract.风格禁忌 → 风格一致性 BLOCK（shot 级防不住风格漂）
    shot = GOOD_SHOT.replace(
        "不要换脸、不要换衣、不要改发型、不要文字/logo。风格禁忌（继承本集基础视觉风格契约）：照片皮肤、3D塑料、风格跳变。",
        "不要换脸、不要换衣、不要改发型、不要文字/logo。",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "风格一致性" and "风格禁忌" in f["msg"] for f in gate.findings)


def test_image_overview_requires_episode_visual_contract(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出图" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "00_总览.md").write_text("# 总览\n\n## 本集图数统计\n", encoding="utf-8")

    gate.check_image_prompt_overview(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "视觉契约" and "本集视觉一致性契约" in f["msg"] for f in gate.findings)


def test_image_overview_contract_missing_field_is_blocked(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出图" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    # 有契约标题与四字段，独缺「景别阶梯」
    (prompt_dir / "00_总览.md").write_text(
        "# 总览\n\n## 本集视觉一致性契约\n- 色调基线：冷青\n- 场景光位锚：烛光顶侧光\n"
        "- 场景轴线·视线：沈念居左\n- 角色状态演进表：镜3起左颊伤\n",
        encoding="utf-8",
    )

    gate.check_image_prompt_overview(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "视觉契约" and "景别阶梯" in f["msg"] for f in gate.findings)


def _write_storyboard(tmp_path, vc):
    import json
    root = tmp_path / "制漫剧" / "测试剧"
    sb_dir = root / "脚本" / "第1集"
    sb_dir.mkdir(parents=True)
    data = {"episode": 1, "policy": {"tailframe_default": True}, "clips": []}
    if vc is not None:
        data["visual_contract"] = vc
    (sb_dir / "storyboard.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(root)


def _write_storyboard_with_contracts(tmp_path, vc, sc, legacy=False):
    import json
    root = tmp_path / "制漫剧" / "测试剧"
    sb_dir = root / "脚本" / "第1集"
    sb_dir.mkdir(parents=True)
    data = {"episode": 1, "policy": {"tailframe_default": True}, "clips": []}
    if vc is not None:
        data["visual_contract"] = vc
    if sc is not None:
        data["cinematic_contract" if legacy else "style_contract"] = sc
    (sb_dir / "storyboard.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(root)


def _write_storyboard_with_clips(tmp_path, clips):
    import json
    root = tmp_path / "制漫剧" / "测试剧"
    sb_dir = root / "脚本" / "第1集"
    sb_dir.mkdir(parents=True)
    data = {"episode": 1, "policy": {"tailframe_default": True}, "clips": clips}
    (sb_dir / "storyboard.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(root)


def _identity_registry(overrides=None):
    data = {
        "kind": "n2d_asset_identity_registry",
        "version": 1,
        "characters": [
            {
                "id": "CHAR_SHEN",
                "name": "沈念",
                "scope": "全篇",
                "forms": [
                    {
                        "form": "常态",
                        "asset_key": "沈念",
                        "anchor_phrase": "凤眼薄唇·乌黑半披发带·月白旧宫装",
                        "reference_group": {
                            "front": "出图/共享/图片/定妆_沈念.png",
                            "side": "出图/共享/图片/定妆_沈念_侧.png",
                            "back": "出图/共享/图片/定妆_沈念_背.png",
                            "outfit": "出图/共享/图片/定妆_沈念_半身.png",
                            "turnaround": "出图/共享/图片/定妆_沈念_三视图.png",
                            "expressions": [],
                        },
                        "identity_adapters": {
                            "image": {
                                "codex": {"mode": "reference_group", "status": "fallback_reference_group"},
                                "kling": {"mode": "character_id", "status": "unregistered", "id": ""},
                            },
                            "video": {
                                "dreamina": {"mode": "first_last_frame", "status": "fallback_reference_group"},
                                "kling": {"mode": "character_id", "status": "unregistered", "id": ""},
                                "seedance": {"mode": "face_lock", "status": "unregistered", "reference": ""},
                            },
                            "lora": {
                                "status": "not_needed",
                                "base_model": "",
                                "model_path": "",
                                "trigger": "",
                                "dataset": "",
                            },
                        },
                        "angle_policy": {
                            "allowed": ["front", "three_quarter", "side", "back", "over_shoulder"],
                            "risky": ["extreme_top", "extreme_low", "face_too_small", "deep_shadow"],
                            "requires_extra_reference": ["side", "back", "full_body_action"],
                        },
                        "drift_forbidden": ["face_shape", "hairstyle", "outfit_palette", "body_type"],
                    }
                ],
            }
        ],
    }
    if overrides:
        form = data["characters"][0]["forms"][0]
        for key, value in overrides.items():
            form[key] = value
    return data


def _write_identity_registry(tmp_path, data=None, make_assets=False):
    import json
    root = tmp_path / "制漫剧" / "测试剧"
    registry_dir = root / "出图" / "common"
    registry_dir.mkdir(parents=True)
    registry = _identity_registry() if data is None else data
    (registry_dir / "identity_registry.json").write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    if make_assets:
        for rel in registry["characters"][0]["forms"][0]["reference_group"].values():
            if not isinstance(rel, str) or not rel.endswith(".png"):
                continue
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"\x89PNG\r\n\x1a\n")
    return str(root)


def _asset_registry():
    return {
        "kind": "n2d_asset_reference_registry",
        "version": 1,
        "assets": [
            {
                "id": "LOC_01",
                "type": "scene",
                "name": "冷宫寝殿",
                "scope": "第1集起复用",
                "spatial_layout": "床榻在画左深处，门口在画右，铜镜位于画左前景，人物走位沿床榻到门口横轴",
                "reference_group": {"primary": "出图/共享/图片/定妆_冷宫寝殿.png"},
                "constraints": {
                    "layout": "床榻到门口横轴",
                    "axis": "沈念画左，柳娘子画右",
                    "light_anchor": "画左前 3000K 残烛暖主光；画右后冷月背光",
                    "lighting_signature": "3000K 残烛暖主光 + 冷月背光，低饱和冷暖对撞",
                },
                "drift_forbidden": ["layout", "axis", "light_direction", "era_style"],
            },
            {
                "id": "PROP_01",
                "type": "prop",
                "name": "斑驳铜镜",
                "scope": "第1集起复用",
                "owner": "沈念",
                "current_state": "床榻旁，镜面斑驳不可照出清晰倒影",
                "lifecycle": "第1集起作为沈念身份线索反复出现，不损毁不换型",
                "reference_group": {"primary": "出图/共享/图片/定妆_斑驳铜镜.png"},
                "constraints": {"structure": "单镜面，斑驳铜绿镜框，无多镜面/重复镜框"},
                "drift_forbidden": ["single_mirror_surface", "frame_shape", "era_style"],
            },
        ],
    }


def _write_asset_registry(tmp_path, data=None, make_assets=False):
    import json
    root = tmp_path / "制漫剧" / "测试剧"
    registry_dir = root / "出图" / "共享"
    registry_dir.mkdir(parents=True, exist_ok=True)
    registry = _asset_registry() if data is None else data
    (registry_dir / "asset_registry.json").write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    if make_assets:
        for asset in registry.get("assets", []):
            ref = asset.get("reference_group", {}) if isinstance(asset, dict) else {}
            rel = ref.get("primary", "") if isinstance(ref, dict) else ""
            if not isinstance(rel, str) or not rel.endswith(".png"):
                continue
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"\x89PNG\r\n\x1a\n")
    return str(root)


def _good_compliance(root, *, status_overrides=None):
    data = {
        "kind": "n2d_compliance_manifest",
        "version": 1,
        "distribution_intent": "publish_candidate",
        "rights": {
            "source_text": {"status": "original", "evidence": "作者自有项目"},
            "adaptation": {"status": "original", "evidence": "同源改编"},
            "music_bgm": {"status": "not_applicable"},
            "sfx": {"status": "not_applicable"},
            "fonts": {"status": "not_applicable"},
        },
        "character_likeness": {
            "characters": [
                {"character_id": "CHAR_SHEN", "status": "synthetic_character", "evidence": "原创合成角色"}
            ],
        },
        "voice": {
            "status": "synthetic_voice",
            "uses_voice_clone": False,
            "authorization_status": "not_applicable",
            "evidence": "未使用真人参考音",
        },
        "ai_disclosure": {
            "required": True,
            "visible_label": {"status": "planned", "text": "AI 合成"},
            "metadata_label": {"status": "planned"},
            "c2pa_or_content_credentials": {"status": "not_supported"},
            "hidden_or_platform_watermark": {"status": "planned"},
        },
        "watermark": {
            "ai_visible": {"status": "planned"},
            "metadata": {"status": "planned"},
            "final_assets": [],
        },
        "platform_review": {
            "targets": [{
                "platform": "抖音",
                "region": "CN",
                "language": "zh",
                "policy_profile": "douyin_cn_ai_drama_2026-06-08",
                "profile_checked_at": "2026-06-08",
                "copyright_review": "ready",
                "ai_disclosure_upload": "ready",
                "content_rating_review": "ready",
                "requires_localization": False,
            }],
        },
        "localization": {
            "status": "not_applicable",
            "subtitle_languages": ["zh"],
        },
        "regulatory_filing": {
            "regime": "NRTA_网络微短剧",
            "applicable": True,
            "tier": "其他",
            "planning_filing_no": "网微剧备字(2026)第001号",
            "release_filing_no": "网微剧上字(2026)第001号",
            "pre_broadcast_review": "ready",
            "filed_at": "2026-06-01",
            "notes": "",
        },
    }
    if status_overrides:
        for path, value in status_overrides.items():
            cur = data
            parts = path.split(".")
            for part in parts[:-1]:
                if part.isdigit():
                    cur = cur[int(part)]
                else:
                    cur = cur[part]
            cur[parts[-1]] = value
    comp = root / "合规"
    comp.mkdir(parents=True, exist_ok=True)
    (comp / "compliance_manifest.json").write_text(__import__("json").dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def test_compliance_manifest_missing_is_blocked(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)

    gate.check_compliance_manifest(str(root), "第1集", "image")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "compliance_manifest.json" in f["msg"] for f in gate.findings)


def test_compliance_manifest_requires_character_record_for_registry(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root, status_overrides={"character_likeness.characters": []})

    gate.check_compliance_manifest(str(root), "第1集", "image")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "CHAR_SHEN" in f["msg"] for f in gate.findings)


def test_compliance_manifest_requires_rights_fields(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root, status_overrides={
        "rights.adaptation": {},
        "rights.music_bgm": "missing",
    })

    gate.check_compliance_manifest(str(root), "第1集", "image")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "rights.adaptation" in f["loc"] for f in gate.findings)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "rights.music_bgm" in f["loc"] for f in gate.findings)


def test_compliance_manifest_blocks_placeholder_evidence_and_platform(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root, status_overrides={
        "rights.source_text.status": "user_declared",
        "rights.source_text.evidence": "TODO: 原创/公版/授权证明",
        "rights.adaptation.status": "user_declared",
        "rights.adaptation.evidence": "待补",
        "platform_review.targets.0.platform": "TODO",
        "platform_review.targets.0.policy_profile": "TODO_profile_2026-06-08",
    })

    gate.check_compliance_manifest(str(root), "第1集", "compose")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "rights.source_text" in f["loc"] for f in gate.findings)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "rights.adaptation" in f["loc"] for f in gate.findings)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "平台审核缺字段：platform" in f["msg"] for f in gate.findings)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "平台审核缺字段：policy_profile" in f["msg"] for f in gate.findings)


def test_compliance_manifest_blocks_invalid_platform_review_fields(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root, status_overrides={
        "platform_review.targets.0.platform": "not_applicable",
        "platform_review.targets.0.region": "ready",
        "platform_review.targets.0.policy_profile": "douyin_ai_disclosure",
        "platform_review.targets.0.profile_checked_at": "ready",
        "platform_review.targets.0.copyright_review": "douyin",
    })

    gate.check_compliance_manifest(str(root), "第1集", "compose")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "platform 必须是具体平台" in f["msg"] for f in gate.findings)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "region 必须是具体平台/地区" in f["msg"] for f in gate.findings)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "policy_profile 必须带 YYYY-MM-DD" in f["msg"] for f in gate.findings)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "profile_checked_at 必须是 YYYY-MM-DD" in f["msg"] for f in gate.findings)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "copyright_review 必须 ready/done/not_applicable" in f["msg"] for f in gate.findings)


def test_compliance_manifest_blocks_unauthorized_voice_clone(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root, status_overrides={
        "voice.status": "authorized_clone",
        "voice.uses_voice_clone": True,
        "voice.authorization_status": "pending",
        "voice.evidence": "",
    })

    gate.check_compliance_manifest(str(root), "第1集", "video")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "authorization_status" in f["msg"] for f in gate.findings)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "授权缺 evidence" in f["msg"] for f in gate.findings)


def test_compliance_manifest_requires_overseas_localization(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root, status_overrides={
        "platform_review.targets.0.platform": "YouTube",
        "platform_review.targets.0.region": "US",
        "platform_review.targets.0.language": "en",
        "platform_review.targets.0.requires_localization": True,
        "localization.status": "draft",
        "localization.subtitle_languages": ["zh"],
    })

    gate.check_compliance_manifest(str(root), "第1集", "compose")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "出海本地化" in f["msg"] for f in gate.findings)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "目标语言 en" in f["msg"] for f in gate.findings)


def test_compliance_manifest_review_requires_done_watermark_asset(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root)

    gate.check_compliance_manifest(str(root), "第1集", "review")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "必须 done" in f["msg"] for f in gate.findings)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "合规前置" and "最终水印资产" in f["msg"] for f in gate.findings)


def test_identity_registry_missing_is_blocked(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    gate.check_identity_registry(str(root), require_reference_assets=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "identity_registry.json" in f["msg"] for f in gate.findings)


def test_identity_registry_missing_reference_field_is_blocked(tmp_path):
    data = _identity_registry()
    del data["characters"][0]["forms"][0]["reference_group"]["side"]
    root = _write_identity_registry(tmp_path, data)
    gate.check_identity_registry(root, require_reference_assets=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "reference_group 缺核心路径：side" in f["msg"] for f in gate.findings)


def test_identity_registry_rejects_cross_character_expression_reference(tmp_path):
    data = _identity_registry()
    data["characters"][0]["forms"][0]["reference_group"]["expressions"] = [
        "出图/共享/图片/定妆_柳娘子_人皮态_脸部特写.png"
    ]
    root = _write_identity_registry(tmp_path, data)
    gate.check_identity_registry(root, require_reference_assets=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "跨角色/形态污染" in f["msg"] for f in gate.findings)


def test_identity_registry_ready_adapter_requires_handle(tmp_path):
    data = _identity_registry()
    data["characters"][0]["forms"][0]["identity_adapters"]["video"]["kling"] = {
        "mode": "character_id",
        "status": "registered",
        "id": "",
    }
    root = _write_identity_registry(tmp_path, data)
    gate.check_identity_registry(root, require_reference_assets=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "registered/ready" in f["msg"] for f in gate.findings)


def test_identity_registry_ready_lora_requires_model_path_and_trigger(tmp_path):
    data = _identity_registry()
    data["characters"][0]["forms"][0]["identity_adapters"]["lora"] = {
        "status": "ready",
        "base_model": "flux",
        "model_path": "",
        "trigger": "",
    }
    root = _write_identity_registry(tmp_path, data)
    gate.check_identity_registry(root, require_reference_assets=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "LoRA ready" in f["msg"] for f in gate.findings)


def test_identity_registry_lora_warning_override_requires_notes(tmp_path):
    data = _identity_registry()
    data["characters"][0]["forms"][0]["identity_adapters"]["lora"] = {
        "status": "ready",
        "base_model": "flux",
        "model_path": "models/shen.safetensors",
        "trigger": "shen_char",
        "model_hash": "fakehash",
        "validation_report": "models/shen_validation_report.json",
    }
    root = Path(_write_identity_registry(tmp_path, data))
    model = root / "models" / "shen.safetensors"
    model.parent.mkdir(parents=True, exist_ok=True)
    model.write_bytes(b"fake-lora-model")
    (root / "models" / "shen_validation_report.json").write_text(
        json.dumps(
            {
                "kind": "n2d_lora_validation_report",
                "verdict": "pass",
                "model_sha256": "fakehash",
                "warnings": ["dataset_has_warnings"],
                "manual_review": {"approved": True, "allow_dataset_warnings": True, "notes": ""},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    gate.check_identity_registry(str(root), require_reference_assets=False)

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "manual_review.notes" in f["msg"] for f in gate.findings)


def test_identity_registry_rejects_invalid_adapter_status(tmp_path):
    data = _identity_registry()
    data["characters"][0]["forms"][0]["identity_adapters"]["video"]["kling"] = {
        "mode": "character_id",
        "status": "done",
        "id": "abc",
    }
    root = _write_identity_registry(tmp_path, data)
    gate.check_identity_registry(root, require_reference_assets=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "未知 status" in f["msg"] for f in gate.findings)


def test_identity_registry_rejects_backend_mode_mismatch(tmp_path):
    data = _identity_registry()
    data["characters"][0]["forms"][0]["identity_adapters"]["video"]["seedance"] = {
        "mode": "character_id",
        "status": "registered",
        "id": "wrong",
    }
    root = _write_identity_registry(tmp_path, data)
    gate.check_identity_registry(root, require_reference_assets=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "mode" in f["msg"] and "seedance" in f["loc"] for f in gate.findings)


def test_identity_registry_reference_assets_required_for_video(tmp_path):
    root = _write_identity_registry(tmp_path)
    gate.check_identity_registry(root, require_reference_assets=True)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "路径不存在" in f["msg"] for f in gate.findings)


def test_identity_registry_full_contract_passes(tmp_path):
    root = _write_identity_registry(tmp_path, make_assets=True)
    gate.check_identity_registry(root, require_reference_assets=True)
    assert not any(f["dim"] == "资产身份注册层" for f in gate.findings)


def test_asset_reference_registry_missing_is_blocked(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    gate.check_asset_reference_registry(str(root), require_reference_assets=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产引用注册层" and "asset_registry.json" in f["msg"] for f in gate.findings)


def test_asset_reference_registry_rejects_prefix_type_mismatch(tmp_path):
    data = _asset_registry()
    data["assets"][0]["id"] = "PROP_99"
    root = _write_asset_registry(tmp_path, data)
    gate.check_asset_reference_registry(root, require_reference_assets=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产引用注册层" and "LOC_" in f["msg"] for f in gate.findings)


def test_asset_reference_registry_requires_prop_structure(tmp_path):
    data = _asset_registry()
    del data["assets"][1]["constraints"]["structure"]
    data["assets"][1]["constraints"]["color"] = "铜绿"
    root = _write_asset_registry(tmp_path, data)
    gate.check_asset_reference_registry(root, require_reference_assets=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产引用注册层" and "structure" in f["msg"] for f in gate.findings)


def test_asset_reference_registry_allows_scene_layout_to_mention_props(tmp_path):
    data = _asset_registry()
    data["assets"][0]["constraints"]["layout"] = "床榻到门口横轴；沈念、床榻、铜镜在画左，门口在画右。"
    root = _write_asset_registry(tmp_path, data)
    gate.check_asset_reference_registry(root, require_reference_assets=False)
    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "资产引用注册层" and "关键道具 constraints" in f["msg"] for f in gate.findings)


def test_asset_reference_registry_reference_assets_required_for_video(tmp_path):
    root = _write_asset_registry(tmp_path)
    gate.check_asset_reference_registry(root, require_reference_assets=True)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产引用注册层" and "路径不存在" in f["msg"] for f in gate.findings)


def test_asset_reference_registry_full_contract_passes(tmp_path):
    root = _write_asset_registry(tmp_path, make_assets=True)
    gate.check_asset_reference_registry(root, require_reference_assets=True)
    assert not any(f["dim"] == "资产引用注册层" for f in gate.findings)


def test_identity_adapter_matrix_missing_is_blocked(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    gate.check_identity_adapter_matrix(str(root))
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份闭环" and "identity_adapter_matrix.json" in f["msg"] for f in gate.findings)


def test_identity_adapter_matrix_minimal_contract_passes(tmp_path):
    import json
    root = tmp_path / "制漫剧" / "测试剧"
    data_dir = root / "生产数据"
    data_dir.mkdir(parents=True)
    (data_dir / "identity_adapter_matrix.json").write_text(
        json.dumps({
            "kind": "n2d_identity_adapter_matrix",
            "version": 1,
            "forms": [{
                "character_id": "CHAR_SHEN",
                "form": "常态",
                "reference_group": {"front": "出图/共享/characters/CHAR_SHEN/front.png"},
                "image_bindings": {"codex": {"mode": "reference_group", "status": "fallback_reference_group"}},
                "video_bindings": {"dreamina": {"mode": "reference_group", "status": "fallback_reference_group"}},
                "lora_binding": {"status": "not_needed"},
            }],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    gate.check_identity_adapter_matrix(str(root))
    assert not any(f["dim"] == "资产身份闭环" for f in gate.findings)


def test_storyboard_missing_visual_contract_is_blocked(tmp_path):
    root = _write_storyboard(tmp_path, None)
    gate.check_storyboard_visual_contract(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "视觉契约" and "visual_contract 种子块" in f["msg"] for f in gate.findings)


def test_storyboard_visual_contract_missing_field_is_blocked(tmp_path):
    # 有 visual_contract 但缺「景别阶梯」
    root = _write_storyboard(tmp_path, {"色调基线": "冷青", "场景光位锚": {}, "场景轴线视线": {}, "角色状态演进": {}})
    gate.check_storyboard_visual_contract(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "视觉契约" and "景别阶梯" in f["msg"] for f in gate.findings)


def test_storyboard_full_visual_contract_passes(tmp_path):
    root = _write_storyboard(tmp_path, {"色调基线": "x", "场景光位锚": {}, "场景轴线视线": {}, "角色状态演进": {}, "景别阶梯": "y"})
    gate.check_storyboard_visual_contract(root, "第1集")
    assert not any(f["dim"] == "视觉契约" for f in gate.findings)


def test_storyboard_missing_style_contract_is_blocked(tmp_path):
    root = _write_storyboard_with_contracts(
        tmp_path,
        {"色调基线": "x", "场景光位锚": {}, "场景轴线视线": {}, "角色状态演进": {}, "景别阶梯": "y"},
        None,
    )
    gate.check_storyboard_style_contract(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "基础视觉风格契约" and "style_contract" in f["msg"] for f in gate.findings)


def test_storyboard_style_contract_missing_field_is_blocked(tmp_path):
    root = _write_storyboard_with_contracts(
        tmp_path,
        None,
        {"风格名": "国漫写实", "视觉基调": "东方幻想", "镜头与构图": "中景到特写", "光色策略": "青金对比", "运动边界": "慢推/固定"},
    )
    gate.check_storyboard_style_contract(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "基础视觉风格契约" and "风格禁忌" in f["msg"] for f in gate.findings)


def test_storyboard_legacy_cinematic_contract_is_accepted(tmp_path):
    root = _write_storyboard_with_contracts(
        tmp_path,
        None,
        {
            "摄影基调": "写实电影剧照",
            "镜头焦段": "35/50/85mm",
            "光源动机": "窗光+烛火",
            "色彩策略": "低饱和",
            "运镜边界": "慢推/固定",
            "真实感禁忌": ["塑料皮肤"],
        },
        legacy=True,
    )
    gate.check_storyboard_style_contract(root, "第1集")
    assert not any(f["dim"] == "基础视觉风格契约" for f in gate.findings)


def test_storyboard_complex_clip_requires_special_template(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [{"id": "EP01_CLIP03", "label": "山洞追逐", "scene": "王敦在山洞里奔逃，追兵紧追不舍"}],
    )
    gate.check_storyboard_special_templates(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "专项镜头模板" and "缺 template/template_contract" in f["msg"] for f in gate.findings)


def test_storyboard_special_template_missing_field_is_blocked(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [{
            "id": "EP01_CLIP05",
            "label": "符阵爆发",
            "template": "magic_burst",
            "template_contract": {
                "template_id": "magic_burst",
                "beats": ["蓄力", "释放", "余波"],
                "blocking": "王敦画面左前，符阵在画面右后地面亮起",
                "camera_rule": "固定中景，不旋转",
                "continuity_must": ["符阵颜色保持淡青", "王敦衣服不变"],
                "negative": ["不要新增火焰", "不要换符纹形状"],
                "charge_frame": "符纹沿地面亮起",
                "release_frame": "淡青光束向上爆开",
            },
        }],
    )
    gate.check_storyboard_special_templates(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "专项镜头模板" and "effect_asset" in f["msg"] for f in gate.findings)


def test_storyboard_special_template_full_contract_passes(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [{
            "id": "EP01_CLIP02",
            "label": "对话反打",
            "template": "dialogue_shot_reverse",
            "template_contract": {
                "template_id": "dialogue_shot_reverse",
                "beats": ["王敦抬眼", "婷婷反打追问", "王敦轻笑"],
                "blocking": "王敦画左靠石壁，婷婷画右洞口，两人隔豆油灯对视",
                "camera_rule": "守洞口到石壁横轴，只用过肩和中近景反打",
                "continuity_must": ["王敦始终画左", "豆油灯在前景中线", "冷青光位不跳"],
                "negative": ["不要跳轴", "不要交换左右站位", "不要新增第三人"],
                "axis": "洞口→石壁横轴",
                "eyeline": "王敦看画右洞口，婷婷看画左石壁",
                "shot_pairing": "A 王敦 CU / B 婷婷 OTS 反打",
            },
        }],
    )
    gate.check_storyboard_special_templates(root, "第1集")
    assert not any(f["dim"] == "专项镜头模板" for f in gate.findings)


def test_storyboard_hug_or_pull_requires_special_template(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [{"id": "EP01_CLIP06", "label": "抓腕拉扯", "scene": "沈念被太监抓腕拉扯，半步踉跄后推开"}],
    )

    gate.check_storyboard_special_templates(root, "第1集")

    assert any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "专项镜头模板"
        and "hug_or_pull" in f["msg"]
        and "缺 template/template_contract" in f["msg"]
        for f in gate.findings
    )


def test_storyboard_multi_character_same_frame_full_contract_passes(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [{
            "id": "EP01_CLIP07",
            "label": "三人同框对峙",
            "template": "multi_character_same_frame",
            "template_contract": {
                "template_id": "multi_character_same_frame",
                "beats": ["沈念站定", "王敦侧身护住", "太监压近"],
                "blocking": "沈念画左前，王敦画中偏右，太监画右后，三人保持三角站位",
                "camera_rule": "固定中景，不越轴，不环绕",
                "continuity_must": ["沈念始终画左", "王敦衣服不变", "太监不挡沈念正脸"],
                "negative": ["不要交换左右站位", "不要三张脸都抢焦点", "不要新增第四人"],
                "character_slots": {"沈念": "画左前景", "王敦": "中景偏右", "太监": "右后侧脸"},
                "face_priority": ["沈念", "王敦"],
                "overlap_rules": ["太监可侧脸虚焦", "王敦不可遮挡沈念眼睛"],
            },
        }],
    )

    gate.check_storyboard_special_templates(root, "第1集")

    assert not any(f["dim"] == "专项镜头模板" for f in gate.findings)


def test_storyboard_ensemble_template_missing_focus_hierarchy_is_blocked(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [{
            "id": "EP01_CLIP08",
            "label": "群臣围堵",
            "template": "ensemble_blocking",
            "template_contract": {
                "template_id": "ensemble_blocking",
                "beats": ["群臣让开", "沈念抬眼", "侍卫压近"],
                "blocking": "沈念居中前景，群臣分列左右后景，侍卫从画右压近",
                "camera_rule": "固定广角中远景，不越轴",
                "continuity_must": ["沈念居中", "群臣只作背景虚焦", "殿内光位不变"],
                "negative": ["不要每个群臣都清脸", "不要人物挤成一团"],
                "screen_positions": {"沈念": "中央前景", "群臣": "左右后景", "侍卫": "画右中景"},
                "crowd_simplification": "群臣用背影、侧影、虚焦处理",
            },
        }],
    )

    gate.check_storyboard_special_templates(root, "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "专项镜头模板" and "focus_hierarchy" in f["msg"] for f in gate.findings)


def test_image_overview_requires_style_contract_when_visual_contract_exists(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出图" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "00_总览.md").write_text(
        "# 总览\n\n## 本集视觉一致性契约\n- 色调基线：冷青\n- 场景光位锚：烛光顶侧光\n"
        "- 场景轴线·视线：沈念居左\n- 角色状态演进表：镜3起左颊伤\n- 景别阶梯：MS→CU\n",
        encoding="utf-8",
    )

    gate.check_image_prompt_overview(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "基础视觉风格契约" and "本集基础视觉风格契约" in f["msg"] for f in gate.findings)


def test_native_av_mode_allows_native_speech_no_block(tmp_path):
    # 制作模式=原生音画：native_speech 是有意路由，不再强制 no_native_speech，仅 WARN 提示 AI 标识。
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 制作模式: 原生音画\n- 视频原生音轨: 保留原片音轨\n", encoding="utf-8")
    overview = "本集原生音画 opt-in 清单：native_speech 有意生成，成片须带 AI 标识水印。"

    gate.check_native_audio_opt_in_overview(str(root), "第1集", overview, "loc")

    assert not any(f["sev"] == gate.BLOCK for f in gate.findings)


def test_voice_first_mode_still_blocks_native_speech_without_disclaimer(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 制作模式: 配音先行\n- 视频原生音轨: 保留原片音轨\n", encoding="utf-8")
    overview = "本集原生音画 opt-in 清单：保留环境声。"  # 缺 no_native_speech 声明

    gate.check_native_audio_opt_in_overview(str(root), "第1集", overview, "loc")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画" for f in gate.findings)


def test_compose_gate_warns_watermark_pending(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    (root / "脚本" / "第1集").mkdir(parents=True)
    (root / "脚本" / "第1集" / "字幕_中文.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\n你好\n", encoding="utf-8")
    (root / "_设置.md").write_text("# _设置\n- 水印: AI标识+品牌\n", encoding="utf-8")
    (root / "出视频" / "第1集" / "视频").mkdir(parents=True)
    (root / "出视频" / "第1集" / "视频" / "Clip01.mp4").write_text("x", encoding="utf-8")
    gate.check_compose_inputs(str(root), "第1集")
    assert any(f["sev"] == gate.WARN and f["dim"] == "水印" and "AI 合规标识" in f["msg"] for f in gate.findings)


def test_compose_gate_blocks_missing_srt_voice_first(tmp_path):
    # 配音先行：缺中文字幕是硬闸
    root = tmp_path / "制漫剧" / "vf"
    (root / "脚本" / "第1集").mkdir(parents=True)
    (root / "出视频" / "第1集" / "视频").mkdir(parents=True)
    (root / "出视频" / "第1集" / "视频" / "Clip01.mp4").write_text("x", encoding="utf-8")
    gate.check_compose_inputs(str(root), "第1集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "字幕" for f in gate.findings)


def test_compose_gate_native_av_missing_srt_is_warn_not_block(tmp_path):
    # 原生音画：finalize 不产 SRT（字幕走成片后 whisperx），缺字幕只 WARN，不能挡成片
    root = tmp_path / "制漫剧" / "av"
    (root / "脚本" / "第1集").mkdir(parents=True)
    (root / "_设置.md").write_text("- 制作模式: 原生音画\n", encoding="utf-8")
    (root / "出视频" / "第1集" / "视频").mkdir(parents=True)
    (root / "出视频" / "第1集" / "视频" / "Clip01.mp4").write_text("x", encoding="utf-8")
    gate.check_compose_inputs(str(root), "第1集")
    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "字幕" for f in gate.findings)
    assert any(f["sev"] == gate.WARN and f["dim"] == "字幕" and "whisperx" in f["msg"] for f in gate.findings)


def test_image_ai_setting_dreamina_official_cli_passes(tmp_path):
    # 阶段2：Dreamina/即梦官方 CLI 是可选生图后端，不再按名称一律阻断。
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: 即梦\n", encoding="utf-8")

    gate.check_image_ai_policy(str(root), "第1集")

    assert not any(f["dim"] == "生图AI一致性" for f in gate.findings)


def test_image_ai_prompt_can_name_dreamina_backend(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出图" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: Dreamina\n", encoding="utf-8")
    (prompt_dir / "00_总览.md").write_text("生图AI: Dreamina\n本集计划用 dreamina 生图。", encoding="utf-8")

    gate.check_image_ai_policy(str(root), "第1集")

    assert not any(f["dim"] == "生图AI一致性" for f in gate.findings)


def test_image_ai_same_video_ai_shorthand_is_blocked(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: 同视频AI\n", encoding="utf-8")

    gate.check_image_ai_policy(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "生图AI一致性" and "含糊" in f["msg"] for f in gate.findings)


def test_image_ai_approved_alternate_backend_passes(tmp_path):
    # 阶段1：官方多参考后端（Seedream）放行，不再因"非 Codex"阻断。
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出图" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: Seedream\n", encoding="utf-8")
    (prompt_dir / "00_总览.md").write_text("生图AI: Seedream\n本集用 Seedream Universal Reference 锁人。", encoding="utf-8")

    gate.check_image_ai_policy(str(root), "第1集")

    assert not any(f["dim"] == "生图AI一致性" for f in gate.findings)


def test_image_ai_unknown_backend_warns_not_blocks(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: 某小众生图器\n", encoding="utf-8")

    gate.check_image_ai_policy(str(root), "第1集")

    matches = [f for f in gate.findings if f["dim"] == "生图AI一致性"]
    assert matches and all(f["sev"] == gate.WARN for f in matches)


def test_image_ai_mixing_two_approved_backends_is_blocked(tmp_path):
    # 设置 Codex，但 prompt 声明 Seedream → 同项目混用，BLOCK。
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出图" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: Codex\n", encoding="utf-8")
    (prompt_dir / "00_总览.md").write_text("生图AI: Seedream\n", encoding="utf-8")

    gate.check_image_ai_policy(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "生图AI一致性" and "混用" in f["msg"] for f in gate.findings)


def test_image_ai_mixing_codex_and_dreamina_is_blocked(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出图" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: Codex\n", encoding="utf-8")
    (prompt_dir / "00_总览.md").write_text("生图AI: Dreamina\n", encoding="utf-8")

    gate.check_image_ai_policy(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "生图AI一致性" and "混用" in f["msg"] for f in gate.findings)


def test_role_makeup_prompt_requires_standard_three_view(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出图" / "common" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "角色定妆.md").write_text(
        """## ① CHAR_01 沈念·常态（⬜）

**目标存档**：`出图/共享/图片/定妆_沈念.png`
**参考图来源**：无需参考图
**角色定妆组**：
- 主参考：`出图/共享/图片/定妆_沈念.png`（正脸中性光）
- 角度参考：`出图/共享/图片/定妆_沈念_侧.png`（侧脸）

### 正向 prompt（中文）
```text
角色设定图。
```

### 正向 prompt（英文）
```text
Character reference sheet.
```

### 负向 prompt
```text
文字/logo。
```

### 检查清单（定妆自查·最易漏③人物/⑥中性光影/一致性）
1. ✅ 锚点：凤眼薄唇

### 自检（生成后逐张过 · 落档闸门）
**自检**：
- [ ] 同一个人
""",
        encoding="utf-8",
    )

    gate.check_common_image_prompts(str(root))

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "角色三视图" and "标准三视图" in f["msg"] for f in gate.findings)


def test_role_makeup_prompt_requires_halfbody_crop_rule(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出图" / "common" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "角色定妆.md").write_text(
        """## ① CHAR_01 沈念·常态（⬜）

**目标存档**：`出图/共享/图片/定妆_沈念.png`
**身份注册**：`出图/共享/identity_registry.json` → `CHAR_01.常态`
**参考图来源**：无需参考图
**角色定妆组**：
- 正面主参考：`出图/共享/图片/定妆_沈念.png`
- 侧面参考：`出图/共享/图片/定妆_沈念_侧.png`
- 背面参考：`出图/共享/图片/定妆_沈念_背.png`
- 服装参考：`出图/共享/图片/定妆_沈念_半身.png`
- 人审拼版：`出图/共享/图片/定妆_沈念_三视图.png`
- 锚点句：凤眼薄唇

### 正向 prompt（中文）
```text
角色设定图。
```

### 正向 prompt（英文）
```text
Character reference sheet.
```

### 负向 prompt
```text
文字/logo。
```

### 检查清单（定妆自查·最易漏③人物/⑥中性光影/一致性）
1. ✅ 锚点：凤眼薄唇

### 自检（生成后逐张过 · 落档闸门）
**自检**：
- [ ] 同一个人
""",
        encoding="utf-8",
    )

    gate.check_common_image_prompts(str(root))

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "服装参考" and "半身服装参考" in f["msg"] for f in gate.findings)


def test_role_makeup_prompt_halfbody_crop_rule_passes(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出图" / "common" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "角色定妆.md").write_text(
        """## ① CHAR_01 沈念·常态（⬜）

**目标存档**：`出图/共享/图片/定妆_沈念.png`
**身份注册**：`出图/共享/identity_registry.json` → `CHAR_01.常态`
**参考图来源**：无需参考图
**角色定妆组**：
- 正面主参考：`出图/共享/图片/定妆_沈念.png`
- 侧面参考：`出图/共享/图片/定妆_沈念_侧.png`
- 背面参考：`出图/共享/图片/定妆_沈念_背.png`
- 服装参考：`出图/共享/图片/定妆_沈念_半身.png`，从已通过自检的正面主参考裁切并放大/重采样回 9:16；人物主体居中、头身中线接近画面中线、左右留白基本均衡；不得用白底/浅灰底/空白补满下半截
- 人审拼版：`出图/共享/图片/定妆_沈念_三视图.png`
- 锚点句：凤眼薄唇

### 正向 prompt（中文）
```text
角色设定图。
```

### 正向 prompt（英文）
```text
Character reference sheet.
```

### 负向 prompt
```text
文字/logo。
```

### 检查清单（定妆自查·最易漏③人物/⑥中性光影/一致性）
1. ✅ 锚点：凤眼薄唇

### 自检（生成后逐张过 · 落档闸门）
**自检**：
- [ ] 半身服装参考来自正面主参考裁切并重采样回 9:16，无白底/浅灰底/空白补下半截
""",
        encoding="utf-8",
    )

    gate.check_common_image_prompts(str(root))

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "服装参考" for f in gate.findings)


def test_good_video_clip_prompt_passes_director_structure():
    gate.check_video_clip_prompt_section("01_clips.md", GOOD_VIDEO_CLIP)
    assert gate.findings == []


def test_video_clip_suspect_camera_move_warns():
    # 镜头运动含旋转飞行 → 运动一致性 WARN（疑越运动边界）
    clip = GOOD_VIDEO_CLIP.replace(
        "镜头运动：略俯 MCU 缓慢推近 0.5x，结尾稳定停住；",
        "镜头运动：360 旋转环绕飞行急速拉近；",
    )
    gate.check_video_clip_prompt_section("01_clips.md", clip)
    assert any(f["sev"] == gate.WARN and f["dim"] == "运动一致性" for f in gate.findings)


def test_good_video_clip_has_no_camera_move_warn():
    gate.check_video_clip_prompt_section("01_clips.md", GOOD_VIDEO_CLIP)
    assert not any(f["dim"] == "运动一致性" for f in gate.findings)


def test_video_clip_missing_identity_lock_is_blocked():
    clip = GOOD_VIDEO_CLIP.replace(
        "**角色身份注册层**：`CHAR_SHEN/常态`；目标后端 dreamina=fallback_reference_group；fallback reference_group=出图/共享/图片/定妆_沈念.png + 侧面/半身参考；高危角度=deep_shadow；禁漂项=face_shape/hairstyle/outfit_palette\n",
        "",
    ).replace(
        "身份锁定约束：读取 identity_registry.json；dreamina 回退首帧+尾帧+reference_group；保持 drift_forbidden=face_shape/hairstyle/outfit_palette；\n",
        "",
    )
    gate.check_video_clip_prompt_section("01_clips.md", clip)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "身份锁定约束" in f["msg"] for f in gate.findings)


def test_video_clip_missing_motion_refinement_is_blocked():
    clip = GOOD_VIDEO_CLIP.replace(
        "**运动精修**：幅度=极小；能量=克制蓄压；身体守卫=肩颈和下巴不大幅扭动，脸部轮廓不拉伸，手部不穿过衣襟。\n",
        "",
    ).replace(
        "运动精修约束：幅度极小，能量克制，脸部轮廓和发髻不拉伸，手部不穿模；\n",
        "",
    )
    gate.check_video_clip_prompt_section("01_clips.md", clip)
    assert any(f["sev"] == gate.BLOCK and "运动精修" in f["msg"] for f in gate.findings)


def test_video_clip_closeup_missing_fine_identity_lock_is_blocked():
    clip = GOOD_VIDEO_CLIP.replace(
        "**近景/反打身份锁定**：本镜是说话近景；优先引用 expressions/脸部特写，缺脸部特写时用正脸 front + 侧面 + 半身 reference_group；锁脸型、五官比例、发型发髻、标志配饰、服装配色；只允许眼神和嘴角小幅变化，脸漂则降级 MCU/侧脸/反应镜。\n",
        "",
    ).replace(
        "近景身份锁定约束：近景优先脸部特写/表情参考；缺 reference_controls 时只做低幅度眼神和嘴角变化，不大幅转头，不重绘五官，配角近景不稳则降级 MCU/OTS/侧脸；\n",
        "",
    )
    gate.check_video_clip_prompt_section("01_clips.md", clip)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "近景" in f["msg"] for f in gate.findings)


def test_video_clip_missing_native_audio_policy_is_blocked():
    clip = GOOD_VIDEO_CLIP.replace(
        "**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=no_native_speech；compose_policy=丢弃；review=生成后确认无原生人声\n",
        "",
    ).replace(
        "原生音画约束：默认禁止原生人声，不生成对白/旁白/哼唱；本镜 compose_policy=丢弃；\n",
        "",
    )
    gate.check_video_clip_prompt_section("01_clips.md", clip)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画" and "原生音画策略" in f["msg"] for f in gate.findings)


def test_video_clip_missing_model_route_is_blocked():
    clip = GOOD_VIDEO_CLIP.replace(
        "**模型路由**：shot_type=dialogue_closeup；primary_backend=dreamina；fallback_backends=seedance,kling；mode=image2video；native_audio_policy=none；identity_requirement=reference_group；risk_flags=mouth_visible；rationale=普通近景先用项目默认后端，失败切身份/运动更强后端；degrade_plan=改侧脸或反应镜，必要时切 seedance/kling 重跑\n",
        "",
    ).replace(
        "模型路由约束：读取 video_model_routes.json；本镜 primary_backend=dreamina，fallback=seedance,kling，mode=image2video，native_audio_policy=none，identity_requirement=reference_group；prompt 只使用 dreamina 支持的 image2video 能力；失败按 degrade_plan 改侧脸或切 fallback 重跑；\n",
        "",
    )
    gate.check_video_clip_prompt_section("01_clips.md", clip)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "模型路由" and "模型路由" in f["msg"] for f in gate.findings)


def test_video_clip_model_route_constraint_alone_does_not_count_as_route_field():
    clip = GOOD_VIDEO_CLIP.replace(
        "**模型路由**：shot_type=dialogue_closeup；primary_backend=dreamina；fallback_backends=seedance,kling；mode=image2video；native_audio_policy=none；identity_requirement=reference_group；risk_flags=mouth_visible；rationale=普通近景先用项目默认后端，失败切身份/运动更强后端；degrade_plan=改侧脸或反应镜，必要时切 seedance/kling 重跑\n",
        "",
    )
    gate.check_video_clip_prompt_section("01_clips.md", clip)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "模型路由" and "缺模型路由字段" in f["msg"] for f in gate.findings)


def test_video_clip_character_layer_cannot_use_identity_requirement_none():
    clip = GOOD_VIDEO_CLIP.replace("identity_requirement=reference_group", "identity_requirement=none")

    gate.check_video_clip_prompt_section("01_clips.md", clip)

    assert any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "模型路由"
        and "identity_requirement=none" in f["msg"]
        for f in gate.findings
    )


def test_video_clip_physical_interaction_requires_motion_control_field():
    clip = GOOD_VIDEO_CLIP.replace(
        "**模型路由**：shot_type=dialogue_closeup；primary_backend=dreamina；fallback_backends=seedance,kling；mode=image2video；native_audio_policy=none；identity_requirement=reference_group；risk_flags=mouth_visible；rationale=普通近景先用项目默认后端，失败切身份/运动更强后端；degrade_plan=改侧脸或反应镜，必要时切 seedance/kling 重跑\n",
        "**模型路由**：shot_type=hug_or_pull；primary_backend=kling；fallback_backends=seedance,dreamina；mode=frames2video；native_audio_policy=none；identity_requirement=character_id_or_reference_group；risk_flags=contact_motion,feature_melting_risk,physical_interaction；rationale=拉扯高危；degrade_plan=拆手部特写/反打/释放帧\n",
    )

    gate.check_video_clip_prompt_section("01_clips.md", clip)

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "Motion Control" and "物理交互控制" in f["msg"] for f in gate.findings)


def test_video_clip_physical_interaction_motion_control_field_passes():
    clip = GOOD_VIDEO_CLIP.replace(
        "**模型路由**：shot_type=dialogue_closeup；primary_backend=dreamina；fallback_backends=seedance,kling；mode=image2video；native_audio_policy=none；identity_requirement=reference_group；risk_flags=mouth_visible；rationale=普通近景先用项目默认后端，失败切身份/运动更强后端；degrade_plan=改侧脸或反应镜，必要时切 seedance/kling 重跑\n",
        "**模型路由**：shot_type=hug_or_pull；primary_backend=kling；fallback_backends=seedance,dreamina；mode=frames2video；native_audio_policy=none；identity_requirement=character_id_or_reference_group；risk_flags=contact_motion,feature_melting_risk,physical_interaction；rationale=拉扯高危；degrade_plan=拆手部特写/反打/释放帧\n"
        "**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_01/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,instance_masks,contact_map；failure_modes=FeatureMelting,hand_fusion；gate_policy=block_without_ready_manifest_or_degrade_only_manifest\n",
    ).replace(
        "身份锁定约束：读取 identity_registry.json；dreamina 回退首帧+尾帧+reference_group；保持 drift_forbidden=face_shape/hairstyle/outfit_palette；\n",
        "物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/instance/contact 控制资产；degrade_only 时拆手部特写/反打/释放帧；禁止只靠文本 prompt 猜遮挡和手部归属；\n"
        "身份锁定约束：读取 identity_registry.json；dreamina 回退首帧+尾帧+reference_group；保持 drift_forbidden=face_shape/hairstyle/outfit_palette；\n",
    ).replace(
        "- [ ] 人物运动自然\n",
        "- [ ] 人物运动自然\n- [ ] Motion Control / FeatureMelting：检查手部归属、肢体边界、遮挡顺序，无特征融化\n",
    )

    gate.check_video_clip_prompt_section("01_clips.md", clip)

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "Motion Control" for f in gate.findings)


def test_video_clip_native_audio_opt_in_requires_low_risk_no_speech():
    clip = GOOD_VIDEO_CLIP.replace(
        "**原生音画策略**：audio_intent=none；risk=low；mouth_visible=no；speech_policy=no_native_speech；compose_policy=丢弃；review=生成后确认无原生人声",
        "**原生音画策略**：audio_intent=ambience；risk=medium；mouth_visible=yes；speech_policy=allow_native_speech；compose_policy=低音量混入环境声；review=未确认",
    ).replace(
        "原生音画约束：默认禁止原生人声，不生成对白/旁白/哼唱；本镜 compose_policy=丢弃；",
        "原生音画约束：允许平台生成现场声音；",
    )
    gate.check_video_clip_prompt_section("01_clips.md", clip)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画" and "低风险" in f["msg"] for f in gate.findings)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画" and "无口型" in f["msg"] for f in gate.findings)


def test_video_clip_missing_director_intent_is_blocked():
    clip = GOOD_VIDEO_CLIP.replace("**导演意图**：这条镜头不是展示人物漂亮，而是让观众感到沈念正在压住恐惧，镜头慢慢逼近她的眼神。\n", "")
    gate.check_video_clip_prompt_section("01_clips.md", clip)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "导演调度" and "导演意图" in f["msg"] for f in gate.findings)


def test_video_overview_requires_episode_director_contract(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "00_总览.md").write_text("# 总览\n\n## 本集统计\n", encoding="utf-8")

    gate.check_video_prompt_overview(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "导演一致性" and "本集导演一致性契约" in f["msg"] for f in gate.findings)


def test_video_overview_requires_style_contract_when_director_contract_exists(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "00_总览.md").write_text(
        "# 总览\n\n## 本集导演一致性契约\n"
        "- 主色调：冷青\n- 镜头语法：慢推和固定\n- 轴线：床到门横轴\n- 剧情状态锁：觉醒前不发光\n- 场景状态：烛火不跳位\n",
        encoding="utf-8",
    )

    gate.check_video_prompt_overview(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "基础视觉风格契约" and "本集基础视觉风格契约" in f["msg"] for f in gate.findings)


def test_video_overview_native_audio_mix_requires_opt_in_list(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 视频原生音轨: 低音量混入环境声\n", encoding="utf-8")
    (prompt_dir / "00_总览.md").write_text(
        "# 总览\n\n## 本集导演一致性契约\n"
        "- 主色调：冷青\n- 镜头语法：慢推和固定\n- 轴线：床到门横轴\n- 剧情状态锁：觉醒前不发光\n- 场景状态：烛火不跳位\n\n"
        "## 本集基础视觉风格契约\n"
        "- 风格名：写实电影感\n- 视觉基调：低饱和\n- 镜头与构图：中景到特写\n- 光色策略：冷青暖烛\n- 运动边界：慢推\n- 风格禁忌：照片皮肤\n",
        encoding="utf-8",
    )

    gate.check_video_prompt_overview(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画" and "opt-in 清单" in f["msg"] for f in gate.findings)


def test_video_overview_requires_model_routes_json(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "00_总览.md").write_text(
        "# 总览\n\n## 本集导演一致性契约\n"
        "- 主色调：冷青\n- 镜头语法：慢推和固定\n- 轴线：床到门横轴\n- 剧情状态锁：觉醒前不发光\n- 场景状态：烛火不跳位\n\n"
        "## 本集基础视觉风格契约\n"
        "- 风格名：写实电影感\n- 视觉基调：低饱和\n- 镜头与构图：中景到特写\n- 光色策略：冷青暖烛\n- 运动边界：慢推\n- 风格禁忌：照片皮肤\n\n"
        "## 本集模型路由表\n",
        encoding="utf-8",
    )

    gate.check_video_prompt_overview(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "模型路由" and "video_model_routes.json" in f["msg"] for f in gate.findings)


def test_video_overview_missing_closeup_identity_risk_table_is_blocked():
    overview = "## 本集资产身份速查\n- CHAR_02 小禾 reference_group ready\n"

    gate.check_video_closeup_identity_overview(overview, "00_总览.md")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "本集近景身份风险表" in f["msg"] for f in gate.findings)


def test_video_overview_closeup_identity_risk_table_passes():
    overview = """
## 本集资产身份速查
- CHAR_02 小禾 reference_group ready

## 本集近景身份风险表
| 角色/形态 | 近景风险 Clip | 可用脸部/表情参考 | 风险 | 执行策略 |
|---|---|---|---|---|
| CHAR_02/惊慌护主 小禾 | Clip06 | 无脸部特写，只有 reference_group | 高风险 | 降级 MCU/OTS/侧脸/手部/物件反应镜 |
"""

    gate.check_video_closeup_identity_overview(overview, "00_总览.md")

    assert gate.findings == []


def _motion_control_route(manifest_path="出视频/第1集/control/Clip_01/motion_control_manifest.json"):
    return {
        "clip_id": "Clip_01",
        "shot_type": "hug_or_pull",
        "template": "hug_or_pull",
        "primary_backend": "kling",
        "fallback_backends": ["seedance", "dreamina"],
        "mode": "frames2video",
        "native_audio_policy": "none",
        "identity_requirement": "character_id_or_reference_group",
        "risk_flags": ["contact_motion", "feature_melting_risk", "physical_interaction"],
        "motion_control": {
            "level": "required",
            "required": True,
            "manifest_required": True,
            "manifest_path": manifest_path,
            "required_inputs": ["pose_sequence", "depth_sequence", "instance_masks", "contact_map"],
            "backend_control_level": "medium",
            "backend_capabilities": ["first_last_frame", "motion_brush"],
            "recommended_control_backends": ["comfyui_ltx", "kling_motion_control"],
            "failure_modes": ["feature_melting", "hand_fusion"],
            "gate_policy": "block_without_ready_manifest_or_degrade_only_manifest",
            "degrade_allowed": True,
            "notes": ["test"],
        },
        "degrade_plan": "拆手部特写、反打、释放帧。",
    }


def _write_routes(root, route):
    prompt_dir = root / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    data = {"kind": "n2d_video_model_routes", "routes": [route]}
    (prompt_dir / "video_model_routes.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _basic_route(**overrides):
    route = {
        "clip_id": "Clip_01",
        "shot_type": "general_motion",
        "primary_backend": "dreamina",
        "fallback_backends": ["seedance", "kling"],
        "mode": "image2video",
        "native_audio_policy": "none",
        "identity_requirement": "reference_group",
        "risk_flags": [],
        "max_clip_seconds": 8,
        "motion_control": {
            "level": "none",
            "required": False,
            "manifest_required": False,
            "manifest_path": "",
            "required_inputs": [],
            "backend_control_level": "weak",
            "failure_modes": [],
            "gate_policy": "not_required",
            "degrade_allowed": True,
        },
        "degrade_plan": "失败两次后重路由。",
    }
    route.update(overrides)
    return route


def test_long_duration_route_blocks_before_paid_video(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _write_routes(root, _basic_route(risk_flags=["long_duration"]))

    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    finding = next(f for f in gate.findings if f["dim"] == "单Clip时长")
    assert finding["sev"] == gate.BLOCK
    assert finding["return_to_stage"] == "script_stage2"
    assert "storyboard.json" in " ".join(finding["affected_artifacts"])


def test_fixed_default_allows_empty_fallback_when_backup_disabled(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (root / "_设置.md").write_text("- 视频备用后端: 无\n", encoding="utf-8")
    data = {
        "kind": "n2d_video_model_routes",
        "routing_mode": "fixed_default",
        "routes": [_basic_route(fallback_backends=[])],
    }
    (prompt_dir / "video_model_routes.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert not any(
        f["sev"] == gate.BLOCK and f["dim"] == "模型路由" and "fallback_backends" in f["msg"]
        for f in gate.findings
    )


def test_fixed_default_empty_fallback_blocks_without_explicit_backup_setting(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    data = {
        "kind": "n2d_video_model_routes",
        "routing_mode": "fixed_default",
        "routes": [_basic_route(fallback_backends=[])],
    }
    (prompt_dir / "video_model_routes.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert any(
        f["sev"] == gate.BLOCK and f["dim"] == "模型路由" and "fallback_backends" in f["msg"]
        for f in gate.findings
    )


def test_motion_control_required_route_blocks_without_manifest(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _write_routes(root, _motion_control_route())

    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "Motion Control" and "motion_control_manifest.json" in f["msg"] for f in gate.findings)


def test_motion_control_degrade_only_manifest_passes_route_gate(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    route = _motion_control_route()
    _write_routes(root, route)
    manifest = root / route["motion_control"]["manifest_path"]
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "kind": "n2d_motion_control_manifest",
                "version": 1,
                "clip_id": "Clip_01",
                "status": "degrade_only",
                "degrade_plan": "拆成手部特写 + 反打 + 释放帧，不直接生成全身拉扯。",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "Motion Control" for f in gate.findings)


def test_motion_control_ready_manifest_requires_existing_control_assets(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    route = _motion_control_route()
    _write_routes(root, route)
    manifest = root / route["motion_control"]["manifest_path"]
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "kind": "n2d_motion_control_manifest",
                "version": 1,
                "clip_id": "Clip_01",
                "status": "ready",
                "control_inputs": {
                    "pose_sequence": {"status": "ready", "path": "出视频/第1集/control/Clip_01/openpose_%03d.png"},
                    "depth_sequence": {"status": "ready", "path": "出视频/第1集/control/Clip_01/depth_%03d.png"},
                    "instance_masks": {"status": "ready", "path": "出视频/第1集/control/Clip_01/seg_%03d.png"},
                    "contact_map": {"status": "ready", "path": "出视频/第1集/control/Clip_01/contact_map.json"},
                },
                "contact_points": [{"a": "CHAR_A.right_hand", "b": "CHAR_B.left_wrist", "frames": "12-36"}],
                "occlusion_order": ["CHAR_A.right_hand over CHAR_B.left_wrist"],
                "body_part_ownership": ["CHAR_A.right_hand", "CHAR_B.left_wrist"],
                "failure_modes": ["feature_melting", "hand_fusion"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "Motion Control" and "本地资产" in f["msg"] for f in gate.findings)


def test_motion_control_ready_manifest_uri_without_verification_is_blocked(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    route = _motion_control_route()
    _write_routes(root, route)
    manifest = root / route["motion_control"]["manifest_path"]
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "kind": "n2d_motion_control_manifest",
                "version": 1,
                "clip_id": "Clip_01",
                "status": "ready",
                "control_inputs": {
                    "pose_sequence": {"status": "ready", "uri": "s3://bucket/pose.zip"},
                    "depth_sequence": {"status": "ready", "uri": "s3://bucket/depth.zip"},
                    "instance_masks": {"status": "ready", "uri": "s3://bucket/masks.zip"},
                    "contact_map": {"status": "ready", "uri": "s3://bucket/contact.json"},
                },
                "contact_points": [{"a": "CHAR_A.right_hand", "b": "CHAR_B.left_wrist", "frames": "12-36"}],
                "occlusion_order": ["CHAR_A.right_hand over CHAR_B.left_wrist"],
                "body_part_ownership": ["CHAR_A.right_hand", "CHAR_B.left_wrist"],
                "failure_modes": ["feature_melting", "hand_fusion"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "Motion Control" and "control_inputs.pose_sequence" in f["msg"] for f in gate.findings)


def test_motion_control_ready_manifest_verified_remote_uri_passes_route_gate(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    route = _motion_control_route()
    _write_routes(root, route)
    manifest = root / route["motion_control"]["manifest_path"]
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "kind": "n2d_motion_control_manifest",
                "version": 1,
                "clip_id": "Clip_01",
                "status": "ready",
                "control_inputs": {
                    key: {
                        "status": "ready",
                        "uri": f"s3://bucket/Clip_01/{key}.zip",
                        "verified_at": "2026-06-08",
                        "sha256": f"sha256-{key}",
                    }
                    for key in ("pose_sequence", "depth_sequence", "instance_masks", "contact_map")
                },
                "contact_points": [{"a": "CHAR_A.right_hand", "b": "CHAR_B.left_wrist", "frames": "12-36"}],
                "occlusion_order": ["CHAR_A.right_hand over CHAR_B.left_wrist"],
                "body_part_ownership": ["CHAR_A.right_hand", "CHAR_B.left_wrist"],
                "failure_modes": ["feature_melting", "hand_fusion"],
                "degrade_plan": "控制失败则拆手部特写和反打。",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "Motion Control" for f in gate.findings)


def test_motion_control_ready_manifest_passes_route_gate(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    route = _motion_control_route()
    _write_routes(root, route)
    manifest = root / route["motion_control"]["manifest_path"]
    manifest.parent.mkdir(parents=True)
    control_dir = root / "出视频" / "第1集" / "control" / "Clip_01"
    control_dir.mkdir(parents=True, exist_ok=True)
    for name in ("openpose_001.png", "depth_001.png", "seg_001.png"):
        (control_dir / name).write_bytes(b"\x89PNG\r\n\x1a\n")
    (control_dir / "contact_map.json").write_text("{}", encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "kind": "n2d_motion_control_manifest",
                "version": 1,
                "clip_id": "Clip_01",
                "status": "ready",
                "control_inputs": {
                    "pose_sequence": {"status": "ready", "path": "出视频/第1集/control/Clip_01/openpose_%03d.png"},
                    "depth_sequence": {"status": "ready", "path": "出视频/第1集/control/Clip_01/depth_%03d.png"},
                    "instance_masks": {"status": "ready", "path": "出视频/第1集/control/Clip_01/seg_%03d.png"},
                    "contact_map": {"status": "ready", "path": "出视频/第1集/control/Clip_01/contact_map.json"},
                },
                "contact_points": [{"a": "CHAR_A.right_hand", "b": "CHAR_B.left_wrist", "frames": "12-36"}],
                "occlusion_order": ["CHAR_A.right_hand over CHAR_B.left_wrist"],
                "body_part_ownership": ["CHAR_A.right_hand", "CHAR_B.left_wrist"],
                "failure_modes": ["feature_melting", "hand_fusion"],
                "degrade_plan": "控制失败则拆手部特写和反打。",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "Motion Control" for f in gate.findings)


def test_video_prompt_clip_native_audio_opt_in_requires_overview_list(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "00_总览.md").write_text(
        "# 总览\n\n## 本集导演一致性契约\n"
        "- 主色调：冷青\n- 镜头语法：慢推和固定\n- 轴线：床到门横轴\n- 剧情状态锁：觉醒前不发光\n- 场景状态：烛火不跳位\n\n"
        "## 本集基础视觉风格契约\n"
        "- 风格名：写实电影感\n- 视觉基调：低饱和\n- 镜头与构图：中景到特写\n- 光色策略：冷青暖烛\n- 运动边界：慢推\n- 风格禁忌：照片皮肤\n",
        encoding="utf-8",
    )
    clip = GOOD_VIDEO_CLIP.replace(
        "audio_intent=none；risk=low；mouth_visible=no；speech_policy=no_native_speech；compose_policy=丢弃；review=生成后确认无原生人声",
        "audio_intent=ambience；risk=low；mouth_visible=no；speech_policy=no_native_speech；compose_policy=低音量混入环境声；review=确认仅雨声",
    ).replace(
        "原生音画约束：默认禁止原生人声，不生成对白/旁白/哼唱；本镜 compose_policy=丢弃；",
        "原生音画约束：允许低风险雨声环境底，禁止原生人声/对白/旁白/哼唱；",
    )
    (prompt_dir / "01_clips.md").write_text(clip, encoding="utf-8")

    gate.check_prompt_checklists(str(root), "第1集", "video")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画" and "opt-in 清单" in f["msg"] for f in gate.findings)


def test_native_audio_keep_with_voice_track_is_blocked(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出视频" / "第1集" / "prompt"
    voice_dir = root / "合成" / "第1集" / "配音"
    prompt_dir.mkdir(parents=True)
    voice_dir.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 视频原生音轨: 保留原片音轨\n", encoding="utf-8")
    (voice_dir / "voice_zh.wav").write_bytes(b"fake wav")
    (prompt_dir / "00_总览.md").write_text(
        "## 原生音画 opt-in 清单\n"
        "| Clip | audio_intent | risk | mouth_visible | speech_policy | compose_policy |\n"
        "|---|---|---|---|---|---|\n"
        "| Clip 1 | ambience | low | no | no_native_speech / 无原生人声 | 保留原片音轨 |\n",
        encoding="utf-8",
    )

    gate.check_native_audio_compose_policy(str(root), "第1集", ["Clip01.mp4"])

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画" and "双人声" in f["msg"] for f in gate.findings)


def test_video_stage_blocks_noaudio_derivative_outputs(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    vid = root / "出视频" / "第1集" / "视频"
    vid.mkdir(parents=True)
    (vid / "Clip_01_冷宫.noaudio.mp4").write_bytes(b"derived")

    gate.check_video_stage_raw_output_policy(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音轨" and "AI 平台原片" in f["msg"] for f in gate.findings)


def test_video_stage_blocks_raw_with_audio_split_dir(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    vid = root / "出视频" / "第1集" / "视频"
    (vid / "_raw_with_audio").mkdir(parents=True)

    gate.check_video_stage_raw_output_policy(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音轨" and "_raw_with_audio" in f["msg"] for f in gate.findings)


def test_native_av_allows_voiceover_only_track(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    voice_dir = root / "合成" / "第1集" / "配音"
    voice_dir.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 制作模式: 原生音画\n", encoding="utf-8")
    (voice_dir / "voice_zh.wav").write_bytes(b"fake wav")
    (voice_dir / "时长清单.json").write_text(
        json.dumps([{"角色": "旁白", "文本": "三日前，冷宫起火。"}], ensure_ascii=False),
        encoding="utf-8",
    )

    gate.check_native_audio_compose_policy(str(root), "第1集", ["Clip01.mp4"])

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画" for f in gate.findings)
    assert any(f["sev"] == gate.WARN and f["dim"] == "原生音画" and "旁白/系统" in f["msg"] for f in gate.findings)


def test_native_av_blocks_character_voice_track(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    voice_dir = root / "合成" / "第1集" / "配音"
    voice_dir.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 制作模式: 原生音画\n", encoding="utf-8")
    (voice_dir / "voice_zh.wav").write_bytes(b"fake wav")
    (voice_dir / "时长清单.json").write_text(
        json.dumps([{"角色": "沈念", "文本": "谁敢动我？"}], ensure_ascii=False),
        encoding="utf-8",
    )

    gate.check_native_audio_compose_policy(str(root), "第1集", ["Clip01.mp4"])

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画" and "无法确认仅为旁白/系统" in f["msg"] for f in gate.findings)


def test_style_contract_name_mismatch_setting_warns(tmp_path):
    import json
    root = tmp_path / "制漫剧" / "测试剧"
    (root / "脚本" / "第1集").mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 基础视觉风格: 二次元赛璐璐\n", encoding="utf-8")
    sc = {"风格名": "写实电影感", "视觉基调": "x", "镜头与构图": "x",
          "光色策略": "x", "运动边界": "x", "风格禁忌": ["x"]}
    (root / "脚本" / "第1集" / "storyboard.json").write_text(
        json.dumps({"episode": 1, "policy": {"tailframe_default": True},
                    "style_contract": sc, "clips": []}, ensure_ascii=False), encoding="utf-8")
    gate.check_storyboard_style_contract(str(root), "第1集")
    assert any(f["sev"] == gate.WARN and f["dim"] == "风格一致性" and "不一致" in f["msg"] for f in gate.findings)


def test_native_av_placeholder_not_blocked(tmp_path):
    # 制作模式=原生音画：说话镜不靠配音，占位/缺配音不应 BLOCK
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 制作模式: 原生音画\n", encoding="utf-8")
    gate.check_placeholder_policy(str(root), "第1集", "video")
    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "配音" for f in gate.findings)


# ── T1: 契约继承 + 配音指纹 接进 gate ─────────────────────────────────────────
_IMG_OVERVIEW = """# 第1集 — 出图总览

## 本集视觉一致性契约
- 色调基线：冷青灰压暗；残烛暖金只照脸。
- 光位锚：冷宫寝殿=画左前 3000K 残烛暖主光；画右后冷月背光。
- 轴线：守床榻到门口横轴；沈念画左看画右，柳娘子画右看画左。
- 状态演进：沈念 Clip01-13 黑瞳常态；Clip14 起左腕疤裂暗金。
- 景别阶梯：LS建制 -> CU铜镜 -> MCU对峙 -> ECU金瞳。
"""

_VID_OVERVIEW = """# 第1集 — 出视频总览

## 本集导演一致性契约
- 主色调：冷青灰压暗。
- 镜头语法：铺垫慢推。
- 轴线：守床榻到门口横轴。
- 剧情状态锁：金瞳不得提前。
- 场景状态：残烛常亮。

## 本集视觉一致性契约
- 色调基线：冷青灰压暗；残烛暖金只照脸。
- 场景光位锚：冷宫寝殿=画左前 3000K 残烛暖主光；画右后冷月背光。
- 场景轴线视线：守床榻到门口横轴；沈念画左看画右，柳娘子画右看画左。
- 角色状态演进：沈念 Clip01-13 黑瞳常态；Clip14 起左腕疤裂暗金。
- 景别阶梯：LS建制 → CU铜镜 → MCU对峙 → ECU金瞳。
"""


def _write_overviews(tmp_path, img, vid):
    for sub, text in (("出图", img), ("出视频", vid)):
        d = tmp_path / sub / "第1集" / "prompt"
        d.mkdir(parents=True, exist_ok=True)
        (d / "00_总览.md").write_text(text, encoding="utf-8")
    return str(tmp_path)


def test_contract_inheritance_identical_passes(tmp_path):
    root = _write_overviews(tmp_path, _IMG_OVERVIEW, _VID_OVERVIEW)
    gate.findings.clear()
    gate.check_contract_inheritance(root, "第1集")
    assert gate.findings == []


def test_contract_inheritance_axis_rewrite_blocks(tmp_path):
    vid = _VID_OVERVIEW.replace(
        "- 场景轴线视线：守床榻到门口横轴；沈念画左看画右，柳娘子画右看画左。",
        "- 场景轴线视线：守床榻到门口横轴；沈念画右看画左，柳娘子画左看画右。")
    root = _write_overviews(tmp_path, _IMG_OVERVIEW, vid)
    gate.findings.clear()
    gate.check_contract_inheritance(root, "第1集")
    blocks = [f for f in gate.findings if f["sev"] == gate.BLOCK and f["dim"] == "契约继承"]
    assert blocks and "场景轴线视线" in blocks[0]["msg"]
    assert blocks[0]["return_to_stage"] == "video_prompt"


def test_contract_inheritance_video_missing_section_blocks(tmp_path):
    vid = _VID_OVERVIEW.split("## 本集视觉一致性契约")[0]  # 只剩导演契约(运动层)，缺像素层整节
    root = _write_overviews(tmp_path, _IMG_OVERVIEW, vid)
    gate.findings.clear()
    gate.check_contract_inheritance(root, "第1集")
    assert all(f["sev"] == gate.BLOCK for f in gate.findings)
    assert len(gate.findings) == len(gate.VISUAL_CONTRACT_FIELDS)


def test_contract_inheritance_missing_overview_skips_no_double_block(tmp_path):
    # 视频总览缺：check_video_prompt_overview 已 BLOCK，这里不重复报
    d = tmp_path / "出图" / "第1集" / "prompt"
    d.mkdir(parents=True, exist_ok=True)
    (d / "00_总览.md").write_text(_IMG_OVERVIEW, encoding="utf-8")
    gate.findings.clear()
    gate.check_contract_inheritance(str(tmp_path), "第1集")
    assert gate.findings == []


def _write_voice(tmp_path, vo_text, recorded_fp):
    (tmp_path / "脚本" / "第1集").mkdir(parents=True, exist_ok=True)
    (tmp_path / "脚本" / "第1集" / "voiceover.txt").write_text(vo_text, encoding="utf-8")
    meta_dir = tmp_path / "合成" / "第1集" / "配音"
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / "时长清单.meta.json").write_text(
        json.dumps({"kind": "n2d.voice_manifest_meta", "voiceover_fingerprint": recorded_fp}),
        encoding="utf-8")
    return str(tmp_path)


def test_voiceover_fingerprint_match_passes(tmp_path):
    vo = "[镜头1·沈念·克制] 你来了。\n[镜头2·柳娘子·冷] 我一直在。\n"
    root = _write_voice(tmp_path, vo, gate.voiceover_fingerprint(str(tmp_path / "脚本" / "第1集" / "voiceover.txt")))
    gate.findings.clear()
    gate.check_voiceover_fingerprint(root, "第1集")
    assert not any(f["sev"] == gate.BLOCK for f in gate.findings)


def test_voiceover_fingerprint_mismatch_blocks(tmp_path):
    vo = "[镜头1·沈念·克制] 你来了。\n[镜头2·柳娘子·冷] 我一直在。\n"
    root = _write_voice(tmp_path, vo, "deadbeef" * 8)  # 配音时记录的旧指纹，与当前不符
    gate.findings.clear()
    gate.check_voiceover_fingerprint(root, "第1集")
    blocks = [f for f in gate.findings if f["sev"] == gate.BLOCK and f["dim"] == "配音"]
    assert blocks and blocks[0]["return_to_stage"] == "voice"
    assert "指纹失配" in blocks[0]["msg"]


# ── T2: 换后端丢锁机检 ────────────────────────────────────────────────────────
def _write_routes_and_matrix(tmp_path, routes, forms):
    rp = tmp_path / "出视频" / "第1集" / "prompt"
    rp.mkdir(parents=True, exist_ok=True)
    (rp / "video_model_routes.json").write_text(
        json.dumps({"kind": gate.VIDEO_MODEL_ROUTES_KIND, "routes": routes}), encoding="utf-8")
    mp = tmp_path / "生产数据"
    mp.mkdir(parents=True, exist_ok=True)
    (mp / "identity_adapter_matrix.json").write_text(
        json.dumps({"kind": "n2d_identity_adapter_matrix", "forms": forms}), encoding="utf-8")
    return str(tmp_path)


def _form(name, scope, bindings):
    # bindings: {backend: (binding, ready)}
    return {"character_name": name, "character_id": "CHAR_X", "scope": scope,
            "video_bindings": {b: {"binding": bd, "ready": rd} for b, (bd, rd) in bindings.items()}}


def test_route_identity_all_fallback_no_finding(tmp_path):
    # 无原生锁（全 reference_group 兜底，如 demo）→ 不报
    forms = [_form("沈念", "核心", {"kling": ("fallback_reference_group", True), "seedance": ("reference_group", True)})]
    routes = [{"primary_backend": "seedance"}, {"primary_backend": "kling"}]
    root = _write_routes_and_matrix(tmp_path, routes, forms)
    gate.findings.clear()
    gate.check_route_identity_readiness(root, "第1集")
    assert not any(f["dim"] == "换后端丢锁" for f in gate.findings)


def test_route_identity_native_lock_lost_core_blocks(tmp_path):
    # 核心角色在 kling 原生 character_id 锁脸，但 clip 路由到 seedance（仅兜底）→ BLOCK
    forms = [_form("沈念", "核心", {"kling": ("character_id", True), "seedance": ("fallback_reference_group", True)})]
    routes = [{"primary_backend": "seedance"}]
    root = _write_routes_and_matrix(tmp_path, routes, forms)
    gate.findings.clear()
    gate.check_route_identity_readiness(root, "第1集")
    blocks = [f for f in gate.findings if f["dim"] == "换后端丢锁" and f["sev"] == gate.BLOCK]
    assert blocks and "seedance" in blocks[0]["msg"] and blocks[0]["return_to_stage"] == "video_prompt"


def test_route_identity_native_lock_downgrade_minor_warns(tmp_path):
    # 次要角色同样情形 → WARN（不拦）
    forms = [_form("小禾", "配角", {"kling": ("character_id", True), "seedance": ("fallback_reference_group", True)})]
    routes = [{"primary_backend": "seedance"}]
    root = _write_routes_and_matrix(tmp_path, routes, forms)
    gate.findings.clear()
    gate.check_route_identity_readiness(root, "第1集")
    fs = [f for f in gate.findings if f["dim"] == "换后端丢锁"]
    assert fs and all(f["sev"] == gate.WARN for f in fs)


def test_route_identity_backend_missing_binding_blocks(tmp_path):
    # 角色原生锁在 kling，但路由用 veo，且 veo 上无任何绑定 entry → 必丢锁 BLOCK
    forms = [_form("沈念", "配角", {"kling": ("character_id", True)})]
    routes = [{"primary_backend": "veo"}]
    root = _write_routes_and_matrix(tmp_path, routes, forms)
    gate.findings.clear()
    gate.check_route_identity_readiness(root, "第1集")
    blocks = [f for f in gate.findings if f["dim"] == "换后端丢锁" and f["sev"] == gate.BLOCK]
    assert blocks and "veo" in blocks[0]["msg"]


def test_route_identity_routed_to_native_backend_passes(tmp_path):
    # 路由到角色原生锁所在后端 → 无 finding
    forms = [_form("沈念", "核心", {"kling": ("character_id", True), "seedance": ("fallback_reference_group", True)})]
    routes = [{"primary_backend": "kling"}]
    root = _write_routes_and_matrix(tmp_path, routes, forms)
    gate.findings.clear()
    gate.check_route_identity_readiness(root, "第1集")
    assert not any(f["dim"] == "换后端丢锁" for f in gate.findings)


# ── T5: 定妆库 ↔ identity_registry 双向对账 ──────────────────────────────────
def _setup_costume(tmp_path, reference_group, disk_basenames):
    img = Path(gate.shared_asset_path(str(tmp_path), "图片"))
    img.mkdir(parents=True, exist_ok=True)
    for bn in disk_basenames:
        (img / bn).write_bytes(b"PNG")
    reg = {"characters": [{"name": "沈念", "forms": [{"form": "常态", "reference_group": reference_group}]}]}
    Path(gate.identity_registry_path(str(tmp_path))).write_text(json.dumps(reg), encoding="utf-8")
    return str(tmp_path)


def _rel(tmp_path, bn):
    return __import__("os").path.relpath(str(Path(gate.shared_asset_path(str(tmp_path), "图片")) / bn), str(tmp_path))


def test_costume_reconcile_all_registered_no_finding(tmp_path):
    bns = ["定妆_沈念_常态.png", "定妆_沈念_常态_侧.png"]
    rg = {"front": _rel(tmp_path, bns[0]), "side": _rel(tmp_path, bns[1])}
    root = _setup_costume(tmp_path, rg, bns)
    gate.findings.clear()
    gate.check_costume_registry_reconcile(root)
    assert not any(f["dim"] == "定妆对账" for f in gate.findings)


def test_costume_reconcile_registry_path_missing_on_disk(tmp_path):
    rg = {"front": _rel(tmp_path, "定妆_沈念_常态.png"), "outfit": _rel(tmp_path, "定妆_沈念_常态_半身.png")}
    root = _setup_costume(tmp_path, rg, ["定妆_沈念_常态.png"])  # 半身缺
    gate.findings.clear()
    gate.check_costume_registry_reconcile(root)
    miss = [f for f in gate.findings if f["dim"] == "定妆对账" and "磁盘缺失" in f["msg"]]
    assert miss and "半身" in miss[0]["msg"]


def test_costume_reconcile_orphan_variant_of_known_char(tmp_path):
    rg = {"front": _rel(tmp_path, "定妆_沈念_常态.png")}
    # 磁盘多了一张同角色 stem 的脏污变体，没进 registry → orphan
    root = _setup_costume(tmp_path, rg, ["定妆_沈念_常态.png", "定妆_沈念_常态_脏污.png"])
    gate.findings.clear()
    gate.check_costume_registry_reconcile(root)
    orphans = [f for f in gate.findings if f["dim"] == "定妆对账" and "未进 identity_registry" in f["msg"]]
    assert orphans and "脏污" in orphans[0]["msg"]


def test_costume_reconcile_scene_costume_not_flagged(tmp_path):
    rg = {"front": _rel(tmp_path, "定妆_沈念_常态.png")}
    # 场景定妆不属任何角色 stem → 不误报为 orphan
    root = _setup_costume(tmp_path, rg, ["定妆_沈念_常态.png", "定妆_冷宫寝殿.png"])
    gate.findings.clear()
    gate.check_costume_registry_reconcile(root)
    assert not any(f["dim"] == "定妆对账" and "冷宫" in f["msg"] for f in gate.findings)


# ── T8: 跨集色调/风格基线 ────────────────────────────────────────────────────
def _write_sb(tmp_path, ep, tone, style_name):
    d = tmp_path / "脚本" / ep
    d.mkdir(parents=True, exist_ok=True)
    (d / "storyboard.json").write_text(json.dumps({
        "visual_contract": {"色调基线": tone},
        "style_contract": {"风格名": style_name},
    }, ensure_ascii=False), encoding="utf-8")


def test_cross_episode_style_consistent_no_finding(tmp_path):
    _write_sb(tmp_path, "第1集", "冷青灰压暗；残烛暖金只照脸。", "写实电影感")
    _write_sb(tmp_path, "第2集", "冷青灰压暗；本集多一道月光。", "写实电影感")  # 基调首句同，细化不同
    gate.findings.clear()
    gate.check_cross_episode_style(str(tmp_path), "第2集")
    assert not any(f["dim"] in ("跨集色调", "跨集风格") for f in gate.findings)


def test_cross_episode_tone_drift_warns(tmp_path):
    _write_sb(tmp_path, "第1集", "冷青灰压暗；残烛暖金。", "写实电影感")
    _write_sb(tmp_path, "第2集", "暖橙明亮高调；全程顺光。", "写实电影感")  # 基调首句变了
    gate.findings.clear()
    gate.check_cross_episode_style(str(tmp_path), "第2集")
    tone = [f for f in gate.findings if f["dim"] == "跨集色调"]
    assert tone and "第1集" in tone[0]["msg"] and tone[0]["return_to_stage"] == "script_stage2"


def test_cross_episode_style_name_drift_warns(tmp_path):
    _write_sb(tmp_path, "第1集", "冷青灰压暗。", "写实电影感")
    _write_sb(tmp_path, "第2集", "冷青灰压暗。", "二次元厚涂")  # 风格名变了
    gate.findings.clear()
    gate.check_cross_episode_style(str(tmp_path), "第2集")
    assert any(f["dim"] == "跨集风格" and "二次元厚涂" in f["msg"] for f in gate.findings)


def test_cross_episode_style_baseline_episode_itself_skips(tmp_path):
    _write_sb(tmp_path, "第1集", "冷青灰压暗。", "写实电影感")
    gate.findings.clear()
    gate.check_cross_episode_style(str(tmp_path), "第1集")  # 自己就是打样集
    assert gate.findings == []


# ── T9: _进度.md 文本 × 产物双签 ─────────────────────────────────────────────
def _progress(tmp_path, **cols):
    header = "| 集 | " + " | ".join(cols) + " |"
    sep = "|" + "---|" * (len(cols) + 1)
    row = "| 第1集 | " + " | ".join(cols.values()) + " |"
    (tmp_path / "_进度.md").write_text("\n".join([header, sep, row]) + "\n", encoding="utf-8")


def test_signoff_voice_done_but_no_manifest_blocks(tmp_path):
    _progress(tmp_path, 配音="✅")
    gate.findings.clear()
    gate.check_progress_artifact_signoff(str(tmp_path), "第1集", ("配音",))
    blocks = [f for f in gate.findings if f["dim"] == "产物签收"]
    assert blocks and blocks[0]["return_to_stage"] == "voice" and "配音" in blocks[0]["msg"]


def test_signoff_voice_done_with_manifest_passes(tmp_path):
    _progress(tmp_path, 配音="✅")
    d = tmp_path / "合成" / "第1集" / "配音"
    d.mkdir(parents=True)
    (d / "时长清单.json").write_text("[]", encoding="utf-8")
    (d / "voice_zh.wav").write_bytes(b"RIFF")  # 满足"真实配音"变体
    gate.findings.clear()
    gate.check_progress_artifact_signoff(str(tmp_path), "第1集", ("配音",))
    assert not any(f["dim"] == "产物签收" for f in gate.findings)


def test_signoff_skips_not_done_columns(tmp_path):
    _progress(tmp_path, 配音="⬜")  # 未完成 → 由 require_progress 管，签收不报
    gate.findings.clear()
    gate.check_progress_artifact_signoff(str(tmp_path), "第1集", ("配音",))
    assert not any(f["dim"] == "产物签收" for f in gate.findings)


def _settings(tmp_path: Path, mode: str) -> None:
    (tmp_path / "_设置.md").write_text(f"- 制作模式: {mode}\n", encoding="utf-8")


def _voice_manifest(tmp_path: Path, *, placeholder: bool) -> None:
    d = tmp_path / "合成" / "第1集" / "配音"
    d.mkdir(parents=True)
    row = {"idx": 0, "文本": "测试", "时长": 1.0}
    if placeholder:
        row["占位"] = True
        (d / "_占位说明.md").write_text("rough timing", encoding="utf-8")
    else:
        (d / "voice_zh.wav").write_bytes(b"RIFF")
    (d / "时长清单.json").write_text(json.dumps([row], ensure_ascii=False), encoding="utf-8")


def test_voice_first_rough_progress_blocks_paid_gate_prereq(tmp_path):
    _settings(tmp_path, "配音先行")
    _progress(tmp_path, 配音="⏳rough")

    gate.findings.clear()
    gate.require_progress(str(tmp_path), "第1集", ("配音",))
    gate.check_placeholder_policy(str(tmp_path), "第1集", "image")

    blocks = [f for f in gate.findings if f["sev"] == gate.BLOCK and f["dim"] in {"进度", "配音"}]
    assert blocks


def test_video_first_rough_progress_satisfies_gate_with_manifest_warning(tmp_path):
    _settings(tmp_path, "先出视频后配音")
    _progress(tmp_path, 配音="⏳rough")
    _voice_manifest(tmp_path, placeholder=True)

    gate.findings.clear()
    gate.require_progress(str(tmp_path), "第1集", ("配音",))
    gate.check_placeholder_policy(str(tmp_path), "第1集", "video")

    assert not any(f["sev"] == gate.BLOCK and f["dim"] in {"进度", "配音"} for f in gate.findings)
    assert any(f["sev"] == gate.WARN and f["dim"] == "配音" and "先出视频后配音" in f["msg"] for f in gate.findings)


def test_video_first_rough_without_manifest_blocks_as_unverifiable(tmp_path):
    _settings(tmp_path, "先出视频后配音")
    _progress(tmp_path, 配音="⏳rough")

    gate.findings.clear()
    gate.require_progress(str(tmp_path), "第1集", ("配音",))
    gate.check_placeholder_policy(str(tmp_path), "第1集", "video")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "配音" and "时长清单" in f["msg"] for f in gate.findings)


def test_signoff_stage_without_contract_needs_some_output(tmp_path):
    _progress(tmp_path, 分镜设计="✅")  # script_stage2 无 output_contract，要求 outputs 至少一个在
    gate.findings.clear()
    gate.check_progress_artifact_signoff(str(tmp_path), "第1集", ("分镜设计",))
    assert any(f["dim"] == "产物签收" and f["return_to_stage"] == "script_stage2" for f in gate.findings)
    # 补一个产物后放行
    sd = tmp_path / "脚本" / "第1集"; sd.mkdir(parents=True)
    (sd / "storyboard.json").write_text("{}", encoding="utf-8")
    gate.findings.clear()
    gate.check_progress_artifact_signoff(str(tmp_path), "第1集", ("分镜设计",))
    assert not any(f["dim"] == "产物签收" for f in gate.findings)


# ── T11: 机位逐镜契约化（②机位 substantive WARN）─────────────────────────────
def test_shot_camera_default_flatview_warns():
    sec = GOOD_SHOT.replace("| ② 机位 | 微俯视 |", "| ② 机位 | 正面平视 |")
    gate.findings.clear()
    gate.check_image_shot_prompt_section("p.md", 1, sec)
    assert any(f["sev"] == gate.WARN and f["dim"] == "构图景别" and "机位即态度" in f["msg"] for f in gate.findings)


def test_shot_camera_substantive_no_warn():
    gate.findings.clear()
    gate.check_image_shot_prompt_section("p.md", 1, GOOD_SHOT)  # ②机位=微俯视
    assert not any(f["dim"] == "构图景别" and "机位即态度" in f["msg"] for f in gate.findings)


# ── 多角色同框绑定歧义（资产身份注册层.md 第7节）单测 ──

def test_multi_char_binding_ambiguity_pure():
    assert gate._multi_char_binding_ambiguity("目标：`CHAR_SHEN/受难` 独角镜") is None       # 单角色不管
    got = gate._multi_char_binding_ambiguity("`CHAR_SHEN/受难` 与 `CHAR_LIU/常服` 对峙")
    assert got == ["CHAR_LIU", "CHAR_SHEN"]                                                  # 同框无星标 → 歧义
    assert gate._multi_char_binding_ambiguity("`CHAR_SHEN/受难*` 与 `CHAR_LIU/常服` 对峙") is None  # 星标后放行
    assert gate._multi_char_binding_ambiguity("`CHAR_SHEN*` 与 `CHAR_LIU` 同框") is None     # 裸 ID 星标也认


def test_shot_section_warns_on_unstarred_multi_char():
    gate.findings.clear()
    section = GOOD_SHOT.replace("CHAR_SHEN/常态", "CHAR_SHEN/常态` 与 `CHAR_LIU/常服", 1)
    assert "CHAR_LIU" in section
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, section)
    assert any(f["sev"] == gate.WARN and "未星标 primary" in str(f["msg"]) for f in gate.findings)
    gate.findings.clear()
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, section.replace("CHAR_SHEN/常态`", "CHAR_SHEN/常态*`", 1))
    assert not any("未星标 primary" in str(f["msg"]) for f in gate.findings)


def test_shot_scale_class_extracts_and_disambiguates():
    assert gate.shot_scale_class("CU 85mm 缓推") == "CU"
    assert gate.shot_scale_class("MCU 50mm") == "MCU"      # MCU 不被 CU 误命中
    assert gate.shot_scale_class("ECU 大特写") == "ECU"     # ECU 不被 CU 误命中
    assert gate.shot_scale_class("大远景 24mm") == "ELS"    # 大远景 不被 远景(LS) 误命中
    assert gate.shot_scale_class("中近景") == "MCU"          # 中近景 不被 中景(MS) 误命中
    assert gate.shot_scale_class("全景航拍") == "LS"
    assert gate.shot_scale_class("无景别词") is None


def test_monotonous_scale_runs_finds_runs_min3():
    assert gate.monotonous_scale_runs(["CU", "CU", "CU"]) == [(0, 2, "CU", 3)]
    assert gate.monotonous_scale_runs(["CU", "MS", "CU"]) == []          # 有变化 → 无单调
    assert gate.monotonous_scale_runs(["CU", "CU", None, "CU", "CU"]) == []  # None 打断、各段 <3
    assert gate.monotonous_scale_runs(["MS", "MS", "MS", "MS"]) == [(0, 3, "MS", 4)]


def _write_scale_sb(root, ep, clips):
    sb_dir = root / "脚本" / ep
    sb_dir.mkdir(parents=True, exist_ok=True)
    (sb_dir / "storyboard.json").write_text(json.dumps({"clips": clips}, ensure_ascii=False),
                                            encoding="utf-8")


def test_check_shot_scale_progression_flags_monotonous(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"
    ep = "第1集"
    _write_scale_sb(root, ep, [
        {"id": "Clip_01", "shots": [{"lens": "CU 85mm"}]},
        {"id": "Clip_02", "shots": [{"lens": "CU 85mm"}]},
        {"id": "Clip_03", "shots": [{"lens": "CU 缓推"}]},
        {"id": "Clip_04", "shots": [{"lens": "LS 35mm"}]},
    ])
    gate.check_shot_scale_progression(str(root), ep)
    monotone = [f for f in gate.findings if f["dim"] == "景别阶梯"]
    assert len(monotone) == 1
    assert monotone[0]["sev"] == gate.WARN and "Clip_01→Clip_03" in monotone[0]["loc"]


def test_check_shot_scale_progression_exempts_reverse_shots(tmp_path):
    # 对白正反打：连续 CU 但带反打标记 → 合法交替变化，不告警
    gate.findings.clear()
    root = tmp_path / "work"
    ep = "第1集"
    _write_scale_sb(root, ep, [
        {"id": "Clip_01", "shots": [{"lens": "CU 正面说话"}]},
        {"id": "Clip_02", "shots": [{"lens": "CU 反打"}]},
        {"id": "Clip_03", "shots": [{"lens": "CU 过肩反打"}]},
    ])
    gate.check_shot_scale_progression(str(root), ep)
    assert [f for f in gate.findings if f["dim"] == "景别阶梯"] == []


def _seed_pngs_and_qc(root, ep, hard_blocks, qc_present=True):
    import os, time
    png_dir = root / "出图" / ep / "图片"
    png_dir.mkdir(parents=True, exist_ok=True)
    png = png_dir / "镜头01.png"
    png.write_bytes(b"x")
    qc_path = root / "生产数据" / "image_qc" / ep / f"image_qc_{ep}.json"
    if qc_present:
        qc_path.parent.mkdir(parents=True, exist_ok=True)
        qc_path.write_text(json.dumps({"summary": {"hard_blocks": hard_blocks, "verdict":
                            "block" if hard_blocks else "ok"}}, ensure_ascii=False), encoding="utf-8")
        # make QC newer than the PNG so the freshness branch passes
        future = time.time() + 100
        os.utime(qc_path, (future, future))
    return png, qc_path


def test_input_frame_qc_blocks_when_image_qc_has_hard(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _seed_pngs_and_qc(root, ep, hard_blocks=2)
    gate.check_input_frame_qc(str(root), ep)
    blocks = [f for f in gate.findings if f["dim"] == "出图落档QC" and f["sev"] == gate.BLOCK]
    assert len(blocks) == 1 and "图生视频会忠实" in blocks[0]["msg"]
    assert blocks[0].get("return_to_stage") == "image"


def test_input_frame_qc_warns_when_no_qc_result(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _seed_pngs_and_qc(root, ep, hard_blocks=0, qc_present=False)
    gate.check_input_frame_qc(str(root), ep)
    warns = [f for f in gate.findings if f["dim"] == "出图落档QC" and f["sev"] == gate.WARN]
    assert len(warns) == 1 and "未见 image_qc" in warns[0]["msg"]


def test_input_frame_qc_passes_when_clean_and_fresh(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _seed_pngs_and_qc(root, ep, hard_blocks=0)
    gate.check_input_frame_qc(str(root), ep)
    assert [f for f in gate.findings if f["dim"] == "出图落档QC"] == []


def test_input_frame_qc_warns_when_qc_stale(tmp_path):
    import os, time
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    png, qc_path = _seed_pngs_and_qc(root, ep, hard_blocks=0)
    # make the PNG newer than the QC result (出图后改过帧未重验)
    future = time.time() + 500
    os.utime(png, (future, future))
    gate.check_input_frame_qc(str(root), ep)
    warns = [f for f in gate.findings if f["dim"] == "出图落档QC" and f["sev"] == gate.WARN]
    assert len(warns) == 1 and "晚于上次 image_qc" in warns[0]["msg"]


def _seed_video_prompt(root, ep, clips_md, storyboard=None):
    pdir = root / "出视频" / ep / "prompt"
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "01_clips.md").write_text(clips_md, encoding="utf-8")
    if storyboard is not None:
        sb_dir = root / "脚本" / ep
        sb_dir.mkdir(parents=True, exist_ok=True)
        (sb_dir / "storyboard.json").write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")


def _mk_png(root, ep, name):
    d = root / "出图" / ep / "图片"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_bytes(b"x")


def _record_image_event(root, ep, asset, *, status="pass", self_check="pass", event="generation"):
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": "n2d_production_event",
        "version": 1,
        "ts": "2026-01-01T00:00:00+00:00",
        "episode": ep,
        "stage": "image",
        "event": event,
        "source": "test",
        "generation": {"asset": asset, "status": status},
    }
    if self_check is not None:
        payload["meta"] = {"self_check": self_check}
    with open(prod / "production_events.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def test_video_prompt_frames_blocks_missing_firstframe(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    # 首帧 PNG NOT created on disk → BLOCK (would fail the paid backend call)
    _seed_video_prompt(root, ep, "## Clip 01\n**首帧**：`出图/第1集/图片/Clip_01.png`\n")
    gate.check_video_prompt_frames(str(root), ep)
    blocks = [f for f in gate.findings if f["dim"] == "首帧" and f["sev"] == gate.BLOCK]
    assert len(blocks) == 1 and "白扣一次" in blocks[0]["msg"]


def test_video_prompt_frames_warns_missing_endframe(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _mk_png(root, ep, "Clip_01.png")  # 首帧 exists
    _seed_video_prompt(root, ep,
                       "## Clip 01\n**首帧**：`出图/第1集/图片/Clip_01.png`\n**尾帧**：`出图/第1集/图片/Clip_01_end.png`\n")
    gate.check_video_prompt_frames(str(root), ep)
    warns = [f for f in gate.findings if f["dim"] == "尾帧" and f["sev"] == gate.WARN]
    assert len(warns) == 1 and "降级为单首帧" in warns[0]["msg"]


def test_video_prompt_frames_warns_dropped_doubleframe_intent(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _mk_png(root, ep, "Clip_01.png")
    # video prompt omits 尾帧, but storyboard marks need_endframe=true → 双帧 intent dropped (WARN)
    _seed_video_prompt(root, ep, "## Clip 01\n**首帧**：`出图/第1集/图片/Clip_01.png`\n",
                       storyboard={"clips": [{"continuity": {"need_endframe": True}}]})
    gate.check_video_prompt_frames(str(root), ep)
    warns = [f for f in gate.findings if f["dim"] == "尾帧" and f["sev"] == gate.WARN]
    assert len(warns) == 1 and "誊抄时丢失" in warns[0]["msg"]


def test_video_prompt_frames_passes_when_all_present(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _mk_png(root, ep, "Clip_01.png"); _mk_png(root, ep, "Clip_01_end.png")
    _seed_video_prompt(root, ep,
                       "## Clip 01\n**首帧**：`出图/第1集/图片/Clip_01.png`\n**尾帧**：`出图/第1集/图片/Clip_01_end.png`\n",
                       storyboard={"clips": [{"continuity": {"need_endframe": True}}]})
    gate.check_video_prompt_frames(str(root), ep)
    assert [f for f in gate.findings if f["dim"] in ("首帧", "尾帧")] == []


# ── 中段锚帧（opt-in midframe split）契约 ──

def _write_midframe_storyboard(tmp_path, midframe, *, duration=10, make_png=False):
    import json
    root = tmp_path / "work"; ep = "第1集"
    sb_dir = root / "脚本" / ep
    sb_dir.mkdir(parents=True, exist_ok=True)
    _mk_png(root, ep, "Clip_01.png")
    cont = {"start_state": "s", "end_state": "e", "transition": "硬切", "need_endframe": False,
            "endframe_exempt_reason": "最终 Clip"}
    if midframe is not None:
        cont["midframe"] = midframe
    if make_png:
        _mk_png(root, ep, "Clip_01_mid.png")
    data = {"episode": 1, "policy": {"tailframe_default": True},
            "clips": [{"id": "EP01_CLIP01", "duration": duration,
                       "firstframe_png": "出图/第1集/图片/Clip_01.png", "continuity": cont}]}
    (sb_dir / "storyboard.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(root)


def _midframe_findings():
    return [f for f in gate.findings if f["dim"] == "中段锚帧"]


def test_midframe_absent_is_fine(tmp_path):
    root = _write_midframe_storyboard(tmp_path, None)
    gate.check_storyboard_contract(root, "第1集")
    assert _midframe_findings() == []


def test_midframe_must_be_object(tmp_path):
    root = _write_midframe_storyboard(tmp_path, "出图/第1集/图片/Clip_01_mid.png")
    gate.check_storyboard_contract(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and "必须是 object" in f["msg"] for f in _midframe_findings())


def test_midframe_missing_fields_blocked(tmp_path):
    root = _write_midframe_storyboard(tmp_path, {"midframe_png": "出图/第1集/图片/Clip_01_mid.png"},
                                      make_png=True)
    gate.check_storyboard_contract(root, "第1集")
    msgs = [f["msg"] for f in _midframe_findings() if f["sev"] == gate.BLOCK]
    assert any("split_at_sec" in m for m in msgs)
    assert any("reason" in m for m in msgs)


def test_midframe_split_outside_duration_blocked(tmp_path):
    root = _write_midframe_storyboard(
        tmp_path,
        {"midframe_png": "出图/第1集/图片/Clip_01_mid.png", "split_at_sec": 12,
         "reason": "三拍动作中段漂移"},
        duration=10, make_png=True)
    gate.check_storyboard_contract(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and "split_at_sec=12" in f["msg"] for f in _midframe_findings())


def test_midframe_missing_png_blocked(tmp_path):
    root = _write_midframe_storyboard(
        tmp_path,
        {"midframe_png": "出图/第1集/图片/Clip_01_mid.png", "split_at_sec": 5,
         "reason": "三拍动作中段漂移"},
        make_png=False)
    gate.check_storyboard_contract(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and "锚帧 PNG 不存在" in f["msg"] for f in _midframe_findings())


def test_midframe_full_contract_passes(tmp_path):
    root = _write_midframe_storyboard(
        tmp_path,
        {"midframe_png": "出图/第1集/图片/Clip_01_mid.png", "split_at_sec": 5,
         "reason": "9s 三拍动作，redraw×2 中段漂移"},
        make_png=True)
    _record_image_event(Path(root), "第1集", "出图/第1集/图片/Clip_01_mid.png")
    gate.check_storyboard_contract(root, "第1集")
    assert _midframe_findings() == []


def test_midframe_png_requires_generation_self_check(tmp_path):
    root = _write_midframe_storyboard(
        tmp_path,
        {"midframe_png": "出图/第1集/图片/Clip_01_mid.png", "split_at_sec": 5,
         "reason": "9s 三拍动作，redraw×2 中段漂移"},
        make_png=True)
    gate.check_storyboard_contract(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and "缺中段动作自检 pass 记账" in f["msg"] for f in _midframe_findings())


def test_midframe_latest_failed_self_check_blocks(tmp_path):
    root = _write_midframe_storyboard(
        tmp_path,
        {"midframe_png": "出图/第1集/图片/Clip_01_mid.png", "split_at_sec": 5,
         "reason": "9s 三拍动作，redraw×2 中段漂移"},
        make_png=True)
    _record_image_event(Path(root), "第1集", "出图/第1集/图片/Clip_01_mid.png")
    _record_image_event(Path(root), "第1集", "出图/第1集/图片/Clip_01_mid.png",
                        status="fail", self_check="fail", event="redraw")
    gate.check_storyboard_contract(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and "最近一次生成记录不是 pass" in f["msg"] for f in _midframe_findings())


def test_midframe_pass_without_self_check_blocks(tmp_path):
    root = _write_midframe_storyboard(
        tmp_path,
        {"midframe_png": "出图/第1集/图片/Clip_01_mid.png", "split_at_sec": 5,
         "reason": "9s 三拍动作，redraw×2 中段漂移"},
        make_png=True)
    _record_image_event(Path(root), "第1集", "出图/第1集/图片/Clip_01_mid.png", self_check=None)
    gate.check_storyboard_contract(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and "缺少通过值 self_check=pass" in f["msg"] for f in _midframe_findings())


def test_video_prompt_frames_warns_missing_midframe_png(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _mk_png(root, ep, "Clip_01.png")
    _seed_video_prompt(root, ep,
                       "## Clip 01\n**首帧**：`出图/第1集/图片/Clip_01.png`\n"
                       "**中段锚帧**：`出图/第1集/图片/Clip_01_mid.png`\n")
    gate.check_video_prompt_frames(str(root), ep)
    warns = [f for f in gate.findings if f["dim"] == "中段锚帧" and f["sev"] == gate.WARN]
    assert len(warns) == 1 and "PNG 不存在" in warns[0]["msg"]


def test_video_prompt_frames_warns_dropped_midframe_intent(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _mk_png(root, ep, "Clip_01.png")
    # storyboard declares continuity.midframe, but prompt block lacks **中段锚帧** → split intent dropped
    _seed_video_prompt(root, ep, "## Clip 01\n**首帧**：`出图/第1集/图片/Clip_01.png`\n",
                       storyboard={"clips": [{"continuity": {
                           "need_endframe": False,
                           "midframe": {"midframe_png": "出图/第1集/图片/Clip_01_mid.png",
                                        "split_at_sec": 5, "reason": "中段漂移"}}}]})
    gate.check_video_prompt_frames(str(root), ep)
    warns = [f for f in gate.findings if f["dim"] == "中段锚帧" and f["sev"] == gate.WARN]
    assert len(warns) == 1 and "誊抄时丢失" in warns[0]["msg"]


def test_video_prompt_frames_midframe_present_passes(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _mk_png(root, ep, "Clip_01.png"); _mk_png(root, ep, "Clip_01_mid.png")
    _seed_video_prompt(root, ep,
                       "## Clip 01\n**首帧**：`出图/第1集/图片/Clip_01.png`\n"
                       "**中段锚帧**：`出图/第1集/图片/Clip_01_mid.png`\n",
                       storyboard={"clips": [{"continuity": {
                           "need_endframe": False,
                           "midframe": {"midframe_png": "出图/第1集/图片/Clip_01_mid.png",
                                        "split_at_sec": 5, "reason": "中段漂移"}}}]})
    gate.check_video_prompt_frames(str(root), ep)
    assert [f for f in gate.findings if f["dim"] == "中段锚帧"] == []


# ── anchors（N 锚帧链·anchor_planner 写）契约 ──

def _anchors(*at_secs, png_prefix="出图/第1集/图片/Clip_01_a"):
    return [{"anchor_png": f"{png_prefix}{k}.png", "at_sec": at, "reason": "auto: R2 普通长镜"}
            for k, at in enumerate(at_secs, 1)]


def test_anchors_full_chain_passes(tmp_path):
    root = _write_midframe_storyboard(tmp_path, None, duration=15)
    import json
    sb_path = tmp_path / "work" / "脚本" / "第1集" / "storyboard.json"
    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    sb["clips"][0]["continuity"]["anchors"] = _anchors(5, 10)
    sb_path.write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    _mk_png(tmp_path / "work", "第1集", "Clip_01_a1.png")
    _mk_png(tmp_path / "work", "第1集", "Clip_01_a2.png")
    _record_image_event(tmp_path / "work", "第1集", "出图/第1集/图片/Clip_01_a1.png")
    _record_image_event(tmp_path / "work", "第1集", "出图/第1集/图片/Clip_01_a2.png")
    gate.check_storyboard_contract(str(tmp_path / "work"), "第1集")
    assert _midframe_findings() == []


def test_anchors_and_midframe_together_blocked(tmp_path):
    root = _write_midframe_storyboard(
        tmp_path,
        {"midframe_png": "出图/第1集/图片/Clip_01_mid.png", "split_at_sec": 5, "reason": "x"},
        make_png=True)
    import json
    sb_path = tmp_path / "work" / "脚本" / "第1集" / "storyboard.json"
    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    sb["clips"][0]["continuity"]["anchors"] = _anchors(5)
    sb_path.write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    gate.check_storyboard_contract(str(tmp_path / "work"), "第1集")
    assert any(f["sev"] == gate.BLOCK and "不能同时声明" in f["msg"] for f in _midframe_findings())


def test_anchors_not_increasing_blocked(tmp_path):
    root = _write_midframe_storyboard(tmp_path, None, duration=15)
    import json
    sb_path = tmp_path / "work" / "脚本" / "第1集" / "storyboard.json"
    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    sb["clips"][0]["continuity"]["anchors"] = _anchors(10, 5)
    sb_path.write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    _mk_png(tmp_path / "work", "第1集", "Clip_01_a1.png")
    _mk_png(tmp_path / "work", "第1集", "Clip_01_a2.png")
    gate.check_storyboard_contract(str(tmp_path / "work"), "第1集")
    assert any(f["sev"] == gate.BLOCK and "严格递增" in f["msg"] for f in _midframe_findings())


def test_anchors_missing_png_blocked(tmp_path):
    root = _write_midframe_storyboard(tmp_path, None, duration=15)
    import json
    sb_path = tmp_path / "work" / "脚本" / "第1集" / "storyboard.json"
    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    sb["clips"][0]["continuity"]["anchors"] = _anchors(5, 10)
    sb_path.write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    _mk_png(tmp_path / "work", "第1集", "Clip_01_a1.png")  # a2 缺
    gate.check_storyboard_contract(str(tmp_path / "work"), "第1集")
    assert any(f["sev"] == gate.BLOCK and "锚帧 2 但锚帧 PNG 不存在" in f["msg"] for f in _midframe_findings())


def test_video_prompt_frames_warns_partial_anchor_transcription(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _mk_png(root, ep, "Clip_01.png"); _mk_png(root, ep, "Clip_01_a1.png"); _mk_png(root, ep, "Clip_01_a2.png")
    # storyboard 声明 2 锚帧，prompt 只誊抄了 1 个 → WARN
    _seed_video_prompt(root, ep,
                       "## Clip 01\n**首帧**：`出图/第1集/图片/Clip_01.png`\n"
                       "**锚帧1**：`出图/第1集/图片/Clip_01_a1.png`\n",
                       storyboard={"clips": [{"continuity": {
                           "need_endframe": False, "anchors": _anchors(5, 10)}}]})
    gate.check_video_prompt_frames(str(root), ep)
    warns = [f for f in gate.findings if f["dim"] == "中段锚帧" and f["sev"] == gate.WARN]
    assert len(warns) == 1 and "只引用了 1 个" in warns[0]["msg"]


def test_video_prompt_frames_full_anchor_chain_passes(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _mk_png(root, ep, "Clip_01.png"); _mk_png(root, ep, "Clip_01_a1.png"); _mk_png(root, ep, "Clip_01_a2.png")
    _seed_video_prompt(root, ep,
                       "## Clip 01\n**首帧**：`出图/第1集/图片/Clip_01.png`\n"
                       "**锚帧1**：`出图/第1集/图片/Clip_01_a1.png`\n"
                       "**锚帧2**：`出图/第1集/图片/Clip_01_a2.png`\n",
                       storyboard={"clips": [{"continuity": {
                           "need_endframe": False, "anchors": _anchors(5, 10)}}]})
    gate.check_video_prompt_frames(str(root), ep)
    assert [f for f in gate.findings if f["dim"] == "中段锚帧"] == []


def _write_midframe_policy_storyboard(tmp_path, cont_extra):
    import json
    root = tmp_path / "work"; ep = "第1集"
    sb_dir = root / "脚本" / ep
    sb_dir.mkdir(parents=True, exist_ok=True)
    _mk_png(root, ep, "Clip_01.png")
    cont = {"start_state": "s", "end_state": "e", "transition": "硬切", "need_endframe": False,
            "endframe_exempt_reason": "最终 Clip"}
    cont.update(cont_extra)
    data = {"episode": 1, "policy": {"tailframe_default": True, "midframe_default": True},
            "clips": [{"id": "EP01_CLIP01", "duration": 6,
                       "firstframe_png": "出图/第1集/图片/Clip_01.png", "continuity": cont}]}
    (sb_dir / "storyboard.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(root)


def test_midframe_default_policy_blocks_undeclared_clip(tmp_path):
    root = _write_midframe_policy_storyboard(tmp_path, {})
    gate.check_storyboard_contract(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and "三帧契约" in f["msg"] for f in _midframe_findings())


def test_midframe_default_policy_accepts_exempt_reason(tmp_path):
    root = _write_midframe_policy_storyboard(
        tmp_path, {"midframe_exempt_reason": "极短镜 <3s，中帧与首尾几乎重合"})
    gate.check_storyboard_contract(root, "第1集")
    assert _midframe_findings() == []


def test_midframe_default_policy_accepts_declared_anchor(tmp_path):
    root = _write_midframe_policy_storyboard(
        tmp_path, {"anchors": [{"anchor_png": "出图/第1集/图片/Clip_01_mid.png",
                                "at_sec": 3.0, "use": "qc",
                                "reason": "default: 三帧契约（use=qc）"}]})
    _mk_png(tmp_path / "work", "第1集", "Clip_01_mid.png")
    _record_image_event(tmp_path / "work", "第1集", "出图/第1集/图片/Clip_01_mid.png")
    gate.check_storyboard_contract(root, "第1集")
    assert _midframe_findings() == []


def test_compliance_regulatory_filing_pending_blocks_at_compose(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root, status_overrides={
        "distribution_intent": "paid_distribution",
        "regulatory_filing.pre_broadcast_review": "pending",
        "regulatory_filing.release_filing_no": "TODO: 上线备案号",
    })
    gate.check_compliance_manifest(str(root), "第1集", "compose")
    assert any(f["sev"] == gate.BLOCK and "regulatory_filing" in f["loc"] and "pre_broadcast_review" in f["msg"] for f in gate.findings)
    assert any(f["sev"] == gate.BLOCK and "regulatory_filing" in f["loc"] and "release_filing_no" in f["msg"] for f in gate.findings)


def test_compliance_regulatory_filing_internal_only_is_info(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root, status_overrides={
        "distribution_intent": "internal_only",
        "regulatory_filing.pre_broadcast_review": "pending",
        "regulatory_filing.release_filing_no": "TODO",
    })
    gate.check_compliance_manifest(str(root), "第1集", "compose")
    reg = [f for f in gate.findings if "regulatory_filing" in f["loc"]]
    assert reg and all(f["sev"] == gate.INFO for f in reg)


def test_compliance_regulatory_filing_good_passes_at_compose(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root)  # filled regulatory_filing, publish_candidate
    gate.check_compliance_manifest(str(root), "第1集", "compose")
    assert not any("regulatory_filing" in f["loc"] for f in gate.findings)
