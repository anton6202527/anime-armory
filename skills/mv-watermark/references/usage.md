# mv-watermark — 调用细节

## 输入判定
按输入文件扩展名自动判定走图还是视频：
- 图：`.png .jpg .jpeg .webp .bmp` → Pillow `alpha_composite`，写 PNG `Comment` / JPEG EXIF `ImageDescription`。
- 视频：`.mp4 .mov .mkv .webm .m4v .avi` → Pillow 渲染全画幅透明水印层 → ffmpeg `overlay=0:0` 全程烧 + 写 `comment` 元数据，`-c:a copy` 不动音轨。

## 参数表
| 参数 | 默认 | 说明 |
|---|---|---|
| `--mode` | `ai` | `ai`=合规 AI 标识（强制）；`brand`=品牌/logo |
| `--settings-root` | 无 | 作品根；brand 模式可从 `_设置.md` 读取 `水印文字` / `水印logo文件` / `水印位置` / `水印透明度` / `水印大小` |
| `--text` | ai 模式有内置合规文案 | 主文字水印；brand 模式 logo/text/desc 至少给其一 |
| `--desc` | 无 | 描述小字行（仅 brand），配在 logo/主文字**下方**；可与 logo+text 同时出现 |
| `--logo` | 无 | logo PNG 路径（仅 brand）；可与 --text/--desc **组合**竖向堆叠 |
| `--pos` | ai=`tr` / brand=`br` | `tl tr bl br center`（整块一起落位） |
| `--opacity` | `1.0` | brand 文字/logo 整体透明度 0~1（ai 固定醒目） |
| `--scale` | `0.12` | brand logo 宽 / 画面宽 |
| `--fontscale` | `0.030` | 主文字字号 / 画面高 |
| `--descscale` | `0.62` | 描述行字号 / 主文字字号 |
| `--margin` | `0.02` | 边距 / min(画宽,画高) |
| `--meta` | ai 有默认 | 写入文件元数据 comment 的描述文本（不可见·溯源用） |

> **brand 组合规则**：`--logo` / `--text` / `--desc` 给哪个画哪个，竖向堆成一块（logo 在上、主文字其次、描述小字在下），整块按 `--pos` 落位、水平居中对齐。三者全给即「图标 + 标题 + 副描述」完整角标。

## 示例
```bash
# 合规：换脸视频（faceswap 调）
python3 watermark.py _raw_换脸.mp4 换脸成片.mp4 --text "本视频含 AI 换脸合成 / AI-generated"

# 合规：生图（出图阶段批量可循环调）
python3 watermark.py shot.png shot_ai.png

# 品牌：片头账号水印，左上、半透明
python3 watermark.py 成片.mp4 成片_品牌.mp4 --mode brand --text "@账号" --pos tl --opacity 0.6 --fontscale 0.025

# 品牌：右下角 logo，占画宽 10%
python3 watermark.py 成片.mp4 成片_品牌.mp4 --mode brand --logo brand.png --pos br --scale 0.10 --opacity 0.85

# 品牌：沿用项目 _设置.md 里的账号/位置/透明度/大小
python3 watermark.py 成片.mp4 成片_品牌.mp4 --mode brand --settings-root "制漫剧/某作品"
```

## 红线
- 只加不去：本工具**没有**、也**不会加**去水印/抹标识参数。
- AI 合成内容投放：`--mode ai` 强制；隐式水印按平台另补，不在本地工具范围。
- 本机 ffmpeg 无 libass/drawtext → 一律走 Pillow→overlay，别改成滤镜烧字。
