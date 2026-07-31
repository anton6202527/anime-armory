---
name: song-cover
description: 写歌·翻唱/换声（可选）— 把一首歌的人声换成目标音色（歌声转换 SVC：RVC / so-vits-svc）。**仅限自有嗓 / 已授权音色 / 合成音色**，带合规闸门。song 写歌线可选步。Use when asked to 翻唱 / 换音色 / 换嗓 / AI翻唱 / 声音转换 / RVC. Triggers 翻唱, 换音色, 换嗓, AI翻唱, 歌声转换, RVC, so-vits-svc, song-cover.
---

# song-cover — 翻唱 / 换声（写歌线·可选）

把一首歌（song-compose 产 或 用户给）的**人声换成目标音色**——歌声转换（SVC），不是重新作曲。**自包含**，用通用工具 RVC / so-vits-svc + demucs。

> ⚠️ **换成真实歌手的嗓 = 需授权**（2026 opt-in）。本 skill 只服务合法场景。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/song/song-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`翻唱后端`、`演唱音色(合规·每次确认)`。

## 第 0 步 — 合规闸门（硬性，先过）
| 必须满足 | 说明 |
|---|---|
| **目标音色合法** | 仅 ① 自有嗓 ② 已授权音色 ③ 纯合成音色（无真人对应） |
| **被翻唱曲有权** | 原曲词曲版权另属原作者；商用翻唱需授权（自有原创歌随意） |
**拒做**：未授权真人歌手嗓、用于冒充/误导、未成年。命中即拒并说明。

## 依赖
```bash
# RVC（最流行，低延迟）：装 RVC WebUI；给目标音色几分钟干声训一个模型
# so-vits-svc：同类 SVC，GPU 友好
pip install demucs    # 先分离人声再转换，质量更高（Mac 可跑）
```

## 工作流
1. 过合规闸门（音色来源 + 原曲权利）。
2. **分离人声**：demucs 把目标歌分成 vocals / instrumental。
3. **转换音色**：RVC（用目标音色模型）把 vocals 转成目标嗓。
4. **回混**：转换后 vocals + 原 instrumental → 新换声音频；不要手工覆盖正式母版。
5. **登记并使下游失效**：用 `scripts/register_cover.py` 记录音色授权、模型与音频 hash，更新 `歌/song.wav` / `混音/pre_master.wav`，旧 master、master check、release pack 自动视为过期。之后重新跑母版与发行链。

```bash
python3 skills/song/song-cover/scripts/register_cover.py "<写歌作品根>" "<换声.wav>" \
  --model "<模型或音色>" --authorization authorized
```

## 详细参考
- RVC / so-vits-svc 安装·训练音色·转换·回混：`references/rvc.md`

## 常见错误
| 错误 | 纠正 |
|---|---|
| 跳过合规闸门 | 先确认音色合法 + 原曲权利 |
| 换未授权真人歌手嗓 | 拒做 |
| 不分离直接转整首 | 先 demucs 分 vocals，只转人声再回混 |
| 换声后沿用旧母版报告 | register cover 后重新跑 master delivery、BS.1770 检查和 release pack |
| 想把歌声转换当成视频换脸 | 那是另一类音画处理；歌声转换只处理人声音色 |
