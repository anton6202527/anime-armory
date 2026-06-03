# RVC / so-vits-svc 翻唱接入（song-cover）

> 仅在合规闸门通过后用（自有/授权/合成音色；原曲有权）。

## 流程总览
`目标歌 → demucs 分离 vocals/instrumental → RVC 把 vocals 转成目标音色 → 与原 instrumental 回混 → 新歌`

## 1) 分离人声（demucs，Mac 可跑）
```bash
python3 -m demucs --two-stems vocals -o _demucs 歌/song.wav
# 得 _demucs/htdemucs/song/{vocals.wav,no_vocals.wav}
```

## 2) 训练目标音色模型（RVC，需 GPU 更快）
- 装 RVC WebUI（官方仓库）；准备目标音色**几分钟干净干声**（自有/授权）。
- WebUI 训练 → 得 `.pth` 模型 + index。
- so-vits-svc 是同类替代，流程相近。

## 3) 转换 vocals → 目标音色
- RVC WebUI「推理」：输入 `vocals.wav` + 选目标模型 → 输出转换后 vocals。
- 参数：音高(transpose 半音，男女互换常 ±12)、index rate、保护清辅音。

## 4) 回混
```bash
ffmpeg -y -i 转换后vocals.wav -i _demucs/htdemucs/song/no_vocals.wav \
  -filter_complex "[0:a]volume=1.0[v];[1:a]volume=0.9[b];[v][b]amix=inputs=2:normalize=0,dynaudnorm" \
  歌/song_cover.wav
```

## 合法性
- 目标音色：自有 / 授权 / 合成；**真人歌手嗓需授权**（2026 opt-in）。
- 翻唱已发行曲：词曲版权属原作者，商用须授权。自有原创歌随意。
