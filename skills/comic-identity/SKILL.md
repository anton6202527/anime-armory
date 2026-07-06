---
name: comic-identity
description: 画漫画角色/场景/道具一致性流程。Use when comic panels show character drift, wrong faces, changed outfits, inconsistent monsters/props/locations, missing shared reference images, needing 定妆/identity_registry/reference anchors, rerun plans for affected panels, or a consistency gate before comic-compose for projects under 创作区/画漫画. Produces 出图/共享/identity_registry.json, 出图/共享/图片 anchors, comic identity reports, and panel rerun targets. Triggers 漫画一致性, 角色一致性, 定妆, 换脸, 脸漂, 共享参考, identity_registry, comic-identity.
---

# comic-identity — 漫画共享定妆与一致性闸门

在 `comic-image` 和 `comic-compose` 之间补一层一致性流程：先把会反复出现的人物、妖物、场景、道具、系统资产落成共享参考，再让逐格出图真实消费这些参考图。不要把人物漂移的图直接交给 `comic-compose`。

## 输入

- `脚本/第N话/panel_script.json`：每格的 `references` 真值。
- `出图/第N话/prompt/panel_jobs.json`：逐格出图任务和当前引用绑定。
- `出图/第N话/panels/*.png`：已采纳或待复核的面板图。
- `出图/共享/图片/` 与 `出图/共享/identity_registry.json`：共享定妆库。

## 输出

- `出图/共享/identity_registry.json`：`CHAR_`、`MON_`、`LOC_`、`PROP_`、`SYS_` 等参考资产登记。
- `出图/共享/图片/<REF_ID>__anchor.png`：可传给生图后端的锚点图。
- `出图/共享/图片/<CHAR_ID>__front.png` / `__three_quarter.png` / `__side.png` / `__back.png` / `__face.png`：人物标准多视图包。项目 `_设置.md` 的 `定妆级别` 默认是 `长线专门定妆`，常驻角色进入批量生产前必须补齐。
- `生产数据/comic_identity_views_第N话_contact_sheet.jpg`：人物多视图 QA 拼图，用于快速检查是否缺图、串脸或视图不对。
- `生产数据/comic_identity_report_第N话.json/md`：缺失引用、每格真实参考输入数、重抽目标。
- 更新 `panel_jobs.json` 中每个 reference 的真实 `path`。

## 快速命令

从已采纳面板种下共享锚点：

```bash
python3 skills/comic-identity/scripts/identity.py "创作区/画漫画/作品名" --chapter 第1话 seed \
  --map CHAR_JYC=P002 --map CHAR_PEI=P005 --map MON_TIGER=P004 --overwrite
```

生成一致性报告并回填可解析路径：

```bash
python3 skills/comic-identity/scripts/identity.py "创作区/画漫画/作品名" --chapter 第1话 report --write
```

按长线口径生成常驻角色专门定妆多视图：

```bash
python3 skills/comic-identity/scripts/identity.py "创作区/画漫画/作品名" --chapter 第1话 views \
  --backend auto --characters CHAR_JYC,CHAR_PEI --views front,three_quarter,side,back,face
```

Codex 图像通道不可用或需要真实图生图后端时，可显式走即梦官方 CLI：

```bash
python3 skills/comic-identity/scripts/identity.py "创作区/画漫画/作品名" --chapter 第1话 views \
  --backend dreamina --characters CHAR_JYC,CHAR_PEI --views front,three_quarter,side,back,face \
  --model-version 5.0 --resolution-type 2k
```

报告里的 `rerun_targets` 交给 `comic-image` 重抽：

```bash
python3 skills/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 \
  --targets P003,P004 --force --max-attempts 3
```

## 工作流

1. 先跑 `report --write`。若有 `missing_refs`，先补共享参考，不要合成。
2. 对常驻角色和关键资产建立锚点。短 demo 可从已采纳面板种 `__anchor.png`；默认长线口径应换成正面/45度/侧面/背面和关键表情的专门定妆图。用 `views` 子命令从当前 anchor 生成并登记多视图；`--backend auto` 会优先用可用后端，必要时可显式指定 `dreamina`。
   - `views` 默认对非 `front` 视图优先使用已存在的 `front` 定妆图作为参考锚点，避免原剧情格的坐跪、挥砍、裁切等动作姿态污染多视图；需要强制用原始锚点时传 `--no-prefer-front-anchor`。
3. 重新跑 `report --write`，确认每个带 reference 的格子都有真实图片路径。
4. 对 `rerun_targets` 用 `comic-image` 的 `--force --targets ...` 重抽。runner 会把参考图作为 `codex exec --image` 真实附件传入，并写 `生产数据/codex_reference_bundles/`。
5. 重抽后再跑一次 `report --write`。`missing_refs=[]` 且 `rerun_targets=[]` 后，才进入 `comic-compose`。

## 判定口径

- `reference id` 只是名字，不等于模型看见了参考图；必须有真实 `path`，并在生成记录里有 `reference_input_count > 0`。
- 带 `CHAR_` 或 `MON_` 的格子如果是旧图、没有 reference manifest、或生成时 `reference_input_count=0`，必须进 `rerun_targets`。
- 多人同框不是删除剧情的理由；补齐每个主体的锚点，再重抽该格。
- 人物标准多视图是 `front / three_quarter / side / back / face`。`report --write` 会列 `missing_character_views`；`定妆级别=长线专门定妆` 时这些缺口是进入发布/连载审查前的阻断项。
- 出图阶段不再生产空白气泡：台词、旁白、拟声词和气泡形状属于 `comic-compose`。旧图中遗留无字气泡时，优先回 `comic-image` 重出无气泡画面；无法重出时，合成阶段只能遮盖对应文字槽，不应留下空泡。

## 不做什么

- 不把其它生产线脚本或数据结构直接 import 到漫画线；本 skill 只使用漫画线自己的共享定妆、真实参考入参和重抽计划流程。
- 不做本地贴脸、换脸或裁脸贴回。修复脸漂应重抽整格或补定妆后重抽。
- 不替代 `comic-image` 生成图片，也不替代 `comic-compose` 嵌字。
