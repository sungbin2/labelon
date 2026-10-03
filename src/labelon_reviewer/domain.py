"""도메인 엔티티와 예외 (functional-design/domain-entities.md)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

DEFAULT_FACT_COUNT = 5  # 초안마다 다를 수 있다(5~6개 관찰). 실제 개수는 초안을 따른다
MAX_TURNS = 6


def utcnow() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------- 예외
class LabelonReviewerError(Exception):
    """도구 공통 예외."""


class LoginRequired(LabelonReviewerError):
    pass


class PageStructureError(LabelonReviewerError):
    pass


class NoJobAvailable(LabelonReviewerError):
    def __init__(self, page_kind: str, message: str = ""):
        super().__init__(message or f"가져올 작업이 없습니다 (페이지: {page_kind})")
        self.page_kind = page_kind


class ModelCallError(LabelonReviewerError):
    pass


class ModelRefused(ModelCallError):
    """모델이 안전 분류기 등으로 응답을 거부(stop_reason=refusal). 같은 모델로 재시도하지 않는다."""


class SubmitError(LabelonReviewerError):
    pass


class ItemExpired(LabelonReviewerError):
    pass


class IllegalTransition(LabelonReviewerError):
    pass


class ConfigError(LabelonReviewerError):
    def __init__(self, field: str, reason: str):
        super().__init__(f"설정 오류 [{field}]: {reason}")
        self.field = field
        self.reason = reason


# ---------------------------------------------------------------- 원천
class RelatedQA(BaseModel):
    question: str = ""
    answer: str = ""
    id: int | None = None


class SourceItem(BaseModel):
    job_id: int
    dataset_id: int
    dataset_name: str = ""
    file_id: int
    job_vqa_id: int | None = None
    annotator_id: int | None = None
    image_url: str = ""
    org_file_name: str = ""
    file_name: str = ""
    category: str = ""
    weather: str = ""
    detected_object: str = ""
    related_qa: list[RelatedQA] = Field(default_factory=list)
    job_date: datetime
    job_status: str = ""
    de_identification_status: str = ""


class DatasetInfo(BaseModel):
    """LabelOn 프로젝트 홈 "진행중인 작업" 카드 1개."""

    dataset_id: int
    job_type: str = ""  # 예: AH25 (UC-LE)
    project_name: str = ""
    project_code: str = ""
    dataset_name: str = ""
    credit: int | None = None
    grade: str = ""

    @property
    def supported(self) -> bool:
        return self.job_type == "AH25"


# ---------------------------------------------------------------- 초안
class Instruction(BaseModel):
    archetype: str = ""
    persona: str = ""
    task: str = ""


class DialogueTurn(BaseModel):
    turn: int
    user: str = ""
    assistant: str = ""

    def is_empty(self) -> bool:
        return not (self.user.strip() or self.assistant.strip())


class Dialogue(BaseModel):
    context: dict[str, Any] = Field(default_factory=dict)
    turns: list[DialogueTurn] = Field(default_factory=list)

    def active_turns(self) -> list[DialogueTurn]:
        return [t for t in self.turns if not t.is_empty()]

    def turn(self, n: int) -> DialogueTurn | None:
        for t in self.turns:
            if t.turn == n:
                return t
        return None


class Draft(BaseModel):
    instruction: Instruction = Field(default_factory=Instruction)
    scene: str = ""
    facts: list[str] = Field(default_factory=list)
    cot1: str = ""
    cot2: str = ""
    cot3: str = ""
    dialogue: Dialogue = Field(default_factory=Dialogue)

    @field_validator("facts", mode="before")
    @classmethod
    def _clean_facts(cls, v: Any) -> list[str]:
        return [str(x) if x is not None else "" for x in (v or [])]

    @property
    def fact_count(self) -> int:
        return len(self.facts)

    # 필드 주소 체계: scene, fact_1..fact_5, cot1..cot3, turn_N_assistant
    def get_field(self, name: str) -> str:
        if name in ("archetype", "persona", "task"):
            return getattr(self.instruction, name)
        if name == "scene":
            return self.scene
        if name.startswith("fact_"):
            return self.facts[int(name[5:]) - 1]
        if name in ("cot1", "cot2", "cot3"):
            return getattr(self, name)
        if name.startswith("turn_") and name.endswith("_assistant"):
            t = self.dialogue.turn(int(name.split("_")[1]))
            return t.assistant if t else ""
        if name.startswith("turn_") and name.endswith("_user"):  # 사이클 6: 질문도 편집
            t = self.dialogue.turn(int(name.split("_")[1]))
            return t.user if t else ""
        raise KeyError(name)

    def set_field(self, name: str, value: str) -> None:
        if name in ("archetype", "persona", "task"):  # 사이클 7: Instruction 도 사람이 편집
            setattr(self.instruction, name, value)
        elif name == "scene":
            self.scene = value
        elif name.startswith("fact_"):
            self.facts[int(name[5:]) - 1] = value
        elif name in ("cot1", "cot2", "cot3"):
            setattr(self, name, value)
        elif name.startswith("turn_") and name.endswith("_assistant"):
            t = self.dialogue.turn(int(name.split("_")[1]))
            if t is None:
                raise KeyError(name)
            t.assistant = value
        elif name.startswith("turn_") and name.endswith("_user"):
            t = self.dialogue.turn(int(name.split("_")[1]))
            if t is None:
                raise KeyError(name)
            t.user = value
        else:
            raise KeyError(name)

    def editable_fields(self) -> list[str]:
        names = ["archetype", "persona", "task", "scene"] + [f"fact_{i}" for i in range(1, len(self.facts) + 1)] + ["cot1", "cot2", "cot3"]
        for t in self.dialogue.active_turns():
            names += [f"turn_{t.turn}_user", f"turn_{t.turn}_assistant"]
        return names


# ---------------------------------------------------------------- 판정
class Verdict(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class FactVerdict(BaseModel):
    index: int
    verdict: Verdict
    evidence: str = ""


class FieldVerdict(BaseModel):
    field: str
    consistent: bool
    note: str = ""
    role_fits: bool = True  # cot1~3: 단계 역할(장소·상황 / 위험·주의 / 행동·답변)에 맞는가 (사이클 3)
    beyond_cot3: bool = False  # turn_n: CoT 3단계 범위를 넘는 추론(사진에 없는 인물·상황) (사이클 3)


class PersonaTaskFit(BaseModel):
    cot_fits: bool = True
    dialogue_fits: bool = True
    note: str = ""


class ArchetypeSuggestion(BaseModel):
    """판정 모델의 아키타입 적합성 판단 (사이클 3, 가이드 D)."""

    fits: bool = True
    suggested: str = ""
    reason: str = ""


class ImpossibleFlags(BaseModel):
    """사이클 4 (가이드 불가 예시 1~4): 모델이 판정하는 불가 사유 플래그."""

    core_error_propagated: bool = False  # 핵심 물체·팩트 오인식이 CoT·QA 전반에 전파
    persona_infeasible_guidance: bool = False  # 페르소나가 수행할 수 없는 확인·행동 요구
    unsafe_guidance: bool = False  # 위험 행위 권고(무단횡단 등)
    note: str = ""

    def any(self) -> bool:
        return self.core_error_propagated or self.persona_infeasible_guidance or self.unsafe_guidance


class TextIssue(BaseModel):
    """사이클 4 (가이드 오류 예시 1·3, 중점 사항): 오탈자·추측·숫자 표기 오류."""

    field: str
    kind: str  # typo | speculation | number | direction(두 방향 결합, 사이클 5)
    wrong: str = ""
    correct: str = ""


class InstructionCheck(BaseModel):
    archetype_known: bool
    task_matches_template: bool
    persona_matches_config: bool
    mismatch_details: list[str] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.archetype_known and self.task_matches_template and self.persona_matches_config


class ModelUsage(BaseModel):
    stage: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    num_turns: int = 0


class JudgeResult(BaseModel):
    instruction_check: InstructionCheck
    fact_verdicts: list[FactVerdict]
    field_verdicts: list[FieldVerdict]
    persona_task_fit: PersonaTaskFit = Field(default_factory=PersonaTaskFit)
    missing_in_image: list[str] = Field(default_factory=list)
    impossible_reason_suggestion: str = ""
    consistency_score: int
    impossible_candidate: bool
    needs_revision: bool
    model_usage: ModelUsage | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
    # 사이클 3 (검수 가이드)
    qa_matches_cot3: bool = True
    task_qa_direction_match: bool = True
    appliance_controls_visible: bool | None = None
    archetype_suggestion: ArchetypeSuggestion = Field(default_factory=ArchetypeSuggestion)
    phone_numbers: list[str] = Field(default_factory=list)
    impossible_reasons: list[str] = Field(default_factory=list)
    # 사이클 4 (가이드 이미지 슬라이드)
    archetype_fits_environment: bool = True
    environment_note: str = ""
    impossible_flags: ImpossibleFlags = Field(default_factory=ImpossibleFlags)
    text_issues: list[TextIssue] = Field(default_factory=list)

    def archetype_correction(self) -> str | None:
        """적용 가능한 아키타입 정정값 (없으면 None). 유효성(6종·현재와 다름)은 JudgeStage 가 확인해 채운다."""
        s = self.archetype_suggestion
        return s.suggested if (not s.fits and s.suggested) else None


class RevisedDraft(BaseModel):
    draft: Draft
    change_notes: list[dict[str, str]] = Field(default_factory=list)
    skipped: bool = False
    model_usage: ModelUsage | None = None
    instruction_changed: bool = False  # 사이클 3: 아키타입·task 정정 적용
    dropped_turns: list[int] = Field(default_factory=list)  # 사이클 3: 삭제된 원래 턴 번호


class FinalDraft(Draft):
    edited_by_user: bool = False
    updated_at: datetime = Field(default_factory=utcnow)

    @classmethod
    def from_draft(cls, d: Draft, edited: bool = False) -> FinalDraft:
        return cls(**d.model_dump(), edited_by_user=edited, updated_at=utcnow())

    def as_draft(self) -> Draft:
        return Draft(**{k: v for k, v in self.model_dump().items() if k in Draft.model_fields})


# ---------------------------------------------------------------- 제출
class SubmissionKind(str, Enum):
    APPROVE = "APPROVE"
    IMPOSSIBLE = "IMPOSSIBLE"
    SKIP = "SKIP"


class SubmissionRecord(BaseModel):
    kind: SubmissionKind
    payload_snapshot: dict[str, Any] = Field(default_factory=dict)
    response_message: str = ""
    success: bool
    submitted_at: datetime = Field(default_factory=utcnow)
    error: str | None = None


# ---------------------------------------------------------------- diff
class DiffOp(str, Enum):
    EQUAL = "EQUAL"
    INSERT = "INSERT"
    DELETE = "DELETE"
    REPLACE = "REPLACE"


class DiffSegment(BaseModel):
    op: DiffOp
    base_text: str = ""
    other_text: str = ""


class FieldDiff(BaseModel):
    field: str
    changed: bool
    segments: list[DiffSegment] = Field(default_factory=list)


# ---------------------------------------------------------------- 상태
class ReviewState(str, Enum):
    READY = "READY"
    FETCHING = "FETCHING"
    JUDGING = "JUDGING"
    REVISING = "REVISING"
    REVIEW = "REVIEW"
    SUBMITTING = "SUBMITTING"
    DONE = "DONE"
    ERROR = "ERROR"
    EXPIRED = "EXPIRED"


class ReviewEvent(str, Enum):
    FETCH_STARTED = "FETCH_STARTED"
    PARSED = "PARSED"
    JUDGED = "JUDGED"
    REVISED = "REVISED"
    REVIEW_READY = "REVIEW_READY"
    EDITED = "EDITED"
    REVERTED = "REVERTED"
    SUBMIT_STARTED = "SUBMIT_STARTED"
    SUBMITTED = "SUBMITTED"
    SUBMIT_FAILED = "SUBMIT_FAILED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"
    RESET = "RESET"
    REANALYZE = "REANALYZE"  # 사이클 7: 검토 대기 건을 다시 판정·수정


class ImagePaths(BaseModel):
    original: str
    resized: str


class ReviewItem(BaseModel):
    item_id: int | None = None
    state: ReviewState = ReviewState.READY
    source: SourceItem | None = None
    draft: Draft | None = None
    judge: JudgeResult | None = None
    revised: RevisedDraft | None = None
    final: FinalDraft | None = None
    diffs: list[FieldDiff] = Field(default_factory=list)
    deadline: datetime | None = None
    warnings: list[str] = Field(default_factory=list)
    submission: SubmissionRecord | None = None
    image_paths: ImagePaths | None = None
    error: str | None = None
    stage_started_at: datetime = Field(default_factory=utcnow)
    login_required: bool = False
    browser_alive: bool = True

    def remaining_seconds(self, now: datetime | None = None) -> int | None:
        if self.deadline is None:
            return None
        now = now or utcnow()
        return int((self.deadline - now).total_seconds())
