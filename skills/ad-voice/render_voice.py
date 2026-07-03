#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拍广告 VO 配音：voiceover.txt → 逐句音频 + 整轨 vo.wav + 时长清单.json（实测时长驱动镜头）。

多后端可插拔；本脚本内置 **macOS say 占位** 与 **estimate 静音占位**（无凭证时也能把时长跑出来）。
真后端（CosyVoice / MiniMax / 火山 / 克隆）由各自 CLI 产 wav 后用 --from-dir 登记。

克隆真人嗓 = 合规硬闸门：需 VOICE_CLONE_AUTHORIZED=1，否则拒做（2026 opt-in）。

用法：
    python3 render_voice.py <作品根> --backend say        # macOS 占位
    python3 render_voice.py <作品根> --backend estimate    # 跨平台静音占位（按字数估时）
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

import voice_manifest as vm

CN_CHARS_PER_SEC = 4.5   # 中文播报约每秒 4–5 字，用于 estimate 占位估时

# 占位后端（不产生真实声纹）——这些后端永远不触发克隆闸门。
PLACEHOLDER_BACKENDS = {"say", "estimate"}
# 云端商用后端：请求具体「代言人/名人」voice_id（仿真人音色）须有授权痕迹。
CLOUD_BACKENDS = {"minimax", "火山", "volc", "volcano"}


def norm_backend(name):
    """后端名归一：小写 + 去连字符/下划线，使 cosyvoice-v2 / Cosy_Voice / XTTS 等变体统一比对。"""
    return (name or "").strip().lower().replace("-", "").replace("_", "")


def _is_ref_audio_env(key, prefix=None):
    """env 名是否是「参考音」(声纹来源)？匹配 <PFX>_REF_* 且非 *_TEXT（_TEXT 是逐字稿）。

    prefix=None 时匹配任意前缀的 *_REF_* —— 任何参考音的存在即表明意图克隆，
    比按后端名猜前缀更稳（变体名/自定义命名都拦得住）。
    """
    if key.endswith("_TEXT"):
        return False
    if prefix:
        pfx = prefix.strip().upper()
        return key == f"{pfx}_REF_AUDIO" or key.startswith(f"{pfx}_REF_")
    return key.endswith("_REF_AUDIO") or "_REF_" in key


def clone_refs(prefix=None):
    """扫描环境里的参考音 env，返回命中的 env 名列表（排序，便于报错信息稳定）。"""
    return sorted(k for k, v in os.environ.items()
                  if v and _is_ref_audio_env(k, prefix))


def clone_authorization_check(backend, args):
    """克隆授权硬闸门：仅当**真的在克隆**时才要求 VOICE_CLONE_AUTHORIZED=1。

    触发条件（任一）——按"实际是否克隆/仿真人音色"判定，**不**按后端名是否在某固定集合：
      - 显式传了参考音/克隆开关：--ref / --clone；
      - 环境里给了参考音 env（<PREFIX>_REF_*，默认 PREFIX 取归一后端名大写）；
      - 请求了具体的代言人/名人 voice_id（--voice-id / 云端商用后端的指定音色）。
    占位后端（say/estimate）合成的是默认占位嗓，不克隆任何人，绝不触发。
    返回触发闸门的原因列表（空=无需授权）。
    """
    nb = norm_backend(backend)
    if nb in PLACEHOLDER_BACKENDS:
        return []
    reasons = []
    if args.ref:
        reasons.append(f"--ref {args.ref}（参考音克隆）")
    if args.clone:
        reasons.append("--clone（克隆开关）")
    # 环境参考音：给了 --ref-prefix 就按它精确匹配，否则扫任意 *_REF_*（参考音存在=意图克隆）。
    refs = clone_refs(args.ref_prefix)
    if refs:
        reasons.append(f"参考音 env：{','.join(refs)}")
    if args.voice_id:
        reasons.append(f"--voice-id {args.voice_id}（指定代言人/名人音色）")
    return reasons


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe_duration(path):
    """ffprobe 读时长（秒）。失败返回 None。"""
    if not shutil.which("ffprobe"):
        return None
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def synth_say(text, out_wav, voice="Tingting"):
    """macOS say → aiff → wav。返回是否成功。"""
    if not shutil.which("say"):
        return False
    aiff = out_wav + ".aiff"
    if run(["say", "-v", voice, "-o", aiff, text]).returncode != 0:
        # 某些中文环境 say 中文会空音频；交给上层降级
        return False
    if not shutil.which("ffmpeg"):
        return False
    ok = run(["ffmpeg", "-y", "-i", aiff, "-ar", "44100", "-ac", "1", out_wav]).returncode == 0
    if os.path.exists(aiff):
        os.remove(aiff)
    return ok and os.path.exists(out_wav) and (probe_duration(out_wav) or 0) > 0.05


def synth_silence(out_wav, seconds):
    """生成指定秒数静音 wav（estimate 占位 / say 降级）。"""
    if not shutil.which("ffmpeg"):
        return False
    return run(["ffmpeg", "-y", "-f", "lavfi", "-t", f"{seconds:.3f}",
                "-i", "anullsrc=r=44100:cl=mono", out_wav]).returncode == 0


def est_seconds(text):
    return max(0.6, len(text.strip()) / CN_CHARS_PER_SEC)


def main():
    ap = argparse.ArgumentParser(description="拍广告 VO 配音 + 时长清单")
    ap.add_argument("project_root")
    ap.add_argument("--backend", default="say", help="say | estimate | <真后端名>")
    ap.add_argument("--gap", type=float, default=0.25, help="句间停顿秒")
    ap.add_argument("--placeholder-voice", default="Tingting")
    ap.add_argument("--ref", help="参考音 wav（克隆他人嗓）——触发授权闸门")
    ap.add_argument("--clone", action="store_true", help="显式克隆开关——触发授权闸门")
    ap.add_argument("--ref-prefix", help="参考音 env 前缀（默认=归一后端名大写，如 COSYVOICE_REF_*）")
    ap.add_argument("--voice-id", help="指定代言人/名人 voice_id（仿真人音色）——触发授权闸门")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    vo_txt = os.path.join(root, "脚本", "voiceover.txt")
    if not os.path.isfile(vo_txt):
        print(f"[err] 缺 {vo_txt}（先跑 ad-script 脚本 pass）", file=sys.stderr)
        sys.exit(2)

    backend = args.backend.strip().lower()
    # 克隆/仿真人音色授权硬闸门：按"实际是否在克隆"判定，不按后端名固定集合（详见 clone_authorization_check）。
    clone_reasons = clone_authorization_check(backend, args)
    if clone_reasons and os.environ.get("VOICE_CLONE_AUTHORIZED") != "1":
        print("[block] 检测到克隆/仿真人音色（" + "；".join(clone_reasons) + "），"
              "需 VOICE_CLONE_AUTHORIZED=1（肖像+声音授权，2026 opt-in）。"
              "代言人/名人真声另需授权痕迹（ad-craft/ai_usage.py --talent-status）。"
              "未授权拒做——用默认嗓（不喂参考音/不指定 voice_id）或 --backend say 占位先跑时长。",
              file=sys.stderr)
        sys.exit(3)

    voicemap = {}
    vmap_path = os.path.join(root, "设定库", "voicemap.json")
    if os.path.isfile(vmap_path):
        with open(vmap_path, encoding="utf-8") as f:
            voicemap = json.load(f)

    out_dir = os.path.join(root, "配音")
    os.makedirs(out_dir, exist_ok=True)
    with open(vo_txt, encoding="utf-8") as f:
        lines = vm.parse_voiceover(f.read())

    real_backend = backend not in ("say", "estimate")
    entries, wavs, cursor = [], [], 0.0
    for idx, (role, text) in enumerate(lines, 1):
        line_wav = os.path.join(out_dir, f"line_{idx:02d}.wav")
        placeholder = backend in ("say", "estimate")
        ok = False
        if backend == "say":
            ok = synth_say(text, line_wav, args.placeholder_voice)
        if not ok:  # estimate 后端 / say 降级
            placeholder = True
            ok = synth_silence(line_wav, est_seconds(text))
        dur = probe_duration(line_wav) or est_seconds(text)
        start, end = cursor, cursor + dur
        entries.append(vm.manifest_entry(
            idx, role, text, dur, start, end, args.gap, os.path.basename(line_wav),
            voicemap, real_backend, placeholder, args.placeholder_voice))
        wavs.append(line_wav)
        cursor = end + args.gap

    # 拼整轨 vo.wav（句间补静音 gap）
    vo_wav = os.path.join(out_dir, "vo.wav")
    if shutil.which("ffmpeg") and wavs:
        concat_list = os.path.join(out_dir, "_concat.txt")
        silence = os.path.join(out_dir, "_gap.wav")
        synth_silence(silence, args.gap)
        with open(concat_list, "w", encoding="utf-8") as f:
            for i, w in enumerate(wavs):
                f.write(f"file '{w}'\n")
                if i < len(wavs) - 1:
                    f.write(f"file '{silence}'\n")
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", vo_wav])
        for tmp in (concat_list, silence):
            if os.path.exists(tmp):
                os.remove(tmp)

    manifest = {"schema_version": 1, "kind": "ad_voice_manifest",
                "backend": backend, "total_seconds": round(cursor, 3),
                "has_placeholder": any(e.get("占位") for e in entries), "lines": entries}
    with open(os.path.join(out_dir, "时长清单.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"[ok] 配音 {len(entries)} 句  总时长≈{cursor:.2f}s  后端={backend}"
          + ("  ⏳占位（正式定稿前需真配音复跑）" if manifest["has_placeholder"] else ""))
    print(f"     时长清单：{os.path.join(out_dir, '时长清单.json')}")


if __name__ == "__main__":
    main()
