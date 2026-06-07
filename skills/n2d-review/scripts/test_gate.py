"""从本目录跑：cd skills/n2d-review/scripts && python -m pytest test_gate.py"""
import gate


GOOD_SHOT = """## 镜头 1（冷开场）🔑关键镜

**目标存档**：`出图/第1集/镜头1_冷开场.png`
**参考图**（多图参考派生铁律）：
- `出图/common/定妆_沈念.png`（正脸主参考，强度 0.8）
- `出图/common/定妆_沈念_侧.png`（角度锚，强度 0.55）
- `出图/common/定妆_沈念_半身.png`（服装锚，强度 0.5）
- `出图/common/定妆_冷宫寝殿.png`（场景定妆，强度 0.45）

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
不要换脸、不要换衣、不要改发型、不要文字/logo。
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
- 重抽预算：主要人物/关键镜，软上限 4 次 ｜ 实抽__次 → ⬜过 ⬜重抽 ⬜到顶取定妆最一致版
"""


def setup_function():
    gate.findings.clear()


def test_good_character_shot_prompt_passes_strict_structure():
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, GOOD_SHOT)
    assert gate.findings == []


def test_character_shot_missing_anchor_is_blocked():
    shot = GOOD_SHOT.replace("锚点句：", "").replace("锚点句已拼", "人物已拼")
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert any(f["sev"] == gate.BLOCK and f["dim"] == "角色一致性" and "锚点句" in f["msg"] for f in gate.findings)


def test_shot_without_reference_block_is_blocked_as_text2image():
    shot = GOOD_SHOT.replace("**参考图**（多图参考派生铁律）：\n- `出图/common/定妆_沈念.png`（正脸主参考，强度 0.8）\n- `出图/common/定妆_沈念_侧.png`（角度锚，强度 0.55）\n- `出图/common/定妆_沈念_半身.png`（服装锚，强度 0.5）\n- `出图/common/定妆_冷宫寝殿.png`（场景定妆，强度 0.45）\n", "")
    gate.check_image_shot_prompt_section("01_分镜出图.md", 1, shot)
    assert any(f["sev"] == gate.BLOCK and "参考图" in f["msg"] for f in gate.findings)
