# Alignment evidence schemas

`alignment_report.json` schema 5 separates three facts that must not be conflated:

1. `character_coverage_ratio` is deterministic text-to-timestamp coverage.
2. `whisperx_alignment_scores` contains raw diagnostics from a general speech aligner. It is explicitly uncalibrated, not singing-specific, and acceptance-ineligible.
3. `acceptance` records one formal evidence route after the generated files have been inspected.

## Required binding

After generation, read `acceptance.required_binding` or run:

```bash
python3 skills/mv/mv-lyric-sync/scripts/align.py <作品根> \
  --accept-existing --show-required-binding
```

The returned object has this shape:

```json
{
  "master": {"path": "歌/song.wav", "sha256": "<64 hex>"},
  "alignment_audio": {"path": "歌/vocals.wav", "sha256": "<64 hex>"},
  "lyrics": {"path": "词/lyrics.md", "sha256": "<64 hex>"},
  "ass": {"path": "字幕/karaoke.ass", "sha256": "<64 hex>"},
  "lrc": {"path": "字幕/lyrics.lrc", "sha256": "<64 hex>"},
  "report_preaccept_content_sha256": "<64 hex>"
}
```

`report_preaccept_content_sha256` is a stable hash of the report excluding only `acceptance`, `manual_review`, and `acoustic_evidence`. Consequently, changing line timing, textual coverage, raw WhisperX diagnostics, corrections, or stem timing invalidates it. The signer also records the physical pending report file SHA before overwriting it.

On acceptance, `acceptance.evidence_content_sha256` separately hashes the stored acoustic or listening evidence. Editing a reviewer, note, score, threshold, model, or evidence row after sign-off therefore invalidates the acceptance even though those evidence blocks are intentionally excluded from the preaccept hash.

## Singing acoustic evidence schema 1

The evidence producer must copy the required binding exactly. A minimal valid per-line payload is:

```json
{
  "schema_version": 1,
  "kind": "mv_singing_alignment_acoustic_evidence",
  "model": {
    "name": "<singing/phoneme alignment model>",
    "version": "<immutable version or model digest>"
  },
  "singing_specific": true,
  "calibrated": true,
  "acceptance_eligible": true,
  "metric": "<calibrated metric name>",
  "threshold": 0.9,
  "confidence": 0.95,
  "status": "pass",
  "binding": {
    "master": {"path": "歌/song.wav", "sha256": "<64 hex>"},
    "alignment_audio": {"path": "歌/vocals.wav", "sha256": "<64 hex>"},
    "lyrics": {"path": "词/lyrics.md", "sha256": "<64 hex>"},
    "ass": {"path": "字幕/karaoke.ass", "sha256": "<64 hex>"},
    "lrc": {"path": "字幕/lyrics.lrc", "sha256": "<64 hex>"},
    "report_preaccept_content_sha256": "<64 hex>"
  },
  "per_line": [
    {"line_index": 0, "score": 0.96, "threshold": 0.9, "status": "pass"},
    {"line_index": 1, "score": 0.94, "threshold": 0.9, "status": "pass"}
  ]
}
```

`phonemes[]` may replace `per_line[]`; each phoneme row still needs a valid `line_index`, score, and passing threshold/status. Evidence must cover every 0-based lyric line. The overall and every unit score must meet its declared threshold. `acceptance_eligible=true` is an explicit producer assertion for this formal evidence artifact; anonymous model names, missing versions, uncalibrated scores, non-singing models, stale bindings, incomplete line coverage, or non-passing statuses fail closed.

The raw WhisperX char/word score block cannot be copied into this schema: it is deliberately marked `calibrated=false` and `singing_specific=false`.

## Named listening review

Listening evidence is written only by the second-step CLI:

```bash
python3 skills/mv/mv-lyric-sync/scripts/align.py <作品根> --accept-existing \
  --listening-reviewer "<person name>" \
  --listening-notes "<full line-by-line comparison and conclusion>"
```

The generated `manual_review` contains:

- a non-placeholder reviewer and non-empty notes;
- `scope=full_song_line_by_line_against_master_and_alignment_audio`;
- the complete required binding;
- gate-compatible `bound_inputs_sha256` and `bound_outputs_sha256`;
- both canonical preaccept content SHA and the physical pending report file SHA.

Changing master, stem, lyrics, ASS, LRC, or any preaccept report fact invalidates this review.

## Low-coverage corrections schema

Low textual coverage additionally requires a corrections file and complete corrected ASS/LRC. Every weak/missing lyric line needs a master-timeline correction:

```json
{
  "corrections": [
    {
      "line_index": 3,
      "start": 12.425,
      "end": 15.880,
      "reason": "vocal onset and final consonant checked against master"
    }
  ]
}
```

`line_index` is 0-based. `start` and `end` are finite master seconds with `0 <= start < end`. `low_coverage_correction.required_line_indices` records the complete required set: every missing/under-85% line, every line with missing characters when global coverage is under 90%, and both sides of raw timing conflicts. The corrected ASS must contain at least one `Dialogue:` event per lyric line, and the corrected LRC at least one timed row per lyric line. The report keeps the original text coverage metric while using corrected master timings for affected `lines[]`; the correction packet binds the installed ASS/LRC hashes. Corrections do not replace formal acoustic/listening acceptance.

## Stem-to-master timing schema

When `audio != master_song`, `stem_master_timing` must be `status=pass` through one of:

- `automatic_exact_content_hash`;
- `automatic_ffmpeg_rms_envelope_correlation`, with early/middle/late window scores, a minimum-correlation threshold, estimated offset, and drift within threshold;
- `named_offset_drift_declaration`, with reviewer, notes, explicit offset, and explicit drift.

The mapping convention is:

```text
master_time = stem_time + offset_seconds
              + drift_seconds * (stem_time / stem_duration)
```

Both master and stem path/SHA are embedded in `stem_master_timing.bindings`. Decode failure, insufficient correlation, a search-edge match, excessive drift, incomplete named declaration, or stale hashes blocks generation/signoff.
