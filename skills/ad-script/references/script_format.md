# 广告脚本 / 分镜 格式（ad-script 参考）

## 广告脚本.md（脚本 pass）

逐段秒级时间轴，每段四件套：画面 / 台词·VO / 音乐床·SFX / 镜头建议。

```markdown
# 广告脚本 — <项目名>（主片 30s · 16:9）

## [0–3s] 钩子
- 画面：清晨闹钟疯响，主角一把按掉，黑眼圈特写。
- VO：「又是被闹钟拖起来的一天？」
- 音乐/SFX：闹钟刺耳 → 戛然而止
- 镜头：特写，手持微晃，冷调

## [3–10s] 痛点
...

## [10–22s] 产品 / 方案
- 画面：产品 hero shot，包装正面，品牌色铺底。
- VO：「<合规主张>」          # 不写"最/第一/治愈"，claim 留依据
- 镜头：环绕推近，光位 45° 主光

## [22–27s] 证据 / 记忆点
...

## [27–30s] CTA / 品牌包装
- 画面：end card：logo + slogan + CTA
- VO/字幕：「<slogan>」「<行动指令>」
```

## voiceover.txt（驱动配音）

逐句一行，可前缀角色/旁白；VO 旁白用 `旁白：`。每行将被 `ad-voice` 测实际时长。

```
旁白：又是被闹钟拖起来的一天？
旁白：<合规主张>
旁白：<slogan>
```

## storyboard.json（分镜 pass · 配音后）

实测时长驱动；每镜带 `visual_contract` 与接缝 `continuity`。

```json
{
  "schema_version": 1,
  "master_seconds": 30,
  "visual_contract": {"品牌色": "#E60012", "光位锚": "45°主光", "画风": "写实电影感"},
  "shots": [
    {"shot_id": "S1", "section": "钩子", "duration": 3.0,
     "frame": "特写·闹钟·冷调", "vo_lines": [1],
     "assets": {"PROD_main": false, "CHAR_user": true},
     "continuity": {"transition": "硬切", "need_end_frame": false}},
    {"shot_id": "S4", "section": "产品/证据", "duration": 4.0,
     "frame": "产品 hero shot + 有依据的数据宣称", "claim_ids": ["claim_01"],
     "disclosures": [{"claim_id": "claim_01", "text": "适用条件与样本局限",
       "source_text": "来源：某机构 2026Q2 报告", "duration_sec": 4,
       "font_height_ratio": 0.04, "contrast_review": "pass", "safe_zone_review": "pass",
       "relationship": "same_screen", "relative_prominence": "sufficient"}],
     "assets": {"PROD_main": true},
     "continuity": {"transition": "硬切", "need_end_frame": false}},
    {"shot_id": "S5", "section": "CTA", "duration": 3.0,
     "frame": "end card: logo+slogan+CTA", "assets": {"PROD_main": true, "BRAND_main": true},
     "continuity": {"transition": "硬切", "need_end_frame": false}}
  ]
}
```

- `vo_lines`：该镜承载的 VO 句子下标（指向 `配音/时长清单.json` 每句的 `idx`，1-based）。`finalize_storyboard.py` 据此查**单镜 VO 溢出**（单镜 VO 秒数 > 该镜 duration → 旁白被截断 block）。
- `assets`：逐镜绑定 `PROD_xx`（产品）/`CHAR_xx`（角色）/`LOC_xx`（场景）/`logo`/`slogan`/`CTA`，供 `ad-image` 三层定妆库锁一致性、并供定稿闸门做**强制项落镜**判定。产品镜必带 `PROD_xx`；brief mandatories（logo/slogan/法律声明/CTA）须由某镜的 `frame`/`assets`/`legal_lines`/end card 承载，否则定稿 block。
- `claim_ids` + `disclosures`：每个会播出的 claim 必须绑定承载镜；引证来源、实验条件、适用范围、有效期/样本局限按 `claim_id` 同屏或紧邻呈现。普通 `legal_lines` 只能证明“有一行字”，不能证明 claim 与来源/条件的关系。`finalize_storyboard.py` 验结构，`cutdown.py` 把 claim+披露当原子组合，防止短版只留大字宣称。
- `continuity.transition`：硬切 / 微溶解 / 跳切；`need_end_frame`：是否要尾帧接力（`ad-image` 出 `镜头N_end.png`，`ad-video` 双帧引导）。
- 总时长（Σ duration）必须 ≈ `master_seconds`，由 `finalize_storyboard.py` 闸门对账。

## 镜头时长.json

`finalize_storyboard.py` 产物：每镜时长 + VO 对账 + findings。下游 `ad-image`/`ad-video` 据此排产。
