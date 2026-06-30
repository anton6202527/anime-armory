#!/usr/bin/env python3
"""现场摩擦信号采集 —— "自我优化"闭环的生产者原语。

任何 n2d skill 在跑生产时撞到「这个 skill 该改」的瞬间——缺陷 / 不得不绕的
workaround / 与基准对不上的产出 / 意外——调一行 `log_friction()`，往**作品根下**
`生产数据/优化信号.jsonl` 追加一条结构化信号。消费端是 n2d-review 流程自审
(`self_audit.py --work <作品根>`)，**只读不写**，把积压信号并进「差距清单」。

设计法（与 docs/skill-design-principles.md 一致）：
  * 只写日志、不改任何生产逻辑；任何异常一律静默吞掉并返回 None——采集**永远**
    不能拖垮正在跑的生产（C4 降级不加锁）。
  * 信号落在 `创作区/.../生产数据/`（per-work 生产数据），不是 `skills/` 下的自审
    报告——保住 n2d-review mode② "不归档自审报告" 的宪法立场；review 端只 READ。
  * 纯 stdlib，刻意不 import 其它 _lib 模块，可被任意 skill 一行引入。
"""

from __future__ import annotations

import datetime as dt
import json
import os
from typing import Any, Dict, List, Mapping, Optional

try:  # POSIX flock；非 POSIX 兜底为目录锁
    import fcntl
except ImportError:  # pragma: no cover - 非 POSIX
    fcntl = None  # type: ignore[assignment]


FRICTION_KIND = "n2d_friction_signal"
FRICTION_VERSION = 1
FRICTION_FILENAME = "优化信号.jsonl"
PRODUCTION_DIRNAME = "生产数据"

# 信号种类（permissive：未知值不拒绝，只在消费端归并时如实分组——降级不加锁）。
VALID_KINDS = ("defect", "workaround", "mismatch", "surprise", "suggestion")
# 严重度与 self_audit 的 finding sev 同表，便于消费端直接透传。
VALID_SEVERITIES = ("info", "warn", "block")


def friction_dir(work_root: str) -> str:
    return os.path.join(str(work_root).rstrip("/"), PRODUCTION_DIRNAME)


def friction_log_path(work_root: str) -> str:
    return os.path.join(friction_dir(work_root), FRICTION_FILENAME)


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _append_jsonl(path: str, record: Mapping[str, Any]) -> None:
    """flock 串行化的单行追加；O_APPEND 保证不同进程的整行不交错。"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o644)
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, line.encode("utf-8"))
    finally:
        if fcntl is not None:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:  # pragma: no cover - 防御
                pass
        os.close(fd)


def log_friction(
    work_root: str,
    skill: str,
    what: str,
    *,
    kind: str = "surprise",
    stage: str = "",
    episode: str = "",
    evidence: str = "",
    proposed: str = "",
    severity: str = "info",
    extra: Optional[Mapping[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """记一条「该 skill 该改」的现场信号。失败必静默返回 None，绝不抛。

    参数（除前三个外都可省）：
      work_root  作品根（`创作区/<line>/<剧名>/`）——信号落它下面的生产数据目录。
      skill      撞到问题的 skill 名（消费端的「该改哪个 skill」=loc）。
      what       一句话现象（必填，空则不记）。
      kind       defect/workaround/mismatch/surprise/suggestion（未知值如实保留）。
      stage      阶段/镜号等更细定位（「哪段」）。
      episode    第N集。
      evidence   证据路径/镜号/链接。
      proposed   建议改法（消费端的 suggestion）。
      severity   info/warn/block（透传给 self_audit finding 的 sev）。
      extra      附加字段（浅合并进记录，键名不覆盖固定字段）。
    """
    try:
        what = str(what or "").strip()
        skill = str(skill or "").strip()
        if not work_root or not skill or not what:
            return None
        sev = severity if severity in VALID_SEVERITIES else "info"
        record: Dict[str, Any] = {
            "kind": FRICTION_KIND,
            "version": FRICTION_VERSION,
            "ts": _now_iso(),
            "skill": skill,
            "signal_kind": str(kind or "surprise").strip() or "surprise",
            "severity": sev,
            "what": what,
            "stage": str(stage or "").strip(),
            "episode": str(episode or "").strip(),
            "evidence": str(evidence or "").strip(),
            "proposed": str(proposed or "").strip(),
        }
        if extra:
            for k, v in dict(extra).items():
                record.setdefault(str(k), v)
        _append_jsonl(friction_log_path(work_root), record)
        return record
    except Exception:  # noqa: BLE001 - 采集绝不拖垮生产
        return None


def read_friction(work_root: str) -> List[Dict[str, Any]]:
    """读回某作品的所有摩擦信号；坏行跳过、文件不存在返回 []（容错优先）。"""
    path = friction_log_path(work_root)
    out: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict) and rec.get("kind") == FRICTION_KIND:
                    out.append(rec)
    except FileNotFoundError:
        return []
    except OSError:
        return []
    return out


_SEV_ORDER = {"info": 0, "warn": 1, "block": 2}


def summarize_friction(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """把信号按 (skill, signal_kind) 归并成簇，供消费端逐簇产「差距行」。

    每簇取最高严重度、最近一条的 what/proposed/ts 作代表，附计数与样本。
    """
    clusters: Dict[tuple, Dict[str, Any]] = {}
    for rec in records:
        skill = str(rec.get("skill") or "?")
        sig = str(rec.get("signal_kind") or "surprise")
        key = (skill, sig)
        c = clusters.get(key)
        if c is None:
            c = {
                "skill": skill,
                "signal_kind": sig,
                "count": 0,
                "severity": "info",
                "latest_ts": "",
                "latest_what": "",
                "latest_proposed": "",
                "evidence": [],
            }
            clusters[key] = c
        c["count"] += 1
        sev = str(rec.get("severity") or "info")
        if _SEV_ORDER.get(sev, 0) > _SEV_ORDER.get(c["severity"], 0):
            c["severity"] = sev
        ts = str(rec.get("ts") or "")
        if ts >= c["latest_ts"]:  # ISO8601 字典序=时序
            c["latest_ts"] = ts
            c["latest_what"] = str(rec.get("what") or "")
            c["latest_proposed"] = str(rec.get("proposed") or "")
        ev = str(rec.get("evidence") or "").strip()
        if ev and ev not in c["evidence"]:
            c["evidence"].append(ev)
    ordered = sorted(
        clusters.values(),
        key=lambda c: (-_SEV_ORDER.get(c["severity"], 0), -c["count"], c["skill"]),
    )
    return {
        "total": len(records),
        "clusters": ordered,
        "by_severity": {
            sev: sum(1 for r in records if str(r.get("severity") or "info") == sev)
            for sev in VALID_SEVERITIES
        },
    }
