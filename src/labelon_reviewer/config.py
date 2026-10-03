"""설정 로더 C-01. config.yaml → AppConfig. 오류 시 항목명을 포함한 ConfigError."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

from .domain import ConfigError

DEFAULT_ARCHETYPE_TEMPLATES: dict[str, str] = {
    "일상지원": "(Persona) 이 주변에서 가려는 곳과 필요한 것을 찾아갈 수 있도록 주변 시설과 길이 어떻게 이어져 있는지 확인하고, 어느 쪽으로 가야 하는지와 걸리는 것을 우선 안내하세요.",  # 2026-09-30 변경 (검수자 피드백)
    "보행안전": "(Persona) 안전하게 이동할 수 있도록 진행 방향의 보행환경을 확인하고, 이동 경로의 장애물과 위험요소를 우선 안내하세요.",
    "쇼핑": "(Persona) 찾는 물건에 닿을 수 있도록 물건이 어디에 어떻게 놓여 있는지 확인하고, 손을 뻗을 방향과 걸리는 것을 우선 안내하세요.",
    "음식": "(Persona) 음식을 스스로 다룰 수 있도록 음식과 관련된 것이 어디에 있는지 확인하고, 손이 닿는 방향과 조심할 것을 우선 안내하세요.",
    "실내탐색": "(Persona) 실내를 스스로 다닐 수 있도록 공간의 구조와 가구 배치를 확인하고, 지나갈 길과 부딪힐 만한 것을 우선 안내하세요.",
    "가전조작": "(Persona) 기기를 다룰 수 있도록 가전이 어디에 있고 어느 면이 앞면인지, 보이는 조작 단서(손잡이·표시등·틈·문)가 무엇인지 짚고, 어느 쪽에서 무엇을 만지면 되는지 우선 안내하세요.",
}


# 서버에 남아 있는 옛 문장의 초안도 템플릿 일치로 인정한다 (검사 전용. 정정 Task 생성에는 쓰지 않음)
DEFAULT_LEGACY_ARCHETYPE_TEMPLATES: dict[str, list[str]] = {
    "일상지원": ["(Persona) 이 공간에서 필요한 것을 찾을 수 있도록 주변 시설과 물건이 어떻게 놓여 있는지 확인하고, 무엇이 어느 쪽에 있는지 우선 안내하세요."],
}


class ModelsConfig(BaseModel):
    judge: str = "claude-sonnet-5"
    revise: str = "claude-fable-5-1"
    # 거부(refusal) 시 1회 대체 호출할 모델. 빈 문자열이면 대체 없음
    judge_fallback: str = ""
    revise_fallback: str = "claude-sonnet-5"


class EffortConfig(BaseModel):
    judge: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    revise: Literal["low", "medium", "high", "xhigh", "max"] = "high"


class CliTimeouts(BaseModel):
    judge: int = Field(120, ge=10, le=900)
    revise: int = Field(180, ge=10, le=900)


class CliConfig(BaseModel):
    path: str = "claude"
    cwd: str = "C:/labelon-reviewer-work"
    flags_profile: Literal["basic", "system_prompt", "minimal"] = "minimal"
    max_turns: int = Field(4, ge=1, le=10)
    timeouts: CliTimeouts = Field(default_factory=CliTimeouts)


class LabelonConfig(BaseModel):
    base_url: str = "https://www.labelon.kr"
    job_time_limit_minutes: int = Field(60, ge=1)
    server_tz_offset_hours: int = 9


class ChromeConfig(BaseModel):
    channel: Literal["chrome", "chromium", "msedge"] = "chrome"
    profile_dir: str = ".profile/chrome"


class ImpossibleRules(BaseModel):
    """규칙 기반 불가 후보 (사이클 3, 가이드 C '수정 사항이 많으면 불가')."""

    max_false_facts: int = Field(3, ge=1)
    max_inconsistent_fields: int = Field(4, ge=1)


class TextRules(BaseModel):
    remove_phone_numbers: bool = True


class RevisionRules(BaseModel):
    """수정안 제약 (사이클 8). allow_turn_drop=False 면 모델이 턴을 삭제하지 못하고 내용만 고친다."""

    allow_turn_drop: bool = False


class UiConfig(BaseModel):
    """검토 화면 편집 동작 (사이클 6)."""

    edit_delay_ms: int = Field(1500, ge=300, le=10000)  # 입력이 멈춘 뒤 저장까지 지연. 한글 조합 중에는 저장하지 않음


class PathsConfig(BaseModel):
    data: str = "data"
    logs: str = "logs"


class AppConfig(BaseModel):
    dataset_id: int = Field(..., ge=1)  # 기본·폴백 데이터셋. 실제 대상은 화면에서 선택한 값(data/ui-state.json)
    persona: str = ""  # 선택. 초안에 persona 가 비어 있을 때만 프롬프트에 사용(데이터셋마다 다르므로 비교하지 않음)
    threshold: int = Field(40, ge=0, le=100)
    archetype_templates: dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_ARCHETYPE_TEMPLATES))
    legacy_archetype_templates: dict[str, list[str]] = Field(default_factory=lambda: {k: list(v) for k, v in DEFAULT_LEGACY_ARCHETYPE_TEMPLATES.items()})
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    effort: EffortConfig = Field(default_factory=EffortConfig)
    model_backend: Literal["claude_cli", "anthropic_sdk", "fake"] = "claude_cli"
    cli: CliConfig = Field(default_factory=CliConfig)
    labelon: LabelonConfig = Field(default_factory=LabelonConfig)
    chrome: ChromeConfig = Field(default_factory=ChromeConfig)
    image_max_side: int = Field(1568, ge=256, le=4000)
    cache_retention_days: int = Field(7, ge=0)
    ui_port: int = Field(8765, ge=1024, le=65535)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    impossible_rules: ImpossibleRules = Field(default_factory=ImpossibleRules)
    text_rules: TextRules = Field(default_factory=TextRules)
    revision_rules: RevisionRules = Field(default_factory=RevisionRules)
    ui: UiConfig = Field(default_factory=UiConfig)
    base_dir: Path = Field(default_factory=Path.cwd, exclude=True)

    @field_validator("archetype_templates")
    @classmethod
    def _templates_have_placeholder(cls, v: dict[str, str]) -> dict[str, str]:
        if not v:
            raise ValueError("아키타입 템플릿이 비어 있습니다")
        for k, t in v.items():
            if "(Persona)" not in t:
                raise ValueError(f"'{k}' 템플릿에 (Persona) 자리표시자가 없습니다")
        return v

    @field_validator("legacy_archetype_templates")
    @classmethod
    def _legacy_have_placeholder(cls, v: dict[str, list[str]]) -> dict[str, list[str]]:
        for k, lst in v.items():
            for t in lst:
                if "(Persona)" not in t:
                    raise ValueError(f"'{k}' 레거시 템플릿에 (Persona) 자리표시자가 없습니다")
        return v

    def templates_for(self, archetype: str) -> list[str]:
        """검사에 쓰는 템플릿 목록: 현재 문장 + 레거시 문장. 없는 아키타입이면 빈 목록."""
        cur = self.archetype_templates.get(archetype)
        if cur is None:
            return []
        return [cur, *self.legacy_archetype_templates.get(archetype, [])]

    # 편의 경로
    @property
    def data_dir(self) -> Path:
        return self.base_dir / self.paths.data

    @property
    def logs_dir(self) -> Path:
        return self.base_dir / self.paths.logs

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def resized_dir(self) -> Path:
        return self.data_dir / "resized"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "history.db"

    @property
    def profile_dir(self) -> Path:
        return self.base_dir / self.chrome.profile_dir

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.logs_dir, self.cache_dir, self.resized_dir, self.profile_dir, Path(self.cli.cwd)):
            d.mkdir(parents=True, exist_ok=True)


def load(path: str | Path) -> AppConfig:
    p = Path(path)
    if not p.exists():
        raise ConfigError("file", f"설정 파일이 없습니다: {p}. config.example.yaml 을 복사해 config.yaml 을 만드세요")
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ConfigError("yaml", f"YAML 문법 오류: {e}") from e
    if not isinstance(raw, dict):
        raise ConfigError("root", "최상위는 매핑(키: 값)이어야 합니다")
    try:
        cfg = AppConfig(**raw)
    except ValidationError as e:
        first = e.errors()[0]
        field = ".".join(str(x) for x in first.get("loc", ())) or "root"
        raise ConfigError(field, first.get("msg", "invalid")) from e
    cfg.base_dir = p.resolve().parent
    return cfg
