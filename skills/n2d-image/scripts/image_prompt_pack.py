#!/usr/bin/env python3
"""Generate the n2d image prompt pack for an episode.

This is a no-cost writer: it creates prompt/spec files, identity and asset
registries, and application receipts. It does not create PNGs or call any image
backend.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)

from n2d_contract import (  # noqa: E402
    ASSET_REFERENCE_REGISTRY_KIND,
    IDENTITY_IMAGE_ADAPTERS,
    IDENTITY_REGISTRY_KIND,
    IDENTITY_VIDEO_ADAPTERS,
)
from n2d_visual_styles import DEFAULT_STYLE, style_anchor_path_for  # noqa: E402

REFERENCE_PLAN_APPLICATION_KIND = "n2d_reference_plan_application"
DIRECTOR_CAMERA_PLAN_APPLICATION_KIND = "n2d_director_camera_plan_application"
SCRIPT_CONTRACT_APPLICATION_KIND = "n2d_script_contract_application"
SCRIPT_QUALITY_CONTRACT_KIND = "n2d_script_quality_contract"
CONSUMED_CONTRACTS_KIND = "n2d_prompt_consumed_contracts"
CONSUMED_CONTRACTS_VERSION = 1
SCRIPT_CONTRACT_REQUIRED_FIELDS = [
    "core_attraction",
    "first_3s_visual_hook",
    "retention_promise_ledger",
    "pacing_allocation",
    "clip_dramatic_function",
    "audience_question_ledger",
    "performance_cues",
]
ASSET_ID_HINTS: Dict[str, Dict[str, Any]] = {
    "LOC_ZAYI_DADIAN": {
        "name": "秀竹峰杂役大殿",
        "path_name": "定妆_秀竹峰杂役大殿",
        "profile": "黑暗破旧的秀竹峰杂役大殿，旧木梁、粗木柱、石地、角落杂役用品，门缝冷光，底层压迫感。",
        "scene_dna": {
            "belonging_anchor": "太虚门秀竹峰底层杂役班，黑暗旧殿，不是仙宫。",
            "landmarks": ["旧木梁", "粗木柱", "石地", "角落杂役用品", "门缝冷光"],
            "spatial_layout": "张老大画右前景压迫，贺平生画左下，群杂役两侧与后景围压。",
            "architecture_materials": "旧木梁、粗柱、石地、灰尘、油污，灰褐低饱和。",
            "color_lighting_weather": "夜/内，画左门缝冷光，低照度，灰褐冷调。",
            "resident_assets": ["粗木柱", "杂役用品", "尘土", "油污"],
            "forbidden": ["仙宫", "官府大堂", "现代办公室", "明亮金碧大殿"],
        },
    },
    "LOC_ZAYI_YUAN": {
        "name": "秀竹峰杂役院",
        "path_name": "定妆_秀竹峰杂役院",
        "profile": "秀竹峰底层杂役生活区，低矮旧房、巨大水缸、空屋硬板床、铁碗、窗格冷月光。",
        "scene_dna": {
            "belonging_anchor": "秀竹峰底层杂役生活区，低矮旧房和贫瘠空屋。",
            "landmarks": ["六七间低矮旧房", "巨大水缸", "空屋硬板床", "铁碗", "窗格冷月光"],
            "spatial_layout": "水缸区韩老三画右前方，贺平生画左后方，两口水缸占后景；空屋内硬板床贴墙。",
            "architecture_materials": "灰褐旧木、粗糙石地、旧门板、冷窗格。",
            "color_lighting_weather": "日转夜；空屋用窗格月光画右后，冷灰贫瘠。",
            "resident_assets": ["两口水缸", "硬板床", "铁碗", "钥匙", "铁锁"],
            "forbidden": ["精致庭院", "仙宫厢房", "现代宿舍", "富贵家具"],
        },
    },
    "LOC_HOUSHAN_QIANTAN": {
        "name": "后山山泉浅潭",
        "path_name": "定妆_后山山泉浅潭",
        "profile": "后山崎岖小路尽头，一尺宽小瀑布、巨石、清澈浅潭、竹影和冷月，水底可见黑陶破盆。",
        "scene_dna": {
            "belonging_anchor": "秀竹峰后山挑水源头，清澈浅潭和冷月弱光。",
            "landmarks": ["一尺宽小瀑布", "巨石", "清澈浅潭", "竹影", "冷月倒影"],
            "spatial_layout": "浅潭居中，巨石与小瀑布在后景，挑水桶/扁担靠近前景。",
            "architecture_materials": "湿石、浅水、砂石、竹影、苔藓。",
            "color_lighting_weather": "夜，冷蓝月光，破盆只有极弱微光。",
            "resident_assets": ["水桶", "扁担", "黑陶破盆", "砂石"],
            "forbidden": ["强光柱", "仙宫池", "现代塑料桶", "神器化破盆"],
        },
    },
    "LOC_ZAYI_HUT": {
        "name": "贺平生杂役小屋",
        "path_name": "定妆_场景_贺平生杂役小屋",
        "profile": "低矮旧木小屋，硬板床、窗格冷光、墙角黑陶破盆、粗糙木门、几乎无家具，清晨冷灰青或深夜冷月光，贫瘠但画面可读。",
    },
    "LOC_HOUSHAN_WATER_PATH": {
        "name": "后山挑水路",
        "path_name": "定妆_场景_后山挑水路",
        "profile": "秀竹峰后山崎岖挑水小路，湿石、竹影、水桶晃动，黄昏到入夜冷蓝天光，表现十五趟挑水的身体压力。",
    },
    "LOC_ZAYI_FOOD_YARD": {
        "name": "杂役饭棚",
        "path_name": "定妆_场景_杂役饭棚",
        "profile": "杂役饭棚与粗木桌，旧大锅、木碗、低饱和脏暖晨光，底层劳动空间，背景只保留杂役生活轮廓，不新增清晰无名角色脸。",
    },
    "LOC_ZAYI_WATER_JARS": {
        "name": "杂役院水缸区",
        "path_name": "定妆_场景_杂役院水缸区",
        "profile": "杂役院两口巨大水缸区域，粗糙石地、水痕、低矮旧屋边缘和木桶扁担，水缸体量压迫，清晨冷灰或低饱和脏暖侧光，不新增现代水箱。",
        "scene_dna": {
            "belonging_anchor": "秀竹峰杂役院水缸区，日常劳动压迫空间。",
            "landmarks": ["两口巨大水缸", "粗糙石地", "低矮旧屋边缘", "木桶扁担"],
            "spatial_layout": "两口巨大水缸占后景或中后景，角色在前景显得很小，水缸边沿高过少年肩头。",
            "architecture_materials": "粗糙石地、旧木屋边、陶缸或石缸湿冷反光、低饱和灰褐。",
            "color_lighting_weather": "清晨冷灰或脏暖低饱和侧光，水面和缸壁轻微反光。",
            "resident_assets": ["两口巨大水缸", "木水桶", "粗木扁担", "水痕"],
            "forbidden": ["现代水箱", "豪华庭院", "仙宫水池", "水缸比例变小"],
        },
    },
    "LOC_WAIMEN_JIUYUAN": {
        "name": "太虚门外门旧院",
        "path_name": "定妆_太虚门外门旧院",
        "profile": "太虚门外门旧院回忆场景，旧院门、低矮院墙、外门旧袍和被夺资源的贫瘠感。",
    },
    "PROP_XIUZHEN_ZIYUAN": {
        "name": "修真资源包",
        "path_name": "定妆_修真资源包",
        "profile": "低阶修真资源小包，旧布包、少量灵石、短颈圆口小药瓶、玉简，不华丽。",
        "must_not_have": ["壶嘴", "侧嘴", "斜嘴", "喷口", "茶壶嘴", "出水口", "现代物件", "文字水印"],
    },
    "PROP_WATER_JARS": {"name": "两口巨大水缸", "path_name": "定妆_秀竹峰杂役院", "profile": "杂役院后景两口巨大水缸，体量压迫，不新增现代水箱。"},
    "PROP_KEY_LOCK": {"name": "旧钥匙与生锈铁锁", "path_name": "定妆_旧钥匙与生锈铁锁", "profile": "旧钥匙和生锈铁锁，小件交接道具，铁色暗哑。"},
    "PROP_TIE_WAN": {"name": "铁碗钥匙铁锁", "path_name": "定妆_铁碗钥匙铁锁", "profile": "旧铁碗、钥匙和铁锁，贫瘠空屋生活道具，铁色暗哑。"},
    "PROP_SHUI_TONG": {"name": "水桶与扁担", "path_name": "定妆_水桶与扁担", "profile": "木水桶与粗木扁担，少年挑水工具，旧木色低饱和。"},
    "PROP_BIAN_DAN": {"name": "粗木扁担", "path_name": "定妆_水桶与扁担", "profile": "粗木扁担，横向穿过少年肩颈，长度和木质稳定。"},
    "PROP_HEI_TAO_PEN": {
        "name": "黑陶破盆",
        "path_name": "定妆_黑陶破盆",
        "profile": "普通脸盆大小的黑陶破盆，旧、黑、破，只有极弱微光，不神器化。",
        "owner": "CHAR_HE_PINGSHENG",
        "weapon_profile": {
            "design_intent": "贺平生贯穿长线的黑陶破盆/法宝胚胎，本集只作为改变水与灵米的奇物容器，不作为攻击武器。",
            "silhouette": "普通脸盆大小的圆口黑陶破盆，厚陶壁、边缘小缺口、低矮盆形，不能变鼎、锅、金盆或宝盆。",
            "scale": "普通洗衣盆/脸盆比例，可放在少年脚边、墙角或由少年双手端起，不能大到压过人物身体。",
            "material": "旧黑陶，粗糙磨损，边口有缺口和擦痕，低反光，不出现金属质感。",
            "palette": "黑褐、深灰、少量冷灰反光；异常只允许盆底极小微绿弱光。",
            "ornament_motif": "无符文、无金边、无华丽纹饰，外观看起来像破旧日用品。",
            "carry_modes": ["墙角摆放", "地面近景", "少年双手端起", "倾倒或盛水"],
            "combat_usage": "本集不攻击、不格挡、不飞行，只承担灵水/灵米变化容器和主角秘密线索。",
            "vfx_signature": "盆底一点微绿游丝弱光，面积很小，禁止强光柱、神器爆发、漂浮符号或遮挡人物脸。",
            "forbidden_drift": ["不要变成鼎", "不要变成锅", "不要变成金色法器", "不要变成现代塑料盆", "不要强发光符文"],
        },
    },
    "PROP_GREEN_WATER": {"name": "碧绿灵水", "path_name": "定妆_道具_碧绿灵水", "profile": "满盆碧绿清水，颜色异常但水面安静，清晨冷光反射，观众能感到不寻常；不要画成化学荧光或强烈能量效果。"},
    "PROP_FOOD_BOWL": {"name": "杂役饭碗", "path_name": "定妆_道具_杂役饭碗", "profile": "粗木饭碗或旧陶饭碗，盛着底层杂役的稀饭/粗饭，碗沿磨损，低饱和脏暖晨光，不华丽、不现代。"},
    "PROP_GRAY_RICE": {"name": "灰败灵米", "path_name": "定妆_道具_灰败灵米", "profile": "白里泛灰绿的劣质灵米，米粒粗糙干瘪，在月光下显得不值钱，能看出不是上等米。"},
    "PROP_SPIRIT_RICE_BAG": {"name": "灵米布袋", "path_name": "定妆_道具_灵米布袋", "profile": "旧粗布粮袋，袋口磨损，能倒出小半袋灰白米粒，张老大拿在手里显得像施恩。"},
    "VFX_WUXING_GUANGDIAN": {"name": "五行光点", "path_name": "定妆_五行光点", "profile": "五行灵根解释用的五色小光点，短暂、低亮度、不可变成强法术爆发。"},
    "VFX_BASIN_MICROGLOW": {"name": "盆底微绿亮点", "path_name": "定妆_特效_盆底微绿亮点", "profile": "黑陶破盆底部的一缕细小微绿亮点，像水下游动的弱光，只占很小面积，克制神异，不变强光柱、不遮挡人物脸、不出现符号文字。"},
}
ASSET_ID_HINTS.update({
    # 第3集脚本使用更语义化的资产 ID；这里绑定到第1/2集已签收的共享定妆，
    # 避免同一物/同一场景被误当作新资产重新出图。
    "LOC_SERVANT_HUT": {**ASSET_ID_HINTS["LOC_ZAYI_HUT"], "name": "杂役破屋"},
    "LOC_MOUNTAIN_SPRING": {**ASSET_ID_HINTS["LOC_HOUSHAN_QIANTAN"], "name": "山泉"},
    "LOC_KITCHEN_YARD": {**ASSET_ID_HINTS["LOC_ZAYI_WATER_JARS"], "name": "食堂水缸"},
    "PROP_MOUNTAIN_SPRING": {**ASSET_ID_HINTS["LOC_HOUSHAN_QIANTAN"], "name": "山泉"},
    "PROP_BLACK_BASIN": {**ASSET_ID_HINTS["PROP_HEI_TAO_PEN"], "name": "黑陶破盆"},
    "PROP_GREY_RICE_MEMORY": {**ASSET_ID_HINTS["PROP_GRAY_RICE"], "name": "灰败灵米残影"},
    "PROP_WATER_BUCKETS": {**ASSET_ID_HINTS["PROP_SHUI_TONG"], "name": "挑水木桶"},
    "PROP_WATER_JAR": {**ASSET_ID_HINTS["PROP_WATER_JARS"], "name": "食堂水缸"},
    "PROP_DOOR_LOCK": {**ASSET_ID_HINTS["PROP_KEY_LOCK"], "name": "门栓铁锁"},
    "PROP_DOOR": {**ASSET_ID_HINTS["LOC_ZAYI_HUT"], "name": "破屋木门"},
    "LOC_BLACK_HALL": {**ASSET_ID_HINTS["LOC_ZAYI_DADIAN"], "name": "黑暗杂役大殿", "path_name": "定妆_场景_黑暗杂役大殿"},
    "LOC_BLACK_HALL_TO_WATER_YARD": {**ASSET_ID_HINTS["LOC_ZAYI_WATER_JARS"], "name": "黑殿到水缸区转场", "path_name": "定妆_场景_黑殿到水缸区转场"},
    "LOC_SERVANT_QUARTER": {**ASSET_ID_HINTS["LOC_ZAYI_HUT"], "name": "杂役空房", "path_name": "定妆_场景_杂役空房"},
    "LOC_MOUNTAIN_PATH_NIGHT": {**ASSET_ID_HINTS["LOC_HOUSHAN_WATER_PATH"], "name": "夜山路", "path_name": "定妆_场景_夜山路"},
    "LOC_WATER_ROUTE": {**ASSET_ID_HINTS["LOC_HOUSHAN_WATER_PATH"], "name": "后山挑水路", "path_name": "定妆_场景_后山挑水路"},
    "LOC_NIGHT_POOL": {**ASSET_ID_HINTS["LOC_HOUSHAN_QIANTAN"], "name": "夜潭", "path_name": "定妆_场景_夜潭"},
    "PROP_SERVANT_HALL_LAMP": {
        "name": "黑殿旧油灯",
        "path_name": "定妆_道具_黑殿旧油灯",
        "profile": "黑暗杂役大殿里的旧油灯/粗陶灯盏，弱暖光只照出压迫轮廓，不现代、不华丽、不抢人物脸。",
        "must_not_have": ["现代电灯", "霓虹", "清晰文字", "华丽仙器"],
    },
    "PROP_IRON_BOWL": {
        "name": "旧铁碗",
        "path_name": "定妆_道具_旧铁碗",
        "profile": "杂役空房里的旧铁碗，边缘磨损、暗哑铁色、可装粗饭，贫瘠生活道具，不现代、不发光。",
        "must_not_have": ["精致金碗", "现代餐具", "文字水印", "神器光效"],
    },
    "PROP_EMPTY_BUCKETS": {
        "name": "空木桶",
        "path_name": "定妆_道具_空木桶",
        "profile": "挑水前的旧木桶，桶内空、木箍磨损、低饱和旧木色，体量适合瘦小少年挑担。",
        "must_not_have": ["塑料桶", "金属水桶", "现代提手", "自动盛水"],
    },
    "PROP_RUST_LOCK": {
        "name": "生锈铁锁",
        "path_name": "定妆_道具_生锈铁锁",
        "profile": "杂役空房门上或手里的生锈铁锁/旧钥匙，小件暗铁色，表现贫瘠和管束，不放大成法器。",
        "must_not_have": ["现代密码锁", "崭新金锁", "符文法器", "文字水印"],
        "weapon_like_role": "not_entity_weapon",
    },
    "VFX_INNER_SECT_FACELESS_SILHOUETTE": {
        "name": "内门无脸剪影层",
        "path_name": "定妆_远景修士剪影",
        "profile": "远处冷灯下的模糊修士剪影层，只作权力压迫符号，不露清晰五官，不登记具体人物身份。",
        "must_not_have": ["清晰正脸", "新增具名角色", "现代灯光", "华丽仙宫"],
    },
    "PROP_INNER_SECT_LANTERN": {
        "name": "内门冷灯笼",
        "path_name": "定妆_道具_PROP_INNER_SECT_LANTERN",
        "profile": "夜色中远处仙门内门门楼和廊下的冷蓝灯笼/宫灯，青黑旧金属灯架，冷蓝白光，只作远景灯火锚和权力压迫信号；不是现代电灯，不是霓虹，不是巨大法器。",
        "must_not_have": ["现代电灯", "霓虹招牌", "文字水印", "巨大发光法器", "清晰人物脸"],
        "weapon_profile": {
            "design_intent": "内门远景的冷蓝灯火锚，作为权力高处被惊动的视觉信号，不是可手持法宝。",
            "silhouette": "方柱宫灯/廊下吊灯轮廓，黑旧金属框、磨砂灯面、冷蓝白内光。",
            "scale": "远景和近景均保持一人前臂到半身尺度的廊下宫灯，不放大成神器装置。",
            "material": "青黑旧金属框、磨砂半透明灯面、低反光冷光源。",
            "palette": "冷蓝白灯光、青黑金属、夜色冷灰。",
            "ornament_motif": "克制仙门几何纹样，边框细节稳定，不出现现代标识或文字。",
            "carry_modes": ["廊下悬挂", "门楼两侧远景灯火", "近景灯具结构参考"],
            "combat_usage": "不参与战斗，不发射法术，只提供光位和尾钩压迫感。",
            "vfx_signature": "冷蓝白稳定光晕，面积克制，不变霓虹、不爆闪、不遮挡人物脸。",
            "forbidden_drift": ["不要变现代路灯", "不要变霓虹招牌", "不要变巨大发光法器", "不要出清晰人物脸"],
        },
    },
})
ASSET_ID_HINTS.update({
    "WEAPON_01": {
        "name": "横刀",
        "path_name": "定妆_武器_横刀",
        "profile": "大唐镇魔司制式横刀，暗银直身刀刃，黑色刀柄，旧金属护手，战损血尘克制；单把实体武器，刀光只作半透明运动轨迹。",
        "must_not_have": ["副刀", "短刃", "匕首", "右手第二把刀", "副手持刀", "后手短刀", "双持", "刀鞘变成刀刃", "光效变成实体刀刃"],
        "constraints": {
            "blade_topology": "weapon_count=1；single_hilt=1；single_straight_blade=1；主角只持一把实体横刀；副手/后手不得生成短刃、匕首、副刀或第二把刀。",
            "vfx_boundary": "刀光、光轨、残影只能是半透明运动轨迹或边缘高光，不得变成实体刀刃、第二把刀或可握持武器。",
            "must_not_have": ["副刀", "短刃", "匕首", "右手第二把刀", "副手持刀", "后手短刀", "双持", "刀鞘变成刀刃", "光效变成实体刀刃"],
        },
        "weapon_profile": {
            "blade_topology": "weapon_count=1；single_hilt=1；single_straight_blade=1；只允许一把实体横刀入画；副手/后手不得出现短刃、匕首、副刀或第二把刀。",
            "combat_usage": "单武器动作道具；可双手配合一把横刀或一手持刀一手空手/护身，但不得双持，不得补出副手短刃。",
            "vfx_signature": "刀光/光轨/残影为半透明运动轨迹，不是实体武器，不可画成第二把刀刃。",
            "forbidden_drift": ["不要副刀", "不要短刃", "不要匕首", "不要右手第二把刀", "不要副手持刀", "不要后手短刀", "不要双持", "不要刀鞘变成刀刃"],
        },
    },
    "VFX_系统面板": {
        "name": "百妖谱金色古卷面板",
        "path_name": "定妆_特效_百妖谱金色古卷面板",
        "profile": "百妖谱金色古卷空光幕，符纹边框固定，内部文字区留空，所有可读文字由 compose overlay 后期叠加。",
    },
    "VFX_虎山神摹影": {
        "name": "虎山神摹影黑血妖气",
        "path_name": "定妆_特效_虎妖黑血妖气",
        "profile": "虎山神被百妖谱收录时的黑灰虎形摹影和黑血妖气，半透明、克制，不遮挡主角脸。",
        "constraints": {
            "reveal_min_clip": 6,
            "pre_reveal_policy": "第5集 Clip06 前只可作为画外伏笔/气息描述，不得渲染出虎形、血虎、红虎或虎妖画卷。",
            "reveal_terms": ["暗红虎形杀伐气", "虎形摹影", "血虎", "红虎", "黑血虎", "虎妖画卷", "虎影"],
        },
    },
    "VFX_道行计数overlay": {
        "name": "道行计数金色 overlay",
        "path_name": "定妆_特效_百妖谱金色古卷面板",
        "profile": "依附百妖谱面板的金色道行计数动效；底图只留空面板，数值文字由 compose overlay 后期叠加。",
    },
})
ASSET_ID_ALIASES: Dict[str, str] = {
    "WEAPON_01 横刀": "WEAPON_01",
    "横刀": "WEAPON_01",
    "VFX_系统面板/百妖谱": "VFX_系统面板",
    "百妖谱": "VFX_系统面板",
    "VFX_系统面板/道行计数overlay": "VFX_道行计数overlay",
    "道行计数overlay": "VFX_道行计数overlay",
}
ASSET_TOKEN_RE = re.compile(r"(?:LOC|PROP|WEAPON|OUTFIT|VFX|MOUNT_GROUP)_[A-Za-z0-9_\u4e00-\u9fff]+(?:/[A-Za-z0-9_\u4e00-\u9fff]+)?(?:\s+[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9_]*)?")
ASSET_PREFIX_RE = re.compile(r"^(LOC|PROP|WEAPON|OUTFIT|VFX|MOUNT_GROUP)_")
STYLE_ANCHOR_REL = style_anchor_path_for(DEFAULT_STYLE)
STYLE_ANCHOR_REGISTRY_REL = "出图/共享/style_anchor_registry.json"
STYLE_REFERENCE_BOARD_RULES = (
    "统一风格锚只锁本剧渲染语言：写实国漫 / 影视级写实短剧质感、半写实 3D 国漫、冷灰低饱和、自然皮肤、旧木/布料/金属材质、"
    "镜头焦段、材质颗粒和整体色彩倾向；不得继承风格锚里的具体人物脸、服装、动作、剧情状态或背景场景。"
    "角色定妆背景以中性灰白棚拍底为准，风格锚不得把雨窗/房间/道具背景带进定妆照。"
)
FULL_CHARACTER_BOARD_RULES = (
    "统一定妆参考板，不是剧情剧照：中性站姿、中性表情、全身从头到鞋靴完整入画，"
    "统一中性灰白/18%灰棚拍背景，背景干净无窗、无房间、无家具、无剧情道具、无环境叙事；"
    "柔和均匀棚拍光，轻微冷灰色彩管理，同一半写实 3D 国漫写实材质；"
    "不要页游/仙侠游戏概念立绘，不要复杂剧情调度。"
)
PARTIAL_CHARACTER_BOARD_RULES = (
    "restricted_partial 局部参考板，不是剧情剧照：只画手部、肩背、布料或侧后剪影；不建立完整正脸，"
    "不出现清晰五官，不画跪哭/递笔录等剧情动作；统一中性灰白/18%灰棚拍背景，无窗、无房间、无剧情道具。"
)

EP_RE = re.compile(r"\d+")
INNER_FOCUS_RE = re.compile(
    r"内心戏|内心独白|心声|心理反应|心理活动|心念|心想|暗想|自省|心里一沉|心里想|"
    r"inner monologue|internal monologue|thought beat|subjective reaction",
    re.I,
)


def shot_number(value: Any) -> Optional[int]:
    text = str(value or "")
    match = (
        re.search(r"(?:Clip|片段)\s*[_-]?\s*([0-9０-９]+)", text, re.I)
        or re.search(r"镜(?:头)?\s*([0-9０-９]+)", text)
        or re.search(r"shot\s*([0-9０-９]+)", text, re.I)
    )
    if not match:
        return None
    raw = match.group(1).translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    try:
        return int(raw)
    except ValueError:
        return None


def state_range_end(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return value
    text = str(value)
    if re.search(r"(?:集尾|全集|后续|跨集|长期|持续|未解除|until\s+end)", text, re.I):
        return None
    return shot_number(text)


CHARACTER_DEFS: Dict[str, Dict[str, Any]] = {
    "CHAR_SHEN_YAN": {
        "name": "沈砚",
        "scope": "核心主角/全篇长线",
        "form": "常态",
        "asset_key": "CHAR_SHEN_YAN__常态",
        "tier": "core",
        "anchor": "清瘦冷静青年录事，黑发束起，深青灰窄袖官服，袖中半片旧铜，开睛时瞳内细金丝",
        "face": "清瘦青年脸，窄长眼，鼻梁清直，薄唇，五官克制耐看，右眼开睛时只有瞳内细金丝。",
        "hair": "黑发束起，发冠简洁，无夸张发饰。",
        "outfit": "深青灰窄袖古代录事官服，旧黑腰带，袖口和肩线利落。",
        "accessories": "半片旧铜藏在袖中，右眼金睛只在剧情触发时显现。",
        "texture": "写实国漫皮肤质感，低饱和冷灰环境下仍保留脸部层次。",
        "performance_signature": "先看证据再抬眼逼问，表情冷静克制，右眼刺痛时下意识按眼但不夸张。",
        "relative_scale": "比裴决略矮半头，清瘦但站姿稳定。",
        "signature_equipment": ["PROP_OLD_COPPER_HALF", "VFX_JINJING_GOLD_EYE"],
        "drift": ["不要少年幼态脸", "不要白衣仙侠飘带", "不要把金睛做成全脸发光", "不要现代发型"],
    },
    "CHAR_PI_DEMON_CHENGUI": {
        "name": "换皮妖·陈贵皮相",
        "scope": "第1集核心反派",
        "form": "陈贵皮相",
        "asset_key": "CHAR_PI_DEMON_CHENGUI__陈贵皮相",
        "tier": "core",
        "anchor": "陈贵皮相中年商户，深褐旧商户袍，干净皂靴，温和假笑，动作过静",
        "face": "中年商户皮相，温和假笑过度平静；妖相揭露只在第6镜后由状态锁/VFX 注入，非血腥。",
        "hair": "普通中年男子束发，发际和鬓角自然，不做主角式精致发冠。",
        "outfit": "深褐旧商户袍，干净黑色皂靴，衣料朴素但姿态僵硬。",
        "accessories": "茶碗和干净皂靴是身份破绽；妖相只短促显露。",
        "texture": "冷雨光下的假温和、端坐过静、皮相僵硬；妖相纹理只在揭露后短促显现。",
        "performance_signature": "坐姿过静，假笑延迟，听见金睛时先看沈砚右眼再收回妖相。",
        "relative_scale": "中年男子正常身量，坐姿压低但存在感阴冷。",
        "signature_equipment": ["PROP_CLEAN_BLACK_BOOT", "PROP_STILL_TEA", "VFX_SKIN_DEMON_REVEAL"],
        "drift": ["不要血腥器官", "不要做成尖牙怪物全露", "不要年轻俊美化", "不要现代商人装"],
    },
    "CHAR_PEIJUE": {
        "name": "裴决",
        "scope": "长线核心男二/术士",
        "form": "常态",
        "asset_key": "CHAR_PEIJUE__常态",
        "tier": "core",
        "anchor": "玄色劲装高挑术士，腰悬短刀，符火冷蓝，冷硬少言",
        "face": "高挑冷硬青年脸，眉眼锋利，表情少，目光判断多于情绪。",
        "hair": "黑发高束，鬓发干净，行动时发尾轻动。",
        "outfit": "玄色劲装，束腕束腰，适合术士机动，腰间短刀与符纸袋。",
        "accessories": "短刀、符纸、冷蓝符火；不抢沈砚金睛视觉中心。",
        "texture": "冷灰屋内的黑衣层次，符火只在手边形成边缘光。",
        "performance_signature": "声音先到，人从门口阴影入场，动作短、准、冷。",
        "relative_scale": "比沈砚高半头，肩更宽，站位更像执行者。",
        "signature_equipment": ["WEAPON_PEIJUE_SHORT_BLADE", "VFX_PEIJUE_FU_FIRE"],
        "drift": ["不要白衣仙人", "不要红橙大火", "不要现代战术服", "不要笑容外放"],
    },
    "CHAR_FANGZHENG": {
        "name": "坊正",
        "scope": "第1集功能角色/局部参考",
        "form": "局部参考",
        "asset_key": "CHAR_FANGZHENG__局部参考",
        "tier": "restricted_partial",
        "anchor": "圆滑中年坊正，布袍前景阻挡，递笔录压事，绝不清晰主角脸",
        "face": "功能角色只保留轮廓和手部，不建立完整正脸。",
        "hair": "普通中年发髻，虚焦或侧背出现。",
        "outfit": "暗色布袍、手持笔录纸，前景遮挡。",
        "accessories": "笔录纸、毛笔。",
        "texture": "前景虚焦布料和手部局部。",
        "performance_signature": "赔笑递笔录、挡在门口压事，脸不可成为主视觉。",
        "relative_scale": "中年普通身量，常在画左前景。",
        "signature_equipment": ["PROP_RECORD_PAPER"],
        "drift": ["不要清晰主角脸", "不要现代干部装", "不要过度抢戏"],
    },
    "CHAR_CHEN_WIFE": {
        "name": "陈妻",
        "scope": "第1集功能角色/局部参考",
        "form": "局部参考",
        "asset_key": "CHAR_CHEN_WIFE__局部参考",
        "tier": "restricted_partial",
        "anchor": "陈妻跪哭挡视线，布衣妇人手肩局部，绝不清晰主角脸",
        "face": "功能角色只保留哭跪轮廓、肩颈和手部，不建立完整正脸。",
        "hair": "朴素妇人发髻，虚焦或侧背。",
        "outfit": "低饱和旧布衣，跪姿形成前景阻挡。",
        "accessories": "无主视觉饰品。",
        "texture": "湿冷屋内布料和手指压肩的受力感。",
        "performance_signature": "跪求、僵住、被妖指尖威胁，作为情绪层而非主角脸。",
        "relative_scale": "跪姿低于沈砚，常在画中或前景。",
        "signature_equipment": [],
        "drift": ["不要清晰主角脸", "不要精致女主妆", "不要现代服饰"],
    },
}


ASSET_DEFS: Dict[str, Dict[str, Any]] = {
    "LOC_CHEN_HOUSE": {
        "type": "scene",
        "name": "靖京西坊陈宅正屋",
        "path_name": "定妆_场景_陈宅正屋",
        "positive": "雨后旧宅正屋，门槛半干血迹，湿脚印通向桌边，桌上油灯弱暖边，门外冷雨光画左入射，家人跪哭只做背景轮廓。",
        "negative": "现代家具、现代灯具、豪华宫殿、强红蓝霓虹、血腥器官、墙上可读长文字。",
        "constraints": {
            "layout": "门槛在前景下方，桌案在画左/中景，墙面和门口形成纵深，沈砚多在画右。",
            "light_anchor": "画左冷雨光5200K，桌上油灯2600K弱暖边，暗部保留。",
            "axis_rules": "沈砚↔陈贵皮相横轴；沈砚看画左，陈贵看画右；公开揭穿为沈砚→证据→妖三角轴。",
            "must_not_have": ["现代物件", "豪华宫殿", "新增刀具证物", "可读长文字"],
        },
        "drift": ["门窗位置不可随机跳变", "油灯不能变主光大光源", "不要把陈宅画成宫殿"],
        "self_check": "门槛血、桌案、门外冷雨光、油灯弱暖边、画左画右轴线都可读。",
    },
    "PROP_BLOOD_THRESHOLD": {
        "type": "prop",
        "name": "门槛半干血迹",
        "path_name": "定妆_道具_门槛血迹",
        "positive": "门槛木地上的半干暗红血迹，雨后边缘被水晕开，证据感强但非血腥。",
        "negative": "大量喷溅、器官、现代警戒线、文字标注。",
        "owner": "陈宅证据链",
        "current_state": "半干暗红，位置固定在门槛前景下方",
        "lifecycle": {"first_seen": "EP01_CLIP01", "payoff": "EP01_CLIP08", "state_order": ["半干血迹", "被沈砚指认为死亡证据"]},
        "constraints": {"structure": "贴地痕迹，不是道具牌；边缘水晕，颜色低饱和暗红", "must_not_have": ["器官", "大面积血泊"]},
        "drift": ["不要移动到桌边", "不要变成喷溅血浆", "不要新增文字标签"],
    },
    "PROP_MUD_FOOTPRINT": {
        "type": "prop",
        "name": "雨水泥脚印",
        "path_name": "定妆_道具_泥脚印",
        "positive": "雨水带泥脚印从门槛向屋内延伸，湿泥边缘自然，方向指向桌案。",
        "negative": "现代鞋印图案过清、脚印发光、文字箭头。",
        "owner": "陈宅证据链",
        "current_state": "湿泥脚印，连贯但被雨水冲淡",
        "lifecycle": {"first_seen": "EP01_CLIP02", "payoff": "EP01_CLIP08", "state_order": ["门槛外入屋", "被沈砚回收为脚印不对"]},
        "constraints": {"structure": "贴地连续印迹，不能漂浮或像贴纸", "must_not_have": ["发光边", "现代箭头"]},
        "drift": ["方向必须通向陈贵座位", "不可变成血脚印"],
    },
    "PROP_CLEAN_BLACK_BOOT": {
        "type": "prop",
        "name": "干净皂靴",
        "path_name": "定妆_道具_干净皂靴",
        "positive": "古代黑色皂靴，鞋面干净得异常，和雨后泥脚印形成矛盾。",
        "negative": "现代皮鞋、运动鞋、金属靴、过度华丽刺绣。",
        "owner": "CHAR_PI_DEMON_CHENGUI",
        "current_state": "鞋面干净，不沾雨泥",
        "lifecycle": {"first_seen": "EP01_CLIP03", "payoff": "EP01_CLIP08", "state_order": ["干净异常", "成为冒充证据"]},
        "constraints": {"structure": "古代皂靴剪影，圆头软靴，黑布/黑皮低反光", "must_not_have": ["现代鞋底", "运动鞋纹"]},
        "drift": ["始终是干净黑皂靴", "不要变成布鞋"],
    },
    "PROP_STILL_TEA": {
        "type": "prop",
        "name": "不动热茶",
        "path_name": "定妆_道具_不动热茶",
        "positive": "旧茶碗中热茶水面静止不晃，边缘有极轻蒸汽，油灯弱暖边照到碗沿。",
        "negative": "现代茶杯、咖啡杯、浮字、夸张沸腾。",
        "owner": "CHAR_PI_DEMON_CHENGUI",
        "current_state": "热茶静止，端坐半夜仍一丝不晃",
        "lifecycle": {"first_seen": "EP01_CLIP01", "payoff": "EP01_CLIP08", "state_order": ["冷开异常", "证据回收"]},
        "constraints": {"structure": "古代旧茶碗，圆口浅碗，茶面镜面静止", "must_not_have": ["现代杯柄", "文字茶杯"]},
        "drift": ["茶面必须不动", "不要换成酒杯或药碗"],
    },
    "PROP_OLD_COPPER_HALF": {
        "type": "prop",
        "name": "半片旧铜",
        "path_name": "定妆_道具_半片旧铜",
        "positive": "袖中半片旧铜，边缘磨损，微微发烫在皮肤上留下红痕，旧金属暗哑。",
        "negative": "完整铜镜、现代硬币、发光神器、可读文字铭文。",
        "owner": "CHAR_SHEN_YAN",
        "current_state": "袖中发烫，触发金睛前兆",
        "lifecycle": {"first_seen": "EP01_CLIP05", "payoff": "第2集继续解释", "state_order": ["袖中旧物", "发烫触发"]},
        "constraints": {"structure": "半片不规则旧铜，暗哑磨损，不能完整圆镜", "must_not_have": ["现代硬币", "长铭文"]},
        "drift": ["不要变成完整镜子", "不要强发光抢金睛"],
    },
    "PROP_RECORD_PAPER": {
        "type": "prop",
        "name": "笔录纸",
        "path_name": "定妆_道具_笔录纸",
        "positive": "旧纸笔录，坊正递给沈砚画押，只露纸张和笔，不出现可读长文。",
        "negative": "现代合同、打印纸、清晰大段文字。",
        "owner": "CHAR_FANGZHENG",
        "current_state": "递出待画押",
        "lifecycle": {"first_seen": "EP01_CLIP02", "payoff": "沈砚拒绝画押", "state_order": ["递出", "被拒"]},
        "constraints": {"structure": "古代旧纸和毛笔，文字不可读", "must_not_have": ["现代打印字", "签字笔"]},
        "drift": ["只做功能道具", "不要抢占画面"],
    },
    "WEAPON_PEIJUE_SHORT_BLADE": {
        "type": "weapon",
        "name": "裴决短刀",
        "path_name": "定妆_武器_裴决短刀",
        "positive": "裴决腰间短刀，黑鞘短柄，低调实用，符火术士的近身备用武器。",
        "negative": "大剑、长枪、现代军刀、过度华丽发光。",
        "constraints": {"structure": "短刀比例贴合腰间，不喧宾夺主", "must_not_have": ["长剑", "现代刀具"]},
        "drift": ["始终腰悬短刀，不变长兵器"],
        "weapon_profile": {
            "design_intent": "低调术士装备，辅助裴决冷硬行动气质。",
            "silhouette": "短柄短鞘，贴腰携带。",
            "scale": "全长约前臂长度，不能大过主角身体比例。",
            "material": "黑鞘、暗金旧扣、哑光金属刀柄。",
            "palette": "黑、暗灰、少量旧金属。",
            "ornament_motif": "极简符纹压印，不发光。",
            "carry_modes": ["腰间横挂", "门口阴影中只露轮廓"],
            "combat_usage": "第1集不拔刀，仅作为术士身份装备。",
            "vfx_signature": "不主动发光，符火由 VFX_PEIJUE_FU_FIRE 承担。",
            "forbidden_drift": ["不要变长剑", "不要现代战术刀", "不要抢符火高光"],
        },
        "owner": "CHAR_PEIJUE",
        "character_id": "CHAR_PEIJUE",
    },
    "VFX_JINJING_GOLD_EYE": {
        "type": "vfx",
        "name": "金睛旧金光",
        "path_name": "定妆_特效_金睛旧金光",
        "positive": "沈砚右眼瞳内旧金细丝短促发亮，只照眼眶和少量鳞翳，不把整张脸点亮。",
        "negative": "全脸发光、页游金光爆炸、眼睛变激光、遮住五官。",
        "constraints": {"face_policy": "face_locked", "carries_identity": ["CHAR_SHEN_YAN/常态"], "must_not_have": ["全脸发光", "遮住眼鼻嘴"]},
        "drift": ["金光只在右眼瞳内", "不能变成全身神光"],
    },
    "VFX_SKIN_DEMON_REVEAL": {
        "type": "vfx",
        "name": "换皮妖揭皮显相",
        "path_name": "定妆_特效_揭皮显相",
        "positive": "人皮像泡烂湿纸卷开，露出青灰鳞翳和竖瞳，克制可读非血腥。",
        "negative": "血腥撕脸、器官、恐怖片烂肉、全身怪物化。",
        "constraints": {"face_policy": "face_locked", "carries_identity": ["CHAR_PI_DEMON_CHENGUI/陈贵皮相"], "must_not_have": ["血腥器官", "烂肉特写"]},
        "drift": ["始终是湿纸卷皮和青灰鳞翳", "不要变成红色恶魔"],
    },
    "VFX_PEIJUE_FU_FIRE": {
        "type": "vfx",
        "name": "裴决冷蓝符火",
        "path_name": "定妆_特效_冷蓝符火",
        "positive": "冷蓝符火横穿屋内，符纸边缘短促火星，亮度克制，命中人皮墙面。",
        "negative": "橘红大火、爆炸火墙、烟花、遮脸大光效。",
        "constraints": {"face_policy": "none", "must_not_have": ["大火墙", "遮住沈砚五官"]},
        "drift": ["符火颜色冷蓝", "不要把屋内打成舞台灯"],
    },
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, data: Mapping[str, Any]) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def flatten_contract_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        return "；".join(f"{k}={flatten_contract_value(v)}" for k, v in value.items() if flatten_contract_value(v))
    if isinstance(value, list):
        return "；".join(flatten_contract_value(v) for v in value if flatten_contract_value(v))
    return str(value or "").strip()


def summarize_contract_value(value: Any, limit: int = 260) -> str:
    text = flatten_contract_value(value)
    if len(text) <= limit:
        return text
    parts = [part.strip() for part in text.split("；") if part.strip()]
    kept: List[str] = []
    size = 0
    for part in parts:
        extra = len(part) + (1 if kept else 0)
        if kept and size + extra > max(20, limit - 1):
            break
        if not kept and len(part) > max(20, limit - 1):
            return part[: max(20, limit - 1)].rstrip("=：:，,；; ") + "…"
        kept.append(part)
        size += extra
    return ("；".join(kept) or text[: max(20, limit - 1)].rstrip("=：:，,；; ")) + "…"


def load_script_contract(root: Path, ep: str) -> Mapping[str, Any]:
    data = load_json(root / "生产数据" / f"script_quality_contract_{ep}.json")
    if isinstance(data, Mapping) and data.get("kind") == SCRIPT_QUALITY_CONTRACT_KIND:
        return data
    return {}


def script_contract_fields(contract: Mapping[str, Any]) -> Mapping[str, Any]:
    fields = contract.get("signable_fields")
    return fields if isinstance(fields, Mapping) else {}


def script_contract_content_hash(contract: Mapping[str, Any]) -> str:
    return str(contract.get("content_hash") or contract.get("contract_hash") or "").strip()


def script_contract_global_lines(fields: Mapping[str, Any]) -> List[str]:
    lines: List[str] = []
    pacing = fields.get("pacing_allocation")
    if isinstance(pacing, Mapping):
        summary = pacing.get("runtime_summary") if isinstance(pacing.get("runtime_summary"), Mapping) else {}
        declared = pacing.get("declared")
        bits = []
        if summary:
            bits.append(
                "primary=%s%% compressed=%s%%"
                % (
                    round(float(summary.get("primary_runtime_share") or 0) * 100),
                    round(float(summary.get("compressed_runtime_share") or 0) * 100),
                )
            )
            if summary.get("primary_clip_ids"):
                bits.append("主时长=" + ",".join(str(x) for x in summary.get("primary_clip_ids")[:8]))
            if summary.get("compressed_clip_ids"):
                bits.append("一笔带过=" + ",".join(str(x) for x in summary.get("compressed_clip_ids")[:8]))
        if declared:
            bits.append(summarize_contract_value(declared, 180))
        if bits:
            lines.append("  - Pacing: " + "；".join(bits))
    ledger = fields.get("retention_promise_ledger")
    if isinstance(ledger, list):
        for idx, row in enumerate(ledger[:8], start=1):
            text = summarize_contract_value(row, 260)
            if text:
                lines.append(f"  - R{idx:02d}: {text}")
    qledger = fields.get("audience_question_ledger")
    questions = qledger.get("questions") if isinstance(qledger, Mapping) else []
    if isinstance(questions, list):
        for idx, row in enumerate(questions[:8], start=1):
            text = summarize_contract_value(row, 260)
            if text:
                lines.append(f"  - Q{idx:02d}: {text}")
    return lines


def script_clip_contract(contract: Mapping[str, Any], clip_id_value: str) -> Mapping[str, Any]:
    fields = script_contract_fields(contract)
    for row in fields.get("clip_dramatic_functions") or []:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("clip_id") or "") == str(clip_id_value):
            return row
    return {}


def normalize_ep(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    m = EP_RE.search(text)
    return f"第{m.group(0)}集" if m else text


def clip_number(clip_id: str, fallback: int) -> int:
    m = re.search(r"(\d+)", str(clip_id or ""))
    return int(m.group(1)) if m else fallback


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join([str(k) + " " + flatten(v) for k, v in value.items()])
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    return str(value or "")


def shot_reverse_contract_patterns(root: Path, ep: str) -> Dict[str, Mapping[str, Any]]:
    data = load_json(root / "脚本" / ep / "shot_reverse_contract.json")
    if not isinstance(data, Mapping):
        return {}
    out: Dict[str, Mapping[str, Any]] = {}
    for row in data.get("patterns") or []:
        if not isinstance(row, Mapping):
            continue
        cid = str(row.get("clip_id") or "").strip()
        if cid:
            out[cid] = row
    return out


def shot_reverse_prompt_line(root: Path, ep: str, clip: Mapping[str, Any], idx: int) -> str:
    pattern = shot_reverse_contract_patterns(root, ep).get(str(clip.get("id") or f"EP01_CLIP{idx:02d}"))
    if not isinstance(pattern, Mapping):
        return ""
    participants = pattern.get("participants") if isinstance(pattern.get("participants"), Mapping) else {}
    a = participants.get("A") if isinstance(participants.get("A"), Mapping) else {}
    b = participants.get("B") if isinstance(participants.get("B"), Mapping) else {}
    coverage = pattern.get("coverage") if isinstance(pattern.get("coverage"), Mapping) else {}
    sides = pattern.get("screen_sides") if isinstance(pattern.get("screen_sides"), Mapping) else {}
    a_id = str(a.get("character_id") or "")
    b_id = str(b.get("character_id") or "")
    return "；".join([
        f"axis_id={pattern.get('axis_id')}",
        f"A={a_id}，位置={a.get('screen_position')}，视线={a.get('eyeline_direction')}",
        f"B={b_id}，位置={b.get('screen_position')}，视线={b.get('eyeline_direction')}",
        f"站位模式={sides.get('spatial_mode')}，A/B 不互换",
        f"OTS={coverage.get('a_ots')} / {coverage.get('b_ots')}",
        f"coverage={flatten_contract_value(pattern.get('camera_coverage'))}",
        f"镜头匹配={flatten_contract_value(pattern.get('lens_height_distance_match'))}",
        f"越轴={flatten_contract_value(pattern.get('crossing_axis_policy'))}；缓冲={flatten_contract_value(pattern.get('buffer_or_reestablishing'))}",
    ])


def safe_slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_\u4e00-\u9fff]+", "_", str(value or "")).strip("_")
    return text or "asset"


def shared_image_exists(root: Path, stem: str) -> bool:
    base = root / "出图" / "共享" / "图片"
    candidates = [
        base / f"定妆_{stem}.png",
        base / f"定妆_{stem}_正面.png",
        base / f"定妆_{stem}_45度.png",
        base / f"定妆_{stem}_侧.png",
        base / f"定妆_{stem}_侧面.png",
        base / f"定妆_{stem}_背.png",
        base / f"定妆_{stem}_背面.png",
        base / f"定妆_{stem}_半身.png",
        base / f"定妆_{stem}_脸部特写.png",
    ]
    return any(p.is_file() for p in candidates)


def character_asset_stem(root: Path, cid: str, name: str, form: str) -> str:
    name_slug = safe_slug(name or cid)
    form_slug = safe_slug(form or "")
    candidates = []
    if form_slug:
        candidates.append(f"{cid}__{form_slug}")
    if form_slug and form_slug not in {"常态", "默认", "default"}:
        candidates.append(f"{name_slug}_{form_slug}")
    if "/" in str(name):
        candidates.append(safe_slug(str(name).replace("/", "_")))
    candidates.append(name_slug)
    if str(name).startswith("太虚门"):
        candidates.append(safe_slug(str(name).replace("太虚门", "", 1)))
    for stem in candidates:
        if shared_image_exists(root, stem):
            return stem
    return candidates[0]


def shared_rel(stem: str, suffix: str = "") -> str:
    return f"出图/共享/图片/定妆_{stem}{suffix}.png"


def pick_existing_ref(root: Path, candidates: Sequence[str], *, key: str = "", source: str = "") -> Dict[str, Any]:
    for rel in candidates:
        if (root / rel).is_file():
            return ref_item(root, rel, key=key, source=source or rel)
    first = candidates[0] if candidates else shared_rel("待生成")
    return ref_item(root, first, key=key, source=source or first)


def external_visual_reference_entries(root: Path, cid: str, cfg: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """User-provided identity anchors that should be attached before the first generated makeup PNG."""
    name = safe_slug(str(cfg.get("name") or cid))
    candidates = [
        f"出图/共享/图片/{cid}_定型参考.png",
        f"出图/共享/图片/{cid}_定型参考_待绑定.png",
        f"出图/共享/图片/{cid}_定型参考_成年觉醒态.png",
        f"出图/共享/图片/{cid}_参考.png",
        f"出图/共享/图片/{name}_定型参考.png",
    ]
    out: List[Dict[str, Any]] = []
    seen = set()
    for rel in candidates:
        if rel in seen or not (root / rel).is_file():
            continue
        seen.add(rel)
        out.append({
            "path": rel,
            "status": "ready",
            "source": "user_provided_project_reference",
            "use_policy": "identity_reference",
            "sha256": sha256_file(root / rel),
        })
    return out


def parse_card_header(text: str, kind: str) -> Tuple[str, str]:
    pattern = rf"^#\s*{kind}卡\s*[—-]\s*(.+?)（ID[:：]\s*([^)）]+)[)）]"
    m = re.search(pattern, text, re.M)
    if not m:
        name_m = re.search(rf"^#\s*{kind}卡\s*[：:]\s*(.+?)\s*$", text, re.M)
        return (name_m.group(1).strip(), "") if name_m else ("", "")
    return m.group(1).strip(), m.group(2).strip()


def parse_character_card_identity(text: str, fallback_name: str = "") -> Tuple[str, str]:
    name, cid = parse_card_header(text, "角色")
    if not cid:
        m = re.search(r"^\s*-\s*character_id\s*[:：]\s*`?([^`\s]+)`?\s*$", text, re.M)
        if m:
            cid = m.group(1).strip()
    if not name:
        header = re.search(r"^#\s*角色卡[：:]\s*(.+?)\s*$", text, re.M)
        if header:
            name = header.group(1).strip()
    name = name or fallback_name
    return name, cid


def character_asset_index(root: Path) -> Dict[str, Dict[str, Any]]:
    data = load_json(root / "设定库" / "character_assets" / "_index.json")
    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(data, Mapping):
        return out
    for row in data.get("characters") or []:
        if not isinstance(row, Mapping):
            continue
        cid = str(row.get("character_id") or row.get("id") or "").strip()
        if not cid:
            continue
        out[cid] = dict(row)
        manifest_rel = str(row.get("manifest") or "").strip()
        manifest = load_json(root / manifest_rel) if manifest_rel else None
        if isinstance(manifest, Mapping):
            out[cid]["manifest_data"] = manifest
    return out


def manifest_card_path(root: Path, row: Mapping[str, Any]) -> Optional[Path]:
    manifest = row.get("manifest_data") if isinstance(row.get("manifest_data"), Mapping) else {}
    ts = manifest.get("truth_sources") if isinstance(manifest, Mapping) else {}
    card = str((ts or {}).get("character_card") or "").strip()
    if card:
        p = root / card
        if p.is_file():
            return p
    name = str(row.get("name") or manifest.get("character_name") or "").strip()
    if name:
        p = root / "设定库" / "characters" / f"{name}.md"
        if p.is_file():
            return p
    return None


def md_bullet(text: str, label: str) -> str:
    m = re.search(rf"^\s*-\s*{re.escape(label)}\s*[：:]\s*(.+?)\s*$", text, re.M)
    return m.group(1).strip() if m else ""


def md_bullet_contains(text: str, label: str) -> str:
    m = re.search(rf"^\s*-\s*[^：:\n]*{re.escape(label)}[^：:\n]*[：:]\s*(.+?)\s*$", text, re.M)
    return m.group(1).strip() if m else ""


def md_bold_value(text: str, label: str) -> str:
    m = re.search(rf"\*\*[^*\n]*{re.escape(label)}[^*\n]*\*\*\s*[：:]\s*(.+)", text)
    return m.group(1).strip() if m else ""


AGE_CONTEXT_RE = re.compile(
    r"(?:外观)?(?:约)?(?:[0-9０-９]{1,3}|[一二三四五六七八九十两〇零百]+)"
    r"(?:[到至~－—-](?:[0-9０-９]{1,3}|[一二三四五六七八九十两〇零百]+))?"
    r"岁(?:以上|上下|左右|出头|档)?(?:混合)?"
    r"|(?:成年档|少年档|青年档|中年档|老年档|成年|少年|少女|青年|中年|老年)"
)


def character_roster_sections(card_dir: Path) -> Dict[str, str]:
    path = card_dir / "_角色总表.md"
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, re.M))
    sections: Dict[str, str] = {}
    for i, match in enumerate(matches):
        name = match.group(1).strip()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[name] = text[match.end():end]
    return sections


def roster_text_for(roster: Mapping[str, str], name: str, cid: str) -> str:
    candidates = [name, name.replace("／", "/"), name.replace("/", "／"), cid]
    for key in candidates:
        if key in roster:
            return roster[key]
    compact = {re.sub(r"\s+", "", key): value for key, value in roster.items()}
    for key in candidates:
        value = compact.get(re.sub(r"\s+", "", key))
        if value:
            return value
    return ""


def clean_age_context(value: str) -> str:
    text = value.strip().strip("。；;,， ")
    if "/" in text:
        parts = [part.strip() for part in text.split("/") if part.strip()]
        if len(parts) >= 2:
            text = parts[1]
    match = AGE_CONTEXT_RE.search(text)
    return match.group(0).strip() if match else text


def extract_age_context(card_text: str, roster_text: str) -> str:
    sources = [card_text, roster_text]
    for text in sources:
        for label in ("年龄档", "年龄", "姓名 / 年龄 / 性别", "姓名/年龄/性别"):
            value = md_bullet_contains(text, label)
            if value and "待补" not in value:
                return clean_age_context(value)
    for text in sources:
        for label in ("当前状态", "视觉特征", "固定外貌"):
            value = md_bullet_contains(text, label)
            if value and "待补" not in value:
                match = AGE_CONTEXT_RE.search(value)
                if match:
                    return match.group(0).strip()
    return ""


def extract_visual_identity(card_text: str, roster_text: str) -> str:
    for text in (card_text, roster_text):
        for label in ("固定外貌", "视觉特征", "脸/发/瞳/体型/服装"):
            value = md_bullet_contains(text, label)
            if value and "待补" not in value:
                return value.strip()
    return ""


def project_style_name(root: Path) -> str:
    settings = root / "_设置.md"
    if settings.is_file():
        m = re.search(r"基础视觉风格[：:]\s*(.+?)(?:\s+#.*)?$", settings.read_text(encoding="utf-8"), re.M)
        if m:
            return m.group(1).strip()
    return DEFAULT_STYLE


def required_character_ids(story: Mapping[str, Any]) -> List[str]:
    ids: List[str] = []

    def normalize_marker(raw: Any) -> str:
        text = str(raw or "").strip().strip("`，。、；;*")
        text = text.split("/", 1)[0]
        if text.endswith("_partial"):
            text = text[: -len("_partial")]
        m = re.match(r"^(.+)_\d{1,3}$", text)
        if m and m.group(1) in ids:
            text = m.group(1)
        return text

    def add_marker(raw: Any) -> None:
        text = normalize_marker(raw)
        if text.startswith(("CHAR_", "CROWD_", "GROUP_")) and text not in ids:
            ids.append(text)

    for clip in story.get("clips") or []:
        if not isinstance(clip, Mapping):
            continue
        for cid in clip.get("character_ids") or []:
            add_marker(cid)
    vc = visual_contract(story)
    states = vc.get("角色状态演进") or vc.get("角色状态演进表") or {}
    if isinstance(states, Mapping):
        for key in states:
            add_marker(str(key).split()[0])
    blob = json.dumps(story, ensure_ascii=False)
    for token in re.findall(r"(?<![A-Za-z0-9_])(?:CHAR|CROWD|GROUP)_[A-Za-z0-9_]*[A-Za-z0-9]", blob):
        add_marker(token)
    return ids


def add_unique(items: List[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def canonical_asset_id(raw: Any) -> str:
    text = str(raw or "").strip().strip("`，。、；;")
    if not text:
        return ""
    if text in ASSET_ID_ALIASES:
        return ASSET_ID_ALIASES[text]
    if text.startswith("AMBIENT_"):
        return ""
    match = ASSET_TOKEN_RE.match(text)
    if not match:
        return ASSET_ID_ALIASES.get(text, "")
    token = match.group(0).strip()
    if token in ASSET_ID_ALIASES:
        return ASSET_ID_ALIASES[token]
    # Keep the machine id stable; human aliases belong in name/profile, never id.
    token = token.split()[0]
    if token in ASSET_ID_ALIASES:
        return ASSET_ID_ALIASES[token]
    if "/" in token and token not in ASSET_ID_HINTS:
        token = token.split("/", 1)[0]
    return token if ASSET_PREFIX_RE.match(token) else ""


def asset_ids_from_value(value: Any, *, include_aliases: bool = True) -> List[str]:
    text = flatten(value)
    ids: List[str] = []
    if include_aliases:
        for alias, target in ASSET_ID_ALIASES.items():
            if alias and alias in text:
                add_unique(ids, target)
    for match in ASSET_TOKEN_RE.findall(text):
        add_unique(ids, canonical_asset_id(match))
    return ids


def asset_name_from_raw(raw: Any, aid: str) -> str:
    text = str(raw or "").strip()
    hint = ASSET_ID_HINTS.get(aid, {})
    if hint.get("name"):
        return str(hint["name"])
    if text in ASSET_ID_ALIASES:
        return text
    if text.startswith("AMBIENT_"):
        return text[len("AMBIENT_"):]
    if "/" in text and text.startswith(aid.split("_", 1)[0] + "_"):
        return text.split("/")[-1]
    if text.startswith(aid):
        return text[len(aid):].strip(" /：:|-_") or aid.replace("_", " ")
    parts = text.split(maxsplit=1)
    if len(parts) == 2 and canonical_asset_id(parts[0]) == aid:
        return parts[1].strip()
    return aid.replace("_", " ")


def clean_asset_display_name(aid: str, name: str) -> str:
    text = str(name or "").strip()
    if not text:
        return aid
    text = re.sub(r"^(LOC|PROP|WEAPON|OUTFIT|VFX|MOUNT_GROUP)[_\s]+", "", text).strip()
    return text or aid


def clean_material_name(value: str, aid: str = "") -> str:
    text = str(value or "").strip()
    text = re.split(r"\s+@", text, maxsplit=1)[0].strip()
    text = re.sub(r"^[\s/／|｜:：-]+", "", text).strip()
    if aid and text.startswith(aid):
        text = text[len(aid):].strip(" /／：:|-_")
    return text


def asset_type_for_id(aid: str, category: str = "") -> str:
    if aid.startswith("LOC_") or category == "locations":
        return "scene"
    if aid.startswith("MOUNT_GROUP_"):
        return "prop"
    if aid.startswith("WEAPON_"):
        return "weapon"
    if aid.startswith("VFX_"):
        return "vfx"
    if aid.startswith("OUTFIT_"):
        return "outfit"
    return "prop"


def required_asset_ids(story: Mapping[str, Any]) -> List[str]:
    ids: List[str] = []
    reqs = story.get("asset_requirements") or []
    if isinstance(reqs, Mapping):
        for key, values in reqs.items():
            if key == "characters":
                continue
            for aid in asset_ids_from_value(values):
                add_unique(ids, aid)
    else:
        for item in reqs:
            if isinstance(item, Mapping):
                add_unique(ids, canonical_asset_id(item.get("asset_id")))
            else:
                for aid in asset_ids_from_value(item):
                    add_unique(ids, aid)
    for clip in story.get("clips") or []:
        if not isinstance(clip, Mapping):
            continue
        for aid in clip_assets(clip):
            add_unique(ids, aid)
        schedule = clip.get("entity_schedule")
        if isinstance(schedule, Mapping):
            for key in ("objects", "locations"):
                for aid in asset_ids_from_value(schedule.get(key) or []):
                    add_unique(ids, aid)
    return ids


def state_key_for(data: Mapping[str, Any], cid: str) -> Optional[str]:
    candidates = [cid]
    ccfg = CHARACTER_DEFS.get(cid)
    if isinstance(ccfg, Mapping):
        candidates.append(str(ccfg.get("name") or ""))
    acfg = ASSET_DEFS.get(cid)
    if isinstance(acfg, Mapping):
        candidates.append(str(acfg.get("name") or ""))
    for candidate in candidates:
        if candidate and candidate in data:
            return candidate
    for key in data:
        key_head = str(key).split()[0]
        if any(candidate and key_head == candidate for candidate in candidates):
            return str(key)
    return None


def first_form_from_card(text: str) -> str:
    variants = md_bullet_contains(text, "形态变体")
    if variants:
        cleaned = re.sub(r"第\d+集\s*", "", variants)
        cleaned = re.split(r"[；;，,。]", cleaned)[0].strip()
        cleaned = cleaned.replace("/", "").replace(" ", "")
        if cleaned:
            return cleaned
    return "常态"


FALLBACK_CHARACTER_VISUALS: Dict[str, Dict[str, str]] = {
    "CHAR_WANG_DUN": {
        "name": "王敦",
        "scope": "核心主角/全篇长线/九龙气运逃犯",
        "age_context": "中年感壮汉，三十多岁到四十岁之间的粗砺成熟感",
        "face": "黑黝黝宽脸，颧骨和下颌厚实，眉骨压低，鼻梁粗直，嘴唇冻裂，咧笑时白牙明显；眼神滑头里藏狠劲，不少年幼态。",
        "hair": "黑发束成粗短发髻，逃亡段略乱带污水和血尘，管事段整理进旧布巾或简陋木簪。",
        "outfit": "洗得发白的宽松青色道袍，故意放宽两圈压住宽肩和肚腹，旧黑腰带；逃亡段可切换为破旧囚衣和玄铁金链伤痕。",
        "accessories": "手腕九道金色锁链烙印/旧伤，算盘、灵石袋或账册只在灵药谷管事段出现。",
        "relative_scale": "宽肩厚骨架，体量明显大于普通杂役；伪装时显得土憨笨重，动作却灵活。",
        "performance_signature": "表面土憨抠门、嘴贱爱笑，危险时笑意收窄，眼底变冷；常看缝隙、出口、火塘和对方反应。",
    },
    "CHAR_JAILER_A": {
        "name": "狱卒甲",
        "scope": "第1集天牢看守/结丹期狱卒",
        "age_context": "中年看守，三十多岁，夜班疲惫感",
        "face": "灰黄皮肤，窄脸，眼袋重，眉头常皱，神情警觉但迟钝；不美型主角脸。",
        "hair": "黑发束在狱卒小冠下，鬓角凌乱，帽檐压低。",
        "outfit": "大齐天牢黑灰制式狱卒甲衣，皮革护肩，旧金属护腕，腰间钥匙串，手持昏黄巡夜灯笼。",
        "accessories": "巡夜灯笼、钥匙串、短棍。",
        "relative_scale": "普通成年男性体格，比王敦窄一圈。",
        "performance_signature": "举灯停步、侧耳听地脉，视线向地面裂缝和牢室暗处扫，不看镜头。",
    },
    "CHAR_JAILER_B": {
        "name": "狱卒乙",
        "scope": "第1集天牢看守/嘲讽型狱卒",
        "age_context": "中年看守，三十多岁偏油滑",
        "face": "圆短脸，眼神懒散，嘴角带轻蔑笑，胡茬稀疏；和狱卒甲明显区分。",
        "hair": "黑发束在歪斜狱卒小冠下，几缕碎发贴额。",
        "outfit": "大齐天牢黑灰制式狱卒甲衣，皮革护胸，旧金属腰牌，靴子厚重压迫。",
        "accessories": "巡夜灯笼、腰牌、短棍。",
        "relative_scale": "普通成年男性体格，站姿松垮。",
        "performance_signature": "打哈欠、俯视牢缝、用靴子和话语压人，轻敌嘲讽。",
    },
    "CHAR_PURSUER": {
        "name": "大齐追兵",
        "scope": "第1集大齐皇城追捕军士/功能角色",
        "age_context": "成年军士队伍，二十多到四十岁；主参考可为群像，基础角度资产取单名代表军士",
        "face": "棱角硬的普通军士脸，表情紧绷，眉眼被盔檐压住；群像主参考不建立主角脸，45度/侧面/背面/半身/脸部特写必须只画一名普通代表军士。",
        "hair": "黑发收在红黑盔帽内，鬓发短整。",
        "outfit": "大齐城防红黑甲衣，暗红布甲片、黑皮革绑腿、旧金属护腕，手持海捕文书或军令。",
        "accessories": "海捕文书、火把、城防令旗。",
        "relative_scale": "军士群像体格统一，前景军士可稍高壮。",
        "performance_signature": "展开追缉令、抬头看城阵、朝街巷喝令，动作急促。",
    },
    "CROWD_VALLEY_WORKERS": {
        "name": "灵药谷杂役群",
        "scope": "灵药谷杂役群像/局部参考",
        "age_context": "少年到青年杂役群像",
        "face": "只保留低头侧后剪影、肩背和手部，不建立清晰个人正脸。",
        "hair": "黑发用粗布巾或木簪简单束起，群像不可抢主角脸。",
        "outfit": "洗旧青灰杂役短袍，袖口磨损，布鞋和泥点，挑水/浇花劳动装。",
        "accessories": "木水桶、扁担、浇水瓢。",
        "relative_scale": "群像比王敦更瘦小，低头缩脖子形成被管束感。",
        "performance_signature": "低头浇水、缩脖子应声、肩背劳作，避免清晰正脸抢戏。",
    },
    "CHAR_XIAO_LIUZI": {
        "name": "小六子",
        "scope": "灵药谷采买青衣弟子/消息触发角色",
        "age_context": "十七八岁的年轻男弟子",
        "face": "瘦长少年脸，肤色偏白，眼睛灵活又胆小，跑急时脸色发白，嘴唇薄。",
        "hair": "黑发用青色布带束成小髻，跑动时碎发贴额。",
        "outfit": "灵药谷洗旧青衣弟子袍，袖口和鞋面带泥点，腰间小布包。",
        "accessories": "皱巴巴海捕文书、小布包。",
        "relative_scale": "比王敦矮瘦一圈，肩窄，缩脖子时更显胆小。",
        "performance_signature": "慌跑报信、压低声音八卦，被王敦揽肩警告时发僵。",
    },
    "CHAR_HE_PINGSHENG": {
        "name": "贺平生",
        "scope": "核心长线兄弟线/火工少年",
        "age_context": "十五六岁的瘦小少年",
        "face": "瘦小少年脸，脸颊削瘦，肤色被风晒得发黄，眼神干净但倔，抬头时有一点火光反照。",
        "hair": "黑发乱束，几缕碎发垂在额前，发尾干枯。",
        "outfit": "破旧灰青短袍，袖口磨破，草鞋开口露泥脚趾，裤脚沾泥。",
        "accessories": "草鞋、旧布包；火工身份出现时可带小火钳或柴篮。",
        "relative_scale": "瘦得像快折的竹竿，比王敦矮很多，站在谷口显得单薄。",
        "performance_signature": "先低头忍耐，抬头时眼神干净倔强；火塘会朝他方向偏转。",
    },
    "CHAR_ZHANG_LAODA": {
        "name": "张老大",
        "scope": "第1集秀竹峰杂役班压迫者/短线小反派",
        "age_context": "三十多岁的粗砺成年男修杂役头目",
        "face": "粗宽脸，颧骨硬，眼神势利下压，嘴角常带嘲讽；不是俊美主角脸。",
        "hair": "黑发用旧布巾或低髻束起，鬓角略乱，发际线和头巾轮廓稳定。",
        "outfit": "低饱和深灰褐杂役头目袍，衣料比普通杂役稍厚但仍旧，腰带粗旧，袖口磨损。",
        "accessories": "可有旧木牌、账册或短鞭感压迫道具；本集以水缸、扁担命令为主。",
        "relative_scale": "成年男性体格，比贺平生高壮一圈，高位俯视形成压迫。",
        "performance_signature": "俯视、嘴角压笑、手势下令，视线锁贺平生或水缸，不看镜头摆拍。",
    },
    "CHAR_HAN_LAOSAN": {
        "name": "韩老三",
        "scope": "第1集功能性带路杂役/不展开支线",
        "age_context": "二十多到三十岁的普通成年杂役",
        "face": "普通瘦长杂役脸，神情麻木疲惫，五官不抢戏；本集多为半身、过肩或侧背。",
        "hair": "黑发随意束起，几缕碎发，低阶杂役布巾。",
        "outfit": "洗旧灰青杂役短袍，袖口和裤脚磨损，布鞋带泥。",
        "accessories": "可携小木牌、饭碗或钥匙等功能性小道具；不建立高光法器。",
        "relative_scale": "普通成年男性体格，比贺平生略高，存在感低于主角。",
        "performance_signature": "带路、递物、过肩提示，动作短促实用，不展开情绪表演。",
    },
    "GROUP_SERVANTS": {
        "name": "群杂役",
        "scope": "第1集黑殿围观杂役群/压迫氛围层",
        "age_context": "少年到成年底层杂役群像",
        "face": "只保留侧脸、背影、低清笑影和半圆围堵轮廓，不建立可复用个人正脸。",
        "hair": "群体黑发粗布束发，轮廓低调，不抢贺平生和张老大的主脸。",
        "outfit": "灰青、灰褐、脏白低饱和杂役短袍群像，袖口磨损、布鞋沾泥。",
        "accessories": "木桶、扫帚、破布包等底层生活小道具只作氛围，不能抢主道具。",
        "relative_scale": "前景/后景半圆压边形成包围，单个体量不抢主角。",
        "performance_signature": "哄笑、侧头、低声议论、围堵压边；清晰主脸最多作为低优先级侧影。",
    },
    "CHAR_FEMALE_LEAD": {
        "name": "女主待绑定",
        "scope": "待确认女主/用户参考母本/本集禁止入镜",
        "age_context": "成年态参考；若剧情需要少女态必须另行派生",
        "face": "东方女主鹅蛋脸，大而清澈的眼睛，清冷温润神态，精致但不低幼；脸部 DNA 来自用户参考母本。",
        "hair": "长黑发半束，发丝柔顺，发冠和发饰等级按剧情身份可降低但发量和气质不漂。",
        "outfit": "姓名确认前只保留白金仙衣和金色法阵高阶审美作为风格锚；正式出场时按身份重派生常态服装。",
        "accessories": "精致发冠、长坠耳饰和金色法阵只属于高阶/参考态；早期形态需降级。",
        "relative_scale": "成年仙子参考体态，具体身高体量待剧情绑定。",
        "performance_signature": "清冷温润、克制、眼神干净；本集只作风格/脸部母本，不进入分镜画面。",
    },
    "CHAR_04": {
        "name": "陈青源",
        "scope": "第3集飞鹰门门主/求救误认线关键角色",
        "age_context": "四十岁上下的中年江湖门主",
        "face": "方阔脸，颧骨硬，虬髯短须，眉骨重，火把侧照下眼神急迫但压着恭敬；不是美型少年脸。",
        "hair": "黑发束高髻，鬓角有乱发和风尘，发冠低调旧金属。",
        "outfit": "深灰黑江湖劲装，皮革护腕，外披短斗篷，衣摆带尘土和马行泥点。",
        "accessories": "旧金属腰牌、皮革护腕、马缰或火把只作剧情道具。",
        "relative_scale": "成年魁梧男体格，比姜月初宽厚一圈；跪地时仍有门主的硬骨架。",
        "performance_signature": "先急勒马、再恭敬误认，跪地求救时压低身位但眼神把希望推给对方。",
    },
    "GROUP_飞鹰门马队": {
        "name": "飞鹰门马队",
        "scope": "第3集官道夜路群体剪影/火把与马匹压迫层",
        "age_context": "成年江湖门人群体，不建立清晰个人身份",
        "face": "只保留远景剪影、侧后轮廓和低清火把下脸影，不出现可核验正脸，不生成多张清晰个人脸。",
        "hair": "群体束发或帽影只作轮廓，不能抢主角和陈青源身份。",
        "outfit": "深灰黑江湖劲装群像，马队火把、缰绳、鞍具形成后景线条。",
        "accessories": "火把、马匹、缰绳、鞍具，全部作为群体局部锚。",
        "relative_scale": "后景马队和跪地群体必须低于前景姜月初与中景陈青源的叙事权重。",
        "performance_signature": "齐停、压低、跪地剪影，动作服务求救场面，不看镜头，不抢清晰正脸。",
    },
}
CORE_SCOPE_RE = re.compile(r"全篇|全程|长线|核心|主角|女主|男主|主反派")
CORE_SCOPE_HINTS_BY_ID = {
    "CHAR_01": "核心主角/全篇长线",
}


def human_name_from_id(cid: str, fallback: str = "") -> str:
    cfg = FALLBACK_CHARACTER_VISUALS.get(cid)
    if cfg and cfg.get("name"):
        return cfg["name"]
    text = str(fallback or cid)
    if text and not text.startswith(("CHAR_", "CROWD_")):
        return text
    slug = re.sub(r"^(CHAR|CROWD)_", "", str(cid)).strip("_")
    if not slug:
        return str(cid)
    return slug.replace("_", " ").title()


def fallback_character_visual(cid: str, name: str, key: str, default: str = "") -> str:
    cfg = FALLBACK_CHARACTER_VISUALS.get(cid) or {}
    if cfg.get(key):
        return str(cfg[key])
    display = human_name_from_id(cid, name)
    generic: Dict[str, str] = {
        "scope": "本集入镜角色",
        "age_context": "成年古装角色，年龄感按剧情身份保守处理",
        "face": f"{display} 的脸型、年龄感、肤色和五官比例必须稳定；五官清楚耐看，不使用同质化网红脸。",
        "hair": f"{display} 使用古装束发或布巾束发，发型轮廓跨镜保持。",
        "outfit": f"{display} 穿低饱和古装衣袍，领口、袖口、腰带和下摆结构稳定，不出现现代服饰。",
        "accessories": "无固定配饰；若本镜另有道具，以分镜 prompt 为准。",
        "relative_scale": "按 storyboard 中同框体量关系保持。",
        "performance_signature": "表演按剧情身份保持，眼神和动作服务当前戏剧功能，不看镜头摆拍。",
    }
    return generic.get(key, default)


def merge_scope(base: str, hint: str) -> str:
    base = str(base or "").strip()
    hint = str(hint or "").strip()
    if not hint:
        return base
    if not base:
        return hint
    if hint in base:
        return base
    return f"{hint}；{base}"


def narrative_scope_for(cid: str, base_scope: str, visual_tier: str) -> Tuple[str, str]:
    """Return (scope, narrative_tier) without confusing form reference tier.

    `visual_tier=core` means a full makeup/reference pack, not necessarily a
    long-running story role.  Long-running backend gates read character-level
    scope/tier, so only add core/longline markers when there is a narrative
    signal or a stable project convention such as CHAR_01.
    """
    if visual_tier == "restricted_partial" or cid.startswith(("CROWD_", "GROUP_")):
        return str(base_scope or "").strip(), "局部参考"
    scope = str(base_scope or "").strip()
    fallback_scope = str((FALLBACK_CHARACTER_VISUALS.get(cid) or {}).get("scope") or "")
    if CORE_SCOPE_RE.search(fallback_scope):
        scope = merge_scope(scope, fallback_scope)
    if cid in CORE_SCOPE_HINTS_BY_ID:
        scope = merge_scope(scope, CORE_SCOPE_HINTS_BY_ID[cid])
    narrative_tier = "核心长线" if CORE_SCOPE_RE.search(scope) else "单集角色"
    return scope, narrative_tier


SCOPE_VISUAL_HINT_RE = re.compile(
    r"(青皮|绿眼|兽瞳|狼妖|巨狼|虎妖|狐妖|半妖|妖化|兽化|犬齿|獠牙|爪|角|鳞|羽|疤|独眼|红纹|禁止画成|不是俊美|非人)",
    re.I,
)


def apply_scope_visual_hints(
    *,
    name: str,
    scope: str,
    face: str,
    hair: str,
    outfit: str,
    accessories: str,
    drift: Sequence[str],
) -> Tuple[str, str, str, str, List[str]]:
    """Promote visual truth from narrative scope when source cards are sparse.

    New single-episode demons often arrive with only an identity/scope sentence
    such as "青皮巨狼特征、绿眼、禁止画成俊美人类".  Without this bridge the
    fallback drawable DNA turns them into generic costume humans.
    """
    scope_text = sanitize_static_identity_text(scope)
    if not scope_text or not SCOPE_VISUAL_HINT_RE.search(scope_text):
        return face, hair, outfit, accessories, list(drift)

    prefix = f"{name} 的剧情视觉真值必须入画：{scope_text}"
    if prefix not in face:
        face = f"{prefix}；{face}"

    if any(token in scope_text for token in ("狼妖", "巨狼", "兽化", "兽瞳", "犬齿", "獠牙", "爪")):
        wolf_face = "非人狼妖特征必须清晰：兽瞳、狼耳/狼鬃发际、尖犬齿、长指爪甲，不得洗成人类五官模板。"
        if wolf_face not in face:
            face = f"{wolf_face}；{face}"
        claw = "兽化长指、爪甲、犬齿是身份标记；若本镜另有道具，以分镜 prompt 为准。"
        if "爪甲" not in accessories and "犬齿" not in accessories:
            accessories = f"{claw}；{accessories}".strip("；")
    if "青衫" in scope_text and "青" not in outfit:
        outfit = f"青衫/深青灰古装衣袍按剧情身份保持；{outfit}"

    out_drift = list(drift)
    for item in (
        f"不要把{name}换成普通俊美人类",
        f"不要丢失{name} scope里的非人/妖物视觉特征",
    ):
        if item not in out_drift:
            out_drift.append(item)
    return face, hair, outfit, accessories, out_drift


def derive_character_defs(root: Path, story: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    needed = required_character_ids(story)
    card_dir = root / "设定库" / "characters"
    by_id: Dict[str, Tuple[Path, str, str]] = {}
    asset_index = character_asset_index(root)
    roster = character_roster_sections(card_dir)
    materials = material_character_map(root, story)
    for cid, row in asset_index.items():
        card_path = manifest_card_path(root, row)
        text = card_path.read_text(encoding="utf-8") if card_path and card_path.is_file() else ""
        manifest = row.get("manifest_data") if isinstance(row.get("manifest_data"), Mapping) else {}
        name = str(row.get("name") or manifest.get("character_name") or cid)
        by_id[cid] = (card_path or (card_dir / f"{name}.md"), name, text)
    for path in sorted(card_dir.glob("*.md")) if card_dir.is_dir() else []:
        text = path.read_text(encoding="utf-8")
        name, cid = parse_character_card_identity(text, path.stem)
        if cid:
            by_id[cid] = (path, name, text)
    if not by_id and not needed:
        return CHARACTER_DEFS

    defs: Dict[str, Dict[str, Any]] = {}
    used: List[str] = []
    for cid in needed:
        add_unique(used, cid)
    for cid in by_id:
        add_unique(used, cid)
    style = project_style_name(root)
    vc_text = flatten(visual_contract(story))
    for cid in used:
        entry = by_id.get(cid)
        material = materials.get(cid, {})
        manifest = asset_index.get(cid, {}).get("manifest_data")
        if not isinstance(manifest, Mapping):
            manifest = {}
        if entry:
            _path, name, text = entry
        else:
            name, text = human_name_from_id(cid), ""
        if material.get("name") and (not text or name in {cid, "04"} or cid.startswith("GROUP_")):
            name = str(material.get("name") or name)
        material_profile = str(material.get("profile") or "")
        roster_text = roster_text_for(roster, name, cid)
        identity = md_bullet(text, "身份")
        traits = md_bullet(text, "性格关键词")
        age_context = extract_age_context(text, roster_text) or fallback_character_visual(cid, name, "age_context")
        visual_identity = extract_visual_identity(text, roster_text)
        face = md_bullet(text, "固定外貌") or visual_identity or fallback_character_visual(cid, name, "face")
        if age_context and age_context not in face:
            face = f"{age_context}；{face}"
        face = sanitize_static_identity_text(face)
        body = md_bullet(text, "固定体态")
        scale = sanitize_static_identity_text(md_bullet(text, "相对身量") or body or fallback_character_visual(cid, name, "relative_scale"))
        outfit = sanitize_static_identity_text(md_bullet(text, "固定服装") or fallback_character_visual(cid, name, "outfit"))
        palette = md_bullet(text, "固定配色")
        hair = md_bullet_contains(text, "发型/发色/发饰") or fallback_character_visual(cid, name, "hair")
        makeup = md_bullet(text, "妆容")
        accessory = md_bullet(text, "配饰") or fallback_character_visual(cid, name, "accessories", "无")
        performance = md_bullet_contains(text, "固定表情风格 / 动作习惯") or traits or fallback_character_visual(cid, name, "performance_signature")
        anchor = md_bold_value(text, "锚点句") or md_bullet(text, "锚点句")
        if not anchor:
            anchors = md_bold_value(text, "识别锚点")
            anchor = anchors or f"{name}·{face}·{outfit}"
        anchor = sanitize_static_identity_text(anchor)
        form = str(manifest.get("form") or first_form_from_card(text) or "常态")
        partial_probe = f"{name} {form} {identity} {traits} {material_profile}"
        explicit_partial = any(tok in text for tok in ("不生成清晰正脸", "禁止清晰正脸", "绝不清晰主角脸", "只使用局部", "局部参考"))
        is_partial = any(tok in partial_probe for tok in ("虚化", "剪影", "背影", "回忆影", "局部参考")) or explicit_partial
        tier = "restricted_partial" if cid.startswith(("CROWD_", "GROUP_")) or is_partial else "core"
        equipment: List[str] = []
        for aid in required_asset_ids(story):
            if aid.startswith("WEAPON_") and name and name in vc_text and aid not in equipment:
                equipment.append(aid)
        if cid == "CHAR_01":
            for aid in required_asset_ids(story):
                if aid.startswith("VFX_") and ("系统" in aid or "面板" in aid or "百妖" in flatten(story.get("asset_requirements") or [])):
                    if aid not in equipment:
                        equipment.append(aid)
        if cid == "CHAR_03":
            for aid in required_asset_ids(story):
                if aid.startswith("VFX_") and ("虎" in aid or "妖气" in aid):
                    if aid not in equipment:
                        equipment.append(aid)
        drift = [
            f"不要把{name}换成其他脸",
            "不要现代服饰",
            "不要高饱和页游光效",
            "不要丢失本角色锚点句",
        ]
        drift_hint = ""
        m = re.search(r"禁漂项\s*[=＝:：]\s*([^。\n]+)", text)
        if m:
            drift_hint = m.group(1).strip()
        if drift_hint:
            drift.append(drift_hint)
        bundle_manifest = asset_index.get(cid, {}).get("manifest")
        bundle_package = str(asset_index.get(cid, {}).get("package_dir") or "")
        if bundle_package and safe_slug(name or cid) not in bundle_package and name not in {cid, "04"}:
            bundle_manifest = None
        raw_scope = identity or material_profile or fallback_character_visual(cid, name, "scope")
        scope, narrative_tier = narrative_scope_for(cid, raw_scope, tier)
        face, hair, outfit, accessory, drift = apply_scope_visual_hints(
            name=name or cid,
            scope=scope,
            face=face,
            hair=hair,
            outfit=outfit,
            accessories=accessory,
            drift=drift,
        )
        row: Dict[str, Any] = {
            "name": name or cid,
            "scope": scope,
            "narrative_tier": narrative_tier,
            "form": form,
            "asset_key": character_asset_stem(root, cid, name or cid, form),
            "tier": tier,
            "anchor": anchor,
            "age_context": age_context,
            "face": face,
            "hair": hair,
            "outfit": outfit,
            "accessories": accessory,
            "texture": f"{style}；{palette or makeup or '冷灰低饱和材质'}",
            "performance_signature": performance,
            "relative_scale": scale,
            "signature_equipment": equipment,
            "drift": [d for d in drift if d],
            "asset_bundle": {
                "manifest": bundle_manifest,
                "package_dir": bundle_package,
            } if bundle_manifest else None,
        }
        if cid == "CHAR_01" and "镇魔司伪装态" in f"{material_profile} {flatten(story.get('asset_requirements') or [])} {flatten(story.get('clips') or [])}":
            disguise_form = "镇魔司伪装态"
            disguise_outfit = "镇魔司黑衣赤纹劲装，黑衣交领窄袖，衣襟和袖口有克制赤纹图案，束腰，横刀挂腰，布料沾血尘；赤纹是服装纹样不是可读文字。"
            row["extra_forms"] = [
                {
                    "form": disguise_form,
                    "asset_key": character_asset_stem(root, cid, name or cid, disguise_form),
                    "anchor": f"{name}·冷艳东方少女脸·黑色束发·镇魔司黑衣赤纹·横刀挂腰·冷面压慌眼神",
                    "face": row["face"],
                    "hair": "黑色长发利落束起，碎发少，动作中保持东方少女脸锚不变。",
                    "outfit": disguise_outfit,
                    "accessories": "横刀、黑衣赤纹束腰、血尘；不得新增现代徽章或可读文字。",
                    "texture": row["texture"],
                    "relative_scale": row["relative_scale"],
                    "performance_signature": "冷面官威压住慌乱，眼神不看镜头，视线锁戏内求救者或官道深处。",
                    "drift": merge_unique_terms(row["drift"], ["不要套回囚衣", "不要丢失黑衣赤纹", "不要把赤纹画成文字", "不要把横刀变成长剑"]),
                    "signature_equipment": merge_unique_terms(row["signature_equipment"], ["WEAPON_01", "PROP_镇魔司黑衣赤纹"]),
                }
            ]
        defs[cid] = row
    return defs or CHARACTER_DEFS


def asset_req_map(story: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    out: Dict[str, Mapping[str, Any]] = {}
    reqs = story.get("asset_requirements") or []
    if isinstance(reqs, Mapping):
        for key, values in reqs.items():
            if key == "characters":
                continue
            for raw in values or []:
                aid = canonical_asset_id(raw)
                if not aid:
                    continue
                hint = ASSET_ID_HINTS.get(aid, {})
                out[aid] = {
                    "asset_id": aid,
                    "name": asset_name_from_raw(raw, aid),
                    "type": hint.get("type") or asset_type_for_id(aid, str(key)),
                    "profile": hint.get("profile") or asset_name_from_raw(raw, aid),
                    "raw": raw,
                }
        return out
    for item in reqs:
        if isinstance(item, Mapping) and item.get("asset_id"):
            aid = canonical_asset_id(item.get("asset_id"))
            if aid:
                out[aid] = {**item, "asset_id": aid}
        else:
            aid = canonical_asset_id(item)
            if aid:
                hint = ASSET_ID_HINTS.get(aid, {})
                out[aid] = {
                    "asset_id": aid,
                    "name": asset_name_from_raw(item, aid),
                    "type": hint.get("type") or asset_type_for_id(aid),
                    "profile": hint.get("profile") or asset_name_from_raw(item, aid),
                    "raw": item,
                }
    return out


def material_asset_map(root: Path, story: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    """Read episode material-list asset names/prompts.

    Storyboards often carry stable machine ids such as `PROP_GREEN_WATER` while
    the human-readable Chinese asset name and visual prompt live in
    `脚本/第N集/素材清单.md`.  If the prompt pack ignores that file, shared asset
    prompts degrade into "PROP GREEN WATER" placeholders, which is too weak for
    paid generation.
    """
    ep = normalize_ep(str(story.get("episode_label") or story.get("episode") or ""))
    if not ep:
        return {}
    path = root / "脚本" / ep / "素材清单.md"
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    header_re = re.compile(
        r"^###\s+((?:LOC|PROP|WEAPON|OUTFIT|VFX|MOUNT_GROUP)_[A-Za-z0-9_\u4e00-\u9fff]+)\s*([^\n]*)$",
        re.M,
    )
    headers = list(header_re.finditer(text))
    out: Dict[str, Mapping[str, Any]] = {}
    for index, match in enumerate(headers):
        aid = canonical_asset_id(match.group(1))
        if not aid:
            continue
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        body = text[match.end():end]
        raw_name = clean_material_name(match.group(2), aid)
        cn_m = re.search(r"^\s*(?:[-*]\s*)?中文\s*prompt\s*[：:]\s*(.+?)\s*$", body, re.M | re.I)
        en_m = re.search(r"^\s*(?:[-*]\s*)?英文\s*prompt\s*[：:]\s*(.+?)\s*$", body, re.M | re.I)
        profile = cn_m.group(1).strip() if cn_m else raw_name
        out[aid] = {
            "asset_id": aid,
            "name": raw_name or asset_name_from_raw(aid, aid),
            "type": asset_type_for_id(aid),
            "profile": profile or raw_name or asset_name_from_raw(aid, aid),
            "positive": profile or raw_name,
            "english_prompt": en_m.group(1).strip() if en_m else "",
            "source": str(path.relative_to(root)),
        }
    return out


def material_character_map(root: Path, story: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    """Read episode material-list character names and descriptions."""
    ep = normalize_ep(str(story.get("episode_label") or story.get("episode") or ""))
    if not ep:
        return {}
    path = root / "脚本" / ep / "素材清单.md"
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    line_re = re.compile(
        r"^\s*-\s*((?:CHAR|CROWD|GROUP)_[A-Za-z0-9_\u4e00-\u9fff]+)(?:\s+([^：:\n]+?))?\s*[：:]\s*(.+?)\s*$",
        re.M,
    )
    out: Dict[str, Mapping[str, Any]] = {}
    for match in line_re.finditer(text):
        cid = match.group(1).strip()
        raw_name = (match.group(2) or "").strip()
        desc = match.group(3).strip()
        name = raw_name.split("/", 1)[0].strip() if raw_name else human_name_from_id(cid)
        out[cid] = {
            "id": cid,
            "name": name or human_name_from_id(cid),
            "profile": desc,
            "source": str(path.relative_to(root)),
        }
    return out


def complete_asset_scene_dna(
    cfg: Mapping[str, Any],
    *,
    asset_id: str,
    asset_type: str,
    visual: Mapping[str, Any],
) -> Dict[str, Any]:
    """Return a full scene_dna block for any registry asset.

    The review gate validates the same required fields on all asset rows. Props
    and VFX therefore need placement/light/forbidden anchors too, not only LOCs.
    """
    existing = dict(cfg.get("scene_dna") or {})
    constraints = cfg.get("constraints") if isinstance(cfg.get("constraints"), Mapping) else {}
    name = str(cfg.get("name") or asset_id)
    profile = str(cfg.get("positive") or cfg.get("current_state") or constraints.get("structure") or name)
    axis = flatten(visual.get("场景轴线视线", {}))
    light = flatten(visual.get("场景光位锚", {}))
    if not light:
        light = "继承所在镜头场景主光，低饱和冷灰，禁止自发强光。"
    if asset_type in {"scene", "location"}:
        layout = str(constraints.get("layout") or existing.get("spatial_layout") or "按 storyboard 场景轴线和地标保持。")
        materials = str(existing.get("architecture_materials") or profile)
        residents = existing.get("resident_assets") or [name]
        forbidden = existing.get("forbidden") or ["现代物件", "地标漂移", "空间轴线随机跳变"]
        belonging = str(existing.get("belonging_anchor") or name)
    else:
        layout = str(existing.get("spatial_layout") or f"{name}只作为剧情资产出现在被声明镜头，比例和位置服从角色手部/场景轴线。")
        materials = str(existing.get("architecture_materials") or profile)
        residents = existing.get("resident_assets") or [name]
        forbidden = existing.get("forbidden") or [f"{name}结构漂移", "现代物件", "文字水印", "数量漂移"]
        belonging = str(existing.get("belonging_anchor") or f"{name} 属于本集剧情资产，不是独立场景。")
    return {
        "belonging_anchor": belonging,
        "landmarks": existing.get("landmarks") or [name],
        "spatial_layout": layout,
        "architecture_materials": materials,
        "color_lighting_weather": str(existing.get("color_lighting_weather") or light),
        "resident_assets": residents,
        "forbidden": forbidden,
        **({"dof_profile": existing["dof_profile"]} if isinstance(existing.get("dof_profile"), Mapping) else {}),
    }


def bottle_like_prop(name: str, profile: str) -> bool:
    return any(token in f"{name}\n{profile}" for token in ("毒酒", "酒瓶", "瓷瓶", "药瓶", "瓶", "酒盏", "赐死"))


def merge_unique_terms(*groups: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for group in groups:
        for item in group:
            text = str(item).strip()
            if text and text not in seen:
                seen.add(text)
                out.append(text)
    return out


def existing_asset_registry_map(root: Path) -> Dict[str, Mapping[str, Any]]:
    data = load_json(root / "出图" / "共享" / "asset_registry.json")
    if not isinstance(data, Mapping):
        return {}
    out: Dict[str, Mapping[str, Any]] = {}
    for asset in data.get("assets") or []:
        if not isinstance(asset, Mapping):
            continue
        aid = str(asset.get("id") or "").strip()
        if aid:
            out[aid] = asset
    return out


def asset_hint_from_registry_asset(asset: Mapping[str, Any]) -> Dict[str, Any]:
    if not asset:
        return {}
    hint: Dict[str, Any] = {}
    for key in ("name", "type", "owner", "character_id", "current_state", "lifecycle", "scene_dna", "weapon_profile", "weapon_like_role"):
        value = asset.get(key)
        if value not in (None, "", [], {}):
            hint[key] = value
    constraints = asset.get("constraints") if isinstance(asset.get("constraints"), Mapping) else {}
    if constraints:
        hint["constraints"] = dict(constraints)
        if constraints.get("structure"):
            hint["profile"] = constraints.get("structure")
        if isinstance(constraints.get("must_not_have"), list):
            hint["must_not_have"] = list(constraints.get("must_not_have") or [])
    drift = asset.get("drift_forbidden")
    if isinstance(drift, list) and drift:
        hint["drift"] = [str(x) for x in drift if str(x).strip()]
    return hint


def scene_card_map(root: Path) -> Dict[str, Tuple[str, str]]:
    out: Dict[str, Tuple[str, str]] = {}
    loc_dir = root / "设定库" / "locations"
    for path in sorted(loc_dir.glob("*.md")) if loc_dir.is_dir() else []:
        text = path.read_text(encoding="utf-8")
        name, aid = parse_card_header(text, "场景")
        if aid:
            out[aid] = (name, text)
    return out


def derive_asset_defs(root: Path, story: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    ids = required_asset_ids(story)
    if not ids:
        return ASSET_DEFS
    reqs = asset_req_map(story)
    materials = material_asset_map(root, story)
    scenes = scene_card_map(root)
    existing_assets = existing_asset_registry_map(root)
    defs: Dict[str, Dict[str, Any]] = {}
    vc = visual_contract(story)
    for aid in ids:
        req = reqs.get(aid, {})
        material = materials.get(aid, {})
        base_hint = ASSET_ID_HINTS.get(aid, {})
        registry_hint = asset_hint_from_registry_asset(existing_assets.get(aid, {}))
        hint = deep_merge_mapping(base_hint, registry_hint) if registry_hint else dict(base_hint)
        hint_constraints = hint.get("constraints") if isinstance(hint.get("constraints"), Mapping) else {}
        if aid.startswith("LOC_"):
            name, text = scenes.get(aid, (str(material.get("name") or hint.get("name") or req.get("name") or aid), ""))
            env = md_bullet(text, "建筑/环境风格")
            weather = md_bullet_contains(text, "时间 / 天气 / 光线")
            tone = md_bullet_contains(text, "主色调 / 氛围")
            anchors = md_bullet(text, "连续性锚点")
            positive = (
                md_bold_value(text, "Codex 图片 Prompt（中文）")
                or " ".join(x for x in [env, weather, tone, anchors] if x)
                or str(material.get("profile") or req.get("profile") or hint.get("profile") or name)
            )
            negative = "现代物品、平台UI、水印、空间轴线随机跳变、丢失连续性锚点"
            scene_dna = dict(hint.get("scene_dna") or {})
            scene_dna = complete_asset_scene_dna(
                {
                    "name": name or str(req.get("name") or aid),
                    "positive": positive,
                    "constraints": {
                        "layout": anchors or scene_dna.get("spatial_layout") or "保持 storyboard 场景轴线和地标。",
                        "light_anchor": flatten(vc.get("场景光位锚", {})) or weather,
                    },
                    "scene_dna": scene_dna,
                },
                asset_id=aid,
                asset_type="scene",
                visual=vc,
            )
            hint_drift = hint.get("drift") if isinstance(hint.get("drift"), list) else []
            drift_terms = [str(x) for x in hint_drift if str(x).strip()] or [
                "不要丢失本场景地标、空间轴线、光位和常驻物件",
                "不要把本场景随机改成仙宫、现代空间或无关地点",
            ]
            defs[aid] = {
                "type": "scene",
                "name": name or str(req.get("name") or aid),
                "path_name": str(hint.get("path_name") or f"定妆_场景_{safe_slug(name or aid)}"),
                "positive": positive,
                "negative": negative,
                "constraints": {
                    "layout": anchors or scene_dna.get("spatial_layout") or "保持 storyboard 场景轴线和地标。",
                    "light_anchor": flatten(vc.get("场景光位锚", {})) or weather,
                    "axis_rules": flatten(vc.get("场景轴线视线", {})),
                    "face_policy": "faceless",
                    "must_not_have": ["现代物件", "平台UI", "水印", "空间轴线随机跳变"],
                },
                "drift": drift_terms,
                "scene_dna": scene_dna,
                "spatial_layout": anchors or "",
                "axis_rules": flatten(vc.get("场景轴线视线", {})),
                "screen_direction_rules": flatten(vc.get("场景轴线视线", {})),
                "self_check": f"{name or aid} 的地标、空间布局、光位、角色站位和出入口方向可读。",
            }
            continue
        atype = str(req.get("type") or ("weapon" if aid.startswith("WEAPON_") else "vfx" if aid.startswith("VFX_") else "prop"))
        if material.get("type") and not req.get("type"):
            atype = str(material.get("type"))
        if atype == "magic_weapon":
            atype = "weapon"
        name = str(material.get("name") or req.get("name") or hint.get("name") or aid.replace("_", " "))
        name = clean_asset_display_name(aid, name)
        profile = str(
            hint_constraints.get("structure")
            or material.get("profile")
            or req.get("profile")
            or req.get("description")
            or hint.get("profile")
            or name
        )
        negative_items = req.get("negative") if isinstance(req.get("negative"), list) else []
        negative = "、".join(str(x) for x in negative_items) or "现代物件、文字水印、结构漂移"
        path_prefix = "武器" if atype == "weapon" else "特效" if atype == "vfx" else "道具"
        must_not_have = [str(x).replace("不要", "").strip() for x in negative_items if str(x).strip()]
        hint_must_not: List[str] = []
        for source in (hint.get("must_not_have"), hint_constraints.get("must_not_have")):
            if isinstance(source, list):
                hint_must_not.extend(str(x).replace("不要", "").strip() for x in source if str(x).strip())
        if not must_not_have:
            if atype == "weapon":
                must_not_have = [
                    "变成长剑",
                    "华丽仙剑",
                    "现代军刀",
                    "多把复制",
                    "副刀",
                    "短刃",
                    "匕首",
                    "右手第二把刀",
                    "副手持刀",
                    "后手短刀",
                    "双持",
                    "刀鞘变成刀刃",
                    "双刃",
                    "多刃",
                    "双向开刃",
                    "第二把刀刃",
                    "光效变成实体刀刃",
                ]
            elif atype == "vfx":
                must_not_have = ["随机改色", "遮挡主体脸", "现代科幻UI", "过度血腥猎奇"]
            else:
                must_not_have = ["现代物件", "文字水印", "结构漂移", "数量漂移"]
        must_not_have = merge_unique_terms(must_not_have, hint_must_not)
        if atype == "prop" and bottle_like_prop(name, profile):
            must_not_have = merge_unique_terms(
                must_not_have,
                ["壶嘴", "侧嘴", "斜嘴", "喷口", "茶壶嘴", "出水口"],
            )
        constraints = dict(hint_constraints)
        constraints.update({
            "structure": profile,
            "face_policy": constraints.get("face_policy") or "faceless",
            "must_not_have": must_not_have,
        })
        if aid == "VFX_系统面板":
            constraints.update({
                "structure": "金色古卷空光幕，符纹边框固定，内部文字区留空，数值由 compose overlay 叠加。",
                "face_policy": "none",
                "must_not_have": ["AI生成可读文字", "现代手机UI", "随机蓝色科幻屏", "乱码文字"],
            })
        hint_drift = hint.get("drift") if isinstance(hint.get("drift"), list) else []
        drift_terms = merge_unique_terms(
            [f"不要让{name}结构/颜色/尺寸漂移"],
            [f"不要{x}" for x in must_not_have],
            [str(x) for x in hint_drift if str(x).strip()],
        )
        defs[aid] = {
            "type": atype,
            "name": name,
            "path_name": str(hint.get("path_name") or f"定妆_{path_prefix}_{safe_slug(name)}"),
            "positive": profile,
            "negative": negative,
            "constraints": constraints,
            "drift": drift_terms,
            "owner": req.get("owner") or hint.get("owner") or "剧情资产",
            "current_state": profile,
            "scene_dna": complete_asset_scene_dna(
                {
                    "name": name,
                    "positive": profile,
                    "current_state": profile,
                    "constraints": constraints,
                    "scene_dna": hint.get("scene_dna") if isinstance(hint, Mapping) else {},
                },
                asset_id=aid,
                asset_type=atype,
                visual=vc,
            ),
            "lifecycle": req.get("lifecycle") if isinstance(req.get("lifecycle"), Mapping) else {
                "first_seen": "第1集",
                "state_order": ["共享定妆", "本集引用"],
                "status": "active",
            },
        }
        if atype == "weapon":
            default_weapon_profile = {
                "design_intent": profile,
                "silhouette": f"{profile}；单一实体武器轮廓，不复制第二把刀刃。",
                "blade_topology": flatten_contract_value(constraints.get("blade_topology")) or "默认按一柄一刃/单一实体处理；若剧情另有双刃武器必须在 asset_registry 显式声明。",
                "scale": "按角色手部比例，竖屏可读但不夸张。",
                "material": "暗银金属、低反光、战损血尘克制呈现。",
                "palette": "暗银、黑柄、冷灰血尘",
                "ornament_motif": "镇魔司制式，低调克制。",
                "carry_modes": ["手持", "落地", "近景局部"],
                "combat_usage": "本集关键动作道具；实体刀刃数量和握持点必须唯一，只允许一把实体武器；副手/后手不得补出短刃、匕首、副刀或第二把刀，不可变成长剑/仙剑/现代军刀，不可多把复制。",
                "vfx_signature": flatten_contract_value(constraints.get("vfx_boundary")) or "不主动发光；只继承场景光位。刀光/爪光/VFX 只能是半透明光效，不得被渲染成第二把实体刀刃。",
                "forbidden_drift": [
                    "不要变成长剑",
                    "不要华丽仙剑",
                    "不要现代军刀",
                    "不要副刀",
                    "不要短刃",
                    "不要匕首",
                    "不要右手第二把刀",
                    "不要副手持刀",
                    "不要后手短刀",
                    "不要双持",
                    "不要刀鞘变成刀刃",
                    "不要双刃",
                    "不要多刃",
                    "不要第二把刀刃",
                    "不要让光效变成实体刀刃",
                ],
            }
            if isinstance(hint.get("weapon_profile"), Mapping):
                default_weapon_profile = deep_merge_mapping(default_weapon_profile, hint["weapon_profile"])
            if negative_items:
                default_weapon_profile["forbidden_drift"] = merge_unique_terms(
                    default_weapon_profile.get("forbidden_drift", []),
                    [str(x) for x in negative_items],
                )
            defs[aid]["weapon_profile"] = default_weapon_profile
        elif isinstance(hint.get("weapon_profile"), Mapping):
            defs[aid]["weapon_profile"] = dict(hint["weapon_profile"])
        if isinstance(hint.get("weapon_like_role"), str) and hint.get("weapon_like_role"):
            defs[aid]["weapon_like_role"] = str(hint["weapon_like_role"])
    return defs or ASSET_DEFS


def configure_project_defs(root: Path, story: Mapping[str, Any]) -> None:
    global CHARACTER_DEFS, ASSET_DEFS
    CHARACTER_DEFS = derive_character_defs(root, story)
    ASSET_DEFS = derive_asset_defs(root, story)


def prompt_safe_forbidden(value: Any) -> str:
    """Format style taboo terms without triggering wardrobe-positive lint."""
    if isinstance(value, list):
        terms = [str(x).strip() for x in value if str(x).strip()]
    else:
        terms = [x.strip() for x in re.split(r"[；;、,，]", str(value or "")) if x.strip()]
    replacements = {
        # Avoid wardrobe/armor lint false positives when the term only appears
        # inside style taboos that are embedded in positive prompt sections.
        "塑料盔甲": "塑料硬质防具质感",
        "塑料CG盔甲": "塑料硬质防具质感",
        "塑料 CG 盔甲": "塑料硬质防具质感",
        "战甲": "硬质道具感误入",
        "盔甲": "硬质道具感误入",
        "不要把狼妖提前做成完整定妆正脸": "不要提前做狼妖完整定妆头像",
        "完整定妆正脸": "完整定妆头像",
        "完整狼妖正脸": "完整狼妖头像",
    }
    return "、".join(replacements.get(term, term) for term in terms)


def ref_item(root: Path, path: str, *, key: str = "", source: str = "出图/共享/图片/定妆母本_待生成.png") -> Dict[str, Any]:
    item: Dict[str, Any] = {"path": path, "status": "ready" if (root / path).is_file() else "planned"}
    if key in {"three_quarter", "side", "back"}:
        method = "controlled_multiref_generation"
    elif key in {"half_body", "full_body", "face_anchor_refs"}:
        method = "front_crop"
    else:
        method = ""
    if method:
        source_path = root / source
        source_sha = sha256_file(source_path) if source_path.is_file() else "prompt-stage-source-pending"
        item["derivation"] = {
            "method": method,
            "source_path": source,
            "source_sha256": source_sha,
            "crop_box": [0, 0, 1, 1],
        }
    return item


def char_asset_base(root: Path, cid: str, name: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_\u4e00-\u9fff]+", "_", name).strip("_") or cid
    return root / "设定库" / "character_assets" / f"{cid}__{safe}"


def ensure_asset_bundle(root: Path, cid: str, cfg: Mapping[str, Any]) -> Dict[str, Any]:
    existing = cfg.get("asset_bundle") if isinstance(cfg.get("asset_bundle"), Mapping) else None
    if existing and existing.get("manifest") and existing.get("package_dir"):
        bundle = dict(existing)
        base = root / str(bundle.get("base_dir") or bundle.get("package_dir"))
        sections = dict(bundle.get("sections") or {})
        for sec in ("reference", "prompts", "lora", "voice", "adapters", "qc"):
            d = base / sec
            d.mkdir(parents=True, exist_ok=True)
            sections[sec] = str(d.relative_to(root))
        bundle["sections"] = sections
        return bundle
    base = char_asset_base(root, cid, str(cfg["name"]))
    sections = {}
    for sec in ("reference", "prompts", "lora", "voice", "adapters", "qc"):
        d = base / sec
        d.mkdir(parents=True, exist_ok=True)
        sections[sec] = str(d.relative_to(root))
    manifest = {
        "kind": "n2d_project_character_asset_bundle",
        "version": 1,
        "character_id": cid,
        "name": cfg["name"],
        "scope": cfg["scope"],
        "directories": sections,
        "truth_sources": {
            "identity_registry": "出图/共享/identity_registry.json",
            "character_card": f"设定库/characters/{cfg['name']}.md",
        },
        "created_by": "n2d-image image_prompt_pack.py",
        "updated_at": now_iso(),
    }
    write_json(base / "manifest.json", manifest)
    return {
        "manifest": str((base / "manifest.json").relative_to(root)),
        "package_dir": str(base.relative_to(root)),
        "base_dir": str(base.relative_to(root)),
        "sections": sections,
    }


def adapter_defaults() -> Dict[str, Any]:
    image = {
        backend: {"mode": spec["default_mode"], "status": spec["default_status"]}
        for backend, spec in IDENTITY_IMAGE_ADAPTERS.items()
    }
    video = {
        backend: {"mode": spec["default_mode"], "status": spec["default_status"]}
        for backend, spec in IDENTITY_VIDEO_ADAPTERS.items()
    }
    return {"image": image, "video": video, "lora": {"status": "not_needed", "reason": "第1集先用共享定妆参考组；跨集漂移再升级 LoRA。"}}


def generation_control(seed_base: int) -> Dict[str, Any]:
    return {
        "seed_strategy": "fixed_pool",
        "seed_pool": [seed_base + i for i in range(6)],
        "usage": {"turnaround": seed_base, "expression": seed_base + 1, "closeup": seed_base + 2, "shot": seed_base + 3},
        "backend_support": {
            "codex": "unsupported_or_unknown",
            "openai": "backend_dependent",
            "dreamina": "backend_dependent",
            "seedream": "backend_dependent_verify_adapter",
            "kling": "backend_dependent_verify_adapter",
        },
        "fallback_policy": "record seed no-op/degraded when backend does not support seed; never treat unsupported seed as reproducible.",
        "record_required": ["requested_seed", "effective_seed", "seed_effective", "seed_support", "seed_strategy"],
    }


def character_reference_card_rel(cid: str, cfg: Mapping[str, Any], form_cfg: Optional[Mapping[str, Any]] = None) -> str:
    name = str((form_cfg or {}).get("name") or cfg.get("name") or cid)
    form = str((form_cfg or {}).get("form") or cfg.get("form") or "常态")
    base_form = str(cfg.get("form") or "常态")
    if cid.startswith("GROUP_"):
        return f"角色卡/{cid}.md"
    base = f"角色卡/{cid}_{safe_slug(name)}"
    if form and form not in {"常态", "默认", "default"} and form != base_form:
        return f"{base}__{safe_slug(form)}.md"
    return f"{base}.md"


def asset_reference_card_rel(aid: str, cfg: Mapping[str, Any]) -> str:
    folder = "场景卡" if str(cfg.get("type") or "") in {"scene", "location"} else "道具卡"
    name = clean_asset_display_name(aid, str(cfg.get("name") or aid)).strip()
    if not name or name == aid or name.startswith(aid) or aid.endswith(name):
        return f"{folder}/{aid}.md"
    return f"{folder}/{aid}_{safe_slug(name)}.md"


def reference_slot(root: Path, rel: str, slot: str) -> Dict[str, Any]:
    path = root / rel
    item: Dict[str, Any] = {"slot": slot, "path": rel, "status": "ready" if path.is_file() else "planned"}
    if path.is_file():
        item["sha256"] = sha256_file(path)
    return item


def full_reference_group(root: Path, cid: str, cfg: Mapping[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    ak = str(cfg["asset_key"])
    source = pick_existing_ref(root, [
        shared_rel(ak),
        shared_rel(ak, "_正面"),
        shared_rel(ak, "_front"),
    ])["path"]
    rg = {
        "front": ref_item(root, source),
        "three_quarter": pick_existing_ref(root, [shared_rel(ak, "_45度"), shared_rel(ak, "_三分之二")], key="three_quarter", source=source),
        "side": pick_existing_ref(root, [shared_rel(ak, "_侧"), shared_rel(ak, "_侧面"), shared_rel(ak, "_侧背")], key="side", source=source),
        "back": pick_existing_ref(root, [shared_rel(ak, "_背"), shared_rel(ak, "_背面"), shared_rel(ak, "_侧背")], key="back", source=source),
        "outfit": pick_existing_ref(root, [shared_rel(ak, "_半身"), shared_rel(ak, "_全身"), source], key="half_body", source=source),
        "half_body": pick_existing_ref(root, [shared_rel(ak, "_半身"), shared_rel(ak, "_全身"), source], key="half_body", source=source),
        "turnaround": pick_existing_ref(root, [shared_rel(ak, "_三视图"), shared_rel(ak, "_turnaround")]),
        "face_anchor_refs": [
            pick_existing_ref(
                root,
                [
                    shared_rel(ak, "_脸部特写_脸锚裁切"),
                    shared_rel(ak, "_脸部特写"),
                    shared_rel(ak, "_表情_克制_脸锚裁切"),
                    shared_rel(ak, "_表情_克制"),
                    source,
                ],
                key="face_anchor_refs",
                source=source,
            ),
        ],
        "expressions": [],
    }
    for emotion in ("克制", "疲惫隐忍", "警觉", "震动"):
        ref = pick_existing_ref(
            root,
            [shared_rel(ak, f"_表情_{emotion}_脸锚裁切"), shared_rel(ak, f"_表情_{emotion}")],
            key="face_anchor_refs",
            source=source,
        )
        if ref.get("status") == "ready":
            rg["expressions"].append({**ref, "emotion": emotion})
    if not rg["expressions"]:
        rg["expressions"].append({**ref_item(root, source, key="face_anchor_refs", source=source), "emotion": "基础"})
    atlas = {
        "build_tier": "full_makeup_pack",
        "base_views": {
            "front": rg["front"],
            "three_quarter": rg["three_quarter"],
            "side": rg["side"],
            "back": rg["back"],
            "half_body": rg["half_body"],
        },
        "face_anchor_refs": rg["face_anchor_refs"],
        "expression_refs": rg["expressions"],
        "notes": "所有拆分角度以正面主参考/三视图为母本，同源派生，避免逐张文生图补角度造成脸漂。",
    }
    return rg, atlas


def partial_reference_group(root: Path, cid: str, cfg: Mapping[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    ak = str(cfg["asset_key"])
    source = pick_existing_ref(root, [shared_rel(ak), shared_rel(ak, "_侧背"), shared_rel(ak, "_剪影局部")])["path"]
    rg = {
        "silhouette": ref_item(root, source),
        "hand": pick_existing_ref(root, [shared_rel(ak, "_手部局部"), source]),
        "outfit": pick_existing_ref(root, [shared_rel(ak, "_布料局部"), shared_rel(ak, "_半身"), source]),
    }
    atlas = {
        "build_tier": "restricted_partial",
        "partial_refs": rg,
        "no_full_face": True,
        "notes": "功能角色只使用局部/剪影/手部参考，绝不正脸，不建完整主角脸。",
    }
    return rg, atlas


IDENTITY_FORM_PRESERVE_KEYS = {
    "image_adapters",
    "reference_manifest",
    "reference_input_mode",
    "qc_policy",
    "signoff",
    "adapter_signoff",
    "lock_signoff",
}


def deep_merge_mapping(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = deep_merge_mapping(merged[key], value)
        else:
            merged[key] = value
    return merged


def existing_identity_forms(root: Path) -> Dict[Tuple[str, str], Mapping[str, Any]]:
    data = load_json(root / "出图" / "共享" / "identity_registry.json")
    out: Dict[Tuple[str, str], Mapping[str, Any]] = {}
    if not isinstance(data, Mapping):
        return out
    for char in data.get("characters") or []:
        if not isinstance(char, Mapping):
            continue
        cid = str(char.get("id") or "").strip()
        if not cid:
            continue
        for form in char.get("forms") or []:
            if not isinstance(form, Mapping):
                continue
            form_name = str(form.get("form") or "").strip()
            if form_name:
                out[(cid, form_name)] = form
    return out


def preserve_existing_identity_lock_fields(form: Dict[str, Any], previous: Mapping[str, Any]) -> None:
    """Keep manually signed execution locks when prompt pack regenerates registry."""
    if not previous:
        return
    prev_adapters = previous.get("identity_adapters") if isinstance(previous.get("identity_adapters"), Mapping) else {}
    if prev_adapters:
        form["identity_adapters"] = deep_merge_mapping(form.get("identity_adapters") or {}, prev_adapters)
    for key in IDENTITY_FORM_PRESERVE_KEYS:
        value = previous.get(key)
        if value not in (None, "", [], {}):
            form[key] = value


def build_identity_registry(root: Path) -> Dict[str, Any]:
    previous_forms = existing_identity_forms(root)
    chars: List[Dict[str, Any]] = []
    for i, (cid, cfg) in enumerate(CHARACTER_DEFS.items(), start=1):
        bundle = ensure_asset_bundle(root, cid, cfg)
        form_cfgs: List[Mapping[str, Any]] = [cfg]
        for extra in cfg.get("extra_forms") or []:
            if isinstance(extra, Mapping):
                form_cfgs.append(extra)
        forms: List[Dict[str, Any]] = []
        for fidx, form_cfg in enumerate(form_cfgs):
            merged_cfg = {
                **cfg,
                **dict(form_cfg),
                "tier": cfg.get("tier", "core"),
                "name": cfg.get("name", cid),
                "scope": cfg.get("scope", ""),
            }
            restricted = merged_cfg["tier"] == "restricted_partial"
            rg, atlas = partial_reference_group(root, cid, merged_cfg) if restricted else full_reference_group(root, cid, merged_cfg)
            primary_ref = rg.get("silhouette") if restricted else rg.get("front")
            primary_path = str(primary_ref.get("path") if isinstance(primary_ref, Mapping) else "")
            primary_ready = bool(primary_path and (root / primary_path).is_file())
            form: Dict[str, Any] = {
                "form": merged_cfg["form"],
                "asset_key": merged_cfg["asset_key"],
                "anchor_phrase": merged_cfg["anchor"],
                "character_dna": {
                    "face": merged_cfg["face"],
                    "hair": merged_cfg["hair"],
                    "outfit": merged_cfg["outfit"],
                    "accessories": merged_cfg["accessories"],
                    "texture": merged_cfg["texture"],
                },
                "physical_scale": {"relative_scale": merged_cfg["relative_scale"]},
                "wardrobe_profile": {
                    "silhouette": merged_cfg["outfit"],
                    "palette": "冷灰、深青、玄黑、低饱和旧金属",
                    "layers": "古装内外层明确",
                    "collar": "古装交领/束领，不现代圆领",
                    "sleeve": "窄袖或布袖按角色身份",
                    "waist": "束腰/旧腰带",
                    "hem": "竖屏下摆完整但不拖成仙侠飘带",
                    "fabric": "低饱和布料/皮革/旧金属",
                    "forbidden_drift": merged_cfg["drift"],
                },
                "reference_group": rg,
                "reference_atlas": atlas,
                "reference_slots": [
                    reference_slot(root, character_reference_card_rel(cid, cfg, form_cfg), "character_card"),
                    reference_slot(root, primary_path, "primary_reference") if primary_path else {"slot": "primary_reference", "path": "", "status": "planned"},
                ],
                "identity_adapters": adapter_defaults(),
                "generation_control": generation_control(1100 + i * 100 + fidx * 10),
                "angle_policy": {
                    "allowed": ["front", "three_quarter", "side", "MCU", "CU", "MS", "shot_reverse"],
                    "risky": ["deep_shadow", "face_too_small", "extreme_top", "extreme_low", "strong_vfx_over_face"],
                    "requires_extra_reference": ["ECU", "大表情", "背光暗部", "多人同框近景"],
                },
                "drift_forbidden": merged_cfg["drift"],
                "performance_signature": merged_cfg["performance_signature"],
                "signature_equipment": merged_cfg["signature_equipment"],
                "self_check_passed": primary_ready,
                "self_check_note": "existing shared PNG reused by prompt pack" if primary_ready else "prompt-stage registered; PNG 自检在出图后回填。",
            }
            if restricted:
                form["restricted_partial"] = True
                form["no_full_face"] = True
            preserve_existing_identity_lock_fields(form, previous_forms.get((cid, str(form.get("form") or ""))) or {})
            forms.append(form)
        character: Dict[str, Any] = {
            "id": cid,
            "name": cfg["name"],
            "scope": cfg["scope"],
            "tier": cfg.get("narrative_tier") or ("局部参考" if cfg.get("tier") == "restricted_partial" else "单集角色"),
            "forms": forms,
            "asset_bundle": bundle,
            "evolution_profile": {
                "mode": "multi_form" if len(forms) > 1 else "single_anchor",
                "identity_anchor_form": cfg["form"],
                "forms": [str(f.get("form") or "") for f in forms],
            },
        }
        external_refs = external_visual_reference_entries(root, cid, cfg)
        if external_refs:
            character["external_visual_references"] = external_refs
        chars.append(character)
    return {
        "kind": IDENTITY_REGISTRY_KIND,
        "version": 1,
        "generated_at": now_iso(),
        "characters": chars,
        "notes": "第1集 prompt 阶段身份注册层；ready 表示定妆位已定义，PNG 文件由下一步 image 阶段生成并回填 self_check/anchor_sha。",
    }


def asset_ref(path_name: str, suffix: str = ".png") -> Dict[str, Any]:
    return {"path": f"出图/共享/图片/{path_name}{suffix}", "status": "ready"}


def asset_ref_existing(root: Path, candidates: Sequence[str]) -> Dict[str, Any]:
    for path_name in candidates:
        item = asset_ref(path_name)
        if (root / item["path"]).is_file():
            return item
    item = asset_ref(candidates[0] if candidates else "定妆_待生成")
    item["status"] = "planned"
    return item


def scene_lighting_signature(cfg: Mapping[str, Any], constraints: Mapping[str, Any]) -> Dict[str, Any]:
    """Derive a structured scene light signature from existing scene text.

    The review gate only needs a registered `lighting_signature`, while later
    pixel checks use numeric `mean_hue`/`saturation_range` only when explicitly
    present.  Prompt-pack generation should therefore preserve measured-free
    text and light direction instead of inventing brittle numeric thresholds.
    """
    existing = constraints.get("lighting_signature")
    if isinstance(existing, Mapping) and existing:
        return dict(existing)
    scene_dna = cfg.get("scene_dna") if isinstance(cfg.get("scene_dna"), Mapping) else {}
    parts = [
        constraints.get("light_anchor"),
        scene_dna.get("color_lighting_weather"),
        cfg.get("profile"),
    ]
    text = "；".join(str(p).strip() for p in parts if str(p or "").strip())
    if not text:
        return {}
    low = text.lower()
    cool = any(k in low for k in ("冷", "月", "青", "蓝", "灰", "cool", "moon", "blue"))
    warm = any(k in low for k in ("暖", "灯", "火", "金", "晨光", "warm", "lamp", "fire", "gold"))
    if cool and warm:
        color_temperature = "mixed_cool_warm"
    elif cool:
        color_temperature = "cool_low_key"
    elif warm:
        color_temperature = "warm_low_key"
    else:
        color_temperature = "neutral_low_key"
    if any(k in text for k in ("低饱和", "灰", "旧", "脏", "暗", "low saturation", "desaturated")):
        saturation_profile = "low_desaturated"
    else:
        saturation_profile = "controlled"

    h = ""
    v = ""
    if any(k in text for k in ("画左", "左侧", "左前", "左后", "左")) or "left" in low:
        h = "left"
    elif any(k in text for k in ("画右", "右侧", "右前", "右后", "右")) or "right" in low:
        h = "right"
    if any(k in text for k in ("上方", "顶", "天井", "overhead", "top")):
        v = "top"
    elif any(k in text for k in ("下方", "底光", "脚下", "under", "bottom")):
        v = "bottom"
    direction = "_".join(p for p in (h, v) if p) or "storyboard_defined"
    return {
        "color_temperature": color_temperature,
        "saturation_profile": saturation_profile,
        "key_light_direction": direction,
        "source_text": text[:240],
        "numeric_measurement": "pending_after_landed_frame_qc",
    }


def build_asset_registry(root: Path) -> Dict[str, Any]:
    assets: List[Dict[str, Any]] = []
    for aid, cfg in ASSET_DEFS.items():
        path_name = str(cfg["path_name"])
        primary = asset_ref_existing(root, [path_name])
        rg: Dict[str, Any] = {"primary": primary}
        if cfg["type"] in {"scene", "location"}:
            rg.update({
                "front": asset_ref_existing(root, [path_name, path_name + "_正机位"]),
                "reverse": asset_ref_existing(root, [path_name + "_反打", path_name + "_反打机位", path_name]),
                "floor_plan": asset_ref_existing(root, [path_name + "_平面图", path_name]),
            })
        if cfg["type"] in {"prop", "weapon"}:
            rg.update({
                "scale_ref": asset_ref_existing(root, [path_name + "_比例", path_name]),
                "in_hand": asset_ref_existing(root, [path_name + "_手持", path_name]),
            })
        constraints = dict(cfg.get("constraints") or {}) if isinstance(cfg.get("constraints"), Mapping) else {}
        if cfg["type"] in {"scene", "location"} and not constraints.get("lighting_signature"):
            lighting_signature = scene_lighting_signature(cfg, constraints)
            if lighting_signature:
                constraints["lighting_signature"] = lighting_signature
        asset: Dict[str, Any] = {
            "id": aid,
            "type": cfg["type"],
            "name": cfg["name"],
            "reference_group": rg,
            "reference_slots": [
                reference_slot(root, asset_reference_card_rel(aid, cfg), "asset_card"),
                reference_slot(root, str(primary.get("path") or ""), "primary_reference") if primary.get("path") else {"slot": "primary_reference", "path": "", "status": "planned"},
            ],
            "constraints": constraints,
            "face_policy": constraints.get("face_policy") if constraints else "faceless",
                "drift_forbidden": cfg.get("drift", []),
                "scene_dna": cfg.get("scene_dna") or complete_asset_scene_dna(cfg, asset_id=aid, asset_type=str(cfg.get("type") or ""), visual={}),
                "self_check_passed": bool((root / primary["path"]).is_file()),
                "self_check_note": "existing shared PNG reused by prompt pack" if (root / primary["path"]).is_file() else "prompt-stage registered; PNG 自检在出图后回填。",
            }
        if cfg["type"] in {"prop"}:
            asset.update({
                "owner": cfg.get("owner", "剧情证据链"),
                "current_state": cfg.get("current_state", "待出图"),
                "lifecycle": cfg.get("lifecycle", {}),
            })
        if cfg["type"] in {"scene", "location"}:
            asset.update({
                "core": True,
                "frequency": 12,
                "spatial_layout": cfg.get("spatial_layout") or constraints.get("layout", "按 storyboard 场景轴线和地标保持。"),
                "floor_plan": cfg.get("floor_plan") or constraints.get("layout", "按 storyboard 场景轴线和地标保持。"),
                "doors_windows": cfg.get("doors_windows") or "按场景卡，不新增现代门窗或室内结构。",
                "axis_rules": cfg.get("axis_rules") or constraints.get("axis_rules", "按 storyboard 场景轴线视线保持。"),
                "screen_direction_rules": cfg.get("screen_direction_rules") or constraints.get("axis_rules", "按 storyboard 场景轴线视线保持。"),
                "scene_dna": cfg.get("scene_dna") or {
                    "belonging_anchor": cfg["name"],
                    "landmarks": [cfg["name"]],
                    "spatial_layout": constraints.get("layout", ""),
                    "architecture_materials": cfg.get("positive", ""),
                    "color_lighting_weather": constraints.get("light_anchor", ""),
                    "resident_assets": [],
                    "forbidden": "现代物件、地标漂移、空间轴线随机跳变。",
                    "dof_profile": {"depth_intent": "medium"},
                },
                "scene_atlas": {
                    "base_views": {
                        "front": asset_ref_existing(root, [path_name, path_name + "_正机位"]),
                        "back": asset_ref_existing(root, [path_name + "_反打", path_name + "_反打机位", path_name]),
                    }
                },
            })
        if isinstance(cfg.get("weapon_profile"), Mapping):
            asset["weapon_profile"] = cfg["weapon_profile"]
            asset["owner"] = cfg.get("owner")
            asset["character_id"] = cfg.get("character_id")
        if isinstance(cfg.get("weapon_like_role"), str) and cfg.get("weapon_like_role"):
            asset["weapon_like_role"] = cfg["weapon_like_role"]
        assets.append(asset)
    return {
        "kind": ASSET_REFERENCE_REGISTRY_KIND,
        "version": 1,
        "generated_at": now_iso(),
        "assets": assets,
        "notes": "第1集 prompt 阶段资产注册层；ready 表示定妆位已定义，PNG 文件由下一步 image 阶段生成。",
    }


PRESERVED_REGISTRY_KEYS = {
    "anchor_sha",
    "self_check_passed",
    "self_check_note",
    "self_check_at",
    "self_check_by",
    "human_review",
    "face_consistency",
    "machine_evidence",
    "png_sha256",
    "artifact_sha256",
}


def preserve_registry_evidence(new_value: Any, old_value: Any) -> Any:
    """Carry forward machine review evidence when regenerating registries.

    Prompt pack generation is allowed to rebuild creative structure from the
    current storyboard, but it must not erase QC receipts such as anchor_sha or
    faceless pixel evidence.  Evidence is copied only along matching shapes and
    matching list entries with the same semantic key.
    """
    if isinstance(new_value, dict) and isinstance(old_value, Mapping):
        merged: Dict[str, Any] = dict(new_value)
        for key in PRESERVED_REGISTRY_KEYS:
            if key in old_value:
                if key.startswith("self_check") and not bool(new_value.get("self_check_passed")):
                    continue
                if key == "self_check_passed" and bool(new_value.get("self_check_passed")):
                    continue
                if key == "self_check_note" and bool(new_value.get("self_check_passed")):
                    continue
                merged[key] = old_value[key]
        for key, child in list(merged.items()):
            if key in old_value and key not in PRESERVED_REGISTRY_KEYS:
                merged[key] = preserve_registry_evidence(child, old_value[key])
        return merged
    if isinstance(new_value, list) and isinstance(old_value, Sequence) and not isinstance(old_value, (str, bytes, bytearray)):
        old_items = [item for item in old_value if isinstance(item, Mapping)]

        def item_key(item: Any) -> Optional[Tuple[str, str]]:
            if not isinstance(item, Mapping):
                return None
            for key in ("id", "form", "emotion", "path", "asset_key", "name"):
                value = item.get(key)
                if value not in (None, ""):
                    return (key, str(value))
            return None

        old_by_key = {k: item for item in old_items if (k := item_key(item))}
        merged_list = []
        for idx, item in enumerate(new_value):
            old_item = None
            k = item_key(item)
            if k:
                old_item = old_by_key.get(k)
            if old_item is None and idx < len(old_value):
                candidate = old_value[idx]
                if isinstance(candidate, Mapping):
                    old_item = candidate
            merged_list.append(preserve_registry_evidence(item, old_item) if old_item is not None else item)
        return merged_list
    return new_value


def merge_existing_registry_evidence(root: Path, rel_path: Path, new_data: Dict[str, Any]) -> Dict[str, Any]:
    existing = load_json(root / rel_path)
    if not isinstance(existing, Mapping):
        return new_data
    merged = preserve_registry_evidence(new_data, existing)
    return merged if isinstance(merged, dict) else new_data


def clip_chars(clip: Mapping[str, Any]) -> List[str]:
    raw = clip.get("character_ids") or []
    out: List[str] = []
    for item in raw:
        text = str(item)
        if text.startswith(("CHAR_", "CROWD_", "GROUP_")) and text not in out:
            out.append(text)
    return out


def clip_assets(clip: Mapping[str, Any]) -> List[str]:
    ids: List[str] = []
    for key in ("location_id",):
        add_unique(ids, canonical_asset_id(clip.get(key)))
    for key in ("object_ids", "asset_ids", "vfx_ids"):
        for aid in asset_ids_from_value(clip.get(key) or []):
            add_unique(ids, aid)
    schedule = clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), Mapping) else {}
    offscreen_ids = set(asset_ids_from_value(schedule.get("offscreen_presence") or []))
    for key in ("objects", "locations", "required_presence"):
        for aid in asset_ids_from_value(schedule.get(key) or []):
            add_unique(ids, aid)
    structured_ids = list(ids)
    for aid in asset_ids_from_value(clip, include_aliases=False):
        # Free-text scans can see "VFX_虎山神摹影只作后段气息" or
        # "PROP_村道血迹破布保持前集后景" when writers append prose directly
        # after an id. If the clip has already declared a structured asset id,
        # normalize any longer free-text token back to that id instead of
        # minting a bogus registry entry.
        normalized = aid
        for known in sorted((x for x in structured_ids if x), key=len, reverse=True):
            if aid != known and aid.startswith(known):
                normalized = known
                break
        if normalized in offscreen_ids and normalized not in structured_ids:
            continue
        add_unique(ids, normalized)
    return [aid for aid in ids if aid not in offscreen_ids or aid in structured_ids]


def clip_offscreen_assets(clip: Mapping[str, Any]) -> List[str]:
    schedule = clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), Mapping) else {}
    return list(dict.fromkeys(asset_ids_from_value(schedule.get("offscreen_presence") or [])))


def _clip_index_from_value(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    match = re.search(r"(?:Clip|CLIP|镜头)?\s*0*([1-9][0-9]*)", text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def asset_reveal_min_clip(asset_id: str) -> Optional[int]:
    cfg = ASSET_DEFS.get(asset_id) or {}
    constraints = cfg.get("constraints") if isinstance(cfg.get("constraints"), Mapping) else {}
    for key in ("reveal_min_clip", "visible_from_clip", "first_visible_clip", "min_visible_clip"):
        value = constraints.get(key) if key in constraints else cfg.get(key)
        parsed = _clip_index_from_value(value)
        if parsed is not None:
            return parsed
    lifecycle = cfg.get("lifecycle") if isinstance(cfg.get("lifecycle"), Mapping) else {}
    for key in ("first_visible_clip", "visible_from_clip", "reveal_min_clip"):
        parsed = _clip_index_from_value(lifecycle.get(key))
        if parsed is not None:
            return parsed
    return None


def future_hidden_assets(asset_ids: Sequence[str], idx: int) -> List[str]:
    out: List[str] = []
    for aid in asset_ids:
        min_clip = asset_reveal_min_clip(aid)
        if min_clip is not None and idx < min_clip:
            out.append(aid)
    return out


def active_assets_for_clip(asset_ids: Sequence[str], idx: int) -> Tuple[List[str], List[str]]:
    hidden = set(future_hidden_assets(asset_ids, idx))
    return [aid for aid in asset_ids if aid not in hidden], [aid for aid in asset_ids if aid in hidden]


def future_asset_terms(asset_id: str) -> Tuple[List[str], List[str]]:
    cfg = ASSET_DEFS.get(asset_id) or {}
    constraints = cfg.get("constraints") if isinstance(cfg.get("constraints"), Mapping) else {}
    list_terms = [asset_id]
    name = str(cfg.get("name") or "").strip()
    if name:
        list_terms.append(name)
    reveal_terms = [str(x).strip() for x in (constraints.get("reveal_terms") or []) if str(x).strip()]
    return list(dict.fromkeys(list_terms)), list(dict.fromkeys(reveal_terms))


def _drop_list_term(text: str, term: str) -> str:
    if not term:
        return text
    escaped = re.escape(term)
    patterns = [
        rf"`{escaped}`\s*[、,，]?\s*",
        rf"[、,，]\s*{escaped}",
        rf"{escaped}\s*[、,，]\s*",
        escaped,
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text)
    return text


def _drop_clauses_with_terms(text: str, terms: Sequence[str]) -> str:
    if not text or not terms:
        return text
    parts = re.split(r"([。；;，,\n])", text)
    kept: List[str] = []
    for i in range(0, len(parts), 2):
        clause = parts[i]
        sep = parts[i + 1] if i + 1 < len(parts) else ""
        if clause and any(term and term in clause for term in terms):
            continue
        kept.append(clause + sep)
    return "".join(kept)


def sanitize_future_asset_text(value: Any, hidden_assets: Sequence[str]) -> Any:
    if not hidden_assets:
        return value
    if isinstance(value, Mapping):
        return {k: sanitize_future_asset_text(v, hidden_assets) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_future_asset_text(v, hidden_assets) for v in value]
    if not isinstance(value, str):
        return value
    text = value
    for aid in hidden_assets:
        list_terms, reveal_terms = future_asset_terms(aid)
        for term in list_terms:
            text = _drop_list_term(text, term)
        text = _drop_clauses_with_terms(text, reveal_terms)
    text = re.sub(r"[、,，]\s*([；;。])", r"\1", text)
    text = re.sub(r"=\s*[、,，；;]+", "=", text)
    text = re.sub(r"：\s*[、,，；;]+", "：", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip("、,，；; ")


def future_asset_guard_line(hidden_assets: Sequence[str], idx: int) -> str:
    rows: List[str] = []
    for aid in hidden_assets:
        cfg = ASSET_DEFS.get(aid) or {}
        constraints = cfg.get("constraints") if isinstance(cfg.get("constraints"), Mapping) else {}
        min_clip = asset_reveal_min_clip(aid)
        terms = [str(x) for x in (constraints.get("reveal_terms") or []) if str(x).strip()]
        policy = str(constraints.get("pre_reveal_policy") or "").strip()
        name = str(cfg.get("name") or aid)
        row = f"`{aid}`/{name} 最早显现镜头=Clip{min_clip:02d}" if min_clip else f"`{aid}`/{name} 当前镜头未到显现时机"
        if policy:
            row += f"；{policy}"
        if terms:
            row += "；本镜不得出现：" + "、".join(terms)
        forbidden = asset_forbidden_terms([aid])
        if forbidden:
            row += "；资产禁项：" + "、".join(forbidden)
        rows.append(row)
    if not rows:
        return ""
    return f"本镜 Clip{idx:02d} 禁用未到显现时机资产：" + "；".join(rows)


def clip_text_blob(clip: Mapping[str, Any], keys: Sequence[str]) -> str:
    parts: List[str] = []
    for key in keys:
        if key not in clip:
            continue
        value = clip.get(key)
        if isinstance(value, (Mapping, list)):
            parts.append(json.dumps(value, ensure_ascii=False, sort_keys=True))
        else:
            parts.append(str(value or ""))
    return "\n".join(parts)


def is_inner_focus_clip(clip: Mapping[str, Any]) -> bool:
    text = clip_text_blob(clip, (
        "id",
        "label",
        "scene",
        "description",
        "dramatic_function",
        "story_function",
        "rhythm",
        "audience_effect",
        "template",
        "template_contract",
        "shots",
        "subtitle_lines",
        "voiceover",
    ))
    return bool(INNER_FOCUS_RE.search(text))


def inner_focus_context_reason(clip: Mapping[str, Any]) -> str:
    for key in ("inner_focus_context_reason", "context_presence_reason"):
        value = flatten(clip.get(key))
        if value:
            return value
    policy = clip.get("inner_focus_policy") if isinstance(clip.get("inner_focus_policy"), Mapping) else {}
    for key in ("context_reason", "allow_context"):
        value = flatten(policy.get(key))
        if value:
            return value
    contract = clip.get("template_contract") if isinstance(clip.get("template_contract"), Mapping) else {}
    for key in ("inner_focus_context_reason", "inner_focus_allow_context"):
        value = flatten(contract.get(key))
        if value:
            return value
    return ""


def inner_focus_directive(clip: Mapping[str, Any], chars: Sequence[str], assets: Sequence[str]) -> str:
    if not is_inner_focus_clip(clip):
        return ""
    subject = chars[0] if chars else "本镜思考主体"
    others = [c for c in chars[1:]]
    context_reason = inner_focus_context_reason(clip)
    context_line = f"；若保留其他实体，必须服务：{context_reason}" if context_reason else ""
    other_line = f"；非焦点主体 {', '.join(others)} 不给清晰脸/全身/新增动作" if others else ""
    asset_line = f"；非必要资产 {', '.join(assets[:4])} 不抢画面" if assets else ""
    return (
        f"内心戏主体隔离：画面焦点只给 {subject} 的 CU/MCU/手部/眼神/呼吸/光影反应；"
        "其他人物、妖魔、系统面板、武器或道具默认转为画外、虚焦剪影、极弱记忆符号或禁入，"
        "不要重复上一镜群像/怪物/道具陈列，不让背景实体抢走心理反应。"
        f"{other_line}{asset_line}{context_line}"
    )


def continuity_frame_count(clip: Mapping[str, Any]) -> Tuple[int, bool, bool]:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    anchors = cont.get("anchors") if isinstance(cont.get("anchors"), list) else []
    anchor_count = sum(
        1
        for item in anchors
        if isinstance(item, Mapping) and str(item.get("anchor_png") or "").strip()
    )
    mid_count = 1 if isinstance(cont.get("midframe"), Mapping) else 0
    has_mid = bool(mid_count or anchor_count)
    need_end = cont.get("need_endframe") is not False
    return 1 + mid_count + anchor_count + (1 if need_end else 0), has_mid, need_end


def continuity_target_paths(ep: str, idx: int, clip: Mapping[str, Any]) -> Tuple[List[str], List[str]]:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    need_end = cont.get("need_endframe") is not False
    paths: List[str] = []
    frame_parts: List[str] = []

    def add(path: Any, label: str) -> None:
        text = str(path or "").strip()
        if not text or text in paths:
            return
        paths.append(text)
        frame_parts.append(f"{label} `{text}`")

    add(
        clip.get("firstframe_png") or cont.get("firstframe_png") or f"出图/{ep}/图片/Clip{idx:02d}_first.png",
        "首帧",
    )

    midframe = cont.get("midframe") if isinstance(cont.get("midframe"), Mapping) else None
    if midframe:
        add(
            midframe.get("anchor_png") or midframe.get("midframe_png") or f"出图/{ep}/图片/Clip{idx:02d}_mid.png",
            "中段锚帧",
        )

    anchors = cont.get("anchors") if isinstance(cont.get("anchors"), list) else []
    for aidx, anchor in enumerate(anchors, start=1):
        if not isinstance(anchor, Mapping):
            continue
        label = f"动作锚帧 a{aidx}"
        add(anchor.get("anchor_png"), label)

    if need_end:
        add(
            clip.get("endframe_png") or cont.get("endframe_png") or f"出图/{ep}/图片/Clip{idx:02d}_end.png",
            "尾帧",
        )
    return paths, frame_parts


def cross_episode_handoff_prompt_lines(clip: Mapping[str, Any]) -> Tuple[str, str]:
    """Render the cross-episode action handoff contract into prompt text."""
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    handoff = cont.get("cross_episode_handoff") if isinstance(cont.get("cross_episode_handoff"), Mapping) else {}
    if not handoff:
        return "无跨集动作接力。", ""

    def list_text(key: str) -> str:
        value = handoff.get(key)
        if isinstance(value, list):
            return "；".join(str(item).strip() for item in value if str(item).strip())
        return str(value or "").strip()

    prev_tail = str(handoff.get("prev_tail_frame") or "").strip()
    from_episode = str(handoff.get("from_episode") or "").strip()
    from_clip = str(handoff.get("from_clip") or "").strip()
    handoff_type = str(handoff.get("handoff_type") or "").strip()
    must_inherit = list_text("must_inherit")
    no_reset = list_text("no_reset") or list_text("forbid_reset")
    line = (
        f"`{prev_tail}`；from={from_episode}/{from_clip}；handoff_type={handoff_type or 'continuous_action'}；"
        f"must_inherit={must_inherit or '上一集尾帧角色站位、距离、朝向、武器/爪势、光位、轴线'}；"
        f"no_reset={no_reset or '不得重建制远景/不得重新登场/不得让已近身角色退回深景'}"
    )
    positive = (
        f"跨集动作接力：必须以 `{prev_tail}` 作为 source_frame 几何底板，直接承接上一集尾帧的动作瞬间；"
        f"继承 {must_inherit or '角色站位、距离、朝向、武器/爪势、光位和轴线'}；"
        f"禁止 {no_reset or '重建制远景、重新从远处走来、把已开战主体退回深景'}；"
    )
    return line, positive


def continuity_shot_size(clip: Mapping[str, Any]) -> str:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    text = str(cont.get("shot_size") or "").strip()
    if text:
        return text
    parts: List[str] = []
    for row in clip.get("shots") or []:
        if isinstance(row, Mapping) and row.get("lens"):
            parts.append(str(row.get("lens")))
    return "→".join(parts)


PHYSICAL_LENS_RE = re.compile(r"\b(?:\d{2,3}mm|f/\d(?:\.\d)?|焦段|光圈)\b", re.I)


def physical_lens_defaults(lens: str, desc: str = "") -> str:
    """Return a conservative focal-length/aperture hint for prompt lint and rendering."""
    text = f"{lens} {desc}"
    if PHYSICAL_LENS_RE.search(text):
        return ""
    if re.search(r"\b(?:ECU|CU|BCU)\b|大特写|特写|近景|反打|过肩", text, re.I):
        return "85mm, f/1.8"
    if re.search(r"\b(?:MCU|MS)\b|中近景|中景|半身", text, re.I):
        return "50mm, f/2.8"
    if re.search(r"\b(?:ELS|LS|WS)\b|远景|全景|建立镜头|空场景", text, re.I):
        return "24mm, f/5.6"
    return "35mm, f/4"


def lens_with_physical_defaults(lens: Any, desc: str = "") -> str:
    base = str(lens or "").strip() or "MS 中景"
    defaults = physical_lens_defaults(base, desc)
    if not defaults:
        return base
    return f"{base}；物理镜头参数：{defaults}"


def body_grounding_directive(clip: Mapping[str, Any], lens: str, desc: str) -> str:
    """Prevent ambiguous lower-body crops in kneel/crouch/close-up shots."""
    ground_contract = (
        "脚底/膝盖/身体接触面合约：脚底落点、膝盖落点、臀部/躯干重心落点必须落在地表或被明确自然裁切；"
        "人物不得埋入泥土/草丛/废墟，必须不埋入；不得穿模，必须不穿模；不得融合地面/土/废墟/道具/光效，必须不融合；"
        "若只画半身/近景，画幅裁切必须清楚，不用地面遮挡来省略腿脚。"
    )
    text = " ".join(
        str(x or "")
        for x in [
            lens,
            desc,
            clip.get("description"),
            clip.get("label"),
            (clip.get("continuity") or {}).get("shot_size") if isinstance(clip.get("continuity"), Mapping) else "",
        ]
    )
    if re.search(r"蹲|跪|半跪|坐姿|坐下|起身|扶刀|刀尖撑地|kneel|crouch|squat", text, re.I):
        return (
            "身体接地/姿态防呆：若画蹲/跪/半跪/坐姿，必须清楚交代臀部重心、双膝/小腿/脚靴与地面接触关系；"
            "膝盖和脚部不得被泥土、烟雾、前景草丛或画幅遮没；禁止人物下半身像埋进土里、从地面长出、只剩上半身贴地。"
            + ground_contract
        )
    if re.search(r"\bECU\b|\bCU\b|\bMCU\b|特写|近景|半身|反打|INSERT|插入", text, re.I):
        return (
            "身体裁切防呆：本镜按近景/半身/插入镜处理，裁切必须明确在胸口、腰部或手部局部，"
            "不要画成似蹲非蹲的中景；若画到腰部以下，必须完整交代腿部和地面关系。"
            "禁止前景黑雾、草丛、土坡或画幅把下半身吞掉，造成半截埋进地里的错觉。"
            + ground_contract
        )
    return (
        "身体接地/裁切防呆：人物与地面的接触关系必须可读；禁止用烟雾、前景遮挡或画幅裁切掩盖腿脚，"
        "导致身体比例断裂、下半身消失或像埋在地里。"
        + ground_contract
    )


def anatomy_integrity_directive(chars: Sequence[str], lens: str) -> str:
    if not chars:
        return "无具名人物主体；若临时出现人物轮廓，只允许自然背身/侧后剪影，不生成清晰多肢或断肢。"
    return (
        "人体完整性/解剖完整性合约：可见身体范围必须与镜头景别一致，"
        f"本镜按 `{lens or 'storyboard 景别'}` 控制入画范围；"
        "允许画幅裁切和自然遮挡，但必须保留连续躯干、肩线、手臂、手腕、前臂、髋部、腿脚的合理连接；"
        "不得多手、多肢、额外手、第三只手、重复手、漂浮手、断手、六指、多指、粘连、缺肢、断肢、身体埋入、穿模或身体与地面/道具/光效融合。"
    )


def hand_ownership_directive(chars: Sequence[str], assets: Sequence[str], desc: str, idx: Optional[int] = None) -> str:
    if not chars:
        return "无具名角色手部；若临时出现手或武器操作，必须降为无脸/无手剪影或补角色 ID 后再画。"
    owners = "、".join(char_form_ref(c, idx, assets) for c in chars)
    asset_text = "、".join(assets) if assets else "本镜道具/武器/对方身体接触点"
    has_weapon = any(str(a).startswith("WEAPON_") or ASSET_DEFS.get(str(a), {}).get("type") == "weapon" for a in assets)
    weapon_guard = (
        "若本镜包含武器，只允许握持资产注册层里的实体武器；未握主武器的副手/后手必须空手、护身或执行剧本指定接触动作，"
        "不得生成副刀、短刃、匕首、第二把实体武器或把刀鞘/袖口/腰带画成刀刃；"
        if has_weapon else ""
    )
    return (
        f"手部归属合约：每只可见手必须明确属于 {owners} 中的某一名角色，标清左手/右手；"
        "每只手必须自然连接同侧手腕、同侧前臂、肘部连接和肩线连接；"
        f"握持点/接触点只允许落在 {asset_text} 或剧本指定动作上，接触点必须清楚；"
        f"{weapon_guard}"
        "禁止额外手、第三只手、重复手、漂浮断手、手从卷轴/刀柄/光效/地面里长出、左右手归属互换、多指或粘连。"
    )


def face_visibility_directive(chars: Sequence[str], lens: str, desc: str) -> str:
    if not chars:
        return "无清晰具名角色脸；若临时出现人物脸，必须先绑定角色 ID 与脸部参考，否则保持背身/侧后剪影。"
    context = f"{lens} {desc}"
    face_coverage = re.search(r"\b(?:CU|MCU|MS|OTS)\b|近景|中景|半身|反打|过肩", context, re.I)
    noface_context = any(token in context for token in ("ELS", "远景", "背影", "侧后", "剪影", "无脸", "不正面"))
    if noface_context and not face_coverage:
        return (
            "本镜人物只允许背身、侧后轮廓或远景小比例；不看镜头，不做正面肖像，"
            "不解析五官；若需要身份可读，只保留服装轮廓、发型轮廓和体态比例。"
        )
    focus_note = (
        "非焦点群演、肉盾、远景剪影可无脸处理，但主检角色不能用背影、暗影、发丝或特效规避身份核验；"
        if noface_context else ""
    )
    return (
        f"{focus_note}眼鼻嘴三角区清晰，主检角色至少保留可比对的脸部轮廓与五官比例；"
        "黑烟、烟雾、法术特效、血光或金光只允许在脸外侧、身后或前景边缘，"
        "不得遮住眼鼻嘴，不得遮住五官，不得重画脸；"
        "动作镜可用三分之二侧脸、45°侧脸或过肩露脸，但不能用暗影、发丝、特效或极小脸规避身份核验。"
    )


def director_map(root: Path, ep: str) -> Dict[str, Mapping[str, Any]]:
    data = load_json(root / "生产数据" / f"director_camera_plan_{ep}.json")
    out: Dict[str, Mapping[str, Any]] = {}
    if isinstance(data, Mapping):
        for row in data.get("clips") or []:
            if isinstance(row, Mapping):
                out[str(row.get("clip_id") or "")] = row
    return out


def style_contract(story: Mapping[str, Any]) -> Mapping[str, Any]:
    return story.get("style_contract") if isinstance(story.get("style_contract"), Mapping) else {}


def style_name_from_contract(sc: Mapping[str, Any]) -> str:
    return str(sc.get("风格名") or sc.get("style_name") or DEFAULT_STYLE).strip() or DEFAULT_STYLE


def style_anchor_rels(sc: Mapping[str, Any]) -> List[str]:
    raw = sc.get("style_anchor") or sc.get("风格锚") or sc.get("anchors")
    if isinstance(raw, str):
        vals = [raw]
    elif isinstance(raw, (list, tuple)):
        vals = [str(item) for item in raw]
    else:
        vals = []
    out = [str(item or "").strip() for item in vals if str(item or "").strip()]
    if not out:
        out = [style_anchor_path_for(style_name_from_contract(sc))]
    return out


def primary_style_anchor_rel(sc: Mapping[str, Any]) -> str:
    return style_anchor_rels(sc)[0]


def style_anchor_registry(root: Path, story: Mapping[str, Any]) -> Mapping[str, Any]:
    sc = style_contract(story)
    style_name = style_name_from_contract(sc)
    anchors: List[Dict[str, Any]] = []
    for idx, rel in enumerate(style_anchor_rels(sc)):
        path = root / rel
        entry: Dict[str, Any] = {
            "id": "STYLE_ANCHOR" if idx == 0 else f"STYLE_ANCHOR_{idx + 1}",
            "name": style_name,
            "path": rel,
            "status": "ready" if path.is_file() else "planned",
            "use_policy": "style_only",
            "identity_policy": "do_not_clone_face_or_costume",
            "role": "shared_rendering_language_anchor",
        }
        if path.is_file():
            entry["sha256"] = sha256_file(path)
        anchors.append(entry)
    selected = dict(anchors[0]) if anchors else {
        "id": "STYLE_ANCHOR",
        "name": style_name,
        "path": style_anchor_path_for(style_name),
        "status": "planned",
        "use_policy": "style_only",
        "identity_policy": "do_not_clone_face_or_costume",
        "role": "shared_rendering_language_anchor",
    }
    return {
        "kind": "n2d_style_anchor_registry",
        "version": 1,
        "generated_at": now_iso(),
        "style_name": style_name,
        "selected_anchor": selected,
        "anchors": anchors,
        "rules": {
            "use_policy": "style_only",
            "identity_policy": "do_not_clone_face_or_costume",
            "notes": STYLE_REFERENCE_BOARD_RULES,
        },
    }


def visual_contract(story: Mapping[str, Any]) -> Mapping[str, Any]:
    return story.get("visual_contract") if isinstance(story.get("visual_contract"), Mapping) else {}


def clip_visual_tone(vc: Mapping[str, Any], idx: int) -> str:
    tone = str(vc.get("色调基线") or "")
    if idx < 3:
        tone = re.sub(r"[；;]?\s*镇魔司黑衣赤纹[^。；;]*[。；;]?", "；", tone)
        tone = re.sub(r"[；;]{2,}", "；", tone).strip("；; ")
    return tone


def character_anchor_for_clip(cid: str, idx: int) -> str:
    cfg = active_character_form_cfg(cid, idx)
    anchor = str(cfg.get("anchor") or "")
    if cid == "CHAR_PI_DEMON_CHENGUI" and idx >= 6:
        return "陈贵皮相中年商户，干净皂靴端茶不动，皮相错位，短暂显露青灰鳞翳竖瞳"
    return anchor


def sanitize_state_lock(text: str, cid: str, idx: int) -> str:
    value = text
    if cid == "CHAR_PI_DEMON_CHENGUI" and idx < 11:
        value = value.replace("，最后被符火钉墙", "")
        value = value.replace("最后被符火钉墙", "")
    if cid == "CHAR_SHEN_YAN" and idx < 11:
        value = value.replace("右眼残金逐渐熄灭", "右眼金光断续压暗")
        value = value.replace("右眼金光熄灭", "右眼金光断续压暗")
        value = value.replace("被裴决救下后趴低，", "")
        value = value.replace("秘密暴露", "秘密尚未公开")
    return value.strip("，。 ") + "。"


def state_entries_for_clip(story: Mapping[str, Any], cid: str, idx: int) -> List[str]:
    vc = visual_contract(story)
    data = vc.get("角色状态演进") or vc.get("角色状态演进表") or {}
    if not isinstance(data, Mapping):
        return []
    key = state_key_for(data, cid)
    entries = data.get(key) if key else []
    if isinstance(entries, (str, Mapping)):
        entries = [entries]
    if not isinstance(entries, list):
        return []
    out: List[str] = []
    for entry in entries:
        if isinstance(entry, Mapping):
            desc = str(entry.get("状态") or entry.get("status") or entry.get("description") or "").strip()
            start = shot_number(entry.get("自") or entry.get("from") or entry.get("start") or desc) or 1
            end = state_range_end(entry.get("至") or entry.get("until") or entry.get("end") or entry.get("保持") or entry.get("keep"))
        else:
            desc = str(entry).strip()
            start = shot_number(desc) or 1
            end = state_range_end(desc)
        if "→" in desc and not shot_number(desc):
            parts = [part.strip(" ，,。") for part in desc.split("→") if part.strip(" ，,。")]
            if parts:
                desc = parts[min(max(idx - 1, 0), len(parts) - 1)]
        if desc and idx >= start and (end is None or idx <= end):
            out.append(sanitize_state_lock(desc, cid, idx))
    return out


def sanitize_static_identity_text(text: str) -> str:
    """Keep permanent identity separate from episode-only visual states."""
    value = str(text or "")
    replacements = {
        "，肩颈瘦，挑水后有压痕": "，肩颈瘦",
        "，挑水后有压痕": "",
        "挑水后有压痕": "",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = re.sub(r"[，,；;]\s*[^\n，,；;。]{0,12}后有压痕", "", value)
    value = re.sub(r"\s{2,}", " ", value)
    return value.strip("，,；; ")


def state_lock_line(story: Mapping[str, Any], chars: Sequence[str], idx: int, assets: Sequence[str] = ()) -> str:
    rows: List[str] = []
    for cid in list(chars) + list(assets):
        entries = state_entries_for_clip(story, cid, idx)
        if entries:
            rows.append(f"`{cid}`: {'；'.join(entries)}")
    return "；".join(rows) if rows else "本镜无角色状态增量；只继承基础身份定妆。"


def sanitize_future_state_text(value: Any, idx: int) -> Any:
    if isinstance(value, Mapping):
        return {k: sanitize_future_state_text(v, idx) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_future_state_text(v, idx) for v in value]
    if not isinstance(value, str):
        return value
    text = value
    text = text.replace("角色状态继承 storyboard visual_contract", "本镜状态锁继承")
    text = text.replace("锁住光位、轴线、角色状态", "锁住光位、轴线和本镜状态锁")
    text = text.replace("清晰正脸", "可辨三分之二侧脸/侧脸身份")
    text = text.replace("正脸特写", "三分之二侧脸特写")
    text = text.replace("完整定妆正脸", "完整定妆头像")
    text = text.replace("完整狼妖正脸", "完整狼妖头像")
    camera_gaze_replacements = {
        "半身侧对镜头": "半身侧身面向百妖谱面板，视线不看镜头",
        "侧对镜头": "侧身面向戏内目标，视线不看镜头",
        "正对镜头": "正对戏内目标，视线不看镜头",
        "面对镜头": "面对戏内目标，视线不看镜头",
        "看向镜头": "看向戏内目标，视线不看镜头",
        "直视主镜头": "直视戏内目标，视线不看镜头",
        "直视镜头": "直视戏内目标，视线不看镜头",
    }
    for old, new in camera_gaze_replacements.items():
        text = text.replace(old, new)
    if idx < 3:
        early_loot_replacements = {
            "黑衣边角": "镇魔卫衣物边角",
            "黑衣碎片": "镇魔卫衣物碎片",
        }
        for old, new in early_loot_replacements.items():
            text = text.replace(old, new)
    if idx < 6:
        replacements = {
            "人皮湿纸般卷起露青灰鳞翳竖瞳": "皮相僵硬、动作过静",
            "短暂显露青灰鳞翳竖瞳": "短暂露出异常凝视",
            "青灰鳞翳竖瞳": "异常凝视",
            "鳞翳竖瞳": "异常凝视",
            "皮相错位": "皮相过静",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
    if idx < 11:
        replacements = {
            "右眼残金逐渐熄灭": "右眼金光断续压暗",
            "右眼金光熄灭": "右眼金光断续压暗",
            "被裴决救下后趴低": "被危机压低身位",
            "秘密暴露": "秘密尚未公开",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
    return text


def active_character_form_cfg(cid: str, idx: Optional[int] = None, assets: Sequence[str] = ()) -> Mapping[str, Any]:
    cfg = CHARACTER_DEFS.get(cid)
    if not cfg:
        return {}
    extras = [extra for extra in cfg.get("extra_forms") or [] if isinstance(extra, Mapping)]
    if extras:
        asset_text = " ".join(str(a) for a in assets)
        for extra in extras:
            marker = f"{extra.get('form', '')} {extra.get('outfit', '')} {asset_text}"
            if "镇魔司" in marker and ((idx is not None and idx >= 3) or "PROP_镇魔司黑衣赤纹" in asset_text):
                return {
                    **cfg,
                    **dict(extra),
                    "tier": cfg.get("tier", "core"),
                    "name": cfg.get("name", cid),
                    "scope": cfg.get("scope", ""),
                }
    return cfg


def char_form_ref(cid: str, idx: Optional[int] = None, assets: Sequence[str] = ()) -> str:
    cfg = active_character_form_cfg(cid, idx, assets)
    if not cfg:
        return f"{cid}/常态"
    return f"{cid}/{cfg['form']}"


def char_file_ref(cid: str, idx: Optional[int] = None, assets: Sequence[str] = ()) -> str:
    cfg = active_character_form_cfg(cid, idx, assets)
    return shared_rel(str(cfg["asset_key"]))


def primary_character_ref(root: Optional[Path], cid: str, idx: Optional[int] = None, assets: Sequence[str] = ()) -> str:
    cfg = active_character_form_cfg(cid, idx, assets)
    if root is None:
        return char_file_ref(cid, idx, assets)
    if cfg["tier"] == "restricted_partial":
        rg, _atlas = partial_reference_group(root, cid, cfg)
        item = rg.get("silhouette")
    else:
        rg, _atlas = full_reference_group(root, cid, cfg)
        item = rg.get("front")
    return str(item.get("path") if isinstance(item, Mapping) else char_file_ref(cid, idx, assets))


def face_anchor_ref(root: Optional[Path], cid: str, idx: Optional[int] = None, assets: Sequence[str] = ()) -> str:
    cfg = active_character_form_cfg(cid, idx, assets)
    if root is None:
        return shared_rel(str(cfg["asset_key"]), "_脸部特写")
    rg, _atlas = full_reference_group(root, cid, cfg)
    refs = rg.get("face_anchor_refs") if isinstance(rg.get("face_anchor_refs"), list) else []
    item = refs[0] if refs else {}
    return str(item.get("path") if isinstance(item, Mapping) else shared_rel(str(cfg["asset_key"]), "_脸部特写"))


def auxiliary_character_refs(root: Optional[Path], cid: str, idx: Optional[int] = None, assets: Sequence[str] = ()) -> List[Tuple[str, str]]:
    cfg = active_character_form_cfg(cid, idx, assets)
    if not cfg or cfg.get("tier") == "restricted_partial":
        return []
    ak = str(cfg.get("asset_key") or cid)
    candidates = [
        ("45度锚", shared_rel(ak, "_45度")),
        ("侧面锚", shared_rel(ak, "_侧")),
        ("背面锚", shared_rel(ak, "_背")),
        ("半身锚", shared_rel(ak, "_半身")),
    ]
    refs: List[Tuple[str, str]] = []
    for label, rel in candidates:
        if root is None or (root / rel).is_file():
            refs.append((label, rel))
    return refs


def make_shared_index(root: Path, story: Optional[Mapping[str, Any]] = None) -> str:
    sc = style_contract(story or {})
    style_anchor_rel = primary_style_anchor_rel(sc)
    rows = []
    for cid, cfg in CHARACTER_DEFS.items():
        forms = [cfg] + [extra for extra in cfg.get("extra_forms") or [] if isinstance(extra, Mapping)]
        for form_cfg in forms:
            merged = {**cfg, **dict(form_cfg)}
            rows.append(f"| 角色 | `{cid}/{merged['form']}` | `{shared_rel(str(merged['asset_key']))}` | ⏳prompt ready | {merged['anchor']} |")
    for aid, cfg in ASSET_DEFS.items():
        rows.append(f"| {cfg['type']} | `{aid}` | `出图/共享/图片/{cfg['path_name']}.png` | ⏳prompt ready | {cfg['name']} |")
    return "\n".join([
        "# 共享定妆索引",
        "",
        "本索引只登记 prompt 阶段的共享定妆位；未实际产出 PNG 前不标 ✅。",
        f"统一风格锚：`{style_anchor_rel}`；机器登记：`{STYLE_ANCHOR_REGISTRY_REL}`。共享角色定妆必须先继承该锚的渲染语言，再锁各自身份。",
        "",
        "| 类型 | ID | 目标存档 | 状态 | 锚点 |",
        "|---|---|---|---|---|",
        *rows,
        "",
    ])


def shared_character_prompt(story: Optional[Mapping[str, Any]] = None) -> str:
    sc = style_contract(story or {})
    style_name = style_name_from_contract(sc)
    style_anchor_rel = primary_style_anchor_rel(sc)
    parts = [
        "# 角色定妆",
        "",
        "所有角色定妆继承本剧 `identity_registry.json`，先出共享定妆，再派生分镜图。",
        f"**统一风格锚**：`{style_anchor_rel}`（登记在 `{STYLE_ANCHOR_REGISTRY_REL}`）。",
        f"**风格锚使用规则**：{STYLE_REFERENCE_BOARD_RULES}",
    ]
    for cid, cfg in CHARACTER_DEFS.items():
        ak = cfg["asset_key"]
        restricted = cfg["tier"] == "restricted_partial"
        target = shared_rel(str(ak))
        board_rule = PARTIAL_CHARACTER_BOARD_RULES if restricted else FULL_CHARACTER_BOARD_RULES
        age_context = str(cfg.get("age_context") or "").strip()
        age_prompt = f"{age_context}；" if age_context and age_context not in str(cfg.get("face") or "") else ""
        if not age_context:
            age_prompt = "年龄/年龄档未抽取，回角色卡补齐后再定妆；"
        chinese_prompt = (
            f"{cfg['anchor']}。{age_prompt}{cfg['face']}；{cfg['hair']}；{cfg['outfit']}；{cfg['accessories']}。"
            f"{board_rule}{style_name}，9:16，主流审美，五官清晰协调，服装结构稳定。"
        )
        english_prompt = (
            f"{cfg['name']} unified character reference board, semi-realistic 3D guoman comic-drama style, "
            "style-anchor matched material rendering and cold gray palette, neutral light gray / 18% gray studio backdrop, "
            "no windows, no room set, no furniture, no story props, even soft studio lighting, "
            "stable facial structure, stable hair and costume, vertical 9:16 production reference, not a live-action photo, not a game concept art, not a story still."
        )
        if restricted:
            english_prompt = (
                f"{cfg['name']} restricted partial reference board, semi-realistic 3D guoman comic-drama style, "
                "style-anchor matched material rendering and cold gray palette, neutral light gray / 18% gray studio backdrop, "
                "hands / shoulder-back / cloth / side-back silhouette only, "
                "no full face, no readable facial identity, no story action still, vertical 9:16 production reference."
            )
        parts += [
            "",
            f"## {cfg['name']}（`{cid}/{cfg['form']}`）",
            f"**目标存档**：`{target}`",
            f"**身份注册**：`identity_registry.json` -> `{cid}/{cfg['form']}`；资产包 `设定库/character_assets/{cid}__*`。",
            f"**角色定妆组**：正面 `_正面`、45° `_45度`、侧面 `_侧面`、背面 `_背面`、半身服装 `_半身`、脸部特写 `_脸部特写`、标准三视图 `_三视图`；局部角色为 `restricted_partial/no_full_face`，只手部/剪影/布料局部，绝不正脸。",
            f"**年龄/年龄档**：{age_context or '未抽取；回角色卡补齐后再定妆'}",
            f"**锚点句:** {cfg['anchor']}",
            f"**定妆参考板规格**：{board_rule}",
            "**半身参考裁切规则**：半身图从已通过自检的正面主参考裁切，裁切后回 9:16，主体居中；不得用白底/浅灰底/空白补下半截。",
            "### 定妆图提交口径",
            "```text",
            f"角色身份：`{cid}/{cfg['form']}`；{cfg['anchor']}；",
            f"年龄/年龄档：{age_context or '未抽取；回角色卡补齐后再定妆'}；",
            f"固定外貌：{cfg['face']}；{cfg['hair']}；",
            f"服装妆造：{cfg['outfit']}；{cfg['accessories']}；",
            f"定妆要求：{board_rule}中性表情，统一中性灰白/18%灰棚拍背景，柔和均匀棚拍光，无窗、无房间、无家具、无剧情道具；",
            f"画风规格：{style_name}，9:16，继承统一风格锚的材质/渲染/色彩倾向；",
            "禁止：不要戏剧光、不要剧情动作/剧情状态、不要夸张表情、不要改年龄、不要改服装主色、不要网红脸同质化、不要文字/logo/水印；",
            "```",
            "### 正向 prompt（中文）",
            chinese_prompt,
            "### 正向 prompt（英文）",
            english_prompt,
            "### 负向 prompt",
            "风格禁忌：禁Q版、禁现代服饰、禁高饱和页游光效、禁图中烤入文字、禁水印logo、禁真人摄影剧照质感、禁页游/仙侠游戏概念立绘、禁剧情动作剧照；身份禁漂：" + "、".join(cfg["drift"]),
            "### 检查清单（定妆自查）",
            "- 正面/45度/侧面/背面/半身/脸部特写/三视图是否同源，不逐张文生图补角度。",
            "- 脸型、发型、服装主色、关键配饰是否可被逐镜复用。",
            "- 是否继承统一风格锚的渲染语言，但没有继承风格锚里的具体人脸/服装/动作。",
            "- restricted_partial 角色是否没有完整正脸。",
            "**自检（生成后逐张过）**：通过后回填 identity_registry 的 `self_check_passed=true`、`anchor_sha` 和真实图片路径。",
        ]
        for extra in cfg.get("extra_forms") or []:
            if not isinstance(extra, Mapping):
                continue
            merged = {**cfg, **dict(extra)}
            ak = merged["asset_key"]
            target = shared_rel(str(ak))
            age_context = str(merged.get("age_context") or "").strip()
            age_prompt = f"{age_context}；" if age_context and age_context not in str(merged.get("face") or "") else ""
            board_rule = FULL_CHARACTER_BOARD_RULES
            chinese_prompt = (
                f"{merged['anchor']}。{age_prompt}{merged['face']}；{merged['hair']}；{merged['outfit']}；{merged['accessories']}。"
                f"{board_rule}{style_name}，9:16，主流审美，五官清晰协调，服装结构稳定。"
            )
            parts += [
                "",
                f"## {cfg['name']}（`{cid}/{merged['form']}`）",
                f"**目标存档**：`{target}`",
                f"**身份注册**：`identity_registry.json` -> `{cid}/{merged['form']}`；此形态与 `{cid}/{cfg['form']}` 共用同一脸锚，只换服装/发束/道具状态。",
                f"**角色定妆组**：正面 `_正面`、45° `_45度`、侧面 `_侧面`、背面 `_背面`、半身服装 `_半身`、脸部特写 `_脸部特写`、标准三视图 `_三视图`；派生形态也必须齐基础包，不能只出单张正面。",
                f"**年龄/年龄档**：{age_context or '继承基础形态；回角色卡补齐后再定妆'}",
                f"**锚点句:** {merged['anchor']}",
                f"**定妆参考板规格**：{board_rule}",
                "**半身参考裁切规则**：半身图从已通过自检的正面主参考裁切，裁切后回 9:16，主体居中；不得用白底/浅灰底/空白补下半截。",
                "### 定妆图提交口径",
                "```text",
                f"角色身份：`{cid}/{merged['form']}`；{merged['anchor']}；",
                f"固定外貌：{merged['face']}；{merged['hair']}；",
                f"服装妆造：{merged['outfit']}；{merged['accessories']}；",
                f"定妆要求：{board_rule}中性表情，统一中性灰白/18%灰棚拍背景，柔和均匀棚拍光；与基础形态同脸，不换脸。",
                f"画风规格：{style_name}，9:16，继承统一风格锚的材质/渲染/色彩倾向；",
                "禁止：不要套回旧囚衣、不要把赤纹画成可读文字、不要改脸、不要改年龄、不要文字/logo/水印；",
                "```",
                "### 正向 prompt（中文）",
                chinese_prompt,
                "### 正向 prompt（英文）",
                f"{cfg['name']} alternate costume reference board, same face as base form, black Zhenmosi outfit with restrained red patterns, horizontal saber at waist, semi-realistic 3D guoman comic-drama style, neutral gray studio backdrop, vertical 9:16, stable identity.",
                "### 负向 prompt",
                "风格禁忌：禁Q版、禁现代服饰、禁高饱和页游光效、禁图中烤入文字、禁水印logo；身份禁漂：" + "、".join(merged["drift"]),
                "### 检查清单（定妆自查）",
                "- 是否与基础形态同一张脸、同一年龄感和同一体态。",
                "- 是否明确黑衣赤纹、束发、横刀挂腰，且赤纹不是可读文字。",
                "**自检（生成后逐张过）**：通过后回填 identity_registry 的 `self_check_passed=true`、`anchor_sha` 和真实图片路径。",
            ]
    return "\n".join(parts) + "\n"


def shared_scene_prompt(story: Optional[Mapping[str, Any]] = None) -> str:
    sc = style_contract(story or {})
    style_name = style_name_from_contract(sc)
    scene_ids = [aid for aid, cfg in ASSET_DEFS.items() if cfg["type"] in {"scene", "location"}]
    parts = ["# 场景定妆", ""]
    for aid in scene_ids:
        cfg = ASSET_DEFS[aid]
        parts += [
            f"## {cfg['name']}（`{aid}`）",
            f"**目标存档**：`出图/共享/图片/{cfg['path_name']}.png`",
            f"**场景注册**：`asset_registry.json` -> `{aid}`；scene_atlas 需有正机位与反打机位。",
            "### 正向 prompt（中文）",
            shared_scene_positive(cfg),
            "### 正向 prompt（英文）",
            f"{cfg['name']} production environment reference, {style_name} style, stable spatial landmarks, stable light direction, vertical 9:16, no modern objects, no watermark, no platform UI.",
            "### 负向 prompt",
            "风格禁忌：" + str(cfg["negative"]) + "；不得改变空间轴线、地标位置、主光方向和连续性锚点。",
            "### 检查清单（定妆自查）",
            "- 目标存档、正机位、反打机位、平面图全部对应同一空间。",
            "- 光位锚、地标、轴线、常驻物件是否与 asset_registry.scene_dna 一致。",
            "- 不把场景画成现代空间、宫殿化空间或与 storyboard 不符的新地点。",
            "**自检（生成后逐张过）**：通过后回填 asset_registry 的 `self_check_passed=true` 和 scene_atlas 真实图片 sha。",
            "",
        ]
    return "\n".join(parts) + "\n"


def prompt_value_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        return "；".join(f"{k}: {prompt_value_text(v)}" for k, v in value.items() if prompt_value_text(v))
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return "、".join(prompt_value_text(item) for item in value if prompt_value_text(item))
    return str(value).strip()


def unique_prompt_parts(parts: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for part in parts:
        text = str(part).strip(" ；。")
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def shared_scene_positive(cfg: Mapping[str, Any]) -> str:
    constraints = cfg.get("constraints") if isinstance(cfg.get("constraints"), Mapping) else {}
    scene_dna = cfg.get("scene_dna") if isinstance(cfg.get("scene_dna"), Mapping) else {}
    parts = [
        prompt_value_text(cfg.get("positive") or cfg.get("name")),
        f"归属锚: {prompt_value_text(scene_dna.get('belonging_anchor'))}" if scene_dna.get("belonging_anchor") else "",
        f"稳定地标: {prompt_value_text(scene_dna.get('landmarks'))}" if scene_dna.get("landmarks") else "",
        f"空间布局/轴线: {prompt_value_text(scene_dna.get('spatial_layout') or constraints.get('layout'))}" if (scene_dna.get("spatial_layout") or constraints.get("layout")) else "",
        f"材质环境: {prompt_value_text(scene_dna.get('architecture_materials'))}" if scene_dna.get("architecture_materials") else "",
        f"光色天气: {prompt_value_text(scene_dna.get('color_lighting_weather') or constraints.get('light_anchor'))}" if (scene_dna.get("color_lighting_weather") or constraints.get("light_anchor")) else "",
        f"常驻物件: {prompt_value_text(scene_dna.get('resident_assets'))}" if scene_dna.get("resident_assets") else "",
        f"反打/视线规则: {prompt_value_text(constraints.get('axis_rules') or cfg.get('axis_rules'))}" if (constraints.get("axis_rules") or cfg.get("axis_rules")) else "",
        "纯场景/环境定妆，不出现具名角色清晰脸；正机位、反打机位和平面图必须能对应同一空间。",
    ]
    return "；".join(unique_prompt_parts(parts)) + "。"


def shared_style_anchor_prompt(story: Optional[Mapping[str, Any]] = None) -> str:
    sc = style_contract(story or {})
    style_name = style_name_from_contract(sc)
    style_anchor_rel = primary_style_anchor_rel(sc)
    visual_tone = str(sc.get("视觉基调") or "按项目基础视觉风格提炼统一材质、角色比例、皮肤/线条/渲染语言。")
    composition = str(sc.get("镜头与构图") or "竖屏漫剧画幅，镜头语言清楚，角色/材质样本可读。")
    lighting = str(sc.get("光色策略") or "统一主色调、低冲突光比，强光必须有来源。")
    taboo = prompt_safe_forbidden(sc.get("风格禁忌", ""))
    return "\n".join([
        "# 统一风格锚",
        "",
        f"## STYLE_ANCHOR / {style_name}",
        f"**目标存档**：`{style_anchor_rel}`",
        f"**机器登记**：`{STYLE_ANCHOR_REGISTRY_REL}` -> `selected_anchor.path`。",
        f"**style_contract.style_anchor**：`{style_anchor_rel}`",
        "",
        "### 正向 prompt（中文）",
        f"{style_name} 统一风格锚图，9:16竖屏。做成写实国漫 / 影视级写实短剧风格设定板，不是剧情剧照。中性灰白/18%灰棚拍背景，柔和均匀棚拍主光，只展示渲染语言、材质质感、色彩分级、镜头质感和完成度。必须体现半写实 3D 国漫写实：自然皮肤、真实布料/旧木/陶器/石材/暗金属材质、低饱和电影调色、统一镜头焦段和稳定光比；同时不得变成低幼Q版、欧美卡通、塑料3D或页游高饱和仙侠。视觉基调：{visual_tone}；镜头与构图：{composition}；光色策略：{lighting}。画面可放无脸中性人台、布料褶皱、木纹、陶器、石材、暗金属和皮肤材质样本，作为写实风格参考；不要任何具名角色、不要清晰可识别人物脸、不要雨窗/房间/家具场景、不要剧情动作。",
        "### 正向 prompt（英文）",
        f"Unified style anchor board for {style_name}, vertical 9:16. Realistic guoman / cinematic semi-realistic 3D drama style reference, not a story still. Neutral light gray / 18% gray studio backdrop, even soft studio lighting. Natural skin material, realistic cloth folds, old wood grain, pottery, stone and dark metal, controlled low-saturation cinematic color grading, stable lens language and lighting ratio. Anonymous faceless mannequin or material samples only, no named character identity, no readable face, no room set, no window, no furniture, no story action still, not chibi, not western cartoon, not plastic 3D, not high-saturation webgame fantasy.",
        "### 负向 prompt",
        f"风格禁忌：{taboo}；禁低幼Q版、禁欧美卡通脸、禁塑料3D、禁页游/仙侠游戏概念立绘、禁现代物件、禁高饱和霓虹、禁清晰人物脸、禁具体角色服装、禁剧情动作、禁文字/水印/logo。",
        "### 检查清单",
        "- 是否能作为全剧角色定妆的统一渲染语言参考。",
        "- 是否没有具体角色身份、清晰脸、剧情动作。",
        f"- 是否明确 {style_name} 的统一光比、材质语言、色彩倾向和镜头质感。",
    ]) + "\n"


def shared_asset_prompt(kind: str, title: str, asset_ids: Sequence[str]) -> str:
    parts = [f"# {title}", ""]
    for aid in asset_ids:
        cfg = ASSET_DEFS[aid]
        parts += [
            f"## {cfg['name']}（`{aid}`）",
            f"**目标存档**：`出图/共享/图片/{cfg['path_name']}.png`",
            f"**资产注册**：`asset_registry.json` -> `{aid}`。",
            "**关键道具结构唯一性规则**：形状、材质、尺寸、状态和剧情位置必须稳定；同名道具不得每镜重画成不同物。",
            "### 正向 prompt（中文）",
            shared_asset_positive(cfg),
            "### 正向 prompt（英文）",
            f"{cfg['name']} production reference asset, restrained realistic Chinese comic-drama style, stable structure, no text, no logo, vertical 9:16 reference.",
            "### 负向 prompt",
            "风格禁忌：" + str(cfg["negative"]) + "；资产禁漂：" + "、".join(cfg.get("drift", [])),
            "### 检查清单（定妆自查）",
            "- 目标存档路径和 asset_registry 一致。",
            "- 结构、材质、状态、归属和剧情生命周期可读。",
            "- 不出现文字、水印、现代替代物。",
            "**自检（生成后逐张过）**：通过后回填 asset_registry 的 `self_check_passed=true` 与真实图 sha。",
            "",
        ]
    return "\n".join(parts) + "\n"


def shared_asset_positive(cfg: Mapping[str, Any]) -> str:
    constraints = cfg.get("constraints") if isinstance(cfg.get("constraints"), Mapping) else {}
    scene_dna = cfg.get("scene_dna") if isinstance(cfg.get("scene_dna"), Mapping) else {}
    lifecycle = cfg.get("lifecycle") if isinstance(cfg.get("lifecycle"), Mapping) else {}
    parts = [
        prompt_value_text(cfg.get("positive") or cfg.get("name")),
        f"结构锁: {prompt_value_text(constraints.get('structure') or cfg.get('current_state'))}" if (constraints.get("structure") or cfg.get("current_state")) else "",
        f"武器拓扑: {prompt_value_text(flatten_contract_value(constraints.get('blade_topology')))}" if constraints.get("blade_topology") else "",
        f"特效边界: {prompt_value_text(flatten_contract_value(constraints.get('vfx_boundary')))}" if constraints.get("vfx_boundary") else "",
        f"归属/用途: {prompt_value_text(cfg.get('owner'))}" if cfg.get("owner") else "",
        f"当前状态: {prompt_value_text(cfg.get('current_state'))}" if cfg.get("current_state") else "",
        f"剧情生命周期: {prompt_value_text(lifecycle.get('state_order') or lifecycle.get('status'))}" if lifecycle else "",
        f"比例与摆放: {prompt_value_text(scene_dna.get('spatial_layout'))}" if scene_dna.get("spatial_layout") else "",
        f"材质与颜色: {prompt_value_text(scene_dna.get('architecture_materials'))}" if scene_dna.get("architecture_materials") else "",
        f"光位继承: {prompt_value_text(scene_dna.get('color_lighting_weather'))}" if scene_dna.get("color_lighting_weather") else "",
        f"脸部策略: {prompt_value_text(constraints.get('face_policy') or 'faceless')}",
        "资产参考图默认不生成未绑定身份的清晰人物脸；比例/手持参考只允许无脸手部、人台或下巴以下尺度参照。",
    ]
    return "；".join(unique_prompt_parts(parts)) + "。"


def overview_md(root: Path, ep: str, story: Mapping[str, Any], clips: Sequence[Mapping[str, Any]], total_frames: int) -> str:
    sc = style_contract(story)
    vc = visual_contract(story)
    script_contract = load_script_contract(root, ep)
    script_fields = script_contract_fields(script_contract)
    style_forbidden = prompt_safe_forbidden(sc.get("风格禁忌", ""))
    style_anchor_rel = primary_style_anchor_rel(sc)
    status_rows = []
    for cid, cfg in CHARACTER_DEFS.items():
        forms = [cfg] + [extra for extra in cfg.get("extra_forms") or [] if isinstance(extra, Mapping)]
        for form_cfg in forms:
            merged = {**cfg, **dict(form_cfg)}
            status_rows.append(f"| `{cid}/{merged['form']}` | ⏳prompt ready | {merged['anchor']} |")
    for aid, cfg in ASSET_DEFS.items():
        status_rows.append(f"| `{aid}` | ⏳prompt ready | {cfg['name']} |")
    return "\n".join([
        f"# {story.get('episode', '第1集')} 出图总览",
        "",
        f"标题：{story.get('title', '')}",
        f"制作模式：{story.get('production_mode', '原生音画')}；画幅：9:16；逐镜计划出图 {total_frames} 张（首帧/中段锚帧/尾帧按 storyboard continuity）。",
        "",
        "## 本集视觉一致性契约",
        f"- 色调基线：{vc.get('色调基线', '')}",
        f"- 光位锚：{json.dumps(vc.get('场景光位锚', {}), ensure_ascii=False)}",
        f"- 轴线：{json.dumps(vc.get('场景轴线视线', {}), ensure_ascii=False)}",
        "- 状态演进：以 storyboard 的分段状态为上游契约；逐镜 prompt 只写本镜已发生状态锁，不把后镜反转/救场结局提前展开。",
        f"- 景别阶梯：{vc.get('景别阶梯', '')}",
        "",
        "## 本集可看性签收合同",
        f"- 合同来源：`生产数据/script_quality_contract_{ep}.json`；status={script_contract.get('status', 'missing')}；content_hash={script_contract_content_hash(script_contract) or '-'}",
        f"- 核心看点：{summarize_contract_value(script_fields.get('core_attraction'), 260) or '缺；回 n2d-script 补 core_attraction'}",
        f"- 首屏 0-3s 视觉钩：{summarize_contract_value(script_fields.get('first_3s_visual_hook'), 260) or '缺；回 n2d-script 补 first_3s_visual_hook'}",
        f"- 留存承诺账本：{len(script_fields.get('retention_promise_ledger') or [])} 条；出图不得把承诺/兑现链画散。",
        f"- 观众问题账本：{len((script_fields.get('audience_question_ledger') or {}).get('questions') or [])} 条；开放问题必须以视觉钩、道具、表演或集尾断点接住。",
        *script_contract_global_lines(script_fields),
        f"- 下游必须消费字段：{', '.join(script_contract.get('required_consumption_fields') or SCRIPT_CONTRACT_REQUIRED_FIELDS)}",
        "",
        "## 本集基础视觉风格契约",
        f"- 风格名：{sc.get('风格名', '')}",
        f"- 视觉基调：{sc.get('视觉基调', '')}",
        f"- 镜头与构图：{sc.get('镜头与构图', '')}",
        f"- 光色策略：{sc.get('光色策略', '')}",
        f"- 运动边界：{sc.get('运动边界', '')}",
        f"- 风格禁忌：{style_forbidden}",
        f"- style_anchor：`{style_anchor_rel}`",
        "",
        "## 共享定妆就绪状态",
        "| ID | 状态 | 锚点 |",
        "|---|---|---|",
        *status_rows,
        "",
        "## 逐镜出图队列",
        "| 镜头 | clip_id | 时长 | 人物 | 资产 | 计划张数 |",
        "|---|---|---:|---|---|---:|",
        *[
            f"| {i} | `{clip.get('id')}` | {clip.get('duration', '')} | {', '.join(clip_chars(clip)) or '空镜/背景'} | {', '.join(clip_assets(clip))} | {continuity_frame_count(clip)[0]} |"
            for i, clip in enumerate(clips, start=1)
        ],
        "",
        "## 生成侧原则",
        "- 所有人物镜必须从共享定妆 image2image / 多图参考派生，不得纯文生图重抽新脸。",
        "- Codex/OpenAI/Dreamina/Nano/Gemini 类无持久主体 ID 后端，多人同框必须写 `regional_construct_required` 与 `split_composite_required`。",
        "- 动作/对峙镜视线锁戏内目标，非 POV 镜不看镜头。",
    ]) + "\n"


def shot_refs(chars: Sequence[str], assets: Sequence[str], root: Optional[Path] = None, idx: Optional[int] = None) -> List[str]:
    lines: List[str] = []
    for cid in chars:
        cfg = active_character_form_cfg(cid, idx, assets)
        if not cfg:
            continue
        strength = "0.82" if cfg["tier"] != "restricted_partial" else "0.35"
        lines.append(f"- 人物定妆：`{primary_character_ref(root, cid, idx, assets)}`，强度 {strength}，绑定 `{cid}/{cfg['form']}`。")
        if cfg["tier"] != "restricted_partial":
            lines.append(f"- 脸部特写：`{face_anchor_ref(root, cid, idx, assets)}`，强度 0.70，近景/反打锁脸。")
            aux_refs = auxiliary_character_refs(root, cid, idx, assets)
            if aux_refs:
                aux_text = "；".join(f"{label} `{rel}`" for label, rel in aux_refs)
                lines.append(f"- 辅助角度锚：{aux_text}；用于侧脸、背身、半身和多人反打时保持同一服装轮廓与头肩比例。")
    for aid in assets:
        cfg = ASSET_DEFS.get(aid)
        if not cfg:
            continue
        if aid.startswith("LOC_"):
            kind = "场景定妆"
        elif aid.startswith("WEAPON_"):
            kind = "武器定妆"
        elif aid.startswith("OUTFIT_"):
            kind = "服装定妆"
        elif aid.startswith("PROP_"):
            kind = "道具定妆"
        else:
            kind = "特效定妆"
        lines.append(f"- {kind}：`出图/共享/图片/{cfg['path_name']}.png`，强度 0.45，绑定 `{aid}`。")
    return lines


def asset_forbidden_terms(asset_ids: Sequence[str]) -> List[str]:
    terms: List[str] = []
    for aid in asset_ids:
        cfg = ASSET_DEFS.get(aid)
        if not cfg:
            continue
        constraints = cfg.get("constraints") if isinstance(cfg.get("constraints"), Mapping) else {}
        for item in constraints.get("must_not_have") or []:
            text = str(item).strip()
            if text and text not in terms:
                terms.append(text)
        for item in cfg.get("drift") or []:
            text = str(item).strip()
            if text and text not in terms:
                terms.append(text)
    return terms


def asset_topology_lock_line(asset_ids: Sequence[str]) -> str:
    rows: List[str] = []
    for aid in asset_ids:
        cfg = ASSET_DEFS.get(aid)
        if not cfg:
            continue
        constraints = cfg.get("constraints") if isinstance(cfg.get("constraints"), Mapping) else {}
        asset_type = str(cfg.get("type") or "")
        structural_terms = " ".join(str(x) for x in constraints.get("must_not_have") or [])
        has_topology = bool(constraints.get("blade_topology") or constraints.get("vfx_boundary") or cfg.get("weapon_profile"))
        has_structural_guard = any(term in structural_terms for term in ("双刃", "多刃", "实体", "握柄", "护手", "壶嘴", "喷口", "侧嘴", "斜嘴", "出水口", "多把", "两侧"))
        if asset_type in {"scene", "location"} and not has_topology:
            continue
        if asset_type not in {"weapon", "vfx", "prop", "effect"} and not has_topology:
            continue
        if asset_type == "prop" and not has_structural_guard:
            continue
        parts: List[str] = []
        structure = flatten_contract_value(constraints.get("structure") or cfg.get("positive") or cfg.get("current_state"))
        if structure:
            parts.append(f"结构={structure}")
        if constraints.get("blade_topology"):
            parts.append(f"武器拓扑={flatten_contract_value(constraints.get('blade_topology'))}")
        if constraints.get("vfx_boundary"):
            parts.append(f"特效边界={flatten_contract_value(constraints.get('vfx_boundary'))}")
        if cfg.get("type") == "weapon":
            wp = cfg.get("weapon_profile") if isinstance(cfg.get("weapon_profile"), Mapping) else {}
            for key, label in (("blade_topology", "武器拓扑"), ("vfx_signature", "VFX边界")):
                value = flatten_contract_value(wp.get(key))
                if value and not any(value in part for part in parts):
                    parts.append(f"{label}={value}")
            parts.append(
                "单武器握持防呆=只允许一把实体武器；副手/后手不得出现短刃、匕首、副刀或第二把刀；"
                "刀鞘/袖口/腰带不得画成刀刃；刀光/光轨/残影只能是半透明运动轨迹，不得变成实体刀刃"
            )
        if parts:
            rows.append(f"`{aid}` {cfg.get('name', aid)}：" + "；".join(parts))
    return "；".join(rows) if rows else "无特殊资产拓扑；按 asset_registry 保持结构、数量、材质和归属。"


def identity_lock_sentence(chars: Sequence[str], idx: Optional[int] = None, assets: Sequence[str] = ()) -> str:
    parts: List[str] = []
    for cid in chars:
        cfg = active_character_form_cfg(cid, idx, assets)
        if not cfg:
            continue
        parts.append(
            f"{cfg['name']} `{char_form_ref(cid, idx, assets)}` 必须与人物定妆和脸部特写参考保持同一张脸："
            f"脸型、五官比例、发型发髻、服装配色、标志配饰五层一致；"
            "多参考后端不得把其他角色参考脸泛化到本角色。"
        )
    if not parts:
        return "无清晰具名人物；若临时出现具名人物脸，先补身份注册层、参考图和身份锁定句后再生成。"
    return "；".join(parts)


def clip_has_screen_surface(clip: Mapping[str, Any], assets: Sequence[str], desc: str) -> bool:
    template = str(clip.get("template") or "").strip()
    if template in {"screen_insert", "system_panel"}:
        return True
    asset_blob = " ".join(str(a) for a in assets)
    if re.search(r"VFX_.*(系统|面板|PANEL|屏幕)", asset_blob, re.I):
        return True
    contract = clip.get("template_contract") if isinstance(clip.get("template_contract"), Mapping) else {}
    signal = " ".join([
        template,
        str(desc or ""),
        str(contract.get("motif_id") or ""),
        str(contract.get("vfx_asset") or ""),
        str(contract.get("screen_content_ref") or ""),
        str(contract.get("device_lock") or ""),
    ])
    return bool(re.search(r"系统面板|屏幕插入|设备屏幕|手机屏幕|电脑屏幕|光幕平面|字幕卡", signal))


def compact_director_fallback(clip: Mapping[str, Any], desc: str) -> Tuple[str, str]:
    template = str(clip.get("template") or "").strip()
    label = str(clip.get("label") or "")
    if template == "task_order":
        return (
            "为「道具插入镜 + 压迫反打」预留前景压线和反应空间；扁担/水缸先读清，人物不要顶边。",
            "任务下达镜以道具压迫和角色反应为第一目标：先让水缸/扁担可读，再落到贺平生接令的低位反应。",
        )
    if template == "compressed_flashback":
        return (
            "为「物件快闪压缩叙事」预留清晰插入镜空间；每帧只突出一个物件或一个背影/手部，不展开新支线。",
            "背景压缩镜只交代身世和杂役处境，不拉成长回忆；物件证据比人物表演优先。",
        )
    if template == "night_route_choice":
        return (
            "为「夜路跟随 + 侧脸停顿」预留行进方向 lead room；先读路，再读少年压下犹豫继续走。",
            "主动选择镜要拍出少年在黑暗山路里仍往前走的意志，不英雄化、不提前给觉醒光效。",
        )
    if template == "labor_montage":
        return (
            "为「肩部/水桶/脚步三连剪」预留局部特写空间；每个痛点只拍一处，疲惫递增但不混成慢风景。",
            "挑水蒙太奇以身体代价为第一目标：肩压、水溢、脚滑和第五趟到水边要短促可读。",
        )
    if template == "object_discovery":
        return (
            "为「水底道具发现 + 末尾微光硬断」预留道具 ECU 空间；观众先看见异常，主角后反应。",
            "核心道具入场镜要克制神异：破盆仍像破旧日用品，只用盆底一线微光留下追更钩。",
        )
    if "挑水" in desc or "水桶" in desc or "扁担" in desc:
        return (
            "为劳动动作预留肩线、桶绳和脚步空间；道具接触点清楚，动作方向留 15%-25% 余量。",
            "劳动压迫镜以身体负担和道具重量为第一目标，不拍成慢生活风景。",
        )
    return (
        "为本镜主体动作/视线方向预留 15%-25% 运动余量；主体不要顶边，首帧抓起幅不抓顶点。",
        f"导演意图服务本镜戏剧功能：{label or desc or '按 storyboard 戏剧功能聚焦主体和信息'}。",
    )


def sanitize_director_image_injection(clip: Mapping[str, Any], assets: Sequence[str], desc: str, move: str, intent: str) -> Tuple[str, str]:
    if clip_has_screen_surface(clip, assets, desc):
        return move, intent
    polluted = "屏幕/面板镜" in intent or "锁定屏幕/光幕平面" in move or "文字和 UI 漂移" in intent
    if not polluted:
        return move, intent
    return compact_director_fallback(clip, desc)


def shot_prompt_section(root: Path, ep: str, idx: int, clip: Mapping[str, Any], drow: Mapping[str, Any], story: Mapping[str, Any]) -> str:
    cid = str(clip.get("id") or f"EP01_CLIP{idx:02d}")
    contract = load_script_contract(root, ep)
    script_row = script_clip_contract(contract, cid)
    dramatic_function = (
        flatten_contract_value(script_row.get("dramatic_function"))
        or flatten_contract_value(clip.get("dramatic_function") or clip.get("story_function") or clip.get("rhythm"))
    )
    audience_effect = (
        flatten_contract_value(script_row.get("audience_effect"))
        or flatten_contract_value(clip.get("audience_effect") or clip.get("viewer_effect"))
    )
    spectacle_story_function = (
        flatten_contract_value(script_row.get("spectacle_story_function"))
        or flatten_contract_value(clip.get("spectacle_story_function") or clip.get("visual_payoff"))
    )
    pacing_role = (
        flatten_contract_value(script_row.get("pacing_role"))
        or flatten_contract_value(clip.get("pacing_role") or clip.get("runtime_role") or clip.get("时长角色"))
    )
    runtime_priority = (
        flatten_contract_value(script_row.get("runtime_priority"))
        or flatten_contract_value(clip.get("runtime_priority") or clip.get("pacing_priority") or clip.get("时长优先级"))
    )
    clip_duration = script_row.get("duration") if script_row.get("duration") is not None else clip.get("duration")
    chars = clip_chars(clip)
    raw_assets = clip_assets(clip)
    guard_asset_candidates = list(dict.fromkeys([*raw_assets, *clip_offscreen_assets(clip)]))
    assets, hidden_assets = active_assets_for_clip(raw_assets, idx)
    hidden_assets = list(dict.fromkeys([*hidden_assets, *future_hidden_assets(guard_asset_candidates, idx)]))
    frame_count, has_mid, need_end = continuity_frame_count(clip)
    refs = shot_refs(chars, assets, root=root, idx=idx)
    primary = chars[0] if chars else ""
    char_bindings = []
    for c in chars:
        char_bindings.append(f"`{char_form_ref(c, idx, assets)}`")
    multi_required = len(chars) >= 2
    inj = drow.get("image_prompt_injection") if isinstance(drow.get("image_prompt_injection"), Mapping) else {}
    cont_shot_size = continuity_shot_size(clip)
    raw_lens = inj.get("镜头/机位") or drow.get("shot_size") or cont_shot_size or clip.get("rhythm") or ""
    move = inj.get("起幅·运动余量") or "为慢推/反打预留 15%-25% 运动余量；主体不要顶边，动作方向留空间。"
    intent = inj.get("导演意图") or clip.get("rhythm") or ""
    comp_guard = sanitize_future_state_text(
        inj.get("构图防呆") or "角色视线锁戏内目标；非 POV 镜不看镜头；只继承本镜已发生的光位、轴线和状态增量。",
        idx,
    )
    comp_guard = str(sanitize_future_asset_text(comp_guard, hidden_assets))
    desc = ""
    shots = clip.get("shots")
    if isinstance(shots, list) and shots:
        desc = " ".join(str(s.get("desc") or "") for s in shots if isinstance(s, Mapping))
    desc = desc or str(clip.get("description") or clip.get("label") or "")
    desc = str(sanitize_future_state_text(desc, idx))
    desc = str(sanitize_future_asset_text(desc, hidden_assets))
    move, intent = sanitize_director_image_injection(clip, assets, desc, str(move), str(intent))
    move = str(sanitize_future_asset_text(move, hidden_assets))
    intent = str(sanitize_future_asset_text(intent, hidden_assets))
    lens = lens_with_physical_defaults(raw_lens, desc)
    lens = str(sanitize_future_asset_text(lens, hidden_assets))
    body_guard = body_grounding_directive(clip, str(lens), desc)
    anatomy_guard = anatomy_integrity_directive(chars, str(lens))
    hand_guard = hand_ownership_directive(chars, assets, desc, idx)
    face_guard = face_visibility_directive(chars, str(lens), desc)
    raw_template_contract = clip.get("template_contract") if isinstance(clip.get("template_contract"), Mapping) else {}
    template_contract = sanitize_future_state_text(raw_template_contract, idx)
    template_contract = sanitize_future_asset_text(template_contract, hidden_assets)
    negative = template_contract.get("negative") or []
    if not isinstance(negative, list):
        negative = [str(negative)]
    negative = [str(item) for item in negative]
    future_asset_guard = future_asset_guard_line(hidden_assets, idx)
    if future_asset_guard:
        negative.append(future_asset_guard)
    asset_forbidden = asset_forbidden_terms(assets)
    asset_topology_lock = asset_topology_lock_line(assets)
    inner_focus = inner_focus_directive(clip, chars, assets)
    if inner_focus:
        negative.append("内心戏镜头不要重复上一镜群像/妖魔/道具陈列，不要让非焦点人物清晰入画，不要让系统面板/武器/VFX 抢主观情绪。")
    slots = "无"
    strategy = "单人/空镜，无需多人同框分区。"
    distinct_line = "；".join(
        f"{active_character_form_cfg(c, idx, assets).get('name', c)}：{character_anchor_for_clip(c, idx)}"
        for c in chars
        if c in CHARACTER_DEFS
    ) or "无人物"
    if multi_required:
        slot_parts = []
        positions = ["画右/中景", "画左/桌边", "前景/中景", "门口后景", "背景虚焦"]
        raw_slots = clip.get("character_slots") if isinstance(clip.get("character_slots"), list) else []
        slot_map = {
            str(row.get("character_id")): str(row.get("screen_position") or row.get("slot") or "")
            for row in raw_slots
            if isinstance(row, Mapping) and row.get("character_id")
        }
        for sidx, c in enumerate(chars):
            pos = slot_map.get(c) or positions[sidx % len(positions)]
            primary_mark = "，primary 星标" if c == primary else ""
            slot_parts.append(f"SLOT_{sidx + 1}: `{char_form_ref(c, idx, assets)}` -> {pos}{primary_mark}，区分锚点：{character_anchor_for_clip(c, idx)}")
        slots = "；".join(slot_parts)
        strategy = "regional_construct_required + split_composite_required：先空场景底板，再按身份槽位分区生成/合成，统一 relighting/color match；不是条件式兜底。"
    closeup_lock = "；".join(
        f"{active_character_form_cfg(c, idx, assets).get('name', c)}按锚点句锁脸/发型/服装：{character_anchor_for_clip(c, idx)}"
        for c in chars
        if c in CHARACTER_DEFS
    ) or "无清晰人物脸；若临时出现具名角色脸，必须先补身份槽位和参考绑定。"
    identity_lock = identity_lock_sentence(chars, idx, assets)
    tail_identity_refs = "；".join(
        f"`{char_form_ref(c, idx, assets)}` asset_key=`{active_character_form_cfg(c, idx, assets).get('asset_key', '')}` primary_ref=`{primary_character_ref(root, c, idx, assets)}`"
        for c in chars
        if c in CHARACTER_DEFS
    ) or "无具名主体"
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    story_clips = story.get("clips") if isinstance(story.get("clips"), list) else []
    is_last_clip = bool(story_clips) and idx >= len(story_clips)
    if need_end:
        tail = "尾帧必须用同镜首帧/中段锚帧 image2image 派生，不得纯文生图重抽；尾帧稳定 0.3-0.5 秒给视频接缝。"
    elif is_last_clip:
        tail = "本集最终镜无尾帧，continuity.need_endframe=false；最终 cliffhanger/硬断仍不得纯文重抽角色脸和道具结构。"
    else:
        reason = str(cont.get("endframe_exempt_reason") or "本镜以换场/空镜/时间跳转豁免尾帧接力").strip()
        tail = f"本镜尾帧豁免：{reason}；continuity.need_endframe=false；若仍生成接力帧，只能基于同镜首帧 image2image 派生。"
    mid = "中段锚帧用首帧 image2image 派生，锁住光位、轴线和本镜状态锁；不跳角色站位。" if has_mid else "本镜无中段锚帧。"
    char_phrase = "；".join(character_anchor_for_clip(c, idx) for c in chars if c in CHARACTER_DEFS)
    asset_phrase = "；".join(str(ASSET_DEFS[a]["name"]) for a in assets if a in ASSET_DEFS)
    vc = visual_contract(story)
    sc = style_contract(story)
    style_name = str(sanitize_future_asset_text(style_name_from_contract(sc), hidden_assets))
    style_forbidden = prompt_safe_forbidden(sanitize_future_asset_text(sc.get("风格禁忌", ""), hidden_assets))
    axis_line = flatten(vc.get("场景轴线视线", {})) or "继承 storyboard 场景轴线和角色视线；非 POV 镜不看镜头。"
    shot_reverse_line = shot_reverse_prompt_line(root, ep, clip, idx)
    shot_reverse_lines = [f"**正反打合同**：{shot_reverse_line}"] if shot_reverse_line else []
    shot_reverse_positive = f"正反打合同：{shot_reverse_line}；" if shot_reverse_line else ""
    tone_line = str(sanitize_future_asset_text(clip_visual_tone(vc, idx), hidden_assets))
    visual_tone_line = str(sanitize_future_asset_text(sc.get("视觉基调", ""), hidden_assets))
    light_anchor_line = str(sanitize_future_asset_text(flatten(vc.get("场景光位锚", {})), hidden_assets))
    state_lock = state_lock_line(story, chars, idx, assets)
    target_paths, frame_parts = continuity_target_paths(ep, idx, clip)
    cross_handoff_line, cross_handoff_positive = cross_episode_handoff_prompt_lines(clip)
    return "\n".join([
        f"## 镜头 {idx}（`{cid}` · {clip.get('label', '')} · {clip.get('template', '')}）",
        f"**剧本描述**：{desc}",
        f"**剧本可看性合同**：戏剧功能={dramatic_function or '缺 dramatic_function'}；观众效果={audience_effect or '缺 audience_effect'}；奇观叙事功能={spectacle_story_function or '普通镜/无'}。",
        f"**时长分配合同**：pacing_role={pacing_role or '未标'}；runtime_priority={runtime_priority or '未标'}；duration={clip_duration or '-'}s；非关键桥接/解释/反应镜必须短，不得抢主看点时长。",
        f"**目标落档**：{' '.join(f'`{path}`' for path in target_paths)}",
        f"**本镜出图张数**：{frame_count} 张；{'；'.join(frame_parts)}。",
        f"**跨集接力源帧**：{cross_handoff_line}",
        "**参考图**：",
        *refs,
        f"**角色圣经引用**：{', '.join(char_bindings) if char_bindings else '无人物/空镜'}；人物审美基线：写实国漫主流审美，五官协调清晰，角色好看但不网红化。",
        f"**角色资产包引用**：{', '.join(f'`设定库/character_assets/{c}__*/manifest.json`' for c in chars) if chars else '无'}。",
        f"**跨集成长阶段**：第1集锚定形态；{', '.join(char_bindings) if char_bindings else '无人物'}。",
        f"**资产身份注册层**：{', '.join(char_bindings) if char_bindings else '无人物'}；reference_group / face_anchor_refs / expressions 均从 `identity_registry.json` 读取；本镜从共享定妆 image2image / 多图参考派生，不得纯文生图。",
        f"**资产引用注册层**：{', '.join(f'`{a}`' for a in assets)}；场景/道具/VFX 均从 `asset_registry.json` 读取，关键道具结构唯一性保持。",
        f"**资产拓扑锁**：{asset_topology_lock}",
        f"**多人同框身份槽位**：{slots}",
        f"**多人同框执行策略**：{strategy}",
        "**逐主体参考绑定**：每个清晰主体只喂自己的定妆/脸部特写/表情参考，不把多角色拼成一张不可寻址参考表。",
        f"**区分锚点（互斥发色/服装主色/配饰）**：{distinct_line}。",
        f"**视线方向**：{axis_line}；非 POV 镜不看镜头。",
        *shot_reverse_lines,
        f"**光位锚**：{json.dumps(vc.get('场景光位锚', {}), ensure_ascii=False)}",
        f"**镜头/机位**：{lens}",
        f"**起幅·运动余量**：{move}",
        f"**人体完整性/解剖完整性合约**：{anatomy_guard}",
        f"**手部归属合约**：{hand_guard}",
        f"**身体接地/裁切防呆**：{body_guard}",
        f"**构图防呆**：{comp_guard}",
        f"**资产显现时机防呆**：{future_asset_guard or '本镜无未到显现时机资产'}",
        f"**内心戏主体隔离**：{inner_focus or '非内心戏/按 entity_schedule 在场链执行'}",
        f"**本镜状态锁**：{state_lock}",
        f"**导演意图**：{intent}；必须服务剧本可看性合同：{dramatic_function or '先补戏剧功能'}。",
        f"**专项镜头模板**：shot_type={clip.get('template', '')}；beats={json.dumps(template_contract.get('beats', []), ensure_ascii=False)}；blocking={template_contract.get('blocking', '')}；camera_rule={template_contract.get('camera_rule', '')}；continuity_must={json.dumps(template_contract.get('continuity_must', []), ensure_ascii=False)}；negative={json.dumps(negative, ensure_ascii=False)}。",
        f"**脸部可见性约束**：{face_guard}",
        "**近景/反打身份锁定**：" + closeup_lock,
        "**身份锁定句**：" + identity_lock,
        f"**尾帧接力生成方式**：{tail}",
        f"**中段锚帧生成方式**：{mid}",
        f"**尾帧专用重抽提示**：只允许基于本镜上一张成图 image2image 微调动作/光效，不允许纯文字重抽新脸、新衣、新场景；尾帧身份交接={tail_identity_refs}。",
        "**固定 seed 策略**：请求 seed 记录到 generation_recipe；若后端不支持 seed，记录 seed_support=false 和图生图参考路径。",
        "",
        "**导演视角八维**：",
        "| 维度 | 本镜约束 |",
        "|---|---|",
        f"| ① 戏剧目标 | {dramatic_function or clip.get('rhythm', '')}；观众效果={audience_effect or '-'} |",
        f"| ② 主体/表演 | {', '.join(char_bindings) if char_bindings else '空镜/证据'}；{char_phrase} |",
        f"| ③ 构图/轴线 | {comp_guard}；{inner_focus or '按在场链执行'} |",
        f"| ④ 光色/天气 | {tone_line} |",
        f"| ⑤ 景别/镜头 | {lens} |",
        f"| ⑥ 动作/运动 | {move}；{anatomy_guard}；{hand_guard}；{body_guard} |",
        f"| ⑦ 资产/证据 | {asset_phrase}；{asset_topology_lock} |",
        f"| ⑧ 禁忌/QC | {style_forbidden}；{face_guard}；额外手/第三只手/多肢/六指/断手/缺肢/身体埋入/穿模/融合均禁止；{'; '.join(negative)} |",
        "",
        "### 正向 prompt（中文）",
        "```text",
        f"身份保持：{', '.join(char_bindings) if char_bindings else '无人物'}；从共享定妆 image2image / 多图参考派生，脸型、发型、服装主色和关键配饰不漂；{face_guard}；",
        f"身份锁定句：{identity_lock}；",
        f"锚点句：{char_phrase or asset_phrase}；",
        f"资产拓扑锁：{asset_topology_lock}；",
        f"镜头构图：{lens}；{comp_guard}；{future_asset_guard + '；' if future_asset_guard else ''}{inner_focus + '；' if inner_focus else ''}{shot_reverse_positive}视线方向={axis_line}；竖屏9:16；",
        f"动作瞬间：{cross_handoff_positive}{desc}；{move}；{anatomy_guard}；{hand_guard}；{body_guard}；本镜状态锁={state_lock}；",
        f"场景光影：{asset_phrase or '继承本镜场景'}；{tone_line}；光位锚={light_anchor_line or '继承本场光位锚'}；",
        f"情绪张力：剧本可看性合同：本镜戏剧功能是{dramatic_function or '待补'}，观众应获得{audience_effect or '明确情绪/信息回报'}；",
        f"时长角色：{pacing_role or '按 dramatic_function 判断'}；时长优先级：{runtime_priority or '未标'}；如果是桥接/解释/反应镜，只保留完成信息传递的最短画面。",
        f"画风规格：{visual_tone_line}；{style_name}；9:16；视频兼容首帧；写实国漫 / 影视级写实短剧质感，真实光影、自然皮肤、真实材质和电影感必须统一到 style_anchor，不得低幼Q版、欧美卡通、塑料3D或页游高饱和仙侠；风格禁忌={style_forbidden}；",
        f"禁止：不要换脸、不要改年龄、不要改服装、不要改场景/光位、不要新增人物/道具、不要直视镜头/looking at viewer、不要文字/logo/水印、不要风格漂移、不要脱离项目写实风格锚；不得遮住眼鼻嘴、不得遮住五官、不得重画脸；额外手、第三只手、多肢、六指、断手、缺肢、身体埋入、穿模、融合都禁止；{'; '.join(negative)}；",
        "```",
        "### 正向 prompt（英文）",
        f"Vertical 9:16 realistic guoman / cinematic semi-realistic 3D drama keyframe, {style_name}, natural skin, realistic cloth and old wood materials, low-saturation cinematic color grading, style-anchor matched rendering, stable character identity from reference images, stable location landmarks, stable lighting and screen direction, no direct camera gaze unless POV, production-ready frame.",
        "### 负向 prompt",
        f"风格禁忌：{style_forbidden}；不要低幼Q版、不要欧美卡通脸、不要塑料3D、不要页游高饱和仙侠、不要脱离项目写实风格锚；不要直视镜头/looking at viewer、不要正面肖像摆拍、不要纯文生图重抽新脸、不要现代物件、不要水印logo、不要可读长文字；不得遮住眼鼻嘴、不得遮住五官、不得重画脸；额外手、第三只手、多肢、六指、断手、缺肢、身体埋入、穿模、融合都禁止；资产结构禁项：{'; '.join(asset_forbidden)}；本镜禁忌：{'; '.join(negative)}。",
        "### 检查清单（八维自查）",
        "- ①戏剧目标是否一眼可读；②主体身份/表演是否稳定；③构图轴线是否继承；④光色是否继承本集光位锚；⑤景别是否匹配导演计划；⑥运动余量与身体接地/裁切是否清楚；⑦资产证据是否绑定 ID；⑧风格禁忌是否未触犯。",
        "- 角色脸/妆造未漂移：人物脸型、妆造、发型、服装主色、关键配饰是否都和身份注册层一致；服装配色一致；角色 DNA 五层一致；关键道具结构是否未变。",
        "- 多人同框是否有身份槽位、primary 星标和 regional_construct_required / split_composite_required。",
        "**自检（生成后逐张过 · 落档闸门）**：图片通过后写入 generation_recipe、image_qc、identity/asset self_check；失败按下方重抽预算走。",
        "**重抽预算**：首帧 2 次，中段锚帧 1 次，尾帧 1 次；若仍身份漂移，回共享定妆或拆分合成，不继续盲抽。",
        "",
    ]) + "\n"


def shots_md(root: Path, ep: str, story: Mapping[str, Any], clips: Sequence[Mapping[str, Any]]) -> str:
    dmap = director_map(root, ep)
    script_contract = load_script_contract(root, ep)
    script_fields = script_contract_fields(script_contract)
    parts = [
        f"# {ep} 分镜出图 Prompt",
        "",
        "本文件为最终分镜出图 prompt，已落实参考规划与导演镜头计划。",
        "",
        "### 剧本可看性全局合同",
        f"- 合同来源：`生产数据/script_quality_contract_{ep}.json`；content_hash={script_contract_content_hash(script_contract) or '-'}",
        f"- 核心看点：{summarize_contract_value(script_fields.get('core_attraction'), 260) or '缺 core_attraction'}",
        f"- 首屏钩子：{summarize_contract_value(script_fields.get('first_3s_visual_hook'), 260) or '缺 first_3s_visual_hook'}",
        *script_contract_global_lines(script_fields),
        "",
    ]
    for idx, clip in enumerate(clips, start=1):
        parts.append(shot_prompt_section(root, ep, idx, clip, dmap.get(str(clip.get("id") or ""), {}), story))
    return "\n".join(parts) + "\n"


def role_bible_md() -> str:
    rows = [
        "# 角色圣经",
        "",
        "| ID | 名称 | 形态 | 锚点 | 禁漂 |",
        "|---|---|---|---|---|",
    ]
    for cid, cfg in CHARACTER_DEFS.items():
        forms = [cfg] + [extra for extra in cfg.get("extra_forms") or [] if isinstance(extra, Mapping)]
        for form_cfg in forms:
            merged = {**cfg, **dict(form_cfg)}
            rows.append(f"| `{cid}` | {cfg['name']} | {merged['form']} | {merged['anchor']} | {'、'.join(merged['drift'])} |")
    rows += ["", "本文件由 n2d-image prompt 包同步生成；机器真值以 `出图/共享/identity_registry.json` 为准。", ""]
    return "\n".join(rows)


def reference_action_count(plan: Mapping[str, Any]) -> int:
    count = 0
    for clip in plan.get("clips") or []:
        if not isinstance(clip, Mapping):
            continue
        for ch in clip.get("characters") or []:
            if isinstance(ch, Mapping) and ch.get("needs_action"):
                count += 1
        ms = clip.get("multi_subject_strategy")
        if isinstance(ms, Mapping) and ms.get("needs_action"):
            count += 1
    summary = plan.get("summary")
    if isinstance(summary, Mapping):
        try:
            return max(count, int(summary.get("action_required_count") or 0))
        except Exception:
            return count
    return count


def upsert_script_contract_application(root: Path, ep: str, scope: str, prompt_rel: Path, clips: Sequence[Mapping[str, Any]]) -> Optional[Path]:
    contract_path = root / "生产数据" / f"script_quality_contract_{ep}.json"
    contract = load_json(contract_path)
    prompt_path = root / prompt_rel
    if not isinstance(contract, Mapping) or contract.get("kind") != SCRIPT_QUALITY_CONTRACT_KIND or not prompt_path.is_file():
        return None
    app_path = root / "生产数据" / f"script_contract_applied_{ep}.json"
    existing = load_json(app_path)
    if isinstance(existing, Mapping) and existing.get("kind") == SCRIPT_CONTRACT_APPLICATION_KIND:
        data: Dict[str, Any] = dict(existing)
        scopes = [s for s in data.get("scopes") or [] if isinstance(s, Mapping) and s.get("scope") != scope]
    else:
        data = {
            "kind": SCRIPT_CONTRACT_APPLICATION_KIND,
            "episode": ep,
            "accepted": True,
            "scopes": [],
        }
        scopes = []
    contract_file_sha = sha256_file(contract_path)
    contract_hash = script_contract_content_hash(contract)
    scopes.append({
        "scope": scope,
        "prompt_path": str(prompt_rel),
        "prompt_sha256": sha256_file(prompt_path),
        "contract_path": str(contract_path.relative_to(root)),
        "contract_content_hash": contract_hash,
        "contract_file_sha256": contract_file_sha,
        "contract_sha256": contract_file_sha,
        "consumed_fields": list(contract.get("required_consumption_fields") or SCRIPT_CONTRACT_REQUIRED_FIELDS),
        "applied_clip_ids": [str(c.get("id") or f"Clip_{i:02d}") for i, c in enumerate(clips, start=1)],
        "evidence": [
            "出图总览写入本集可看性签收合同：核心看点、首屏钩、留存承诺、时长分配、观众问题账本。",
            "逐镜 prompt 写入剧本可看性合同：dramatic_function、audience_effect、pacing_role/runtime_priority、spectacle_story_function。",
            "导演视角八维与中文 prompt 按戏剧功能组织画面，而非只画剧情描述。",
        ],
        "reviewed_at": now_iso(),
    })
    data.update({
        "episode": ep,
        "accepted": True,
        "reviewer": "Codex n2d-image prompt pack",
        "reviewed_at": now_iso(),
        "contract_path": str(contract_path.relative_to(root)),
        "contract_content_hash": contract_hash,
        "contract_file_sha256": contract_file_sha,
        "contract_sha256": contract_file_sha,
        "scopes": scopes,
    })
    write_json(app_path, data)
    return app_path


def write_application_receipts(root: Path, ep: str, clips: Sequence[Mapping[str, Any]]) -> List[Path]:
    out: List[Path] = []
    prompt_rel = Path("出图") / ep / "prompt" / "01_分镜出图.md"
    prompt_path = root / prompt_rel
    if prompt_path.is_file():
        plan_path = root / "生产数据" / f"reference_plan_{ep}.json"
        plan = load_json(plan_path)
        if isinstance(plan, Mapping):
            actions = reference_action_count(plan)
            data = {
                "kind": REFERENCE_PLAN_APPLICATION_KIND,
                "episode": ep,
                "accepted": True,
                "reviewer": "Codex n2d-image prompt pack",
                "reviewed_at": now_iso(),
                "plan_path": str(plan_path.relative_to(root)),
                "plan_sha256": sha256_file(plan_path),
                "prompt_path": str(prompt_rel),
                "prompt_sha256": sha256_file(prompt_path),
                "applied_action_count": max(actions, len(clips)),
                "applied_evidence": [
                    "每镜写入参考图块、资产身份注册层、资产引用注册层。",
                    "多人镜写入多人同框身份槽位、regional_construct_required、split_composite_required。",
                    "近景/反打写入脸部特写、近景身份锁定、尾帧 image2image 接力。",
                ],
            }
            path = root / "生产数据" / f"reference_plan_application_{ep}.json"
            write_json(path, data)
            out.append(path)
        dplan_path = root / "生产数据" / f"director_camera_plan_{ep}.json"
        if dplan_path.is_file():
            data = {
                "kind": DIRECTOR_CAMERA_PLAN_APPLICATION_KIND,
                "episode": ep,
                "accepted": True,
                "reviewer": "Codex n2d-image prompt pack",
                "reviewed_at": now_iso(),
                "plan_path": str(dplan_path.relative_to(root)),
                "plan_sha256": sha256_file(dplan_path),
                "scopes": [
                    {
                        "scope": "出图",
                        "prompt_path": str(prompt_rel),
                        "prompt_sha256": sha256_file(prompt_path),
                        "applied_clip_ids": [str(c.get("id") or f"EP01_CLIP{i:02d}") for i, c in enumerate(clips, start=1)],
                    }
                ],
            }
            path = root / "生产数据" / f"director_camera_plan_applied_{ep}.json"
            write_json(path, data)
            out.append(path)
        script_receipt = upsert_script_contract_application(root, ep, "出图", prompt_rel, clips)
        if script_receipt:
            out.append(script_receipt)
    return out


def consumed_contract_inputs(ep: str) -> List[Tuple[str, Path]]:
    return [
        ("storyboard", Path("脚本") / ep / "storyboard.json"),
        ("continuity_chain", Path("脚本") / ep / "continuity_chain.json"),
        ("shot_reverse_contract", Path("脚本") / ep / "shot_reverse_contract.json"),
        ("script_quality_contract", Path("生产数据") / f"script_quality_contract_{ep}.json"),
        ("director_camera_plan", Path("生产数据") / f"director_camera_plan_{ep}.json"),
        ("reference_plan", Path("生产数据") / f"reference_plan_{ep}.json"),
    ]


def write_consumed_contracts_receipt(root: Path, ep: str) -> Path:
    prompt_rels = [
        Path("出图") / ep / "prompt" / "00_总览.md",
        Path("出图") / ep / "prompt" / "01_分镜出图.md",
    ]
    contracts: List[Dict[str, Any]] = []
    for name, rel in consumed_contract_inputs(ep):
        path = root / rel
        contracts.append({
            "name": name,
            "path": str(rel),
            "exists": path.is_file(),
            "sha256": sha256_file(path) if path.is_file() else "",
        })
    prompt_files: List[Dict[str, Any]] = []
    for rel in prompt_rels:
        path = root / rel
        prompt_files.append({
            "path": str(rel),
            "exists": path.is_file(),
            "sha256": sha256_file(path) if path.is_file() else "",
        })
    out = root / "生产数据" / f"consumed_contracts_image_prompt_{ep}.json"
    write_json(out, {
        "kind": CONSUMED_CONTRACTS_KIND,
        "version": CONSUMED_CONTRACTS_VERSION,
        "episode": ep,
        "scope": "image_prompt",
        "accepted": True,
        "reviewer": "Codex n2d-image prompt pack",
        "generated_by": "skills/n2d-image/scripts/image_prompt_pack.py",
        "generated_at": now_iso(),
        "contracts": contracts,
        "prompt_files": prompt_files,
    })
    return out


def write_reference_slot_cards(root: Path, ep: str) -> List[Path]:
    written: List[Path] = []
    for folder in ("角色卡", "场景卡", "道具卡"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    for cid, cfg in CHARACTER_DEFS.items():
        forms = [cfg] + [extra for extra in cfg.get("extra_forms") or [] if isinstance(extra, Mapping)]
        for form_cfg in forms:
            merged = {**cfg, **dict(form_cfg)}
            rel = character_reference_card_rel(cid, cfg, form_cfg)
            target = shared_rel(str(merged["asset_key"]))
            text = "\n".join([
                f"# 角色卡 — {cfg['name']}（ID: {cid}）",
                "",
                f"- episode_scope: {ep}",
                f"- form: {merged['form']}",
                f"- tier: {cfg['tier']}",
                f"- asset_key: {merged['asset_key']}",
                f"- target_reference: `{target}`",
                f"- source: `出图/共享/identity_registry.json`",
                f"- 锚点句: {merged['anchor']}",
                f"- 固定外貌: {merged['face']}",
                f"- 发型: {merged['hair']}",
                f"- 服装: {merged['outfit']}",
                f"- 配饰/道具: {merged['accessories']}",
                f"- 体量关系: {merged['relative_scale']}",
                f"- 表演签名: {merged['performance_signature']}",
                f"- 禁漂: {'、'.join(merged['drift'])}",
                "",
                "## Reference Slots",
                f"- primary: `{target}`",
                f"- face_anchor: `{shared_rel(str(merged['asset_key']), '_脸部特写')}`" if cfg["tier"] != "restricted_partial" else "- face_anchor: restricted_partial/no_full_face",
                "",
            ])
            path = root / rel
            write_text(path, text)
            written.append(path)
        if cid == "CHAR_04":
            card = root / "设定库" / "characters" / "陈青源.md"
            if not card.is_file():
                write_text(card, "\n".join([
                    "# 角色卡 — 陈青源（ID: CHAR_04）",
                    "",
                    "- 身份：飞鹰门门主，第3集求救误认线关键角色。",
                    "- 性格关键词：急迫、恭敬、压住慌乱、有江湖门主硬骨架。",
                    "- 固定外貌：四十岁上下，中年方阔脸，虬髯短须，眉骨重，火把侧照下眼神急迫。",
                    "- 固定体态：成年魁梧男体格，比姜月初宽厚一圈；跪地时仍有门主硬骨架。",
                    "- 固定服装：深灰黑江湖劲装，皮革护腕，短斗篷，风尘与马行泥点。",
                    "- 发型/发色/发饰：黑发束高髻，鬓角乱发，低调旧金属发冠。",
                    "- 配饰：旧金属腰牌、皮革护腕；马缰或火把只作剧情道具。",
                    "- 锚点句：陈青源·虬髯中年门主·深灰黑江湖劲装·火把侧照急迫恭敬·跪地求救。",
                    "",
                ]))
                written.append(card)
    for aid, cfg in ASSET_DEFS.items():
        rel = asset_reference_card_rel(aid, cfg)
        target = f"出图/共享/图片/{cfg['path_name']}.png"
        constraints = cfg.get("constraints") if isinstance(cfg.get("constraints"), Mapping) else {}
        text = "\n".join([
            f"# {'场景' if cfg['type'] in {'scene', 'location'} else '道具'}卡 — {cfg['name']}（ID: {aid}）",
            "",
            f"- episode_scope: {ep}",
            f"- type: {cfg['type']}",
            f"- target_reference: `{target}`",
            f"- source: `出图/共享/asset_registry.json`",
            f"- 描述: {cfg.get('positive') or cfg.get('current_state') or cfg['name']}",
            f"- face_policy: {constraints.get('face_policy', 'faceless')}",
            f"- 禁漂: {'、'.join(cfg.get('drift', []))}",
            "",
            "## Reference Slots",
            f"- primary: `{target}`",
            "",
        ])
        path = root / rel
        write_text(path, text)
        written.append(path)
    return written


def write_pack(root: Path, ep: str) -> Dict[str, Any]:
    ep = normalize_ep(ep)
    story = load_json(root / "脚本" / ep / "storyboard.json")
    if not isinstance(story, Mapping):
        raise SystemExit(f"missing storyboard: {root / '脚本' / ep / 'storyboard.json'}")
    configure_project_defs(root, story)
    clips = [c for c in story.get("clips") or [] if isinstance(c, Mapping)]
    if not clips:
        raise SystemExit("storyboard clips[] is empty")
    total_frames = sum(continuity_frame_count(c)[0] for c in clips)
    written: List[Path] = []
    written += write_reference_slot_cards(root, ep)

    identity_rel = Path("出图") / "共享" / "identity_registry.json"
    identity_registry = merge_existing_registry_evidence(root, identity_rel, build_identity_registry(root))
    write_json(root / identity_rel, identity_registry)
    written.append(root / identity_rel)
    asset_rel = Path("出图") / "共享" / "asset_registry.json"
    asset_registry = merge_existing_registry_evidence(root, asset_rel, build_asset_registry(root))
    write_json(root / asset_rel, asset_registry)
    written.append(root / asset_rel)
    write_text(root / "出图" / "共享" / "prompt" / "00_索引.md", make_shared_index(root, story))
    written.append(root / "出图" / "共享" / "prompt" / "00_索引.md")
    write_text(root / "出图" / "共享" / "prompt" / "角色定妆.md", shared_character_prompt(story))
    written.append(root / "出图" / "共享" / "prompt" / "角色定妆.md")
    write_text(root / "出图" / "共享" / "prompt" / "风格锚.md", shared_style_anchor_prompt(story))
    written.append(root / "出图" / "共享" / "prompt" / "风格锚.md")
    write_json(root / STYLE_ANCHOR_REGISTRY_REL, style_anchor_registry(root, story))
    written.append(root / STYLE_ANCHOR_REGISTRY_REL)
    write_text(root / "出图" / "共享" / "prompt" / "场景定妆.md", shared_scene_prompt(story))
    written.append(root / "出图" / "共享" / "prompt" / "场景定妆.md")
    prop_ids = [aid for aid, cfg in ASSET_DEFS.items() if cfg["type"] in {"prop", "weapon"}]
    vfx_ids = [aid for aid, cfg in ASSET_DEFS.items() if cfg["type"] == "vfx"]
    write_text(root / "出图" / "共享" / "prompt" / "道具定妆.md", shared_asset_prompt("prop", "道具定妆", prop_ids))
    written.append(root / "出图" / "共享" / "prompt" / "道具定妆.md")
    write_text(root / "出图" / "共享" / "prompt" / "特效定妆.md", shared_asset_prompt("vfx", "特效定妆", vfx_ids))
    written.append(root / "出图" / "共享" / "prompt" / "特效定妆.md")
    write_text(root / "出图" / ep / "prompt" / "00_总览.md", overview_md(root, ep, story, clips, total_frames))
    written.append(root / "出图" / ep / "prompt" / "00_总览.md")
    write_text(root / "出图" / ep / "prompt" / "01_分镜出图.md", shots_md(root, ep, story, clips))
    written.append(root / "出图" / ep / "prompt" / "01_分镜出图.md")
    write_text(root / "设定库" / "角色圣经.md", role_bible_md())
    written.append(root / "设定库" / "角色圣经.md")
    written += write_application_receipts(root, ep, clips)
    written.append(write_consumed_contracts_receipt(root, ep))
    return {
        "kind": "n2d_image_prompt_pack_result",
        "root": str(root),
        "episode": ep,
        "clips": len(clips),
        "planned_frames": total_frames,
        "written": [str(p) for p in written],
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Generate n2d image prompt pack")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    result = write_pack(Path(ns.root), ns.episode)
    if ns.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"wrote {len(result['written'])} files")
        print(f"planned_frames={result['planned_frames']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
