# FaceFusion 接入参考（video-faceswap 本地换脸）

> 仅在第 0 步合规闸门通过后使用。FaceFusion 是开源、全本地、免费的换脸平台，支持 Apple Silicon。

## 安装（Mac M1+ / Linux CUDA）
```bash
# 需 Python 3.12 + conda
git clone https://github.com/facefusion/facefusion
cd facefusion
conda create -n facefusion python=3.12 -y && conda activate facefusion
python install.py --onnxruntime default        # Mac: 走 CoreML；NVIDIA: --onnxruntime cuda
```
- Mac：执行后用 `--execution-providers coreml`，线程 `--execution-thread-count 10-16`。
- 无独显也能跑，慢；M 系列芯片明显更快。

## Headless（脚本化）换脸
```bash
python facefusion.py headless-run \
  --source-paths 源脸.jpg \           # 1 张清晰正脸（多张不同角度更稳）
  --target-path  源片.mp4 \
  --output-path  _raw_换脸.mp4 \
  --processors face_swapper face_enhancer \
  --face-swapper-model inswapper_128_fp16 \   # 质量高慢；hyperswap_1a_256=默认快
  --face-enhancer-model gfpgan_1.4 \
  --execution-providers coreml --execution-thread-count 12
```
> 不同版本子命令/参数名可能微调（3.x 用 `headless-run`）；首次跑先 `python facefusion.py --help` 核对。

## 常见画质问题 → 处理
| 问题 | 处理 |
|---|---|
| 手/麦克风挡脸时穿帮 | 开 face occluder 蒙版（`--face-mask-types occlusion box`） |
| 多人脸串脸 | 用 `--face-selector-mode` + 参考脸（reference）锁定只换目标那张 |
| 换后偏糊 | 加 `face_enhancer`（GFPGAN/CodeFormer），`--face-enhancer-blend` 调 |
| 肤色/光照不匹配 | 提高源脸质量、与目标光照相近的源图；必要时后期调色 |
| 侧脸/大角度崩 | 源脸给多角度；大角度帧本就难，必要时分段换 |

## 强制 AI 标识（法律必做，见 SKILL 第 4 步）
换完务必调公共 `watermark` skill（`watermark.py --mode ai`）烧可见提示 + 写元数据。中国《标识办法》要求**可见 + 隐式**双标识；平台投放按平台隐式水印要求再补。**绝不**做去水印。

## 合法性（重申）
仅 本人脸 / 已授权演员（留存授权声明）/ 纯合成脸。名人或他人未授权、诈骗、绕过人脸识别、NSFW、未成年 → 拒做。依据：中国《AI 生成合成内容标识办法》、US DEFIANCE/NO FAKES Act、EU AI Act、丹麦肖像权法。
