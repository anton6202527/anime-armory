#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拍广告 VO 配音：voiceover.txt → 逐句音频 + 整轨 vo.wav + 时长清单.json（实测时长驱动镜头）。

多后端可插拔；本脚本内置 **macOS say 占位** 与 **estimate 静音占位**（无凭证时也能把时长跑出来）。
真后端（CosyVoice / MiniMax / 火山 / 克隆）必须先由各自 CLI/API 产 wav，再用 --from-dir 登记。

克隆真人嗓 = 合规硬闸门：需 VOICE_CLONE_AUTHORIZED=1，否则拒做（2026 opt-in）。

用法：
    python3 render_voice.py <作品根> --backend say        # macOS 占位
    python3 render_voice.py <作品根> --backend estimate    # 跨平台静音占位（按字数估时）
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

import voice_manifest as vm

_AD_LIB = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "_lib"))
if _AD_LIB not in sys.path:
    sys.path.insert(0, _AD_LIB)
import io_utils  # noqa: E402  本线 _lib 原子写（清单落盘不可半写）

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


def is_placeholder_backend(backend):
    """True when this script is allowed to synthesize placeholder audio itself."""
    return norm_backend(backend) in PLACEHOLDER_BACKENDS


def text_sha256(text):
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_prev_lines(manifest_path):
    """上次 时长清单.json → (idx→entry 映射, 上次 backend)。读不出来按空处理（全量重合成）。"""
    try:
        with open(manifest_path, encoding="utf-8") as f:
            prev = json.load(f)
    except (OSError, ValueError):
        return {}, ""
    lines = prev.get("lines") if isinstance(prev, dict) else None
    if not isinstance(lines, list):
        return {}, ""
    return ({e.get("idx"): e for e in lines if isinstance(e, dict)},
            str(prev.get("backend") or ""))


def line_reusable(prev_entry, line_wav, t_sha, expected_voice_key):
    """占位 wav 复用判定：文件在、文本 hash 未变、音色键未变、时长可读才跳过重合成。"""
    return bool(prev_entry
                and os.path.isfile(line_wav)
                and prev_entry.get("text_sha256") == t_sha
                and prev_entry.get("voice_key") == expected_voice_key
                and (probe_duration(line_wav) or 0) > 0.05)


def import_external_wav(src, dst):
    """外部真 VO 导入保护：目标已存在且内容不同时，先把旧文件落 dst.bak 再覆盖，绝不静默覆盖。"""
    if os.path.abspath(src) == os.path.abspath(dst):
        return
    if os.path.isfile(dst):
        if file_sha256(dst) == file_sha256(src):
            return
        shutil.copyfile(dst, dst + ".bak")
    shutil.copyfile(src, dst)


def external_line_wavs(from_dir, count):
    """Collect line_01.wav..line_NN.wav from an external real-VO render directory.

    The sequence must be complete and ffprobe-readable before registration; otherwise
    real VO timing would silently fall back to estimates, which is exactly what this
    stage is meant to avoid.
    """
    src_dir = os.path.abspath(from_dir)
    if not os.path.isdir(src_dir):
        raise ValueError(f"--from-dir 不存在或不是目录: {src_dir}")
    wavs = []
    for idx in range(1, count + 1):
        path = os.path.join(src_dir, f"line_{idx:02d}.wav")
        if not os.path.isfile(path):
            raise ValueError(f"--from-dir 缺逐句音频: {path}")
        dur = probe_duration(path)
        if dur is None or dur <= 0.05:
            raise ValueError(f"--from-dir 音频无法读取有效时长: {path}")
        wavs.append((path, dur))
    return wavs


def stitch_track(wavs, vo_wav, gap):
    """Stitch line wavs into vo.wav with a fixed gap. Return True on success."""
    if not (shutil.which("ffmpeg") and wavs):
        return False
    out_dir = os.path.dirname(os.path.abspath(vo_wav))
    concat_list = os.path.join(out_dir, "_concat.txt")
    silence = os.path.join(out_dir, "_gap.wav")
    if not synth_silence(silence, gap):
        return False
    with open(concat_list, "w", encoding="utf-8") as f:
        for i, w in enumerate(wavs):
            f.write(f"file '{w}'\n")
            if i < len(wavs) - 1:
                f.write(f"file '{silence}'\n")
    ok = run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", vo_wav]).returncode == 0
    for tmp in (concat_list, silence):
        if os.path.exists(tmp):
            os.remove(tmp)
    return ok


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
    ap.add_argument("--from-dir", help="登记外部真后端已生成的 line_01.wav..line_NN.wav；真后端必填")
    ap.add_argument("--force", action="store_true", help="忽略逐句复用缓存，占位全量重合成")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    vo_txt = os.path.join(root, "脚本", "voiceover.txt")
    if not os.path.isfile(vo_txt):
        print(f"[err] 缺 {vo_txt}（先跑 ad-script 脚本 pass）", file=sys.stderr)
        sys.exit(2)

    backend = args.backend.strip()
    backend_norm = norm_backend(backend)
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

    real_backend = not is_placeholder_backend(backend)
    external_wavs = []
    if real_backend:
        if not args.from_dir:
            print("[block] 真 VO 后端不能静默降级为占位。"
                  f"当前后端={backend}，但 ad-voice 尚未内置该后端的直接合成器；"
                  "请先用对应 CLI/API 生成逐句 line_01.wav..line_NN.wav，"
                  "再用 --from-dir 登记，或临时改用 --backend say/estimate 只做 rough preview。",
                  file=sys.stderr)
            sys.exit(4)
        try:
            external_wavs = external_line_wavs(args.from_dir, len(lines))
        except ValueError as exc:
            print(f"[block] {exc}", file=sys.stderr)
            sys.exit(5)

    manifest_path = os.path.join(out_dir, "时长清单.json")
    prev_lines, prev_backend = load_prev_lines(manifest_path)
    entries, wavs, cursor, reused = [], [], 0.0, 0
    for idx, (role, text) in enumerate(lines, 1):
        line_wav = os.path.join(out_dir, f"line_{idx:02d}.wav")
        t_sha = text_sha256(text)
        placeholder = not real_backend
        ok = False
        dur = None
        if real_backend:
            src, dur = external_wavs[idx - 1]
            import_external_wav(src, line_wav)
            ok = True
        else:
            # 占位复用：同后端、文本/音色键未变且 wav 可读 → 跳过重合成（--force 全量重跑）
            expected_key = vm.voice_key_for(role, voicemap, False, args.placeholder_voice)
            prev = prev_lines.get(idx)
            if (not args.force and prev_backend == backend.lower()
                    and line_reusable(prev, line_wav, t_sha, expected_key)):
                placeholder = bool(prev.get("占位", True))
                dur = probe_duration(line_wav)
                ok = True
                reused += 1
            elif backend_norm == "say":
                ok = synth_say(text, line_wav, args.placeholder_voice)
        if not ok and not real_backend:  # estimate 后端 / say 降级
            placeholder = True
            ok = synth_silence(line_wav, est_seconds(text))
        dur = dur if dur is not None else (probe_duration(line_wav) or est_seconds(text))
        start, end = cursor, cursor + dur
        entry = vm.manifest_entry(
            idx, role, text, dur, start, end, args.gap, os.path.basename(line_wav),
            voicemap, real_backend, placeholder, args.placeholder_voice)
        entry["text_sha256"] = t_sha
        entries.append(entry)
        wavs.append(line_wav)
        cursor = end + args.gap

    # 拼整轨 vo.wav（句间补静音 gap）
    vo_wav = os.path.join(out_dir, "vo.wav")
    if not stitch_track(wavs, vo_wav, args.gap) and real_backend:
        print("[block] 真 VO 逐句音频已登记，但 vo.wav 整轨拼接失败；请检查 ffmpeg/源 wav 后重跑。",
              file=sys.stderr)
        sys.exit(6)

    manifest = {"schema_version": 1, "kind": "ad_voice_manifest",
                "backend": backend.lower(), "total_seconds": round(cursor, 3),
                "has_placeholder": any(e.get("占位") for e in entries), "lines": entries}
    if args.from_dir:
        manifest["source"] = {"type": "external_line_wavs", "from_dir": os.path.abspath(args.from_dir)}
    io_utils.write_json_atomic(manifest_path, manifest)

    qc_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_qc.py")
    qc = subprocess.run([sys.executable, qc_script, root])
    if real_backend and qc.returncode:
        print("[block] 正式 VO 技术 QC 未通过；修复 配音/voice_qc.json findings 后重跑。", file=sys.stderr)
        sys.exit(7)

    print(f"[ok] 配音 {len(entries)} 句  总时长≈{cursor:.2f}s  后端={backend}"
          + (f"  复用 {reused} 句" if reused else "")
          + ("  ⏳占位（正式定稿前需真配音复跑）" if manifest["has_placeholder"] else ""))
    print(f"     时长清单：{manifest_path}")


if __name__ == "__main__":
    main()
