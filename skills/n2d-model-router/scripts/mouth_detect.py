#!/usr/bin/env python3
"""mouth_visible 自动预填 —— 从首帧 PNG 检测嘴部可见性，预填/复核每 Clip 的 `mouth_visible`。

背景：`router.clip_has_mouth_visible()` 只从**分镜文本关键词**（口型/嘴/说话/台词/正脸…）推
mouth_visible；但渲染出的首帧可能与文本不符——反应镜文本没写"说话"却张着嘴、或文本写"正脸"
实际侧脸。`mouth_visible` 又决定**原生音画 opt-in**（开环境声要求 `mouth_visible=no`）和是否要
口型同步，填错 → 原生人声漏进说话镜 / 口型对不上。本脚本给每 Clip 一个**图像端**判断，预填
建议值并标出图↔文本不一致，省得操作者逐镜手判。

  · 文本端（始终可用）：复用 `router.clip_has_mouth_visible`（单一真值源，不另立关键词）。
  · 图像端（可选）：装 insightface 时用 106 关键点判正脸 + 嘴部可见；缺库优雅跳过、回退文本端，
                    显式标 `image=unknown`，绝不臆造。

纯函数（prompt 字段解析 / 文本×图像×prompt 三方复核）无依赖、带 pytest。

用法：python3 mouth_detect.py <作品根> 第N集 [--json]
退出码：有任一图↔文本/图↔prompt 冲突(warn) → 1，否则 0。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router  # noqa: E402  复用 load_storyboard / clip_has_mouth_visible / make_clip_id / _clip_text

_PROMPT_MV = re.compile(r"mouth_visible\s*[=:：]\s*(yes|no|是|否|y|n)", re.I)


def parse_prompt_mouth_visible(text: str) -> Optional[bool]:
    """从一段视频 prompt 文本里抽 `mouth_visible=yes/no`（兼容中英/=/:）。无则 None。纯函数。"""
    m = _PROMPT_MV.search(text or "")
    if not m:
        return None
    return m.group(1).lower() in ("yes", "是", "y")


def reconcile(text_says: bool, image_says: Optional[bool],
              prompt_says: Optional[bool]) -> Dict[str, Any]:
    """文本启发式 × 图像检测 × prompt 已填值 三方复核。纯函数。

    建议值优先级：图像 > 文本（图像是渲染真相，文本只是意图）。
    冲突判级：图↔prompt 不一致 = warn（prompt 要按图改，否则原生音画/口型出错）；
              无图时退而比 文本↔prompt（弱冲突，也 warn 提示人确认）。
    """
    suggested = text_says if image_says is None else image_says
    source = "text" if image_says is None else "image"
    verdict, msg = "ok", ""
    if image_says is not None and prompt_says is not None and image_says != prompt_says:
        verdict = "warn"
        msg = (f"图上嘴可见={_yn(image_says)} 但 prompt 标 mouth_visible={_yn(prompt_says)}"
               f"——按图改，否则原生音画 opt-in/口型会错")
    elif image_says is None and prompt_says is not None and text_says != prompt_says:
        verdict = "warn"
        msg = (f"分镜文本暗示嘴可见={_yn(text_says)} 但 prompt 标 mouth_visible={_yn(prompt_says)}"
               f"——装 insightface 可图像端定夺；否则人确认")
    elif image_says is not None and image_says != text_says:
        verdict = "warn"
        msg = (f"图上嘴可见={_yn(image_says)} 与分镜文本启发式={_yn(text_says)} 不一致"
               f"——以图为准，建议 mouth_visible={_yn(image_says)}")
    return {"verdict": verdict, "suggested": suggested, "suggested_source": source,
            "text_says": text_says, "image_says": image_says, "prompt_says": prompt_says,
            "message": msg}


def _yn(value: Optional[bool]) -> str:
    return "yes" if value else "no" if value is not None else "unknown"


# ---- 图像端（可选） ----

def _load_face_app():
    try:
        import insightface  # noqa: F401
        from insightface.app import FaceAnalysis
    except Exception:
        return None
    try:
        app = FaceAnalysis(allowed_modules=["detection", "landmark_2d_106"])
        app.prepare(ctx_id=-1, det_size=(640, 640))
        return app
    except Exception:
        return None


def detect_mouth_in_image(png_path: str, app=None) -> Optional[bool]:
    """首帧是否有「正脸 + 嘴部可见」。缺库/无脸/读图失败 → None（交文本端，不臆造）。"""
    if app is None:
        app = _load_face_app()
    if app is None:
        return None
    try:
        import cv2
        img = cv2.imread(png_path)
        if img is None:
            return None
        faces = app.get(img)
    except Exception:
        return None
    if not faces:
        return False  # 检测器在位但画面无脸 → 嘴不可见（空镜/背身）
    # 取最大脸；有 106 关键点则看嘴部点是否构成可见张合区域（粗判，宁松勿误杀）
    face = max(faces, key=lambda f: float(getattr(f, "det_score", 0) or 0))
    lmk = getattr(face, "landmark_2d_106", None)
    if lmk is None:
        return True  # 有脸但无细点：保守认为正脸说话镜居多 → 嘴可见
    try:
        ys = [float(p[1]) for p in lmk[52:72]]  # 106 点中嘴部区段
        return (max(ys) - min(ys)) > 1.0  # 嘴部有垂直跨度 = 可见
    except Exception:
        return True


# ---- 编排 ----

def _first_frame_png(root: str, ep: str, clip_id: str) -> Optional[str]:
    num = "".join(ch for ch in clip_id if ch.isdigit())
    stems = []
    if num:
        n = int(num)
        stems = [f"镜头{n:02d}", f"镜头{n}", f"Clip_{n:02d}", clip_id]
    for stem in stems:
        p = os.path.join(root, "出图", ep, "图片", f"{stem}.png")
        if os.path.isfile(p):
            return p
    return None


def _prompt_mouth_for_clip(root: str, ep: str, clip_id: str) -> Optional[bool]:
    """从该集视频 prompt 里找该 Clip 的 mouth_visible（best-effort：扫 prompt/ 下 md）。"""
    pdir = os.path.join(root, "出视频", ep, "prompt")
    if not os.path.isdir(pdir):
        return None
    for name in sorted(os.listdir(pdir)):
        if not name.endswith(".md"):
            continue
        try:
            text = open(os.path.join(pdir, name), encoding="utf-8").read()
        except Exception:
            continue
        # 定位到该 clip 的段落再就近取 mouth_visible（粗切：按 clip_id 出现处截一段）
        idx = text.find(clip_id)
        seg = text[idx: idx + 600] if idx >= 0 else ""
        val = parse_prompt_mouth_visible(seg)
        if val is not None:
            return val
    return None


def analyze(root: str, ep: str) -> Dict[str, Any]:
    try:
        sb = router.load_storyboard(Path(root), ep)
    except Exception as exc:
        return {"available": False, "rows": [], "notes": [f"mouth 预填跳过：{exc}"]}
    clips = sb.get("clips")
    if not isinstance(clips, list) or not clips:
        return {"available": False, "rows": [], "notes": ["storyboard 无 clips[]"]}
    app = _load_face_app()
    notes: List[str] = []
    if app is None:
        notes.append("未装 insightface——仅文本端预填 mouth_visible，图像端复核跳过（image=unknown）")
    rows: List[Dict[str, Any]] = []
    for i, clip in enumerate(clips, 1):
        if not isinstance(clip, Mapping):
            continue
        clip_id = router.make_clip_id(clip, i)
        text_says = router.clip_has_mouth_visible(clip)
        png = _first_frame_png(root, ep, clip_id)
        image_says = detect_mouth_in_image(png, app) if (png and app) else None
        prompt_says = _prompt_mouth_for_clip(root, ep, clip_id)
        r = reconcile(text_says, image_says, prompt_says)
        r.update({"clip_id": clip_id, "heading": clip_id, "loc": f"出视频/{ep}/{clip_id}",
                  "png": os.path.relpath(png, root) if png else None})
        rows.append(r)
    return {"available": True, "rows": rows, "notes": notes}


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="mouth_visible 自动预填/复核")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 1 if any(r["verdict"] == "warn" for r in res["rows"]) else 0
    print(f"=== mouth_visible 预填：{ns.root} {ns.episode} ===")
    if not res["available"]:
        for n in res["notes"]:
            print(f"  · {n}")
        return 0
    for r in res["rows"]:
        mark = "⚠️" if r["verdict"] == "warn" else "·"
        print(f"{mark} {r['clip_id']}: 建议 mouth_visible={_yn(r['suggested'])}"
              f"（{r['suggested_source']}；文本={_yn(r['text_says'])} 图={_yn(r['image_says'])} prompt={_yn(r['prompt_says'])}）")
        if r["message"]:
            print(f"     {r['message']}")
    for n in res["notes"]:
        print(f"  · {n}")
    return 1 if any(r["verdict"] == "warn" for r in res["rows"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
