"""규칙 검사기 C-05: R1 결정론적 검사 (BR-01, BR-02).

2026-09-28 개정(사이클 2): 데이터셋마다 페르소나가 다르므로 설정 페르소나와의 비교는 하지 않는다.
초안의 instruction.persona 를 그 건의 기준으로 삼아 아키타입 템플릿 일치만 검사한다.
"""

from __future__ import annotations

import re

from .config import AppConfig
from .domain import Instruction, InstructionCheck

PARTICLES = ("가", "이", "은", "는", "을", "를")
PLACEHOLDER = "(Persona)"
PHONE_RE = re.compile(r"(?<!\d)(?:\d{2,4}-\d{3,4}-\d{4}|\d{3,4}-\d{4})(?!\d)")
# 두 방향을 붙인 표현 (예: 앞 왼쪽, 뒤 오른쪽, 왼쪽 앞) → 한 방향으로 고쳐야 한다 (2026-09-30 검수자 피드백)
DIRECTION_RE = re.compile(r"(?:앞|뒤)\s?(?:왼|오른)쪽|(?:왼|오른)쪽\s?(?:앞|뒤)쪽?")


def subject_particle(word: str) -> str:
    """주격 조사: 마지막 글자에 받침이 있으면 '이', 없으면 '가'. 한글이 아니면 '가'."""
    w = (word or "").strip()
    if not w:
        return "가"
    ch = w[-1]
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        return "이" if (code - 0xAC00) % 28 else "가"
    return "가"


def build_task(template: str, persona: str) -> str:
    """템플릿의 (Persona) 를 '페르소나+조사' 로 치환한 task 문장."""
    p = (persona or "").strip()
    return template.replace(PLACEHOLDER, p + subject_particle(p), 1)


def correct_instruction(instruction: Instruction, suggested: str, config: AppConfig) -> Instruction | None:
    """제안 아키타입이 6종 중 하나이고 현재와 다르면 정정된 Instruction 을 반환, 아니면 None (사이클 3 D4)."""
    s = (suggested or "").strip()
    template = config.archetype_templates.get(s)
    if template is None or s == instruction.archetype.strip():
        return None
    return Instruction(archetype=s, persona=instruction.persona, task=build_task(template, instruction.persona))


def find_phone_numbers(text: str) -> list[str]:
    return PHONE_RE.findall(text or "")


def find_compound_directions(text: str) -> list[str]:
    """'앞 왼쪽' 같은 두 방향 결합 표현을 등장 순서대로 (중복 제거)."""
    out: list[str] = []
    for m in DIRECTION_RE.finditer(text or ""):
        if m.group(0) not in out:
            out.append(m.group(0))
    return out


def strip_phone_numbers(text: str) -> str:
    out = PHONE_RE.sub("", text or "")
    return re.sub(r"[ \t]{2,}", " ", out).replace(" .", ".").strip()


def _norm(s: str | None) -> str:
    return re.sub(r"\s+", "", s or "")


def expected_task_pattern(template: str, persona: str) -> re.Pattern[str]:
    """템플릿의 (Persona) 를 페르소나로 치환한 문장. 공백 무시, 페르소나 직후 조사 선택 허용."""
    body = template.replace(PLACEHOLDER, "", 1)
    return re.compile(
        "^" + re.escape(_norm(persona)) + "(?:" + "|".join(PARTICLES) + ")?" + re.escape(_norm(body)) + "$"
    )


def check(instruction: Instruction, config: AppConfig) -> InstructionCheck:
    details: list[str] = []
    template = config.archetype_templates.get(instruction.archetype.strip())
    archetype_known = template is not None
    if not archetype_known:
        details.append(
            f"archetype '{instruction.archetype}' 은 정의된 6종({', '.join(config.archetype_templates)})에 없습니다"
        )
    if not instruction.persona.strip():
        details.append("persona 가 비어 있습니다")

    task_ok = False
    if archetype_known:
        task_ok = any(
            expected_task_pattern(t, instruction.persona).fullmatch(_norm(instruction.task)) is not None
            for t in config.templates_for(instruction.archetype.strip())
        )
        if not task_ok:
            expected = template.replace(PLACEHOLDER, instruction.persona + "가", 1)
            details.append(f"task 가 '{instruction.archetype}' 템플릿과 다릅니다. 기대: {expected}")

    return InstructionCheck(
        archetype_known=archetype_known,
        task_matches_template=task_ok,
        persona_matches_config=True,  # 하위 호환 필드. 데이터셋별 페르소나는 초안 값을 기준으로 한다
        mismatch_details=details,
    )
