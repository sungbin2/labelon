"""판정 단계 C-07: RuleChecker → 모델 판정 → 스키마 보정 → 점수 → 불가 규칙 → needs_revision.

사이클 3(검수 가이드): 아키타입 제안, Task·QA 방향, 가전조작 조작부, CoT 역할, QA↔CoT3, 전화번호, 수정량 과다.
"""

from __future__ import annotations

import logging
from typing import Any

from . import rules
from .config import AppConfig
from .domain import (
    ArchetypeSuggestion,
    Draft,
    FactVerdict,
    FieldVerdict,
    ImagePaths,
    ImpossibleFlags,
    JudgeResult,
    PersonaTaskFit,
    SourceItem,
    TextIssue,
    Verdict,
)
from .model.base import ModelClient

log = logging.getLogger(__name__)

FACT_WEIGHT = {Verdict.TRUE: 1.0, Verdict.UNKNOWN: 0.5, Verdict.FALSE: 0.0}
APPLIANCE_ARCHETYPE = "가전조작"


def compute_score(facts: list[FactVerdict], fields: list[FieldVerdict]) -> int:
    """BR-10~12: Facts 60(개수에 따라 균등 배분) + Scene 20 + CoT·대화 20."""
    fact_score = (60 * sum(FACT_WEIGHT[f.verdict] for f in facts) / len(facts)) if facts else 60
    scene = next((f for f in fields if f.field == "scene"), None)
    scene_score = 20 if (scene and scene.consistent) else 0
    others = [f for f in fields if f.field != "scene"]
    if others:
        other_score = round(20 * sum(1 for f in others if f.consistent) / len(others))
    else:
        other_score = 20
    return int(round(fact_score + scene_score + other_score))


def normalize_raw(
    raw: dict[str, Any], draft: Draft, warnings: list[str]
) -> tuple[list[FactVerdict], list[FieldVerdict], PersonaTaskFit, list[str], str, dict[str, Any]]:
    """BR-13: 누락은 UNKNOWN / consistent=False 로 채우고 경고. 사이클 3 추가 항목은 extras 로 반환."""
    facts: list[FactVerdict] = []
    by_idx = {int(f.get("index", i)): f for i, f in enumerate(raw.get("facts") or []) if isinstance(f, dict)}
    for i in range(len(draft.facts)):
        f = by_idx.get(i)
        if f is None:
            warnings.append(f"모델 판정에 fact {i + 1} 누락 → UNKNOWN 처리")
            facts.append(FactVerdict(index=i, verdict=Verdict.UNKNOWN, evidence="판정 누락"))
            continue
        v = str(f.get("verdict", "UNKNOWN")).upper()
        verdict = Verdict(v) if v in Verdict.__members__ else Verdict.UNKNOWN
        facts.append(FactVerdict(index=i, verdict=verdict, evidence=str(f.get("evidence", ""))))

    fields: list[FieldVerdict] = []
    scene = raw.get("scene") or {}
    if not isinstance(scene, dict) or "consistent" not in scene:
        warnings.append("모델 판정에 scene 누락 → 불일치 처리")
        scene = {"consistent": False, "note": "판정 누락"}
    fields.append(FieldVerdict(field="scene", consistent=bool(scene.get("consistent")), note=str(scene.get("note", ""))))

    cot_by = {str(c.get("field")): c for c in (raw.get("cot") or []) if isinstance(c, dict)}
    for name in ("cot1", "cot2", "cot3"):
        c = cot_by.get(name)
        if c is None:
            warnings.append(f"모델 판정에 {name} 누락 → 불일치 처리")
            c = {"consistent": False, "note": "판정 누락"}
        fields.append(FieldVerdict(field=name, consistent=bool(c.get("consistent")), note=str(c.get("note", "")),
                                   role_fits=bool(c.get("role_fits", True))))

    turn_by = {int(t.get("turn", 0)): t for t in (raw.get("dialogue_turns") or []) if isinstance(t, dict)}
    for t in draft.dialogue.active_turns():
        d = turn_by.get(t.turn)
        if d is None:
            warnings.append(f"모델 판정에 turn {t.turn} 누락 → 불일치 처리")
            d = {"consistent": False, "note": "판정 누락"}
        fields.append(FieldVerdict(field=f"turn_{t.turn}", consistent=bool(d.get("consistent")), note=str(d.get("note", "")),
                                   beyond_cot3=bool(d.get("beyond_cot3", False))))

    fit_raw = raw.get("persona_task_fit") or {}
    fit = PersonaTaskFit(
        cot_fits=bool(fit_raw.get("cot_fits", True)), dialogue_fits=bool(fit_raw.get("dialogue_fits", True)),
        note=str(fit_raw.get("note", "")),
    )
    missing = [str(x) for x in (raw.get("missing_in_image") or [])]
    reason = str(raw.get("impossible_reason_suggestion") or "")

    sug_raw = raw.get("archetype_suggestion") or {}
    acv = raw.get("appliance_controls_visible")
    flags_raw = raw.get("impossible_flags") or {}
    issues: list[TextIssue] = []
    for x in raw.get("text_issues") or []:
        if isinstance(x, dict) and x.get("field") and x.get("kind") in ("typo", "speculation", "number", "direction"):
            issues.append(TextIssue(field=str(x["field"]), kind=str(x["kind"]), wrong=str(x.get("wrong") or ""), correct=str(x.get("correct") or "")))
    extras = {
        "qa_matches_cot3": bool(raw.get("qa_matches_cot3", True)),
        "task_qa_direction_match": bool(raw.get("task_qa_direction_match", True)),
        "appliance_controls_visible": (bool(acv) if isinstance(acv, bool) else None),
        "archetype_suggestion": ArchetypeSuggestion(
            fits=bool(sug_raw.get("fits", True)), suggested=str(sug_raw.get("suggested") or "").strip(),
            reason=str(sug_raw.get("reason") or ""),
        ),
        # 사이클 4: 누락 시 "문제 없음"
        "archetype_fits_environment": bool(raw.get("archetype_fits_environment", True)),
        "environment_note": str(raw.get("environment_note") or ""),
        "impossible_flags": ImpossibleFlags(
            core_error_propagated=bool(flags_raw.get("core_error_propagated", False)),
            persona_infeasible_guidance=bool(flags_raw.get("persona_infeasible_guidance", False)),
            unsafe_guidance=bool(flags_raw.get("unsafe_guidance", False)),
            note=str(flags_raw.get("note") or ""),
        ),
        "text_issues": issues,
    }
    return facts, fields, fit, missing, reason, extras


def _text_fields(draft: Draft) -> list[tuple[str, str]]:
    out = [("scene", draft.scene), *[(f"fact_{i + 1}", f) for i, f in enumerate(draft.facts)],
           ("cot1", draft.cot1), ("cot2", draft.cot2), ("cot3", draft.cot3)]
    for t in draft.dialogue.turns:
        if not t.is_empty():
            out.append((f"turn_{t.turn}_assistant", t.assistant))
    return out


def detect_compound_directions(draft: Draft) -> list[TextIssue]:
    """'앞 왼쪽' 등 두 방향 결합 표현을 필드별로 text_issues(direction) 로 (사이클 5, 결정론)."""
    return [TextIssue(field=f, kind="direction", wrong=w, correct="")
            for f, tx in _text_fields(draft) for w in rules.find_compound_directions(tx)]


def merge_text_issues(detected: list[TextIssue], reported: list[TextIssue]) -> list[TextIssue]:
    """도구 검출을 앞에, 모델 보고는 같은 (field, wrong) 이 없을 때만 뒤에."""
    seen = {(d.field, d.wrong) for d in detected}
    return detected + [r for r in reported if (r.field, r.wrong) not in seen]


def detect_phone_numbers(draft: Draft) -> list[str]:
    texts = [draft.scene, *draft.facts, draft.cot1, draft.cot2, draft.cot3]
    for t in draft.dialogue.turns:
        texts += [t.user, t.assistant]
    found: list[str] = []
    for tx in texts:
        for p in rules.find_phone_numbers(tx):
            if p not in found:
                found.append(p)
    return found


class JudgeStage:
    def __init__(self, config: AppConfig, client: ModelClient) -> None:
        self.config = config
        self.client = client

    async def run(self, images: ImagePaths, item: SourceItem, draft: Draft, warnings: list[str] | None = None) -> JudgeResult:
        warnings = warnings if warnings is not None else []
        cfg = self.config
        ic = rules.check(draft.instruction, cfg)
        raw, usage = await self.client.judge(images.resized, item, draft)  # ModelCallError 는 상위로
        facts, fields, fit, missing, reason, ex = normalize_raw(raw, draft, warnings)
        score = compute_score(facts, fields)

        # 아키타입 정정 가능 여부 (가이드 D). 유효하지 않은 제안은 경고로만
        sug: ArchetypeSuggestion = ex["archetype_suggestion"]
        correction = None
        env_ok: bool = ex["archetype_fits_environment"]
        if not env_ok and not sug.fits:
            # 사이클 4: 환경 충돌이면 불가가 우선, 정정 미적용
            warnings.append(f"아키타입이 이미지 환경과 맞지 않아 정정 제안 '{sug.suggested}' 을 적용하지 않습니다")
            sug = ArchetypeSuggestion(fits=True, suggested="", reason=sug.reason)
        if not sug.fits:
            correction = rules.correct_instruction(draft.instruction, sug.suggested, cfg)
            if correction is None:
                if sug.suggested:
                    warnings.append(f"모델의 아키타입 제안 '{sug.suggested}' 은 적용할 수 없어 무시합니다 ({sug.reason})")
                sug = ArchetypeSuggestion(fits=True, suggested="", reason=sug.reason)

        phones = detect_phone_numbers(draft) if cfg.text_rules.remove_phone_numbers else []
        ex["text_issues"] = merge_text_issues(detect_compound_directions(draft), ex["text_issues"])
        if phones:
            warnings.append("전화번호가 포함되어 있습니다(삭제 대상): " + ", ".join(phones))

        false_n = sum(1 for f in facts if f.verdict is Verdict.FALSE)
        inconsistent_n = sum(1 for f in fields if not f.consistent)

        # 불가 후보 규칙 (D2)
        reasons: list[str] = []
        if score <= cfg.threshold:
            reasons.append(f"정합성 점수 {score} (임계값 {cfg.threshold} 이하)")
        if not ex["task_qa_direction_match"] and correction is None:
            reasons.append("Task 가 요구하는 방향과 QA 내용이 다름")
        if draft.instruction.archetype.strip() == APPLIANCE_ARCHETYPE and ex["appliance_controls_visible"] is False:
            reasons.append("가전조작 아키타입이지만 사진에 조작부가 보이지 않음")
        if false_n >= cfg.impossible_rules.max_false_facts:
            reasons.append(f"거짓 팩트 {false_n}개 (수정량 과다)")
        if inconsistent_n >= cfg.impossible_rules.max_inconsistent_fields:
            reasons.append(f"불일치 필드 {inconsistent_n}개 (수정량 과다)")
        # 사이클 4 (가이드 불가 예시)
        flags: ImpossibleFlags = ex["impossible_flags"]
        tail = f": {flags.note}" if flags.note else ""
        if not env_ok:
            reasons.append("아키타입이 이미지 환경과 맞지 않음" + (f": {ex['environment_note']}" if ex["environment_note"] else ""))
        if flags.core_error_propagated:
            reasons.append("핵심 물체·팩트 오인식이 CoT·QA 전반에 전파됨" + tail)
        if flags.persona_infeasible_guidance:
            reasons.append("페르소나가 수행할 수 없는 확인·행동을 요구함" + tail)
        if flags.unsafe_guidance:
            reasons.append("위험 행위를 권고함" + tail)
        impossible = bool(reasons)
        if impossible and not reason:
            reason = "; ".join(reasons)

        # 수정 필요 (D3)
        # 사이클 10: revise_impossible=True 면 불가 후보라도 수정안을 만든다(사람이 고쳐 승인할 수 있도록)
        needs_revision = (cfg.revision_rules.revise_impossible or not impossible) and (
            false_n > 0 or inconsistent_n > 0 or not fit.cot_fits or not fit.dialogue_fits
            or correction is not None or not ex["qa_matches_cot3"]
            or any(f.field.startswith("cot") and not f.role_fits for f in fields)
            or any(f.beyond_cot3 for f in fields) or bool(phones) or bool(ex["text_issues"])
        )
        log.info("judge score=%d impossible=%s(%s) needs_revision=%s correction=%s", score, impossible, "; ".join(reasons), needs_revision,
                 correction.archetype if correction else None)
        return JudgeResult(
            instruction_check=ic, fact_verdicts=facts, field_verdicts=fields, persona_task_fit=fit,
            missing_in_image=missing, impossible_reason_suggestion=reason, consistency_score=score,
            impossible_candidate=impossible, needs_revision=needs_revision, model_usage=usage, raw=raw,
            qa_matches_cot3=ex["qa_matches_cot3"], task_qa_direction_match=ex["task_qa_direction_match"],
            appliance_controls_visible=ex["appliance_controls_visible"], archetype_suggestion=sug,
            phone_numbers=phones, impossible_reasons=reasons,
            archetype_fits_environment=env_ok, environment_note=ex["environment_note"],
            impossible_flags=flags, text_issues=ex["text_issues"],
        )
