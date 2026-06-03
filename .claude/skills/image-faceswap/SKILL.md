---
name: image-faceswap
description: 通用图片换脸（公共能力，不属于任何生产线家族）— 给一张目标图片（或链接）+ 一张源脸，把图里的脸换成源脸。任何流程（制MV / 制漫剧 / 出图阶段 / 单独使用）都可调用。**仅限本人脸 / 已授权演员脸 / 纯合成脸**，带强制「合规闸门 + AI 标识水印」。基于 FaceFusion(本地, Mac 可跑)。Use when asked to 图片换脸 / 给照片换脸 / 把图里的脸换成XX / 照片换脸 / image face swap. Triggers 图片换脸, 照片换脸, 给图换脸, 换头像, 图换脸, image faceswap, photo face swap, image-faceswap.
---

# image-faceswap — 通用图片换脸（公共能力 · 合规闸门 + 强制标识）

把一张图片（本地文件或链接）里的人脸换成**用户提供的源脸**。**这是一个公共能力**，不绑定任何生产线——制MV、制漫剧的出图阶段、或用户单独使用都能调它。和 [[video-faceswap]] 是一对（视频版/图片版），共用同一套 FaceFusion 底座 + 合规规则。只用通用工具：**FaceFusion**（本地换脸）+ **yt-dlp**（取链接，可选）+ **Pillow**（打标）。

> ⚠️ **换真人脸 = deepfake，2026 强监管。本 skill 只服务合法场景，且每张产物强制打 AI 标识。**

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`swap模型`、`增强模型`（`源脸合法性` 见下方第 0 步合规闸门，**每次确认**）。

## 第 0 步 — 合规闸门（硬性，先过，不过直接拒做）

逐项确认，任一不满足 → **拒绝并说明**：

| 必须满足 | 说明 |
|---|---|
| **源脸来源合法** | 仅限 ① 用户**本人脸** ② **已书面授权的演员**脸 ③ **纯合成脸**（无真人对应） |
| **目标图片有改编权** | 自有素材 / 已授权 / 公版；链接图片先确认有权改它（版权） |
| **输出必打 AI 标识** | 可见水印 + 元数据标注（法律强制，见第 4 步）；**绝不**提供抹水印 |

**一律拒做**（直接说明不能做）：
- 名人 / 他人**未授权**的脸
- 用于**诈骗 / 误导 / 绕过人脸识别**等身份认证
- **NSFW / 色情** / 涉**未成年人**
- 要求**去除 / 伪造** AI 水印或标识

> 闸门通过后把授权记进任务的 meta/说明（`源脸=本人|授权(附声明)|合成`、`目标图片权利=自有|授权|公版`、通过时间）。auto mode 下无法确认来源合法 → **默认拒做**，要用户显式声明。

## 工作流（闸门通过后）

输出位置由调用方决定：
- 被某作品调用 → 落该作品目录（如 `制MV/<曲名>/换脸/` 或漫剧的 `出图/换脸/`）。
- 单独使用 → `--out <目录>`，缺省落输入图片同级的 `换脸_<原名>/`。

1. **取图**：本地文件直接用；链接 → `yt-dlp -o "<目录>/源图.%(ext)s" "<URL>"` 或直接下载（先过闸门②版权）。
2. **准备源脸**：1 张清晰正脸（多角度/光照更稳）。
3. **换脸**（FaceFusion headless，Mac=CoreML，详见 `references/facefusion.md`）：
   ```bash
   python facefusion.py headless-run \
     --source-paths 源脸.jpg --target-path 源图.jpg --output-path _raw_换脸.png \
     --processors face_swapper face_enhancer \
     --face-swapper-model inswapper_128_fp16 \
     --execution-providers coreml --execution-thread-count 12
   ```
   > target/output 是**图片**（jpg/png）就是图片换脸；命令与视频版同，只换 `--target-path`/`--output-path` 后缀。
4. **强制打 AI 标识（法律必做）**：
   ```bash
   python3 <skill>/label_watermark_image.py _raw_换脸.png 换脸成片.png "本图含 AI 换脸合成"
   ```
   烧可见提示 + 写图片元数据（PNG Comment / JPEG EXIF）。中国《标识办法》还要隐式水印——平台投放按平台要求补隐式标识。
5. **落档**：成片 `换脸成片.png`；如被某作品调用，按该作品约定回写进度。

## 依赖（仅通用工具，无 skill 依赖）
- **FaceFusion**（Python 3.12 + conda；Mac M1+ 用 CoreML）。与 [[video-faceswap]] 同一份安装，详见 `references/facefusion.md`。
- **yt-dlp**（取链接，可选）。
- **Pillow**（`label_watermark_image.py` 打标，纯 Pillow，不需 ffmpeg）。

## 详细参考
- FaceFusion 安装/调用/Mac/遮挡处理：`references/facefusion.md`
- 法律依据：中国《AI 生成合成内容标识办法》(2025，须可见+隐式水印+肖像同意)、美国 DEFIANCE/NO FAKES Act、欧盟 AI Act、丹麦肖像权法。

## 常见错误 / 红线
| 错误 | 纠正 |
|---|---|
| 跳过第 0 步合规闸门 | 闸门是本 skill 第一职责，**先确认源脸合法再动手** |
| 换名人/他人未授权脸 | 拒做（违 NO FAKES/肖像权/标识办法） |
| 输出不打 AI 标识 | 法律强制，必走第 4 步打标+元数据 |
| 应要求抹掉/伪造水印 | 拒做（中国法明令禁止改 AI 水印） |
| 下载链接图片不问版权 | 先过闸门②，确认有改编权 |
| 用视频版的 label_watermark.py 打图片 | 图片用 `label_watermark_image.py`（纯 Pillow，不走 ffmpeg） |
