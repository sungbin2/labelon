"""LabelOn UC-LE 작업 화면 파서 C-03 (2026-09-23 관찰 구조 기준).

페이지 인라인 스크립트:
  const vqaCotList = [ {...} ];          # 원천 (id, datasetId, fileId, jobDate, qaList, ...)
  const vqaCotResultList = [ {...} ];    # 서버 초안 (instruction/facts/finalAnswer 는 JSON 문자열)
화면 textarea 순서:
  .ucle_instruction_textarea x3 → (scene) → .ucle_facts_textarea x5 → (cot1..3)
  .ucle_final_question_input / .ucle_final_answer_input 각 6개
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from ..domain import (
    DatasetInfo,
    Dialogue,
    DialogueTurn,
    Draft,
    Instruction,
    PageStructureError,
    RelatedQA,
    SourceItem,
)

JOB_PATH = "/job/ucle/annotator"
IN_PROGRESS_PANEL_ID = "v-tab-02"  # 프로젝트 홈 '진행중인 작업' 탭 패널 (2026-09-28 관찰)
SUPPORTED_JOB_TYPES = ("AH25",)


# ------------------------------------------------------------------ 스크립트 배열 추출
def extract_script_array(html: str, name: str) -> list[Any]:
    m = re.search(r"(?:const|let|var)\s+" + re.escape(name) + r"\s*=\s*\[", html)
    if not m:
        raise PageStructureError(f"스크립트에서 {name} 배열을 찾을 수 없습니다")
    start = m.end() - 1
    depth = 0
    i = start
    in_str = False
    esc = False
    n = len(html)
    while i < n:
        ch = html[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "[" or ch == "{":
                depth += 1
            elif ch == "]" or ch == "}":
                depth -= 1
                if depth == 0:
                    text = html[start : i + 1]
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError as e:
                        raise PageStructureError(f"{name} JSON 파싱 실패: {e}") from e
                    if not isinstance(data, list):
                        raise PageStructureError(f"{name} 이 배열이 아닙니다")
                    return data
        i += 1
    raise PageStructureError(f"{name} 배열이 닫히지 않았습니다")


def _loads_lenient(value: Any, default: Any) -> Any:
    """React 코드와 동일: JSON 문자열 → 실패 시 ' → \" 치환 후 재시도."""
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    s = str(value).strip()
    if not s:
        return default
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        try:
            return json.loads(s.replace("'", '"'))
        except json.JSONDecodeError:
            return default


# ------------------------------------------------------------------ 변환
def parse_job_date(value: str, server_tz_offset_hours: int) -> datetime:
    """서버는 KST 시각을 +00:00 으로 표기해 내려준다. 시간대만 교체한다."""
    s = str(value).replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    tz = timezone(timedelta(hours=server_tz_offset_hours))
    return dt.replace(tzinfo=tz).astimezone(UTC)


def to_source_item(head: dict[str, Any], image_url: str, tz_offset: int) -> SourceItem:
    try:
        return SourceItem(
            job_id=int(head["id"]), dataset_id=int(head["datasetId"]), dataset_name=str(head.get("datasetName") or ""),
            file_id=int(head["fileId"]), job_vqa_id=head.get("jobVqaId"), annotator_id=head.get("annotatorId"),
            image_url=image_url, org_file_name=str(head.get("orgFileName") or ""), file_name=str(head.get("fileName") or ""),
            category=str(head.get("category") or ""), weather=str(head.get("weather") or ""),
            detected_object=str(head.get("detectedObject") or ""),
            related_qa=[RelatedQA(question=str(q.get("question", "")), answer=str(q.get("answer", "")), id=q.get("id"))
                        for q in (head.get("qaList") or []) if isinstance(q, dict)],
            job_date=parse_job_date(head["jobDate"], tz_offset), job_status=str(head.get("jobStatus") or ""),
            de_identification_status=str(head.get("deIdentificationStatus") or ""),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise PageStructureError(f"원천 데이터 필드 오류: {e}") from e


def to_draft(res: dict[str, Any]) -> Draft:
    ins = _loads_lenient(res.get("instruction"), {}) or {}
    facts = _loads_lenient(res.get("facts"), []) or []
    fa = _loads_lenient(res.get("finalAnswer"), {}) or {}
    if isinstance(fa, list):  # React 코드는 배열도 허용
        dialogue_list, context = fa, {}
    else:
        dialogue_list, context = fa.get("dialogue") or [], fa.get("context") or {}
    if isinstance(dialogue_list, dict):
        dialogue_list = [dialogue_list]
    turns = []
    for i, t in enumerate(dialogue_list):
        if not isinstance(t, dict):
            continue
        turns.append(DialogueTurn(turn=int(t.get("turn", i + 1)), user=str(t.get("user", "")), assistant=str(t.get("assistant", ""))))
    turns.sort(key=lambda t: t.turn)
    return Draft(
        instruction=Instruction(archetype=str(ins.get("archetype", "")), persona=str(ins.get("persona", "")), task=str(ins.get("task", ""))),
        scene=str(res.get("scene") or ""), facts=[str(x) for x in facts],
        cot1=str(res.get("cot1") or ""), cot2=str(res.get("cot2") or ""), cot3=str(res.get("cot3") or ""),
        dialogue=Dialogue(context=context if isinstance(context, dict) else {}, turns=turns),
    )


def extract_image_url(html: str) -> str:
    m = re.search(r'ucleObj\.image\s*=\s*"([^"]+)"', html)
    if m:
        return m.group(1).replace("\\/", "/")
    m = re.search(r'<img[^>]+class="[^"]*ucle_source_image[^"]*"[^>]+src="([^"]+)"', html)
    if m:
        return m.group(1)
    raise PageStructureError("이미지 URL 을 찾을 수 없습니다")


def csrf_token(html: str) -> str:
    m = re.search(r'id="csrf"[^>]*value="([^"]+)"', html) or re.search(r'name="_csrf"[^>]*value="([^"]+)"', html)
    if not m:
        raise PageStructureError("CSRF 토큰을 찾을 수 없습니다")
    return m.group(1)


def parse_html(html: str, server_tz_offset_hours: int = 9) -> tuple[SourceItem, Draft]:
    src = extract_script_array(html, "vqaCotList")
    res = extract_script_array(html, "vqaCotResultList")
    if not src or not isinstance(src[0], dict):
        raise PageStructureError("vqaCotList 가 비어 있습니다")
    head = src[0]
    result = res[0] if res and isinstance(res[0], dict) else {}
    item = to_source_item(head, extract_image_url(html), server_tz_offset_hours)
    return item, to_draft(result)


def current_job_id(html: str) -> int | None:
    try:
        src = extract_script_array(html, "vqaCotList")
        return int(src[0]["id"]) if src else None
    except (PageStructureError, KeyError, TypeError, ValueError):
        return None


# ------------------------------------------------------------------ 페이지 종류
def page_kind(url: str, html: str) -> str:
    u = (url or "").lower()
    # 미로그인 상태에서 보호 페이지에 접근하면 /access 로 리다이렉트되며 "로그인 후 확인이 가능한 메뉴" 안내가 표시된다 (2026-09-23 관찰)
    if (
        'type="password"' in html or "type='password'" in html or "/login" in u or "/access" in u
        or "로그인 후 확인이 가능한" in html
    ):
        return "LOGIN"
    if JOB_PATH in u and "vqaCotList" in html:
        return "JOB"
    if "/project/home" in u:
        return "HOME"
    return "OTHER"


# ------------------------------------------------------------------ 프로젝트 홈: 진행중 데이터셋 목록
_TAG_RE = re.compile(r"<[^>]+>")
# 원본 HTML 은 onclick 안의 작은따옴표를 &#39; 로 이스케이프한다(2026-09-29 관찰). DOM 에서는 디코딩되어 보이므로 둘 다 허용
_Q = r"(?:'|&#39;|&apos;)"
_CARD_RE = re.compile(
    r"""<a[^>]*onclick=["']jobPage\(\s*""" + _Q + r"annotator" + _Q + r"\s*,\s*" + _Q + r"([A-Za-z0-9]+)" + _Q
    + r"\s*,\s*" + _Q + r"(\d+)" + _Q + r"""\s*\)["'][^>]*>(.*?)</a>""",
    re.S,
)
_TIT_RE = re.compile(r'class="[^"]*project-tit[^"]*"[^>]*>(.*?)</p>', re.S)
_CODE_RE = re.compile(r'class="[^"]*project-tit[^"]*"[^>]*>.*?</p>\s*<span[^>]*>(.*?)</span>', re.S)
_NAME_RE = re.compile(r'class="[^"]*program-txt[^"]*"[^>]*>(.*?)</p>', re.S)
_CREDIT_RE = re.compile(r"크레딧.*?title-r-13[^>]*>\s*([\d,]+)", re.S)  # class 이름의 숫자(title-m-13)를 피한다
_GRADE_RE = re.compile(r"등급.*?<span[^>]*>(.*?)</span>", re.S)


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", html)).strip()


def _panel(html: str, panel_id: str) -> str:
    # 실제 페이지(2026-09-29 관찰)에는 탭 버튼에 data-id="v-tab-02" 가 먼저 나오므로 속성 이름이 정확히 id 인 것만 잡는다
    m = re.search(r'(?<![\w-])id="' + re.escape(panel_id) + r'"', html)
    if not m:
        raise PageStructureError(f"프로젝트 홈에서 패널 #{panel_id} 를 찾을 수 없습니다")
    start = m.start()
    nxt = re.search(r'class="[^"]*v-ctn-sec[^"]*"[^>]*(?<![\w-])id="v-tab-\d+"', html[m.end():])
    end = m.end() + nxt.start() if nxt else len(html)
    return html[start:end]


def parse_dataset_list(html: str, panel_id: str = IN_PROGRESS_PANEL_ID) -> list[DatasetInfo]:
    """프로젝트 홈 HTML 의 '진행중인 작업' 패널에서 UC-LE 데이터셋 카드를 추출한다. 미지원 타입은 제외."""
    section = _panel(html, panel_id)
    out: list[DatasetInfo] = []
    seen: set[int] = set()
    for job_type, ds_id, body in _CARD_RE.findall(section):
        did = int(ds_id)
        if did in seen:
            continue
        seen.add(did)
        tit = _TIT_RE.search(body)
        code = _CODE_RE.search(body)
        name = _NAME_RE.search(body)
        credit = _CREDIT_RE.search(body)
        grade = _GRADE_RE.search(body)
        info = DatasetInfo(
            dataset_id=did, job_type=job_type,
            project_name=_text(tit.group(1)) if tit else "", project_code=_text(code.group(1)) if code else "",
            dataset_name=_text(name.group(1)) if name else _text(body)[:60],
            credit=int(credit.group(1).replace(",", "")) if credit else None,
            grade=_text(grade.group(1)) if grade else "",
        )
        if info.job_type not in SUPPORTED_JOB_TYPES:
            continue
        out.append(info)
    return out


# ------------------------------------------------------------------ 필드 locator
@dataclass(frozen=True)
class FieldLocatorMap:
    instruction_textarea: str = "textarea.ucle_instruction_textarea"  # 0 archetype, 1 persona, 2 task
    plain_textarea: str = "textarea.ucle_field_textarea:not(.ucle_instruction_textarea):not(.ucle_facts_textarea)"  # scene, cot1..3
    facts_textarea: str = "textarea.ucle_facts_textarea"
    question_textarea: str = "textarea.ucle_final_question_input"
    answer_textarea: str = "textarea.ucle_final_answer_input"
    radio: str = "input.eu_input[type=radio]"  # 0: 가능, 1: 불가
    submit_button: str = "button.eu_button[type=submit]"
    confirm_text: str = "해당 작업 내용을 제출하시겠습니까"
    # LabelOn 공통 모달 (method.js ModalConfirm / ModalAlert)
    confirm_modal: str = "#commonmodal2"
    confirm_modal_text: str = "#commonmodal2_text"
    confirm_ok_button: str = "button:has-text('확인')"
    alert_modal: str = "#commonmodal1"
    alert_text: str = "#commonmodal1_text"
    alert_close_button: str = "#commonmodal1 button"
    success_text: str = "저장되었습니다"
    impossible_reason_textarea: str = "textarea[placeholder*='불가 사유'], textarea[placeholder*='불가사유'], textarea[placeholder*='불가']"
    # facts 개수는 초안마다 다르므로(5~6개 관찰) 제출 시 초안 길이로 대체된다
    expected_counts: dict[str, int] = field(default_factory=lambda: {"plain": 4, "facts": 5, "question": 6, "answer": 6, "radio": 2})

    def plain_index(self, name: str) -> int:
        return {"scene": 0, "cot1": 1, "cot2": 2, "cot3": 3}[name]


def field_locators() -> FieldLocatorMap:
    return FieldLocatorMap()
