---
name: mv-watermark
description: mv 线专属水印（自包含，随 mv 线打包）— 给一张图片或一段视频烧水印。两类：①合规 AI 标识（法律强制·可见提示+元数据·只加不去），②品牌/logo/账号水印（文字或 logo PNG，位置/透明度/大小可选）。图/视频用同一个工具，按扩展名自动判定。任何流程（制MV / 制漫剧 / 出图出视频 / 换脸 / 单独使用）都可调用，与 mv-video-faceswap 同级的本线能力。本机 ffmpeg 无 libass → 一律 Pillow 渲染水印层再 overlay。Use when asked to 加水印 / 打水印 / 烧水印 / AI标识 / 加logo / 打品牌 / 防盗水印 / watermark. Triggers 水印, 加水印, 打水印, 烧水印, AI标识, AI标识水印, 加logo, 品牌水印, 账号水印, 防盗水印, watermark.
---

# mv-watermark — 通用水印（mv 线专属 · 合规 AI 标识 + 品牌水印）

给**图片或视频**烧水印。**这是 mv 线专属能力**（随 mv 线打包）——制漫剧、制MV、出图/出视频、faceswap、或用户单独使用都能调它（与 `mv-video-faceswap` 同级）。只用通用工具：**Pillow**（渲染水印层）+ **ffmpeg**（视频 overlay）。图还是视频按输入扩展名自动判定。

两类水印（`--mode`）：

| mode | 用途 | 默认位置 | 是否强制/可去 |
|---|---|---|---|
| `ai`（默认） | **合规 AI 标识**：可见提示 + 写元数据，标注内容为 AI 合成 | 右上角 `tr` | 法律强制 · **只加不去** |
| `brand` | **品牌/logo/账号水印**：文字或 logo PNG | 右下角 `br` | 可选 · 位置/透明度/大小可调 |

> ⚠️ **铁律：本 skill 只“加”水印，绝不提供“去”水印。** 中国《AI 生成合成内容标识办法》(2025) 禁止改/去 AI 水印。任何“去水印/抹标识/伪造水印”请求一律拒做。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/mv-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**。

本 skill 涉及的选择点（仅 `brand` 模式）：`水印文字`、`水印logo文件`、`水印位置`(tl/tr/bl/br/center)、`水印透明度`、`水印大小`。传 `--settings-root <作品根>` 时，工具会从该作品的 `_设置.md` 读取这些默认值；命令行显式参数优先。`ai` 合规标识不是品牌偏好项——**投放前强制打、不可去**。

## 合规（`ai` 模式必读）

- AI 合成内容（生图 / 生视频 / 换脸 / 配音）投放前**必须**带可见 AI 标识 + 元数据；faceswap 与 voice-clone 的产物**强制**走本步，不可跳过。
- 本工具写可见提示 + 文件元数据（视频 `comment`、PNG `Comment`、JPEG EXIF `ImageDescription`）。中国法还要**隐式水印**——平台投放时按各平台要求另补隐式标识，隐式标识不在本地工具范围。
- n2d 产线不得把水印当“成片后想起来再补”的事项：先在 `合规/compliance_manifest.json` 声明 `ai_disclosure` 和 `watermark` 策略；本工具执行后，把输出文件写回 `watermark.final_assets[]`。`n2d-review/scripts/gate.py --stage compose` 检查策略，`--stage review` 检查最终水印资产。
- **绝不**提供去水印/抹标识/伪造标识能力。

## 用法

输出位置由调用方决定：被某作品调用 → 落该作品目录；单独使用 → 用户指定 `<out>`。

```bash
# ① 合规 AI 标识（默认 mode=ai）——图或视频同一个命令
python3 <skill>/watermark.py 输入.mp4 输出_水印.mp4
python3 <skill>/watermark.py 输入.png 输出_水印.png --text "本图含 AI 合成 / AI-generated"

# ② 品牌/账号文字水印
python3 <skill>/watermark.py 成片.mp4 成片_品牌.mp4 --mode brand --text "@我的账号" --pos br --opacity 0.8

# ③ 品牌 logo PNG 水印
python3 <skill>/watermark.py 成片.mp4 成片_品牌.mp4 --mode brand --logo logo.png --pos br --scale 0.12

# ④ logo + 主文字 + 描述行 三者组合（竖向堆叠：logo 上·主文字中·描述小字下）
python3 <skill>/watermark.py 成片.mp4 成片_品牌.mp4 --mode brand \
  --logo logo.png --text "剧名/账号" --desc "AI 漫剧 · 第1集 · 转载注明" --pos br --opacity 0.85

# ⑤ 从作品 _设置.md 读取 brand 默认值
python3 <skill>/watermark.py 成片.mp4 成片_品牌.mp4 --mode brand --settings-root 制漫剧/某作品
```

**brand 模式 `--logo` / `--text` / `--desc` 三者可任意组合**（给哪个画哪个，竖向堆成一块按 `--pos` 落位）；`--desc` 是配在主文字下方的小字描述行。`--meta` 则是写进文件元数据（不可见、溯源用）的描述文本。

参数：`--mode ai|brand`、`--settings-root`(作品根，读取品牌水印默认值)、`--text`(主文字)、`--desc`(描述小字行)、`--logo`、`--pos tl|tr|bl|br|center`、`--opacity 0~1`、`--scale`(logo宽/画宽)、`--fontscale`(主字号/画高)、`--descscale`(描述字号/主字号)、`--margin`、`--meta`(元数据描述)。详见 `references/usage.md`。

## 依赖（仅通用工具，无 skill 依赖）
- **Pillow**（渲染水印层；系统中文字体 PingFang/STHeiti，回退 DejaVu）。
- **ffmpeg + ffprobe**（视频 overlay；本机精简版无 libass，故走 Pillow→overlay，**不要**写 drawtext/subtitles 滤镜）。

## 被谁调用
- `mv-video-faceswap`：换脸产物强制烧 `--mode ai`（合规）。
- `n2d-compose`：按 `n2d-compliance` 合规包声明的策略烧 `--mode ai` / `--mode brand`，并回写最终资产路径。
- `mv-compose`：成片可选烧 `--mode ai`（AI 合成投放）或 `--mode brand`（账号/片头水印）。
- `ad-compose`：交付前给主片/cutdown 烧 `--mode ai`（AI 合成投放强制）或 `--mode brand`（品牌 logo/slogan）。
- 任何其他线 / 用户单独使用。

## 常见错误 / 红线
| 错误 | 纠正 |
|---|---|
| 应要求去水印/抹标识/伪造水印 | **拒做**（中国法明令禁止改 AI 水印） |
| AI 合成投放不打 AI 标识 | 法律强制，必走 `--mode ai` |
| 写 `drawtext`/`subtitles` 滤镜 | 本机 ffmpeg 无 libass，本工具已用 Pillow→overlay |
| brand 模式既无 --text 也无 --logo | 二者必给其一 |
