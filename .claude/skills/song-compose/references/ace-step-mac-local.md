# ACE-Step 本地（Mac）实测 — 安装可行，但 16GB 机出整首歌不现实

> 2026-06 在本机实测，作为 song-compose 后端选型（"先验证 ACE-Step 在 Mac 速度再定主力"）的结论。

## 安装（一次性，已跑通）
- `git clone --depth 1 https://github.com/ace-step/ACE-Step ~/ACE-Step`
- `conda create -n acestep python=3.10 -y`
- `conda run -n acestep pip install -e .`（拉 torch 2.12 / diffusers / transformers / librosa 等）
- 首次运行自动从 HF 下 `ACE-Step/ACE-Step-v1-3.5B` → `~/.cache/ace-step/checkpoints`（**7.7GB**）

## 必踩的两个坑
1. **`infer.py` 用随机 DataSampler，不读你的词**。要自写脚本直接调 `ACEStepPipeline(...)(prompt=style, lyrics=结构化词, audio_duration=, infer_step=, manual_seeds=, save_path=)`。脚本见 `~/ACE-Step/gen_song.py`（style/lyrics 走文件，--fp32/--duration/--steps/--seed/--out）。
2. **torchaudio≥2.11 的 `save()` 走 TorchCodec**，未装 torchcodec 直接 `ImportError`。不要去装 torchcodec（要配 torch 版本）；在 import pipeline 前 monkeypatch：
   ```python
   import torchaudio, soundfile as sf
   def _save(path, t, sr, *a, **k):
       arr = t.detach().cpu().float().numpy()
       arr = arr.T if arr.ndim==2 else arr   # (ch,frames)->(frames,ch)
       sf.write(str(path), arr, int(sr))
   torchaudio.save = _save
   ```
3. 跑前置 `PYTORCH_ENABLE_MPS_FALLBACK=1`；pipeline 在 mps 上强制把 bf16 切回 fp32（见 pipeline_ace_step.py:129），所以 `--fp32`。

## 性能实测（致命）
- 机器：**16GB 统一内存 Mac（MPS）**。
- 任务：20s 音频 / 20 步 / fp32。
- 结果：**总耗时 3 小时 21 分**。前 11 步 ~48–108s/it 还行，**第 12 步起爆到 1100–1700s/it**——3.5B fp32(14GB+激活) 超 16GB → 疯狂 swap。
- 推断：整首歌（~180s 音频 × 60 步）= 数十倍工作量 + 更长 latent 占更多内存 → **几天且大概率 OOM 崩**。出来的 20s 是真有人声音乐（RMS 0.16/peak 0.92），质量维度 OK，是**速度不可用**。

## 结论 / 选型建议
- **16GB Mac：不要用本地 ACE-Step 出整首歌。** 顶多生成 ~20–30s 短段（配 `cpu_offload=True` 降峰值内存或许能稳在 ~50–100s/it），仍要 ~30–60 分钟一段。
- 整首歌优先 **Suno/Udio 云**（`歌/_suno_prompt.txt` 已备好可直接贴）。
- 若坚持本地：需 ≥32–64GB 内存或 CUDA 机；或等 ACE-Step 出可用的 q4 量化权重（REPO_ID_QUANT 当前仓库标注未定）。
