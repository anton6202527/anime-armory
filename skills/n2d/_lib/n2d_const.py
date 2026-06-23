#!/usr/bin/env python3
"""Shared constants for the n2d pipeline."""

from __future__ import annotations

# ── identity_registry 共享字段 ──────────────────────────────────────────────
# reference_group 的标准参考视图键
IDENTITY_REFERENCE_KEYS = ("front", "side", "back", "outfit", "turnaround")

# identity_adapter 是否携带"已注册句柄"的字段（任一非空即视为已登记）
IDENTITY_HANDLE_FIELDS = ("id", "handle", "reference", "model_path")

# identity_adapters.<backend>.status 的标准状态集合
IDENTITY_ADAPTER_KNOWN_STATUSES = (
    "unregistered", "fallback_reference_group", "registered", "pending", "training",
    "ready", "error", "deprecated", "unsupported", "not_needed",
)
IDENTITY_ADAPTER_READY_STATUSES = ("registered", "ready")
IDENTITY_ADAPTER_FALLBACK_STATUSES = ("unregistered", "fallback_reference_group", "fallback", "reference_group")
IDENTITY_ADAPTER_PASSIVE_STATUSES = ("unsupported", "not_needed")
IDENTITY_ADAPTER_IN_PROGRESS_STATUSES = ("pending", "training")

# ── compliance / gate 共享状态集合 ────────────────────────────────────────────
COMPLIANCE_ALLOWED_RIGHTS = ("original", "public_domain", "licensed", "stock_licensed", "user_declared", "not_applicable", "unknown", "")
COMPLIANCE_RIGHTS_EVIDENCE_REQUIRED = ("licensed", "stock_licensed", "user_declared")
COMPLIANCE_APPROVED_CHARACTER = ("actor_authorized", "self_authorized", "licensed_likeness", "ai_generated_original", "synthetic_character", "not_applicable")
COMPLIANCE_BLOCKED_CHARACTER = ("unauthorized", "disputed")
COMPLIANCE_SAFE_VOICE = ("authorized_clone", "stock_voice", "human_recording", "synthetic_voice", "not_applicable")
COMPLIANCE_READY_STATUSES = ("ready", "done", "not_applicable")
COMPLIANCE_DONE_STATUSES = ("ready", "done", "approved", "not_applicable")
COMPLIANCE_PLATFORM_REVIEW_STATUSES = ("ready", "done", "not_applicable")
COMPLIANCE_PRE_BROADCAST_STATUSES = ("pending", "ready", "filed", "approved", "done", "not_applicable")
COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS = ("internal_only", "demo", "test")
COMPLIANCE_PLACEHOLDER_MARKERS = ("todo", "待补", "待办", "xxx", "xxx", "...", "n/a?")
COMPLIANCE_OVERSEAS_PLATFORMS = ("tiktok", "youtube", "reelshort", "instagram", "facebook")
COMPLIANCE_DOMESTIC_REGIONS = ("cn", "china", "mainland", "中国", "中国大陆", "内地")
COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS = ("platform_review", "localization", "regulatory_filing")
# AI 生成合成内容标识：n2d 只保留非阻断 manifest / best-effort 后处理 / 发布待办提示。
# 显式标签、元数据隐式标识、数字水印和平台披露不得成为主流程 blocker。
COMPLIANCE_AI_LABEL_STATUSES = ("pending", "done", "not_applicable")
COMPLIANCE_AI_LABEL_DEFAULT_TEXT = "AI生成"
COMPLIANCE_AI_LABEL_SPEC = "GB45438-2025"
# AI 标识字段仅供 INFO 提醒和发布检查参考，不参与主流程放行。
COMPLIANCE_STATUS_LIKE_VALUES = (
    "pending", "ready", "done", "not_applicable", "filed", "approved",
    "blocked", "missing", "unknown", "todo",
)

# ── 重抽原因分类 ────────────────────────────────────────────────────────────
REDRAW_REASON_ENUM = ("identity_drift", "composition", "action_quality", "glitch", "prompt_adjustment", "other")
# 重抽原因九类维度（单一真值源）。键名与消费端对齐：dashboard render 的「一致性小计」按
# (face_consistency/outfit_consistency/scene_drift/style_drift) 求和，n2d-score / SKILL.md 同此命名。
# 2026-06-15：const 曾漂成另一套键(identity_drift/composition/glitch…)与 render+test+doc 全部脱节，
# 致「一致性小计」恒为 0、文本归类落不进消费维度；此处恢复为文档化的九类。
REDRAW_REASON_CATEGORIES = {
    "face_consistency": "脸漂/身份",
    "outfit_consistency": "服装/配色",
    "scene_drift": "场景/光位",
    "style_drift": "画风",
    "prop_structure": "道具/特效",
    "reference_crop": "参考图裁切",
    "prompt_conflict": "prompt 冲突",
    "temporal": "时序/接缝",
    "other": "其他",
}
# 自由文本 → 维度：按序首个命中即归类（顺序即优先级），无命中落 other。
# 顺序上 prop_structure 放在 scene_drift 前——"道具/法宝结构"含"结构"易被场景类误吞。
REDRAW_REASON_KEYWORDS = (
    ("face_consistency", ("崩脸", "不像", "脸飘", "脸漂", "人不对", "换脸", "身份", "identity", "face")),
    ("outfit_consistency", ("衣服", "服装", "配色", "妆造", "outfit")),
    ("prop_structure", ("道具", "法宝", "结构", "件数", "特效", "prop")),
    ("scene_drift", ("场景", "光位", "背景", "环境", "scene")),
    ("style_drift", ("画风", "风格", "style")),
    ("temporal", ("接缝", "时序", "闪烁", "跳切", "flicker", "seam", "temporal")),
    ("reference_crop", ("参考图", "裁切", "crop")),
    ("prompt_conflict", ("prompt 冲突", "提示词冲突", "词冲突", "prompt conflict")),
)

# ── 音色一致性契约 ──────────────────────────────────────────────────────────
VOICE_KEY_FIELD = "voice_key"
VOICE_KEY_LEGACY_FIELD = "音色键"
VOICE_KEY_PLACEHOLDER_SUFFIX = "_placeholder"
EMOTION_FLOW_FIELD = "emotion_flow"

# ── 制作模式 ──────────────────────────────────────────────────────────────
# 2026-06-16 默认由「配音先行」改为「原生音画」：初学者/快速预览优先——说话镜由原生音画
# 后端一次出台词+口型+环境声，不卡在前期配音、最快看到出图/出视频；且原生音轨即成片音轨，
# 没有「后期补真音→重定时→溢出重出视频」的最贵返工。需强 voice-acting 控制、或后端是
# image2video-only（说话镜会降级）时，首跑菜单可改回「配音先行」。仍是首跑必给菜单的预选项。
PRODUCTION_MODE_DEFAULT = "原生音画"

# ── 视觉风格 ──────────────────────────────────────────────────────────────
STYLE_CONTRACT_FIELDS = ("风格名", "视觉基调", "镜头与构图", "光色策略", "运动边界", "风格禁忌")
CINEMATIC_CONTRACT_FIELDS = ("摄影基调", "镜头焦段", "光源动机", "色彩策略", "运镜边界", "真实感禁忌")
VISUAL_CONTRACT_FIELDS = ("色调基线", "场景光位锚", "场景轴线视线", "角色状态演进", "景别阶梯")
SPATIAL_ANCHOR_FIELD = "spatial_anchor"
IDENTITY_ANCHOR_POINTS_FIELD = "identity_anchor_points"

# ── 镜头类型 ──────────────────────────────────────────────────────────────
SHOT_TYPE_KEYWORDS = (
    ("fight_exchange", ("打斗", "搏斗", "交手", "格挡", "出拳", "挥剑", "命中", "受击", "撞击", "掌风", "刀光", "fight", "combat", "hit")),
    ("chase", ("追逐", "追赶", "追杀", "奔逃", "逃跑", "追上", "紧追", "chase", "running away")),
    ("flight", (
        "御剑", "御剑飞行", "飞行", "凌空", "腾空", "腾云", "驾雾", "腾云驾雾", "掠空", "掠过云",
        "飞掠", "坠落", "飞檐", "云海穿行", "空中追逐", "剑光飞行", "flight", "flying", "cloud riding",
        "sword flight",
    )),
    ("reveal_reaction_chain", ("真相揭示", "身份曝光", "身份揭露", "掉马", "马甲暴露", "真实身份", "当众揭穿", "揭穿", "揭露", "证据链", "血书", "遗诏", "密信", "内鬼", "身世", "认亲", "reveal", "identity reveal")),
    ("public_confrontation", ("公开对质", "当众对质", "公堂", "朝堂", "审讯", "逼问", "盘问", "质问", "谈判", "交易", "交涉", "智斗", "权谋", "当众打脸", "反将一军", "confrontation", "interrogation", "negotiation")),
    ("dialogue_shot_reverse", ("对话反打", "正反打", "反打", "过肩", "对视", "视线对位", "台词", "dialogue", "shot reverse", "ots", "eyeline")),
    ("dialogue_closeup", ("说话特写", "口型", "嘴部", "近景说话", "lip-sync", "mouth", "close-up dialogue")),
    ("magic_burst", ("法术", "符阵", "符纹", "灵光", "灵力", "爆发", "雷劫", "雷落", "光束", "剑气", "护盾", "阵法", "magic", "burst", "spell")),
    ("hug_or_pull", ("拥抱", "抱住", "拉扯", "拉住", "抓腕", "拽住", "推开", "扯住", "拉袖", "tug", "pull", "grab", "hug")),
    ("intimate_interaction", ("牵手", "靠近", "亲密", "搀扶", "扶住", "抚脸", "扶肩", "贴近", "疗伤", "intimate", "touch")),
    ("relationship_turn", ("告白", "表白", "承认心意", "心动", "定情", "决裂", "分手", "误会爆发", "反目", "和解", "破镜重圆", "救赎", "互相救场", "吃醋", "护短", "原谅", "relationship turn", "confession", "reconciliation")),
    ("multi_character_same_frame", ("多人同框", "双人同框", "两人同框", "三人同框", "同框", "同画面", "two-shot", "group shot")),
    ("ensemble_blocking", ("群像", "群戏", "群臣", "门徒", "人群", "围观", "队列", "站位", "多人站位", "围住", "围堵", "众人", "ensemble", "crowd")),
    ("multi_person_blocking", ("多人", "三人", "四人", "multi-person", "blocking")),
    ("empty_establishing", ("空镜", "转场", "远景", "氛围", "环境", "establishing", "ambience", "empty")),
)

SPECIAL_TEMPLATE_SHOT_TYPES = (
    "fight_exchange", "chase", "flight", "dialogue_shot_reverse", "magic_burst",
    "reveal_reaction_chain", "public_confrontation", "relationship_turn",
    "hug_or_pull", "intimate_interaction", "multi_character_same_frame",
    "ensemble_blocking", "multi_person_blocking",
)

# 高物理风险/高运动模板：人物姿态一动就崩、接触/遮挡靠帧间插值才稳。这些镜若后端吃不下
# 首尾/中段锚帧，安全网（双帧/多帧插值）会静默失效 → 帧能力不匹配从 WARN 升 BLOCK。
# 单一真值源：anchor_planner（排锚帧密度）与 gate（帧能力闸门）共用，避免两处各定义一份漂移。
HIGH_MOTION_TEMPLATES = frozenset({
    "fight_exchange", "chase", "magic_burst", "flight",
    "hug_or_pull", "intimate_interaction",
})

# 近景表情跨度档（角色脸的情绪从起到止跨几档）。单一真值源：storyboard.continuity.expression_span
# 与 gate 的「大表情近景必须首尾双帧」闸门共用。`大`=跨情绪（平静→爆哭/隐忍→暴怒），是脸被表情
# 带着重画的头号根因，必须走 frames2video 首尾双帧只插值或降级 MCU。
EXPRESSION_SPAN_VALUES = ("微", "中", "大")
EXPRESSION_SPAN_BIG = "大"

# ── 运镜词典（中→英→[速度+方向+起止点] 槽位）──────────────────────────────────────────────
# 把运镜从"只有关键词"升级成结构化：每条带 en（喂英文 prompt）+ slots（速度/方向/起止点该填什么）。
# 动作镜 prompt 应从这里取词并填槽（Veo/即梦运镜段是传达情绪与速度感最强的工具），而非自由散文。
CAMERA_MOVE_LEXICON = {
    "推镜头": {"en": "dolly in", "slots": ("speed", "end_size")},
    "拉镜头": {"en": "dolly out", "slots": ("speed", "end_size")},
    "摇镜头": {"en": "pan", "slots": ("speed", "direction")},
    "移镜头": {"en": "tracking", "slots": ("speed", "direction")},
    "升降": {"en": "crane", "slots": ("speed", "direction", "end_height")},
    "变焦": {"en": "zoom", "slots": ("speed", "end_size")},
    "环绕": {"en": "orbit / circular (360°)", "slots": ("speed", "direction", "arc")},
    "跟拍": {"en": "following / FPV", "slots": ("speed", "direction")},
    "甩镜": {"en": "whip pan", "slots": ("direction",)},
    "冲击变焦": {"en": "crash zoom", "slots": ("end_size",)},
    "手持晃动": {"en": "handheld shake", "slots": ("strength",)},
    "弧线运镜": {"en": "180-degree arc shot", "slots": ("direction", "start_subject", "end_subject")},
    "无人机升起": {"en": "aerial drone ascend", "slots": ("speed", "end_height")},
}
# 速度词槽候选（填进 slots.speed），中→英。
CAMERA_SPEED_WORDS = {
    "缓慢": "slow", "匀速": "steady", "快速": "rapid", "急速冲击": "fast snap", "轻微": "gentle",
}

# ── 运动强度连续档（替代 HIGH_MOTION_TEMPLATES 二分的细粒度补充）──────────────────────────────
# HIGH_MOTION_TEMPLATES 是「是否高风险」的二分闸；这里给 0–3 连续档，供 prompt 调 motion strength/
# cfg 与下游采样密度参考（强动作降 cfg/motion strength 换脸稳是 2026 公认做法）。1=轻微局部动，
# 2=明显全身/主体动，3=高速大幅动作(打斗/追逐/飞行峰值)。0=静帧/空镜。
MOTION_INTENSITY_LEVELS = (0, 1, 2, 3)
MOTION_INTENSITY_BY_TEMPLATE = {
    "fight_exchange": 3, "chase": 3, "flight": 3, "magic_burst": 3,
    "hug_or_pull": 2, "intimate_interaction": 2,
    "dialogue_closeup": 1, "dialogue_shot_reverse": 1,
    "empty_establishing": 0,
}

# ── 负向身份锁词表（动作镜默认注入的 negative prompt）──────────────────────────────────────
# 高动态镜身份最常见崩法：脸/下巴漂移、服装变色、配饰消失、年龄漂移、背景闪烁。Kling 官方给的
# 负向词把这些显式钉死。prompt 生成器对吃身份的镜默认拼上（单一真值源，避免各处各写一份）。
IDENTITY_LOCK_NEGATIVE_TERMS = (
    "de-aging", "morphing features", "shifting jawline", "changing face shape",
    "changing clothes", "color shift", "disappearing accessories",
    "extra limbs", "extra fingers", "flickering background", "identity drift",
)

# ── 题材母题(motif) ──────────────────────────────────────────────────────────
# 穿越/系统流等爽文里高频复现的"母题场景"（系统面板出现/升级/签到/抽奖/爆装备）：相对固定的
# 场景模板 + 每次出现带成长属性（面板进化、等级只增不减）。motif 是 n2d 线内一等概念，靠
# motif_registry.json（数据真值）+ 专项镜头模板库.md 的 motif 模板（镜头契约）+ asset_registry 的
# VFX lifecycle（成长状态机·只进不退）+ n2d-compose 期 overlay（清晰数值文字层）贯穿全流程。
# 检测特征是单一真值源：split/分镜检测器（motif_detector）与 gate 共用，避免两处各定义一份漂移。
MOTIF_ID_PREFIX = "MOTIF_"
# 题材 → 关键词。检测器据此识别题材；命中关键词数 ≥ GENRE_MIN_HITS 即判定，多题材取命中最多者。
GENRE_KEYWORDS = (
    ("系统流", ("系统", "面板", "宿主", "绑定", "签到", "任务奖励", "抽奖", "属性面板", "经验值", "升级", "金手指", "叮——", "恭喜宿主")),
    ("穿越", ("穿越", "重生", "魂穿", "异世界", "回到古代", "前世", "上一世", "醒来发现", "莫名来到")),
    ("修仙", ("修仙", "修真", "灵气", "渡劫", "金丹", "元婴", "筑基", "境界", "御剑", "宗门", "灵根")),
    ("都市", ("总裁", "豪门", "霸总", "微信", "写字楼", "董事长", "集团", "都市")),
    ("宫斗", ("皇上", "娘娘", "嫔妃", "后宫", "册封", "贵妃", "冷宫", "凤印", "圣旨")),
    ("赘婿", ("赘婿", "上门女婿", "岳父", "丈母娘", "入赘", "废物女婿")),
    ("战神", ("战神", "兵王", "退役", "佣兵", "龙组", "镇国", "特种兵")),
)
GENRE_MIN_HITS = 2
# 母题类型 → 关键词。检测器在分镜/正文里据此识别母题桥段。系统面板是首个落地样板；
# 后续 level_up/signin/gacha/loot/cheat 只在此加枚举值 + motif_registry 配置，不改架构。
MOTIF_TYPE_KEYWORDS = (
    ("system_panel", ("系统面板", "面板", "属性栏", "状态栏", "属性面板", "数据面板", "光幕", "虚拟屏", "信息面板", "等级", "经验条", "属性值")),
    ("level_up", ("升级", "等级提升", "突破", "进阶", "level up", "境界提升", "属性提升", "经验满")),
    ("system_refresh", ("系统刷新", "系统更新", "系统升级", "新功能解锁", "系统进化", "面板进化", "系统重启")),
    ("signin", ("签到", "每日签到", "连续签到", "签到奖励", "打卡")),
    ("gacha", ("抽奖", "抽卡", "转盘", "开箱", "幸运抽取", "十连")),
    ("loot", ("爆装备", "掉落", "爆出", "获得装备", "开宝箱", "战利品", "掉宝")),
    ("cheat", ("金手指", "外挂", "作弊器", "系统绑定", "激活系统", "系统降临")),
)
MOTIF_TYPE_MIN_HITS = 1
# 母题首样板：系统面板。绑定的 VFX 资产 id（asset_registry 里的成长 VFX，lifecycle 锁档位只进不退）。
SYSTEM_PANEL_MOTIF_ID = "MOTIF_系统面板"
SYSTEM_PANEL_VFX_ID = "VFX_系统面板"
SYSTEM_PANEL_TEMPLATE_ID = "system_panel"
# motif 成长状态机：这些字段只增不减（机检退级=block），与 asset_lifecycle 的 lifecycle 单调校验同源。
MOTIF_MONOTONIC_FIELDS_DEFAULT = ("level", "panel_tier")
# system_panel overlay 文字层默认字段（n2d-compose render_panel 据此渲染清晰数值，AI 只出空光幕底）。
SYSTEM_PANEL_OVERLAY_FIELDS = ("title", "level", "attrs")

# ── 拆集边界启发式词典（题材可扩展·单一真值源）─────────────────────────────
# split_novel.py（粗切）与 boundary_audit.py（预筛）共用：识别"可作粗胚右边界的强钩"+
# "冲突→爽点/反转"闭环信号。仅启发式，最终钩力/闭环由人或 LLM 精修判定。
# 题材词面在 base 之上按命中题材合并——治"词典只覆盖古言爽文/修仙，女频情感/悬疑/都市退化成无闭环"。
# 默认（未识别题材）= base ∪ 古装动作，复刻历史正则覆盖，保证旧项目行为不变。
# 取值键与 GENRE_KEYWORDS 题材键松对齐；女频/悬疑等可经 _设置.md `题材` 自由文本子串命中。

# 集尾强钩（句尾收束信号）：悬念/惊叹/省略/破折号 + 反转/突变/疑问/紧迫词（题材无关，恒并入）。
BOUNDARY_STRONG_END_BASE = (
    "？", "！", "…", "——", "?", "!",
    "竟然", "竟", "居然", "原来", "没想到", "不料", "岂料",
    "突然", "猛地", "猛然", "骤然", "霎时", "忽然",
    "难道", "莫非", "是谁", "什么", "为什么", "怎么", "凭什么",
    "来了", "出事", "不好了", "糟了", "完了",
)
# 冲突信号（base：通用对抗/危机·题材无关）
BOUNDARY_CONFLICT_BASE = (
    "逼", "威胁", "羞辱", "责罚", "围住", "拦住", "抓住", "质问", "审问",
    "怒", "恨", "怕", "惊", "哭", "跪", "危", "险", "死", "陷害", "冤", "背叛", "惩罚",
)
# 爽点/反转信号（base：通用反击/翻盘/揭示·题材无关）
BOUNDARY_PAYOFF_BASE = (
    "反击", "还手", "夺回", "臣服", "震住", "压住", "赢", "胜", "救", "成功",
    "冷笑", "一笑", "抬头", "睁眼", "原来", "竟然", "竟", "居然", "没想到",
    "不料", "岂料", "突然", "猛地", "反而", "却",
)

# 题材扩展词面：base ∪ 命中题材桶。
BOUNDARY_GENRE_LEXICON = {
    # 古装动作（宫斗/修仙/武侠/战神古装向）：原正则覆盖的古言爽文/打斗词面（=历史默认）。
    "古装动作": {
        "strong_end": ("妖", "斩了", "破阵"),
        "conflict": ("冷宫", "刀", "剑", "血", "毒", "妖", "怪", "追", "逃", "抢", "夺", "打", "杀"),
        "payoff": ("夺回", "跪倒", "跪下", "觉醒", "突破", "升级", "斩", "破阵", "出关", "破境"),
    },
    # 女频情感/言情/虐恋/甜宠/霸总：误会/心动/醋意/告白/虐恋/HE。
    "女频情感": {
        "strong_end": ("心动了", "脸红了", "她哭了", "他走了", "分手吧", "我喜欢你", "原来你也"),
        "conflict": ("误会", "争吵", "冷战", "吃醋", "醋意", "心碎", "失望", "决裂", "分手",
                     "退婚", "嫉妒", "猜忌", "绿茶", "白莲", "抢走", "插足", "误解", "怀疑"),
        "payoff": ("告白", "表白", "和好", "心动", "脸红", "护住", "宠", "撑腰", "复合",
                   "在一起", "拥抱", "破镜重圆", "释怀", "原谅", "心软", "动情"),
    },
    # 悬疑/推理/犯罪/探案：线索/真凶/反转/不在场。
    "悬疑": {
        "strong_end": ("是凶手", "另有其人", "他没死", "线索断了", "真相是", "活着"),
        "conflict": ("尸体", "凶手", "失踪", "被杀", "命案", "嫌疑", "跟踪", "陷阱",
                     "栽赃", "灭口", "勒索", "绑架", "密室", "作案"),
        "payoff": ("真凶", "破案", "真相", "证据", "识破", "反杀", "翻案", "锁定",
                   "招供", "落网", "反转", "水落石出"),
    },
    # 都市/职场/逆袭/赘婿/战神现代向：身份反差/打脸/逆袭。
    "都市": {
        "strong_end": ("打脸", "是大佬", "真实身份", "后台竟是"),
        "conflict": ("看不起", "嘲讽", "针对", "排挤", "刁难", "解雇", "下马威",
                     "踩", "欺压", "讽刺", "刁蛮"),
        "payoff": ("打脸", "逆袭", "真实身份", "扮猪吃虎", "碾压", "震惊全场",
                   "封神", "翻盘", "实力", "曝光", "镇住"),
    },
}

# 题材自由文本子串 → lexicon 桶（别名归一）。同一 genre_text 可命中多桶，全部并入。
BOUNDARY_GENRE_ALIASES = (
    (("女频", "情感", "言情", "虐恋", "甜宠", "恋爱", "霸总", "总裁", "豪门", "宠妻", "婚"), "女频情感"),
    (("悬疑", "推理", "犯罪", "探案", "罪案", "刑侦", "灵异", "无限"), "悬疑"),
    (("都市", "职场", "逆袭", "赘婿", "战神", "兵王", "高武"), "都市"),
    (("宫斗", "宅斗", "后宫", "古言", "古装", "宫廷"), "古装动作"),
    (("修仙", "修真", "玄幻", "仙侠", "武侠", "洪荒"), "古装动作"),
)


def boundary_buckets(genre_text):
    """题材文本 → 命中的 lexicon 桶名列表；未命中返回历史默认 ['古装动作']。"""
    text = (genre_text or "").strip().lower()
    hits = []
    for needles, bucket in BOUNDARY_GENRE_ALIASES:
        if any(n in text for n in needles) and bucket not in hits:
            hits.append(bucket)
    return hits or ["古装动作"]


def boundary_lexicon(genre_text=None):
    """返回 (strong_end, conflict, payoff) 三元组：base ∪ 命中题材桶。

    供 split_novel / boundary_audit 构建正则。未识别题材时复刻历史覆盖（base ∪ 古装动作）。
    """
    buckets = boundary_buckets(genre_text)
    strong = list(BOUNDARY_STRONG_END_BASE)
    conflict = list(BOUNDARY_CONFLICT_BASE)
    payoff = list(BOUNDARY_PAYOFF_BASE)
    for b in buckets:
        spec = BOUNDARY_GENRE_LEXICON.get(b, {})
        strong += list(spec.get("strong_end", ()))
        conflict += list(spec.get("conflict", ()))
        payoff += list(spec.get("payoff", ()))
    # 去重保序
    dedup = lambda xs: list(dict.fromkeys(xs))
    return dedup(strong), dedup(conflict), dedup(payoff)


# ── 路径与目录 ─────────────────────────────────────────────────────────────
SHARED_ASSET_DIR = "共享"
LEGACY_SHARED_ASSET_DIR = "common"
PRODUCTION_DIR = "生产数据"

# ── 机检精度 ──────────────────────────────────────────────────────────────
PRECISION_FULL = "full"
PRECISION_DEGRADED = "degraded"
PRECISION_NONE = "none"
PRECISION_LEVELS = (PRECISION_FULL, PRECISION_DEGRADED, PRECISION_NONE)

PRECISION_ALIASES = {
    "ok": PRECISION_FULL, "full": PRECISION_FULL,
    "insufficient_precision": PRECISION_DEGRADED, "pillow_fallback": PRECISION_DEGRADED,
    "degraded": PRECISION_DEGRADED,
    "none": PRECISION_NONE, "unavailable": PRECISION_NONE,
}

# ── 产物 Kind ──────────────────────────────────────────────────────────────
MANIFEST_KIND = "n2d_episode_manifest"
IDENTITY_REGISTRY_KIND = "n2d_identity_registry"
ASSET_REFERENCE_REGISTRY_KIND = "n2d_asset_reference_registry"
IDENTITY_ADAPTER_MATRIX_KIND = "n2d_identity_adapter_matrix"
COMPLIANCE_MANIFEST_KIND = "n2d_compliance_manifest"
VIDEO_MODEL_ROUTES_KIND = "n2d_video_model_routes"
MOTION_CONTROL_MANIFEST_KIND = "n2d_motion_control_manifest"
EMOTION_FLOW_KIND = "n2d_emotion_flow"
LORA_VALIDATION_REPORT_KIND = "n2d_lora_validation_report"
SKILL_UPDATE_PLAN_KIND = "n2d_skill_update_plan"
SKILL_UPDATE_SNAPSHOT_KIND = "n2d_skill_update_snapshot"
CONSISTENCY_FINDINGS_KIND = "n2d_consistency_findings"
IMAGE_QC_REPORT_KIND = "n2d_image_qc"
GATE_FINDINGS_KIND = "n2d_gate_findings"
CONSISTENCY_LEDGER_KIND = "n2d_consistency_ledger"
CONTRACT_INHERITANCE_KIND = "n2d_contract_inheritance"
IDENTITY_DRIFT_REPORT_KIND = "n2d_identity_drift_report"
IDENTITY_VOICE_DRIFT_REPORT_KIND = "n2d_identity_voice_drift_report"
IDENTITY_VOICE_PRINT_REPORT_KIND = "n2d_identity_voice_print_report"
PRODUCTION_EVENT_KIND = "n2d_production_event"
PRODUCTION_DASHBOARD_KIND = "n2d_production_dashboard"
PRODUCTION_ALERTS_KIND = "n2d_production_alerts"
ASSET_PACK_KIND = "n2d_asset_pack"
ASSET_RERUN_PLAN_KIND = "n2d_asset_rerun_plan"
MOTIF_REGISTRY_KIND = "n2d_motif_registry"          # 题材母题数据真值（出图/共享/motif_registry.json）
MOTIF_PLAN_KIND = "n2d_motif_plan"                  # 母题检测建议（生产数据/motif_plan_第N集.{json,md}）
COMBAT_REGISTRY_KIND = "n2d_combat_registry"        # 招式/打斗套路真值（出图/共享/combat_registry.json）
BATCH_QUEUE_KIND = "n2d_batch_queue"
DIFFERENTIATION_CANDIDATES_KIND = "n2d_differentiation_candidates"
EPISODE_REVIEW_SCORE_KIND = "n2d_episode_review_score"
# 外部投放战绩 JSONL 可复用该 kind；保持无前缀便于非 n2d 工具读取。
GENRE_PERFORMANCE_RECORD_KIND = "genre_performance_record"
LORA_CARD_KIND = "n2d_lora_card"
LORA_DATASET_MANIFEST_KIND = "n2d_lora_dataset_manifest"
LORA_TRAIN_JOB_KIND = "n2d_lora_train_job"
PLATFORM_FEEDBACK_KIND = "n2d_platform_feedback"
REVIEW_UI_KIND = "n2d_review_ui"
SCORE_VISUAL_CHECKS_KIND = "n2d_score_visual_checks"
VISUAL_STATE_LEDGER_KIND = "n2d_visual_state_ledger"

# ── 重制策略 ──────────────────────────────────────────────────────────────
REGEN_MODE_MINIMAL = "最小"
REGEN_MODE_STRICT_REFRESH = "严审刷新"
LEGACY_REGEN_MODE_KEEP_IMAGES = "保图刷新"

# ── 进度标记 ──────────────────────────────────────────────────────────────
PROGRESS_DONE = "✅"
PROGRESS_TODO = "⬜"
PROGRESS_ROUGH_PREFIX = "⏳"
PROGRESS_PARTIAL_RE = r"(\d+)\s*/\s*(\d+)"

CONTRACT_VERSION = 2
