"""Diff 서비스 C-09: 초안 vs 다른 Draft 의 문장 단위 차이."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from .domain import DiffOp, DiffSegment, Draft, FieldDiff

_SPLIT = re.compile(r"(?<=[.!?。])\s+|\n+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SPLIT.split(text or "") if s and s.strip()]


def _segments(base: list[str], other: list[str]) -> list[DiffSegment]:
    out: list[DiffSegment] = []
    sm = SequenceMatcher(a=base, b=other, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for s in base[i1:i2]:
                out.append(DiffSegment(op=DiffOp.EQUAL, base_text=s, other_text=s))
        elif tag == "delete":
            for s in base[i1:i2]:
                out.append(DiffSegment(op=DiffOp.DELETE, base_text=s))
        elif tag == "insert":
            for s in other[j1:j2]:
                out.append(DiffSegment(op=DiffOp.INSERT, other_text=s))
        else:  # replace
            out.append(
                DiffSegment(op=DiffOp.REPLACE, base_text=" ".join(base[i1:i2]), other_text=" ".join(other[j1:j2]))
            )
    return out


def diff_text(field: str, base: str, other: str) -> FieldDiff:
    if (base or "").strip() == (other or "").strip():
        return FieldDiff(field=field, changed=False, segments=[DiffSegment(op=DiffOp.EQUAL, base_text=base, other_text=other)])
    return FieldDiff(field=field, changed=True, segments=_segments(split_sentences(base), split_sentences(other)))


def diff(base: Draft, other: Draft) -> list[FieldDiff]:
    out: list[FieldDiff] = [
        diff_text("archetype", base.instruction.archetype, other.instruction.archetype),
        diff_text("persona", base.instruction.persona, other.instruction.persona),
        diff_text("task", base.instruction.task, other.instruction.task),
        diff_text("scene", base.scene, other.scene),
    ]
    n = max(len(base.facts), len(other.facts))
    for i in range(n):
        b = base.facts[i] if i < len(base.facts) else ""
        o = other.facts[i] if i < len(other.facts) else ""
        if b.strip() == o.strip():
            out.append(FieldDiff(field=f"fact_{i + 1}", changed=False, segments=[DiffSegment(op=DiffOp.EQUAL, base_text=b, other_text=o)]))
        else:
            out.append(FieldDiff(field=f"fact_{i + 1}", changed=True, segments=[DiffSegment(op=DiffOp.REPLACE, base_text=b, other_text=o)]))
    for name in ("cot1", "cot2", "cot3"):
        out.append(diff_text(name, getattr(base, name), getattr(other, name)))
    turns = {t.turn for t in base.dialogue.turns} | {t.turn for t in other.dialogue.turns}
    for n in sorted(turns):
        bt, ot = base.dialogue.turn(n), other.dialogue.turn(n)
        out.append(diff_text(f"turn_{n}_user", bt.user if bt else "", ot.user if ot else ""))  # 사이클 6
        out.append(diff_text(f"turn_{n}_assistant", bt.assistant if bt else "", ot.assistant if ot else ""))
    return out
