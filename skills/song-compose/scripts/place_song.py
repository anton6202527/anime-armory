#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# song-compose 归一：把生成好的歌(Suno/ACE-Step 产)拷成 写歌/<曲名>/歌/song.wav；
# 可选 --split 用 demucs 分离 vocals/instrumental（下游对齐/卡点更准）。自包含。
# 用法: place_song.py <写歌作品根> <生成的歌文件> [--split]
import sys, os, shutil, subprocess, argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("src"); ap.add_argument("--split", action="store_true")
    args = ap.parse_args()
    if not os.path.exists(args.src): sys.exit(f"找不到源歌：{args.src}")
    gd = os.path.join(args.root, "歌"); os.makedirs(gd, exist_ok=True)

    ff = shutil.which("ffmpeg")
    dst = os.path.join(gd, "song.wav")
    if args.src.lower().endswith(".wav"):
        shutil.copy(args.src, dst)
    elif ff:
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", args.src, "-ar", "44100", "-ac", "2", dst], check=True)
    else:
        shutil.copy(args.src, os.path.join(gd, "song" + os.path.splitext(args.src)[1]))
        print("[warn] 无 ffmpeg，未转 wav，已原样拷入 歌/"); dst = None
    if dst: print(f"[ok] 成品歌 → {dst}")

    if args.split:
        if shutil.which("demucs") or shutil.which("python3"):
            try:
                subprocess.run(["python3", "-m", "demucs", "--two-stems", "vocals",
                                "-o", os.path.join(gd, "_demucs"), dst or args.src], check=True)
                print(f"[ok] demucs 分离 → 歌/_demucs/（vocals/no_vocals）")
            except Exception as e:
                print(f"[warn] demucs 失败（pip install demucs）：{e}")
        else:
            print("[warn] 无 demucs，跳过分离（pip install demucs）")
    print("[next] 挑版定稿 → song-cover(可选) 或 交 mv 做视频")


if __name__ == "__main__":
    main()
