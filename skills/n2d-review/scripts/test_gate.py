import json
import hashlib
import os
import datetime as dt
from pathlib import Path

import gate

_TEST_PNG_BYTES = b"\x89PNG\r\n\x1a\n"
_TEST_PNG_SHA256 = hashlib.sha256(_TEST_PNG_BYTES).hexdigest()


def test_loads_json_from_noisy_stdout_uses_last_json_object():
    payload = gate._loads_json_from_noisy_stdout(
        "Applied providers: ['CPUExecutionProvider'], with options: {'CPUExecutionProvider': {}}\n"
        "find model: /tmp/model.onnx detection [1, 3, '?', '?']\n"
        '{"summary": {"total_block": 3}, "findings": []}\n'
    )

    assert payload["summary"]["total_block"] == 3


def test_preventive_contracts_gate_forwards_block(monkeypatch, tmp_path):
    gate.findings.clear()

    def fake_run(cmd, *args, **kwargs):
        payload = {
            "status": "blocked",
            "findings": [{
                "gate": "shot_intent_gate",
                "severity": "block",
                "loc": "脚本/第1集/storyboard.json",
                "message": "逐镜缺戏剧功能/剪辑意图：Clip_01",
                "return_to_stage": "script_stage2",
            }],
        }
        return gate.subprocess.CompletedProcess(cmd, 2, json.dumps(payload, ensure_ascii=False), "")

    monkeypatch.setattr(gate.subprocess, "run", fake_run)

    gate.check_preventive_contracts(str(tmp_path), "第1集", "image_prompt_preflight")

    assert any(
        f["dim"] == "预防式合同"
        and f["sev"] == gate.BLOCK
        and f.get("return_to_stage") == "script_stage2"
        for f in gate.findings
    )


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
**人物审美基线**：默认主流审美、镜头友好、精致好看但不网红脸；五官比例协调、妆造服装耐看，同时保持沈念的年龄、病弱处境和角色 DNA。
**资产引用注册层**：`LOC_01` 冷宫寝殿；从 `出图/共享/asset_registry.json` 继承 reference_group / constraints / drift_forbidden；锁本场 layout/axis/light_anchor。
**近景/反打身份锁定**：本镜是 CU 近景，必须引用 `定妆_沈念_脸部特写.png` 或表情参考；锁脸型、五官比例、发型发髻、标志配饰和服装配色，不得换脸。
**尾帧接力生成方式**：正反打/表情尾帧必须以同镜首帧或上一张成图 image2image 图生图为母图，不得纯文生图；只改表情/眼神/嘴角，不重画演员脸、发髻、配饰和服装。

**导演视角八维**
| 维度 | 本镜填什么 |
|---|---|
| ① 镜头 | CU + 浅景深 |
| ② 机位 | 微俯视 |
| ③ 人物 | 锚点句：凤眼薄唇·乌黑半披发带·月白旧宫装；人物审美基线=主流审美、镜头友好、好看但不网红脸 |
| ④ 动作 | 抬眼 |
| ⑤ 场景 | 冷宫寝殿 |
| ⑥ 光影 | 侧逆光 |
| ⑦ 情绪 | 克制紧张 |
| ⑧ 画质 | 9:16 cinematic |

### 正向 prompt（中文）
```text
身份保持：`CHAR_SHEN/常态`；锚点句：凤眼薄唇·乌黑半披发带·月白旧宫装；从共享定妆 image2image / 多图参考派生，脸型、发型、服装主色和关键配饰不漂；
镜头构图：CU 微俯视，守画右视线方向，竖屏9:16；
动作瞬间：沈念抬眼的起幅瞬间，按缓慢推近预留构图余量；
场景光影：冷宫寝殿，画左前烛光顶侧光 / 3000K 暖，继承本场光位锚；
情绪张力：克制紧张，观众应读到沈念压住恐惧；
画风规格：冷灰写实3D国风漫剧，9:16，风格禁忌=照片皮肤、3D塑料、风格跳变；
禁止：不要换脸、不要改年龄、不要改服装、不要改场景/光位、不要新增人物/道具、不要文字/logo/水印、不要风格漂移；
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
**近景/反打身份锁定**：本镜是说话近景；优先引用 expressions/脸部特写，缺脸部特写时用正脸 front + 侧面 + 半身 reference_group；锁脸型、五官比例、发型发髻、标志配饰、服装配色；只允许眼神和嘴角小幅变化，脸漂则用 MCU/侧脸/反应镜保真实现。
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
近景身份锁定约束：近景优先脸部特写/表情参考；缺 reference_controls 时只做低幅度眼神和嘴角变化，不大幅转头，不重绘五官，配角近景不稳则用 MCU/OTS/侧脸保真实现；
原生音画约束：默认禁止原生人声，不生成对白/旁白/哼唱；本镜 compose_policy=丢弃；
首帧保持：保持首帧已锁定的沈念脸型、发髻、服装、冷宫寝殿、烛火光位和前景鸩酒托盘，不重定人物外貌、场景布局或光色；
人物运动：沈念急促呼吸后缓慢抬眼，表情从惊惧压成克制；
镜头运动：略俯 MCU 缓慢推近 0.5x，结尾稳定停住；
情绪节奏：[0-2s] 惊惧呼吸压住；[2-4s] 眼神缓慢聚焦；[4-5s] 克制停住，为下一镜留半拍；
动态细节：残烛火光在脸侧跳动，床幔阴影轻颤，冷雾贴地流动；
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按 eyeline cut 服务下一镜；
禁止：不要换脸、不要换衣、不要新增人物或道具、不要改变冷宫场景和烛火光位、不要生成文字/logo/水印、不要生成原生人声；
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


def test_route_frame_capability_warns_for_mid_anchor_on_first_last_backend(tmp_path):
    route = {"clip_id": "Clip_01", "primary_backend": "kling"}
    requirements = {1: {"need_end": True, "anchor_count": 1, "total_timeline_frames": 3}}

    gate.check_route_frame_capability(str(tmp_path), "第1集", route, "routes.json", 1, requirements, "可灵/Kling")

    assert any(f["dim"] == "多帧能力" and f["sev"] == "warn" for f in gate.findings)


def test_route_frame_capability_allows_seedance_via_dreamina_multiframe(tmp_path):
    route = {"clip_id": "Clip_01", "primary_backend": "seedance"}
    requirements = {1: {"need_end": True, "anchor_count": 1, "total_timeline_frames": 3}}

    gate.check_route_frame_capability(str(tmp_path), "第1集", route, "routes.json", 1, requirements, "即梦/Dreamina")

    assert not gate.findings


def test_route_frame_capability_blocks_mid_anchor_for_high_risk_clip(tmp_path):
    # 高风险镜（打斗/大表情近景）帧能力不匹配从 WARN 升 BLOCK
    route = {"clip_id": "Clip_01", "primary_backend": "kling"}
    requirements = {1: {"need_end": True, "anchor_count": 1, "total_timeline_frames": 3, "high_risk": True}}

    gate.check_route_frame_capability(str(tmp_path), "第1集", route, "routes.json", 1, requirements, "可灵/Kling")

    assert any(f["dim"] == "多帧能力" and f["sev"] == "block" for f in gate.findings)


def test_route_frame_capability_high_risk_endframe_blocks(tmp_path):
    # 高风险镜需要尾帧但后端不支持 → BLOCK（双帧安全网静默失效不许放行）
    route = {"clip_id": "Clip_01", "primary_backend": "vidu"}
    requirements = {1: {"need_end": True, "anchor_count": 0, "total_timeline_frames": 2, "high_risk": True}}

    gate.check_route_frame_capability(str(tmp_path), "第1集", route, "routes.json", 1, requirements, "")

    # vidu 等只收首帧/参考图的后端：need_end 且不支持尾帧 → 首尾帧能力 block
    assert any(f["dim"] == "首尾帧能力" and f["sev"] == "block" for f in gate.findings)


def test_route_frame_capability_blocks_endframe_mismatch_in_production(tmp_path):
    (tmp_path / "_设置.md").write_text("- 一致性严格度: production\n", encoding="utf-8")
    route = {"clip_id": "Clip_01", "primary_backend": "vidu"}
    requirements = {1: {"need_end": True, "anchor_count": 0, "total_timeline_frames": 2}}

    gate.check_route_frame_capability(str(tmp_path), "第1集", route, "routes.json", 1, requirements, "")

    assert any(f["dim"] == "首尾帧能力" and f["sev"] == "block" and "production" in f["msg"]
               for f in gate.findings)


def test_action_anchor_contract_blocks_long_fight_with_only_midframe(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [{
            "id": "EP01_CLIP01",
            "duration": 10.0,
            "template": "fight_exchange",
            "template_contract": {"template_id": "fight_exchange", "beats": ["起手", "命中", "收势"]},
            "continuity": {
                "start_state": "s",
                "end_state": "e",
                "transition": "硬切",
                "need_endframe": True,
                "midframe": {"midframe_png": "出图/第1集/图片/镜头01_mid.png", "split_at_sec": 5.0, "reason": "default"},
            },
        }],
    )

    gate.check_action_anchor_contract(root, "第1集", "video_preflight")

    assert any(f["dim"] == "重动作多中帧" and f["sev"] == gate.BLOCK and "continuity.anchors" in f["msg"]
               for f in gate.findings)


def test_action_anchor_contract_allows_long_fight_with_anchors(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [{
            "id": "EP01_CLIP01",
            "duration": 10.0,
            "template": "fight_exchange",
            "template_contract": {"template_id": "fight_exchange", "beats": ["起手", "命中", "收势"]},
            "continuity": {
                "start_state": "s",
                "end_state": "e",
                "transition": "硬切",
                "need_endframe": True,
                "anchors": [
                    {"anchor_png": "出图/第1集/图片/镜头01_a1.png", "at_sec": 3.0, "reason": "起手后"},
                    {"anchor_png": "出图/第1集/图片/镜头01_a2.png", "at_sec": 6.5, "reason": "命中收势"},
                ],
            },
        }],
    )

    gate.check_action_anchor_contract(root, "第1集", "video_preflight")

    assert not gate.findings


def test_action_anchor_contract_ignores_long_dialogue_with_literal_hand_or_name(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [{
            "id": "EP01_CLIP03",
            "duration": 11.0,
            "template": "dialogue_shot_reverse",
            "template_contract": {
                "template_id": "dialogue_shot_reverse",
                "beats": ["张老大手掌拍肩下命令", "江剑背影收拾行囊", "贺平生低头应是"],
            },
            "continuity": {
                "start_state": "s",
                "end_state": "e",
                "transition": "硬切",
                "need_endframe": True,
            },
        }],
    )

    gate.check_action_anchor_contract(root, "第1集", "video_preflight")

    assert not gate.findings


def test_spectacle_sequence_plan_missing_blocks(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [{"id": "Clip 1", "template": "fight_exchange", "scene": "沈念挥剑命中追兵"}],
    )

    gate.check_spectacle_sequence_plan(root, "第1集")

    assert any(f["dim"] == "高动态序列总账" and f["sev"] == gate.BLOCK for f in gate.findings)


def test_spectacle_sequence_plan_covering_clip_passes(tmp_path):
    root = Path(_write_storyboard_with_clips(
        tmp_path,
        [{"id": "Clip 1", "template": "fight_exchange", "scene": "沈念挥剑命中追兵"}],
    ))
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    (prod / "spectacle_sequence_plan_第1集.json").write_text(json.dumps({
        "kind": "n2d_spectacle_sequence_plan",
        "sequences": [{"sequence_id": "SEQ_001", "clip_order": ["Clip_01"]}],
    }, ensure_ascii=False), encoding="utf-8")

    gate.check_spectacle_sequence_plan(str(root), "第1集")

    assert not any(f["dim"] == "高动态序列总账" for f in gate.findings)


def test_route_execution_recipe_missing_blocks():
    gate.check_route_execution_recipe({"clip_id": "Clip_01"}, "routes.json", 1)

    assert any(f["dim"] == "执行配方" and f["sev"] == gate.BLOCK for f in gate.findings)


def test_route_execution_recipe_complete_passes():
    gate.check_route_execution_recipe({
        "clip_id": "Clip_01",
        "execution_recipe": {
            "frame_inputs": {"first_frame": "a.png", "consumption_mode": "first_last", "native_timeline_frames": []},
            "reference_inputs": {"characters": [], "assets": [], "max_reference_images": 0, "motion_reference": {}},
            "control_inputs": {"required": True, "manifest_path": "出视频/第1集/control/Clip_01/motion_control_manifest.json"},
            "audio_inputs": {},
            "fallback": {},
            "capability_match": {},
        },
    }, "routes.json", 1)

    assert not gate.findings


# ── 表情跨度结构化闸门（finding #1：跨情绪近景必须首尾双帧） ─────────────────────────
def _clip(span=None, *, need_end=True, lens="CU 50mm", template="dialogue_closeup", desc="脸部特写"):
    cont = {"start_state": "a", "end_state": "b", "transition": "硬切", "need_endframe": need_end}
    if span is not None:
        cont["expression_span"] = span
    return {"id": "Clip_01", "label": "对峙", "duration": 5.0, "template": template,
            "shots": [{"t": "0-5s", "lens": lens, "desc": desc}], "continuity": cont}


def test_expression_span_absent_is_skipped(tmp_path):
    root = _write_storyboard_with_clips(tmp_path, [_clip(span=None)])
    gate.check_expression_span_frame_contract(root, "第1集")
    assert not gate.findings  # opt-in：未声明=不追踪


def test_expression_span_big_closeup_without_endframe_blocks(tmp_path):
    root = _write_storyboard_with_clips(tmp_path, [_clip(span="大", need_end=False)])
    gate.check_expression_span_frame_contract(root, "第1集")
    assert any(f["dim"] == "表情一致性" and f["sev"] == "block" for f in gate.findings)


def test_expression_span_big_closeup_with_endframe_passes(tmp_path):
    root = _write_storyboard_with_clips(tmp_path, [_clip(span="大", need_end=True)])
    gate.check_expression_span_frame_contract(root, "第1集")
    assert not gate.findings


def test_expression_span_micro_closeup_without_endframe_ok(tmp_path):
    # 微/中 同情绪变化不必双帧
    root = _write_storyboard_with_clips(tmp_path, [_clip(span="微", need_end=False)])
    gate.check_expression_span_frame_contract(root, "第1集")
    assert not gate.findings


def test_expression_span_invalid_value_blocks(tmp_path):
    root = _write_storyboard_with_clips(tmp_path, [_clip(span="特大")])
    gate.check_expression_span_frame_contract(root, "第1集")
    assert any(f["dim"] == "表情一致性" and f["sev"] == "block" for f in gate.findings)


def test_expression_span_big_non_closeup_warns(tmp_path):
    # 大表情但景别是远景（LS）→ WARN（景别可能标错），不 BLOCK
    root = _write_storyboard_with_clips(
        tmp_path, [_clip(span="大", need_end=False, lens="LS 35mm",
                         template="empty_establishing", desc="远景城池建制")])
    gate.check_expression_span_frame_contract(root, "第1集")
    assert any(f["dim"] == "表情一致性" and f["sev"] == "warn" for f in gate.findings)
    assert not any(f["sev"] == "block" for f in gate.findings)


# ── 表情库覆盖闸（把表情锚提到与脸锚同级：大表情近景 + 核心角色必须建表情库·BLOCK） ──────
def _big_expr_clip(char_id="CHAR_01"):
    # 跨情绪大表情近景镜，scene 文本里引用某角色 id（供回连定位）。
    return {"id": "Clip_01", "label": "决裂", "duration": 5.0, "template": "dialogue_closeup",
            "scene": f"{char_id} 由隐忍转暴怒，泪崩", "firstframe_png": "出图/第1集/图片/镜头1.png",
            "shots": [{"t": "0-5s", "lens": "CU 50mm", "desc": "脸部特写"}],
            "continuity": {"start_state": "隐忍", "end_state": "暴怒", "transition": "硬切",
                           "need_endframe": True, "expression_span": "大"}}


def _reg(characters):
    return {"kind": "n2d_identity_registry", "characters": characters}


def test_core_expression_coverage_blocks_when_core_char_lacks_expression_lib(tmp_path):
    root = _write_storyboard_with_clips(tmp_path, [_big_expr_clip("CHAR_01")])
    _write_identity_registry(tmp_path, _reg([
        {"id": "CHAR_01", "name": "沈念", "scope": "贯穿全篇主角",
         "forms": [{"form": "真身", "reference_group": {"front": "a.png"}}]}]))  # 无 expression_anchors

    gate.check_core_expression_anchor_coverage(root, "第1集")

    assert any(f["dim"] == "表情一致性" and f["sev"] == "block"
               and "未建表情库" in f["msg"] for f in gate.findings)


def test_core_expression_coverage_passes_when_anchors_exist(tmp_path):
    root = _write_storyboard_with_clips(tmp_path, [_big_expr_clip("CHAR_01")])
    _write_identity_registry(tmp_path, _reg([
        {"id": "CHAR_01", "name": "沈念", "scope": "贯穿全篇主角",
         "forms": [{"form": "真身", "expression_anchors": [{"emotion": "暴怒", "path": "怒.png"}]}]}]))

    gate.check_core_expression_anchor_coverage(root, "第1集")

    assert not gate.findings


def test_core_expression_coverage_skipped_without_big_expression(tmp_path):
    # 本集无 expression_span=大 镜 → opt-in 未启用追踪，即便核心角色没表情库也跳过。
    root = _write_storyboard_with_clips(tmp_path, [_clip(span="微", need_end=False)])
    _write_identity_registry(tmp_path, _reg([
        {"id": "CHAR_01", "name": "沈念", "scope": "贯穿全篇主角", "forms": [{"form": "真身"}]}]))

    gate.check_core_expression_anchor_coverage(root, "第1集")

    assert not gate.findings


def test_core_expression_coverage_ignores_non_core_char(tmp_path):
    # 大表情近景但只引用一次性配角（非核心长线）→ 不前置 BLOCK（ROI 驱动）。
    root = _write_storyboard_with_clips(tmp_path, [_big_expr_clip("CHAR_07")])
    _write_identity_registry(tmp_path, _reg([
        {"id": "CHAR_07", "name": "路人甲", "scope": "单元配角", "forms": [{"form": "default"}]}]))

    gate.check_core_expression_anchor_coverage(root, "第1集")

    assert not gate.findings


# ── 首/尾帧路径相等校验（finding #3：两侧各查存在，还须是同一张） ───────────────────
def _write_video_clip_prompt(root, body):
    p = Path(root) / "出视频" / "第1集" / "prompt"
    p.mkdir(parents=True, exist_ok=True)
    (p / "01_clips.md").write_text(body, encoding="utf-8")


def _touch_png(root, rel):
    full = Path(root) / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(b"\x89PNG\r\n")
    return rel


def test_video_prompt_firstframe_mismatch_blocks(tmp_path):
    a = "出图/第1集/图片/镜头1_A.png"
    b = "出图/第1集/图片/镜头1_B.png"
    root = _write_storyboard_with_clips(tmp_path, [
        {"firstframe_png": a, "continuity": {"start_state": "s", "end_state": "e",
         "transition": "硬切", "need_endframe": False}}])
    _touch_png(root, a)
    _touch_png(root, b)
    _write_video_clip_prompt(root, f"## Clip 01\n\n**首帧**：`{b}`\n")
    gate.check_video_prompt_frames(root, "第1集")
    assert any(f["dim"] == "首帧" and f["sev"] == "block" for f in gate.findings)


def test_video_prompt_firstframe_match_passes(tmp_path):
    a = "出图/第1集/图片/镜头1_A.png"
    root = _write_storyboard_with_clips(tmp_path, [
        {"firstframe_png": a, "continuity": {"start_state": "s", "end_state": "e",
         "transition": "硬切", "need_endframe": False}}])
    _touch_png(root, a)
    # 视频侧用 ./ 前缀写同一张，归一化后应相等
    _write_video_clip_prompt(root, "## Clip 01\n\n**首帧**：`./出图/第1集/图片/镜头1_A.png`\n")
    gate.check_video_prompt_frames(root, "第1集")
    assert not any(f["dim"] == "首帧" for f in gate.findings)


def test_video_prompt_endframe_mismatch_warns(tmp_path):
    f1 = "出图/第1集/图片/镜头1_A.png"
    e1 = "出图/第1集/图片/镜头1_end.png"
    e2 = "出图/第1集/图片/镜头1_end_other.png"
    root = _write_storyboard_with_clips(tmp_path, [
        {"firstframe_png": f1, "continuity": {"start_state": "s", "end_state": "e",
         "transition": "硬切", "need_endframe": True, "endframe_png": e1}}])
    for rel in (f1, e1, e2):
        _touch_png(root, rel)
    _write_video_clip_prompt(root, f"## Clip 01\n\n**首帧**：`{f1}`\n**尾帧**：`{e2}`\n")
    gate.check_video_prompt_frames(root, "第1集")
    assert any(f["dim"] == "尾帧" and f["sev"] == "warn" for f in gate.findings)


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
        "check_image_backend_api_refresh",
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
        "check_action_anchor_contract",
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
        "check_action_anchor_contract",
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
        "check_consistency_audit_gate",
    ]:
        monkeypatch.setattr(gate, name, mark(name))

    gate.run(str(root), "第1集", "video")

    assert "check_multimodal_continuity" in calls
    assert calls.index("check_image_assets") < calls.index("check_multimodal_continuity")
    assert calls.index("check_multimodal_continuity") < calls.index("check_prompt_checklists")
    assert calls.index("check_prompt_checklists") < calls.index("check_video_stage_raw_output_policy")
    assert calls.index("check_state_continuity") < calls.index("check_consistency_audit_gate")


def test_good_character_shot_prompt_passes_strict_structure():
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, GOOD_SHOT)
    assert gate.findings == []


def test_image_shot_missing_structured_prompt_fields_blocks():
    bad = GOOD_SHOT.replace(
        "身份保持：`CHAR_SHEN/常态`；锚点句：凤眼薄唇·乌黑半披发带·月白旧宫装；从共享定妆 image2image / 多图参考派生，脸型、发型、服装主色和关键配饰不漂；\n",
        "",
    ).replace(
        "动作瞬间：沈念抬眼的起幅瞬间，按缓慢推近预留构图余量；\n",
        "",
    ).replace(
        "禁止：不要换脸、不要改年龄、不要改服装、不要改场景/光位、不要新增人物/道具、不要文字/logo/水印、不要风格漂移；\n",
        "",
    )

    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, bad)

    for key in ("身份保持", "动作瞬间", "禁止"):
        assert any(f["sev"] == gate.BLOCK and f["dim"] == "prompt" and key in f["msg"] for f in gate.findings)


def test_image_shot_prompt_missing_post_generation_self_check_blocks():
    bad = GOOD_SHOT.split("### 自检（生成后逐张过 · 落档闸门）", 1)[0]
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, bad)
    assert any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "prompt"
        and "缺生成后逐张自检段" in str(f["msg"])
        for f in gate.findings
    )


# ── 双人同框 × 单图参考后端 升 BLOCK（脸漂真凶工程化）─────────────────────────
TWO_CHAR_SHOT = GOOD_SHOT.replace(
    "- `出图/共享/图片/定妆_沈念_半身.png`（服装锚，强度 0.5）\n",
    "- `出图/共享/图片/定妆_沈念_半身.png`（服装锚，强度 0.5）\n"
    "- `出图/共享/图片/定妆_柳娘子.png`（柳娘子正脸主参考，强度 0.6）\n",
)

MULTI_SUBJECT_SLOT_FIELDS = (
    "**多人同框身份槽位**：LEFT_SLOT=`CHAR_SHEN/常态*`（primary，画左前景，视线画右，参考=沈念 front+脸部特写/expressions）；"
    "RIGHT_SLOT=`CHAR_LIU/常服`（secondary，画右后景，视线画左，参考=柳娘子 front+半身）。\n"
    "**多人同框执行策略**：split_composite_required；分别出图+合成（登记降级），这是硬执行，不是条件式兜底。\n"
    "**区分锚点**：沈念=乌黑半披+月白粗布；柳娘子=高髻+绛红裙；两两发色/服装主色互斥不撞色。\n"
)

REGIONAL_MULTI_SUBJECT_FIELDS = (
    "**多人同框身份槽位**：LEFT_SLOT=`CHAR_SHEN/常态*`（primary，画左前景，视线画右，参考=沈念 front+脸部特写/expressions）；"
    "RIGHT_SLOT=`CHAR_LIU/常服`（secondary，画右后景，视线画左，参考=柳娘子 front+半身）。\n"
    "**多人同框执行策略**：regional_construct_required；split_composite_required；"
    "empty_plate=`出图/第1集/区域构建/Clip_01/empty_plate.png`；region masks=`masks.json`；"
    "官方 inpaint / regional-prompt 分区构建，统一 relighting/color match；这是硬执行，不是条件式兜底。\n"
    "**区分锚点**：沈念=乌黑半披+月白粗布；柳娘子=高髻+绛红裙；两两发色/服装主色互斥不撞色。\n"
)


def test_two_char_shot_on_single_ref_backend_is_blocked():
    # 单图参考后端(Codex 类，无原生主体锁) + 双人同框 + 未声明多主体策略 → BLOCK
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, TWO_CHAR_SHOT, single_ref_backend=True)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "角色一致性" and "同框" in str(f["msg"])
               for f in gate.findings)


def test_plain_multiref_does_not_escape_codex_two_char_block():
    # Codex 类后端的普通多参考不是持久角色 ID；多人同框仍必须拆分出图/合成或切原生主体后端
    shot = TWO_CHAR_SHOT.replace(
        "**专项镜头模板**：dialogue_shot_reverse；",
        "**专项镜头模板**：dialogue_shot_reverse；多参考策略=普通多参考；",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot, single_ref_backend=True)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "角色一致性" and "普通多参考不是持久主体锁" in str(f["msg"])
               for f in gate.findings)


def test_two_char_shot_on_native_subject_backend_blocks_without_slots():
    # 2026-06：多主体后端(Seedream/可灵/Sora)同框缺空间槽位/执行策略也升 BLOCK——
    # 空间绑定是同框一致性硬约束（无绑定 → 模型把两张脸平均/混位，多主体后端亦然）。
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, TWO_CHAR_SHOT, single_ref_backend=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "角色一致性" and "同框" in str(f["msg"])
               for f in gate.findings)


# ── #5 多人近景同框：槽位绑定不够，近景必须分开生成（SOTA：单帧多主体 cross-attention 串脸） ──
# 仅靠单帧身份槽位（一次生成多张脸）、无反打/分别出图 → 即便原生主体后端也升 BLOCK（近景档收口）。
SLOT_FIELDS_SLOTONLY = (
    "**多人同框身份槽位**：LEFT_SLOT=`CHAR_SHEN/常态*`（primary，画左前景，视线画右）；"
    "RIGHT_SLOT=`CHAR_LIU/常服`（secondary，画右后景，视线画左）。\n"
    "**多人同框执行策略**：native_subject_slots；区域绑定。\n"   # 注意：无「分别出图」——纯单帧槽位绑定
    "**区分锚点**：沈念=乌黑半披+月白粗布；柳娘子=高髻+绛红裙；两两互斥不撞色。\n"
)


def test_multi_person_closeup_on_native_backend_requires_split_not_just_slots():
    # 原生主体后端 + 多人近景，只有单帧槽位绑定（无反打/分别出图）→ 升 BLOCK（近景串脸槽位治不了）。
    shot = TWO_CHAR_SHOT.replace(
        "**专项镜头模板**：dialogue_shot_reverse；",
        "**专项镜头模板**：dialogue_shot_reverse；native_subject_slots；\n" + SLOT_FIELDS_SLOTONLY,
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot, single_ref_backend=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "构图景别" and "近景" in str(f["msg"])
               for f in gate.findings)


def test_multi_person_closeup_escapes_when_split_declared():
    # 声明了分别出图+合成（真分开生成）→ 不再触发近景同框 BLOCK。
    shot = TWO_CHAR_SHOT.replace(
        "**专项镜头模板**：dialogue_shot_reverse；",
        "**专项镜头模板**：dialogue_shot_reverse；native_subject_slots；\n" + MULTI_SUBJECT_SLOT_FIELDS,
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot, single_ref_backend=False)
    assert not any(f["dim"] == "构图景别" and "近景" in str(f["msg"]) for f in gate.findings)


def test_multi_person_closeup_escapes_when_regional_construct_declared():
    shot = TWO_CHAR_SHOT.replace(
        "**专项镜头模板**：dialogue_shot_reverse；",
        "**专项镜头模板**：dialogue_shot_reverse；\n" + REGIONAL_MULTI_SUBJECT_FIELDS,
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot, single_ref_backend=True)
    assert not any(f["dim"] == "角色一致性" and "同框" in str(f["msg"]) for f in gate.findings)
    assert not any(f["dim"] == "构图景别" and "近景" in str(f["msg"]) for f in gate.findings)


def test_native_subject_backend_with_slots_escapes_block():
    # 多主体后端写齐执行策略 + 身份槽位 → 逃生门放行，无同框 finding
    shot = TWO_CHAR_SHOT.replace(
        "**专项镜头模板**：dialogue_shot_reverse；",
        "**专项镜头模板**：dialogue_shot_reverse；native_subject_slots；\n" + MULTI_SUBJECT_SLOT_FIELDS,
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot, single_ref_backend=False)
    assert not any("同框" in str(f["msg"]) for f in gate.findings)


# ── ① 长线剧 × 无持久主体后端 → 核心/常驻角色强制身份锁（治跨集脸漂累积）──
def test_long_running_weak_backend_advises_on_codex_ep3():
    # Codex(无持久主体) + 到第3集 → 建议升档
    assert gate.long_running_weak_backend_advice("codex", 3, 1) is True


def test_long_running_weak_backend_silent_on_short_drama():
    # 单集/双集 demo 不打扰
    assert gate.long_running_weak_backend_advice("codex", 1, 1) is False
    assert gate.long_running_weak_backend_advice("codex", 2, 2) is False


def test_long_running_weak_backend_counts_existing_episodes():
    # 当前集号小但已有 ≥阈值 集存在（多集长剧）→ 仍建议
    assert gate.long_running_weak_backend_advice("codex", 1, 4) is True


def test_long_running_weak_backend_silent_on_persistent_subject_backend():
    # 已是原生主体/主体库后端(Seedream/可灵/Sora) → 不提示，无论多少集
    for canon in ("seedream", "kling", "sora"):
        assert gate.long_running_weak_backend_advice(canon, 50, 50) is False


def _write_weak_backend_registry(tmp_path, *, locked=False, lora=None, image_adapter=None):
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True, exist_ok=True)
    adapters = {"image": image_adapter or {}, "lora": {"status": "candidate"}}
    if locked:
        adapters = {"image": {"face_embedding": {"status": "ready"}}, "lora": {"status": "candidate"}}
    if lora is not None:
        adapters["lora"] = lora
    (shared / "identity_registry.json").write_text(json.dumps({
        "characters": [{
            "id": "CHAR_01",
            "name": "沈念",
            "scope": "长线女主·全篇",
            "forms": [{"form": "常态", "identity_adapters": adapters}],
        }]
    }, ensure_ascii=False), encoding="utf-8")
    return str(tmp_path)


def test_long_running_weak_backend_blocks_core_without_identity_lock(tmp_path):
    gate.findings.clear()
    root = _write_weak_backend_registry(tmp_path, locked=False)
    (tmp_path / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    gate.check_long_running_weak_backend(root, "第3集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "生图AI一致性" and "缺 native subject" in str(f["msg"])
               for f in gate.findings)


def test_long_running_subjectless_backend_blocks_in_demo_too(tmp_path):
    """铁律：跨集脸漂总闸 demo 也无条件 BLOCK（不随 profile 降级）。曾被 c9d37df5 降成 production-only。"""
    gate.findings.clear()
    root = _write_weak_backend_registry(tmp_path, locked=False)  # 无 _设置.md → 默认 demo profile
    gate.check_long_running_weak_backend(root, "第3集")
    hits = [f for f in gate.findings if f["dim"] == "生图AI一致性"]
    assert hits and all(f["sev"] == gate.BLOCK for f in hits)


def test_long_running_weak_backend_allows_core_with_face_embedding(tmp_path):
    gate.findings.clear()
    root = _write_weak_backend_registry(tmp_path, locked=True)
    (tmp_path / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    gate.check_long_running_weak_backend(root, "第3集")
    assert not any(f["dim"] == "生图AI一致性" for f in gate.findings)


def test_long_running_weak_backend_allows_controlled_image2image_chain(tmp_path):
    gate.findings.clear()
    image_adapter = {
        "codex": {
            "mode": "image2image_reference_chain",
            "status": "ready",
            "actual_image_input_required": True,
            "reference_manifest_required": True,
            "full_qc_required": True,
        }
    }
    root = _write_weak_backend_registry(tmp_path, image_adapter=image_adapter)
    (tmp_path / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")

    gate.check_long_running_weak_backend(root, "第3集")

    assert not any(f["dim"] == "生图AI一致性" for f in gate.findings)


def test_long_running_weak_backend_blocks_lora_not_usable_on_current_backend(tmp_path):
    gate.findings.clear()
    root = _write_weak_backend_registry(tmp_path, lora={"status": "ready", "target_backends": ["sdxl"]})
    (tmp_path / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    gate.check_long_running_weak_backend(root, "第3集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "生图AI一致性" for f in gate.findings)


def test_long_running_weak_backend_blocks_unmarked_core_registry(tmp_path):
    gate.findings.clear()
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True, exist_ok=True)
    (tmp_path / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    (shared / "identity_registry.json").write_text(json.dumps({
        "characters": [{
            "id": "CHAR_01",
            "name": "沈念",
            "scope": "未标注",
            "forms": [{"form": "常态", "identity_adapters": {"image": {}}}],
        }]
    }, ensure_ascii=False), encoding="utf-8")

    gate.check_long_running_weak_backend(str(tmp_path), "第3集")

    assert any(
        f["sev"] == gate.BLOCK and f["dim"] == "生图AI一致性" and "未标出核心/常驻角色" in f["msg"]
        for f in gate.findings
    )


def test_two_char_shot_with_registered_degradation_escapes_even_on_single_ref():
    # 即便单图参考后端，本镜声明「分别出图」登记降级 + 身份槽位 → 逃生门放行，无同框 finding
    shot = TWO_CHAR_SHOT.replace(
        "**专项镜头模板**：dialogue_shot_reverse；",
        "**专项镜头模板**：dialogue_shot_reverse；分别出图+合成（登记降级）；\n" + MULTI_SUBJECT_SLOT_FIELDS,
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot, single_ref_backend=True)
    assert not any("同框" in str(f["msg"]) for f in gate.findings)


def test_four_named_chars_in_one_shot_is_blocked_as_over_cap():
    # ≥4 具名角色清晰同框 → 硬上限 BLOCK（任何后端单帧压不住 4+ 张清晰脸）
    shot = TWO_CHAR_SHOT.replace(
        "- `出图/共享/图片/定妆_柳娘子.png`（柳娘子正脸主参考，强度 0.6）\n",
        "- `出图/共享/图片/定妆_柳娘子.png`（柳娘子正脸主参考，强度 0.6）\n"
        "- `出图/共享/图片/定妆_王敦.png`（王敦正脸，强度 0.6）\n"
        "- `出图/共享/图片/定妆_小禾.png`（小禾正脸，强度 0.6）\n",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot, single_ref_backend=True)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "构图景别" and "≥4 具名角色" in str(f["msg"])
               for f in gate.findings)


def test_four_named_chars_wide_crowd_shot_escapes_over_cap():
    # 远景群像（脸不解析）显式标记 → 不触发 ≥4 硬上限
    shot = TWO_CHAR_SHOT.replace(
        "- `出图/共享/图片/定妆_柳娘子.png`（柳娘子正脸主参考，强度 0.6）\n",
        "- `出图/共享/图片/定妆_柳娘子.png`（柳娘子正脸主参考，强度 0.6）\n"
        "- `出图/共享/图片/定妆_王敦.png`（王敦正脸，强度 0.6）\n"
        "- `出图/共享/图片/定妆_小禾.png`（小禾正脸，强度 0.6）\n",
    ).replace("**专项镜头模板**：dialogue_shot_reverse；",
              "**专项镜头模板**：群像远景，脸不解析；")
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot, single_ref_backend=True)
    assert not any("≥4 具名角色" in str(f["msg"]) for f in gate.findings)


def test_multi_char_missing_distinct_anchor_warns_on_codex():
    # ④ 多人同框 × Codex 缺 区分锚点 → WARN
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, TWO_CHAR_SHOT, single_ref_backend=True)
    assert any(f["sev"] == gate.WARN and "区分锚点" in str(f["msg"]) for f in gate.findings)


def test_split_composite_without_identity_slots_still_blocks_codex_multichar():
    # 有硬分层策略但没给每个 CHAR 绑定槽位，合成阶段仍会串脸/不可追责
    shot = TWO_CHAR_SHOT.replace(
        "**专项镜头模板**：dialogue_shot_reverse；",
        "**专项镜头模板**：dialogue_shot_reverse；分别出图+合成（登记降级）；",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot, single_ref_backend=True)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "角色一致性" and "身份槽位" in str(f["msg"])
               for f in gate.findings)


def test_conditional_split_composite_does_not_escape_codex_two_char_block():
    # “若不稳再分层”不是执行策略，不能绕过 Codex 弱后端同框硬闸
    shot = TWO_CHAR_SHOT.replace(
        "**专项镜头模板**：dialogue_shot_reverse；",
        "**专项镜头模板**：dialogue_shot_reverse；若多主体仍不稳，按角色分别出图+合成；",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot, single_ref_backend=True)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "角色一致性" and "普通多参考不是持久主体锁" in str(f["msg"])
               for f in gate.findings)


def test_generic_reference_image_index_lock_is_blocked_for_codex_multichar():
    shot = TWO_CHAR_SHOT.replace(
        "服装配色一致。",
        "身份锁定句：保持与参考图①的人脸、五官比例、发型和服装配色一致。",
    ).replace(
        "脸型、发型、服装主色和关键配饰不漂；",
        "身份锁定句：保持与参考图①的人脸、五官比例、发型和服装配色一致；",
    ).replace(
        "**专项镜头模板**：dialogue_shot_reverse；",
        "**专项镜头模板**：dialogue_shot_reverse；分别出图+合成（登记降级）；",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot, single_ref_backend=True)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "Codex锁脸" and "参考图①" in str(f["msg"])
               for f in gate.findings)


def test_default_arg_blocks_multichar_without_slots():
    # 不传 single_ref_backend（默认 False=多主体后端路径）：同框缺槽位/策略 → BLOCK（2026-06 起空间绑定硬约束）
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, TWO_CHAR_SHOT)
    assert any(f["sev"] == gate.BLOCK and "同框" in str(f["msg"]) for f in gate.findings)


def test_codex_closeup_reaction_requires_face_or_expression_reference():
    shot = GOOD_SHOT.replace("脸部特写", "正脸主参考").replace("表情参考", "正面参考")
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot, single_ref_backend=True)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "Codex锁脸" and "脸部特写/表情库" in str(f["msg"])
               for f in gate.findings)


def test_codex_closeup_reaction_with_face_reference_passes_lock_gate():
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, GOOD_SHOT, single_ref_backend=True)
    assert not any(f["dim"] == "Codex锁脸" for f in gate.findings)


def test_codex_dark_vfx_closeup_requires_face_visibility_guard():
    shot = GOOD_SHOT.replace(
        "**光位锚**：继承本场光位锚",
        "**光位锚**：黑烟暗光特效压脸，继承本场光位锚",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot, single_ref_backend=True)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "Codex锁脸" and "缺脸部可见性约束" in str(f["msg"])
               for f in gate.findings)


def test_codex_dark_vfx_closeup_with_visibility_guard_passes():
    shot = GOOD_SHOT.replace(
        "**光位锚**：继承本场光位锚",
        "**光位锚**：黑烟暗光特效压脸，继承本场光位锚\n**脸部可见性约束**：眼鼻嘴三角区清晰，黑烟不得遮住眼鼻嘴，特效只叠在脸外侧，保留五官，不重画脸。",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot, single_ref_backend=True)
    assert not any(f["dim"] == "Codex锁脸" and "缺脸部可见性约束" in str(f["msg"]) for f in gate.findings)


# ── 弱后端每镜 i2i 强制（P0-a：不止尾帧，每个角色镜都须从定妆 image2image 派生）─────────
def test_codex_character_shot_without_i2i_derivation_is_blocked():
    # 单图参考后端 + 角色镜 + 未声明 image2image/多图参考派生 → BLOCK（纯文生图=跨集换演员）
    shot = GOOD_SHOT.replace("（多图参考派生铁律）", "").replace(
        "；从共享定妆 image2image / 多图参考派生，脸型、发型、服装主色和关键配饰不漂；",
        "；只用文字描述角色，脸型、发型、服装主色和关键配饰不漂；",
    ).replace(
        "**尾帧接力生成方式**：正反打/表情尾帧必须以同镜首帧或上一张成图 image2image 图生图为母图，不得纯文生图；只改表情/眼神/嘴角，不重画演员脸、发髻、配饰和服装。\n",
        "",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot, single_ref_backend=True)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "角色一致性" and "每个" in str(f["msg"]) and "i2i" in str(f["msg"])
               for f in gate.findings)


def test_codex_character_shot_with_i2i_derivation_passes():
    # GOOD_SHOT 自带「多图参考派生」+「image2image」声明 → 弱后端不报 i2i 缺失
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, GOOD_SHOT, single_ref_backend=True)
    assert not any("每个" in str(f["msg"]) and "i2i" in str(f["msg"]) for f in gate.findings)


def test_native_subject_backend_skips_per_shot_i2i_requirement():
    # 原生主体锁后端（single_ref_backend=False）有持久角色 ID，豁免每镜 i2i 硬闸
    shot = GOOD_SHOT.replace("（多图参考派生铁律）", "").replace(
        "**尾帧接力生成方式**：正反打/表情尾帧必须以同镜首帧或上一张成图 image2image 图生图为母图，不得纯文生图；只改表情/眼神/嘴角，不重画演员脸、发髻、配饰和服装。\n",
        "",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot, single_ref_backend=False)
    assert not any(f["dim"] == "角色一致性" and "每个" in str(f["msg"]) and "i2i" in str(f["msg"])
                   for f in gate.findings)


# ── 锚点指纹钉死（P0-b）──────────────────────────────────────────────
def _setup_anchor_registry(tmp_path, anchor_sha=None, png_bytes=b"\x89PNG-anchor-v1"):
    img = tmp_path / "出图" / "共享" / "图片"
    img.mkdir(parents=True)
    (img / "定妆_沈念_常态.png").write_bytes(png_bytes)
    form = {"form": "常态", "reference_group": {"front": "出图/共享/图片/定妆_沈念_常态.png"}}
    if anchor_sha is not None:
        form["anchor_sha"] = anchor_sha
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_01", "name": "沈念", "forms": [form]}]
    }, ensure_ascii=False), encoding="utf-8")
    return str(tmp_path)


def test_anchor_fingerprint_opt_in_skips_when_unpinned(tmp_path):
    root = _setup_anchor_registry(tmp_path, anchor_sha=None)
    gate.check_anchor_fingerprints(root, "第1集")
    assert gate.findings == []


def test_anchor_fingerprint_matches_passes(tmp_path):
    import hashlib
    sha = hashlib.sha256(b"\x89PNG-anchor-v1").hexdigest()
    root = _setup_anchor_registry(tmp_path, anchor_sha=sha)
    gate.check_anchor_fingerprints(root, "第1集")
    assert gate.findings == []


def test_anchor_fingerprint_mismatch_blocks(tmp_path):
    root = _setup_anchor_registry(tmp_path, anchor_sha="0" * 64)
    gate.check_anchor_fingerprints(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "共享定妆" and "被改动" in str(f["msg"])
               for f in gate.findings)


def test_anchor_fingerprint_missing_file_blocks(tmp_path):
    root = _setup_anchor_registry(tmp_path, anchor_sha="0" * 64)
    (tmp_path / "出图" / "共享" / "图片" / "定妆_沈念_常态.png").unlink()
    gate.check_anchor_fingerprints(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "共享定妆" and "锚点丢失" in str(f["msg"])
               for f in gate.findings)


def test_anchor_fingerprint_restricted_partial_prefers_silhouette(tmp_path):
    import hashlib
    img = tmp_path / "出图" / "共享" / "图片"
    img.mkdir(parents=True)
    png_bytes = b"\x89PNG-group-silhouette-v1"
    (img / "定妆_GROUP_群像__常态.png").write_bytes(png_bytes)
    form = {
        "form": "常态",
        "anchor_sha": hashlib.sha256(png_bytes).hexdigest(),
        "no_full_face": True,
        "reference_group": {
            "hand": {"path": "出图/共享/图片/定妆_GROUP_群像__常态_手部局部.png", "status": "planned"},
            "silhouette": {"path": "出图/共享/图片/定妆_GROUP_群像__常态.png", "status": "review_pending"},
        },
        "reference_atlas": {
            "build_tier": "restricted_partial",
            "partial_refs": {
                "hand": {"path": "出图/共享/图片/定妆_GROUP_群像__常态_手部局部.png", "status": "planned"},
                "silhouette": {"path": "出图/共享/图片/定妆_GROUP_群像__常态.png", "status": "review_pending"},
            },
        },
    }
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "GROUP_群像", "name": "群像", "forms": [form]}]
    }, ensure_ascii=False), encoding="utf-8")

    gate.findings.clear()
    gate.check_anchor_fingerprints(str(tmp_path), "第1集")

    assert not [f for f in gate.findings if f["dim"] == "共享定妆" and f["sev"] == gate.BLOCK]


# ── 表情库跨集共享锁定（P1-b）────────────────────────────────────────
def _setup_expr_registry(tmp_path, *, self_check=None, anchor_sha=None, make_file=True,
                         png_bytes=b"\x89PNG-expr-anger-v1"):
    img = tmp_path / "出图" / "共享" / "图片"
    img.mkdir(parents=True)
    if make_file:
        (img / "定妆_沈念_常态_表情_怒.png").write_bytes(png_bytes)
    anchor = {"emotion": "怒", "path": "出图/共享/图片/定妆_沈念_常态_表情_怒.png"}
    if self_check is not None:
        anchor["self_check_passed"] = self_check
    if anchor_sha is not None:
        anchor["anchor_sha"] = anchor_sha
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_01", "name": "沈念", "forms": [
            {"form": "常态", "expression_anchors": [anchor]},
        ]}]
    }, ensure_ascii=False), encoding="utf-8")
    return str(tmp_path)


def test_expression_anchor_opt_in_skips_when_absent(tmp_path):
    (tmp_path / "出图" / "共享").mkdir(parents=True)
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_01", "forms": [{"form": "常态"}]}]
    }, ensure_ascii=False), encoding="utf-8")
    gate.check_expression_anchors(str(tmp_path), "第1集")
    assert gate.findings == []


def test_expression_anchor_finalized_and_unchanged_passes(tmp_path):
    import hashlib
    sha = hashlib.sha256(b"\x89PNG-expr-anger-v1").hexdigest()
    root = _setup_expr_registry(tmp_path, self_check=True, anchor_sha=sha)
    gate.check_expression_anchors(root, "第1集")
    assert gate.findings == []


def test_expression_anchor_missing_file_blocks(tmp_path):
    root = _setup_expr_registry(tmp_path, self_check=True, make_file=False)
    gate.check_expression_anchors(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and "表情锚" in str(f["msg"]) and "图缺失" in str(f["msg"])
               for f in gate.findings)


def test_expression_anchor_dirty_self_check_blocks(tmp_path):
    root = _setup_expr_registry(tmp_path, self_check=False)
    gate.check_expression_anchors(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and "表情锚" in str(f["msg"]) and "未过落档自检" in str(f["msg"])
               for f in gate.findings)


def test_expression_anchor_sha_mismatch_blocks(tmp_path):
    root = _setup_expr_registry(tmp_path, self_check=True, anchor_sha="0" * 64)
    gate.check_expression_anchors(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and "表情锚" in str(f["msg"]) and "被改动" in str(f["msg"])
               for f in gate.findings)


# ── 一角一后端跨集钉（核心 BLOCK / 非核心 WARN）──────────────────────
def _setup_backend_pin_registry(tmp_path, backend_pin, scope="配角"):
    (tmp_path / "出图" / "共享").mkdir(parents=True)
    form = {"form": "常态"}
    if backend_pin is not None:
        form["backend_pin"] = backend_pin
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_01", "name": "沈念", "scope": scope, "forms": [form]}]
    }, ensure_ascii=False), encoding="utf-8")
    return str(tmp_path)  # 无 _设置.md → get_setting 默认 生图AI=Codex


def test_backend_pin_opt_in_skips_when_absent(tmp_path):
    root = _setup_backend_pin_registry(tmp_path, None)
    gate.check_character_backend_pin(root, "第1集")
    assert gate.findings == []


def test_backend_pin_match_passes(tmp_path):
    root = _setup_backend_pin_registry(tmp_path, "Codex")  # 与默认 Codex 一致
    gate.check_character_backend_pin(root, "第1集")
    assert gate.findings == []


def test_backend_pin_mismatch_warns(tmp_path):
    root = _setup_backend_pin_registry(tmp_path, "Seedream")  # 钉 Seedream，项目默认 Codex
    gate.check_character_backend_pin(root, "第1集")
    assert any(f["sev"] == gate.WARN and f["dim"] == "角色一致性" and "身份钉在出图后端" in str(f["msg"])
               for f in gate.findings)


def test_backend_pin_mismatch_blocks_for_core_character(tmp_path):
    root = _setup_backend_pin_registry(tmp_path, "Seedream", scope="长线女主·全篇")
    gate.check_character_backend_pin(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "角色一致性" and "身份钉在出图后端" in str(f["msg"])
               for f in gate.findings)


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


def test_shot_color_temperature_contradiction_warns():
    # 光线落地：单一色温值与暖/冷描述自相矛盾（3000K 偏暖却写"冷调"）→ 光影一致性 WARN
    shot = GOOD_SHOT.replace(
        "**光位锚**：继承本场光位锚（主光：画左前烛光顶侧光 / 3000K 暖 / 动机=残烛），本镜不改光",
        "**光位锚**：继承本场光位锚（主光：画左前 / 3000K 冷调主光），本镜不改光",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert any(f["sev"] == gate.WARN and f["dim"] == "光影一致性" and "自相矛盾" in str(f["msg"])
               for f in gate.findings)


def test_good_shot_color_temperature_no_warn():
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, GOOD_SHOT)
    assert not any(f["dim"] == "光影一致性" and "色温" in str(f["msg"]) for f in gate.findings)


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
    ).replace(
        "**资产引用注册层**：`LOC_01` 冷宫寝殿；从 `出图/共享/asset_registry.json` 继承 reference_group / constraints / drift_forbidden；锁本场 layout/axis/light_anchor。\n",
        "**资产引用注册层**：`LOC_01` 冷宫寝殿；从 `出图/共享/asset_registry.json` 继承场景结构约束；锁本场 layout/axis/light_anchor。\n",
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
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产引用注册层" and "PROP_/WEAPON_/MOUNT_GROUP_xx" in f["msg"] for f in gate.findings)


def test_generic_scene_prop_anchor_phrase_does_not_require_prop_id():
    shot = GOOD_SHOT.replace(
        "**资产引用注册层**：`LOC_01` 冷宫寝殿；从 `出图/共享/asset_registry.json` 继承 reference_group / constraints / drift_forbidden；锁本场 layout/axis/light_anchor。\n",
        "**资产引用注册层**：`LOC_01` 冷宫寝殿；从 `出图/共享/asset_registry.json` 继承 reference_group / constraints / drift_forbidden；锁本场 layout/axis/light_anchor。\n锚点句：无人物或人物不露脸：以场景/道具锚为主\n",
    )
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "资产引用注册层" and "PROP_/WEAPON_/MOUNT_GROUP_xx" in f["msg"] for f in gate.findings)


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

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "契约继承" and "本集视觉一致性契约" in f["msg"] for f in gate.findings)


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

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "契约继承" and "景别阶梯" in f["msg"] for f in gate.findings)


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


def _derived_reference(path, method, source_path):
    return {
        "path": path,
        "status": "ready",
        "derivation": {
            "method": method,
            "source_path": source_path,
            "source_sha256": _TEST_PNG_SHA256,
            "crop_box": [0, 0, 1, 1],
        },
    }


def _identity_registry(overrides=None):
    data = {
        "kind": "n2d_asset_identity_registry",
        "version": 1,
        "characters": [
            {
                "id": "CHAR_SHEN",
                "name": "沈念",
                "scope": "全篇",
                "asset_bundle": {
                    "kind": "project_character_asset_bundle_ref",
                    "manifest": "设定库/character_assets/CHAR_SHEN__shen_nian/manifest.json",
                    "package_dir": "设定库/character_assets/CHAR_SHEN__shen_nian",
                    "role": "female_lead",
                    "sections": ["reference", "prompts", "lora", "voice", "adapters", "qc"],
                    "truth_policy": "manifest_points_to_identity_registry_and_character_bible",
                },
                "forms": [
                    {
                        "form": "常态",
                        "asset_key": "沈念",
                        "anchor_phrase": "凤眼薄唇·乌黑半披发带·月白旧宫装",
                        "character_dna": {
                            "face": "凤眼薄唇，左腕淡疤",
                            "hair": "乌黑半披发带",
                            "outfit": "月白旧宫装",
                            "accessories": "左腕淡疤",
                            "texture": "旧宫装粗布微旧，皮肤自然不过磨",
                        },
                        "reference_group": {
                            "front": "出图/共享/图片/定妆_沈念.png",
                            "three_quarter": _derived_reference(
                                "出图/共享/图片/定妆_沈念_45度.png",
                                "turnaround_split",
                                "出图/共享/图片/定妆_沈念_三视图.png",
                            ),
                            "side": _derived_reference(
                                "出图/共享/图片/定妆_沈念_侧.png",
                                "turnaround_split",
                                "出图/共享/图片/定妆_沈念_三视图.png",
                            ),
                            "back": _derived_reference(
                                "出图/共享/图片/定妆_沈念_背.png",
                                "turnaround_split",
                                "出图/共享/图片/定妆_沈念_三视图.png",
                            ),
                            "half_body": _derived_reference(
                                "出图/共享/图片/定妆_沈念_半身.png",
                                "front_crop",
                                "出图/共享/图片/定妆_沈念.png",
                            ),
                            "turnaround": "出图/共享/图片/定妆_沈念_三视图.png",
                            "face_anchor_refs": [
                                {
                                    "label": "基础脸锚",
                                    **_derived_reference(
                                        "出图/共享/图片/定妆_沈念_脸部特写.png",
                                        "front_crop",
                                        "出图/共享/图片/定妆_沈念.png",
                                    ),
                                },
                            ],
                            "expressions": [
                                {"emotion": "中性", "path": "出图/共享/图片/定妆_沈念_脸部特写.png", "status": "ready"},
                            ],
                        },
                        "reference_atlas": {
                            "version": 1,
                            "build_tier": "standard_full",
                            "base_views": {
                                "front": {"path": "出图/共享/图片/定妆_沈念.png", "status": "ready"},
                                "three_quarter": _derived_reference(
                                    "出图/共享/图片/定妆_沈念_45度.png",
                                    "turnaround_split",
                                    "出图/共享/图片/定妆_沈念_三视图.png",
                                ),
                                "side": _derived_reference(
                                    "出图/共享/图片/定妆_沈念_侧.png",
                                    "turnaround_split",
                                    "出图/共享/图片/定妆_沈念_三视图.png",
                                ),
                                "back": _derived_reference(
                                    "出图/共享/图片/定妆_沈念_背.png",
                                    "turnaround_split",
                                    "出图/共享/图片/定妆_沈念_三视图.png",
                                ),
                                "half_body": _derived_reference(
                                    "出图/共享/图片/定妆_沈念_半身.png",
                                    "front_crop",
                                    "出图/共享/图片/定妆_沈念.png",
                                ),
                            },
                            "face_anchor_refs": [
                                {
                                    "label": "基础脸锚",
                                    **_derived_reference(
                                        "出图/共享/图片/定妆_沈念_脸部特写.png",
                                        "front_crop",
                                        "出图/共享/图片/定妆_沈念.png",
                                    ),
                                },
                            ],
                            "expression_refs": [
                                {"emotion": "中性", "path": "出图/共享/图片/定妆_沈念_脸部特写.png", "status": "ready"},
                            ],
                            "action_refs": [],
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
    for char in registry.get("characters", []):
        bundle = char.get("asset_bundle") if isinstance(char, dict) else None
        if not isinstance(bundle, dict):
            continue
        manifest_rel = bundle.get("manifest", "")
        if not isinstance(manifest_rel, str) or not manifest_rel:
            continue
        manifest_path = root / manifest_rel
        package_dir = root / str(bundle.get("package_dir") or manifest_path.parent)
        directories = {
            section: f"{bundle.get('package_dir')}/{section}"
            for section in ["reference", "prompts", "lora", "voice", "adapters", "qc"]
        }
        for rel in directories.values():
            (root / rel).mkdir(parents=True, exist_ok=True)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps({
            "kind": "n2d_project_character_asset_bundle",
            "version": 1,
            "character_id": char.get("id"),
            "character_name": char.get("name"),
            "package_dir": str(bundle.get("package_dir") or package_dir),
            "truth_sources": {"identity_registry": "出图/共享/identity_registry.json"},
            "directories": directories,
        }, ensure_ascii=False), encoding="utf-8")
    if make_assets:
        def _reference_paths(reference_group):
            for value in reference_group.values():
                values = value if isinstance(value, list) else [value]
                for item in values:
                    if isinstance(item, str):
                        yield item
                    elif isinstance(item, dict):
                        yield str(item.get("path") or "")

        for char in registry.get("characters", []):
            for form in char.get("forms", []):
                for rel in _reference_paths(form.get("reference_group", {})):
                    if not isinstance(rel, str) or not rel.endswith(".png"):
                        continue
                    path = root / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(_TEST_PNG_BYTES)
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
                "scene_dna": {
                    "belonging_anchor": "破败冷宫寝殿 / 沈念觉醒原点",
                    "landmarks": ["旧床榻", "斑驳铜镜", "残烛"],
                    "spatial_layout": ["床榻画左", "门口画右后", "横向轴线"],
                    "architecture_materials": ["冷青灰剥落宫墙", "旧木门窗", "青石地面"],
                    "color_lighting_weather": ["画左前残烛暖光", "画右后冷月背光"],
                    "resident_assets": ["PROP_01 斑驳铜镜", "旧床榻", "残烛"],
                    "forbidden": ["现代卧室", "豪华新宫殿", "床榻门口左右互换"],
                },
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
        "platform_review": {
            "targets": [{
                "platform": "抖音",
                "region": "CN",
                "language": "zh",
                "policy_profile": "douyin_cn_ai_drama_2026-06-08",
                "profile_checked_at": "2026-06-08",
                "copyright_review": "ready",
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
        "ai_labeling": {
            "applicable": True,
            "explicit_label": {"status": "done", "text": "AI生成", "position": "bottom-right"},
            "implicit_metadata": {"spec": "GB45438-2025", "service_provider_code": "SP-001",
                                  "content_id": "C-2026-001", "applied": True},
            "digital_watermark": {"status": "optional_external", "notes": ""},
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


def test_backend_smoke_gate_default_on_for_paid_distribution(tmp_path, monkeypatch):
    monkeypatch.delenv("N2D_REQUIRE_BACKEND_SMOKE", raising=False)
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    # 默认 publish_candidate：smoke 硬闸保持 opt-in（不打扰 demo/内部）
    _good_compliance(root, status_overrides={"distribution_intent": "publish_candidate"})
    assert gate.backend_smoke_gate_enabled(str(root)) is False
    # 付费投放：自动强制证活性
    _good_compliance(root, status_overrides={"distribution_intent": "paid_distribution"})
    assert gate.backend_smoke_gate_enabled(str(root)) is True


def test_backend_smoke_gate_env_override_wins(tmp_path, monkeypatch):
    root = tmp_path / "制漫剧" / "测试剧2"
    root.mkdir(parents=True)
    _good_compliance(root, status_overrides={"distribution_intent": "paid_distribution"})
    monkeypatch.setenv("N2D_REQUIRE_BACKEND_SMOKE", "0")
    assert gate.backend_smoke_gate_enabled(str(root)) is False


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


def test_compliance_manifest_allows_original_source_and_adaptation_without_evidence(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root, status_overrides={
        "rights.source_text": {"status": "original", "evidence": ""},
        "rights.adaptation": {"status": "original", "evidence": ""},
    })

    gate.check_compliance_manifest(str(root), "第1集", "image")

    assert not any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "合规前置"
        and ("rights.source_text" in f["loc"] or "rights.adaptation" in f["loc"])
        for f in gate.findings
    )


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


def test_compliance_manifest_publish_candidate_release_fields_are_info_at_image(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root, status_overrides={
        "platform_review.targets.0.platform": "YouTube",
        "platform_review.targets.0.region": "US",
        "platform_review.targets.0.language": "en",
        "platform_review.targets.0.requires_localization": True,
        "localization.status": "draft",
        "localization.subtitle_languages": ["zh"],
        "regulatory_filing.pre_broadcast_review": "pending",
        "regulatory_filing.release_filing_no": "TODO: 上线备案号",
    })

    gate.check_compliance_manifest(str(root), "第1集", "image")

    release = [
        f for f in gate.findings
        if f["dim"] == "合规前置"
        and (
            "platform_review" in f["loc"]
            or "localization" in f["loc"]
            or "regulatory_filing" in f["loc"]
        )
    ]
    assert release and all(f["sev"] == gate.INFO for f in release), release
    assert not any(f["sev"] == gate.BLOCK for f in release)


def test_compliance_manifest_paid_distribution_release_fields_block_at_image(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root, status_overrides={
        "distribution_intent": "paid_distribution",
        "platform_review.targets.0.platform": "TODO",
        "platform_review.targets.0.policy_profile": "TODO_profile_2026-06-08",
        "regulatory_filing.pre_broadcast_review": "pending",
        "regulatory_filing.release_filing_no": "TODO: 上线备案号",
    })

    gate.check_compliance_manifest(str(root), "第1集", "image")

    assert any(f["sev"] == gate.BLOCK and "平台审核缺字段：platform" in f["msg"] for f in gate.findings)
    assert any(f["sev"] == gate.BLOCK and "regulatory_filing" in f["loc"] and "pre_broadcast_review" in f["msg"] for f in gate.findings)
    assert any(f["sev"] == gate.BLOCK and "regulatory_filing" in f["loc"] and "release_filing_no" in f["msg"] for f in gate.findings)


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


def test_identity_registry_missing_three_quarter_is_blocked(tmp_path):
    data = _identity_registry()
    form = data["characters"][0]["forms"][0]
    del form["reference_group"]["three_quarter"]
    del form["reference_atlas"]["base_views"]["three_quarter"]
    root = _write_identity_registry(tmp_path, data)

    gate.check_identity_registry(root, require_reference_assets=False)

    assert any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "资产身份注册层"
        and "three_quarter" in f["msg"]
        for f in gate.findings
    )


def test_identity_registry_planned_makeup_reference_is_blocked(tmp_path):
    data = _identity_registry()
    form = data["characters"][0]["forms"][0]
    form["reference_group"]["three_quarter"] = {
        "path": "出图/共享/图片/定妆_沈念_45度.png",
        "status": "planned",
    }
    form["reference_atlas"]["base_views"]["three_quarter"]["status"] = "planned"
    root = _write_identity_registry(tmp_path, data)

    gate.check_identity_registry(root, require_reference_assets=False)

    assert any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "资产身份注册层"
        and "planned" in f["msg"]
        and "不能放行" in f["msg"]
        for f in gate.findings
    )


def test_identity_registry_ready_split_reference_requires_same_source_derivation(tmp_path):
    data = _identity_registry()
    form = data["characters"][0]["forms"][0]
    form["reference_group"]["three_quarter"] = {
        "path": "出图/共享/图片/定妆_沈念_45度.png",
        "status": "ready",
    }
    form["reference_atlas"]["base_views"]["three_quarter"] = {
        "path": "出图/共享/图片/定妆_沈念_45度.png",
        "status": "ready",
    }
    root = _write_identity_registry(tmp_path, data)

    gate.check_identity_registry(root, require_reference_assets=False)

    assert any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "资产身份注册层"
        and "同源母本派生" in f["msg"]
        and "derivation.method" in f["msg"]
        for f in gate.findings
    )


def test_identity_registry_turnaround_cannot_replace_split_makeup_refs(tmp_path):
    data = _identity_registry()
    form = data["characters"][0]["forms"][0]
    for key in ("three_quarter", "side", "back", "half_body"):
        del form["reference_group"][key]
    for key in ("three_quarter", "side", "back", "half_body"):
        del form["reference_atlas"]["base_views"][key]
    root = _write_identity_registry(tmp_path, data)

    gate.check_identity_registry(root, require_reference_assets=False)

    missing = [f for f in gate.findings if f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层"]
    assert any("three_quarter" in f["msg"] for f in missing)
    assert any("side" in f["msg"] for f in missing)
    assert any("back" in f["msg"] for f in missing)
    assert any("half_body_or_full_body" in f["msg"] for f in missing)


def test_identity_registry_missing_expression_reference_is_blocked(tmp_path):
    data = _identity_registry()
    data["characters"][0]["forms"][0]["reference_group"]["face_anchor_refs"] = []
    data["characters"][0]["forms"][0]["reference_atlas"]["face_anchor_refs"] = []
    data["characters"][0]["forms"][0]["reference_group"]["expressions"] = []
    data["characters"][0]["forms"][0]["reference_atlas"]["expression_refs"] = []
    root = _write_identity_registry(tmp_path, data)
    gate.check_identity_registry(root, require_reference_assets=False)
    assert any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "资产身份注册层"
        and "reference_group 至少需要一个同源脸部特写/表情参考" in f["msg"]
        for f in gate.findings
    )


def test_identity_registry_face_anchor_refs_satisfy_baseline_without_expression_library(tmp_path):
    data = _identity_registry()
    form = data["characters"][0]["forms"][0]
    form["reference_group"]["face_anchor_refs"] = [
        {
            "label": "基础脸锚",
            **_derived_reference(
                "出图/共享/图片/定妆_沈念_脸部特写.png",
                "front_crop",
                "出图/共享/图片/定妆_沈念.png",
            ),
        }
    ]
    form["reference_group"]["expressions"] = []
    form["reference_atlas"]["face_anchor_refs"] = [
        {
            "label": "基础脸锚",
            **_derived_reference(
                "出图/共享/图片/定妆_沈念_脸部特写.png",
                "front_crop",
                "出图/共享/图片/定妆_沈念.png",
            ),
        }
    ]
    form["reference_atlas"]["expression_refs"] = []
    root = _write_identity_registry(tmp_path, data)

    gate.check_identity_registry(root, require_reference_assets=False)

    assert not any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "资产身份注册层"
        and "同源脸部特写/表情参考" in f["msg"]
        for f in gate.findings
    )


def test_identity_registry_accepts_controlled_multiref_derivation(tmp_path):
    data = _identity_registry()
    form = data["characters"][0]["forms"][0]
    rg = form["reference_group"]
    atlas = form["reference_atlas"]
    source = "出图/共享/图片/定妆_沈念.png"
    for key, path in {
        "three_quarter": "出图/共享/图片/定妆_沈念_45度.png",
        "side": "出图/共享/图片/定妆_沈念_侧.png",
        "back": "出图/共享/图片/定妆_沈念_背.png",
        "half_body": "出图/共享/图片/定妆_沈念_半身.png",
    }.items():
        rg[key] = _derived_reference(path, "controlled_multiref_generation", source)
        atlas["base_views"][key] = _derived_reference(path, "controlled_multiref_generation", source)
    rg["face_anchor_refs"] = [
        {
            "label": "基础脸锚",
            **_derived_reference(
                "出图/共享/图片/定妆_沈念_脸部特写.png",
                "controlled_multiref_generation",
                source,
            ),
        }
    ]
    atlas["face_anchor_refs"] = [
        {
            "label": "基础脸锚",
            **_derived_reference(
                "出图/共享/图片/定妆_沈念_脸部特写.png",
                "controlled_multiref_generation",
                source,
            ),
        }
    ]
    root = _write_identity_registry(tmp_path, data, make_assets=True)

    gate.check_identity_registry(root, require_reference_assets=True)

    assert not any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "资产身份注册层"
        and "拆分定妆必须是同源母本派生" in f["msg"]
        for f in gate.findings
    )


def test_identity_registry_missing_reference_atlas_is_blocked(tmp_path):
    data = _identity_registry()
    del data["characters"][0]["forms"][0]["reference_atlas"]
    root = _write_identity_registry(tmp_path, data)
    gate.check_identity_registry(root, require_reference_assets=False)
    assert any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "资产身份注册层"
        and "reference_atlas 必须是对象" in f["msg"]
        for f in gate.findings
    )


def test_identity_registry_restricted_partial_uses_partial_refs(tmp_path):
    data = _identity_registry()
    char = data["characters"][0]
    char["id"] = "CHAR_QUEEN"
    char["name"] = "皇后"
    char["scope"] = "长线反派·局部参考"
    char["face_policy"] = "no_full_face"
    form = char["forms"][0]
    form["form"] = "局部参考"
    form["asset_key"] = "皇后_局部参考"
    form["reference_group"] = {
        "front": "",
        "side": "",
        "back": "",
        "outfit": "",
        "turnaround": "",
        "hand": {"path": "出图/共享/图片/定妆_皇后_局部_手部搁茶.png", "status": "ready"},
        "silhouette": {"path": "出图/共享/图片/定妆_皇后_局部_帘后剪影.png", "status": "ready"},
        "expressions": [],
    }
    form["reference_atlas"] = {"build_tier": "restricted_partial"}
    form["drift_forbidden"] = ["no_full_face_ever", "no_clear_facial_features"]
    root = _write_identity_registry(tmp_path, data)

    gate.check_identity_registry(root, require_reference_assets=False)

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "reference_group 缺核心路径" in f["msg"] for f in gate.findings)


def test_identity_registry_missing_character_dna_layer_is_blocked(tmp_path):
    data = _identity_registry()
    del data["characters"][0]["forms"][0]["character_dna"]["hair"]
    root = _write_identity_registry(tmp_path, data)
    gate.check_identity_registry(root, require_reference_assets=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "角色 DNA" and "character_dna.hair" in f["loc"] for f in gate.findings)


def test_identity_registry_incomplete_wardrobe_profile_warns(tmp_path):
    data = _identity_registry()
    data["characters"][0]["forms"][0]["wardrobe_profile"] = {
        "silhouette": "月白交领寝衣，柔软宽袖"
    }
    root = _write_identity_registry(tmp_path, data)
    gate.check_identity_registry(root, require_reference_assets=False)
    assert any(
        f["sev"] == gate.WARN and f["dim"] == "服装契约" and "wardrobe_profile" in f["loc"]
        for f in gate.findings
    )
    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "服装契约" for f in gate.findings)


def test_identity_registry_core_character_missing_asset_bundle_is_blocked(tmp_path):
    data = _identity_registry()
    del data["characters"][0]["asset_bundle"]
    root = _write_identity_registry(tmp_path, data)
    gate.check_identity_registry(root, require_reference_assets=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "角色资产包" for f in gate.findings)


def test_identity_registry_shortline_character_missing_asset_bundle_is_blocked(tmp_path):
    data = _identity_registry()
    char = data["characters"][0]
    char["id"] = "CHAR_XIAOHE"
    char["name"] = "小禾"
    char["scope"] = "第1集功能角色"
    del char["asset_bundle"]
    root = _write_identity_registry(tmp_path, data)
    gate.check_identity_registry(root, require_reference_assets=False)
    assert any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "角色资产包"
        and "所有入镜人物" in f["msg"]
        for f in gate.findings
    )


def test_identity_registry_rejects_cross_character_expression_reference(tmp_path):
    data = _identity_registry()
    data["characters"][0]["forms"][0]["reference_group"]["expressions"] = [
        "出图/共享/图片/定妆_柳娘子_人皮态_脸部特写.png"
    ]
    root = _write_identity_registry(tmp_path, data)
    gate.check_identity_registry(root, require_reference_assets=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "跨角色/形态污染" in f["msg"] for f in gate.findings)


def test_identity_registry_rejects_reference_group_from_other_costume_form(tmp_path):
    data = _identity_registry()
    form = data["characters"][0]["forms"][0]
    form["form"] = "红衣觉醒态"
    form["asset_key"] = "沈念_红衣觉醒态"
    root = _write_identity_registry(tmp_path, data)
    gate.check_identity_registry(root, require_reference_assets=False)
    assert any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "资产身份注册层"
        and "服饰/形态变体必须独立定妆" in f["msg"]
        for f in gate.findings
    )


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


def test_identity_registry_reference_assets_can_be_scoped_to_episode_ids(tmp_path):
    data = _identity_registry()
    future = json.loads(json.dumps(data["characters"][0], ensure_ascii=False))
    future["id"] = "CHAR_99"
    future["name"] = "未来角色"
    future["forms"][0]["reference_group"]["side"] = ""
    future["forms"][0]["reference_group"]["back"] = ""
    data["characters"].append(future)
    root = _write_identity_registry(tmp_path, data, make_assets=True)

    gate.findings.clear()
    gate.check_identity_registry(root, require_reference_assets=True, required_character_ids={"CHAR_SHEN"})

    assert not any(
        f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "缺核心路径" in f["msg"]
        for f in gate.findings
    )
    assert not any(
        f["sev"] == gate.BLOCK and f["dim"] == "资产身份注册层" and "路径不存在" in f["msg"]
        for f in gate.findings
    )


def test_identity_registry_full_contract_passes(tmp_path):
    root = _write_identity_registry(tmp_path, make_assets=True)
    gate.check_identity_registry(root, require_reference_assets=True)
    assert not any(f["dim"] == "资产身份注册层" for f in gate.findings)


def test_episode_has_per_shot_frames_detects_pngs(tmp_path):
    root = _write_identity_registry(tmp_path)
    assert gate._episode_has_per_shot_frames(root, "第1集") is False
    frame = Path(root) / "出图" / "第1集" / "图片" / "镜头01.png"
    frame.parent.mkdir(parents=True, exist_ok=True)
    frame.write_bytes(b"\x89PNG\r\n\x1a\n")
    assert gate._episode_has_per_shot_frames(root, "第1集") is True


def test_image_stage_requires_real_shared_pngs_once_frames_exist(tmp_path):
    """两层出图不变量：本集出了逐镜帧后，被引用共享 PNG 必须真在磁盘（不只声明 ready）；
    共享库自举那一次（还没逐镜帧）保持只验声明、不卡死。复刻 gate.py image 块的 _require_real_refs 组合。"""
    root = _write_identity_registry(tmp_path)  # 注册表声明齐全，但共享 PNG 不在磁盘
    ep = "第1集"
    ref_chars = {"CHAR_SHEN"}

    def missing_png_blocks(stage):
        gate.findings.clear()
        require_real = (stage == "image") and gate._episode_has_per_shot_frames(root, ep)
        if require_real:
            gate.check_identity_registry(root, require_reference_assets=True, required_character_ids=ref_chars)
        else:
            gate.check_identity_registry(root, require_reference_assets=False)
        return any(f["sev"] == gate.BLOCK and "路径不存在" in f["msg"] for f in gate.findings)

    # 自举：还没逐镜帧 → 缺共享 PNG 也不卡（保留快速首图/共享库生成）
    assert missing_png_blocks("image") is False
    assert missing_png_blocks("image_preflight") is False
    # 出图后有了逐镜帧 → 缺被引用的共享 PNG 必须 BLOCK（堵"clip 前共享图没真生成"）
    frame = Path(root) / "出图" / ep / "图片" / "镜头01.png"
    frame.parent.mkdir(parents=True, exist_ok=True)
    frame.write_bytes(b"\x89PNG\r\n\x1a\n")
    assert missing_png_blocks("image") is True
    assert missing_png_blocks("image_preflight") is False  # 生成前仍只验声明


def test_image_dispatch_wires_real_ref_check_behind_frame_existence():
    """源码锁：gate.py image 块必须用 `stage=="image" and _episode_has_per_shot_frames` 把
    require_reference_assets 升到 True——防有人改成恒 True（卡死共享库自举）或恒 False（还原声明漏洞）。"""
    src = Path(__file__).with_name("gate.py").read_text(encoding="utf-8")
    assert "_episode_has_per_shot_frames" in src
    assert '_require_real_refs = (stage == "image") and _episode_has_per_shot_frames' in src
    assert "require_reference_assets=True, required_character_ids=_ref_chars" in src


def test_identity_registry_production_core_character_requires_performance_signature(tmp_path):
    root = Path(_write_identity_registry(tmp_path, make_assets=True))
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")

    gate.check_identity_registry(str(root), require_reference_assets=True)

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "角色表演一致性" for f in gate.findings)


def test_identity_registry_production_performance_signature_passes(tmp_path):
    data = _identity_registry()
    data["characters"][0]["forms"][0]["performance_signature"] = {
        "micro_expressions": "先压眼再冷笑",
        "habitual_gestures": "指尖轻敲杯沿",
        "posture": "肩背挺直但步幅克制",
        "speech_rhythm": "短句停顿明确",
        "eye_reaction": "先避开后直视",
    }
    root = Path(_write_identity_registry(tmp_path, data, make_assets=True))
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")

    gate.check_identity_registry(str(root), require_reference_assets=True)

    assert not any(f["dim"] == "角色表演一致性" for f in gate.findings)


def test_identity_registry_production_action_lead_requires_signature_equipment(tmp_path):
    data = _identity_registry()
    form = data["characters"][0]["forms"][0]
    form["combat_role"] = True
    form["performance_signature"] = {
        "micro_expressions": "先压眼再冷笑",
        "habitual_gestures": "左手按住剑柄",
        "posture": "重心压低",
        "speech_rhythm": "短句停顿明确",
        "eye_reaction": "先看对手手腕再对视",
    }
    root = Path(_write_identity_registry(tmp_path, data, make_assets=True))
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")

    gate.check_identity_registry(str(root), require_reference_assets=True)

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "主角装备库" for f in gate.findings)


def test_identity_registry_production_signature_equipment_passes(tmp_path):
    data = _identity_registry()
    form = data["characters"][0]["forms"][0]
    form["combat_role"] = True
    form["signature_equipment"] = ["WEAPON_01"]
    form["performance_signature"] = {
        "micro_expressions": "先压眼再冷笑",
        "habitual_gestures": "左手按住剑柄",
        "posture": "重心压低",
        "speech_rhythm": "短句停顿明确",
        "eye_reaction": "先看对手手腕再对视",
    }
    root = Path(_write_identity_registry(tmp_path, data, make_assets=True))
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")

    gate.check_identity_registry(str(root), require_reference_assets=True)

    assert not any(f["dim"] == "主角装备库" for f in gate.findings)


def test_identity_registry_signature_equipment_accepts_chinese_asset_id(tmp_path):
    data = _identity_registry()
    form = data["characters"][0]["forms"][0]
    form["combat_role"] = True
    form["signature_equipment"] = ["PROP_镇魔司黑衣赤纹"]
    form["performance_signature"] = {
        "micro_expressions": "先压眼再冷笑",
        "habitual_gestures": "左手按住衣襟纹样",
        "posture": "重心压低",
        "speech_rhythm": "短句停顿明确",
        "eye_reaction": "先看对手手腕再对视",
    }
    root = Path(_write_identity_registry(tmp_path, data, make_assets=True))
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")

    gate.check_identity_registry(str(root), require_reference_assets=True)

    assert not any(f["dim"] == "主角装备库" for f in gate.findings)


def test_asset_id_re_extracts_chinese_registry_ids():
    text = "资产引用注册层：PROP_镇魔司黑衣赤纹、LOC_黑风林；MOUNT_GROUP_飞鹰门马队。"

    assert set(gate.ASSET_ID_RE.findall(text)) == {
        "PROP_镇魔司黑衣赤纹",
        "LOC_黑风林",
        "MOUNT_GROUP_飞鹰门马队",
    }


def test_asset_reference_registry_missing_is_blocked(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    gate.check_asset_reference_registry(str(root), require_reference_assets=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产引用注册层" and "asset_registry.json" in f["msg"] for f in gate.findings)


def test_food_bowl_is_not_weapon_like_asset():
    asset = {
        "id": "PROP_FOOD_BOWL",
        "type": "prop",
        "name": "PROP FOOD BOWL",
        "constraints": {"structure": "plain food bowl"},
    }

    assert gate._is_weapon_like_asset(asset) is False
    assert gate._is_weapon_like_asset({"id": "PROP_SHORT_BLADE", "type": "prop", "name": "short blade"}) is True


def test_vfx_only_effect_can_opt_out_of_weapon_like_heuristic():
    asset = {
        "id": "VFX_妖气",
        "type": "vfx",
        "name": "妖气绕刀",
        "is_entity_weapon": False,
        "weapon_like_role": "vfx_only",
        "constraints": {"visual_contract": "妖气绕刀，不是实体武器或本命法宝。"},
    }

    assert gate._is_weapon_like_asset(asset) is False


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


def test_asset_reference_registry_requires_bottle_must_not_have_spout(tmp_path):
    data = _asset_registry()
    prop = data["assets"][1]
    prop["name"] = "毒酒白瓷瓶"
    prop["constraints"] = {"structure": "短颈圆口白瓷瓶，唯一一只，无双口"}
    prop["drift_forbidden"] = ["bottle_shape", "era_style"]
    root = _write_asset_registry(tmp_path, data)
    gate.check_asset_reference_registry(root, require_reference_assets=False)
    assert any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "资产引用注册层"
        and "must_not_have" in f["msg"]
        for f in gate.findings
    )


def test_asset_reference_registry_accepts_bottle_must_not_have_spout(tmp_path):
    data = _asset_registry()
    prop = data["assets"][1]
    prop["name"] = "毒酒白瓷瓶"
    prop["constraints"] = {
        "structure": "短颈圆口白瓷瓶，唯一一只，无双口",
        "must_not_have": ["壶嘴", "侧嘴", "喷口"],
    }
    prop["drift_forbidden"] = ["bottle_shape", "era_style"]
    root = _write_asset_registry(tmp_path, data)
    gate.check_asset_reference_registry(root, require_reference_assets=False)
    assert not any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "资产引用注册层"
        and "must_not_have" in f["msg"]
        for f in gate.findings
    )


def test_asset_reference_registry_scene_missing_scene_dna_is_blocked(tmp_path):
    data = _asset_registry()
    del data["assets"][0]["scene_dna"]
    root = _write_asset_registry(tmp_path, data)
    gate.check_asset_reference_registry(root, require_reference_assets=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "场景 DNA" for f in gate.findings)


def test_asset_reference_registry_accepts_top_level_lighting_signature(tmp_path):
    data = _asset_registry()
    data["assets"][0]["constraints"].pop("lighting_signature", None)
    data["assets"][0]["lighting_signature"] = {
        "color_temperature": "4200K cold moon",
        "key_light": "soft side moon scatter",
    }
    root = _write_asset_registry(tmp_path, data)

    gate.findings.clear()
    gate.check_asset_reference_registry(root, require_reference_assets=False)

    assert not any(
        f["dim"] == "资产引用注册层" and "lighting_signature" in f["msg"]
        for f in gate.findings
    )


def test_asset_reference_registry_scene_dna_missing_layer_is_blocked(tmp_path):
    data = _asset_registry()
    del data["assets"][0]["scene_dna"]["landmarks"]
    root = _write_asset_registry(tmp_path, data)
    gate.check_asset_reference_registry(root, require_reference_assets=False)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "场景 DNA" and "scene_dna.landmarks" in f["loc"] for f in gate.findings)


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


def test_asset_reference_registry_reference_assets_can_be_scoped_to_episode_ids(tmp_path):
    data = _asset_registry()
    future = json.loads(json.dumps(data["assets"][0], ensure_ascii=False))
    future["id"] = "LOC_99"
    future["name"] = "未来场景"
    future["reference_group"]["primary"] = "出图/共享/图片/定妆_未来场景.png"
    data["assets"].append(future)
    root = _write_asset_registry(tmp_path, data, make_assets=True)

    gate.findings.clear()
    gate.check_asset_reference_registry(root, require_reference_assets=True, required_asset_ids={"LOC_01", "PROP_01"})

    assert not any(
        f["sev"] == gate.BLOCK and f["dim"] == "资产引用注册层" and "定妆_未来场景" in f["loc"]
        for f in gate.findings
    )
    assert not any(
        f["sev"] == gate.BLOCK and f["dim"] == "资产引用注册层" and "路径不存在" in f["msg"]
        for f in gate.findings
    )


def test_asset_reference_registry_full_contract_passes(tmp_path):
    root = _write_asset_registry(tmp_path, make_assets=True)
    gate.check_asset_reference_registry(root, require_reference_assets=True)
    assert not any(f["dim"] == "资产引用注册层" for f in gate.findings)


def test_asset_reference_registry_weapon_requires_weapon_profile(tmp_path):
    data = _asset_registry()
    data["assets"].append({
        "id": "WEAPON_01",
        "type": "weapon",
        "name": "霜纹长剑",
        "scope": "沈念第3集起主武器",
        "reference_group": {"primary": "出图/共享/图片/定妆_霜纹长剑.png"},
        "constraints": {"structure": "一柄一刃，直剑，银白剑身，青色剑穗"},
        "drift_forbidden": ["blade_shape", "hilt", "palette"],
    })
    root = _write_asset_registry(tmp_path, data)

    gate.check_asset_reference_registry(root, require_reference_assets=False)

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "主角装备库" and "weapon_profile" in f["loc"] for f in gate.findings)


def test_asset_reference_registry_weapon_profile_passes(tmp_path):
    data = _asset_registry()
    data["assets"].append({
        "id": "WEAPON_01",
        "type": "weapon",
        "name": "霜纹长剑",
        "scope": "沈念第3集起主武器",
        "owner": "CHAR_SHEN",
        "reference_group": {
            "primary": "出图/共享/图片/定妆_霜纹长剑.png",
            "scale_reference": "出图/共享/图片/定妆_霜纹长剑_握持比例.png",
        },
        "weapon_profile": {
            "design_intent": "清冷大气、女性主角本命剑，线条利落不花哨",
            "silhouette": "直剑，窄长银白剑身，短护手，青色剑穗",
            "scale": "全长约角色肩到膝，握柄一手半",
            "material": "冷银金属剑身，玉白护手，青丝剑穗",
            "palette": {"blade": "#D8E3E7", "hilt": "#E8EFEF", "accent": "#5BAFA8"},
            "ornament_motif": "细霜纹沿剑脊，不出现龙纹/火焰纹",
            "carry_modes": ["手持", "背负", "悬浮御剑"],
            "combat_usage": "快刺、横斩、御剑飞行时剑身水平承重",
            "vfx_signature": "青白冷光细线拖尾，短拖尾不爆炸",
            "forbidden_drift": ["宽刃大刀", "金色剑身", "双刃分叉", "多把复制"],
        },
        "constraints": {"structure": "一柄一刃，直剑，银白剑身，青色剑穗"},
        "drift_forbidden": ["blade_shape", "hilt", "palette"],
    })
    root = _write_asset_registry(tmp_path, data)

    gate.check_asset_reference_registry(root, require_reference_assets=False)

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "主角装备库" for f in gate.findings)


def test_asset_reference_registry_production_core_loc_requires_spatial_rules(tmp_path):
    root = Path(_write_asset_registry(tmp_path, make_assets=True))
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")

    gate.check_asset_reference_registry(str(root), require_reference_assets=True)

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "空间/场面调度一致性" for f in gate.findings)


def test_asset_reference_registry_production_core_loc_spatial_rules_pass(tmp_path):
    data = _asset_registry()
    data["assets"][0]["floor_plan"] = "scene_floorplan/LOC_01.png"
    data["assets"][0]["doors_windows"] = "门在画右后，窗在画左后"
    data["assets"][0]["axis_rules"] = "床榻到门口横轴，正反打不越轴"
    data["assets"][0]["screen_direction_rules"] = "沈念默认画左，柳娘子默认画右"
    root = Path(_write_asset_registry(tmp_path, data, make_assets=True))
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")

    gate.check_asset_reference_registry(str(root), require_reference_assets=True)

    assert not any(f["dim"] == "空间/场面调度一致性" for f in gate.findings)


def test_outfit_asset_missing_outfit_profile_warns(tmp_path):
    data = _asset_registry()
    data["assets"].append({
        "id": "OUTFIT_01",
        "type": "outfit",
        "name": "玄青窄袖官袍",
        "scope": "第3集起复用",
        "reference_group": {"primary": "出图/共享/图片/定妆_玄青窄袖官袍.png"},
        "constraints": {"structure": "交领+窄袖+暗银腰封+玄青主色"},
        "drift_forbidden": ["silhouette", "collar", "sleeve", "palette"],
    })
    root = _write_asset_registry(tmp_path, data)
    gate.check_asset_reference_registry(root, require_reference_assets=False)
    assert any(
        f["sev"] == gate.WARN and f["dim"] == "服装契约" and "outfit_profile" in f["loc"]
        for f in gate.findings
    )


def test_identity_adapter_matrix_missing_is_blocked(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    gate.check_identity_adapter_matrix(str(root))
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "资产身份闭环" and "identity_adapter_matrix.json" in f["msg"] for f in gate.findings)


def test_identity_adapter_matrix_minimal_contract_passes(tmp_path):
    import json
    from identity import registry_anchor_fingerprint

    root = Path(_write_identity_registry(tmp_path))
    registry = json.loads((root / "出图" / "common" / "identity_registry.json").read_text(encoding="utf-8"))
    anchor_fingerprint = registry_anchor_fingerprint(registry)
    data_dir = root / "生产数据"
    data_dir.mkdir(parents=True)
    (data_dir / "identity_adapter_matrix.json").write_text(
        json.dumps({
            "kind": "n2d_identity_adapter_matrix",
            "version": 1,
            "summary": {"anchor_fingerprint": anchor_fingerprint},
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
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "契约继承" and "visual_contract 种子块" in f["msg"] for f in gate.findings)


def test_storyboard_visual_contract_missing_field_is_blocked(tmp_path):
    # 有 visual_contract 但缺「景别阶梯」
    root = _write_storyboard(tmp_path, {"色调基线": "冷青", "场景光位锚": {}, "场景轴线视线": {}, "角色状态演进": {}})
    gate.check_storyboard_visual_contract(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "契约继承" and "景别阶梯" in f["msg"] for f in gate.findings)


def test_storyboard_full_visual_contract_passes(tmp_path):
    root = _write_storyboard(tmp_path, {"色调基线": "x", "场景光位锚": {}, "场景轴线视线": {}, "角色状态演进": {}, "景别阶梯": "y"})
    gate.check_storyboard_visual_contract(root, "第1集")
    assert not any(f["dim"] == "契约继承" for f in gate.findings)


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


def test_storyboard_style_contract_requires_style_anchor(tmp_path):
    gate.findings.clear()
    root = _write_storyboard_with_contracts(
        tmp_path,
        None,
        {"风格名": "国漫写实", "视觉基调": "东方幻想", "镜头与构图": "中景到特写", "光色策略": "青金对比", "运动边界": "慢推/固定", "风格禁忌": ["照片感"]},
    )
    gate.check_storyboard_style_contract(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "基础视觉风格契约" and "style_anchor" in f["msg"] for f in gate.findings)


def test_storyboard_style_contract_with_style_anchor_passes(tmp_path):
    gate.findings.clear()
    root = _write_storyboard_with_contracts(
        tmp_path,
        None,
        {"风格名": "国漫写实", "视觉基调": "东方幻想", "镜头与构图": "中景到特写", "光色策略": "青金对比", "运动边界": "慢推/固定", "风格禁忌": ["照片感"], "style_anchor": ["出图/共享/图片/风格锚_国漫写实.png"]},
    )
    gate.check_storyboard_style_contract(root, "第1集")
    assert not any(f["dim"] == "基础视觉风格契约" for f in gate.findings)


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


def test_storyboard_transmigration_premise_does_not_require_realm_portal_template(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [{
            "id": "EP01_CLIP01",
            "label": "尸场醒来",
            "scene": "姜月初在死人堆里惊醒，荒野尸骸战场一片冷雾。",
            "audience_effect": "静音也能读懂她刚穿越就落入死局，产生她怎么活的第一问题。",
            "large_scene_contract": {"establishing_progression": ["尸堆惊醒锁落点"]},
        }],
    )
    gate.check_storyboard_special_templates(root, "第1集")
    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "专项镜头模板" for f in gate.findings)


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


def test_storyboard_system_panel_contract_passes(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [{
            "id": "EP01_CLIP08",
            "label": "系统面板与反噬规则",
            "template": "system_panel",
            "template_contract": {
                "template_id": "system_panel",
                "beats": ["空光幕浮现", "后期 overlay 数值", "反噬规则落下"],
                "blocking": "沈念半侧脸在画右，空光幕居中偏左。",
                "camera_rule": "面板正对屏幕，内部留空，不让 AI 烤文字。",
                "continuity_must": "冷蓝半透明底框稳定；左腕妖纹微亮不消失。",
                "negative": "面板内不出现任何可读文字、数字、汉字或等级数值。",
                "motif_id": "MOTIF_系统面板",
                "vfx_asset": "VFX_系统面板",
                "text_layer": "overlay",
                "growth_ref": {"at_clip": "EP01_CLIP08", "level": 2, "panel_tier": "first_devour_reward"},
                "panel_tier": "first_devour_reward",
            },
        }],
    )
    gate.check_storyboard_special_templates(root, "第1集")
    assert not any(f["dim"] == "专项镜头模板" for f in gate.findings)


def test_storyboard_system_panel_missing_overlay_fields_is_blocked(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [{
            "id": "EP01_CLIP08",
            "label": "系统面板",
            "template": "system_panel",
            "template_contract": {
                "template_id": "system_panel",
                "beats": ["空光幕浮现"],
                "blocking": "沈念画右，空光幕画左。",
                "camera_rule": "面板正对屏幕。",
                "continuity_must": "底框稳定。",
                "negative": "不要文字数字。",
                "motif_id": "MOTIF_系统面板",
                "vfx_asset": "VFX_系统面板",
                "growth_ref": {"at_clip": "EP01_CLIP08", "level": 2},
                "panel_tier": "first_devour_reward",
            },
        }],
    )
    gate.check_storyboard_special_templates(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "专项镜头模板" and "text_layer" in f["msg"] for f in gate.findings)


def test_character_names_in_refs_dedupes_forms_and_ignores_props_vfx():
    refs = """
    - `出图/共享/图片/定妆_沈念_常态.png`
    - `出图/共享/图片/定妆_沈念_常态_45度.png`
    - `出图/共享/图片/定妆_沈念_常态_半身.png`
    - `出图/共享/图片/定妆_沈念_常态_脸部特写.png`
    - `出图/共享/图片/定妆_斑驳铜镜.png`
    - `出图/共享/图片/定妆_VFX_万妖血脉.png`
    - 生成方式=以 `定妆_<角色>` 做 image2image
    """
    assert gate._character_names_in_refs(refs) == {"沈念"}


def test_storyboard_fight_template_requires_action_choreography_fields(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [{
            "id": "EP01_CLIP04",
            "label": "剑掌交锋",
            "template": "fight_exchange",
            "template_contract": {
                "template_id": "fight_exchange",
                "beats": ["起手", "出剑", "命中", "收势"],
                "blocking": "沈念画左前出掌，追兵画右后举剑格挡",
                "camera_rule": "中景起手接命中特写，不越轴",
                "continuity_must": ["沈念始终画左", "剑光颜色不变"],
                "negative": ["不要多人混战", "不要新增连击"],
                "attack_path": "左下到右上",
                "impact_frame": "掌风与剑刃相撞",
                "action_scope": "一招一击",
                "spatial_path": "画左前景到画右中景",
                "readability_beats": ["命中帧停半拍"],
                "force_direction": "沈念掌风推向画右",
                "recovery_beat": "追兵后退半步",
            },
        }],
    )

    gate.check_storyboard_special_templates(root, "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "专项镜头模板" and "speed_curve" in f["msg"] for f in gate.findings)


def test_storyboard_flight_template_full_action_contract_passes(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [{
            "id": "EP01_CLIP05",
            "label": "腾云驾雾",
            "template": "flight",
            "template_contract": {
                "template_id": "flight",
                "beats": ["入云", "巡航", "穿云", "抵达"],
                "blocking": "沈念立于祥云中央，山河在后景向画左后掠",
                "camera_rule": "侧向跟飞，不环绕翻滚",
                "continuity_must": ["祥云形态不变", "沈念姿态不变", "飞行方向左→右"],
                "negative": ["不要人物变形", "不要云团换形状"],
                "pose_lock": "负手立云，身体只小幅前倾",
                "background_motion": "云层和山河向后高速流动",
                "altitude_path": "由云层上方穿入云缝再升出",
                "speed_curve": "巡航匀速→穿云加速→抵达减速",
                "flight_path": "画左入画，沿云海弧线到画右上",
                "altitude_curve": "高→低穿云→高",
                "camera_path": "侧跟飞并轻微下压",
                "spatial_path": "祥云沿画面左下到右上的弧线穿越云海",
                "parallax_layers": ["前景云雾快", "远山慢"],
                "mount_or_cloud_lock": "脚下祥云颜色/形态/大小锁定",
                "readability_beats": ["穿云前给半拍预备", "出云时定住方向"],
                "degrade_plan": "拆成起飞/巡航/穿云/抵达四镜，锁姿态动背景",
                "keyframe_plan": {"start": "入云", "intent_mid": "穿云前", "impact_or_apex": "出云峰值", "end": "抵达"},
                "post_cue_points": [{"cue": "wind_whoosh", "when": "入云"}, {"cue": "parallax_swell", "when": "穿云"}],
                "physics_guard": {"subject_identity": "脸和衣服不漂", "axis_or_path": "画左到画右上", "contact_or_vfx_shape": "祥云不变", "no_extra_motion": "不新增翻滚"},
            },
        }],
    )

    gate.check_storyboard_special_templates(root, "第1集")

    assert not any(f["dim"] == "专项镜头模板" for f in gate.findings)


def test_storyboard_new_scene_templates_full_contracts_pass(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [
            {
                "id": "EP01_CLIP08",
                "label": "公堂掉马",
                "template": "reveal_reaction_chain",
                "template_contract": {
                    "template_id": "reveal_reaction_chain",
                    "beats": ["血书入画", "身份揭穿", "众人反应", "沈念改称谓"],
                    "blocking": "血书在前景桌面，沈念画左，皇叔画右后，裁决者居中后景",
                    "camera_rule": "证物特写接沈念 CU，再切皇叔反应，不越轴",
                    "continuity_must": ["血书位置不变", "沈念始终画左", "皇叔衣冠不变"],
                    "negative": ["不要新增证物", "不要让围观者抢焦点", "不要跳过反应链"],
                    "reveal_object": "带旧印的血书",
                    "knowledge_order": ["沈念已知", "皇叔假装不知道", "裁决者刚知道"],
                    "reaction_beats": ["皇叔否认", "裁决者低头看印", "沈念改称皇叔为罪臣"],
                    "cut_point": "裁决者抬头问最后一个名字前硬断",
                },
            },
            {
                "id": "EP01_CLIP09",
                "label": "当众对质",
                "template": "public_confrontation",
                "template_contract": {
                    "template_id": "public_confrontation",
                    "beats": ["沈念递证", "皇叔反扑", "证人出列", "围观倒戈"],
                    "blocking": "沈念画左前，皇叔画右前，证人从后景中线出列",
                    "camera_rule": "中景建立公堂层级，证据特写后正反打",
                    "continuity_must": ["裁决者居中后景", "围观者虚焦", "令牌始终在桌面"],
                    "negative": ["不要让背景群像清脸", "不要交换左右站位", "不要凭空多出证人"],
                    "stakes": "输者被当堂定罪并失去兵权",
                    "evidence_ladder": ["令牌", "血书", "证人口供"],
                    "power_shift": "皇叔从质问者变成被质问者",
                    "crowd_reaction_order": ["裁决者", "证人", "群臣"],
                },
            },
            {
                "id": "EP01_CLIP10",
                "label": "决裂救场",
                "template": "relationship_turn",
                "template_contract": {
                    "template_id": "relationship_turn",
                    "beats": ["王敦伸手", "沈念后退", "箭来时王敦挡下", "沈念改口"],
                    "blocking": "沈念画左前，王敦画右前，两人间隔半步，箭从右后入画",
                    "camera_rule": "MCU 正反打，挡箭只给肩部与眼神，不做复杂全身接触",
                    "continuity_must": ["沈念泪痕不回退", "王敦衣袖破损持续", "两人左右关系不换"],
                    "negative": ["不要突然拥抱", "不要换脸", "不要把决裂演成甜蜜和解"],
                    "relationship_state_before": "误会爆发后互不信任",
                    "turning_action": "王敦挡箭但沈念仍收回信物",
                    "subtext": "嘴上割席，动作仍承认在意",
                    "relationship_state_after": "正式决裂但留下互相保护的裂缝",
                },
            },
        ],
    )
    gate.check_storyboard_special_templates(root, "第1集")
    assert not any(f["dim"] == "专项镜头模板" for f in gate.findings)


def test_storyboard_reveal_template_missing_reaction_beats_is_blocked(tmp_path):
    root = _write_storyboard_with_clips(
        tmp_path,
        [{
            "id": "EP01_CLIP08",
            "label": "掉马",
            "template": "reveal_reaction_chain",
            "template_contract": {
                "template_id": "reveal_reaction_chain",
                "beats": ["证物入画", "身份揭穿"],
                "blocking": "沈念画左，皇叔画右",
                "camera_rule": "证物特写接反打",
                "continuity_must": ["证物不变"],
                "negative": ["不要跳轴"],
                "reveal_object": "血书",
                "knowledge_order": ["沈念已知", "皇叔刚知道"],
                "cut_point": "皇叔开口前断",
            },
        }],
    )
    gate.check_storyboard_special_templates(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "专项镜头模板" and "reaction_beats" in f["msg"] for f in gate.findings)


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
    # 制作模式=原生音画：native_speech 是有意路由，不再强制 no_native_speech。
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 制作模式: 原生音画\n- 视频原生音轨: 保留原片音轨\n", encoding="utf-8")
    overview = "本集原生音画 opt-in 清单：native_speech 有意生成。"

    gate.check_native_audio_opt_in_overview(str(root), "第1集", overview, "loc")

    assert not any(f["sev"] == gate.BLOCK for f in gate.findings)


def test_voice_first_mode_still_blocks_native_speech_without_disclaimer(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 制作模式: 配音先行\n- 视频原生音轨: 保留原片音轨\n", encoding="utf-8")
    overview = "本集原生音画 opt-in 清单：保留环境声。"  # 缺 no_native_speech 声明

    gate.check_native_audio_opt_in_overview(str(root), "第1集", overview, "loc")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画" for f in gate.findings)


def test_native_av_default_uses_contract_default(tmp_path):
    root = tmp_path / "制漫剧" / "默认模式"
    root.mkdir(parents=True)

    assert gate.is_native_av_production(str(root)) is False


def _write_script_contract_case(root: Path, *, prompt_missing_field: bool = False) -> None:
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    prompt_dir = root / "出图" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    dramatic = "只写剧情描述" if prompt_missing_field else "用可视证据提出观众问题"
    prompt = (
        "# 第1集 出图\n"
        "留存承诺：干净皂靴是破绽；当众揭穿。\n"
        "观众问题：凶手是谁；下一镜给出证据。\n"
        "## Clip 01（Clip_01）\n"
        f"剧本可看性合同：戏剧功能={dramatic}；观众效果=立刻担心主角并期待反击。\n"
    )
    prompt_path = prompt_dir / "01_分镜出图.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    contract = {
        "kind": "n2d_script_quality_contract",
        "version": 1,
        "episode": "第1集",
        "status": "pass",
        "content_hash": "stable-content-hash",
        "required_consumption_fields": [
            "core_attraction",
            "first_3s_visual_hook",
            "retention_promise_ledger",
            "clip_dramatic_function",
            "audience_question_ledger",
            "performance_cues",
        ],
        "signable_fields": {
            "core_attraction": {"category": "强反转", "why_watch": "证据反杀"},
            "first_3s_visual_hook": {"visual_hook": "雨夜血迹"},
            "retention_promise_ledger": [{"promise": "干净皂靴是破绽", "payoff": "当众揭穿"}],
            "audience_question_ledger": {
                "questions": [{"question": "凶手是谁", "expected_next_handling": "下一镜给出证据"}]
            },
            "performance_cues": [],
            "clip_dramatic_functions": [
                {
                    "clip_id": "Clip_01",
                    "dramatic_function": "用可视证据提出观众问题",
                    "audience_effect": "立刻担心主角并期待反击",
                }
            ],
        },
        "findings": [],
        "summary": {"status": "pass", "blocks": 0, "warnings": 0, "clips": 1},
    }
    contract_path = prod / "script_quality_contract_第1集.json"
    contract_path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
    receipt = {
        "kind": "n2d_script_contract_application",
        "episode": "第1集",
        "accepted": True,
        "reviewer": "test",
        "contract_path": "生产数据/script_quality_contract_第1集.json",
        "contract_content_hash": "stable-content-hash",
        "contract_file_sha256": "stale-file-sha-kept-for-audit-only",
        "scopes": [
            {
                "scope": "出图",
                "prompt_path": "出图/第1集/prompt/01_分镜出图.md",
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "contract_content_hash": "stable-content-hash",
                "contract_file_sha256": "stale-file-sha-kept-for-audit-only",
                "consumed_fields": contract["required_consumption_fields"],
                "applied_clip_ids": ["Clip_01"],
            }
        ],
    }
    (prod / "script_contract_applied_第1集.json").write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")


def test_script_contract_consumption_uses_content_hash_not_file_sha(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "合同"
    _write_script_contract_case(root)

    gate.check_script_contract_consumption(str(root), "第1集", ("出图",))

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "剧本可看性消费" for f in gate.findings)


def test_script_contract_consumption_blocks_self_signed_prompt_without_fields(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "合同缺字段"
    _write_script_contract_case(root, prompt_missing_field=True)

    gate.check_script_contract_consumption(str(root), "第1集", ("出图",))

    assert any(
        f["sev"] == gate.BLOCK and f["dim"] == "剧本可看性消费" and "逐 Clip 合同验证" in f["msg"]
        for f in gate.findings
    )


def test_native_voice_identity_missing_blocks_native_av_review(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("- 制作模式: 原生音画\n", encoding="utf-8")

    gate.check_native_voice_identity(str(root), "第1集", "review")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画声线一致性" for f in gate.findings)


def test_native_voice_identity_degraded_backend_blocks_then_warns_with_escape(tmp_path, monkeypatch):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    audio = root / "出视频" / "第1集" / "audio"
    prod = root / "生产数据"
    audio.mkdir(parents=True)
    prod.mkdir(parents=True)
    (root / "_设置.md").write_text("- 制作模式: 原生音画\n", encoding="utf-8")
    (audio / "Clip_01_speech.wav").write_bytes(b"RIFF")
    (audio / "Clip_02_speech.wav").write_bytes(b"RIFF")
    (prod / "native_voice_identity_第1集.json").write_text(json.dumps({
        "kind": gate.NATIVE_VOICE_IDENTITY_SEGMENTS_KIND,
        "segments": [
            {"character_id": "CHAR_01", "speaker_key": "NATIVE", "wav": "出视频/第1集/audio/Clip_01_speech.wav"},
            {"character_id": "CHAR_01", "speaker_key": "NATIVE", "wav": "出视频/第1集/audio/Clip_02_speech.wav"},
        ],
    }, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(gate.vprint, "load_speaker_encoder", lambda: (None, None))

    gate.check_native_voice_identity(str(root), "第1集", "review")
    assert any(f["sev"] == gate.BLOCK and "声纹后端不可用" in f["msg"] for f in gate.findings)

    gate.findings.clear()
    monkeypatch.setenv("N2D_ALLOW_DEGRADED_QC", "1")
    gate.check_native_voice_identity(str(root), "第1集", "review")
    assert any(f["sev"] == gate.WARN and "N2D_ALLOW_DEGRADED_QC" in f["msg"] for f in gate.findings)


# ── 现实覆盖闸：场景验证器适用却休眠 → 交付边界阻断（治「跑了却没执行」）──────────
def _coverage_project(tmp_path):
    root = tmp_path / "剧"
    d = root / "出图" / "共享"
    d.mkdir(parents=True)
    prod = root / "生产数据"
    prod.mkdir()
    import json as _j
    (d / "asset_registry.json").write_text(_j.dumps({"assets": [
        {"id": "LOC_A", "scene_dna": {"resident_assets": ["残匾"]},
         "constraints": {"doors_windows": "门在画左"}}]}, ensure_ascii=False), encoding="utf-8")
    # 预置 dormant sidecars（detector_ran=false / embedding=None），避免 autorun 子进程
    (prod / "resident_presence_第1集.json").write_text('{"detector_ran": false}', encoding="utf-8")
    (prod / "scene_geometry_第1集.json").write_text('{"detector_ran": false}', encoding="utf-8")
    (prod / "scene_embed_第1集.json").write_text('{"probes": [{"embedding": null}]}', encoding="utf-8")
    return str(root)


def test_reality_coverage_blocks_dormant_at_delivery(tmp_path):
    root = _coverage_project(tmp_path)
    gate.findings.clear()
    gate.check_consistency_reality_coverage(root, "第1集", "review")
    cov = [f for f in gate.findings if f["dim"] == "现实覆盖"]
    assert any(f["sev"] == gate.BLOCK for f in cov)          # 适用×休眠 → BLOCK
    assert any(f["sev"] == gate.INFO for f in cov)           # 覆盖率摘要 INFO


def test_reality_coverage_escape_counts_waiver(tmp_path, monkeypatch):
    root = _coverage_project(tmp_path)
    gate.findings.clear()
    gate._DEGRADED_QC_WAIVERS.clear()
    monkeypatch.setenv("N2D_ALLOW_DEGRADED_QC", "1")
    gate.check_consistency_reality_coverage(root, "第1集", "review")
    cov = [f for f in gate.findings if f["dim"] == "现实覆盖"]
    assert not any(f["sev"] == gate.BLOCK for f in cov)      # 逃生口 → 不 block
    assert any(f["sev"] == gate.WARN for f in cov)
    assert len(gate._DEGRADED_QC_WAIVERS) >= 1               # 计债（进 rollup）


def test_reality_coverage_image_stage_no_block(tmp_path):
    root = _coverage_project(tmp_path)
    gate.findings.clear()
    gate.check_consistency_reality_coverage(root, "第1集", "image")
    assert not any(f["dim"] == "现实覆盖" and f["sev"] == gate.BLOCK for f in gate.findings)


def test_reality_coverage_not_applicable_no_block(tmp_path):
    # 项目没登记 LOC/resident/门窗 → 验证器不适用 → 不要求 → 不 block
    root = tmp_path / "剧"
    d = root / "出图" / "共享"
    d.mkdir(parents=True)
    (d / "asset_registry.json").write_text('{"assets": [{"id": "CHAR_A"}]}', encoding="utf-8")
    gate.findings.clear()
    gate.check_consistency_reality_coverage(str(root), "第1集", "review")
    assert not any(f["dim"] == "现实覆盖" and f["sev"] == gate.BLOCK for f in gate.findings)


# ── 声纹 band=bad 实测硬漂 → BLOCK（音色侧 ArcFace·与脸 G5 对称）─────────────────
def _grp(floor, calibrated, bands):
    return {"floor": floor, "floor_calibrated": calibrated,
            "lines": [{"idx": i, "score": 0.3 if b == "bad" else 0.9, "band": b} for i, b in enumerate(bands)]}


def test_voiceprint_calibrated_hard_drift_blocks(monkeypatch):
    monkeypatch.setattr(gate.vcons, "build_report", lambda root: {"voicemap_mismatches": [], "drifts": []})
    monkeypatch.setattr(gate.vprint, "analyze", lambda root, ep, margin=None: {
        "available": True, "mode": "resemblyzer", "manifest": "m.json",
        "groups": {"沈念|cosy:女A": _grp(0.72, True, ["ok", "bad"])}})
    gate.findings.clear()
    gate.check_voice_cross_episode("/tmp/x", "第2集")
    hits = [f for f in gate.findings if f["dim"] == "跨集声纹"]
    assert len(hits) == 1 and hits[0]["sev"] == gate.BLOCK and "ArcFace" in hits[0]["msg"]
    assert hits[0].get("confidence") != "heuristic"  # 实测证据级，不该被启发式降级


def test_voiceprint_uncalibrated_drift_only_warns(monkeypatch):
    # band=bad 但 floor 未标定（单句/欠采样）→ 弱证据，WARN 不硬拦。
    monkeypatch.setattr(gate.vcons, "build_report", lambda root: {"voicemap_mismatches": [], "drifts": []})
    monkeypatch.setattr(gate.vprint, "analyze", lambda root, ep, margin=None: {
        "available": True, "mode": "resemblyzer", "manifest": "m.json",
        "groups": {"柳娘|cosy:女B": _grp(0.70, False, ["bad"])}})
    gate.findings.clear()
    gate.check_voice_cross_episode("/tmp/x", "第2集")
    hits = [f for f in gate.findings if f["dim"] == "跨集声纹"]
    assert len(hits) == 1 and hits[0]["sev"] == gate.WARN


def test_voiceprint_native_group_skipped_in_cross_episode(monkeypatch):
    # native 组由 check_native_voice_identity 专管，check_voice_cross_episode 必须跳过避免双报。
    monkeypatch.setattr(gate.vcons, "build_report", lambda root: {"voicemap_mismatches": [], "drifts": []})
    monkeypatch.setattr(gate.vprint, "analyze", lambda root, ep, margin=None: {
        "available": True, "mode": "resemblyzer", "manifest": "m.json",
        "groups": {"守卫|native:nv1": _grp(0.70, True, ["bad"])}})
    gate.findings.clear()
    gate.check_voice_cross_episode("/tmp/x", "第2集")
    assert not [f for f in gate.findings if f["dim"] == "跨集声纹"]


def test_native_voice_calibrated_hard_drift_blocks_when_required(tmp_path, monkeypatch):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    audio = root / "出视频" / "第1集" / "audio"
    prod = root / "生产数据"
    audio.mkdir(parents=True)
    prod.mkdir(parents=True)
    (root / "_设置.md").write_text("- 制作模式: 原生音画\n", encoding="utf-8")
    (audio / "Clip_01_speech.wav").write_bytes(b"RIFF")
    (prod / "native_voice_identity_第1集.json").write_text(json.dumps({
        "kind": gate.NATIVE_VOICE_IDENTITY_SEGMENTS_KIND,
        "segments": [{"character_id": "CHAR_01", "speaker_key": "NATIVE",
                      "wav": "出视频/第1集/audio/Clip_01_speech.wav"}],
    }, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(gate.vprint, "analyze", lambda root, ep, margin=None: {
        "available": True, "mode": "resemblyzer",
        "native_voice_identity": {"status": "ok"},
        "groups": {"CHAR_01|native:NATIVE": _grp(0.70, True, ["ok", "bad"])}})
    gate.check_native_voice_identity(str(root), "第1集", "review")
    hits = [f for f in gate.findings if f["dim"] == "原生音画声线一致性"]
    assert any(f["sev"] == gate.BLOCK and "实测音色硬漂" in f["msg"] for f in hits), hits


def _patch_image_prompt_preflight_dependencies(monkeypatch):
    for name in (
        "check_compliance_manifest", "require_progress", "check_progress_artifact_signoff",
        "check_placeholder_policy", "check_voiceover_fingerprint", "check_timing_manifest_complete",
        "check_voice_cross_episode", "check_image_ai_policy", "check_backend_reachable",
        "check_drift_risk_advisories", "check_cross_episode_character_definition",
        "check_storyboard_contract", "check_storyboard_visual_contract",
        "check_storyboard_style_contract", "check_storyboard_special_templates",
    ):
        monkeypatch.setattr(gate, name, lambda *a, **k: None)


def _patch_video_prompt_preflight_dependencies(monkeypatch):
    for name in (
        "check_compliance_manifest", "require_progress", "check_progress_artifact_signoff",
        "check_placeholder_policy", "check_voiceover_fingerprint", "check_timing_manifest_complete",
        "check_voice_cross_episode", "check_identity_registry", "check_asset_reference_registry",
        "check_identity_adapter_matrix", "check_route_identity_readiness", "check_storyboard_contract",
        "check_action_anchor_contract", "check_storyboard_style_contract", "check_storyboard_special_templates",
        "check_expression_span_frame_contract", "check_image_assets", "check_input_frame_qc",
        "check_multimodal_continuity", "check_semantic_lineage", "check_state_continuity",
        "check_video_backend_reachable",
    ):
        monkeypatch.setattr(gate, name, lambda *a, **k: None)
    monkeypatch.setattr(gate, "episode_registry_reference_ids", lambda *a, **k: (set(), set()))


def test_image_prompt_preflight_does_not_require_image_prompt(monkeypatch, tmp_path):
    root = tmp_path / "制漫剧" / "预检"
    root.mkdir(parents=True)
    _patch_image_prompt_preflight_dependencies(monkeypatch)

    def fail(*_args, **_kwargs):
        raise AssertionError("image prompt checks must not run before prompt generation")

    monkeypatch.setattr(gate, "check_image_prompt_overview", fail)
    monkeypatch.setattr(gate, "check_prompt_checklists", fail)

    gate.findings.clear()
    gate.run(str(root), "第1集", "image_prompt_preflight")

    assert not gate.findings


def test_video_prompt_preflight_does_not_require_video_prompt(monkeypatch, tmp_path):
    root = tmp_path / "制漫剧" / "预检"
    root.mkdir(parents=True)
    _patch_video_prompt_preflight_dependencies(monkeypatch)

    def fail(*_args, **_kwargs):
        raise AssertionError("video prompt checks must not run before prompt generation")

    monkeypatch.setattr(gate, "check_video_prompt_frames", fail)
    monkeypatch.setattr(gate, "check_prompt_checklists", fail)
    monkeypatch.setattr(gate, "check_video_stage_raw_output_policy", fail)
    monkeypatch.setattr(gate, "check_contract_inheritance", fail)
    monkeypatch.setattr(gate, "check_asset_handoff_inheritance", fail)

    gate.findings.clear()
    gate.run(str(root), "第1集", "video_prompt_preflight")

    assert not gate.findings


def test_compose_gate_blocks_missing_srt_voice_first(tmp_path):
    # 配音先行：缺中文字幕是硬闸
    root = tmp_path / "制漫剧" / "vf"
    (root / "脚本" / "第1集").mkdir(parents=True)
    (root / "_设置.md").write_text("- 制作模式: 配音先行\n", encoding="utf-8")
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


def test_native_av_subtitle_alignment_compose_warns_when_missing(tmp_path):
    root = tmp_path / "制漫剧" / "av"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("- 制作模式: 原生音画\n", encoding="utf-8")

    gate.check_native_av_subtitle_alignment(str(root), "第1集", "compose")

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画字幕对齐" for f in gate.findings)
    assert any(f["sev"] == gate.WARN and f["dim"] == "原生音画字幕对齐" for f in gate.findings)


def test_native_av_subtitle_alignment_review_blocks_when_missing(tmp_path):
    root = tmp_path / "制漫剧" / "av"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("- 制作模式: 原生音画\n", encoding="utf-8")

    gate.check_native_av_subtitle_alignment(str(root), "第1集", "review")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画字幕对齐" for f in gate.findings)


def test_native_av_paid_distribution_compose_blocks_missing_subtitle_alignment(tmp_path):
    root = tmp_path / "制漫剧" / "av"
    (root / "合规").mkdir(parents=True)
    (root / "_设置.md").write_text("- 制作模式: 原生音画\n", encoding="utf-8")
    (root / "合规" / "compliance_manifest.json").write_text(json.dumps({
        "kind": gate.COMPLIANCE_KIND,
        "distribution_intent": "paid_distribution",
    }, ensure_ascii=False), encoding="utf-8")

    gate.check_native_av_subtitle_alignment(str(root), "第1集", "compose")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画字幕对齐" for f in gate.findings)


def test_native_av_subtitle_alignment_valid_sidecar_passes_review(tmp_path):
    root = tmp_path / "制漫剧" / "av"
    (root / "脚本" / "第1集").mkdir(parents=True)
    (root / "生产数据").mkdir(parents=True)
    (root / "_设置.md").write_text("- 制作模式: 原生音画\n", encoding="utf-8")
    (root / "脚本" / "第1集" / "字幕_中文.srt").write_text(
        "1\n00:00:00,000 --> 00:00:02,000\n你好。\n",
        encoding="utf-8",
    )
    (root / "生产数据" / "native_av_subtitle_alignment_第1集.json").write_text(json.dumps({
        "kind": "n2d_native_av_subtitle_alignment",
        "status": "pass",
        "alignment_tool": "whisperx",
        "word_level": True,
        "subtitle_path": "脚本/第1集/字幕_中文.srt",
        "clips": [{"clip_id": "Clip_01", "status": "aligned"}],
    }, ensure_ascii=False), encoding="utf-8")

    gate.check_native_av_subtitle_alignment(str(root), "第1集", "review")

    assert not any(f["dim"] == "原生音画字幕对齐" for f in gate.findings)


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


def _append_image_event(root: Path, asset: str, provider: str, event: str = "generation",
                        *, method: str = "", meta: dict | None = None) -> None:
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    row = {
        "kind": "n2d_production_event",
        "version": 1,
        "episode": "第1集",
        "stage": "image",
        "event": event,
        "generation": {"asset": asset, "provider": provider, "status": "pass"},
    }
    if method:
        row["generation"]["method"] = method
    if meta:
        row["meta"] = meta
    with (prod / "production_events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_image_ai_backend_migration_uses_latest_event_per_asset(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: Dreamina\n", encoding="utf-8")
    _append_image_event(root, "出图/第1集/图片/Clip_01.png", "Codex")
    _append_image_event(root, "出图/第1集/图片/Clip_01.png", "Dreamina", event="redraw")

    gate.check_image_ai_policy(str(root), "第1集")

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "生图AI一致性" for f in gate.findings)


def _write_image_baseline(root: Path, access: str = "Codex", model: str = "GPT Image 2") -> None:
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    (prod / "image_backend_baseline.json").write_text(json.dumps({
        "kind": "n2d_image_backend_baseline", "version": 1,
        "selection": {"access": access, "backend": "", "image_model": model, "channel": ""},
    }, ensure_ascii=False), encoding="utf-8")


def test_image_backend_reality_drifts_from_baseline_blocks(tmp_path):
    # 坑 D：_设置.md 仍声明 Codex（与锁定基线一致），但真实落档事件用了 Dreamina（单一·不混用）→
    # 混用闸/声明对账都抓不到，唯有事件对账基线戳穿：BLOCK「生图后端基线」。
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: Codex\n", encoding="utf-8")
    _write_image_baseline(root, access="Codex")
    _append_image_event(root, "出图/第1集/图片/Clip_01.png", "Dreamina")

    gate.check_image_ai_policy(str(root), "第1集")

    hits = [f for f in gate.findings if f["dim"] == "生图后端基线" and f["sev"] == gate.BLOCK]
    assert hits and any("真实落档事件" in f["msg"] for f in hits)


def test_image_backend_reality_matches_baseline_no_block(tmp_path):
    # 真实事件与锁定基线一致 → 不报「生图后端基线」reconcile。
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: Codex\n", encoding="utf-8")
    _write_image_baseline(root, access="Codex")
    _append_image_event(root, "出图/第1集/图片/Clip_01.png", "Codex")

    gate.check_image_ai_policy(str(root), "第1集")

    assert not any(f["dim"] == "生图后端基线" for f in gate.findings)


def test_image_backend_reality_reconcile_skipped_without_baseline(tmp_path):
    # 无锁定基线 → 事件对账跳过（由 check_image_backend_baseline 管缺基线），不误报。
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: Codex\n", encoding="utf-8")
    _append_image_event(root, "出图/第1集/图片/Clip_01.png", "Dreamina")

    gate.check_image_ai_policy(str(root), "第1集")

    assert not any(f["dim"] == "生图后端基线" for f in gate.findings)


def test_image_ai_backend_mixing_across_latest_assets_is_blocked(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: Dreamina\n", encoding="utf-8")
    _append_image_event(root, "出图/第1集/图片/Clip_01.png", "Dreamina")
    _append_image_event(root, "出图/第1集/图片/Clip_02.png", "Codex")

    gate.check_image_ai_policy(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "生图AI一致性" and "混用" in f["msg"] for f in gate.findings)


def _write_lora_scope(root: Path, clips=("Clip_03",)) -> None:
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    (prod / "lora_exception_scope_第1集.json").write_text(json.dumps({
        "kind": "n2d_lora_exception_scope",
        "episode": "第1集",
        "character_id": "CHAR_SHEN",
        "form": "常态",
        "scope": "hero_shots_only",
        "clips": list(clips),
        "reason": "hero shot needs approved LoRA",
        "project_image_model": "GPT Image 2",
        "lora_base_model": "flux-dev",
        "style_bridge": "match series grade and full image_qc",
        "qc_required": [
            "full image_qc face_reference_coverage",
            "style_consistency",
            "local_face_patch_guard",
        ],
        "not_a_project_model_switch": True,
    }, ensure_ascii=False), encoding="utf-8")


def test_lora_sidechain_requires_exception_scope(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    _append_image_event(
        root,
        "出图/第1集/图片/Clip_03.png",
        "ComfyUI LoRA",
        method="flux_lora",
        meta={"clip": "Clip_03", "lora_model": "CHAR_SHEN.safetensors"},
    )

    gate.check_lora_exception_scope(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "LoRA例外范围" and "缺" in f["msg"] for f in gate.findings)


def test_lora_sidechain_valid_scope_passes_and_does_not_count_as_model_mixing(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 生图AI: Codex\n", encoding="utf-8")
    _write_lora_scope(root, clips=("Clip_03",))
    _append_image_event(root, "出图/第1集/图片/Clip_01.png", "Codex")
    _append_image_event(
        root,
        "出图/第1集/图片/Clip_03.png",
        "ComfyUI LoRA",
        method="flux_lora",
        meta={"clip": "Clip_03", "lora_model": "CHAR_SHEN.safetensors"},
    )

    gate.check_lora_exception_scope(str(root), "第1集")
    gate.check_image_ai_policy(str(root), "第1集")

    assert not any(f["dim"] == "LoRA例外范围" for f in gate.findings)
    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "生图AI一致性" and "混用" in f["msg"] for f in gate.findings)


def test_lora_sidechain_outside_scope_blocks(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    _write_lora_scope(root, clips=("Clip_03",))
    _append_image_event(
        root,
        "出图/第1集/图片/Clip_08.png",
        "ComfyUI LoRA",
        method="flux_lora",
        meta={"clip": "Clip_08", "lora_model": "CHAR_SHEN.safetensors"},
    )

    gate.check_lora_exception_scope(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "LoRA例外范围" and "Clip_08" in f["msg"] for f in gate.findings)


def test_shot_scale_progression_survives_int_shots_schema(tmp_path):
    # 回归：新 storyboard schema 的 shots 是 int 列表（非 dict）；check_shot_scale_progression
    # 旧实现 (s or {}).get(...) 会 AttributeError 整段崩 gate。修后应不崩，并能从 continuity.shot_size 判景别。
    root = tmp_path / "制漫剧" / "测试剧"
    sb_dir = root / "脚本" / "第1集"
    sb_dir.mkdir(parents=True)
    clips = [{"id": f"Clip_{i:02d}", "shots": [1],
              "continuity": {"shot_size": "近景"}} for i in range(1, 5)]
    (sb_dir / "storyboard.json").write_text(
        json.dumps({"clips": clips}, ensure_ascii=False), encoding="utf-8")

    gate.check_shot_scale_progression(str(root), "第1集")  # 不应抛异常
    # 连续 4 镜同近景 → 景别阶梯单调 WARN（证明 continuity.shot_size 被读到）
    assert any(f["dim"] == "景别阶梯" and f["sev"] == gate.WARN for f in gate.findings)


def _write_reference_plan(root, summary):
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    plan = {"kind": "n2d_reference_plan", "episode": "第1集", "backend": "codex",
            "clips": [], "summary": summary}
    (prod / "reference_plan_第1集.json").write_text(
        json.dumps(plan, ensure_ascii=False), encoding="utf-8")


def test_reference_plan_warns_when_actions_pending(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    _write_reference_plan(root, {
        "weak_backend_large_delta_clips": 3,
        "chars_need_lora": ["CHAR_01/常态"],
        "chars_need_native_registration": [],
        "action_required": [{"clip": "C1", "char_id": "CHAR_01", "form": "常态"}],
    })

    gate.check_reference_plan_applied(str(root), "第1集")

    matches = [f for f in gate.findings if f["dim"] == "参考规划落实"]
    assert matches and all(f["sev"] == gate.BLOCK for f in matches)
    assert any("CHAR_01/常态" in f["msg"] for f in matches)


def test_reference_plan_blocks_high_risk_actions_in_demo(tmp_path):
    """铁律：弱后端大变化镜/需注册/需 LoRA 的未落实参考规划 demo 也 BLOCK。曾被 8f2e4c3f/c9d37df5 降成 production-only。"""
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)  # 无 _设置.md → 默认 demo profile
    _write_reference_plan(root, {
        "weak_backend_large_delta_clips": 3,
        "chars_need_lora": ["CHAR_01/常态"],
        "chars_need_native_registration": [],
        "action_required": [{"clip": "C1", "char_id": "CHAR_01", "form": "常态"}],
    })

    gate.check_reference_plan_applied(str(root), "第1集")

    matches = [f for f in gate.findings if f["dim"] == "参考规划落实"]
    assert matches and all(f["sev"] == gate.BLOCK for f in matches)


def _write_director_camera_plan(root, clips):
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    plan = {"kind": "n2d_director_camera_plan", "version": 1, "episode": "第1集", "clips": clips}
    (prod / "director_camera_plan_第1集.json").write_text(
        json.dumps(plan, ensure_ascii=False), encoding="utf-8")


def _write_image_prompt(root, text):
    p = root / "出图" / "第1集" / "prompt"
    p.mkdir(parents=True, exist_ok=True)
    (p / "01_分镜出图.md").write_text(text, encoding="utf-8")


def test_director_camera_plan_blocks_peak_shot_unconsumed(tmp_path):
    # P0-3：含高潮镜的导演运镜计划，但出图 prompt 零运镜词汇 → 付费前 BLOCK（规划好没落片）。
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    _write_director_camera_plan(root, [
        {"clip_id": "Clip_07", "rhythm": "高潮", "recommended": {"reason": "反转瞬间压迫"}},
    ])
    _write_image_prompt(root, "# Clip 07\n正向 prompt：少年挥剑。\n负向：模糊")  # 无导演运镜词汇
    gate.check_director_camera_plan_consumption(str(root), "第1集")
    matches = [f for f in gate.findings if f["dim"] == "导演运镜落实"]
    assert matches and any(f["sev"] == gate.BLOCK for f in matches)
    assert any("Clip_07" in f["msg"] for f in matches if f["sev"] == gate.BLOCK)


def test_director_camera_plan_warns_non_peak_unconsumed(tmp_path):
    # 普通镜未消费 → WARN（不 BLOCK）。
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    _write_director_camera_plan(root, [
        {"clip_id": "Clip_02", "rhythm": "过渡", "recommended": {"reason": "平稳对话"}},
    ])
    _write_image_prompt(root, "# Clip 02\n正向 prompt：少女喝茶。")
    gate.check_director_camera_plan_consumption(str(root), "第1集")
    matches = [f for f in gate.findings if f["dim"] == "导演运镜落实"]
    assert matches and all(f["sev"] == gate.WARN for f in matches)
    assert not any(f["sev"] == gate.BLOCK for f in matches)


def test_director_camera_plan_info_when_consumed(tmp_path):
    # prompt 含导演运镜词汇 → INFO（文档级已消费），即使含高潮镜也不 BLOCK。
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    _write_director_camera_plan(root, [
        {"clip_id": "Clip_07", "rhythm": "高潮", "recommended": {"reason": "反转瞬间压迫"}},
    ])
    _write_image_prompt(root, "# Clip 07\n镜头/机位：CU 推镜。\n起幅·运动余量：预留前景运动余量。\n构图防呆：主体不顶边。")
    gate.check_director_camera_plan_consumption(str(root), "第1集")
    matches = [f for f in gate.findings if f["dim"] == "导演运镜落实"]
    assert matches and all(f["sev"] == gate.INFO for f in matches)


def test_director_camera_plan_skips_when_no_sidecar(tmp_path):
    # 没跑 director_camera_plan（无 sidecar）→ 不强制、零发现（与 reference_plan 一致）。
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    _write_image_prompt(root, "# Clip 07\n正向 prompt：少年挥剑。")
    gate.check_director_camera_plan_consumption(str(root), "第1集")
    assert [f for f in gate.findings if f["dim"] == "导演运镜落实"] == []


def test_director_camera_plan_skips_when_prompt_absent(tmp_path):
    # sidecar 在但出图 prompt 包还没产出 → 不在此 BLOCK（上游阶段负责）。
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    _write_director_camera_plan(root, [
        {"clip_id": "Clip_07", "rhythm": "高潮", "recommended": {"reason": "反转"}},
    ])
    gate.check_director_camera_plan_consumption(str(root), "第1集")
    assert [f for f in gate.findings if f["dim"] == "导演运镜落实"] == []


def _write_director_applied(root, applied_image_ids, *, reviewer="wesley", plan_sha=None, prompt_sha=None):
    prod = root / "生产数据"
    sidecar = prod / "director_camera_plan_第1集.json"
    img_prompt = root / "出图" / "第1集" / "prompt" / "01_分镜出图.md"
    payload = {
        "kind": "n2d_director_camera_plan_application",
        "accepted": True,
        "reviewer": reviewer,
        "plan_sha256": plan_sha if plan_sha is not None else gate._safe_sha256(str(sidecar)),
        "scopes": [{
            "scope": "出图",
            "prompt_path": "出图/第1集/prompt/01_分镜出图.md",
            "prompt_sha256": prompt_sha if prompt_sha is not None else gate._safe_sha256(str(img_prompt)),
            "applied_clip_ids": applied_image_ids,
        }],
    }
    (prod / "director_camera_plan_applied_第1集.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_director_camera_plan_precise_all_signed_info(tmp_path):
    # Tier A：逐镜签收档覆盖所有镜（SHA fresh）→ INFO，即使 prompt 无烟雾词汇也精确采信。
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    _write_director_camera_plan(root, [
        {"clip_id": "Clip_07", "rhythm": "高潮", "recommended": {"reason": "反转"}},
    ])
    _write_image_prompt(root, "# Clip 07\n正向 prompt：少年挥剑。")  # 无烟雾词汇
    _write_director_applied(root, ["Clip_07"])
    gate.check_director_camera_plan_consumption(str(root), "第1集")
    matches = [f for f in gate.findings if f["dim"] == "导演运镜落实"]
    assert matches and all(f["sev"] == gate.INFO for f in matches)
    assert any("逐镜签收落实" in f["msg"] for f in matches)


def test_director_camera_plan_precise_peak_missing_blocks(tmp_path):
    # Tier A：签收档漏了高潮镜 → 精确 BLOCK，点名该镜（非整包烟雾）。
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    _write_director_camera_plan(root, [
        {"clip_id": "Clip_07", "rhythm": "高潮", "recommended": {"reason": "反转"}},
        {"clip_id": "Clip_02", "rhythm": "过渡", "recommended": {"reason": "对话"}},
    ])
    _write_image_prompt(root, "# 分镜\n起幅·运动余量：略。")  # 即使有烟雾词汇，Tier A 仍按签收逐镜判
    _write_director_applied(root, ["Clip_02"])  # 漏签 Clip_07（高潮）
    gate.check_director_camera_plan_consumption(str(root), "第1集")
    blocks = [f for f in gate.findings if f["dim"] == "导演运镜落实" and f["sev"] == gate.BLOCK]
    assert blocks and any("Clip_07" in f["msg"] for f in blocks)


def test_director_camera_plan_precise_non_peak_missing_warns(tmp_path):
    # Tier A：只漏普通镜 → WARN（不 BLOCK）。
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    _write_director_camera_plan(root, [
        {"clip_id": "Clip_02", "rhythm": "过渡", "recommended": {"reason": "对话"}},
        {"clip_id": "Clip_03", "rhythm": "铺垫", "recommended": {"reason": "环境"}},
    ])
    _write_image_prompt(root, "# 分镜\n无关内容。")
    _write_director_applied(root, ["Clip_02"])  # 漏签 Clip_03（普通）
    gate.check_director_camera_plan_consumption(str(root), "第1集")
    matches = [f for f in gate.findings if f["dim"] == "导演运镜落实"]
    assert matches and all(f["sev"] == gate.WARN for f in matches)
    assert any("Clip_03" in f["msg"] for f in matches)


def test_director_camera_plan_stale_signoff_falls_back_to_smoke(tmp_path):
    # 防蒙混：plan_sha256 不符（plan 变了没重签）→ 不走 Tier A，回退烟雾收据；prompt 无词汇+高潮镜→BLOCK。
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    _write_director_camera_plan(root, [
        {"clip_id": "Clip_07", "rhythm": "高潮", "recommended": {"reason": "反转"}},
    ])
    _write_image_prompt(root, "# Clip 07\n正向 prompt：少年挥剑。")  # 无烟雾词汇
    _write_director_applied(root, ["Clip_07"], plan_sha="deadbeef")  # 陈旧签收
    gate.check_director_camera_plan_consumption(str(root), "第1集")
    blocks = [f for f in gate.findings if f["dim"] == "导演运镜落实" and f["sev"] == gate.BLOCK]
    assert blocks and any("找不到任何" in f["msg"] for f in blocks)  # 走了烟雾分支


def test_reference_plan_application_sidecar_clears_pending_actions(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    _write_reference_plan(root, {
        "weak_backend_large_delta_clips": 3,
        "chars_need_lora": ["CHAR_01/常态"],
        "chars_need_native_registration": [],
        "action_required": [{"clip": "C1", "char_id": "CHAR_01", "form": "常态"}],
    })
    prompt = root / "出图" / "第1集" / "prompt" / "01_分镜出图.md"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("参考图入参清单与预算：selected=[face_anchor, expression]\n"
                      "多人同框执行策略：regional_construct_required + split_composite_required\n"
                      "升档取舍：本轮先走多图参考派生，失败后进入 LoRA。\n",
                      encoding="utf-8")
    plan = root / "生产数据" / "reference_plan_第1集.json"
    app = {
        "kind": "n2d_reference_plan_application",
        "accepted": True,
        "reviewer": "test",
        "plan_sha256": hashlib.sha256(plan.read_bytes()).hexdigest(),
        "prompt_path": "出图/第1集/prompt/01_分镜出图.md",
        "prompt_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
        "applied_action_count": 1,
        "applied_evidence": [
            "参考预算、分区构建和升档取舍已写入 01_分镜出图.md",
        ],
    }
    (root / "生产数据" / "reference_plan_application_第1集.json").write_text(
        json.dumps(app, ensure_ascii=False), encoding="utf-8")

    gate.check_reference_plan_applied(str(root), "第1集")

    matches = [f for f in gate.findings if f["dim"] == "参考规划落实"]
    assert matches and all(f["sev"] != gate.BLOCK for f in matches)
    assert any(f["sev"] == gate.INFO for f in matches)


def test_reference_plan_advisory_actions_warn_without_hard_escalation(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    _write_reference_plan(root, {
        "weak_backend_large_delta_clips": 0,
        "chars_need_lora": [],
        "chars_need_native_registration": [],
        "action_required": [{"clip": "C1", "char_id": "CHAR_01", "form": "常态"}],
    })

    gate.check_reference_plan_applied(str(root), "第1集")

    matches = [f for f in gate.findings if f["dim"] == "参考规划落实"]
    assert matches and all(f["sev"] == gate.WARN for f in matches)


def test_reference_plan_silent_when_no_plan_and_no_character_signal(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)

    gate.check_reference_plan_applied(str(root), "第1集")

    assert not any(f["dim"] == "参考规划落实" for f in gate.findings)


def test_reference_plan_missing_blocks_for_core_registry(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    _write_registry(root, [_char("CHAR_01", "沈念", "长线女主·全篇", "常态", "registered")])

    gate.check_reference_plan_applied(str(root), "第1集")

    matches = [f for f in gate.findings if f["dim"] == "参考规划落实"]
    assert matches and matches[0]["sev"] == gate.BLOCK
    assert "reference_plan_第1集.json" in matches[0]["msg"]


def test_reference_plan_missing_warns_for_character_storyboard_without_registry(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    sb_dir = root / "脚本" / "第1集"
    sb_dir.mkdir(parents=True)
    (sb_dir / "storyboard.json").write_text(
        json.dumps({"clips": [{"id": "C1", "characters": ["CHAR_01/常态"]}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    gate.check_reference_plan_applied(str(root), "第1集")

    matches = [f for f in gate.findings if f["dim"] == "参考规划落实"]
    assert matches and matches[0]["sev"] == gate.WARN


def test_reference_plan_silent_when_no_actions(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    _write_reference_plan(root, {"weak_backend_large_delta_clips": 0, "action_required": []})

    gate.check_reference_plan_applied(str(root), "第1集")

    assert not any(f["dim"] == "参考规划落实" for f in gate.findings)


def _write_registry(root, characters):
    shared = root / "出图" / "共享"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "identity_registry.json").write_text(
        json.dumps({"kind": "n2d_identity_registry", "characters": characters}, ensure_ascii=False),
        encoding="utf-8",
    )


def _char(cid, name, scope, form, image_status, backend="seedream"):
    return {
        "id": cid,
        "name": name,
        "scope": scope,
        "forms": [{"form": form, "identity_adapters": {"image": {backend: {"status": image_status}}}}],
    }


def test_native_subject_not_prompted_for_codex(tmp_path):
    # Codex 无持久主体：即便核心角色未注册原生主体，也不该提示去注册（自动回退参考图派生）。
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: Codex\n", encoding="utf-8")
    _write_registry(root, [_char("CHAR_01", "女主", "全篇", "常态", "unregistered")])

    gate.check_image_ai_policy(str(root), "第1集")

    assert not any(f["dim"] == "原生主体注册" for f in gate.findings)


def test_native_subject_not_prompted_for_dreamina(tmp_path):
    # Dreamina/即梦官方 CLI 可多参考，但无持久主体 ID；不能误提示去注册原生主体。
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: Dreamina\n", encoding="utf-8")
    _write_registry(root, [_char("CHAR_01", "沈念", "长线女主·全篇", "常态", "unregistered", backend="dreamina")])

    gate.check_image_ai_policy(str(root), "第1集")

    assert not any(f["dim"] == "原生主体注册" for f in gate.findings)


def test_native_subject_blocks_when_capable_backend_and_core_unregistered(tmp_path):
    # 选了支持原生主体的后端（Seedream）且核心长线角色未注册 → BLOCK，先注册再付费出图。
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: Seedream\n", encoding="utf-8")
    _write_registry(root, [_char("CHAR_01", "沈念", "长线女主·全篇", "常态", "unregistered")])

    gate.check_image_ai_policy(str(root), "第1集")

    matches = [f for f in gate.findings if f["dim"] == "原生主体注册"]
    assert matches and all(f["sev"] == gate.BLOCK for f in matches)
    assert any("CHAR_01/常态" in f["msg"] for f in matches)


def test_native_subject_not_prompted_when_registered(tmp_path):
    # 核心角色已在该后端注册（status=registered）→ 不再提示。
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: Seedream\n", encoding="utf-8")
    _write_registry(root, [_char("CHAR_01", "沈念", "全篇", "常态", "registered")])

    gate.check_image_ai_policy(str(root), "第1集")

    assert not any(f["dim"] == "原生主体注册" for f in gate.findings)


def test_native_subject_not_prompted_for_shortline_only(tmp_path):
    # ROI 默认最小化：只有短线单元妖未注册时不打扰，不对前几集退场的角色前置高档。
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 生图AI: Seedream\n", encoding="utf-8")
    _write_registry(root, [_char("CHAR_06", "小妖A", "第3集短线单元妖", "覆鳞宫女", "unregistered")])

    gate.check_image_ai_policy(str(root), "第1集")

    assert not any(f["dim"] == "原生主体注册" for f in gate.findings)


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

    assert any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "角色定妆基础包"
        and "人物定妆基础包必须写齐" in f["msg"]
        for f in gate.findings
    )


def test_role_makeup_prompt_allows_restricted_partial_without_three_view(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出图" / "common" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "角色定妆.md").write_text(
        """## CHAR_04 皇后·局部参考（⬜ 暂不正脸出镜）

**目标存档（局部）**：`出图/共享/图片/定妆_皇后_局部_手部搁茶.png`、`出图/共享/图片/定妆_皇后_局部_帘后剪影.png`
**身份注册**：`出图/共享/identity_registry.json` → `CHAR_04.局部参考`
**硬约束**：restricted_partial / no_full_face；只手 + 帘后剪影，绝不正脸，不建完整正脸。
- 锚点句：保养得宜的手·暗红宫装袖口·垂帘后朦胧人影（绝不正脸）

### 正向 prompt（中文·手部搁茶局部）
```text
皇后局部参考，只见保养得宜的手、暗红宫装袖口、帘后剪影，绝不正脸。
```

### 正向 prompt（英文·手部搁茶局部）
```text
Queen restricted partial reference, well-kept hand, dark-red robe cuff, behind-curtain silhouette, NEVER showing the face.
```

### 负向 prompt
```text
皇后正脸/清脸/可辨五官（硬禁）、补全上半身正脸、现代物件、水印。
```

### 检查清单（定妆自查·最易漏③人物/⑥中性光影/一致性）
1. ✅ 只手 + 帘后剪影 + 暗红宫装袖口，绝无正脸。

### 自检（生成后逐张过 · 落档闸门）
**自检**：
- [ ] 无正脸、无可辨五官。
""",
        encoding="utf-8",
    )

    gate.check_common_image_prompts(str(root))

    assert not any(f["sev"] == gate.BLOCK and "缺正向 prompt" in f["msg"] for f in gate.findings)
    assert not any(f["sev"] == gate.BLOCK and f["dim"] in {"角色定妆基础包", "角色一致性"} for f in gate.findings)


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
- 45°参考：`出图/共享/图片/定妆_沈念_45度.png`
- 侧面参考：`出图/共享/图片/定妆_沈念_侧.png`
- 背面参考：`出图/共享/图片/定妆_沈念_背.png`
- 服装参考：`出图/共享/图片/定妆_沈念_半身.png`
- 脸部特写：`出图/共享/图片/定妆_沈念_脸部特写.png`
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
- 45°参考：`出图/共享/图片/定妆_沈念_45度.png`
- 侧面参考：`出图/共享/图片/定妆_沈念_侧.png`
- 背面参考：`出图/共享/图片/定妆_沈念_背.png`
- 服装参考：`出图/共享/图片/定妆_沈念_半身.png`，从已通过自检的正面主参考裁切并放大/重采样回 9:16；人物主体居中、头身中线接近画面中线、左右留白基本均衡；不得用白底/浅灰底/空白补满下半截
- 脸部特写：`出图/共享/图片/定妆_沈念_脸部特写.png`
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


def test_video_clip_missing_compact_prompt_fields_is_blocked():
    clip = GOOD_VIDEO_CLIP.replace(
        "首帧保持：保持首帧已锁定的沈念脸型、发髻、服装、冷宫寝殿、烛火光位和前景鸩酒托盘，不重定人物外貌、场景布局或光色；\n",
        "",
    ).replace(
        "情绪节奏：[0-2s] 惊惧呼吸压住；[2-4s] 眼神缓慢聚焦；[4-5s] 克制停住，为下一镜留半拍；\n",
        "",
    ).replace(
        "禁止：不要换脸、不要换衣、不要新增人物或道具、不要改变冷宫场景和烛火光位、不要生成文字/logo/水印、不要生成原生人声；\n",
        "",
    )

    gate.check_video_clip_prompt_section("01_clips.md", clip)

    for key in ("首帧保持", "情绪节奏", "禁止"):
        assert any(f["sev"] == gate.BLOCK and f["dim"] == "prompt" and key in f["msg"] for f in gate.findings)


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


def test_video_clip_freeform_camera_move_warns_unstructured():
    # ⑤ 运镜结构化：自由散文运镜（无结构化词）→ 运动一致性 WARN（提示用 CAMERA_MOVE_LEXICON）
    clip = GOOD_VIDEO_CLIP.replace(
        "镜头运动：略俯 MCU 缓慢推近 0.5x，结尾稳定停住；",
        "镜头运动：镜头慢慢靠近她的脸然后停下；",
    )
    gate.check_video_clip_prompt_section("01_clips.md", clip)
    assert any(f["sev"] == gate.WARN and f["dim"] == "运动一致性" and "结构化运镜词" in str(f["msg"])
               for f in gate.findings)


def test_video_clip_camera_move_missing_speed_warns():
    # ⑤ 运镜结构化：识别到运镜词但缺速度档 → 运动一致性 WARN（补速度词）
    clip = GOOD_VIDEO_CLIP.replace(
        "镜头运动：略俯 MCU 缓慢推近 0.5x，结尾稳定停住；",
        "镜头运动：环绕拍摄主角；",
    )
    gate.check_video_clip_prompt_section("01_clips.md", clip)
    assert any(f["sev"] == gate.WARN and f["dim"] == "运动一致性" and "缺速度档" in str(f["msg"])
               for f in gate.findings)


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
        "**近景/反打身份锁定**：本镜是说话近景；优先引用 expressions/脸部特写，缺脸部特写时用正脸 front + 侧面 + 半身 reference_group；锁脸型、五官比例、发型发髻、标志配饰、服装配色；只允许眼神和嘴角小幅变化，脸漂则用 MCU/侧脸/反应镜保真实现。\n",
        "",
    ).replace(
        "近景身份锁定约束：近景优先脸部特写/表情参考；缺 reference_controls 时只做低幅度眼神和嘴角变化，不大幅转头，不重绘五官，配角近景不稳则用 MCU/OTS/侧脸保真实现；\n",
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


def test_video_clip_high_action_requires_action_choreography_contract():
    clip = GOOD_VIDEO_CLIP.replace(
        "**模型路由**：shot_type=dialogue_closeup；primary_backend=dreamina；fallback_backends=seedance,kling；mode=image2video；native_audio_policy=none；identity_requirement=reference_group；risk_flags=mouth_visible；rationale=普通近景先用项目默认后端，失败切身份/运动更强后端；degrade_plan=改侧脸或反应镜，必要时切 seedance/kling 重跑\n",
        "**模型路由**：shot_type=flight；primary_backend=seedance；fallback_backends=kling,dreamina；mode=image2video；native_audio_policy=none；identity_requirement=face_lock_or_reference_group；risk_flags=high_speed_motion,spatial_path_risk,action_choreography_required；rationale=御剑飞行高动作；degrade_plan=拆起飞/巡航/机动/抵达\n"
        "**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_01/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,camera_path,parallax_layers；failure_modes=pose_drift,altitude_curve_drift；gate_policy=block_without_ready_manifest_or_degrade_only_manifest\n",
    ).replace(
        "身份锁定约束：读取 identity_registry.json；dreamina 回退首帧+尾帧+reference_group；保持 drift_forbidden=face_shape/hairstyle/outfit_palette；\n",
        "物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/camera_path/parallax_layers 控制资产；degrade_only 时拆起飞/巡航/机动/抵达；禁止只靠文本 prompt 猜高速飞行路径；\n"
        "身份锁定约束：读取 identity_registry.json；dreamina 回退首帧+尾帧+reference_group；保持 drift_forbidden=face_shape/hairstyle/outfit_palette；\n",
    ).replace(
        "- [ ] 人物运动自然\n",
        "- [ ] 人物运动自然\n- [ ] Motion Control / FeatureMelting：检查姿态、路径、视差层和高度曲线，无特征融化\n",
    )

    gate.check_video_clip_prompt_section("01_clips.md", clip)

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "动作编排" and "动作编排契约" in f["msg"] for f in gate.findings)


def test_video_clip_high_action_choreography_contract_passes():
    clip = GOOD_VIDEO_CLIP.replace(
        "**环境交互**：残烛光在眼下轻轻跳动，床幔阴影随呼吸微动，前景托盘保持不位移。\n",
        "**环境交互**：云层被剑光切开，前景云雾快速掠过，远山慢速后移。\n"
        "**动作编排契约**：beats=入云/巡航/穿云/抵达；speed_curve=巡航匀速→穿云加速→抵达减速；spatial_path=画左入画沿云海弧线到画右上；camera_path=侧跟飞并轻微下压；readability_beats=穿云前半拍预备/出云定方向；degrade_plan=拆起飞/巡航/机动/抵达；keyframe_plan=start入云/intent_mid穿云前/impact_or_apex出云峰值/end抵达；post_cue_points=wind_whoosh入云/parallax_swell穿云；physics_guard=脸衣不漂/路径不反/祥云不变/不新增翻滚；flight_path=画左到画右上；altitude_curve=高→低穿云→高；pose_lock=负手立剑只小幅前倾；parallax_layers=前景云快/远山慢；mount_or_cloud_lock=青锋剑形态与脚下云团锁定。\n",
    ).replace(
        "**模型路由**：shot_type=dialogue_closeup；primary_backend=dreamina；fallback_backends=seedance,kling；mode=image2video；native_audio_policy=none；identity_requirement=reference_group；risk_flags=mouth_visible；rationale=普通近景先用项目默认后端，失败切身份/运动更强后端；degrade_plan=改侧脸或反应镜，必要时切 seedance/kling 重跑\n",
        "**模型路由**：shot_type=flight；primary_backend=seedance；fallback_backends=kling,dreamina；mode=image2video；native_audio_policy=none；identity_requirement=face_lock_or_reference_group；risk_flags=high_speed_motion,spatial_path_risk,action_choreography_required；rationale=御剑飞行高动作；degrade_plan=拆起飞/巡航/机动/抵达\n"
        "**Motion Control / 物理交互控制**：level=required；manifest_path=出视频/第1集/control/Clip_01/motion_control_manifest.json；required_inputs=pose_sequence,depth_sequence,camera_path,parallax_layers；failure_modes=pose_drift,altitude_curve_drift；gate_policy=block_without_ready_manifest_or_degrade_only_manifest\n",
    ).replace(
        "环境交互约束：残烛光在眼下轻跳，床幔阴影随呼吸微动；\n",
        "环境交互约束：云层被剑光切开，前景云雾快速掠过，远山慢速后移；\n"
        "动作编排约束：按 beats 执行巡航到穿云，只允许 speed_curve 所写加速，spatial_path/camera_path/altitude_curve 不改，keyframe_plan/post_cue_points/physics_guard 不改，readability_beats 在穿云前和出云后各停半拍；\n",
    ).replace(
        "身份锁定约束：读取 identity_registry.json；dreamina 回退首帧+尾帧+reference_group；保持 drift_forbidden=face_shape/hairstyle/outfit_palette；\n",
        "物理交互约束：读取 motion_control_manifest.json；ready 时使用 pose/depth/camera_path/parallax_layers 控制资产；degrade_only 时拆起飞/巡航/机动/抵达；禁止只靠文本 prompt 猜高速飞行路径；\n"
        "身份锁定约束：读取 identity_registry.json；dreamina 回退首帧+尾帧+reference_group；保持 drift_forbidden=face_shape/hairstyle/outfit_palette；\n",
    ).replace(
        "- [ ] 人物运动自然\n",
        "- [ ] 人物运动自然\n- [ ] 动作编排：检查 speed_curve/spatial_path/camera_path/readability_beats/keyframe_plan/post_cue_points/physics_guard 与高度曲线\n- [ ] Motion Control / FeatureMelting：检查姿态、路径、视差层和高度曲线，无特征融化\n",
    )

    gate.check_video_clip_prompt_section("01_clips.md", clip)

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "动作编排" for f in gate.findings)
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


def test_video_clip_native_speech_route_allows_intentional_speech_policy():
    clip = GOOD_VIDEO_CLIP.replace(
        "native_audio_policy=none",
        "native_audio_policy=native_speech",
    ).replace(
        "mode=image2video",
        "mode=native_av",
    ).replace(
        "audio_intent=none；risk=low；mouth_visible=no；speech_policy=no_native_speech；compose_policy=丢弃；review=生成后确认无原生人声",
        "audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词口型同步",
    ).replace(
        "原生音画约束：默认禁止原生人声，不生成对白/旁白/哼唱；本镜 compose_policy=丢弃；",
        "原生音画约束：native_speech 有意生成台词和口型，声源来自画内沈念，compose_policy=保留原片音轨；",
    ).replace(
        "声音约束：无对白、无旁白、不要生成原生人声；",
        "声音约束：本镜台词由原生音画后端生成，后期保留原片音轨；",
    )

    gate.check_video_clip_prompt_section("01_clips.md", clip, route={"mode": "native_av", "native_audio_policy": "native_speech"})

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画" for f in gate.findings)


def test_video_clip_native_speech_route_blocks_old_no_native_policy():
    route = {"mode": "native_av", "native_audio_policy": "native_speech"}

    gate.check_video_clip_prompt_section("01_clips.md", GOOD_VIDEO_CLIP, route=route)

    assert any(
        f["sev"] == gate.BLOCK and f["dim"] == "原生音画" and "native_speech" in f["msg"]
        for f in gate.findings
    )


def test_video_clip_voice_first_route_allows_no_native_speech_policy():
    gate.check_video_clip_prompt_section("01_clips.md", GOOD_VIDEO_CLIP, route={"mode": "image2video", "native_audio_policy": "none"})

    assert not any(
        f["sev"] == gate.BLOCK and f["dim"] == "原生音画" and "不得写 native_speech" in f["msg"]
        for f in gate.findings
    )


def test_video_clip_voice_first_route_blocks_native_speech_policy():
    clip = GOOD_VIDEO_CLIP.replace(
        "audio_intent=none；risk=low；mouth_visible=no；speech_policy=no_native_speech；compose_policy=丢弃；review=生成后确认无原生人声",
        "audio_intent=native_speech；risk=medium；mouth_visible=yes；speech_policy=native_speech；compose_policy=保留原片音轨；review=生成后检查台词口型同步",
    )

    gate.check_video_clip_prompt_section("01_clips.md", clip, route={"mode": "image2video", "native_audio_policy": "none"})

    assert any(
        f["sev"] == gate.BLOCK and f["dim"] == "原生音画" and "不得写 native_speech" in f["msg"]
        for f in gate.findings
    )


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
    (root / "_设置.md").write_text("# _设置\n- 制作模式: 配音先行\n- 视频原生音轨: 低音量混入环境声\n", encoding="utf-8")
    (prompt_dir / "00_总览.md").write_text(
        "# 总览\n\n## 本集导演一致性契约\n"
        "- 主色调：冷青\n- 镜头语法：慢推和固定\n- 轴线：床到门横轴\n- 剧情状态锁：觉醒前不发光\n- 场景状态：烛火不跳位\n\n"
        "## 本集基础视觉风格契约\n"
        "- 风格名：写实电影感\n- 视觉基调：低饱和\n- 镜头与构图：中景到特写\n- 光色策略：冷青暖烛\n- 运动边界：慢推\n- 风格禁忌：照片皮肤\n",
        encoding="utf-8",
    )

    gate.check_video_prompt_overview(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画" and "opt-in 清单" in f["msg"] for f in gate.findings)


def test_native_av_physical_contract_required_in_native_mode(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 制作模式: 原生音画\n", encoding="utf-8")
    gate.check_native_av_physical_contract(str(root), "第1集", "native_speech 有意生成", "00_总览.md")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画物理一致性" and "缺「原生音画物理一致性契约」" in f["msg"] for f in gate.findings)


def test_native_av_physical_contract_requires_all_fields(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 制作模式: 原生音画\n", encoding="utf-8")
    text = "## 原生音画物理一致性契约\n- 声源归属：画内人物\n- 口型策略：说话镜必须口型同步\n"

    gate.check_native_av_physical_contract(str(root), "第1集", text, "00_总览.md")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画物理一致性" and "材质/动作声" in f["msg"] for f in gate.findings)


def test_native_av_physical_contract_passes_when_fields_present(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 制作模式: 原生音画\n", encoding="utf-8")
    text = (
        "## 原生音画物理一致性契约\n"
        "- 声源归属：画内人物对白与可见动作声分离记录\n"
        "- 口型策略：说话镜 native_speech 必须口型同步，非说话镜不得冒出对白\n"
        "- 材质/动作声：衣料、脚步、器物只跟可见动作触发\n"
        "- 空间声学：内景近声、远景衰减、遮挡和混响随景别变化\n"
        "- 字幕/后期策略：成片后 whisperx 对齐，旁白层不得与原生台词重叠\n"
    )

    gate.check_native_av_physical_contract(str(root), "第1集", text, "00_总览.md")

    assert not any(f["dim"] == "原生音画物理一致性" for f in gate.findings)


def test_native_av_physical_contract_required_for_mixed_native_audio(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 制作模式: 配音先行\n- 视频原生音轨: 低音量混入环境声\n", encoding="utf-8")

    gate.check_native_av_physical_contract(str(root), "第1集", "## 原生音画 opt-in 清单\naudio_intent=ambience", "00_总览.md")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画物理一致性" and "物理一致性契约" in f["msg"] for f in gate.findings)


def test_native_av_physics_sidecar_required_when_contract_present(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 制作模式: 原生音画\n", encoding="utf-8")

    gate.check_native_av_physics_sidecar(str(root), "第1集")

    assert any(
        f["sev"] == gate.BLOCK and f["dim"] == "原生音画物理一致性" and "sidecar" in f["msg"]
        for f in gate.findings
    )


def test_native_av_physics_sidecar_required_for_mixed_ambience(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 制作模式: 配音先行\n- 视频原生音轨: 低音量混入环境声\n", encoding="utf-8")

    gate.check_native_av_physics_sidecar(str(root), "第1集")

    assert any("sidecar" in f["msg"] for f in gate.findings)


def test_native_av_physics_sidecar_validates_ambience_source_and_reverb(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 制作模式: 配音先行\n- 视频原生音轨: 低音量混入环境声\n", encoding="utf-8")
    (prod / "native_av_physics_第1集.json").write_text(json.dumps({
        "kind": gate.NATIVE_AV_PHYSICS_KIND,
        "clips": [{
            "clip_id": "Clip_01",
            "audio_intent": "ambience",
            "sound_source": {"source": "雨打窗棂", "visible_evidence": "窗外雨丝可见"},
            "spatial_acoustics": {"space_id": "LOC_01", "distance": "wide", "reverb_profile": "stone_room"},
            "post_policy": {"compose_policy": "低音量混入环境声"},
        }],
    }, ensure_ascii=False), encoding="utf-8")

    gate.check_native_av_physics_sidecar(str(root), "第1集")

    assert not any(f["dim"] == "原生音画物理一致性" for f in gate.findings)


def test_native_av_physics_sidecar_blocks_missing_speaker_evidence(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 制作模式: 原生音画\n", encoding="utf-8")
    (prod / "native_av_physics_第1集.json").write_text(json.dumps({
        "kind": gate.NATIVE_AV_PHYSICS_KIND,
        "clips": [{
            "clip_id": "Clip_01",
            "audio_intent": "native_speech",
            "speaker_source": {"character_id": "CHAR_01", "on_screen": True},
            "lip_sync": {"policy": "match_dialogue"},
            "spatial_acoustics": {"space_id": "LOC_01", "distance": "close", "reverb_profile": "small_room"},
            "post_policy": {"compose_policy": "保留原片音轨"},
        }],
    }, ensure_ascii=False), encoding="utf-8")

    gate.check_native_av_physics_sidecar(str(root), "第1集")

    assert any("mouth_visible=true" in f["msg"] for f in gate.findings)
    assert any("dialogue_ref" in f["msg"] for f in gate.findings)


def test_native_av_physics_sidecar_passes_valid_native_speech(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 制作模式: 原生音画\n", encoding="utf-8")
    (prod / "native_av_physics_第1集.json").write_text(json.dumps({
        "kind": gate.NATIVE_AV_PHYSICS_KIND,
        "clips": [{
            "clip_id": "Clip_01",
            "audio_intent": "native_speech",
            "speaker_source": {
                "character_id": "CHAR_01",
                "on_screen": True,
                "mouth_visible": True,
                "dialogue_ref": "脚本/第1集/voiceover.txt#L10",
            },
            "lip_sync": {"policy": "native_dialogue_match"},
            "action_sounds": [{
                "action": "抬手碰杯",
                "sound": "瓷杯轻响",
                "visible_evidence": "杯子在画内接触桌面",
                "timing": "2.1s",
            }],
            "spatial_acoustics": {"space_id": "LOC_01", "distance": "close", "reverb_profile": "small_room"},
            "post_policy": {"compose_policy": "保留原片音轨"},
        }],
    }, ensure_ascii=False), encoding="utf-8")

    gate.check_native_av_physics_sidecar(str(root), "第1集")

    assert not any(f["dim"] == "原生音画物理一致性" for f in gate.findings)


def test_generation_recipe_evidence_blocks_missing_release_fields(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    (prod / "production_events.jsonl").write_text(json.dumps({
        "episode": "第1集",
        "stage": "image",
        "event": "generation",
        "generation": {"asset": "出图/第1集/图片/Clip_01.png", "status": "pass"},
        "meta": {"recipe_hash": "abc", "prompt_sha256": "def", "seed_effective": False, "seed_support": "unsupported"},
    }, ensure_ascii=False) + "\n", encoding="utf-8")

    gate.check_generation_recipe_evidence(str(root), "第1集", "review")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "生成配方证据" and "backend_version" in f["msg"] for f in gate.findings)


def test_generation_recipe_evidence_blocks_final_media_without_event(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    (root / "_设置.md").parent.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    png = root / "出图" / "第1集" / "图片" / "Clip_01.png"
    mp4 = root / "出视频" / "第1集" / "视频" / "Clip_01.mp4"
    png.parent.mkdir(parents=True)
    mp4.parent.mkdir(parents=True)
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    mp4.write_bytes(b"mp4")
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (prod / "production_events.jsonl").write_text(json.dumps({
        "episode": "第1集",
        "stage": "image",
        "event": "generation",
        "generation": {"asset": "出图/第1集/图片/Clip_01.png", "status": "pass"},
        "meta": {
            "provider": "openai",
            "model": "gpt-image-2",
            "channel": "codex-cli",
            "route_hash": "route-sha",
            "capability_evidence_id": "image_backend_capabilities/codex-2026-06-22",
            "recipe_hash": "abc",
            "prompt_sha256": "def",
            "reference_bundle_sha256": "ghi",
            "backend_version": "codex-2026-06-22",
            "quality_tier": "final",
            "actual_image_inputs": ["出图/共享/图片/定妆_沈念.png"],
            "seed_effective": False,
            "seed_support": "unsupported",
        },
    }, ensure_ascii=False) + "\n", encoding="utf-8")

    gate.check_generation_recipe_evidence(str(root), "第1集", "review")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "生成配方证据" and "Clip_01.mp4" in f["msg"] for f in gate.findings)


def test_generation_recipe_evidence_image_stage_ignores_existing_video_media(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    (root / "_设置.md").parent.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    png = root / "出图" / "第1集" / "图片" / "Clip_01.png"
    mp4 = root / "出视频" / "第1集" / "视频" / "Clip_01.mp4"
    png.parent.mkdir(parents=True)
    mp4.parent.mkdir(parents=True)
    png.write_bytes(_TEST_PNG_BYTES)
    mp4.write_bytes(b"mp4")
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (prod / "production_events.jsonl").write_text(json.dumps({
        "episode": "第1集",
        "stage": "image",
        "event": "generation",
        "generation": {"asset": "出图/第1集/图片/Clip_01.png", "status": "pass"},
        "meta": {
            "provider": "openai",
            "model": "gpt-image-2",
            "channel": "codex-cli",
            "route_hash": "route-sha",
            "capability_evidence_id": "image_backend_capabilities/codex-2026-06-22",
            "recipe_hash": "abc",
            "prompt_sha256": "def",
            "reference_bundle_sha256": "ghi",
            "backend_version": "codex-2026-06-22",
            "quality_tier": "final",
            "actual_image_inputs": ["出图/共享/图片/定妆_沈念.png"],
            "seed_effective": False,
            "seed_support": "unsupported",
        },
    }, ensure_ascii=False) + "\n", encoding="utf-8")

    gate.check_generation_recipe_evidence(str(root), "第1集", "image")

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "生成配方证据" for f in gate.findings)


def test_generation_recipe_evidence_passes_complete_event(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    (prod / "production_events.jsonl").write_text(json.dumps({
        "episode": "第1集",
        "stage": "image",
        "event": "generation",
        "generation": {"asset": "出图/第1集/图片/Clip_01.png", "status": "pass"},
        "meta": {
            "provider": "openai",
            "model": "gpt-image-2",
            "channel": "codex-cli",
            "route_hash": "route-sha",
            "capability_evidence_id": "image_backend_capabilities/codex-2026-06-22",
            "recipe_hash": "abc",
            "prompt_sha256": "def",
            "reference_bundle_sha256": "ghi",
            "backend_version": "codex-2026-06-22",
            "quality_tier": "final",
            "actual_image_inputs": ["出图/共享/图片/定妆_沈念.png"],
            "seed_effective": False,
            "seed_support": "unsupported",
        },
    }, ensure_ascii=False) + "\n", encoding="utf-8")

    gate.check_generation_recipe_evidence(str(root), "第1集", "review")

    assert not any(f["dim"] == "生成配方证据" for f in gate.findings)


def test_generation_recipe_evidence_recovers_moved_project_asset_paths(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    mp4 = root / "出视频" / "第1集" / "视频" / "Clip_02_part1.mp4"
    mp4.parent.mkdir(parents=True)
    mp4.write_bytes(b"mp4")
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    old_absolute = "/Users/old/learn/anime-armory/创作区/制漫剧/测试剧/出视频/第1集/视频/Clip_02_part1.mp4"
    prefixed_relative = "创作区/制漫剧/测试剧/出视频/第1集/视频/Clip_02_part1.mp4"
    assert gate._event_asset_rel(str(root), {"generation": {"asset": old_absolute}}) == "出视频/第1集/视频/Clip_02_part1.mp4"
    assert gate._asset_matches(str(root), prefixed_relative, "出视频/第1集/视频/Clip_02_part1.mp4")
    (prod / "production_events.jsonl").write_text(json.dumps({
        "episode": "第1集",
        "stage": "video",
        "event": "generation",
        "generation": {"asset": old_absolute, "status": "pass"},
        "meta": {
            "provider": "dreamina",
            "model": "dreamina:3.0",
            "channel": "dreamina",
            "route_hash": "route-sha",
            "capability_evidence_id": "video_backend_capabilities/dreamina",
            "recipe_hash": "recipe-video",
            "prompt_sha256": "prompt-video",
            "reference_bundle_sha256": "ref-video",
            "backend_version": "3.0",
            "quality_tier": "720p",
            "actual_image_inputs": ["出图/第1集/图片/Clip02_first.png"],
            "seed_effective": False,
            "seed_support": "unsupported_or_unknown",
        },
    }, ensure_ascii=False) + "\n", encoding="utf-8")

    gate.check_generation_recipe_evidence(str(root), "第1集", "review")

    assert not any(f["dim"] == "生成配方证据" for f in gate.findings)


def test_translation_glossary_release_gate_blocks_missing_file(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    sub = root / "脚本" / "第1集" / "字幕_英文.srt"
    sub.parent.mkdir(parents=True)
    sub.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")

    gate.check_translation_glossary_release_gate(str(root), "第1集", "review")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "译名发布闸门" for f in gate.findings)


def test_translation_glossary_release_gate_requires_category_coverage(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    sub = root / "脚本" / "第1集" / "字幕_英文.srt"
    glossary = root / "设定库" / "translation_glossary.json"
    sub.parent.mkdir(parents=True)
    glossary.parent.mkdir(parents=True)
    sub.write_text("English subtitle", encoding="utf-8")
    glossary.write_text(json.dumps({"terms": [{"cn": "沈念", "en": "Shen Nian", "category": "人名"}]}, ensure_ascii=False), encoding="utf-8")

    gate.check_translation_glossary_release_gate(str(root), "第1集", "review")

    assert any("缺覆盖类目" in f["msg"] for f in gate.findings)


def test_translation_glossary_release_gate_passes_with_coverage(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    sub = root / "脚本" / "第1集" / "字幕_英文.srt"
    glossary = root / "设定库" / "translation_glossary.json"
    sub.parent.mkdir(parents=True)
    glossary.parent.mkdir(parents=True)
    sub.write_text("English subtitle", encoding="utf-8")
    glossary.write_text(json.dumps({
        "terms": [{"cn": "沈念", "en": "Shen Nian", "category": "人名"}],
        "coverage": {
            "人名": "ready",
            "称谓": "not_applicable",
            "境界": "not_applicable",
            "招式": "not_applicable",
            "口头禅": "not_applicable",
            "系统提示语": "not_applicable",
        },
    }, ensure_ascii=False), encoding="utf-8")

    gate.check_translation_glossary_release_gate(str(root), "第1集", "review")

    assert not any(f["dim"] == "译名发布闸门" for f in gate.findings)


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
| CHAR_02/惊慌护主 小禾 | Clip06 | 无脸部特写，只有 reference_group | 高风险 | MCU/OTS/侧脸/手部/物件反应镜保真实现 |
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


def _write_routes(root, route, ep="第1集", **data_overrides):
    prompt_dir = root / "出视频" / ep / "prompt"
    prompt_dir.mkdir(parents=True)
    data = {"kind": "n2d_video_model_routes", "routes": [route]}
    data.update(data_overrides)
    (prompt_dir / "video_model_routes.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _record_video_backend_refresh(root, backend="dreamina", channel="", date=None):
    import video_backend_adapter

    return video_backend_adapter.write_refresh_evidence(
        str(root),
        backend,
        channel=channel,
        sources=["unit test official docs/cli evidence"],
        note="unit test verified current video backend capability",
        today=date or dt.date.today().isoformat(),
    )


def _basic_route(**overrides):
    route = {
        "clip_id": "Clip_01",
        "shot_type": "general_motion",
        "primary_backend": "dreamina",
        "fallback_backends": ["seedance", "kling"],
        "mode": "image2video",
        "native_audio_policy": "none",
        "identity_requirement": "reference_group",
        "clip_characters": [{"character_id": "CHAR_X", "form": "常态"}],
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


def _flight_action_choreography():
    return {
        "required": True,
        "shot_type": "flight",
        "beat_model": "takeoff_cruise_maneuver_arrival",
        "required_fields": [
            "beats", "speed_curve", "spatial_path", "camera_path", "readability_beats", "degrade_plan",
            "keyframe_plan", "post_cue_points", "physics_guard",
            "flight_path", "altitude_curve", "pose_lock", "parallax_layers", "mount_or_cloud_lock",
        ],
        "failure_modes": ["pose_drift", "altitude_curve_drift"],
        "gate_policy": "block_prompt_without_action_choreography_contract",
    }


def _vehicle_action_choreography(required_fields=None):
    return {
        "required": True,
        "shot_type": "vehicle_ride",
        "beat_model": "vehicle_establish_rolling_stop",
        "required_fields": required_fields or [
            "beats", "speed_curve", "spatial_path", "camera_path", "readability_beats", "degrade_plan",
            "keyframe_plan", "post_cue_points", "physics_guard",
            "vehicle_lock", "wheel_rotation", "harness_lock", "screen_direction", "parallax_layers",
        ],
        "failure_modes": ["vehicle_shape_drift", "wheel_count_or_rotation_error", "harness_morph"],
        "gate_policy": "block_prompt_without_action_choreography_contract",
    }


def _road_vehicle_action_choreography(required_fields=None):
    return {
        "required": True,
        "shot_type": "road_vehicle",
        "beat_model": "vehicle_establish_traffic_brake",
        "required_fields": required_fields or [
            "beats", "speed_curve", "spatial_path", "camera_path", "readability_beats", "degrade_plan",
            "keyframe_plan", "post_cue_points", "physics_guard",
            "vehicle_lock", "wheel_rotation", "driver_control_lock", "lane_lock",
            "traffic_flow", "screen_direction", "parallax_layers",
        ],
        "failure_modes": ["vehicle_shape_drift", "wheel_rotation_error", "lane_drift"],
        "gate_policy": "block_prompt_without_action_choreography_contract",
    }


def test_action_choreography_route_required_for_high_action_route():
    route = _basic_route(shot_type="flight", action_choreography=None)

    gate.check_action_choreography_route(route, "routes.json", 1)

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "动作编排" and "action_choreography" in f["msg"] for f in gate.findings)


def test_action_choreography_route_full_contract_passes():
    route = _basic_route(shot_type="flight", action_choreography=_flight_action_choreography())

    gate.check_action_choreography_route(route, "routes.json", 1)

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "动作编排" for f in gate.findings)


def test_action_choreography_route_blocks_missing_vehicle_specific_field():
    fields = [
        "beats", "speed_curve", "spatial_path", "camera_path", "readability_beats", "degrade_plan",
        "keyframe_plan", "post_cue_points", "physics_guard",
        "vehicle_lock", "harness_lock", "screen_direction", "parallax_layers",
    ]
    route = _basic_route(shot_type="vehicle_ride", action_choreography=_vehicle_action_choreography(fields))

    gate.check_action_choreography_route(route, "routes.json", 1)

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "动作编排" and "wheel_rotation" in f["msg"] for f in gate.findings)


def test_action_choreography_route_blocks_missing_road_vehicle_field():
    fields = [
        "beats", "speed_curve", "spatial_path", "camera_path", "readability_beats", "degrade_plan",
        "keyframe_plan", "post_cue_points", "physics_guard",
        "vehicle_lock", "wheel_rotation", "driver_control_lock", "traffic_flow", "screen_direction", "parallax_layers",
    ]
    route = _basic_route(shot_type="road_vehicle", action_choreography=_road_vehicle_action_choreography(fields))

    gate.check_action_choreography_route(route, "routes.json", 1)

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "动作编排" and "lane_lock" in f["msg"] for f in gate.findings)


def test_long_duration_route_blocks_before_paid_video(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _write_routes(root, _basic_route(risk_flags=["long_duration"]))

    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    finding = next(f for f in gate.findings if f["dim"] == "单Clip时长")
    assert finding["sev"] == gate.BLOCK
    assert finding["return_to_stage"] == "script_stage2"
    assert "storyboard.json" in " ".join(finding["affected_artifacts"])


def test_long_duration_route_with_supported_segment_relay_passes_duration_gate(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    route = _basic_route(
        primary_backend="seedance",
        fallback_backends=["dreamina"],
        max_clip_seconds=15,
        risk_flags=["duration_segment_relay"],
        duration_segment_relay={
            "required": True,
            "supported": True,
            "max_clip_seconds": 15,
            "clip_seconds": 18.5,
            "max_segment_seconds": 14.5,
            "segments": [
                {"segment_id": "Clip_01_seg01", "duration_sec": 4.0, "from_frame": "first_frame", "to_frame": "mid_anchor_1"},
                {"segment_id": "Clip_01_seg02", "duration_sec": 14.5, "from_frame": "mid_anchor_1", "to_frame": "end_frame"},
            ],
        },
        execution_recipe={
            "video_segments": {
                "required": True,
                "mode": "first_last_relay",
                "segments": [
                    {"segment_id": "Clip_01_seg01", "duration_sec": 4.0, "from_frame": "first_frame", "to_frame": "mid_anchor_1"},
                    {"segment_id": "Clip_01_seg02", "duration_sec": 14.5, "from_frame": "mid_anchor_1", "to_frame": "end_frame"},
                ],
            }
        },
    )
    _write_routes(root, route)
    _record_video_backend_refresh(root, backend="seedance")
    _record_video_backend_refresh(root, backend="dreamina")

    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert not any(f["dim"] == "单Clip时长" for f in gate.findings)


def test_video_model_routes_require_fresh_backend_evidence(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _write_routes(root, _basic_route(primary_backend="veo", fallback_backends=[]))

    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "生视频后端适配" and "record-refresh" in f["msg"] for f in gate.findings)


def test_video_model_routes_fresh_backend_evidence_passes_refresh_gate(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _record_video_backend_refresh(root, "veo")
    _write_routes(root, _basic_route(primary_backend="veo", fallback_backends=[]))

    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "生视频后端适配" for f in gate.findings)


def test_video_model_routes_blocks_fresh_evidence_when_paid_routing_not_allowed(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("- 生视频渠道: Dreamina\n", encoding="utf-8")
    _record_video_backend_refresh(root, "kling", channel="Dreamina")
    _record_video_backend_refresh(root, "seedance", channel="Dreamina")
    _write_routes(root, _basic_route(primary_backend="kling", fallback_backends=["seedance"]))

    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert any(
        f["sev"] == gate.BLOCK
        and f["dim"] == "生视频后端适配"
        and "不可自动付费路由" in str(f["msg"])
        for f in gate.findings
    )


def test_video_model_routes_identity_route_requires_clip_characters(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _write_routes(root, _basic_route(clip_characters=[]))

    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "模型路由" and "clip_characters" in str(f["msg"])
               for f in gate.findings)


def test_native_av_speech_route_without_native_or_voice_fallback_blocks(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    _settings(root, "原生音画")
    _write_routes(root, _basic_route(shot_type="dialogue_closeup", risk_flags=["mouth_visible"]))

    gate.findings.clear()
    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert any(
        f["sev"] == gate.BLOCK and f["dim"] == "原生音画降级" and "requires_voice_fallback" in f["msg"]
        for f in gate.findings
    )


def test_native_av_voice_fallback_requires_real_voice_manifest(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    _settings(root, "原生音画")
    _write_routes(
        root,
        _basic_route(
            shot_type="dialogue_closeup",
            risk_flags=["mouth_visible"],
            requires_voice_fallback=True,
            fallback_production_mode="voice_first",
        ),
    )

    gate.findings.clear()
    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert any(
        f["sev"] == gate.BLOCK and f["dim"] == "原生音画降级" and f["return_to_stage"] == "voice"
        for f in gate.findings
    )

    _voice_manifest(root, placeholder=False)
    gate.findings.clear()
    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "原生音画降级" for f in gate.findings)


def test_speech_route_requires_mouth_visible_audit_sidecar(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _write_routes(root, _basic_route(shot_type="dialogue_closeup", risk_flags=["mouth_visible"]))

    gate.findings.clear()
    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "mouth_visible证据" for f in gate.findings)


def test_mouth_visible_audit_warn_blocks_paid_video(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _write_routes(root, _basic_route(shot_type="dialogue_closeup", risk_flags=["mouth_visible"]))
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (prod / "mouth_visible_audit_第1集.json").write_text(
        json.dumps({
            "kind": "n2d_mouth_visible_audit",
            "episode": "第1集",
            "rows": [{"clip_id": "Clip_01", "verdict": "warn", "message": "图上嘴可见=yes 但 prompt=no"}],
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    gate.findings.clear()
    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert any(
        f["sev"] == gate.BLOCK and f["dim"] == "mouth_visible证据" and "Clip_01" in f["msg"]
        for f in gate.findings
    )


def test_video_model_routes_ep2_requires_baseline_for_identity_route(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _write_routes(root, _basic_route(primary_backend="veo", fallback_backends=[]), ep="第2集")

    gate.check_video_model_routes(str(root), "第2集", "## 本集模型路由表\n", "00_总览.md")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "后端跨集锁" and "model_routes_baseline.json" in str(f["msg"])
               for f in gate.findings)


def test_video_model_routes_baseline_drift_blocks_for_high_risk(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    (root / "设定库").mkdir(parents=True)
    (root / "设定库" / "model_routes_baseline.json").write_text(
        json.dumps({"kind": "n2d_model_routes_baseline", "shot_type_backends": {"action_fight": "kling"}}),
        encoding="utf-8",
    )
    route = _basic_route(
        clip_id="Clip_01",
        shot_type="action_fight",
        primary_backend="kling",
        fallback_backends=[],
        risk_flags=["contact_motion"],
    )
    _write_routes(
        root,
        route,
        ep="第2集",
        baseline_anchored=True,
        baseline_drift=[{"clip_id": "Clip_01", "shot_type": "action_fight", "was": "seedance", "now": "kling"}],
    )

    gate.check_video_model_routes(str(root), "第2集", "## 本集模型路由表\n", "00_总览.md")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "后端跨集锁" and "baseline_override" in str(f["msg"])
               for f in gate.findings)


def test_video_model_routes_baseline_override_downgrades_drift_to_warn(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    (root / "设定库").mkdir(parents=True)
    (root / "设定库" / "model_routes_baseline.json").write_text("{}", encoding="utf-8")
    route = _basic_route(clip_id="Clip_01", shot_type="action_fight", fallback_backends=[], risk_flags=["contact_motion"])
    _write_routes(
        root,
        route,
        ep="第2集",
        baseline_anchored=True,
        baseline_override={
            "accepted": True,
            "reviewer": "qa",
            "reason": "本集换成动作专用后端，已人工确认角色一致性",
            "expires_at": "2099-01-01",
            "affected_routes": ["Clip_01"],
        },
        baseline_drift=[{"clip_id": "Clip_01", "shot_type": "action_fight", "was": "seedance", "now": "dreamina"}],
    )

    gate.check_video_model_routes(str(root), "第2集", "## 本集模型路由表\n", "00_总览.md")

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "后端跨集锁" for f in gate.findings)
    assert any(f["sev"] == gate.WARN and f["dim"] == "后端跨集锁" for f in gate.findings)


def test_video_model_routes_missing_backend_scope_blocks_mixed_primary_backends(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prompt_dir = root / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    routes = [
        _basic_route(clip_id="Clip_01", primary_backend="dreamina"),
        _basic_route(clip_id="Clip_02", primary_backend="kling"),
    ]
    (prompt_dir / "video_model_routes.json").write_text(
        json.dumps({"kind": "n2d_video_model_routes", "routes": routes}, ensure_ascii=False),
        encoding="utf-8",
    )

    gate.findings.clear()
    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "后端一致性作用域(BSCOPE)" for f in gate.findings)


def test_video_model_routes_accepts_backend_scope_and_requires_action_identity_plan(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    route = _basic_route(
        shot_type="action_fight",
        risk_flags=["contact_motion"],
        motion_control={
            "level": "required",
            "required": True,
            "manifest_required": True,
            "manifest_path": "生产数据/motion_control/Clip_01.json",
            "required_inputs": ["pose_sequence"],
            "backend_control_level": "medium",
            "failure_modes": ["feature_melting"],
            "gate_policy": "block_without_ready_manifest_or_degrade_only_manifest",
            "degrade_allowed": True,
        },
    )
    _write_routes(
        root,
        route,
        backend_consistency_scope={
            "image_generation": "single_model_channel_per_project",
            "video_generation": "per_clip_allowed_with_baseline",
            "required_guards": ["model_routes_baseline", "identity_handoff", "execution_recipe", "post_video_qc"],
        },
    )

    gate.findings.clear()
    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert not any(f["dim"] == "后端一致性作用域(BSCOPE)" for f in gate.findings)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "动作身份优先级" for f in gate.findings)


def test_video_model_routes_legacy_baseline_reason_no_longer_overrides(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    (root / "设定库").mkdir(parents=True)
    (root / "设定库" / "model_routes_baseline.json").write_text("{}", encoding="utf-8")
    route = _basic_route(clip_id="Clip_01", shot_type="action_fight", fallback_backends=[], risk_flags=["contact_motion"])
    _write_routes(
        root,
        route,
        ep="第2集",
        baseline_anchored=True,
        baseline_override_reason="旧式自由文本原因不应放行",
        baseline_drift=[{"clip_id": "Clip_01", "shot_type": "action_fight", "was": "seedance", "now": "dreamina"}],
    )

    gate.check_video_model_routes(str(root), "第2集", "## 本集模型路由表\n", "00_总览.md")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "后端跨集锁" and "结构化 baseline_override" in str(f["msg"])
               for f in gate.findings)


def test_video_model_routes_blocks_fresh_evidence_without_required_capability(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    _record_video_backend_refresh(root, "veo")
    evidence = root / "生产数据" / "video_backend_capabilities" / "veo.json"
    data = json.loads(evidence.read_text(encoding="utf-8"))
    data["capability_assertions"]["supports_last_frame"]["value"] = False
    evidence.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    route = _basic_route(
        primary_backend="veo",
        fallback_backends=[],
        anchor_consumption={"need_end": True, "anchor_count": 0, "consumption_mode": "first_last"},
    )
    _write_routes(root, route)

    gate.check_video_model_routes(str(root), "第1集", "## 本集模型路由表\n", "00_总览.md")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "生视频后端适配" and "supports_last_frame" in str(f["msg"])
               for f in gate.findings)


def test_route_capability_gaps_use_supported_segment_relay_duration():
    route = _basic_route(
        clip_id="Clip_01",
        clip_seconds=18.5,
        duration_segment_relay={
            "supported": True,
            "max_segment_seconds": 14.5,
        },
    )
    assertions = {
        "max_clip_seconds": 15,
        "supports_first_frame": True,
        "identity_mechanism": "face_lock",
    }

    gaps = gate._route_capability_assertion_gaps(route, assertions, "primary")

    assert not any("max_clip_seconds" in item for item in gaps)


def test_route_capability_gaps_allow_lipsync_fallback_degrade_path():
    route = _basic_route(native_audio_policy="lipsync_condition_only")
    assertions = {
        "max_clip_seconds": 15,
        "supports_first_frame": True,
        "lipsync_audio_ref": False,
        "identity_mechanism": "first_frame_or_reference_group",
    }

    gaps = gate._route_capability_assertion_gaps(route, assertions, "fallback")

    assert not any("口型音频参考" in item for item in gaps)


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


def test_native_av_compose_foley_full_warns_when_not_forced(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    route_dir = root / "出视频" / "第1集" / "prompt"
    work = root / "合成" / "第1集" / "_work"
    route_dir.mkdir(parents=True)
    work.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 制作模式: 原生音画\n", encoding="utf-8")
    (route_dir / "video_model_routes.json").write_text(json.dumps({
        "routes": [{"clip_id": "Clip_01", "primary_backend": "Veo 3.1", "native_audio_policy": "native_speech", "mode": "native_av"}],
    }, ensure_ascii=False), encoding="utf-8")
    (work / "foley_render_policy.json").write_text(json.dumps({
        "kind": "n2d_foley_render_policy",
        "mode": "full",
        "reason": "silent_backend:compose_foley_provides_sfx",
        "force_compose_foley": False,
        "strategy": "自动",
    }, ensure_ascii=False), encoding="utf-8")

    gate.check_compose_foley_native_audio_policy(str(root), "第1集")

    assert any(f["sev"] == gate.WARN and f["dim"] == "后期拟音" and "双层拟音" in f["msg"] for f in gate.findings)


def test_native_av_compose_foley_full_forced_is_allowed(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    route_dir = root / "出视频" / "第1集" / "prompt"
    work = root / "合成" / "第1集" / "_work"
    route_dir.mkdir(parents=True)
    work.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 制作模式: 原生音画\n", encoding="utf-8")
    (route_dir / "video_model_routes.json").write_text(json.dumps({
        "routes": [{"clip_id": "Clip_01", "primary_backend": "Veo 3.1", "native_audio_policy": "native_speech", "mode": "native_av"}],
    }, ensure_ascii=False), encoding="utf-8")
    (work / "foley_render_policy.json").write_text(json.dumps({
        "kind": "n2d_foley_render_policy",
        "mode": "full",
        "reason": "forced:FORCE_COMPOSE_FOLEY",
        "force_compose_foley": True,
        "strategy": "自动",
    }, ensure_ascii=False), encoding="utf-8")

    gate.check_compose_foley_native_audio_policy(str(root), "第1集")

    assert not any(f["dim"] == "后期拟音" for f in gate.findings)


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


def test_stylized_face_encoder_policy_warns_without_styleid(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text(
        "# _设置\n- 基础视觉风格: 二次元赛璐璐\n- 脸一致性机检后端: arcface\n",
        encoding="utf-8",
    )

    gate.check_stylized_face_encoder_policy(str(root))

    # 铁律 B11：风格化项目 StyleID 发布闸 demo 也要求——缺 StyleID 且无结构化签收=BLOCK（曾 demo 只 WARN）。
    assert any(
        f["sev"] == gate.BLOCK and f["dim"] == "风格化脸机检"
        for f in gate.findings
    )


def test_stylized_face_encoder_policy_blocks_release_without_styleid(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text(
        "# _设置\n- 基础视觉风格: 国漫写实\n- 脸一致性机检后端: arcface\n- 一致性严格度: production\n",
        encoding="utf-8",
    )

    gate.check_stylized_face_encoder_policy(str(root), "第1集", "image_preflight")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "风格化脸机检" for f in gate.findings)


def test_stylized_face_encoder_policy_allows_structured_release_signoff(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (root / "_设置.md").write_text(
        "# _设置\n- 基础视觉风格: 水墨国风\n- 脸一致性机检后端: arcface\n- 一致性严格度: production\n",
        encoding="utf-8",
    )
    (prod / "styleid_release_signoff_第1集.json").write_text(json.dumps({
        "kind": "n2d_styleid_release_signoff",
        "accepted": True,
        "reviewer": "qa",
        "reason": "本批只做内部交付，已加近景人审",
        "expires_at": "2999-01-01",
    }, ensure_ascii=False), encoding="utf-8")

    gate.check_stylized_face_encoder_policy(str(root), "第1集", "image_preflight")

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "风格化脸机检" for f in gate.findings)
    assert any(f["sev"] == gate.WARN and f["dim"] == "风格化脸机检" for f in gate.findings)


def test_stylized_face_encoder_policy_passes_with_styleid_model(tmp_path, monkeypatch):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    model = tmp_path / "styleid.ckpt"
    model.write_text("stub", encoding="utf-8")
    monkeypatch.setenv("N2D_STYLEID_MODEL", str(model))
    (root / "_设置.md").write_text(
        "# _设置\n- 基础视觉风格: 水墨国风\n- 脸一致性机检后端: styleid\n",
        encoding="utf-8",
    )

    gate.check_stylized_face_encoder_policy(str(root))

    assert not any(f["dim"] == "风格化脸机检" for f in gate.findings)


def test_stylized_face_encoder_policy_reads_styleid_model_from_project_settings(tmp_path, monkeypatch):
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    monkeypatch.delenv("N2D_STYLEID_MODEL", raising=False)
    monkeypatch.setenv("N2D_ALLOW_MODEL_DOWNLOAD", "1")
    (root / "_设置.md").write_text(
        "# _设置\n- 基础视觉风格: 国漫写实\n- 脸一致性机检后端: styleid\n- N2D_STYLEID_MODEL: kwanY/styleid\n",
        encoding="utf-8",
    )

    gate.check_stylized_face_encoder_policy(str(root), "第1集", "image_preflight")

    assert not any(f["dim"] == "风格化脸机检" for f in gate.findings)


def test_storyboard_possession_gate_warns_for_prop_holder_without_ledger(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    sb_dir = root / "脚本" / "第1集"
    sb_dir.mkdir(parents=True)
    (sb_dir / "storyboard.json").write_text(json.dumps({
        "clips": [{
            "id": "Clip_01",
            "action": "CHAR_01 手持 PROP_团扇 走向床榻",
        }]
    }, ensure_ascii=False), encoding="utf-8")

    gate.check_storyboard_possession_gate(str(root), "第1集")

    assert any(f["sev"] == gate.WARN and f["dim"] == "持有账本(POS)" for f in gate.findings)


def test_storyboard_possession_gate_blocks_prop_transfer_without_ledger(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    sb_dir = root / "脚本" / "第1集"
    sb_dir.mkdir(parents=True)
    (sb_dir / "storyboard.json").write_text(json.dumps({
        "clips": [{
            "id": "Clip_02",
            "action": "CHAR_01 将 PROP_毒酒杯 递给 CHAR_02",
        }]
    }, ensure_ascii=False), encoding="utf-8")

    gate.check_storyboard_possession_gate(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "持有账本(POS)" for f in gate.findings)


def test_storyboard_possession_gate_blocks_core_weapon_holder_without_ledger(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    sb_dir = root / "脚本" / "第1集"
    sb_dir.mkdir(parents=True)
    (sb_dir / "storyboard.json").write_text(json.dumps({
        "clips": [{
            "id": "Clip_03",
            "action": "CHAR_01 手持 PROP_本命飞剑 在云端御剑飞行",
        }]
    }, ensure_ascii=False), encoding="utf-8")

    gate.check_storyboard_possession_gate(str(root), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "持有账本(POS)" for f in gate.findings)


def test_storyboard_possession_gate_allows_existing_ledger(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    sb_dir = root / "脚本" / "第1集"
    prod = root / "生产数据"
    sb_dir.mkdir(parents=True)
    prod.mkdir(parents=True)
    (sb_dir / "storyboard.json").write_text(json.dumps({
        "clips": [{
            "id": "Clip_02",
            "action": "CHAR_01 将 PROP_毒酒杯 递给 CHAR_02",
        }]
    }, ensure_ascii=False), encoding="utf-8")
    (prod / "possession_ledger_第1集.json").write_text('{"events":[]}\n', encoding="utf-8")

    gate.check_storyboard_possession_gate(str(root), "第1集")

    assert not any(f["dim"] == "持有账本(POS)" for f in gate.findings)


def test_native_av_placeholder_not_blocked(tmp_path):
    # 制作模式=原生音画：说话镜不靠配音，占位/缺配音不应 BLOCK
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n\n## 选择\n- 制作模式: 原生音画\n", encoding="utf-8")
    gate.check_placeholder_policy(str(root), "第1集", "video")
    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "配音" for f in gate.findings)


def _write_production_settings(root: Path, *, mode: str = "配音先行", image_backend: str = "Codex",
                               image_model: str = "GPT Image 2") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "_设置.md").write_text(
        f"- 制作模式: {mode}\n"
        "- 一致性严格度: production\n"
        f"- 生图AI: {image_backend}\n"
        f"- 生图模型: {image_model}\n",
        encoding="utf-8",
    )


def _write_core_identity(root: Path, *, expression: bool = True, lock: bool = True,
                         image2image_lock: bool = False) -> None:
    path = Path(gate.identity_registry_path(str(root)))
    path.parent.mkdir(parents=True, exist_ok=True)
    form = {
        "form": "常态",
        "reference_group": {
            "front": "出图/共享/图片/定妆_沈念.png",
            "side": "出图/共享/图片/定妆_沈念_侧.png",
            "three_quarter": "出图/共享/图片/定妆_沈念_45.png",
            "back": "出图/共享/图片/定妆_沈念_背.png",
            "half_body": "出图/共享/图片/定妆_沈念_半身.png",
        },
        "identity_adapters": {"image": {}},
    }
    if expression:
        form["reference_group"]["expressions"] = [
            {"emotion": "中性", "path": "出图/共享/图片/定妆_沈念_表情_中性.png", "status": "ready"}
        ]
    if lock:
        form["identity_adapters"]["face_embedding"] = {"status": "ready"}
    if image2image_lock:
        form["identity_adapters"]["image"]["codex"] = {
            "mode": "image2image_reference_chain",
            "status": "ready",
            "actual_image_input_required": True,
            "reference_manifest_required": True,
            "full_qc_required": True,
        }
    path.write_text(json.dumps({
        "kind": "n2d_identity_registry",
        "characters": [{"id": "CHAR_SHEN", "name": "沈念", "tier": "主角", "scope": "贯穿全篇", "forms": [form]}],
    }, ensure_ascii=False), encoding="utf-8")


def test_production_video_first_placeholder_warns_before_compose_and_blocks_delivery(tmp_path):
    root = tmp_path / "work"
    _write_production_settings(root, mode="先出视频后配音")
    _voice_manifest(root, placeholder=True)

    gate.findings.clear()
    gate.check_placeholder_policy(str(root), "第1集", "video")

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "配音" for f in gate.findings)
    assert any(f["sev"] == gate.WARN and f["dim"] == "配音" and "先出视频后配音" in f["msg"]
               for f in gate.findings)

    gate.findings.clear()
    gate.check_placeholder_policy(str(root), "第1集", "compose")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "配音" and "rough demo" in f["msg"]
               for f in gate.findings)


def test_production_core_identity_requires_expression_and_lock(tmp_path):
    root = tmp_path / "work"
    _write_production_settings(root)
    _write_core_identity(root, expression=False, lock=False)

    gate.findings.clear()
    gate.check_production_core_identity_lock(str(root), "第1集", "image_preflight")

    msgs = [f["msg"] for f in gate.findings if f["sev"] == gate.BLOCK and f["dim"] == "核心角色一致性"]
    assert any("缺表情库" in msg for msg in msgs)
    assert any("缺执行层身份锁" in msg for msg in msgs)


def test_production_core_identity_allows_expression_plus_face_embedding(tmp_path):
    root = tmp_path / "work"
    _write_production_settings(root)
    _write_core_identity(root, expression=True, lock=True)

    gate.findings.clear()
    gate.check_production_core_identity_lock(str(root), "第1集", "image_preflight")

    assert not any(f["dim"] == "核心角色一致性" for f in gate.findings)


def test_production_core_identity_allows_expression_plus_image2image_chain(tmp_path):
    root = tmp_path / "work"
    _write_production_settings(root)
    _write_core_identity(root, expression=True, lock=False, image2image_lock=True)

    gate.findings.clear()
    gate.check_production_core_identity_lock(str(root), "第1集", "image_preflight")

    assert not any(f["dim"] == "核心角色一致性" for f in gate.findings)


def test_image_backend_baseline_missing_blocks_production(tmp_path):
    root = tmp_path / "work"
    _write_production_settings(root)

    gate.findings.clear()
    gate.check_image_backend_baseline(str(root), "第1集", "image_preflight")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "生图后端基线" and "record-baseline" in f["msg"]
               for f in gate.findings)


def test_image_backend_baseline_switch_with_outputs_blocks(tmp_path):
    root = tmp_path / "work"
    _write_production_settings(root, image_backend="Codex", image_model="GPT Image 2")
    gate.image_backend_adapter.write_image_backend_baseline(str(root))
    _write_production_settings(root, image_backend="Seedream", image_model="Seedream 4.5")
    _mk_png(root, "第1集", "Clip_01.png")

    gate.findings.clear()
    gate.check_image_backend_baseline(str(root), "第1集", "image_preflight")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "生图后端基线" and "重制计划" in f["msg"]
               for f in gate.findings)


def test_keyshot_plan_missing_blocks_production_preflight(tmp_path):
    root = tmp_path / "work"
    _write_production_settings(root)
    _seed_video_prompt(root, "第1集", "", storyboard={
        "clips": [{"id": "Clip_01", "description": "封面冷开场，主角当众打脸宿敌。"}]
    })

    gate.findings.clear()
    gate.check_keyshot_candidate_plan(str(root), "第1集", "image_preflight")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "关键镜候选" and "K>=3" in f["msg"]
               for f in gate.findings)


def test_keyshot_selection_under_k_blocks_production_image(tmp_path):
    root = tmp_path / "work"
    _write_production_settings(root)
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (prod / "keyshot_candidate_plan_第1集.json").write_text(json.dumps({
        "kind": "n2d_keyshot_candidate_plan",
        "keyshots": [{"clip": "Clip_01", "candidate_count": 3}],
    }, ensure_ascii=False), encoding="utf-8")
    (prod / "candidate_selection_第1集.json").write_text(json.dumps({
        "kind": "n2d_candidate_selection",
        "rows": [{"clip": "Clip_01", "candidate_count": 1, "picked": {"candidate": "candidate_01"}}],
    }, ensure_ascii=False), encoding="utf-8")

    gate.findings.clear()
    gate.check_keyshot_candidate_plan(str(root), "第1集", "image")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "关键镜候选" and "候选不足" in f["msg"]
               for f in gate.findings)


def test_keyshot_selection_requires_real_candidate_files(tmp_path):
    root = tmp_path / "work"
    _write_production_settings(root)
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (prod / "keyshot_candidate_plan_第1集.json").write_text(json.dumps({
        "kind": "n2d_keyshot_candidate_plan",
        "keyshots": [{"clip": "Clip_01", "candidate_count": 3}],
    }, ensure_ascii=False), encoding="utf-8")
    (prod / "candidate_selection_第1集.json").write_text(json.dumps({
        "kind": "n2d_candidate_selection",
        "rows": [{"clip": "Clip_01", "candidate_count": 3, "picked": {"candidate": "candidate_01"}}],
    }, ensure_ascii=False), encoding="utf-8")

    gate.findings.clear()
    gate.check_keyshot_candidate_plan(str(root), "第1集", "image")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "关键镜候选" and "终选候选文件不存在" in f["msg"]
               for f in gate.findings)


def test_keyshot_selection_with_real_candidates_passes_production_image(tmp_path):
    root = tmp_path / "work"
    _write_production_settings(root)
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    cdir = root / "出图" / "第1集" / "候选" / "Clip_01"
    cdir.mkdir(parents=True)
    for idx in range(1, 4):
        (cdir / f"candidate_{idx:02d}.png").write_bytes(_TEST_PNG_BYTES)
    (prod / "keyshot_candidate_plan_第1集.json").write_text(json.dumps({
        "kind": "n2d_keyshot_candidate_plan",
        "keyshots": [{"clip": "Clip_01", "candidate_count": 3}],
    }, ensure_ascii=False), encoding="utf-8")
    (prod / "candidate_selection_第1集.json").write_text(json.dumps({
        "kind": "n2d_candidate_selection",
        "rows": [{
            "clip": "Clip_01",
            "candidate_count": 3,
            "picked": {
                "candidate": "candidate_01",
                "rel": "出图/第1集/候选/Clip_01/candidate_01.png",
            },
        }],
    }, ensure_ascii=False), encoding="utf-8")

    gate.findings.clear()
    gate.check_keyshot_candidate_plan(str(root), "第1集", "image")

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "关键镜候选" for f in gate.findings)


def test_consistency_ledger_gate_blocks_on_block_or_high(tmp_path, monkeypatch):
    import sys
    import types

    fake = types.SimpleNamespace(run=lambda root, ep: {
        "counts": {"block": 1, "high": 0, "medium": 2},
        "delivery_surface": {"status": "blocked"},
    })
    monkeypatch.setitem(sys.modules, "consistency_ledger", fake)

    gate.findings.clear()
    gate.check_consistency_ledger_gate(str(tmp_path), "第1集")

    assert any(f["sev"] == gate.BLOCK and f["dim"] == "验收总账" and "block=1" in f["msg"]
               for f in gate.findings)


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
    (tmp_path / "_设置.md").write_text("- 制作模式: 配音先行\n", encoding="utf-8")
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
            "form": "常态",
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


def test_route_identity_fallback_losing_core_lock_blocks(tmp_path):
    # primary 已在原生锁后端，但失败重试 fallback 只有 reference_group，也会在真实执行时丢锁。
    forms = [_form("沈念", "核心", {"kling": ("character_id", True), "seedance": ("fallback_reference_group", True)})]
    routes = [{"clip_id": "Clip_01", "primary_backend": "kling", "fallback_backends": ["seedance"]}]
    root = _write_routes_and_matrix(tmp_path, routes, forms)
    gate.findings.clear()
    gate.check_route_identity_readiness(root, "第1集")
    blocks = [f for f in gate.findings if f["dim"] == "换后端丢锁" and f["sev"] == gate.BLOCK]
    assert blocks and "fallback" in blocks[0]["msg"] and "seedance" in blocks[0]["msg"]


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


def test_route_identity_scope_uses_clip_characters_only(tmp_path):
    forms = [
        _form("沈念", "核心", {"seedance": ("reference_group", True)}),
        {"character_name": "柳娘子", "character_id": "CHAR_Y", "scope": "核心", "form": "常态",
         "video_bindings": {"kling": {"binding": "character_id", "ready": True},
                            "seedance": {"binding": "fallback_reference_group", "ready": True}}},
    ]
    routes = [{"clip_id": "Clip_01", "primary_backend": "seedance",
               "clip_characters": [{"character_id": "CHAR_X", "form": "常态"}]}]
    root = _write_routes_and_matrix(tmp_path, routes, forms)
    gate.findings.clear()
    gate.check_route_identity_readiness(root, "第1集")
    assert not any(f["dim"] == "换后端丢锁" and "柳娘子" in str(f["msg"]) for f in gate.findings)


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


def test_check_shot_scale_progression_warns_unparseable_lens(tmp_path):
    # G：lens 写了但非标准景别词（抽不出分级）→ 单调性机检静默失效，补一条 warn 提示规范 lens
    gate.findings.clear()
    root = tmp_path / "work"
    ep = "第1集"
    _write_scale_sb(root, ep, [
        {"id": "Clip_01", "shots": [{"lens": "手持跟拍 缓推"}]},     # 无景别词 → None
        {"id": "Clip_02", "shots": [{"lens": "固定机位 微晃"}]},     # 无景别词 → None
        {"id": "Clip_03", "shots": [{"lens": "LS 35mm"}]},          # 标准
    ])
    gate.check_shot_scale_progression(str(root), ep)
    unparsed = [f for f in gate.findings if f["dim"] == "景别阶梯" and "抽不出景别分级" in f["msg"]]
    assert len(unparsed) == 1 and unparsed[0]["sev"] == gate.WARN
    assert "Clip_01" in unparsed[0]["loc"] and "Clip_02" in unparsed[0]["loc"]


def test_check_shot_scale_progression_no_unparsed_warn_when_one_offbeat(tmp_path):
    # 只有 1 个非标准 lens（<2）→ 不报（单个可能是有意写法，不噪声）
    gate.findings.clear()
    root = tmp_path / "work"
    ep = "第1集"
    _write_scale_sb(root, ep, [
        {"id": "Clip_01", "shots": [{"lens": "CU 85mm"}]},
        {"id": "Clip_02", "shots": [{"lens": "手持跟拍 缓推"}]},   # 唯一无景别词镜（1 个 <2）
        {"id": "Clip_03", "shots": [{"lens": "LS 35mm"}]},
    ])
    gate.check_shot_scale_progression(str(root), ep)
    assert not [f for f in gate.findings if f["dim"] == "景别阶梯" and "抽不出景别分级" in f["msg"]]


def _seed_pngs_and_qc(root, ep, hard_blocks, qc_present=True, *, precision="full", coverage=None, legacy=False):
    import os, time
    png_dir = root / "出图" / ep / "图片"
    png_dir.mkdir(parents=True, exist_ok=True)
    png = png_dir / "镜头01.png"
    png.write_bytes(b"x")
    qc_path = root / "生产数据" / "image_qc" / ep / f"image_qc_{ep}.json"
    if qc_present:
        qc_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"summary": {"hard_blocks": hard_blocks, "verdict": "block" if hard_blocks else "ok"}}
        if not legacy:
            payload["qc_environment"] = {"precision_level": precision}
            payload["face_reference_coverage"] = coverage or {
                "verdict": "ok", "missing": [], "required": 1, "covered": 1,
            }
            from skill_snapshot import artifact_fingerprint
            payload["inputs_fingerprint"] = artifact_fingerprint(
                str(root),
                [f"出图/{ep}/图片/镜头01.png"],
            )
        qc_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
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


def test_input_frame_qc_blocks_when_no_qc_result(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _seed_pngs_and_qc(root, ep, hard_blocks=0, qc_present=False)
    gate.check_input_frame_qc(str(root), ep)
    blocks = [f for f in gate.findings if f["dim"] == "出图落档QC" and f["sev"] == gate.BLOCK]
    assert len(blocks) == 1 and "未见 image_qc" in blocks[0]["msg"]


def test_image_stage_runs_input_frame_qc_but_preflight_does_not(tmp_path, monkeypatch):
    """崩脸/coverage 像素硬挡此前只挂 video 阶段——出图阶段(生成后 `--stage image`)现在也接，
    但 pre-gen 的 image_preflight 不接(此时还没 PNG/QC 报告)。锁住这个不对称的接线。"""
    root = tmp_path / "work"; root.mkdir()
    ep = "第1集"
    calls = []
    monkeypatch.setattr(gate, "check_input_frame_qc", lambda r, e: calls.append((r, e)))
    # 一致性总审同样只挂出图后 image，不挂 pre-gen——stub 掉避免真跑 consistency_audit 子进程
    monkeypatch.setattr(gate, "check_consistency_audit_gate", lambda r, e, stage="review": None)
    gate.findings.clear()
    gate.run(str(root), ep, "image_preflight")
    assert calls == []  # 生成前不跑首帧落档 QC（无 PNG/报告，避免误 BLOCK）
    gate.findings.clear()
    gate.run(str(root), ep, "image")
    assert calls == [(str(root), ep)]  # 生成后出图闸门即拦崩脸，不拖到最贵的出视频工位


def test_input_frame_qc_passes_when_clean_and_fresh(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _seed_pngs_and_qc(root, ep, hard_blocks=0)
    gate.check_input_frame_qc(str(root), ep)
    assert [f for f in gate.findings if f["dim"] == "出图落档QC"] == []


def test_input_frame_qc_blocks_when_fingerprint_misses_real_pngs(tmp_path):
    """防伪造：freshness 只证明声明文件没变。报告只指纹了 1 张，但磁盘上有 2 张真实落档 PNG（手写/陈旧
    报告特征）——没被机检的那张必须拦下，否则 1 字节假图 + 最小声明就能蒙混过 freshness。"""
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _seed_pngs_and_qc(root, ep, hard_blocks=0)  # 指纹只覆盖 镜头01.png，clean+fresh
    (root / "出图" / ep / "图片" / "镜头02.png").write_bytes(b"y")  # 真实落档但报告没覆盖
    gate.check_input_frame_qc(str(root), ep)
    blocks = [f for f in gate.findings if f["dim"] == "出图落档QC" and f["sev"] == gate.BLOCK]
    assert len(blocks) == 1 and "不在核验范围" in blocks[0]["msg"]


def test_input_frame_qc_blocks_latest_local_face_patch_even_when_qc_clean(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _seed_pngs_and_qc(root, ep, hard_blocks=0)
    _record_image_event(
        root,
        ep,
        "出图/第1集/图片/镜头01.png",
        provider="local_face_patch",
        method="crop_resize_color_match_alpha_blend",
        event="redraw",
    )
    gate.check_input_frame_qc(str(root), ep)
    blocks = [f for f in gate.findings if f["dim"] == "出图落档QC" and f["sev"] == gate.BLOCK]
    assert len(blocks) == 1
    assert "本地贴脸修复产物禁用" in blocks[0]["msg"]
    assert "embedding 分数只是证据" in blocks[0]["msg"]
    assert blocks[0].get("return_to_stage") == "image"


def test_input_frame_qc_blocks_when_qc_stale(tmp_path):
    import os, time
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    png, qc_path = _seed_pngs_and_qc(root, ep, hard_blocks=0)
    # make the PNG newer than the QC result (出图后改过帧未重验)
    future = time.time() + 500
    os.utime(png, (future, future))
    gate.check_input_frame_qc(str(root), ep)
    blocks = [f for f in gate.findings if f["dim"] == "出图落档QC" and f["sev"] == gate.BLOCK]
    assert len(blocks) == 1 and "晚于上次 image_qc" in blocks[0]["msg"]


def test_input_frame_qc_blocks_degraded_qc_precision(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _seed_pngs_and_qc(root, ep, hard_blocks=0, precision="degraded")
    gate.check_input_frame_qc(str(root), ep)
    blocks = [f for f in gate.findings if f["dim"] == "出图落档QC" and f["sev"] == gate.BLOCK]
    assert len(blocks) == 1 and "不是 full" in blocks[0]["msg"]


def test_input_frame_qc_blocks_legacy_qc_without_face_coverage(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _seed_pngs_and_qc(root, ep, hard_blocks=0, legacy=True)
    gate.check_input_frame_qc(str(root), ep)
    blocks = [f for f in gate.findings if f["dim"] == "出图落档QC" and f["sev"] == gate.BLOCK]
    assert len(blocks) == 1 and "face_reference_coverage" in blocks[0]["msg"]


def test_input_frame_qc_blocks_qc_without_inputs_fingerprint(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _png, qc_path = _seed_pngs_and_qc(root, ep, hard_blocks=0)
    data = json.loads(qc_path.read_text(encoding="utf-8"))
    data.pop("inputs_fingerprint", None)
    qc_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    gate.check_input_frame_qc(str(root), ep)
    blocks = [f for f in gate.findings if f["dim"] == "出图落档QC" and f["sev"] == gate.BLOCK]
    assert len(blocks) == 1 and "inputs_fingerprint" in blocks[0]["msg"]


def test_input_frame_qc_blocks_inputs_fingerprint_mismatch(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    png, _qc_path = _seed_pngs_and_qc(root, ep, hard_blocks=0)
    # Keep mtime old enough that the content fingerprint, not the mtime guard, catches this.
    old_mtime = png.stat().st_mtime
    png.write_bytes(b"new-png-content")
    import os
    os.utime(png, (old_mtime, old_mtime))
    gate.check_input_frame_qc(str(root), ep)
    blocks = [f for f in gate.findings if f["dim"] == "出图落档QC" and f["sev"] == gate.BLOCK]
    assert len(blocks) == 1 and "inputs_fingerprint" in blocks[0]["msg"] and "失配" in blocks[0]["msg"]


def test_input_frame_qc_blocks_face_reference_coverage_missing(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _seed_pngs_and_qc(root, ep, hard_blocks=0, coverage={
        "verdict": "block",
        "missing": [{"shot": "Clip_01", "png": "图片/镜头01.png", "reason": "no_face_comparison"}],
        "required": 1,
        "covered": 0,
    })
    gate.check_input_frame_qc(str(root), ep)
    blocks = [f for f in gate.findings if f["dim"] == "出图落档QC" and f["sev"] == gate.BLOCK]
    assert len(blocks) == 1 and "角色脸定妆比对覆盖未过" in blocks[0]["msg"]


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


def _record_image_event(root, ep, asset, *, status="pass", self_check="pass", event="generation",
                        provider="test", method=None):
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": "n2d_production_event",
        "version": 1,
        "ts": "2026-01-01T00:00:00+00:00",
        "episode": ep,
        "stage": "image",
        "event": event,
        "source": provider,
        "generation": {"asset": asset, "status": status},
        "cost": {"provider": provider},
    }
    if method:
        payload["generation"]["method"] = method
    if self_check is not None:
        payload["meta"] = {"self_check": self_check}
        if method:
            payload["meta"]["method"] = method
    elif method:
        payload["meta"] = {"method": method}
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


def test_video_prompt_frames_blocks_missing_endframe_in_production(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _write_production_settings(root)
    _mk_png(root, ep, "Clip_01.png")  # 首帧 exists
    _seed_video_prompt(root, ep,
                       "## Clip 01\n**首帧**：`出图/第1集/图片/Clip_01.png`\n**尾帧**：`出图/第1集/图片/Clip_01_end.png`\n")
    gate.check_video_prompt_frames(str(root), ep, "video_preflight")
    blocks = [f for f in gate.findings if f["dim"] == "尾帧" and f["sev"] == gate.BLOCK]
    assert len(blocks) == 1 and "降级为单首帧" in blocks[0]["msg"]


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


# ── 中段锚帧（default/planned midframe）契约 ──

def _write_midframe_storyboard(tmp_path, midframe, *, duration=10, make_png=False,
                               midframe_default=None, video_backend=None):
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
    policy = {"tailframe_default": True}
    if midframe_default is not None:
        policy["midframe_default"] = midframe_default
    if video_backend is not None:
        policy["video_backend"] = video_backend
    data = {"episode": 1, "policy": policy,
            "clips": [{"id": "EP01_CLIP01", "duration": duration,
                       "firstframe_png": "出图/第1集/图片/Clip_01.png", "continuity": cont}]}
    (sb_dir / "storyboard.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(root)


def _midframe_findings():
    return [f for f in gate.findings if f["dim"] == "中段锚帧"]


def test_midframe_warns_on_unknown_backend_qc_only(tmp_path):
    # 分级 severity（charter three_frame_graduated_severity）：后端未选/未知，中帧消费不了、仅作 QC
    # 参考 → WARN（不硬拦无谓出图花钱）；中帧仍是默认应产图片资产，WARN≠豁免。
    root = _write_midframe_storyboard(tmp_path, None)
    gate.findings.clear()
    gate.check_storyboard_contract(root, "第1集")
    hits = [f for f in _midframe_findings() if "三帧契约" in f["msg"]]
    assert hits and hits[0]["sev"] == gate.WARN
    assert not any(f["sev"] == gate.BLOCK for f in hits)


def test_midframe_blocks_production_high_motion_even_on_unknown_backend(tmp_path):
    root = _write_midframe_storyboard(tmp_path, None)
    _write_production_settings(Path(root))
    sb_path = Path(root) / "脚本" / "第1集" / "storyboard.json"
    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    sb["clips"][0]["template"] = "fight_exchange"
    sb_path.write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")

    gate.findings.clear()
    gate.check_storyboard_contract(root, "第1集")
    hits = [f for f in _midframe_findings() if "三帧契约" in f["msg"]]
    assert hits and hits[0]["sev"] == gate.BLOCK and "production 高运动镜" in hits[0]["msg"]


def test_midframe_default_flag_does_not_force_block_on_incapable_backend(tmp_path):
    # 防误判回退：policy.midframe_default=true 是 anchor_planner 的"已规划"标记（正常流程恒 true），
    # 不是"弱后端也强制 BLOCK"的意图。severity 纯按后端能力——未选后端即便带该标记仍 WARN，
    # 否则 WARN 路径在正常流程里永不触发，等于回到 44af5704 的一刀切。
    root = _write_midframe_storyboard(tmp_path, None, midframe_default=True)
    gate.findings.clear()
    gate.check_storyboard_contract(root, "第1集")
    hits = [f for f in _midframe_findings() if "三帧契约" in f["msg"]]
    assert hits and hits[0]["sev"] == gate.WARN
    assert not any(f["sev"] == gate.BLOCK for f in hits)


def test_midframe_blocks_on_capable_backend(tmp_path):
    # 即梦/dreamina 原生多帧 → 中帧被消费 → 缺锚帧 BLOCK。
    root = _write_midframe_storyboard(tmp_path, None, video_backend="即梦")
    gate.check_storyboard_contract(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and "三帧契约" in f["msg"] for f in _midframe_findings())


def test_midframe_enforced_despite_disabled_flag_on_capable_backend(tmp_path):
    # 能消费中帧的后端：即便项目想用 midframe_default=false 关掉也照样 BLOCK（缺中帧=成片退化）。
    root = _write_midframe_storyboard(tmp_path, None, video_backend="dreamina", midframe_default=False)
    gate.check_storyboard_contract(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and "三帧契约" in f["msg"] for f in _midframe_findings())


def test_midframe_graduated_severity_matches_backend_capability(tmp_path):
    # 分级真值源 = backend_supports_three_plus_frames：能消费(原生多帧/首尾拆段接力)→BLOCK；
    # 真 first-frame-only→WARN（中帧仅 QC 参考·按 cost 由作者定）。直接对齐能力函数，避免硬编码。
    from n2d_platform_profiles import backend_supports_three_plus_frames
    for backend in ("runway", "seedance", "sora", "pika", "kling", "即梦", "dreamina"):
        root = _write_midframe_storyboard(tmp_path, None, video_backend=backend)
        gate.findings.clear()
        gate.check_storyboard_contract(root, "第1集")
        hits = [f for f in _midframe_findings() if "三帧契约" in f["msg"]]
        expected = gate.BLOCK if backend_supports_three_plus_frames(backend) else gate.WARN
        assert hits and hits[0]["sev"] == expected, (backend, hits[0]["sev"] if hits else None)


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


def test_video_prompt_frames_blocks_missing_midframe_png_in_production(tmp_path):
    gate.findings.clear()
    root = tmp_path / "work"; ep = "第1集"
    _write_production_settings(root)
    _mk_png(root, ep, "Clip_01.png")
    _seed_video_prompt(root, ep,
                       "## Clip 01\n**首帧**：`出图/第1集/图片/Clip_01.png`\n"
                       "**中段锚帧**：`出图/第1集/图片/Clip_01_mid.png`\n")
    gate.check_video_prompt_frames(str(root), ep, "video_preflight")
    blocks = [f for f in gate.findings if f["dim"] == "中段锚帧" and f["sev"] == gate.BLOCK]
    assert len(blocks) == 1 and "PNG 不存在" in blocks[0]["msg"]


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


def test_midframe_default_policy_flags_undeclared_clip(tmp_path):
    # 未声明中帧的镜仍被标记；本 fixture 未选后端 → 分级 severity 为 WARN（中帧仅 QC 参考·按 cost 由作者定）。
    # midframe_default=true 在 policy 里只是"已规划"标记，不把 severity 抬成 BLOCK。
    root = _write_midframe_policy_storyboard(tmp_path, {})
    gate.findings.clear()
    gate.check_storyboard_contract(root, "第1集")
    hits = [f for f in _midframe_findings() if "三帧契约" in f["msg"]]
    assert hits and hits[0]["sev"] == gate.WARN
    assert not any(f["sev"] == gate.BLOCK for f in hits)


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


# ── P1-C: 时长清单逐句完整性（非占位但残缺也拦）─────────────────────────────
def _write_timing(tmp_path, vo_text, rows, monkeypatch):
    monkeypatch.setattr(gate, "is_native_av_production", lambda _root: False)
    (tmp_path / "脚本" / "第1集").mkdir(parents=True, exist_ok=True)
    (tmp_path / "脚本" / "第1集" / "voiceover.txt").write_text(vo_text, encoding="utf-8")
    md = tmp_path / "合成" / "第1集" / "配音"
    md.mkdir(parents=True, exist_ok=True)
    (md / "时长清单.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return str(tmp_path)


_VO2 = "[镜头1·沈念·克制] 你来了。\n[镜头2·柳娘子·冷] 我一直在。\n"


def test_timing_complete_passes(tmp_path, monkeypatch):
    rows = [{"镜头": "镜头1", "voice_key": "沈念#cosy", "时长": 1.2},
            {"镜头": "镜头2", "voice_key": "柳娘子#cosy", "时长": 1.0}]
    root = _write_timing(tmp_path, _VO2, rows, monkeypatch)
    gate.findings.clear()
    gate.check_timing_manifest_complete(root, "第1集")
    assert gate.findings == []


def test_timing_missing_voice_key_blocks(tmp_path, monkeypatch):
    rows = [{"镜头": "镜头1", "voice_key": "沈念#cosy", "时长": 1.2},
            {"镜头": "镜头2", "voice_key": "", "时长": 1.0}]
    root = _write_timing(tmp_path, _VO2, rows, monkeypatch)
    gate.findings.clear()
    gate.check_timing_manifest_complete(root, "第1集")
    b = [f for f in gate.findings if f["sev"] == gate.BLOCK and "voice_key" in f["msg"]]
    assert b and b[0]["return_to_stage"] == "voice"


def test_timing_zero_duration_blocks(tmp_path, monkeypatch):
    rows = [{"镜头": "镜头1", "voice_key": "沈念#cosy", "时长": 0},
            {"镜头": "镜头2", "voice_key": "柳娘子#cosy", "时长": 1.0}]
    root = _write_timing(tmp_path, _VO2, rows, monkeypatch)
    gate.findings.clear()
    gate.check_timing_manifest_complete(root, "第1集")
    assert any(f["sev"] == gate.BLOCK and "时长" in f["msg"] for f in gate.findings)


def test_timing_row_count_mismatch_blocks(tmp_path, monkeypatch):
    rows = [{"镜头": "镜头1", "voice_key": "沈念#cosy", "时长": 1.2}]  # 缺第2句
    root = _write_timing(tmp_path, _VO2, rows, monkeypatch)
    gate.findings.clear()
    gate.check_timing_manifest_complete(root, "第1集")
    b = [f for f in gate.findings if f["sev"] == gate.BLOCK and "句数" in f["msg"]]
    assert b and b[0]["return_to_stage"] == "voice"


def test_timing_legacy_key_field_accepted(tmp_path, monkeypatch):
    # 旧产物用中文 legacy 字段「音色键」，不应误报缺 voice_key
    rows = [{"镜头": "镜头1", "音色键": "沈念#cosy", "时长": 1.2},
            {"镜头": "镜头2", "音色键": "柳娘子#cosy", "时长": 1.0}]
    root = _write_timing(tmp_path, _VO2, rows, monkeypatch)
    gate.findings.clear()
    gate.check_timing_manifest_complete(root, "第1集")
    assert gate.findings == []


def test_timing_missing_manifest_no_double_report(tmp_path, monkeypatch):
    # 缺清单由 check_progress_artifact_signoff 覆盖，这里不重复 BLOCK
    monkeypatch.setattr(gate, "is_native_av_production", lambda _root: False)
    (tmp_path / "脚本" / "第1集").mkdir(parents=True, exist_ok=True)
    (tmp_path / "脚本" / "第1集" / "voiceover.txt").write_text(_VO2, encoding="utf-8")
    gate.findings.clear()
    gate.check_timing_manifest_complete(str(tmp_path), "第1集")
    assert gate.findings == []


# ── P1-A: 出图后端连通性预检 ──────────────────────────────────────────────
def test_backend_reachable_down_blocks(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "get_setting", lambda *a, **k: "Codex")
    monkeypatch.setattr(gate.image_backends, "probe_backend",
                        lambda *a, **k: ("down", "HTTP 502"))
    gate.findings.clear()
    gate.check_backend_reachable(str(tmp_path), "第1集")
    b = [f for f in gate.findings if f["sev"] == gate.BLOCK and f["dim"] == "生图后端连通性"]
    assert b and b[0]["return_to_stage"] == "image"
    assert "502" in b[0]["msg"] and "兜底" in b[0]["msg"]


def test_backend_reachable_unknown_warns_only(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "get_setting", lambda *a, **k: "Codex")
    monkeypatch.setattr(gate.image_backends, "probe_backend",
                        lambda *a, **k: ("unknown", "未找到 CLI"))
    gate.findings.clear()
    gate.check_backend_reachable(str(tmp_path), "第1集")
    assert not any(f["sev"] == gate.BLOCK for f in gate.findings)
    assert any(f["sev"] == gate.WARN and f["dim"] == "生图后端连通性" for f in gate.findings)


def test_backend_reachable_ok_silent(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "get_setting", lambda *a, **k: "Codex")
    monkeypatch.setattr(gate.image_backends, "probe_backend",
                        lambda *a, **k: ("ok", ""))
    gate.findings.clear()
    gate.check_backend_reachable(str(tmp_path), "第1集")
    assert gate.findings == []


# ── 出视频后端连通性预检（镜像图侧 check_backend_reachable，付费出视频前）──────────────────
def test_video_backend_reachable_down_blocks(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "get_setting", lambda *a, **k: "即梦/Dreamina")
    monkeypatch.setattr(gate.video_backend_adapter, "probe_video_backend",
                        lambda *a, **k: ("down", "HTTP 502"))
    gate.findings.clear()
    gate.check_video_backend_reachable(str(tmp_path), "第1集")
    b = [f for f in gate.findings if f["sev"] == gate.BLOCK and f["dim"] == "生视频后端连通性"]
    assert b and b[0]["return_to_stage"] == "video_prompt"
    assert "502" in b[0]["msg"] and "兜底" in b[0]["msg"]


def test_video_backend_reachable_unknown_warns_only(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "get_setting", lambda *a, **k: "即梦/Dreamina")
    monkeypatch.setattr(gate.video_backend_adapter, "probe_video_backend",
                        lambda *a, **k: ("unknown", "无自动探针"))
    gate.findings.clear()
    gate.check_video_backend_reachable(str(tmp_path), "第1集")
    assert not any(f["sev"] == gate.BLOCK for f in gate.findings)
    assert any(f["sev"] == gate.WARN and f["dim"] == "生视频后端连通性" for f in gate.findings)


def test_video_backend_reachable_ok_silent(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "get_setting", lambda *a, **k: "即梦/Dreamina")
    monkeypatch.setattr(gate.video_backend_adapter, "probe_video_backend",
                        lambda *a, **k: ("ok", ""))
    gate.findings.clear()
    gate.check_video_backend_reachable(str(tmp_path), "第1集")
    assert gate.findings == []


def test_video_backend_reachable_skip_probe_leaves_trace(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "get_setting", lambda *a, **k: "即梦/Dreamina")
    monkeypatch.setenv("N2D_SKIP_BACKEND_PROBE", "1")
    gate.findings.clear()
    gate.check_video_backend_reachable(str(tmp_path), "第1集")
    assert any(f["dim"] == "生视频后端连通性" and "N2D_SKIP_BACKEND_PROBE 已设置" in str(f["msg"])
               for f in gate.findings)


# ── 付费前预算硬挂钩（堵 budget_cap 只在事后 rebuild 才告警的松动洞）──────────────────────
def test_evaluate_budget_gate_no_cap_is_empty():
    assert gate.evaluate_budget_gate({"CNY": 999}, {}, None, 5) == []
    assert gate.evaluate_budget_gate({"CNY": 999}, {}, 0, 5) == []


def test_evaluate_budget_gate_over_cap_blocks():
    r = gate.evaluate_budget_gate({"CNY": 120.0}, {}, 100, 0)
    assert r and r[0][0] == "block" and r[0][1] == "CNY" and "120" in r[0][4]


def test_evaluate_budget_gate_forecast_pushes_over_blocks():
    # 已花 80 + 本集预测(2/min × 15min = 30) = 110 > 100 → block（开跑前就拦，防超支）
    r = gate.evaluate_budget_gate({"CNY": 80.0}, {"CNY": 2.0}, 100, 15)
    assert r and r[0][0] == "block" and "将超上限" in r[0][4]


def test_evaluate_budget_gate_near_cap_warns():
    r = gate.evaluate_budget_gate({"CNY": 85.0}, {}, 100, 0, warn_ratio=0.8)
    assert r and r[0][0] == "warn"


def test_evaluate_budget_gate_under_cap_silent():
    assert gate.evaluate_budget_gate({"CNY": 50.0}, {}, 100, 0) == []


def test_evaluate_budget_gate_first_episode_forecast_alone_over():
    # 还没花过钱（cost_totals 空），但本集历史单价×计划时长就超 → 仍 block
    r = gate.evaluate_budget_gate({}, {"USD": 10.0}, 100, 12)
    assert r and r[0][0] == "block" and r[0][1] == "USD"


def test_episode_planned_minutes_total_then_clips(tmp_path):
    sb = tmp_path / "脚本" / "第1集"; sb.mkdir(parents=True)
    (sb / "storyboard.json").write_text(json.dumps({"total_duration": 120}), encoding="utf-8")
    assert gate._episode_planned_minutes(str(tmp_path), "第1集") == 2.0
    (sb / "storyboard.json").write_text(json.dumps({"clips": [{"duration": 30}, {"duration": 30}]}), encoding="utf-8")
    assert gate._episode_planned_minutes(str(tmp_path), "第1集") == 1.0
    (sb / "storyboard.json").write_text(json.dumps({}), encoding="utf-8")
    assert gate._episode_planned_minutes(str(tmp_path), "第1集") == 0.0


def test_check_budget_cap_blocks_pre_spend(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "load_thresholds", lambda root: {"budget_cap": 100, "budget_warn_ratio": 0.8})
    monkeypatch.setattr(gate, "load_json",
                        lambda p: {"totals": {"cost_totals": {"CNY": 150.0}, "cost_per_finished_min": {}}}
                        if "dashboard" in str(p) else {})
    gate.findings.clear()
    gate.check_budget_cap(str(tmp_path), "第1集")
    b = [f for f in gate.findings if f["sev"] == gate.BLOCK and f["dim"] == "预算"]
    assert b and "150" in b[0]["msg"] and "停止付费生成" in b[0]["msg"]


def test_check_budget_cap_noop_without_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "load_thresholds", lambda root: {"budget_cap": None})
    gate.findings.clear()
    gate.check_budget_cap(str(tmp_path), "第1集")
    assert gate.findings == []


def test_image_backend_api_refresh_missing_blocks(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "get_setting", lambda *a, **k: "Codex")
    gate.findings.clear()
    gate.check_image_backend_api_refresh(str(tmp_path), "第1集")
    matches = [f for f in gate.findings if f["dim"] == "生图后端适配"]
    assert any(f["sev"] == gate.BLOCK and "刷新证据" in f["msg"] for f in matches)


def test_image_backend_api_refresh_fresh_allows_missing_block(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "get_setting", lambda *a, **k: "Seedream")
    gate.image_backend_adapter.write_refresh_evidence(
        str(tmp_path),
        "Seedream",
        sources=["https://example.com/official-api-doc"],
        note="official endpoint checked today",
    )
    gate.findings.clear()
    gate.check_image_backend_api_refresh(str(tmp_path), "第1集")
    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "生图后端适配" for f in gate.findings)


def test_drift_advisory_findings_face_band_to_severity():
    report = {
        "kind": "n2d_face_drift_risk",
        "characters": [
            {"character_id": "CHAR_A", "name": "沈念", "band": "high", "score": 72,
             "tier": "reference_group", "suggestions": ["建表情库 expressions + 脸部特写参考"]},
            {"character_id": "CHAR_B", "name": "柳娘子", "band": "medium", "score": 55,
             "tier": "native", "suggestions": ["补侧/背角度参考"]},
            {"character_id": "CHAR_C", "name": "路人", "band": "low", "score": 10, "suggestions": []},
        ],
    }
    rows = gate.drift_advisory_findings(report)
    assert len(rows) == 2  # low 不入
    sevs = {loc.split("（")[0]: sev for sev, _dim, loc, _msg in rows}
    assert sevs["沈念"] == gate.WARN   # high → WARN
    assert sevs["柳娘子"] == gate.INFO  # medium → INFO
    assert all(dim == "脸漂预案" for _sev, dim, _loc, _msg in rows)
    assert "建表情库" in rows[0][3]


def test_drift_advisory_findings_measured_block_is_real_block():
    # ② 回灌：band=block（已实测跨集漂移）→ 真 BLOCK，不再被 high/medium 过滤漏掉
    report = {
        "kind": "n2d_face_drift_risk",
        "characters": [
            {"character_id": "CHAR_A", "name": "沈念", "band": "block", "score": 95,
             "measured_drift": {"embedding_drift_high": 1},
             "suggestions": ["⛔ 上一集已实测跨集脸漂：先处置再出图"]},
        ],
    }
    rows = gate.drift_advisory_findings(report)
    assert len(rows) == 1
    sev, dim, loc, msg = rows[0]
    assert sev == gate.BLOCK and dim == "脸漂实测" and "沈念" in loc
    assert "实测" in msg


def test_drift_advisory_findings_predicted_block_is_preflight_plan_not_measured():
    report = {
        "kind": "n2d_face_drift_risk",
        "characters": [
            {"character_id": "CHAR_A", "name": "沈念", "band": "block", "score": 88,
             "predicted_block_reason": "核心长线角色 + 弱后端预测 high",
             "suggestions": ["⛔ 预测高危已升级为阻断：先补同源表情库"]},
        ],
    }
    rows = gate.drift_advisory_findings(report)
    assert len(rows) == 1
    sev, dim, loc, msg = rows[0]
    assert sev == gate.BLOCK and dim == "脸漂预案" and "沈念" in loc
    assert "本集脸漂风险 block" in msg
    assert "上一集已实测" not in msg


def test_drift_advisory_findings_asset_and_empty():
    asset_report = {
        "kind": "n2d_asset_drift_risk",
        "assets": [
            {"id": "PROP_SWORD", "name": "断魂剑", "band": "high", "score": 80,
             "scope": "全篇", "suggestions": ["锁结构件数 + 颜色拖尾防窜色"]},
        ],
    }
    rows = gate.drift_advisory_findings(asset_report)
    assert len(rows) == 1 and rows[0][0] == gate.WARN and rows[0][1] == "物料漂移预案"
    # 全低危 / 空 → 无行
    assert gate.drift_advisory_findings({"kind": "n2d_face_drift_risk", "characters": []}) == []


def _finalize_work(tmp_path, self_check=False, ref="CHAR_01/常态", with_key=True):
    d = tmp_path / "work"
    (d / "出图" / "共享").mkdir(parents=True)
    form = {"form": "常态", "asset_key": "沈念_常态"}
    if with_key:
        form["self_check_passed"] = self_check
    (d / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps({"characters": [{"id": "CHAR_01", "name": "沈念", "forms": [form]}]}), encoding="utf-8")
    (d / "出图" / "第1集" / "prompt").mkdir(parents=True)
    (d / "出图" / "第1集" / "prompt" / "01_分镜出图.md").write_text(
        f"## 镜头1\n资产身份注册层：`{ref}`\n", encoding="utf-8")
    return d


def test_referenced_assets_finalized_blocks_dirty_definition(tmp_path):
    gate.findings.clear()
    gate.check_referenced_assets_finalized(str(_finalize_work(tmp_path, self_check=False)), "第1集")
    assert any(f["dim"] == "共享定妆" and f["sev"] == "block" for f in gate.findings)


def test_referenced_assets_finalized_passes_when_true(tmp_path):
    gate.findings.clear()
    gate.check_referenced_assets_finalized(str(_finalize_work(tmp_path, self_check=True)), "第1集")
    assert not any(f["dim"] == "共享定妆" for f in gate.findings)


def test_referenced_assets_finalized_skips_when_key_absent_backcompat(tmp_path):
    # 现有作品/先出视频 demo 没登记 self_check_passed → 纯 opt-in，不得突然 BLOCK
    gate.findings.clear()
    gate.check_referenced_assets_finalized(str(_finalize_work(tmp_path, self_check=False, with_key=False)), "第1集")
    assert not gate.findings


def test_referenced_assets_finalized_bare_char_ref_single_form(tmp_path):
    gate.findings.clear()
    gate.check_referenced_assets_finalized(str(_finalize_work(tmp_path, self_check=False, ref="CHAR_01")), "第1集")
    assert any(f["dim"] == "共享定妆" and f["sev"] == "block" for f in gate.findings)


def test_referenced_assets_finalized_requires_evidence_once_adopted(tmp_path):
    """被引用即必需机器证据：项目一旦启用 finalize 追踪（CHAR_01 已 true），同集引用的、确属本 registry
    的 CHAR_02 却无任何证据（无 self_check_passed/anchor_sha）= 漏登记的自断言 → BLOCK，不再静默放行。"""
    d = tmp_path / "work"
    (d / "出图" / "共享").mkdir(parents=True)
    reg = {"characters": [
        {"id": "CHAR_01", "name": "甲", "forms": [{"form": "常态", "self_check_passed": True}]},
        {"id": "CHAR_02", "name": "乙", "forms": [{"form": "常态"}]},
    ]}
    (d / "出图" / "共享" / "identity_registry.json").write_text(json.dumps(reg), encoding="utf-8")
    (d / "出图" / "第1集" / "prompt").mkdir(parents=True)
    (d / "出图" / "第1集" / "prompt" / "01_分镜出图.md").write_text(
        "## 镜头1\n资产身份注册层：`CHAR_01/常态`、`CHAR_02/常态`\n", encoding="utf-8")
    gate.findings.clear()
    gate.check_referenced_assets_finalized(str(d), "第1集")
    blocks = [f for f in gate.findings if f["dim"] == "共享定妆" and f["sev"] == "block"]
    assert len(blocks) == 1 and "CHAR_02/常态" in blocks[0]["msg"] and "被引用即必需" in blocks[0]["msg"]


def test_ffprobe_missing_blocks_double_voice_at_review(tmp_path, monkeypatch):
    """缺核心检测工具→交付边界拦截：ffprobe 不可用(has_audio→None)又存在 n2d-voice 配音轨时，
    双人声硬闸门无法校验，review 默认 BLOCK；N2D_ALLOW_DEGRADED_QC=1 显式放行降级为 WARN。"""
    root = tmp_path / "work"; ep = "第1集"
    (root / "出视频" / ep / "视频").mkdir(parents=True)
    (root / "出视频" / ep / "视频" / "Clip_01.mp4").write_bytes(b"x")
    (root / "合成" / ep / "配音").mkdir(parents=True)
    (root / "合成" / ep / "配音" / "voice_zh.wav").write_bytes(b"x")
    monkeypatch.setattr(gate, "has_audio", lambda p: None)  # ffprobe 不可用
    monkeypatch.delenv("N2D_ALLOW_DEGRADED_QC", raising=False)
    gate.findings.clear()
    gate.check_video_assets(str(root), ep)
    blocks = [f for f in gate.findings if f["dim"] == "原生音画" and f["sev"] == gate.BLOCK]
    assert blocks and "ffprobe" in blocks[0]["msg"]
    # 逃生口：显式放行 → 降级 WARN，不再 BLOCK
    monkeypatch.setenv("N2D_ALLOW_DEGRADED_QC", "1")
    gate.findings.clear()
    gate.check_video_assets(str(root), ep)
    assert not [f for f in gate.findings if f["dim"] == "原生音画" and f["sev"] == gate.BLOCK]
    assert [f for f in gate.findings if f["dim"] == "原生音画" and f["sev"] == gate.WARN]


def test_video_split_count_warn_becomes_info_when_final_timeline_probe_passes(tmp_path, monkeypatch):
    root = tmp_path / "work"; ep = "第1集"
    video_dir = root / "出视频" / ep / "视频"
    video_dir.mkdir(parents=True)
    (video_dir / "Clip_01_part1.mp4").write_bytes(b"x")
    (video_dir / "Clip_01_part2.mp4").write_bytes(b"x")
    (root / "脚本" / ep).mkdir(parents=True)
    (root / "脚本" / ep / "storyboard.json").write_text(
        json.dumps({"clips": [{"id": "EP01_CLIP01"}]}, ensure_ascii=False), encoding="utf-8")
    (root / "生产数据").mkdir(parents=True)
    (root / "生产数据" / f"final_timeline_probe_{ep}.json").write_text(json.dumps({
        "kind": "n2d_final_timeline_probe",
        "actual_duration_sec": 10.0,
        "expected_duration_sec": 10.2,
        "duration_tolerance_sec": 1.0,
        "findings": [],
    }), encoding="utf-8")
    monkeypatch.setattr(gate, "has_audio", lambda p: False)

    gate.findings.clear()
    gate.check_video_assets(str(root), ep)

    assert not [f for f in gate.findings if f["dim"] == "视频" and f["sev"] == gate.WARN and "clip 数" in f["msg"]]
    assert [f for f in gate.findings if f["dim"] == "视频" and f["sev"] == gate.INFO and "clip 数" in f["msg"]]


def test_referenced_assets_finalized_anchor_sha_counts_as_evidence(tmp_path):
    """档①只钉了 anchor_sha（没显式写 self_check_passed=true）也算机器证据 → 不误拦。"""
    d = tmp_path / "work"
    (d / "出图" / "共享").mkdir(parents=True)
    reg = {"characters": [{"id": "CHAR_01", "name": "甲",
                           "forms": [{"form": "常态", "anchor_sha": "abc123"}]}]}
    (d / "出图" / "共享" / "identity_registry.json").write_text(json.dumps(reg), encoding="utf-8")
    (d / "出图" / "第1集" / "prompt").mkdir(parents=True)
    (d / "出图" / "第1集" / "prompt" / "01_分镜出图.md").write_text(
        "## 镜头1\n资产身份注册层：`CHAR_01/常态`\n", encoding="utf-8")
    gate.findings.clear()
    gate.check_referenced_assets_finalized(str(d), "第1集")
    assert not [f for f in gate.findings if f["dim"] == "共享定妆"]


# ── 跨集视觉契约方向反转 gate 落地（防回退成「脚本写了没人跑」的孤儿） ──
_CE_OVERVIEW = ("## 本集视觉一致性契约\n- 色调基线：冷青灰压暗\n- 场景光位锚：冷宫寝殿={light}\n"
                "- 场景轴线视线：冷宫寝殿 画左 -> 画右\n- 状态演进：沈念常态\n- 景别阶梯：CU->MCU\n")


def _write_ce_overview(root, ep, light):
    d = os.path.join(root, "出图", ep, "prompt")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "00_总览.md"), "w", encoding="utf-8").write(_CE_OVERVIEW.format(light=light))


def _write_ce_assets(root):
    d = os.path.join(root, "出图", "共享")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "asset_registry.json"), "w", encoding="utf-8").write(
        json.dumps({"assets": [{"id": "LOC_01", "name": "冷宫寝殿"}]}, ensure_ascii=False))


def test_cross_episode_contract_warns_on_same_scene_light_flip(tmp_path):
    root = str(tmp_path / "剧")
    _write_ce_overview(root, "第1集", "左侧光")
    _write_ce_overview(root, "第2集", "右侧光")
    _write_ce_assets(root)
    gate.findings.clear()
    gate.check_cross_episode_contract(root, "第2集")
    hits = [f for f in gate.findings if f["dim"] == "跨集光位轴线"]
    assert len(hits) == 1 and hits[0]["sev"] == "warn"  # advisory：只 WARN 不 BLOCK


def test_cross_episode_contract_first_episode_no_warn(tmp_path):
    root = str(tmp_path / "剧")
    _write_ce_overview(root, "第1集", "左侧光")
    _write_ce_assets(root)
    gate.findings.clear()
    gate.check_cross_episode_contract(root, "第1集")
    assert not gate.findings  # 首集无前集可比


def test_cross_episode_contract_no_warn_on_consistent_light(tmp_path):
    root = str(tmp_path / "剧")
    _write_ce_overview(root, "第1集", "左侧光")
    _write_ce_overview(root, "第2集", "左侧光")
    _write_ce_assets(root)
    gate.findings.clear()
    gate.check_cross_episode_contract(root, "第2集")
    assert not gate.findings


def test_cross_episode_contract_missing_overview_skips(tmp_path):
    # image_preflight 早于出图：本集总览未生成 → 不误报
    root = str(tmp_path / "剧")
    _write_ce_overview(root, "第1集", "左侧光")
    _write_ce_assets(root)
    gate.findings.clear()
    gate.check_cross_episode_contract(root, "第2集")
    assert not gate.findings


# ── 声纹/音色键跨集一致性 gate 落地（此前只在手动 identity.py --write 时打印、不拦渲染） ──
def _write_voice_manifest(root, ep, entries):
    d = os.path.join(root, "合成", ep, "配音")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "时长清单.json"), "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False)


def _write_voicemap(root, mapping):
    d = os.path.join(root, "设定库")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "voicemap.json"), "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False)


def _voice_line(char, key, shot="镜头1", idx=0):
    return {"角色": char, "voice_key": key, "镜头": shot, "idx": idx}


def test_voice_cross_episode_voicemap_mismatch_blocks(tmp_path):
    root = str(tmp_path / "剧")
    _write_voice_manifest(root, "第2集", [_voice_line("沈念", "cosy:女A")])
    _write_voicemap(root, {"沈念": "cosy:女主声"})  # 注册键与实际用键不符
    gate.findings.clear()
    gate.check_voice_cross_episode(root, "第2集")
    hits = [f for f in gate.findings if f["dim"] == "跨集音色"]
    assert len(hits) == 1 and hits[0]["sev"] == "block"


def test_voice_cross_episode_drift_warns_without_voicemap(tmp_path):
    root = str(tmp_path / "剧")
    _write_voice_manifest(root, "第1集", [_voice_line("沈念", "cosy:女A")])
    _write_voice_manifest(root, "第2集", [_voice_line("沈念", "cosy:女B")])  # 跨集换键、无 voicemap
    gate.findings.clear()
    gate.check_voice_cross_episode(root, "第2集")
    hits = [f for f in gate.findings if f["dim"] == "跨集音色"]
    assert len(hits) == 1 and hits[0]["sev"] == "warn"  # 可能有意，只告警


def test_voice_cross_episode_consistent_no_findings(tmp_path):
    root = str(tmp_path / "剧")
    _write_voice_manifest(root, "第1集", [_voice_line("沈念", "cosy:女主声")])
    _write_voice_manifest(root, "第2集", [_voice_line("沈念", "cosy:女主声")])
    _write_voicemap(root, {"沈念": "cosy:女主声"})
    gate.findings.clear()
    gate.check_voice_cross_episode(root, "第2集")
    assert not [f for f in gate.findings if f["dim"] in ("跨集音色", "跨集声纹")]


def test_voice_cross_episode_placeholder_not_mismatch(tmp_path):
    # 占位应急轨不算 voicemap 失配，不得在 video-first/demo 误 BLOCK
    root = str(tmp_path / "剧")
    _write_voice_manifest(root, "第2集", [_voice_line("沈念", "say:Tingting#placeholder")])
    _write_voicemap(root, {"沈念": "cosy:女主声"})
    gate.findings.clear()
    gate.check_voice_cross_episode(root, "第2集")
    assert not [f for f in gate.findings if f["dim"] == "跨集音色"]


def test_voice_cross_episode_drift_only_targets_current_episode(tmp_path):
    # 为第1集跑 gate 时，第1→2 的漂移（episode_to=第2集）不该算到第1集头上
    root = str(tmp_path / "剧")
    _write_voice_manifest(root, "第1集", [_voice_line("沈念", "cosy:女A")])
    _write_voice_manifest(root, "第2集", [_voice_line("沈念", "cosy:女B")])
    gate.findings.clear()
    gate.check_voice_cross_episode(root, "第1集")
    assert not [f for f in gate.findings if f["dim"] == "跨集音色"]


# ── E 成长派生形态定妆必须 image2image 派生（防纯文生图重抽新脸）─────────────────────

def _evo_registry(tmp_path, derived_mode="same_identity_progressive_upgrade"):
    import json as _json
    root = tmp_path / "制漫剧" / "剧"
    (root / "出图" / "共享").mkdir(parents=True)
    reg = {"characters": [{
        "id": "CHAR_01", "name": "沈念",
        "evolution_profile": {"mode": derived_mode, "identity_anchor_form": "常态"},
        "forms": [
            {"form": "常态", "asset_key": "沈念_常态"},
            {"form": "红衣觉醒态", "asset_key": "沈念_红衣觉醒态"},
        ],
    }]}
    (root / "出图" / "共享" / "identity_registry.json").write_text(
        _json.dumps(reg, ensure_ascii=False), encoding="utf-8")
    return root


def test_evolution_derived_forms_excludes_anchor_and_nonprogressive(tmp_path):
    root = _evo_registry(tmp_path)
    df = gate._evolution_derived_forms(str(root))
    assert [d["form"] for d in df] == ["红衣觉醒态"]   # 锚定 常态 不算派生
    # restricted_partial 模式不纳入
    root2 = _evo_registry(tmp_path / "x", derived_mode="restricted_partial_until_reveal")
    assert gate._evolution_derived_forms(str(root2)) == []


def test_derived_form_costume_without_i2i_derivation_blocks(tmp_path):
    root = _evo_registry(tmp_path)
    df = {"char_id": "CHAR_01", "char_name": "沈念", "asset_key": "沈念_红衣觉醒态",
          "form": "红衣觉醒态", "anchor_form": "常态"}
    sec_bad = "## 沈念/红衣觉醒态\n目标存档: 定妆_沈念_红衣觉醒态.png\n正向 prompt：红衣觉醒，全新造型"
    assert gate._section_is_derived_form(sec_bad, df)
    assert gate._declares_evolution_derivation(sec_bad, "常态") is False


def test_derived_form_with_anchor_i2i_derivation_passes(tmp_path):
    sec_ok = ("## 沈念/红衣觉醒态\n目标存档: 定妆_沈念_红衣觉醒态.png\n"
              "生成方式: 以 定妆_沈念_常态 正脸为母图做 image2image 派生，只升级服装与气场")
    assert gate._declares_evolution_derivation(sec_ok, "常态") is True


# ════════ 一致性审查加固回归（#1/#2/#3 + M4/M5 + L6/L7/L8 + voice 接线）════════
import inspect as _inspect


class _FakeProc:
    def __init__(self, stdout, returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr


def _write_overview(root, ep, text):
    p = Path(root) / "出图" / ep / "prompt"
    p.mkdir(parents=True, exist_ok=True)
    (p / "00_总览.md").write_text(text, encoding="utf-8")


def _write_registry(root, characters):
    p = Path(root) / "出图" / "共享"
    p.mkdir(parents=True, exist_ok=True)
    (p / "identity_registry.json").write_text(
        json.dumps({"kind": "identity_registry", "characters": characters}, ensure_ascii=False),
        encoding="utf-8")


# ── #2 近景必须声明 expression_span（双帧契约从 opt-in 收成强制）──
def _closeup_clip(span=None):
    cont = {"start_state": "平静", "end_state": "爆哭", "transition": "硬切",
            "need_endframe": True, "endframe_png": "出图/第1集/图片/c1_end.png"}
    if span is not None:
        cont["expression_span"] = span
    return {"firstframe_png": "出图/第1集/图片/c1.png", "label": "近景特写", "continuity": cont}


def test_closeup_missing_expression_span_blocks(tmp_path):
    gate.findings.clear()
    root = _write_storyboard_with_clips(tmp_path, [_closeup_clip(span=None)])
    gate.check_storyboard_contract(root, "第1集", require_frame_assets=False)
    assert any(f["dim"] == "表情一致性" and f["sev"] == "block"
               and "expression_span" in str(f["msg"]) for f in gate.findings)


def test_closeup_with_expression_span_no_block(tmp_path):
    gate.findings.clear()
    root = _write_storyboard_with_clips(tmp_path, [_closeup_clip(span="中")])
    gate.check_storyboard_contract(root, "第1集", require_frame_assets=False)
    assert not any(f["dim"] == "表情一致性" for f in gate.findings)


def test_non_closeup_no_expression_span_ok(tmp_path):
    gate.findings.clear()
    clip = {"firstframe_png": "出图/第1集/图片/c1.png", "label": "远景空镜",
            "continuity": {"start_state": "s", "end_state": "e", "transition": "硬切",
                           "need_endframe": True, "endframe_png": "出图/第1集/图片/c1_end.png"}}
    root = _write_storyboard_with_clips(tmp_path, [clip])
    gate.check_storyboard_contract(root, "第1集", require_frame_assets=False)
    assert not any(f["dim"] == "表情一致性" for f in gate.findings)


def test_prompt_preflight_does_not_require_frame_paths(tmp_path):
    gate.findings.clear()
    clip = {"label": "远景空镜",
            "continuity": {"start_state": "s", "end_state": "e", "transition": "硬切",
                           "need_endframe": True}}
    root = _write_storyboard_with_clips(tmp_path, [clip])
    gate.check_storyboard_contract(root, "第1集", require_frame_assets=False)
    assert not any(f["dim"] in {"首帧", "尾帧"} for f in gate.findings)


def _presence_clip(cid, chars, start, end, **cont_extra):
    cont = {"start_state": start, "end_state": end, "transition": "硬切",
            "need_endframe": True, "midframe_exempt_reason": "极短镜<3s"}
    cont.update(cont_extra)
    return {
        "id": cid,
        "scene": "冷宫寝殿",
        "entity_schedule": {"characters": chars},
        "continuity": cont,
    }


def test_storyboard_presence_chain_blocks_unexplained_disappear(tmp_path):
    gate.findings.clear()
    clips = [
        _presence_clip("Clip_01", ["CHAR_SHEN", "CHAR_LIU"], "s", "e"),
        _presence_clip("Clip_02", ["CHAR_SHEN"], "e", "f"),
    ]
    root = _write_storyboard_with_clips(tmp_path, clips)
    gate.check_storyboard_contract(root, "第1集", require_frame_assets=False)
    hits = [f for f in gate.findings if f["dim"] == "人物在场链" and f["sev"] == gate.BLOCK]
    assert hits and "CHAR_LIU" in hits[0]["msg"] and "消失" in hits[0]["msg"]


def test_storyboard_presence_chain_allows_offscreen_handoff(tmp_path):
    gate.findings.clear()
    clips = [
        _presence_clip("Clip_01", ["CHAR_SHEN", "CHAR_LIU"], "s", "e"),
        _presence_clip("Clip_02", ["CHAR_SHEN"], "e", "f", offscreen_presence=["CHAR_LIU"]),
    ]
    root = _write_storyboard_with_clips(tmp_path, clips)
    gate.check_storyboard_contract(root, "第1集", require_frame_assets=False)
    assert not any(f["dim"] == "人物在场链" and f["sev"] == gate.BLOCK for f in gate.findings)


def test_storyboard_presence_chain_blocks_unexplained_appearance(tmp_path):
    gate.findings.clear()
    clips = [
        _presence_clip("Clip_01", ["CHAR_SHEN"], "s", "e"),
        _presence_clip("Clip_02", ["CHAR_SHEN", "CHAR_LIU"], "e", "f"),
    ]
    root = _write_storyboard_with_clips(tmp_path, clips)
    gate.check_storyboard_contract(root, "第1集", require_frame_assets=False)
    assert any(f["dim"] == "人物在场链" and f["sev"] == gate.BLOCK and "CHAR_LIU" in f["msg"]
               for f in gate.findings)


def test_storyboard_presence_chain_allows_explicit_entry(tmp_path):
    gate.findings.clear()
    clips = [
        _presence_clip("Clip_01", ["CHAR_SHEN"], "s", "e"),
        _presence_clip("Clip_02", ["CHAR_SHEN", "CHAR_LIU"], "e", "f",
                       entry_exit="CHAR_LIU 推门入画，停在画面右后方"),
    ]
    root = _write_storyboard_with_clips(tmp_path, clips)
    gate.check_storyboard_contract(root, "第1集", require_frame_assets=False)
    assert not any(f["dim"] == "人物在场链" and f["sev"] == gate.BLOCK for f in gate.findings)


def test_storyboard_ordinary_cut_state_mismatch_warns_not_blocks(tmp_path):
    gate.findings.clear()
    clips = [
        {"firstframe_png": "a.png", "scene": "正堂/夜/内",
         "continuity": {"start_state": "A 入画", "end_state": "A 看向门口",
                        "transition": "straight_cut", "need_endframe": True}},
        {"firstframe_png": "b.png", "scene": "正堂/夜/内",
         "continuity": {"start_state": "B 推门入画", "end_state": "A 转身",
                        "transition": "straight_cut", "need_endframe": True}},
    ]
    root = _write_storyboard_with_clips(tmp_path, clips)
    gate.check_storyboard_contract(root, "第1集", require_frame_assets=False)

    assert not any(f["dim"] == "故事板" and f["sev"] == gate.BLOCK
                   and "start_state 未原样继承" in str(f["msg"]) for f in gate.findings)
    assert any(f["dim"] == "故事板" and f["sev"] == gate.WARN
               and "普通剪辑接缝允许" in str(f["msg"]) for f in gate.findings)


def test_storyboard_exact_tailframe_state_mismatch_blocks(tmp_path):
    gate.findings.clear()
    clips = [
        {"firstframe_png": "a.png",
         "continuity": {"start_state": "A 入画", "end_state": "A 看向门口",
                        "transition": "straight_cut", "need_endframe": True}},
        {"firstframe_png": "b.png",
         "continuity": {"start_state": "B 推门入画", "end_state": "A 转身",
                        "transition": "straight_cut", "handoff_mode": "exact_tailframe_match",
                        "need_endframe": True}},
    ]
    root = _write_storyboard_with_clips(tmp_path, clips)
    gate.check_storyboard_contract(root, "第1集", require_frame_assets=False)

    assert any(f["dim"] == "故事板" and f["sev"] == gate.BLOCK
               and "start_state 未原样继承" in str(f["msg"]) for f in gate.findings)


def _generic_template_contract():
    return {
        "template_id": "generic",
        "beats": ["A 看向门口"],
        "blocking": "A 画左，门口画右",
        "camera_rule": "固定机位，中近景",
        "continuity_must": ["A 发型服装不漂"],
        "negative": ["不要乱码文字"],
    }


def test_storyboard_generic_template_contract_allowed(tmp_path):
    gate.findings.clear()
    clips = [{
        "template": "generic",
        "template_contract": _generic_template_contract(),
        "continuity": {"start_state": "A 入画", "end_state": "A 看门",
                       "transition": "straight_cut", "need_endframe": True},
    }]
    root = _write_storyboard_with_clips(tmp_path, clips)
    gate.check_storyboard_special_templates(root, "第1集")

    assert not any(f["dim"] == "专项镜头模板" and f["sev"] == gate.BLOCK for f in gate.findings)


def test_storyboard_generic_template_missing_base_contract_blocks(tmp_path):
    gate.findings.clear()
    clips = [{
        "template": "generic",
        "template_contract": {"template_id": "generic", "beats": ["A 看向门口"]},
        "continuity": {"start_state": "A 入画", "end_state": "A 看门",
                       "transition": "straight_cut", "need_endframe": True},
    }]
    root = _write_storyboard_with_clips(tmp_path, clips)
    gate.check_storyboard_special_templates(root, "第1集")

    assert any(f["dim"] == "专项镜头模板" and f["sev"] == gate.BLOCK
               and "template=generic" in str(f["msg"]) for f in gate.findings)


# ── L7 endframe 豁免理由不能是占位/单字 ──
def test_short_endframe_exempt_reason_blocks(tmp_path):
    gate.findings.clear()
    clips = [
        {"firstframe_png": "a.png", "label": "远景",
         "continuity": {"start_state": "s", "end_state": "e", "transition": "硬切",
                        "need_endframe": False, "endframe_exempt_reason": "x",
                        "midframe_exempt_reason": "极短镜<3s"}},
        {"firstframe_png": "b.png", "label": "远景",
         "continuity": {"start_state": "e", "end_state": "f", "transition": "硬切",
                        "need_endframe": True, "endframe_png": "b_end.png"}},
    ]
    root = _write_storyboard_with_clips(tmp_path, clips)
    gate.check_storyboard_contract(root, "第1集", require_frame_assets=False)
    assert any(f["dim"] == "尾帧" and f["sev"] == "block" and "过短" in str(f["msg"])
               for f in gate.findings)


def test_substantive_endframe_exempt_reason_ok(tmp_path):
    gate.findings.clear()
    clips = [
        {"firstframe_png": "a.png", "label": "远景",
         "continuity": {"start_state": "s", "end_state": "e", "transition": "硬切",
                        "need_endframe": False, "endframe_exempt_reason": "极短镜<3s 无表情变化",
                        "midframe_exempt_reason": "极短镜<3s"}},
        {"firstframe_png": "b.png", "label": "远景",
         "continuity": {"start_state": "e", "end_state": "f", "transition": "硬切",
                        "need_endframe": True, "endframe_png": "b_end.png"}},
    ]
    root = _write_storyboard_with_clips(tmp_path, clips)
    gate.check_storyboard_contract(root, "第1集", require_frame_assets=False)
    assert not any(f["dim"] == "尾帧" and "过短" in str(f["msg"]) for f in gate.findings)


# ── #1 + M4 一致性总审：降级精度交付边界阻断 / 显式放行 / WARN rollup ──
def _run_consistency(monkeypatch, tmp_path, payload, stage, returncode=0, env=None):
    gate.findings.clear()
    root = tmp_path / "w"
    (root / "生产数据").mkdir(parents=True)
    monkeypatch.setattr(gate.subprocess, "run",
                        lambda *a, **k: _FakeProc(json.dumps(payload), returncode))
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("N2D_ALLOW_DEGRADED_QC", raising=False) if not (env or {}).get(
        "N2D_ALLOW_DEGRADED_QC") else None
    gate.check_consistency_audit_gate(str(root), "第1集", stage=stage)
    return list(gate.findings)


def test_degraded_precision_blocks_at_review(monkeypatch, tmp_path):
    fs = _run_consistency(monkeypatch, tmp_path,
                          {"summary": {"precision_level": "degraded"}, "findings": []}, "review")
    assert any(f["dim"] == "一致性总审" and f["sev"] == "block" for f in fs)


def test_degraded_precision_blocks_at_compose(monkeypatch, tmp_path):
    fs = _run_consistency(monkeypatch, tmp_path,
                          {"summary": {"precision_level": "degraded"}, "findings": []}, "compose")
    assert any(f["dim"] == "一致性总审" and f["sev"] == "block" for f in fs)


def test_degraded_precision_review_waived_by_env(monkeypatch, tmp_path):
    fs = _run_consistency(monkeypatch, tmp_path,
                          {"summary": {"precision_level": "degraded"}, "findings": []}, "review",
                          env={"N2D_ALLOW_DEGRADED_QC": "1"})
    assert not any(f["sev"] == "block" for f in fs)
    assert any(f["sev"] == "warn" and "放行" in str(f["msg"]) for f in fs)


def test_degraded_precision_compose_waived_by_env(monkeypatch, tmp_path):
    fs = _run_consistency(monkeypatch, tmp_path,
                          {"summary": {"precision_level": "degraded"}, "findings": []}, "compose",
                          env={"N2D_ALLOW_DEGRADED_QC": "1"})
    assert not any(f["sev"] == "block" for f in fs)
    assert any(f["sev"] == "warn" and "放行" in str(f["msg"]) for f in fs)


def test_degraded_precision_blocks_at_video_under_production(monkeypatch, tmp_path):
    fs = _run_consistency(monkeypatch, tmp_path,
                          {"summary": {"precision_level": "degraded"}, "findings": []}, "video",
                          env={"N2D_CONSISTENCY_PROFILE": "production"})
    assert any(f["dim"] == "一致性总审" and f["sev"] == "block" and "出视频后闸门" in str(f["msg"]) for f in fs)


# ── 一致性总审前移到出图后 image 闸门：确定性 🔴 维度挡在出视频前 ──

def test_consistency_block_dim_blocks_at_image(monkeypatch, tmp_path):
    """手部多指/天气硬跳/禁用称谓等确定性 block 维度，在出图后 image 闸门即 BLOCK（不拖到 compose）。"""
    payload = {"summary": {"precision_level": "full"},
               "findings": [{"verdict": "block", "dimension": "手部/解剖(N5)",
                             "message": "镜头3 单手 7 指尖（多指）", "return_to_stage": "image"}]}
    fs = _run_consistency(monkeypatch, tmp_path, payload, "image")
    assert any(f["dim"] == "手部/解剖(N5)" and f["sev"] == "block" for f in fs)


def test_fresh_image_qc_downgrades_duplicate_pixel_blocks_at_image(monkeypatch, tmp_path):
    gate.findings.clear()
    root = tmp_path / "w"
    qc_dir = root / "生产数据" / "image_qc" / "第1集"
    qc_dir.mkdir(parents=True)
    (qc_dir / "image_qc_第1集.json").write_text(json.dumps({
        "summary": {"hard_blocks": 0},
        "qc_environment": {"precision_level": "full"},
        "face_reference_coverage": {"verdict": "ok", "precision_level": "full"},
        "inputs_fingerprint": {"files": {}},
    }, ensure_ascii=False), encoding="utf-8")
    payload = {
        "summary": {"precision_level": "full"},
        "findings": [{
            "verdict": "block",
            "dimension": "脸(G1)",
            "message": "低分脸部误报",
            "return_to_stage": "image",
        }],
    }
    monkeypatch.setattr(gate.subprocess, "run", lambda *a, **k: _FakeProc(json.dumps(payload), 1))
    monkeypatch.setitem(gate.check_consistency_audit_gate.__globals__, "fingerprint_is_fresh", lambda fp, r: True)

    gate.check_consistency_audit_gate(str(root), "第1集", stage="image")

    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "脸(G1)" for f in gate.findings)
    assert any(
        f["sev"] == gate.WARN and f["dim"] == "脸(G1)" and "fresh image_qc hard=0" in str(f["msg"])
        for f in gate.findings
    )


def test_image_gate_ignores_video_side_consistency_findings(monkeypatch, tmp_path):
    payload = {
        "summary": {"precision_level": "full"},
        "findings": [{
            "verdict": "block",
            "dimension": "视频语义一致(VSEM)",
            "message": "旧视频报告不应卡 image gate",
            "return_to_stage": "video",
            "affected_artifacts": ["生产数据/video_semantic_consistency_第1集.json"],
        }],
    }
    fs = _run_consistency(monkeypatch, tmp_path, payload, "image", returncode=1)
    assert not any(f["dim"] == "视频语义一致(VSEM)" for f in fs)
    assert not any(f["dim"] == "一致性总审" and f["sev"] == gate.BLOCK for f in fs)


def test_degraded_precision_image_blocks_in_demo(monkeypatch, tmp_path):
    """铁律 B11（C4 豁免堵死）：降级精度（缺 insightface=脸/像素没真验）demo image 也 BLOCK，
    不再静默 WARN 免单——唯一出口显式留痕 N2D_ALLOW_DEGRADED_QC=1。"""
    fs = _run_consistency(monkeypatch, tmp_path,
                          {"summary": {"precision_level": "degraded"}, "findings": []}, "image")
    assert any(f["dim"] == "一致性总审" and f["sev"] == "block" for f in fs)


def test_image_stage_runs_consistency_audit_gate_but_preflight_does_not(tmp_path, monkeypatch):
    """锁住接线：出图后 `--stage image` 跑一致性总审，pre-gen 的 image_preflight 不跑。"""
    root = tmp_path / "work"; root.mkdir()
    ep = "第1集"
    calls = []
    monkeypatch.setattr(gate, "check_input_frame_qc", lambda r, e: None)
    monkeypatch.setattr(gate, "check_consistency_audit_gate",
                        lambda r, e, stage="review": calls.append((r, e, stage)))
    gate.findings.clear()
    gate.run(str(root), ep, "image_preflight")
    assert calls == []  # 生成前无 PNG，一致性总审不跑
    gate.findings.clear()
    gate.run(str(root), ep, "image")
    assert calls == [(str(root), ep, "image")]  # 出图后即跑，stage=image（降级精度只 WARN）


def test_consistency_warn_rollup_over_cap(monkeypatch, tmp_path):
    findings = [{"severity": "warn", "message": f"w{i}", "dimension": "x"} for i in range(20)]
    fs = _run_consistency(monkeypatch, tmp_path,
                          {"summary": {"precision_level": "full"}, "findings": findings}, "review")
    assert any("未在此展开" in str(f["msg"]) for f in fs)


def test_production_profile_escalates_repeated_axis_warn_to_block(monkeypatch, tmp_path):
    payload = {
        "summary": {"precision_level": "full", "by_dim": {"轴线视线(X1)": {"warn": 2}}},
        "findings": [{"severity": "warn", "dimension": "轴线视线(X1)", "message": "关键对峙镜视线越轴"}],
    }
    fs = _run_consistency(monkeypatch, tmp_path, payload, "image", env={"N2D_CONSISTENCY_PROFILE": "production"})
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "轴线视线(X1)" and "production一致性升级" in str(f["msg"])
               for f in fs)


def test_production_profile_advisory_signoff_keeps_warn(monkeypatch, tmp_path):
    gate.findings.clear()
    root = tmp_path / "w"
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (prod / "consistency_advisory_signoff_第1集.json").write_text(
        json.dumps({"accepted": [{
            "accepted": True,
            "dimension": "轴线视线(X1)",
            "message_contains": "关键对峙",
            "reviewer": "qa",
            "reason": "导演有意越轴，已人工确认叙事动机",
            "expires_at": "2099-01-01",
        }]}, ensure_ascii=False),
        encoding="utf-8",
    )
    payload = {
        "summary": {"precision_level": "full", "by_dim": {"轴线视线(X1)": {"warn": 2}}},
        "findings": [{"severity": "warn", "dimension": "轴线视线(X1)", "message": "关键对峙镜视线越轴"}],
    }
    monkeypatch.setenv("N2D_CONSISTENCY_PROFILE", "production")
    monkeypatch.setattr(gate.subprocess, "run", lambda *a, **k: _FakeProc(json.dumps(payload), 0))
    gate.check_consistency_audit_gate(str(root), "第1集", stage="image")
    assert not any(f["sev"] == gate.BLOCK and f["dim"] == "轴线视线(X1)" for f in gate.findings)
    assert any(f["sev"] == gate.WARN and f["dim"] == "轴线视线(X1)" for f in gate.findings)


def test_production_profile_weak_advisory_signoff_still_blocks(monkeypatch, tmp_path):
    gate.findings.clear()
    root = tmp_path / "w"
    prod = root / "生产数据"
    prod.mkdir(parents=True)
    (prod / "consistency_advisory_signoff_第1集.json").write_text(
        json.dumps({"accepted": ["轴线视线(X1)", {"dimension": "轴线视线(X1)"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    payload = {
        "summary": {"precision_level": "full", "by_dim": {"轴线视线(X1)": {"warn": 2}}},
        "findings": [{"severity": "warn", "dimension": "轴线视线(X1)", "message": "关键对峙镜视线越轴"}],
    }
    monkeypatch.setenv("N2D_CONSISTENCY_PROFILE", "production")
    monkeypatch.setattr(gate.subprocess, "run", lambda *a, **k: _FakeProc(json.dumps(payload), 0))
    gate.check_consistency_audit_gate(str(root), "第1集", stage="image")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "轴线视线(X1)" and "finding_hash" in str(f["msg"])
               for f in gate.findings)


def test_delivery_stage_infers_production_profile_without_setting(tmp_path):
    root = tmp_path / "w"
    root.mkdir()
    assert gate.consistency_release_profile(str(root), stage="review", ep="第1集") == "production"
    (root / "_设置.md").write_text("- 一致性严格度: 宽松\n", encoding="utf-8")
    assert gate.consistency_release_profile(str(root), stage="review", ep="第1集") == "demo"


def test_av1_dialogue_closeup_single_warn_blocks_under_production(monkeypatch, tmp_path):
    root = tmp_path / "w"
    root.mkdir()
    monkeypatch.setenv("N2D_CONSISTENCY_PROFILE", "production")
    summary = {"by_dim": {"音画同步(AV1)": {"warn": 1}}}  # 孤例、非关键、image 阶段（非交付边界）
    closeup = {"dimension": "音画同步(AV1)", "message": "Clip_07 近景口型↔配音偏移 90ms", "affected_shots": ["Clip_07"]}
    block, reason = gate._strict_advisory_should_block(str(root), "第1集", "image", closeup, summary)
    assert block is True and reason == "对白近景口型"
    # 同样孤例但非近景（远景）→ 不升 block
    wide = {"dimension": "音画同步(AV1)", "message": "Clip_08 远景口型偏移", "affected_shots": ["Clip_08"]}
    block2, _ = gate._strict_advisory_should_block(str(root), "第1集", "image", wide, summary)
    assert block2 is False
    # 铁律 B11：demo 档位下对白近景口型偏移也升 block（demo 与 production 同标准·不再 demo 免单）
    monkeypatch.setenv("N2D_CONSISTENCY_PROFILE", "demo")
    block3, reason3 = gate._strict_advisory_should_block(str(root), "第1集", "image", closeup, summary)
    assert block3 is True and reason3 == "对白近景口型"


def test_video_required_evidence_missing_blocks_under_production(monkeypatch, tmp_path):
    root = tmp_path / "w"
    root.mkdir()
    monkeypatch.setenv("N2D_CONSISTENCY_PROFILE", "production")
    summary = {"by_dim": {"运动质量(MOT1)": {"warn": 1}}}
    row = {
        "dimension": "运动质量(MOT1)",
        "message": "视频含明确动作/运动镜，但缺 motion_quality 报告",
        "evidence_missing": True,
    }
    block, reason = gate._strict_advisory_should_block(str(root), "第1集", "video", row, summary)
    assert block is True and reason == "视频后验证据缺失"

    # 铁律 B11：demo 也升 block（视频后验证据缺失 demo 与 production 同标准·不再 demo 免单）
    monkeypatch.setenv("N2D_CONSISTENCY_PROFILE", "demo")
    block2, reason2 = gate._strict_advisory_should_block(str(root), "第1集", "video", row, summary)
    assert block2 is True and reason2 == "视频后验证据缺失"


# ── M5 跨集对比跨过缺失的中间集 → WARN ──
def test_cross_episode_skipped_intermediate_warns(tmp_path):
    gate.findings.clear()
    root = tmp_path / "w"
    root.mkdir()
    _write_overview(root, "第1集", "场景 冷宫：光位 左；轴线 左→右")
    _write_overview(root, "第3集", "场景 冷宫：光位 右；轴线 右→左")  # 第2集缺
    gate.check_cross_episode_contract(str(root), "第3集")
    assert any(f["dim"] == "跨集契约" and f["sev"] == "warn"
               and "跨过了缺失的中间集" in str(f["msg"]) for f in gate.findings)


# ── #3 跨集角色文字定义重派生 → WARN；引用了锚定相则放行 ──
_REG = [{"id": "CHAR_01", "name": "沈念 / 林婉儿",
         "forms": [{"anchor_phrase": "凤眼薄唇·乌黑半披素布发带·月白粗布旧宫装·左腕淡疤"}]}]


def test_cross_episode_character_redrive_warns(tmp_path):
    gate.findings.clear()
    root = tmp_path / "w"
    root.mkdir()
    _write_registry(str(root), _REG)
    _write_overview(root, "第2集", "本集 沈念 于金殿现身，红衣金发气场全开。")  # 零锚定相描述符
    gate.check_cross_episode_character_definition(str(root), "第2集")
    assert any(f["dim"] == "跨集角色定义" and f["sev"] == "warn" for f in gate.findings)


def test_cross_episode_character_anchor_cited_ok(tmp_path):
    gate.findings.clear()
    root = tmp_path / "w"
    root.mkdir()
    _write_registry(str(root), _REG)
    _write_overview(root, "第2集", "本集 沈念 月白粗布旧宫装 于冷宫现身。")  # 引用了锚定相 token
    gate.check_cross_episode_character_definition(str(root), "第2集")
    assert not any(f["dim"] == "跨集角色定义" for f in gate.findings)


# ── L8 N2D_SKIP_BACKEND_PROBE 旁路应留痕 ──
def test_skip_backend_probe_noted_in_warn(monkeypatch, tmp_path):
    gate.findings.clear()
    root = tmp_path / "w"
    root.mkdir()
    (root / "_设置.md").write_text("生图AI: Codex\n", encoding="utf-8")
    monkeypatch.setattr(gate.image_backends, "probe_backend", lambda s: ("unknown", "no probe"))
    monkeypatch.setenv("N2D_SKIP_BACKEND_PROBE", "1")
    gate.check_backend_reachable(str(root), "第1集")
    assert any(f["dim"] == "生图后端连通性" and "N2D_SKIP_BACKEND_PROBE 已设置" in str(f["msg"])
               for f in gate.findings)


def test_consistency_rule_registry_all_entries_callable():
    assert not gate._consistency_rule_registry_issues()


def test_production_mode_contract_sync_has_no_issues():
    assert not gate._production_mode_contract_issues()


# ── L6 孤儿守卫：check_* 定义了就必须有调用点（防再出 orphan）──
_KNOWN_ORPHAN_CHECKS: set = set()
# 2026-06：原两个孤儿 check_{markdown,storyboard}_cinematic_contract（纯转调 *_style_contract 的空壳）
# 已删；守卫现要求零孤儿——新增 check_* 必须有调用点，否则本测试 BLOCK。


def test_no_new_orphan_check_functions():
    # 多文件源码全集：增量3 按证据族把 check_ 迁到 gates/<family>.py（def 在那、run() 的调用在 gate.py），
    # 单读 gate.py 会把"已迁出但仍被调用"的闸误判成孤儿。并读 gate.py + gate_core.py + gates/*.py。
    import os as _os, glob as _glob
    sdir = _os.path.dirname(gate.__file__)
    parts = []
    for f in [_os.path.join(sdir, "gate.py"), _os.path.join(sdir, "gate_core.py"),
              *sorted(_glob.glob(_os.path.join(sdir, "gates", "*.py")))]:
        if _os.path.basename(f) == "__init__.py":
            continue
        if _os.path.isfile(f):
            parts.append(open(f, encoding="utf-8").read())
    src = "\n".join(parts)
    orphans = [n for n in dir(gate)
               if n.startswith("check_") and callable(getattr(gate, n))
               and src.count(n) < 2 and n not in _KNOWN_ORPHAN_CHECKS]
    assert not orphans, f"check_* 定义了却从未被调用（孤儿）: {orphans}"


# ── voice 一角一色跨集校验已接进 image/video/compose 三处 ──
def test_voice_cross_episode_wired_into_video_and_compose():
    src = _inspect.getsource(gate.run)
    assert src.count("check_voice_cross_episode(root, ep)") >= 3
    assert src.count("check_timing_manifest_complete(root, ep)") >= 3


# ── 物理尺寸对账：角色名取自 registry，不再写死 demo 名 ──
def _write_idreg_simple(root, characters):
    import json as _json
    p = gate.identity_registry_path(root)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        _json.dump({"characters": characters}, fh, ensure_ascii=False)


def _write_shots_md(root, ep, body):
    pd = os.path.join(root, "出图", ep, "prompt")
    os.makedirs(pd, exist_ok=True)
    with open(os.path.join(pd, "01_分镜出图.md"), "w", encoding="utf-8") as fh:
        fh.write(body)


def test_physical_scale_audit_reads_registry_names_not_hardcoded(tmp_path):
    gate.findings.clear()
    root = str(tmp_path)
    # 非 demo 角色名：旧硬编码实现会对这些名字一律静默放行（假绿灯），新实现应命中。
    _write_idreg_simple(root, [{"id": "CHAR_10", "name": "阿离"},
                                    {"id": "CHAR_11", "name": "墨尘"}])
    _write_shots_md(root, "第1集", "## 镜头 1\n目标：阿离 与 墨尘 对峙\n正文\n")
    gate.check_physical_scale_audit(root, "第1集")
    assert any(f["dim"] == "物理尺寸对账" for f in gate.findings)


def test_physical_scale_audit_silent_when_scale_declared(tmp_path):
    gate.findings.clear()
    root = str(tmp_path)
    _write_idreg_simple(root, [{"id": "CHAR_10", "name": "阿离"},
                                    {"id": "CHAR_11", "name": "墨尘"}])
    # `## 镜头1`（无空格）顺带验 robust split；已写「高半个头」→ 不告警。
    _write_shots_md(root, "第1集", "## 镜头1\n目标：阿离 与 墨尘，阿离比墨尘高半个头\n")
    gate.check_physical_scale_audit(root, "第1集")
    assert not any(f["dim"] == "物理尺寸对账" for f in gate.findings)


def test_physical_scale_audit_warns_when_declared_relative_scale_not_injected(tmp_path):
    gate.findings.clear()
    root = str(tmp_path)
    # registry 声明了 relative_scale，但本镜 prompt 没写它、也没任何关系词 → WARN「声明了却没注入」。
    _write_idreg_simple(root, [
        {"id": "CHAR_10", "name": "阿离",
         "forms": [{"form": "常态", "physical_scale": {"relative_scale": "比墨尘高半个头"}}]},
        {"id": "CHAR_11", "name": "墨尘"}])
    _write_shots_md(root, "第1集", "## 镜头 1\n目标：阿离 与 墨尘 对峙\n正文\n")
    gate.check_physical_scale_audit(root, "第1集")
    hit = [f for f in gate.findings if f["dim"] == "物理尺寸对账"]
    assert hit and "声明了相对身量" in hit[0]["msg"] and "比墨尘高半个头" in hit[0]["msg"]


def test_physical_scale_audit_silent_when_declared_scale_injected(tmp_path):
    gate.findings.clear()
    root = str(tmp_path)
    _write_idreg_simple(root, [
        {"id": "CHAR_10", "name": "阿离",
         "forms": [{"form": "常态", "physical_scale": {"relative_scale": "比墨尘高半个头"}}]},
        {"id": "CHAR_11", "name": "墨尘"}])
    # prompt 已写入声明的相对身量串 → 不告警。
    _write_shots_md(root, "第1集", "## 镜头 1\n目标：阿离 与 墨尘\n阿离比墨尘高半个头，对峙\n")
    gate.check_physical_scale_audit(root, "第1集")
    assert not any(f["dim"] == "物理尺寸对账" for f in gate.findings)


# ── #2 脸漂实测报告新鲜度闸（堵 measured-drift BLOCK 环静默退化） ──
def test_drift_report_freshness_pure_function_cases():
    # 首集（无历史出图）→ 无 finding
    assert gate.drift_report_freshness([], {"available": True, "episodes": []}) == []
    # 报告缺失但有历史出图 → WARN（不硬拦无 insightface 产线）
    out = gate.drift_report_freshness(["第1集"], {})
    assert len(out) == 1 and out[0][0] == gate.WARN
    # 未实测(available False) → WARN
    out = gate.drift_report_freshness(["第1集"], {"available": False, "episodes": ["第1集"]})
    assert len(out) == 1 and out[0][0] == gate.WARN
    # present-but-stale：实测了但漏覆盖历史集 → BLOCK（最危险）
    out = gate.drift_report_freshness(["第1集", "第2集"], {"available": True, "episodes": ["第1集"]})
    assert len(out) == 1 and out[0][0] == gate.BLOCK and "第2集" in out[0][1]
    # 覆盖齐全 → 无 finding
    assert gate.drift_report_freshness(
        ["第1集", "第2集"], {"available": True, "episodes": ["第1集", "第2集"]}) == []


def _fresh_write_png(root, ep):
    d = os.path.join(root, "出图", ep, "图片")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "Clip_01.png"), "wb") as fh:
        fh.write(b"x")


def _fresh_write_report(root, available, episodes):
    import json as _json
    d = os.path.join(root, "生产数据")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "identity_drift_report.json"), "w", encoding="utf-8") as fh:
        _json.dump({"available": available, "episodes": episodes}, fh, ensure_ascii=False)


def test_check_drift_report_freshness_blocks_stale_report(tmp_path):
    gate.findings.clear()
    root = str(tmp_path)
    _fresh_write_png(root, "第1集")             # 历史集已出图
    _fresh_write_report(root, True, [])         # 报告实测了但没覆盖第1集 → 陈旧
    gate.check_drift_report_freshness(root, "第2集")
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "脸漂报告新鲜度" for f in gate.findings)


def test_check_drift_report_freshness_warns_when_report_missing(tmp_path):
    gate.findings.clear()
    root = str(tmp_path)
    _fresh_write_png(root, "第1集")             # 不写报告
    gate.check_drift_report_freshness(root, "第2集")
    assert any(f["sev"] == gate.WARN and f["dim"] == "脸漂报告新鲜度" for f in gate.findings)
    assert not any(f["sev"] == gate.BLOCK for f in gate.findings)


def test_check_drift_report_freshness_silent_on_first_episode(tmp_path):
    gate.findings.clear()
    root = str(tmp_path)
    _fresh_write_png(root, "第1集")             # 只有当前集出图，无历史
    gate.check_drift_report_freshness(root, "第1集")
    assert not any(f["dim"] == "脸漂报告新鲜度" for f in gate.findings)


def test_check_drift_report_freshness_stale_escapes_with_env(tmp_path, monkeypatch):
    gate.findings.clear()
    monkeypatch.setenv("N2D_ALLOW_DEGRADED_QC", "1")
    root = str(tmp_path)
    _fresh_write_png(root, "第1集")
    _fresh_write_report(root, True, [])
    gate.check_drift_report_freshness(root, "第2集")
    assert any(f["sev"] == gate.WARN and "放行" in f["msg"] for f in gate.findings)
    assert not any(f["sev"] == gate.BLOCK for f in gate.findings)


# ── 核心长线角色未钉死锚点 → WARN（advisory） ──
def _ref_episode(root, ep, text):
    d = os.path.join(root, "脚本", ep)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "voiceover.txt"), "w", encoding="utf-8") as fh:
        fh.write(text)


def test_core_anchor_pinning_blocks_unpinned_referenced_core(tmp_path):
    """铁律：核心长线角色一个 form 都没钉死 anchor_sha = BLOCK（治脸漂根因默认开，demo 不降标准）。"""
    gate.findings.clear()
    root = str(tmp_path)
    _write_idreg_simple(root, [{"id": "CHAR_10", "name": "阿离", "scope": "贯穿全篇女主",
                                     "forms": [{"form": "常态", "reference_group": {"front": "x.png"}}]}])
    _ref_episode(root, "第1集", "CHAR_10 出场")
    gate.check_core_anchor_pinning(root, "第1集")
    assert any(f["dim"] == "锚点钉死" and f["sev"] == gate.BLOCK for f in gate.findings)


def test_core_anchor_pinning_silent_when_pinned(tmp_path):
    gate.findings.clear()
    root = str(tmp_path)
    _write_idreg_simple(root, [{"id": "CHAR_10", "name": "阿离", "scope": "贯穿全篇女主",
                                     "forms": [{"form": "常态", "anchor_sha": "deadbeef",
                                                "reference_group": {"front": "x.png"}}]}])
    _ref_episode(root, "第1集", "CHAR_10 出场")
    gate.check_core_anchor_pinning(root, "第1集")
    assert not any(f["dim"] == "锚点钉死" for f in gate.findings)


def test_core_anchor_pinning_skips_minor_role(tmp_path):
    gate.findings.clear()
    root = str(tmp_path)
    _write_idreg_simple(root, [{"id": "CHAR_99", "name": "门口杂役", "scope": "单元配角",
                                     "forms": [{"form": "常态", "reference_group": {"front": "x.png"}}]}])
    _ref_episode(root, "第1集", "CHAR_99 出场")
    gate.check_core_anchor_pinning(root, "第1集")
    assert not any(f["dim"] == "锚点钉死" for f in gate.findings)


# ── AI 生成合成内容标识（非阻断发布待办）────────────────────────────────────
def test_compliance_ai_labeling_good_passes_at_compose(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root)  # ai_labeling 已配置且 applied
    gate.check_compliance_manifest(str(root), "第1集", "compose")
    assert not any("ai_labeling" in f["loc"] for f in gate.findings)


def test_compliance_ai_labeling_missing_codes_reports_info_at_compose(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root, status_overrides={
        "ai_labeling.implicit_metadata": {"spec": "GB45438-2025", "service_provider_code": "TODO", "content_id": "TODO", "applied": False},
    })
    gate.check_compliance_manifest(str(root), "第1集", "compose")
    assert any(f["sev"] == gate.INFO and "ai_labeling" in f["loc"]
               and "service_provider_code" in f["msg"] for f in gate.findings)


def test_compliance_ai_labeling_missing_section_reports_info_at_compose(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root, status_overrides={"ai_labeling": "missing"})
    gate.check_compliance_manifest(str(root), "第1集", "compose")
    assert any(f["sev"] == gate.INFO and "ai_labeling" in f["loc"]
               and "缺 ai_labeling" in f["msg"] for f in gate.findings)


def test_compliance_ai_labeling_not_applied_reports_info_at_review(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    # 配置就绪但尚未由 compose 落标（pending/未 applied）
    _good_compliance(root, status_overrides={
        "ai_labeling.explicit_label": {"status": "pending", "text": "AI生成", "position": "bottom-right"},
        "ai_labeling.implicit_metadata": {"spec": "GB45438-2025", "service_provider_code": "SP-001", "content_id": "C-1", "applied": False},
    })
    gate.check_compliance_manifest(str(root), "第1集", "review")
    assert any(f["sev"] == gate.INFO and "ai_labeling" in f["loc"] and "status" in f["msg"] for f in gate.findings)
    assert any(f["sev"] == gate.INFO and "ai_labeling" in f["loc"] and "applied" in f["msg"] for f in gate.findings)


def test_compliance_ai_labeling_internal_only_downgrades_to_info(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root, status_overrides={
        "distribution_intent": "internal_only",
        "ai_labeling": "missing",
    })
    gate.check_compliance_manifest(str(root), "第1集", "compose")
    # 注意：loc 含 manifest 路径，pytest tmp 目录以测试名命名（含 "ai_labeling"），故按 msg token 过滤
    ai = [f for f in gate.findings if "缺 ai_labeling" in f["msg"]]
    assert ai and all(f["sev"] == gate.INFO for f in ai)  # 内部 demo 降 INFO


def test_compliance_ai_labeling_not_checked_at_image(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root, status_overrides={"ai_labeling": "missing"})
    gate.check_compliance_manifest(str(root), "第1集", "image")
    assert not any("ai_labeling" in f["msg"] for f in gate.findings)  # 标识只在 compose/review 检


def test_compliance_ai_labeling_applicable_false_needs_notes(tmp_path):
    gate.findings.clear()
    root = tmp_path / "制漫剧" / "测试剧"
    _write_identity_registry(tmp_path)
    _good_compliance(root, status_overrides={
        "ai_labeling": {"applicable": False, "notes": ""},
    })
    gate.check_compliance_manifest(str(root), "第1集", "compose")
    assert any(f["sev"] == gate.INFO and "ai_labeling" in f["loc"] and "applicable=false" in f["msg"] for f in gate.findings)


def test_strict_advisory_upgrades_high_dynamic_dims_in_production(tmp_path):
    # 高动态四维(MOT1/SPECV/CAM1/S2V)在 production 交付边界都应可升 BLOCK（CAM1/S2V 是本次补齐）。
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    summary = {"by_dim": {}}
    for dim in ("运动质量(MOT1)", "高动态成片证据(SPECV)", "相机空间轨迹(CAM1)", "主体视频一致(S2V)"):
        row = {"dimension": dim, "message": "缺成片证据", "verdict": "warn"}
        should, reason = gate._strict_advisory_should_block(str(root), "第1集", "review", row, summary)
        assert should is True, dim
        assert reason == "交付边界"


def test_strict_advisory_escalates_at_delivery_boundary_in_demo(tmp_path):
    """铁律 B11：交付边界(review)上 strict-advisory 维度 demo 也升 block——demo 与 production 同标准。
    （真·脆弱启发式 finding 仍由 add() 的 B10 守卫降回 WARN，故不会把低置信信号硬升成发布阻断。）"""
    root = tmp_path / "制漫剧" / "测试剧"
    root.mkdir(parents=True)
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: demo\n", encoding="utf-8")
    summary = {"by_dim": {}}
    row = {"dimension": "相机空间轨迹(CAM1)", "message": "缺成片证据", "verdict": "warn"}
    should, _ = gate._strict_advisory_should_block(str(root), "第1集", "review", row, summary)
    assert should is True


def test_action_beat_budget_blocks_full_exchange_in_one_clip(tmp_path):
    gate.findings.clear()
    # 一镜塞了 攻击+格挡+反击+命中 整段攻防回合 → 跨越 4 个节拍类别，应拦。
    root = _write_storyboard_with_clips(tmp_path, [
        {"id": "Clip 1", "template": "fight_exchange",
         "scene": "CHAR_01 出拳，对方格挡后反击命中", "duration": 4},
    ])
    gate.check_action_beat_budget(root, "第1集", "video")
    beat = [f for f in gate.findings if f["dim"] == "动作节拍预算"]
    assert beat and any("节拍类别" in f["msg"] for f in beat)


def test_action_beat_budget_production_upgrades_to_block(tmp_path):
    gate.findings.clear()
    root = _write_storyboard_with_clips(tmp_path, [
        {"id": "Clip 1", "template": "fight_exchange",
         "scene": "CHAR_01 出拳，对方格挡后反击命中", "duration": 4},
    ])
    (Path(root) / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    gate.check_action_beat_budget(root, "第1集", "video")
    assert any(f["dim"] == "动作节拍预算" and f["sev"] == gate.BLOCK for f in gate.findings)


def test_action_beat_budget_warns_when_beats_too_short(tmp_path):
    gate.findings.clear()
    # 两个节拍(攻击+命中)塞进 1.5s → 单拍 0.75s < 1.2s 下限，命中帧读不出 → WARN。
    root = _write_storyboard_with_clips(tmp_path, [
        {"id": "Clip 1", "template": "fight_exchange",
         "scene": "CHAR_01 挥剑命中追兵", "duration": 1.5},
    ])
    gate.check_action_beat_budget(root, "第1集", "video")
    beat = [f for f in gate.findings if f["dim"] == "动作节拍预算"]
    assert beat and all(f["sev"] == gate.WARN for f in beat)
    assert any("单拍" in f["msg"] for f in beat)


def test_action_beat_budget_passes_single_clean_beat(tmp_path):
    gate.findings.clear()
    # 一镜一动作、时长充裕 → 不拦。
    root = _write_storyboard_with_clips(tmp_path, [
        {"id": "Clip 1", "template": "fight_exchange",
         "scene": "CHAR_01 一记上勾拳命中追兵", "duration": 4},
    ])
    gate.check_action_beat_budget(root, "第1集", "video")
    assert not any(f["dim"] == "动作节拍预算" for f in gate.findings)


def test_action_beat_budget_ignores_structural_contract_keys(tmp_path):
    gate.findings.clear()
    # blocking / physics_guard / negative 是契约字段或禁令，不应被扫成 block/guard/counter 动作拍。
    root = _write_storyboard_with_clips(tmp_path, [
        {"id": "Clip 1", "template": "fight_exchange", "duration": 6,
         "scene": "CHAR_01 短促刺下，刀柄推进后对方眼神僵住",
         "template_contract": {
             "blocking": "CHAR_01 画左，CHAR_02 画右",
             "physics_guard": {"forbid": ["不要让 CHAR_02 突然反击"]},
             "negative": ["不要新增搏斗", "不要突然反击"],
         }},
    ])
    gate.check_action_beat_budget(root, "第1集", "video")
    assert not any(f["dim"] == "动作节拍预算" for f in gate.findings)


def test_action_beat_budget_allows_readable_attack_counter_impact_without_block(tmp_path):
    gate.findings.clear()
    # 没有格挡/招架的 attack→counter/impact 可用首中尾锚或实现分解承接，不等同完整攻防回合。
    root = _write_storyboard_with_clips(tmp_path, [
        {"id": "Clip 1", "template": "fight_exchange", "duration": 9,
         "scene": "CHAR_01 扑向对手，对手一脚反击命中，CHAR_01 倒地"},
    ])
    gate.check_action_beat_budget(root, "第1集", "video")
    assert not any(f["dim"] == "动作节拍预算" for f in gate.findings)


def test_storyboard_high_motion_requires_unexemptable_endframe(tmp_path):
    gate.findings.clear()
    # 末镜也是高速运动镜(fight_exchange)，给了 exempt 理由想豁免首尾帧 → 仍必须 need_endframe=true，BLOCK。
    e = "出图/第1集/图片/镜头1_end.png"
    f = "出图/第1集/图片/镜头1.png"
    root = _write_storyboard_with_clips(tmp_path, [
        {"template": "fight_exchange", "firstframe_png": f,
         "continuity": {"start_state": "s", "end_state": "e", "transition": "硬切",
                        "need_endframe": False, "endframe_exempt_reason": "末镜想省一张"}},
    ])
    gate.check_storyboard_contract(str(root), "第1集")
    hm = [x for x in gate.findings if x["dim"] == "尾帧" and "高速运动镜" in x["msg"]]
    assert hm and all(x["sev"] == gate.BLOCK for x in hm)


def test_storyboard_high_motion_endframe_true_passes(tmp_path):
    gate.findings.clear()
    e = "出图/第1集/图片/镜头1_end.png"
    f = "出图/第1集/图片/镜头1.png"
    root = _write_storyboard_with_clips(tmp_path, [
        {"template": "fight_exchange", "firstframe_png": f,
         "continuity": {"start_state": "s", "end_state": "e", "transition": "硬切",
                        "need_endframe": True, "endframe_png": e}},
    ])
    _touch_png(root, f)
    _touch_png(root, e)
    gate.check_storyboard_contract(str(root), "第1集")
    assert not any(x["dim"] == "尾帧" and "高速运动镜" in x["msg"] for x in gate.findings)


def test_scene_atlas_missing_blocks_production_core_loc(tmp_path):
    # G-I2：production 核心 LOC 缺 scene_atlas（场景四视图）→ BLOCK
    gate.findings.clear()
    root = Path(_write_asset_registry(tmp_path, make_assets=True))
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    gate.check_asset_reference_registry(str(root), require_reference_assets=True)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "场景多机位锁(G-I2)" for f in gate.findings)


def test_scene_atlas_front_plus_alt_passes(tmp_path):
    gate.findings.clear()
    data = _asset_registry()
    data["assets"][0]["scene_atlas"] = {
        "base_views": {
            "front": "出图/共享/图片/定妆_冷宫寝殿_正机位.png",
            "back": "出图/共享/图片/定妆_冷宫寝殿_反打.png",
        }
    }
    root = Path(_write_asset_registry(tmp_path, data, make_assets=True))
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    gate.check_asset_reference_registry(str(root), require_reference_assets=True)
    assert not any(f["dim"] == "场景多机位锁(G-I2)" for f in gate.findings)


def test_scene_atlas_single_angle_exempt(tmp_path):
    gate.findings.clear()
    data = _asset_registry()
    data["assets"][0]["scene_atlas"] = {"single_angle": True}
    root = Path(_write_asset_registry(tmp_path, data, make_assets=True))
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    gate.check_asset_reference_registry(str(root), require_reference_assets=True)
    assert not any(f["dim"] == "场景多机位锁(G-I2)" for f in gate.findings)


def test_scene_atlas_only_front_blocks(tmp_path):
    gate.findings.clear()
    data = _asset_registry()
    data["assets"][0]["scene_atlas"] = {
        "base_views": {"front": "出图/共享/图片/定妆_冷宫寝殿_正机位.png"}
    }
    root = Path(_write_asset_registry(tmp_path, data, make_assets=True))
    (root / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    gate.check_asset_reference_registry(str(root), require_reference_assets=True)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "场景多机位锁(G-I2)" for f in gate.findings)


def test_scene_atlas_required_in_demo_for_core_location(tmp_path):
    """铁律 B11：核心/高频 LOC 的场景多机位锁(G-I2)demo 也强制——曾 production-only。
    （正是'场景共享图'那一类，与角色四视图同标准；单机位场景可显式 single_angle=true 豁免。）"""
    gate.findings.clear()
    root = Path(_write_asset_registry(tmp_path, make_assets=True))
    gate.check_asset_reference_registry(str(root), require_reference_assets=True)
    assert any(f["dim"] == "场景多机位锁(G-I2)" for f in gate.findings)


# ── ③ 系列留存闸 check_series_retention_gate（流程自审 2026-06-25 落地）──

_SERIES_DUP_VO = """[镜头1·沈念·愤怒·快] 她当众打脸，真相大白。  ⚡钩子
[镜头2·旁白·低沉] 没想到竟是逆袭报仇。  💥爽点
[镜头3·沈念·痛快·快] 这一局翻盘了。  🪝集尾
"""

_SERIES_DIFF_VO = """[镜头1·林川·茫然·慢] 清晨的码头很安静。
[镜头2·林川·平静·慢] 他慢慢收起渔网。
[镜头3·旁白·低沉] 海风吹过。
"""


def _mk_series(root: Path, mapping: dict) -> None:
    for ep, vo in mapping.items():
        d = root / "脚本" / ep
        d.mkdir(parents=True, exist_ok=True)
        (d / "voiceover.txt").write_text(vo, encoding="utf-8")


def test_series_retention_gate_under_3_eps_requires_pilot_contract(tmp_path):
    gate.findings.clear()
    _mk_series(tmp_path, {"第1集": _SERIES_DUP_VO, "第2集": _SERIES_DUP_VO})
    gate.check_series_retention_gate(str(tmp_path), "第1集", "compose")
    assert any(
        f["sev"] == gate.BLOCK and f.get("code") == "pilot_arc_contract_missing"
        for f in gate.findings
    )


def test_series_retention_gate_under_3_eps_complete_pilot_contract_passes(tmp_path):
    gate.findings.clear()
    _mk_series(tmp_path, {"第1集": _SERIES_DUP_VO, "第2集": _SERIES_DUP_VO})
    pilot = tmp_path / "设定库" / "pilot_arc_contract.json"
    pilot.parent.mkdir(parents=True, exist_ok=True)
    pilot.write_text(json.dumps({
        "series_promise": "重生女主查出赐死真凶并翻盘",
        "protagonist_desire": "活下来并夺回身份",
        "repeatable_pleasure_loop": "被压迫-发现线索-反击打脸-抛新真相",
        "long_question": "幕后主使是谁",
        "first_payoff_ep": "第1集",
        "first_complication_ep": "第2集",
        "first_reversal_ep": "第2集",
    }, ensure_ascii=False), encoding="utf-8")

    gate.check_series_retention_gate(str(tmp_path), "第1集", "compose")

    assert not any(f["dim"] == gate.SERIES_RETENTION_DIM for f in gate.findings)


def test_series_retention_gate_production_dup_blocks_implicated_ep(tmp_path):
    # 第1集↔第2集 桥段指纹雷同 + production + compose 交付边界 → 牵涉的当前集升 BLOCK
    gate.findings.clear()
    _mk_series(tmp_path, {"第1集": _SERIES_DUP_VO, "第2集": _SERIES_DUP_VO, "第3集": _SERIES_DIFF_VO})
    (tmp_path / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    gate.check_series_retention_gate(str(tmp_path), "第1集", "compose")
    hits = [f for f in gate.findings if f["dim"] == gate.SERIES_RETENTION_DIM]
    assert any(f["sev"] == gate.BLOCK and "重合" in f["msg"] for f in hits)


def test_series_retention_gate_demo_dup_only_warns(tmp_path):
    # 同样雷同，但显式 demo/宽松 档 → 只 WARN 不 BLOCK（窄作用域，不惊扰非交付/demo）。
    # 注：compose 是交付边界，无显式档会被自动推断为 production，故这里必须显式写 demo。
    gate.findings.clear()
    _mk_series(tmp_path, {"第1集": _SERIES_DUP_VO, "第2集": _SERIES_DUP_VO, "第3集": _SERIES_DIFF_VO})
    (tmp_path / "_设置.md").write_text("# _设置\n- 一致性严格度: demo\n", encoding="utf-8")
    gate.check_series_retention_gate(str(tmp_path), "第1集", "compose")
    hits = [f for f in gate.findings if f["dim"] == gate.SERIES_RETENTION_DIM]
    assert hits and not any(f["sev"] == gate.BLOCK for f in hits)


def test_series_retention_gate_non_implicated_ep_info_not_block(tmp_path):
    # 第3集不在任何 dup 里 → 系列 dup finding 对它只 INFO（可见不拦本集），即便 production
    gate.findings.clear()
    _mk_series(tmp_path, {"第1集": _SERIES_DUP_VO, "第2集": _SERIES_DUP_VO, "第3集": _SERIES_DIFF_VO})
    (tmp_path / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    gate.check_series_retention_gate(str(tmp_path), "第3集", "compose")
    dup_hits = [f for f in gate.findings if f["dim"] == gate.SERIES_RETENTION_DIM and "重合" in f["msg"]]
    assert dup_hits and all(f["sev"] == gate.INFO for f in dup_hits)


# --- C1/C2: 有意不连续签收降级 native 一致性 BLOCK 接到 gate ------------------

class _FakeProc:
    def __init__(self, stdout, returncode=0, stderr=""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


def _audit_json(dim, *, sev="block", shots=("Clip_03",), warn=0, block=1):
    return json.dumps({
        "summary": {
            "total_block": block,
            "precision_level": "full",
            "by_dim": {dim: {"block": block, "warn": warn, "ok": 0, "n": block + warn}},
        },
        "findings": [{
            "severity": sev,
            "dimension": dim,
            "message": "白天↔黑夜 2 级跳（时辰硬不连续）",
            "affected_shots": list(shots),
            "affected_artifacts": ["出图/第1集/图片/clip3.png"],
            "return_to_stage": "image",
            "risk_score": 0.50,
        }],
    }, ensure_ascii=False)


def _patch_audit(monkeypatch, payload, returncode=1):
    monkeypatch.setattr(gate.subprocess, "run",
                        lambda *a, **k: _FakeProc(payload, returncode=returncode))


def _write_intentional(root, ep, dim, *, clip="Clip_03", expires="2099-01-01",
                       reason="主角回忆闪回，刻意把夜景切成白日逆光"):
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    (prod / f"intentional_discontinuity_{ep}.json").write_text(json.dumps({
        "kind": "n2d_intentional_discontinuity_manifest",
        "accepted": [{
            "clip_id": clip, "dimension": dim, "reason": reason,
            "signoff": "导演A", "expires_at": expires,
        }],
    }, ensure_ascii=False), encoding="utf-8")


def test_intentional_signoff_downgrades_native_w1_block(tmp_path, monkeypatch):
    gate.findings.clear()
    _intentional_module_reset()
    _write_intentional(tmp_path, "第1集", "天气时辰(W1)")
    _patch_audit(monkeypatch, _audit_json("天气时辰(W1)"))
    gate.check_consistency_audit_gate(str(tmp_path), "第1集", stage="image")
    w1 = [f for f in gate.findings if f["dim"] == "天气时辰(W1)"]
    assert w1 and all(f["sev"] == gate.WARN for f in w1)
    assert any("有意不连续已签收" in f["msg"] for f in w1)
    # 不得因 audit 退出码非 0 误补 generic block
    assert not any(f["dim"] == "一致性总审" and f["sev"] == gate.BLOCK
                   and "退出码" in f["msg"] for f in gate.findings)


def test_native_w1_block_without_manifest_stays_block(tmp_path, monkeypatch):
    gate.findings.clear()
    _intentional_module_reset()
    _patch_audit(monkeypatch, _audit_json("天气时辰(W1)"))
    gate.check_consistency_audit_gate(str(tmp_path), "第1集", stage="image")
    assert any(f["dim"] == "天气时辰(W1)" and f["sev"] == gate.BLOCK for f in gate.findings)


def test_video_evidence_native_block_downgraded_by_advisory_signoff(tmp_path, monkeypatch):
    gate.findings.clear()
    prod = tmp_path / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    (prod / "consistency_advisory_signoff_第1集.json").write_text(json.dumps({
        "accepted": [{
            "accepted": True,
            "dimension": "视频语义一致(VSEM)",
            "message_contains": "DINOv2 whole-frame similarity is below",
            "shot": "Clip_07",
            "reviewer": "qa",
            "reason": "参考尾帧与剧本目标错位，人工复核视频落幅可接受",
            "expires_at": "2099-01-01",
        }]
    }, ensure_ascii=False), encoding="utf-8")
    payload = {
        "summary": {
            "precision_level": "full",
            "by_dim": {"视频语义一致(VSEM)": {"block": 1, "warn": 0, "ok": 0, "n": 1}},
        },
        "findings": [{
            "severity": "block",
            "dimension": "视频语义一致(VSEM)",
            "message": "DINOv2 whole-frame similarity is below the configured VSEM threshold.",
            "affected_shots": ["Clip_07"],
            "affected_artifacts": ["生产数据/video_semantic_consistency_第1集.json"],
            "return_to_stage": "video",
            "risk_score": 0.50,
        }],
    }
    _patch_audit(monkeypatch, json.dumps(payload, ensure_ascii=False))
    gate.check_consistency_audit_gate(str(tmp_path), "第1集", stage="video")
    vsem = [f for f in gate.findings if f["dim"] == "视频语义一致(VSEM)"]
    assert vsem and all(f["sev"] == gate.WARN for f in vsem)
    assert any("consistency_advisory_signoff 已签收" in f["msg"] for f in vsem)
    assert not any(f["sev"] == gate.BLOCK for f in gate.findings)


def test_intentional_signoff_ignored_for_ineligible_face_dim(tmp_path, monkeypatch):
    gate.findings.clear()
    _intentional_module_reset()
    # 即便写了 manifest，脸(G1) 不在可签收维度 → 仍 BLOCK
    _write_intentional(tmp_path, "第1集", "脸(G1)")
    _patch_audit(monkeypatch, _audit_json("脸(G1)"))
    gate.check_consistency_audit_gate(str(tmp_path), "第1集", stage="image")
    assert any(f["dim"] == "脸(G1)" and f["sev"] == gate.BLOCK for f in gate.findings)


def test_intentional_signoff_expired_does_not_downgrade(tmp_path, monkeypatch):
    gate.findings.clear()
    _intentional_module_reset()
    _write_intentional(tmp_path, "第1集", "天气时辰(W1)", expires="2000-01-01")
    _patch_audit(monkeypatch, _audit_json("天气时辰(W1)"))
    gate.check_consistency_audit_gate(str(tmp_path), "第1集", stage="image")
    assert any(f["dim"] == "天气时辰(W1)" and f["sev"] == gate.BLOCK for f in gate.findings)


def test_intentional_signoff_short_reason_rejected(tmp_path, monkeypatch):
    gate.findings.clear()
    _intentional_module_reset()
    _write_intentional(tmp_path, "第1集", "天气时辰(W1)", reason="短")  # <8 chars
    _patch_audit(monkeypatch, _audit_json("天气时辰(W1)"))
    gate.check_consistency_audit_gate(str(tmp_path), "第1集", stage="image")
    assert any(f["dim"] == "天气时辰(W1)" and f["sev"] == gate.BLOCK for f in gate.findings)


def _intentional_module_reset():
    # 清掉模块级缓存，避免跨 test 复用（importlib 缓存本身无状态，但保持显式）
    gate._intentional_discontinuity_module.__dict__.pop("mod", None)


# --- P1: 预算前叙事/留存地板接到批量 gate(image_preflight) 路径 ----------------

class _BeatProc:
    def __init__(self, stdout, returncode=0, stderr=""):
        self.stdout = stdout; self.returncode = returncode; self.stderr = stderr


def _patch_beat(monkeypatch, ep_json=None, series_json=None):
    def fake_run(cmd, *a, **k):
        argv = " ".join(str(c) for c in cmd)
        if "--series" in argv:
            return _BeatProc(json.dumps(series_json or {}, ensure_ascii=False))
        return _BeatProc(json.dumps(ep_json or {}, ensure_ascii=False))
    monkeypatch.setattr(gate.subprocess, "run", fake_run)


def _mk_ep_script(root, ep="第1集"):
    (root / "脚本" / ep).mkdir(parents=True, exist_ok=True)
    (root / "脚本" / ep / "voiceover.txt").write_text("台词", encoding="utf-8")


_MUST_HOOK = {"findings": [
    {"severity": "must", "code": "missing_first_3s_visual_hook", "msg": "storyboard.json 缺 first_3s_visual_hook"},
    {"severity": "warn", "code": "x", "msg": "次要"},
]}


def test_episode_narrative_floor_production_blocks_must(tmp_path, monkeypatch):
    gate.findings.clear()
    _mk_ep_script(tmp_path)
    (tmp_path / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    _patch_beat(monkeypatch, ep_json=_MUST_HOOK)
    gate.check_episode_narrative_floor(str(tmp_path), "第1集", "image_preflight")
    hits = [f for f in gate.findings if f["dim"] == gate.SERIES_RETENTION_DIM and f["sev"] == gate.BLOCK]
    assert hits and "预算前留存地板" in hits[0]["msg"]
    # warn 级 finding 不升 block
    assert not any("次要" in f["msg"] for f in gate.findings if f["sev"] == gate.BLOCK)


def test_episode_narrative_floor_demo_warns_not_blocks(tmp_path, monkeypatch):
    gate.findings.clear()
    _mk_ep_script(tmp_path)  # 无 _设置=demo
    _patch_beat(monkeypatch, ep_json=_MUST_HOOK)
    gate.check_episode_narrative_floor(str(tmp_path), "第1集", "image_preflight")
    assert any(f["dim"] == gate.SERIES_RETENTION_DIM and f["sev"] == gate.WARN for f in gate.findings)
    assert not any(f["sev"] == gate.BLOCK for f in gate.findings)


def test_episode_narrative_floor_signoff_downgrades(tmp_path, monkeypatch):
    gate.findings.clear()
    _mk_ep_script(tmp_path)
    (tmp_path / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    (tmp_path / "生产数据").mkdir(exist_ok=True)
    (tmp_path / "生产数据" / "consistency_advisory_signoff_第1集.json").write_text(json.dumps({
        "accepted": [{"accepted": True, "reviewer": "导演", "reason": "刻意慢热开场",
                      "expires_at": "2099-01-01", "dimension": gate.SERIES_RETENTION_DIM,
                      "message_contains": "first_3s_visual_hook"}]}), encoding="utf-8")
    _patch_beat(monkeypatch, ep_json=_MUST_HOOK)
    gate.check_episode_narrative_floor(str(tmp_path), "第1集", "image_preflight")
    assert not any(f["sev"] == gate.BLOCK for f in gate.findings)


def test_episode_narrative_floor_skips_non_preflight(tmp_path, monkeypatch):
    gate.findings.clear()
    _mk_ep_script(tmp_path)
    _patch_beat(monkeypatch, ep_json=_MUST_HOOK)
    gate.check_episode_narrative_floor(str(tmp_path), "第1集", "image")  # 非 image_preflight
    assert not gate.findings


def test_cold_open_chain_blocks_at_image_preflight_production(tmp_path, monkeypatch):
    gate.findings.clear()
    for i in (1, 2, 3):
        _mk_ep_script(tmp_path, f"第{i}集")
    (tmp_path / "_设置.md").write_text("# _设置\n- 一致性严格度: production\n", encoding="utf-8")
    series = {"duplicates": [], "highlight_climax_findings": [],
              "cold_open_chain_findings": [{"severity": "warn", "code": "p2_slow_next_open",
                                            "msg": "第3集 开场未接住第2集硬断"}]}
    _patch_beat(monkeypatch, series_json=series)
    gate.check_series_retention_gate(str(tmp_path), "第3集", "image_preflight")
    assert any(f["dim"] == gate.SERIES_RETENTION_DIM and f["sev"] == gate.BLOCK
               and "冷开场" in f["msg"] for f in gate.findings)


# ── 掣肘三：跨检测器相关性升级——同一张脸 crop 派生的检测器不得互证为独立证据 ──

def _warn_hi(dim, shot, family=None):
    f = {"sev": gate.WARN, "dim": dim, "loc": shot, "msg": f"{dim} 漂移",
         "risk_score": 0.8, "affected_shots": [shot], "affected_artifacts": [shot]}
    if family is not None:
        f["evidence_family"] = family
    return f


def test_correlate_no_upgrade_on_single_face_family():
    """一张脸漂同时触发 脸/发型/表情/比例——全归 face_embedding 单一族，
    不得自我互证升级成 BLOCK（去除 {face_embedding, unknown}=2 虚假路径）。"""
    findings = [
        _warn_hi("脸一致(G1)", "Clip_03"),
        _warn_hi("发型一致(HAIR)", "Clip_03"),
        _warn_hi("状态化表情(EXP2)", "Clip_03"),
        _warn_hi("比例一致(SCALE)", "Clip_03"),
    ]
    ups = gate.correlate_findings(findings)
    assert ups == [], "单一 face_embedding 根因不应升级为一致性总审 BLOCK"


def test_correlate_upgrades_on_genuinely_independent_families():
    """脸 + 音画 + 场景几何 三个真正独立证据族同镜漂移→合法升级 BLOCK。"""
    findings = [
        _warn_hi("脸一致(G1)", "Clip_05"),
        _warn_hi("音画口型(LIP)", "Clip_05"),
        _warn_hi("场景轴线(AXIS)", "Clip_05"),
    ]
    ups = gate.correlate_findings(findings)
    assert any(u["dim"] == "一致性总审" and u["sev"] == gate.BLOCK for u in ups)


def test_correlate_unknown_family_cannot_be_second_family():
    """两条无法归类(unknown)+一条 face 不构成 ≥2 named 独立族→不升级。"""
    findings = [
        _warn_hi("脸一致(G1)", "Clip_07"),
        _warn_hi("某未分类维度A", "Clip_07", family="unknown"),
        _warn_hi("某未分类维度B", "Clip_07", family="unknown"),
    ]
    ups = gate.correlate_findings(findings)
    assert ups == [], "unknown 默认桶不得充当第二个独立证据族"


def test_evidence_family_disambiguates_aspect_ratio_from_face():
    # P1-8：歧义子串「比例」分流——画面比例(格式) 与 身高比例(身份) 不再误并；泛义「标记」不入脸族。
    f = gate._default_evidence_family
    assert f("画幅", "画面比例 16:9 与首帧不符") == "frame_format"
    assert f("身高比例(R1)", "跨集体型变化") == "face_embedding"   # 身体比例属身份，仍归脸族
    assert f("辨识标记(MK1)", "疤痕缺失") == "face_embedding"
    assert f("节奏", "第3处时间标记点") != "face_embedding"        # 泛义「标记」不误并入脸族
    assert f("脸(G1)", "崩脸") == "face_embedding"


def test_heuristic_confidence_block_auto_downgrades_to_warn():
    # P1：脆弱启发式不得硬阻断——confidence="heuristic" 的 BLOCK 自动降 WARN。
    gate.findings.clear()
    gate.add(gate.BLOCK, "测试启发式", "loc", "某关键词阈值命中", confidence="heuristic")
    assert len(gate.findings) == 1
    f = gate.findings[0]
    assert f["sev"] == gate.WARN
    assert "启发式低置信" in f["msg"]
    assert f.get("risk_score") is not None  # 降级后仍按 WARN 赋 risk_score


def test_non_heuristic_block_stays_block():
    # 确定性闸（无 heuristic 标记）不受影响，照常 BLOCK。
    gate.findings.clear()
    gate.add(gate.BLOCK, "确定性闸", "loc", "硬错误")
    assert gate.findings[0]["sev"] == gate.BLOCK


def test_heuristic_confidence_warn_unchanged():
    # 已是 WARN 的启发式：标记只是元数据，行为不变。
    gate.findings.clear()
    gate.add(gate.WARN, "测试启发式", "loc", "声纹漂移", confidence="heuristic")
    f = gate.findings[0]
    assert f["sev"] == gate.WARN
    assert f.get("confidence") == "heuristic"
    assert "自动降为 WARN" not in f["msg"]


def test_heuristic_demotion_is_counted():
    # #3：非 locked 维度的启发式降级要逐条计账（供 run() 末尾 rollup 显式可查）。
    gate.findings.clear()
    gate._HEURISTIC_BLOCK_DEMOTIONS.clear()
    gate.add(gate.BLOCK, "某启发式维度", "loc", "msg", confidence="heuristic")
    assert len(gate._HEURISTIC_BLOCK_DEMOTIONS) == 1


def test_charter_locked_dim_heuristic_block_not_demoted():
    # #3 核心：charter-locked 维度即便信号是启发式也不许静默降级——lock 胜过 demotion。
    gate.findings.clear()
    gate._HEURISTIC_BLOCK_DEMOTIONS.clear()
    locked = next(iter(gate._charter_locked_dims()))
    gate.add(gate.BLOCK, locked, "loc", "msg", confidence="heuristic")
    assert gate.findings[0]["sev"] == gate.BLOCK
    assert "不降级" in gate.findings[0]["msg"]
    assert len(gate._HEURISTIC_BLOCK_DEMOTIONS) == 0  # 未计入降级账本


def test_heuristic_demotion_rollup_counts_dims():
    roll = gate.heuristic_demotion_rollup([{"dim": "A"}, {"dim": "B"}, {"dim": "A"}], "image")
    assert roll is not None
    sev, loc, msg = roll
    assert sev == gate.WARN and "3 条" in msg and "A" in msg and "B" in msg
    assert gate.heuristic_demotion_rollup([], "image") is None


def _write_skill_baseline(root, sf, mutate=None):
    """写一份 = 当前 skill 树的内容基线到 root，可选把某文件 hash 改成旧值模拟"自基线后改动"。"""
    relevant = sf.relevant_skills_for_diff("image")
    snap = sf.snapshot_for_skills(sf.REPO_ROOT, sf.REPO_SKILLS, relevant)
    if mutate:
        assert mutate in snap["files"], f"{mutate} 不在当前快照里（测试前置已变）"
        snap["files"][mutate] = "0" * 64
    path = sf.snapshot_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, ensure_ascii=False)


def test_skill_freshness_warns_on_material_drift_before_spend():
    """花钱出图前：生产物料的 skill（n2d-image）自基线后改动 → WARN·路由 n2d-update；
    fresh / 无基线 / 仅 gate-only 改动各自的分级。"""
    import tempfile

    sf = gate.skill_freshness
    assert sf is not None

    # 1) material drift（n2d-image/SKILL.md 改了）→ WARN，消息含 n2d-image 与 update_plan 路由
    with tempfile.TemporaryDirectory() as td:
        _write_skill_baseline(td, sf, mutate="skills/n2d-image/SKILL.md")
        gate.findings.clear()
        gate.check_skill_freshness(td, "第1集", "image_preflight")
        hit = [f for f in gate.findings if f["dim"] == "物料新鲜度"]
        assert hit and hit[0]["sev"] == gate.WARN
        assert "n2d-image" in hit[0]["msg"] and "update_plan.py check" in hit[0]["msg"]

    # 2) fresh（基线 == 当前）→ 无声通过
    with tempfile.TemporaryDirectory() as td:
        _write_skill_baseline(td, sf)
        gate.findings.clear()
        gate.check_skill_freshness(td, "第1集", "image_preflight")
        assert not any(f["dim"] == "物料新鲜度" for f in gate.findings)

    # 3) 无基线 → 静默（无可比对对象，不在每个无基线作品的预检里 nag）
    with tempfile.TemporaryDirectory() as td:
        gate.findings.clear()
        gate.check_skill_freshness(td, "第1集", "image_preflight")
        assert not any(f["dim"] == "物料新鲜度" for f in gate.findings)

    # 4) 仅 gate-only 改动（image_qc.py）→ INFO（横切/QC层），不升 WARN
    with tempfile.TemporaryDirectory() as td:
        _write_skill_baseline(td, sf, mutate="skills/n2d-image/scripts/image_qc.py")
        gate.findings.clear()
        gate.check_skill_freshness(td, "第1集", "image_preflight")
        hit = [f for f in gate.findings if f["dim"] == "物料新鲜度"]
        assert hit and not any(f["sev"] == gate.WARN for f in hit)


# ───────────────────────────────────────────────────────────────────────────
# 标记解析闸（花钱前 referenced⊆registered）：写错 id 不许进付费出图/出视频
# 运行：cd skills/n2d-review/scripts && python -m pytest test_gate.py -k referenced_markers
# ───────────────────────────────────────────────────────────────────────────
def _setup_marker_root(td, *, reg_chars, reg_assets, ref_text):
    """在 td 下铺 identity/asset registry + 一集分镜文本，返回 root。"""
    root = td
    os.makedirs(os.path.join(root, "脚本", "第1集"), exist_ok=True)
    os.makedirs(os.path.dirname(gate.identity_registry_path(root)), exist_ok=True)
    with open(gate.identity_registry_path(root), "w", encoding="utf-8") as fh:
        json.dump({"characters": [{"id": c} for c in reg_chars]}, fh, ensure_ascii=False)
    with open(gate.asset_registry_path(root), "w", encoding="utf-8") as fh:
        json.dump({"assets": [{"id": a} for a in reg_assets]}, fh, ensure_ascii=False)
    with open(os.path.join(root, "脚本", "第1集", "storyboard.json"), "w", encoding="utf-8") as fh:
        fh.write(ref_text)
    return root


def test_referenced_markers_unknown_id_blocks(tmp_path):
    # 分镜引用 CHAR_99 / PROP_88，注册层只有 CHAR_01 / LOC_01 → 二者各一条 BLOCK
    root = _setup_marker_root(
        str(tmp_path),
        reg_chars=["CHAR_01"],
        reg_assets=["LOC_01"],
        ref_text="资产身份注册层：CHAR_01 与 CHAR_99；资产引用注册层：LOC_01、PROP_88。",
    )
    gate.findings.clear()
    gate.check_referenced_markers_resolve(root, "第1集")
    blocks = [f for f in gate.findings if f["sev"] == gate.BLOCK]
    msgs = " ".join(f["msg"] for f in blocks)
    assert "CHAR_99" in msgs and "PROP_88" in msgs
    # 已登记的不报
    assert "CHAR_01" not in msgs and "LOC_01" not in msgs
    # 未知标记必须回退到出图阶段处置
    assert all(f.get("return_to_stage") == "image" for f in blocks)


def test_referenced_markers_all_registered_passes(tmp_path):
    root = _setup_marker_root(
        str(tmp_path),
        reg_chars=["CHAR_01", "CHAR_02"],
        reg_assets=["LOC_01", "PROP_05"],
        ref_text="CHAR_01 与 CHAR_02 在 LOC_01 使用 PROP_05。",
    )
    gate.findings.clear()
    gate.check_referenced_markers_resolve(root, "第1集")
    assert not gate.findings


def test_referenced_markers_registered_ids_allow_readable_suffixes(tmp_path):
    root = _setup_marker_root(
        str(tmp_path),
        reg_chars=["CHAR_01"],
        reg_assets=["LOC_01", "WEAPON_01", "MOUNT_GROUP_01"],
        ref_text=(
            "CHAR_01 在 LOC_01_荒野尸骸战场 手持 WEAPON_01_横刀，"
            "旁边是 MOUNT_GROUP_01_飞鹰门马匹与火把。"
        ),
    )
    gate.findings.clear()
    gate.check_referenced_markers_resolve(root, "第1集")
    assert not gate.findings


def test_referenced_markers_empty_registry_delegates(tmp_path):
    # 注册层为空（缺登记）→ 本闸不重复报错，交由 check_identity_registry/asset 各自 BLOCK
    root = _setup_marker_root(
        str(tmp_path),
        reg_chars=[],
        reg_assets=[],
        ref_text="资产身份注册层：CHAR_07；资产引用注册层：LOC_09。",
    )
    gate.findings.clear()
    gate.check_referenced_markers_resolve(root, "第1集")
    assert not gate.findings


# ───────────────────────────────────────────────────────────────────────────
# 内容级新鲜度（PNG 指纹）：报告覆盖了集、但图重出过（指纹不符）= BLOCK（陈旧绿最隐蔽的一种）
# 运行：cd skills/n2d-review/scripts && python -m pytest test_gate.py -k content_fingerprint
# ───────────────────────────────────────────────────────────────────────────
def test_drift_report_freshness_content_fingerprint_pure():
    base = {"available": True, "episodes": ["第1集"]}
    # 指纹匹配 → 无 finding
    rep_ok = dict(base, png_fingerprints={"第1集": "abc"})
    assert gate.drift_report_freshness(["第1集"], rep_ok, {"第1集": "abc"}) == []
    # 指纹不符（图重出过）→ BLOCK
    out = gate.drift_report_freshness(["第1集"], rep_ok, {"第1集": "DIFFERENT"})
    assert len(out) == 1 and out[0][0] == gate.BLOCK and "内容级陈旧" in out[0][1]
    # 报告无 png_fingerprints 字段 + 当前有 PNG → WARN（无法证明内容新鲜）
    out = gate.drift_report_freshness(["第1集"], base, {"第1集": "abc"})
    assert len(out) == 1 and out[0][0] == gate.WARN and "内容指纹" in out[0][1]
    # current_fingerprints=None（旧调用）→ 不做内容核对，向后兼容
    assert gate.drift_report_freshness(["第1集"], rep_ok) == []
    # 报告缺该集指纹但当前该集有 PNG → BLOCK（按内容不可证升级处理）
    rep_partial = dict(base, png_fingerprints={})
    out = gate.drift_report_freshness(["第1集"], rep_partial, {"第1集": "abc"})
    assert len(out) == 1 and out[0][0] == gate.BLOCK


def test_check_drift_report_freshness_blocks_content_stale(tmp_path):
    gate.findings.clear()
    root = str(tmp_path)
    _fresh_write_png(root, "第1集")
    import json as _json
    d = os.path.join(root, "生产数据")
    os.makedirs(d, exist_ok=True)
    # 报告集级覆盖齐全，但记录一个错的指纹 → 内容级陈旧 BLOCK
    with open(os.path.join(d, "identity_drift_report.json"), "w", encoding="utf-8") as fh:
        _json.dump({"available": True, "episodes": ["第1集"],
                    "png_fingerprints": {"第1集": "STALE_FP"}}, fh, ensure_ascii=False)
    gate.check_drift_report_freshness(root, "第2集")
    assert any(f["sev"] == gate.BLOCK and "内容级陈旧" in f["msg"] for f in gate.findings)


def test_check_drift_report_freshness_passes_matching_fingerprint(tmp_path):
    gate.findings.clear()
    root = str(tmp_path)
    _fresh_write_png(root, "第1集")
    real_fp = gate.episode_png_fingerprint(root, "第1集")
    assert real_fp  # 有 PNG 必有指纹
    import json as _json
    d = os.path.join(root, "生产数据")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "identity_drift_report.json"), "w", encoding="utf-8") as fh:
        _json.dump({"available": True, "episodes": ["第1集"],
                    "png_fingerprints": {"第1集": real_fp}}, fh, ensure_ascii=False)
    gate.check_drift_report_freshness(root, "第2集")
    assert not any(f["sev"] == gate.BLOCK for f in gate.findings)


# ───────────────────────────────────────────────────────────────────────────
# 证据等级闸 evidence_grade_findings（#3）：advanced tier PENDING 在交付边界 BLOCK
# 运行：cd skills/n2d-review/scripts && python -m pytest test_gate.py -k evidence_grade
# ───────────────────────────────────────────────────────────────────────────
def _eg_summary(under):
    return {"evidence_grade": {"under_proven": under, "weakest": "structured"}}


def test_evidence_grade_findings_blocks_at_delivery():
    out = gate.evidence_grade_findings(_eg_summary(["主体视频一致(S2V)"]), "review", allow_waiver=False)
    assert len(out) == 1 and out[0][0] == gate.BLOCK and "S2V" in out[0][1]
    out = gate.evidence_grade_findings(_eg_summary(["主体视频一致(S2V)"]), "compose", allow_waiver=False)
    assert out and out[0][0] == gate.BLOCK


def test_evidence_grade_findings_waiver_downgrades_to_warn():
    out = gate.evidence_grade_findings(_eg_summary(["主体视频一致(S2V)"]), "review", allow_waiver=True)
    assert len(out) == 1 and out[0][0] == gate.WARN and "自负其责" in out[0][1]


def test_evidence_grade_findings_warns_at_early_stage():
    out = gate.evidence_grade_findings(_eg_summary(["主体视频一致(S2V)"]), "image", allow_waiver=False)
    assert len(out) == 1 and out[0][0] == gate.WARN


def test_evidence_grade_findings_empty_when_all_proven():
    assert gate.evidence_grade_findings(_eg_summary([]), "review") == []
    assert gate.evidence_grade_findings({}, "review") == []


# ───────────────────────────────────────────────────────────────────────────
# 单一 waiver 收口（#4）：降级 QC waiver 计数 rollup，"满档 vs 凭waiver"成可查字段
# 运行：cd skills/n2d-review/scripts && python -m pytest test_gate.py -k waiver_rollup
# ───────────────────────────────────────────────────────────────────────────
def test_consistency_waiver_rollup_empty_is_none():
    assert gate.consistency_waiver_rollup([], "review") is None


def test_consistency_waiver_rollup_counts_and_dedups_dims():
    waivers = [
        {"dim": "一致性总审", "ep": "第1集", "loc": "x", "reason": "a"},
        {"dim": "一致性总审", "ep": "第1集", "loc": "y", "reason": "b"},
        {"dim": "证据等级", "ep": "第1集", "loc": "z", "reason": "c"},
    ]
    sev, loc, msg = gate.consistency_waiver_rollup(waivers, "review")
    assert sev == gate.WARN and loc == "一致性满档账"
    assert "3 条" in msg and "full_grade=false" in msg
    assert "一致性总审" in msg and "证据等级" in msg
    assert "交付边界" in msg  # review = 交付边界强提示


def test_consistency_waiver_rollup_non_delivery_stage_no_boundary_note():
    sev, loc, msg = gate.consistency_waiver_rollup(
        [{"dim": "脸漂报告新鲜度", "ep": "第1集", "loc": "x", "reason": "r"}], "image")
    assert sev == gate.WARN and "交付边界" not in msg and "1 条" in msg


def test_note_degraded_qc_waiver_feeds_ledger():
    gate._DEGRADED_QC_WAIVERS.clear()
    gate.note_degraded_qc_waiver("证据等级", "第1集", "loc", "reason")
    gate.note_degraded_qc_waiver("一致性总审", "第1集", "loc2", "reason2")
    assert len(gate._DEGRADED_QC_WAIVERS) == 2
    out = gate.consistency_waiver_rollup(gate._DEGRADED_QC_WAIVERS, "compose")
    assert out is not None and "2 条" in out[2]
    gate._DEGRADED_QC_WAIVERS.clear()


def test_progress_receipt_reconcile_blocks_unbacked_checkmark(tmp_path):
    # H3：进度里 出图=✅ 但无 gate 凭据（模拟绕过 do_set 的手写 ✅）→ 验收闸 BLOCK
    root = str(tmp_path)
    (tmp_path / "_进度.md").write_text(
        "| 集 | 出图 | 视频 | 成片 | 验收 |\n|---|---|---|---|---|\n| 第1集 | ✅ | ⬜ | ⬜ | ⬜ |\n",
        encoding="utf-8")
    gate.findings.clear()
    gate.check_progress_receipt_reconcile(root, "第1集")
    hits = [f for f in gate.findings if f["dim"] == "进度凭据对账" and f["sev"] == gate.BLOCK]
    assert hits and "出图" in hits[0]["loc"]


def test_progress_receipt_reconcile_clean_when_no_done_checks(tmp_path):
    root = str(tmp_path)
    (tmp_path / "_进度.md").write_text(
        "| 集 | 出图 | 视频 | 成片 | 验收 |\n|---|---|---|---|---|\n| 第1集 | ⬜ | ⬜ | ⬜ | ⬜ |\n",
        encoding="utf-8")
    gate.findings.clear()
    gate.check_progress_receipt_reconcile(root, "第1集")
    assert not any(f["dim"] == "进度凭据对账" for f in gate.findings)


def test_progress_receipt_reconcile_skips_current_stage_self_lock(tmp_path):
    root = str(tmp_path)
    (tmp_path / "_进度.md").write_text(
        "| 集 | 出图 | 视频 | 成片 | 验收 |\n|---|---|---|---|---|\n| 第1集 | ⬜ | ⬜ | ✅ | ⬜ |\n",
        encoding="utf-8")
    gate.findings.clear()
    gate.check_progress_receipt_reconcile(root, "第1集", current_stage="compose")
    assert not any(f["dim"] == "进度凭据对账" for f in gate.findings)


def _mk_core_registry(tmp_path, core_name="金銮殿"):
    import json as _json, os as _os
    d = tmp_path / "出图" / "共享"
    d.mkdir(parents=True, exist_ok=True)
    (d / "asset_registry.json").write_text(
        _json.dumps({"assets": [{"id": "LOC_HALL", "name": core_name, "core": True},
                                 {"id": "LOC_HALLWAY", "name": "走廊"}]}, ensure_ascii=False),
        encoding="utf-8")
    return str(tmp_path)


def test_w2w3_light_escalates_to_block_on_core_scene_at_compose(tmp_path):
    root = _mk_core_registry(tmp_path)
    row = {"dimension": "天气时辰(W1)", "metric": "light_dir", "scene": "金銮殿", "verdict": "warn"}
    blocked, reason = gate._strict_advisory_should_block(root, "第1集", "compose", row, {})
    assert blocked and "核心场景" in reason


def test_w2w3_light_stays_warn_on_non_core_scene(tmp_path):
    root = _mk_core_registry(tmp_path)
    row = {"dimension": "天气时辰(W1)", "metric": "light_elevation", "scene": "走廊", "verdict": "warn"}
    assert gate._strict_advisory_should_block(root, "第1集", "compose", row, {})[0] is False


def test_w2w3_light_stays_warn_at_image_stage(tmp_path):
    root = _mk_core_registry(tmp_path)
    row = {"dimension": "天气时辰(W1)", "metric": "light_dir", "scene": "金銮殿", "verdict": "warn"}
    assert gate._strict_advisory_should_block(root, "第1集", "image", row, {})[0] is False


def test_daypart_w1_not_escalated_by_core_scene_rule(tmp_path):
    # daypart 不在 light 子集——核心场景 compose 也不被本规则硬升（昼夜切换留人工签收）。
    root = _mk_core_registry(tmp_path)
    row = {"dimension": "天气时辰(W1)", "metric": "daypart", "scene": "金銮殿", "verdict": "warn"}
    assert gate._strict_advisory_should_block(root, "第1集", "compose", row, {})[0] is False


# ── 打斗撞点(SPEC-APEX) 核心打斗镜升 BLOCK（P1 升闸）─────────────────────────────

def test_combat_apex_escalates_to_block_on_core_scene_at_review(tmp_path):
    root = _mk_core_registry(tmp_path)
    row = {"dimension": "打斗撞点(SPEC-APEX)", "metric": "combat_apex_untimestamped",
           "scene": "金銮殿", "verdict": "warn"}
    blocked, reason = gate._strict_advisory_should_block(root, "第1集", "review", row, {})
    assert blocked and "撞点" in reason


def test_combat_apex_escalates_on_key_scene_via_clip_label(tmp_path):
    # 非核心 LOC，但 clip_label 含「高潮」key 标记 → 仍升 BLOCK（key-scene 路径）。
    root = _mk_core_registry(tmp_path)
    row = {"dimension": "打斗撞点(SPEC-APEX)", "metric": "combat_cue_apex_no_keyframe",
           "scene": "练武场", "clip_label": "决战高潮·斩落", "verdict": "warn"}
    assert gate._strict_advisory_should_block(root, "第1集", "compose", row, {})[0] is True


def test_combat_apex_stays_warn_on_incidental_shot(tmp_path):
    # 非核心场景 + 无 key 标记 → 普通打斗镜保持 advisory WARN，不升 BLOCK。
    root = _mk_core_registry(tmp_path)
    row = {"dimension": "打斗撞点(SPEC-APEX)", "metric": "combat_apex_untimestamped",
           "scene": "走廊", "clip_label": "路过小冲突", "verdict": "warn"}
    assert gate._strict_advisory_should_block(root, "第1集", "review", row, {})[0] is False


def test_combat_apex_stays_warn_at_image_stage(tmp_path):
    # 仅交付边界(compose/review)硬化；image/video 阶段保持 WARN。
    root = _mk_core_registry(tmp_path)
    row = {"dimension": "打斗撞点(SPEC-APEX)", "metric": "combat_apex_untimestamped",
           "scene": "金銮殿", "verdict": "warn"}
    assert gate._strict_advisory_should_block(root, "第1集", "image", row, {})[0] is False


def test_combat_apex_no_edit_cue_code_never_blocks(tmp_path):
    # combat_apex_no_edit_cue 是 info 级補强建议，不在硬化 code 集——核心场景交付也不升 BLOCK。
    root = _mk_core_registry(tmp_path)
    row = {"dimension": "打斗撞点(SPEC-APEX)", "metric": "combat_apex_no_edit_cue",
           "scene": "金銮殿", "verdict": "warn"}
    assert gate._strict_advisory_should_block(root, "第1集", "review", row, {})[0] is False


def test_combat_apex_block_downgraded_by_signoff(tmp_path):
    root = _mk_core_registry(tmp_path)
    row = {"dimension": "打斗撞点(SPEC-APEX)", "metric": "combat_apex_untimestamped",
           "scene": "金銮殿", "message": "剪辑峰值无处钉", "verdict": "warn"}
    import json as _json
    prod = tmp_path / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    (prod / "consistency_advisory_signoff_第1集.json").write_text(_json.dumps({"accepted": [{
        "accepted": True, "reviewer": "导演", "reason": "本镜慢镜处理无需离散命中帧",
        "expires_at": "2099-01-01", "dimension": "打斗撞点(SPEC-APEX)",
        "message_contains": "剪辑峰值无处钉",
    }]}, ensure_ascii=False), encoding="utf-8")
    blocked, reason = gate._strict_advisory_should_block(root, "第1集", "review", row, {})
    assert blocked is False and "签收" in reason
