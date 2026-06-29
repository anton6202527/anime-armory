#!/usr/bin/env python3
"""Tests for n2d spectacle/action helper scripts."""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import action_edit_cues  # noqa: E402
import spectacle_contract_audit  # noqa: E402
import spectacle_plan  # noqa: E402
import spectacle_probe_pack  # noqa: E402
import spectacle_sequence_plan  # noqa: E402
import scene_layer_pack  # noqa: E402


def _mk_storyboard(clips):
    d = tempfile.mkdtemp()
    ep = Path(d) / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "storyboard.json").write_text(json.dumps({"clips": clips}, ensure_ascii=False), encoding="utf-8")
    return Path(d)


def _premium_contract(peak="impact"):
    return {
        "keyframe_plan": {
            "start": "起势/建立帧",
            "intent_mid": "动作方向中段锚",
            "impact_or_apex": peak,
            "result_or_recovery": "结果/收势帧",
            "end": "尾帧锁结果",
        },
        "post_cue_points": [
            {"cue": "speed_ramp", "when": "pre_peak"},
            {"cue": "hit_stop_or_flash", "when": peak},
            {"cue": "aftershock", "when": "result"},
        ],
        "physics_guard": {
            "subject_identity": "角色脸和服装不漂",
            "axis_or_path": "运动方向不反转",
            "contact_or_vfx_shape": "接触点/特效形态不变",
            "no_extra_motion": "不新增第二次攻击或新特效",
        },
    }


def test_ascii_spectacle_keywords_use_token_boundaries():
    ordinary = {
        "id": "C01",
        "character_ids": ["CHAR_SHENNIAN"],
        "object_ids": ["PROP_WHITE_SILK"],
        "description": "white silk and poisoned wine on a tray",
    }
    detected = spectacle_contract_audit.audit_clip(ordinary, 1)
    assert detected["spectacle_type"] is None

    vehicle = {"id": "C02", "description": "a car chase on a wet highway"}
    detected_vehicle = spectacle_contract_audit.audit_clip(vehicle, 2)
    assert detected_vehicle["spectacle_type"] == "road_vehicle"


def test_spectacle_inference_ignores_structural_non_visual_fields():
    ordinary = {
        "id": "C01",
        "character_ids": ["CHAR_SHENNIAN/潜行态"],
        "subtitle_lines": ["得到：伪人皮，潜行。"],
        "entity_schedule": {"knowledge_state": {"CHAR_SHENNIAN": ["知道自己获得潜行能力"]}},
        "shots": [{"desc": "沈念看着空光幕收起。"}],
    }

    detected = spectacle_contract_audit.audit_clip(ordinary, 1)

    assert detected["spectacle_type"] is None


def _fight_contract():
    return {
        "template_id": "fight_exchange",
        "beats": ["setup", "attack", "impact", "reaction", "recovery"],
        "blocking": "A left, B right",
        "camera_rule": "stable medium",
        "continuity_must": ["same sword"],
        "negative": ["extra hit"],
        "attack_path": "left to right slash",
        "impact_frame": "end frame",
        "action_scope": "one hit",
        "contact_points": ["sword edge to shield"],
        "force_direction": "screen right",
        "screen_direction": "left_to_right",
        "speed_curve": "fast then stop",
        "spatial_path": "A advances one step",
        "camera_path": "small push",
        "readability_beats": ["hit silhouette clear"],
        "recovery_beat": "B staggers",
        "degrade_plan": "split setup/impact/reaction",
        **_premium_contract("end frame"),
    }


def _vehicle_contract():
    return {
        "template_id": "vehicle_ride",
        "beats": ["establish", "wheel", "side_track", "stop"],
        "blocking": "马车沿画面左到右行进",
        "camera_rule": "侧向跟拍，不越轴",
        "continuity_must": ["四轮车厢不变", "两匹黑马连接车辕"],
        "negative": ["不要新增轮子", "不要断开缰绳"],
        "vehicle_lock": "四轮青布马车，车厢剪影不变",
        "wheel_rotation": "四个车轮同向快速滚动",
        "harness_lock": "两匹黑马缰绳连接车辕，车夫双手握缰",
        "speed_curve": "巡航匀速→过石坎半顿→抵达减速",
        "spatial_path": "沿山路画左到画右",
        "camera_path": "侧向跟拍",
        "screen_direction": "left_to_right",
        "parallax_layers": ["前景树影快", "山路中速", "远山慢"],
        "readability_beats": ["车轮先看清半拍", "急停落幅停在门前"],
        "degrade_plan": "拆轮子/马蹄/车夫手/车内反应/抵达停步",
        **_premium_contract("过石坎颠簸峰值"),
    }


def _road_vehicle_contract():
    return {
        "template_id": "road_vehicle",
        "beats": ["establish", "traffic", "brake"],
        "blocking": "出租车沿高架画面左到右行驶",
        "camera_rule": "侧向跟拍，不越轴",
        "continuity_must": ["黄色出租车车体不变", "司机双手在方向盘"],
        "negative": ["不要新增车轮", "不要让车道漂移"],
        "vehicle_lock": "黄色四门出租车，车灯和车身颜色不变",
        "wheel_rotation": "四个车轮同向滚动，前轮不凭空变形",
        "driver_control_lock": "司机双手握方向盘，车内视线向前",
        "lane_lock": "高架最右车道，画面左到右，不跨到逆向车道",
        "traffic_flow": "旁侧车流同向后掠，远处尾灯成线",
        "speed_curve": "巡航→轻微加速→路口刹车",
        "spatial_path": "沿高架弧线从画左进到画右出",
        "camera_path": "车侧低角度跟拍",
        "screen_direction": "left_to_right",
        "parallax_layers": ["近处护栏快", "车流中速", "城市楼群慢"],
        "readability_beats": ["先看清出租车半拍", "刹车落幅停在路口线前"],
        "degrade_plan": "拆轮胎/后视镜/司机手/车外掠过/抵达停住",
        **_premium_contract("刹车峰值"),
    }


def _screen_insert_contract():
    return {
        "template_id": "screen_insert",
        "beats": ["device", "overlay", "reaction"],
        "blocking": "手机在角色手中，屏幕朝镜头",
        "camera_rule": "固定近景，屏幕平面不大幅旋转",
        "continuity_must": ["同一部黑色手机", "同一只手握持"],
        "negative": ["不要让 AI 画可读文字", "不要新增 UI 按钮"],
        "device_lock": "黑色直板手机，竖屏，边框不变",
        "screen_content_ref": "聊天记录与定位时间码来自 overlay_content",
        "text_layer": "overlay",
        "overlay_content": "compose 期叠聊天记录、定位和时间码",
        "reflection_policy": "轻微玻璃反光，不遮挡 overlay 文字",
        "hand_pose_lock": "右手拇指悬在屏幕下方",
        "readability_beats": ["屏幕稳定 0.8s 供文字读取"],
    }


def _evidence_search_contract():
    return {
        "template_id": "evidence_search",
        "beats": ["search", "reveal", "bag"],
        "blocking": "手从抽屉左侧翻到右侧，物证停在画面中央",
        "camera_rule": "物证近景，人物脸可切反应",
        "continuity_must": ["沾血票据位置不变", "证物袋编号一致"],
        "negative": ["不要凭空新增线索", "不要把血迹形状改掉"],
        "clue_object": "沾血票据，右上角折痕和暗红血点固定",
        "search_path": "手从抽屉左前方拨开文件，露出票据",
        "reveal_frame": "票据完全露出时定住半拍",
        "evidence_chain": "拍照记录后放入透明证物袋",
        "hand_pose_lock": "戴手套的右手捏住票据边缘",
        "occlusion_order": "文件压住票据一角，手在最前景",
        "contamination_guard": "戴手套，不直接触碰血迹区域",
        "readability_beats": ["票据与血点清楚半拍"],
    }


def _tribulation_contract():
    return {
        "template_id": "tribulation_breakthrough",
        "beats": ["omen", "strike", "breakthrough"],
        "blocking": "主角居中盘坐，雷云在画面上方",
        "camera_rule": "命中帧固定，突破后拉远",
        "continuity_must": ["紫色劫雷形态不变", "护体金光不换色"],
        "negative": ["不要乱闪多道雷", "不要把光柱改成火焰"],
        "tribulation_stage": "第三道主雷→撑过→突破光柱",
        "lightning_path": "雷云中心垂直劈向主角护体光罩",
        "impact_frame": "紫雷接触金色护罩的尾帧",
        "shield_lock": "金色半圆护体光罩，裂纹固定",
        "breakthrough_light": "撑过后金色光柱自脚下冲天",
        "vfx_asset_lock": ["VFX_紫劫雷", "VFX_突破金光柱"],
        "intensity_curve": "乌云压低→主雷最亮→短白闪→光柱释放",
        "readability_beats": ["雷击命中停半拍", "突破光柱留白一拍"],
        "degrade_plan": "拆天象/雷击命中/突破光柱三镜",
        **_premium_contract("紫雷接触金色护罩的尾帧"),
    }


def _magic_burst_contract():
    return {
        "template_id": "magic_burst",
        "beats": ["charge", "release", "collision", "aftermath"],
        "blocking": "主角画左持剑，剑气沿画面左到右冲出",
        "camera_rule": "撞点镜稳定，余波拉远",
        "continuity_must": ["青色剑气形态不变", "来源始终是 WEAPON_01"],
        "negative": ["不要新增第二种颜色", "不要把剑气改成火焰"],
        "charge_frame": "剑身青光聚集的起势帧",
        "release_frame": "剑气离剑一瞬",
        "effect_asset": "VFX_青色剑气",
        "energy_path": "画左剑锋到画右护盾的直线弧光",
        "collision_or_apex_frame": "剑气撞上黑色护盾的峰值帧",
        "screen_direction": "left_to_right",
        "power_shift": "撞点先停住，再向画右压过护盾",
        "vfx_asset_lock": ["VFX_青色剑气", "VFX_黑色护盾"],
        "intensity_curve": "蓄力低亮→释放高亮→撞点闪白→余波光点",
        "speed_curve": "蓄力慢→释放快→撞点停→余波慢",
        "spatial_path": "画左到画右",
        "camera_path": "随剑气轻推，撞点停住",
        "readability_beats": ["撞点停半拍", "破盾结果留半拍"],
        "degrade_plan": "拆蓄力/释放/撞点/余波，失败时 VFX overlay",
        **_premium_contract("剑气撞上黑色护盾的峰值帧"),
    }


def _meditation_contract():
    return {
        "template_id": "meditation_cultivation",
        "beats": ["posture", "breath", "inner", "hold"],
        "blocking": "CHAR_01 盘坐蒲团中央，双手结印，衣摆落在膝前",
        "camera_rule": "固定中近景，极缓推近，不环绕",
        "continuity_must": ["坐姿不变", "手印不变", "青白灵气路径不变"],
        "negative": ["不要站起", "不要换手印", "不要乱舞法术"],
        "posture_lock": "脊背直立盘坐，双手丹田前结印，脚踝不动",
        "breath_cycle": "三次缓慢吐纳，胸口轻起伏",
        "energy_flow": "青白灵气从四周入体，沿胸口沉入丹田再绕一周天",
        "aura_vfx_lock": "VFX_青白周天光环，细粒子不变色",
        "inner_state_beat": "丹田内青白波纹扩散一圈后平静",
        "environment_stillness": "烛火只随呼吸轻晃，背景不动",
        "micro_motion": "呼吸、指节轻压、发丝轻动",
        "readability_beats": ["周天光环到丹田停半拍", "收功留白半拍"],
        "degrade_plan": "改静态坐姿关键帧 + aura overlay + 内视插入镜",
        **_premium_contract("丹田青白波纹扩散峰值"),
    }


def _alchemy_contract():
    return {
        "template_id": "alchemy_forging",
        "beats": ["materials", "heat", "transform", "reveal"],
        "blocking": "丹炉居中，右手投药材，炉口火光向上",
        "camera_rule": "道具近景固定，开炉时 CU 定住",
        "continuity_must": ["青铜丹炉不变", "火色由橙到金", "成丹纹样不变"],
        "negative": ["不要凭空新增材料", "不要让丹炉变形", "不要提前出现成丹"],
        "furnace_or_forge_lock": "青铜三足丹炉，炉纹与炉盖形态固定",
        "material_sequence": ["紫叶草", "寒露珠", "金砂"],
        "process_stage_ladder": ["投料", "升温", "凝丹", "开炉"],
        "flame_control": "橙火低燃→金火收束→炉纹发亮",
        "heat_curve": "低温预热→中温旋转→峰值金光→开炉降温",
        "material_state_ladder": ["药材干燥", "化液", "凝成三颗丹丸"],
        "tool_hand_pose": "右手捏药材投炉，左手按炉纹",
        "product_lock": "三颗金纹丹丸，圆形，丹纹一圈",
        "reveal_frame": "炉盖打开后三颗丹丸悬浮的定格帧",
        "vfx_asset_lock": ["VFX_金色炉火", "VFX_丹纹微光"],
        "success_or_failure_beat": "成丹成功，金纹亮起后收束",
        "failure_or_success_safety": "不炸炉；若失败只允许固定灰烟形态",
        "readability_beats": ["材料入炉停半拍", "成丹 reveal_frame 停半拍"],
        "degrade_plan": "拆投料/火候/凝丹/开炉，失败时产品静态揭示",
        **_premium_contract("炉盖打开后三颗丹丸悬浮的定格帧"),
    }


def _dual_cultivation_contract():
    return {
        "template_id": "dual_cultivation",
        "beats": ["consent", "breath", "energy", "hold"],
        "blocking": "两名成年角色相对盘坐，掌心相抵，肩以上与手部可见",
        "camera_rule": "中景固定，低幅推近，不绕拍",
        "continuity_must": ["两人服装完整", "掌心接触点不变", "蓝金灵力循环不变"],
        "negative": ["不要裸露", "不要性行为动作", "不要身体缠绕"],
        "adult_consent_lock": "两名成年角色，双方明确自愿，以疗伤合修为目的",
        "non_explicit_boundary": "非露骨；无裸露、无性行为动作、无性化镜头",
        "paired_posture_lock": "相对盘坐，双掌相抵，背脊直立",
        "distance_boundary": "膝前保持一臂距离，只有掌心接触",
        "contact_points": ["左掌对右掌", "右掌对左掌"],
        "energy_circulation": "蓝金灵力从 A 掌心进入 B 胸口，再回到 A 丹田形成闭环",
        "breath_sync": "两人三次同频吐纳",
        "aura_vfx_lock": "VFX_蓝金双人灵力环",
        "relationship_state": "信任、疗伤、克制亲密",
        "readability_beats": ["灵力闭环峰值停半拍", "疗伤后两人气息平复"],
        "degrade_plan": "改掌心特写、背影光环、反应镜或光雾淡出",
        **_premium_contract("蓝金灵力闭环峰值"),
    }


def _kiss_contract():
    return {
        "template_id": "kiss_or_near_kiss",
        "beats": ["approach", "pause", "near_contact", "separate"],
        "blocking": "两名角色 MCU，CHAR_01 画左，CHAR_02 画右，肩线不交叉",
        "camera_rule": "固定 MCU 极缓推近，不环绕，不越轴",
        "continuity_must": ["两张脸身份不漂", "发型不变", "手始终在肩侧"],
        "negative": ["不要露骨舌吻", "不要脱衣", "不要性行为暗示", "不要脸融合"],
        "age_context_lock": "两名角色均为成年人；若项目设定不明，改近吻停顿或额头吻",
        "consent_lock": "双方主动靠近并停顿确认，自愿亲吻",
        "non_explicit_boundary": "闭口轻吻/近吻，非露骨，无裸露，无性行为动作",
        "relationship_state": "告白兑现后的克制亲密",
        "approach_path": "CHAR_01 从画左轻靠近，CHAR_02 微微抬头，停在近接触距离",
        "face_angle_lock": "两张脸三分之四侧面，鼻梁错开，眼神先对视后轻闭",
        "contact_or_near_contact_frame": "唇边近接触停半拍，不强制嘴部变形",
        "hand_position_lock": "CHAR_01 右手停在 CHAR_02 肩侧衣料上，不碰脸",
        "body_overlap_limit": "肩线轻重叠，胸肩不融合，手臂不穿插",
        "breath_pause": "接近前一拍短暂停呼吸",
        "micro_expression_beats": "对视紧张→放松闭眼→分开后轻微含笑",
        "readability_beats": ["近接触帧停半拍", "分开表情留白半拍"],
        "degrade_plan": "改额头吻/脸颊吻/近吻停顿/手部插入/反应镜",
        **_premium_contract("唇边近接触停半拍"),
    }


def _soul_contract():
    return {
        "template_id": "soul_manifestation",
        "beats": ["body_anchor", "soul_emerge", "probe"],
        "blocking": "肉身盘坐居中，元神从天灵上升",
        "camera_rule": "固定中近景，缓推",
        "continuity_must": ["肉身和元神同脸同发型", "肉身姿态不动"],
        "negative": ["不要把元神画成另一个人", "不要让肉身站起"],
        "body_soul_identity_lock": "元神由 CHAR_01 常态定妆半透明派生，同脸同发型",
        "soul_form_lock": "青白半透明人形，边缘微光",
        "opacity_curve": "0→70% 渐显",
        "emergence_path": "从天灵竖直上升半身高度",
        "host_body_lock": "肉身盘坐闭目不动",
        "conflict_or_probe_target": "神识波纹探向门外黑影",
        "readability_beats": ["元神完全显形停半拍"],
        "degrade_plan": "拆肉身锚定/元神显形/神识探查",
    }


def _realm_portal_contract():
    return {
        "template_id": "realm_portal",
        "beats": ["portal", "entry", "destination"],
        "blocking": "主角从画面前景被裂缝卷入，落到山门远景",
        "camera_rule": "入口固定，硬切目的地显景",
        "continuity_must": ["主角服装和脸不变", "裂缝紫蓝色形态不变"],
        "negative": ["不要中途换脸换衣", "不要把秘境门改成普通门"],
        "portal_lock": "紫蓝环形时空裂缝，边缘碎光",
        "source_world_anchor": "现代出租屋床边",
        "destination_anchor": "异界山门与云海",
        "entry_exit_path": "主角向后被吸入裂缝，再从山门前跌落",
        "body_continuity_lock": "同一角色同一衣服，只做姿态从站立到跌坐",
        "transition_vfx": "紫蓝旋涡、短白闪、边缘星点",
        "readability_beats": ["落地后山门显景半拍"],
        "degrade_plan": "拆入口/卷入/落地显景",
    }


def test_spectacle_contract_audit_blocks_missing_fight_contract():
    root = _mk_storyboard([{"id": "Clip 1", "template": "fight_exchange", "scene": "挥剑命中追兵"}])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert not result["ok"]
    assert any(f["code"] == "missing_template_contract" for f in result["findings"])
    assert any(f.get("field") == "impact_frame" for f in result["findings"])


def test_spectacle_contract_audit_passes_complete_fight_contract():
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "fight_exchange",
        "scene": "挥剑命中追兵",
        "template_contract": _fight_contract(),
    }])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert result["ok"]
    assert result["summary"]["spectacle_clips"] == 1


def test_spectacle_contract_audit_blocks_missing_vehicle_ride_field():
    contract = _vehicle_contract()
    contract.pop("wheel_rotation")
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "vehicle_ride",
        "scene": "山路马车疾行，车轮扬尘",
        "template_contract": contract,
    }])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert not result["ok"]
    assert any(f.get("field") == "wheel_rotation" for f in result["findings"])


def test_spectacle_contract_audit_passes_complete_vehicle_ride_contract():
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "vehicle_ride",
        "scene": "山路马车疾行，车轮扬尘",
        "template_contract": _vehicle_contract(),
    }])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert result["ok"]
    assert result["summary"]["spectacle_clips"] == 1


def test_spectacle_contract_audit_blocks_missing_road_vehicle_field():
    contract = _road_vehicle_contract()
    contract.pop("lane_lock")
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "road_vehicle",
        "scene": "出租车沿高架疾驰，车流后掠",
        "template_contract": contract,
    }])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert not result["ok"]
    assert any(f.get("field") == "lane_lock" for f in result["findings"])


def test_spectacle_contract_audit_passes_screen_insert_contract():
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "screen_insert",
        "scene": "手机屏幕出现聊天记录和定位时间码",
        "template_contract": _screen_insert_contract(),
    }])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert result["ok"]
    assert result["summary"]["spectacle_clips"] == 1


def test_spectacle_contract_audit_passes_evidence_search_contract():
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "evidence_search",
        "scene": "侦探翻抽屉，露出沾血票据",
        "template_contract": _evidence_search_contract(),
    }])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert result["ok"]
    assert result["summary"]["spectacle_clips"] == 1


def test_spectacle_contract_audit_blocks_missing_tribulation_field():
    contract = _tribulation_contract()
    contract.pop("impact_frame")
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "tribulation_breakthrough",
        "scene": "雷劫劈落，主角突破",
        "template_contract": contract,
    }])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert not result["ok"]
    assert any(f.get("field") == "impact_frame" for f in result["findings"])


def test_spectacle_contract_audit_passes_magic_burst_contract():
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "magic_burst",
        "scene": "青色剑气撞上黑色护盾，破盾余波炸开",
        "template_contract": _magic_burst_contract(),
    }])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert result["ok"]
    assert result["summary"]["spectacle_clips"] == 1


def test_spectacle_contract_audit_passes_meditation_contract():
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "meditation_cultivation",
        "scene": "主角静坐吐纳，灵气入体",
        "template_contract": _meditation_contract(),
    }])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert result["ok"]
    assert result["summary"]["spectacle_clips"] == 1


def test_spectacle_contract_audit_passes_alchemy_contract():
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "alchemy_forging",
        "scene": "丹炉开炉，三颗金纹丹丸成形",
        "template_contract": _alchemy_contract(),
    }])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert result["ok"]
    assert result["summary"]["spectacle_clips"] == 1


def test_spectacle_contract_audit_blocks_missing_kiss_boundary():
    contract = _kiss_contract()
    contract.pop("consent_lock")
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "kiss_or_near_kiss",
        "scene": "两人差点吻上",
        "template_contract": contract,
    }])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert not result["ok"]
    assert any(f.get("field") == "consent_lock" for f in result["findings"])


def test_spectacle_contract_audit_passes_dual_and_kiss_contracts():
    root = _mk_storyboard([
        {
            "id": "Clip 1",
            "template": "dual_cultivation",
            "scene": "两名成年角色掌心相抵疗伤合修",
            "template_contract": _dual_cultivation_contract(),
        },
        {
            "id": "Clip 2",
            "template": "kiss_or_near_kiss",
            "scene": "告白后近吻停顿",
            "template_contract": _kiss_contract(),
        },
    ])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert result["ok"]
    assert result["summary"]["spectacle_clips"] == 2


def test_spectacle_contract_audit_passes_soul_manifestation_contract():
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "soul_manifestation",
        "scene": "元神出窍探查",
        "template_contract": _soul_contract(),
    }])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert result["ok"]
    assert result["summary"]["spectacle_clips"] == 1


def test_spectacle_contract_audit_passes_realm_portal_contract():
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "realm_portal",
        "scene": "现代青年被时空裂缝卷入异界",
        "template_contract": _realm_portal_contract(),
    }])

    result = spectacle_contract_audit.audit(str(root), "第1集")

    assert result["ok"]
    assert result["summary"]["spectacle_clips"] == 1


def test_spectacle_plan_writes_motion_manifest(tmp_path):
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "fight_exchange",
        "scene": "挥剑命中追兵",
        "template_contract": _fight_contract(),
    }])

    plan = spectacle_plan.build_plan(root, "第1集")
    manifest = spectacle_plan.write_motion_manifest(root, "第1集", "Clip_01", "fight_exchange")

    assert plan["clips"][0]["motion_control_manifest_path"].endswith("Clip_01/motion_control_manifest.json")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["kind"] == "n2d_motion_control_manifest"
    assert "contact_map" in data["control_inputs"]
    assert plan["clips"][0]["premium_passes"]["level"] == "premium_action_spectacle"
    assert "keyframe_coverage" in plan["clips"][0]["premium_passes"]["qc_dimensions"]


def test_spectacle_plan_handles_magic_burst_as_premium_action(tmp_path):
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "magic_burst",
        "scene": "青色剑气撞上黑色护盾",
        "template_contract": _magic_burst_contract(),
    }])

    plan = spectacle_plan.build_plan(root, "第1集")
    manifest = spectacle_plan.write_motion_manifest(root, "第1集", "Clip_01", "magic_burst")
    data = json.loads(manifest.read_text(encoding="utf-8"))

    row = plan["clips"][0]
    assert row["spectacle_type"] == "magic_burst"
    assert "vfx_layers" in data["control_inputs"]
    assert row["premium_passes"]["keyframe_policy"]["required"]
    assert any(c["cue"] == "impact_or_energy_boom" for c in row["edit_cues"])


def test_spectacle_plan_handles_dual_and_kiss_control_inputs(tmp_path):
    root = _mk_storyboard([
        {
            "id": "Clip 1",
            "template": "dual_cultivation",
            "scene": "两名成年角色掌心相抵疗伤合修",
            "template_contract": _dual_cultivation_contract(),
        },
        {
            "id": "Clip 2",
            "template": "kiss_or_near_kiss",
            "scene": "告白后近吻停顿",
            "template_contract": _kiss_contract(),
        },
    ])

    plan = spectacle_plan.build_plan(root, "第1集")
    dual_manifest = spectacle_plan.write_motion_manifest(root, "第1集", "Clip_01", "dual_cultivation")
    kiss_manifest = spectacle_plan.write_motion_manifest(root, "第1集", "Clip_02", "kiss_or_near_kiss")
    dual_data = json.loads(dual_manifest.read_text(encoding="utf-8"))
    kiss_data = json.loads(kiss_manifest.read_text(encoding="utf-8"))

    assert plan["clips"][0]["spectacle_type"] == "dual_cultivation"
    assert plan["clips"][1]["spectacle_type"] == "kiss_or_near_kiss"
    assert "vfx_layers" in dual_data["control_inputs"]
    assert "contact_map" in kiss_data["control_inputs"]
    assert any(c["cue"] == "energy_loop_swell" for c in plan["clips"][0]["edit_cues"])
    assert any(c["cue"] == "micro_silence_hold" for c in plan["clips"][1]["edit_cues"])


def test_spectacle_sequence_plan_groups_contiguous_action_clips():
    root = _mk_storyboard([
        {"id": "Clip 1", "template": "fight_exchange", "scene": "CHAR_01 挥剑命中", "template_contract": _fight_contract()},
        {"id": "Clip 2", "template": "chase", "scene": "CHAR_01 沿屋脊追逐", "template_contract": {
            "template_id": "chase",
            "screen_direction": "left_to_right",
            "distance_curve": "closing",
            "spatial_path": "roofline",
            "camera_path": "tracking",
            "parallax_layers": ["roof", "moon"],
        }},
    ])

    plan = spectacle_sequence_plan.build_plan(root, "第1集")

    assert plan["kind"] == "n2d_spectacle_sequence_plan"
    assert plan["summary"]["sequences"] == 1
    seq = plan["sequences"][0]
    assert seq["sequence_type"] == "mixed_action"
    assert seq["clip_order"] == ["Clip_01", "Clip_02"]
    assert "CHAR_01" in seq["subject_slots"]["characters"]
    assert seq["premium_coverage_policy"]["required"] is True
    assert "impact_apex_readability" in seq["premium_coverage_policy"]["qc_dimensions"]


def test_sequence_plan_embeds_beat_decomposition_for_action_clips():
    root = _mk_storyboard([
        {"id": "Clip 1", "template": "fight_exchange",
         "scene": "CHAR_01 出拳，对方格挡后反击命中", "template_contract": _fight_contract()},
    ])

    plan = spectacle_sequence_plan.build_plan(root, "第1集")
    row = plan["clips"][0]

    # 动作行带逐拍拆镜推荐 + 检测到的节拍类别（一镜塞了完整攻防回合）。
    assert [b["beat"] for b in row["beat_decomposition"]] == ["setup_attack", "impact", "react_recover"]
    assert set(row["beat_categories"]) >= {"attack", "block", "counter", "impact"}


def test_sequence_plan_injects_identity_lock_and_same_frame_cap():
    root = _mk_storyboard([
        {"id": "Clip 1", "template": "fight_exchange",
         "scene": "CHAR_01 与 CHAR_02 缠斗，CHAR_03 在旁观战 命中",
         "template_contract": _fight_contract()},
    ])

    plan = spectacle_sequence_plan.build_plan(root, "第1集")
    seq = plan["sequences"][0]

    # 负向身份锁词注入序列契约。
    assert "shifting jawline" in seq["negative_identity_lock"]
    # 三具名角色同框 > 2 → 进 over_cap_clips，建议拆镜。
    assert seq["same_frame_policy"]["cap"] == 2
    assert "Clip_01" in seq["same_frame_policy"]["over_cap_clips"]
    # 运动强度连续档 + 3-4 角度建议。
    assert plan["clips"][0]["motion_intensity"] == 3
    assert "3" in seq["identity_reference_advice"] or "3–4" in seq["identity_reference_advice"]


def test_scene_layer_pack_scaffolds_large_scene_pack():
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "large_establishing",
        "scene": "LOC_01 宗门大殿全貌，万人广场",
        "large_scene_contract": {
            "reuse_asset_id": "LOC_01",
            "landmark_anchor": "山门巨匾",
            "scale_reference": "人群像米粒，殿门十丈高",
            "parallax_planes": ["云雾", "殿门", "远山"],
        },
    }])

    plan = scene_layer_pack.build_plan(root, "第1集")

    assert plan["summary"]["scene_layer_packs"] == 1
    pack = plan["packs"][0]["pack"]
    assert pack["kind"] == "n2d_scene_layer_pack"
    assert pack["loc_id"] == "LOC_01"
    assert pack["landmark_anchor"] == "山门巨匾"


def test_spectacle_probe_pack_selects_representative_types():
    root = _mk_storyboard([
        {"id": "Clip 1", "template": "fight_exchange", "scene": "挥剑命中追兵", "template_contract": _fight_contract()},
        {"id": "Clip 2", "template": "chase", "scene": "屋脊追逐，左到右紧追"},
        {"id": "Clip 3", "template": "flight", "scene": "腾云驾雾穿过云海"},
        {"id": "Clip 4", "template": "vehicle_ride", "scene": "马车沿山路左到右疾行"},
        {"id": "Clip 5", "template": "mount_ride", "scene": "主角骑灵狼穿林奔跑"},
        {"id": "Clip 6", "template": "vessel_flight", "scene": "飞舟穿云抵达山门"},
        {"id": "Clip 7", "template": "road_vehicle", "scene": "出租车沿高架疾驰，车流后掠"},
        {"id": "Clip 8", "template": "stealth_stalk", "scene": "黑衣人尾随女主穿过暗走廊，门缝遮挡"},
        {"id": "Clip 9", "scene": "宗门大殿全貌，万人广场，大场景航拍"},
    ])

    pack = spectacle_probe_pack.build_probe_pack(root, "第1集")
    types = {p["spectacle_type"] for p in pack["probe_clips"]}

    assert {
        "fight_exchange",
        "chase",
        "flight",
        "vehicle_ride",
        "mount_ride",
        "vessel_flight",
        "road_vehicle",
        "stealth_stalk",
        "large_establishing",
    }.issubset(types)
    assert pack["benchmark_schema"]["kind"] == "n2d_spectacle_backend_benchmark"


def test_action_edit_cues_contains_hit_stop():
    root = _mk_storyboard([{
        "id": "Clip 1",
        "template": "fight_exchange",
        "scene": "挥剑命中追兵",
        "template_contract": _fight_contract(),
    }])

    cues = action_edit_cues.build_cues(root, "第1集")

    assert cues["kind"] == "n2d_action_edit_cues"
    assert any(cue["cue"] == "hit_stop" for cue in cues["clips"][0]["cues"])


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))


# ── 战斗精修 advisory 字段（表情/二级运动/apex光·缺=WARN 不阻断） ──
def test_spectacle_advisory_fields_for_combat():
    from n2d_spectacle import spectacle_advisory_fields
    assert set(spectacle_advisory_fields("fight_exchange")) == {
        "combat_micro_expression", "secondary_motion", "apex_light"}
    assert set(spectacle_advisory_fields("magic_burst")) >= {"apex_light"}
    assert spectacle_advisory_fields("chase") == ()


def test_audit_warns_missing_polish_but_not_block(tmp_path):
    # 战斗契约必填齐但缺精修字段 → WARN（must=0·不阻断）
    c = _fight_contract()
    for k in ("combat_micro_expression", "secondary_motion", "apex_light"):
        c.pop(k, None)
    root = _mk_storyboard([{"id": "C1", "template": "fight_exchange", "scene": "挥剑命中",
                            "template_contract": c}])
    res = spectacle_contract_audit.audit(str(root), "第1集")
    assert res["ok"]                       # 不阻断
    codes = [f["code"] for cl in res.get("clips", []) for f in cl.get("findings", [])]
    assert "missing_spectacle_polish_field" in codes


# ── 兵器/武技对撞撞点帧 advisory（治打斗很少出现双方兵器硬碰硬相交·info 不阻断） ──
def test_is_weapon_clash_shot():
    from n2d_const import is_weapon_clash_shot
    assert is_weapon_clash_shot("双方刀剑相交·格挡迸火星")
    assert is_weapon_clash_shot("两道剑气对轰僵持较力")
    assert is_weapon_clash_shot("blade lock, sparks fly")
    assert not is_weapon_clash_shot("她平静走入庭院，落座品茶")


def test_clash_advisory_fires_when_clash_text_but_no_clash_frame(tmp_path):
    # 含兵器相交文本却没写 clash_frame/collision_or_apex_frame → info 提示（不阻断）。
    c = _fight_contract()
    root = _mk_storyboard([{"id": "C1", "template": "fight_exchange",
                            "label": "双方兵器相交·格挡较力·迸火星", "template_contract": c}])
    res = spectacle_contract_audit.audit(str(root), "第1集")
    assert res["ok"]  # info 不阻断
    findings = [f for cl in res.get("clips", []) for f in cl.get("findings", [])]
    clash = [f for f in findings if f["code"] == "missing_weapon_clash_frame"]
    assert clash and clash[0]["severity"] == "info"
    assert res["summary"]["weapon_clash_frame_missing"] == 1


def test_clash_advisory_suppressed_when_clash_frame_present(tmp_path):
    c = _fight_contract()
    c["clash_frame"] = "双方刀剑在中点硬碰硬相交·迸火星·力对冲"
    root = _mk_storyboard([{"id": "C1", "template": "fight_exchange",
                            "label": "兵器相交格挡", "template_contract": c}])
    res = spectacle_contract_audit.audit(str(root), "第1集")
    codes = [f["code"] for cl in res.get("clips", []) for f in cl.get("findings", [])]
    assert "missing_weapon_clash_frame" not in codes
    assert res["summary"]["weapon_clash_frame_missing"] == 0


def test_clash_advisory_not_fired_for_plain_fight(tmp_path):
    # 普通打斗（无相交/格挡词）不强求 clash_frame。
    c = _fight_contract()
    root = _mk_storyboard([{"id": "C1", "template": "fight_exchange",
                            "label": "她一剑刺出，命中要害", "template_contract": c}])
    res = spectacle_contract_audit.audit(str(root), "第1集")
    codes = [f["code"] for cl in res.get("clips", []) for f in cl.get("findings", [])]
    assert "missing_weapon_clash_frame" not in codes
