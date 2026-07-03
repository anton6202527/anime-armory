#!/usr/bin/env python3
# 转写 20s demo 真歌的实际唱词+时间戳 → 字幕/asr.json
import json, sys, whisper

song = sys.argv[1]
out = sys.argv[2]
m = whisper.load_model("small")
r = m.transcribe(song, language="zh", word_timestamps=True,
                 condition_on_previous_text=False)
segs = [{"start": round(s["start"], 2), "end": round(s["end"], 2),
         "text": s["text"].strip(),
         "words": [{"w": w["word"], "s": round(w["start"], 2), "e": round(w["end"], 2)}
                   for w in s.get("words", [])]}
        for s in r["segments"] if s["text"].strip()]
json.dump(segs, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"[ok] {len(segs)} segments -> {out}")
for s in segs:
    print(f"  {s['start']:.2f}-{s['end']:.2f}: {s['text']}")
