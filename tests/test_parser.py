from datetime import UTC, datetime

import pytest

from labelon_reviewer.domain import PageStructureError
from labelon_reviewer.labelon import parser
from tests.conftest import FIXTURES as FIXTURES_DIR
from tests.conftest import SAMPLE_FACTS, SAMPLE_INSTRUCTION


def test_parse_fixture(job_page_html, sample_draft):
    item, draft = parser.parse_html(job_page_html, 9)
    assert item.job_id == 158448 and item.dataset_id == 688 and item.file_id == 2190682 and item.annotator_id == 2833767
    assert item.image_url == "https://images.labelon.kr/2021/02/11/150a214ef70b4f6ea16ba176044afde9.jpg"
    assert item.category == "음식" and len(item.related_qa) == 3 and item.related_qa[2].answer == "뜨거운 냄비"
    # 서버 jobDate 09:52 KST → 00:52 UTC
    assert item.job_date == datetime(2026, 9, 23, 0, 52, 33, tzinfo=UTC)
    assert draft.instruction.model_dump() == SAMPLE_INSTRUCTION
    assert draft.facts == SAMPLE_FACTS
    assert len(draft.dialogue.turns) == 3 and draft.dialogue.turn(3).user.endswith("담아?")
    assert draft.dialogue.context["user_type"] == "장난기가 많은 어린아이"
    assert draft.scene == sample_draft.scene and draft.cot2 == sample_draft.cot2


def test_csrf_and_job_id(job_page_html):
    assert parser.csrf_token(job_page_html) == "4bbc2cfe-12c5-4fc5-8efc-d0ce0206ac24"
    assert parser.current_job_id(job_page_html) == 158448


def test_page_kind(job_page_html):
    assert parser.page_kind("https://www.labelon.kr/job/ucle/annotator?datasetId=688", job_page_html) == "JOB"
    assert parser.page_kind("https://www.labelon.kr/project/home", "<html>...</html>") == "HOME"
    assert parser.page_kind("https://www.labelon.kr/login", '<input type="password">') == "LOGIN"
    assert parser.page_kind("https://www.labelon.kr/mypage", "<html/>") == "OTHER"
    assert parser.page_kind("https://www.labelon.kr/access", "<p>로그인 후 확인이 가능한 메뉴입니다.</p>") == "LOGIN"
    assert parser.page_kind("https://www.labelon.kr/project/home", "<p>로그인 후 확인이 가능한 메뉴입니다.</p>") == "LOGIN"


def test_structure_errors():
    with pytest.raises(PageStructureError):
        parser.extract_script_array("<html>no arrays</html>", "vqaCotList")
    with pytest.raises(PageStructureError):
        parser.parse_html('<script>const vqaCotList = [];</script>')


def test_lenient_json_and_dialogue_shapes():
    d = parser.to_draft({"instruction": "{'archetype': '음식', 'persona': 'p', 'task': 't'}", "facts": '["a"]',
                         "finalAnswer": '[{"turn": 2, "user": "u", "assistant": "a"}]'})
    assert d.instruction.archetype == "음식" and d.facts == ["a"] and d.dialogue.turns[0].turn == 2


def test_locator_map():
    loc = parser.field_locators()
    assert loc.plain_index("cot3") == 3 and loc.expected_counts["facts"] == 5


def test_parse_dataset_list():
    html = (FIXTURES_DIR / "project_home_sample.html").read_text(encoding="utf-8")
    items = parser.parse_dataset_list(html)
    assert [d.dataset_id for d in items] == [688, 687, 686, 685, 684, 682]  # 진행중 패널만, 미지원 AH10 제외, 신청가능 700 제외
    first = items[0]
    assert first.dataset_name == "[업사이클링] 거주환경 (어린이3)" and first.credit == 450 and first.grade == "고급자"
    assert first.project_name == "업사이클링" and first.project_code == "UpcyclingLE" and first.supported
    assert items[2].credit == 0 and items[5].dataset_name.endswith("(시각장애2-1)")


def test_parse_dataset_list_ignores_tab_button_data_id():
    """실제 페이지: 탭 버튼 data-id="v-tab-02" 가 패널보다 먼저 나온다 (2026-09-29 운영 결함)."""
    html = (FIXTURES_DIR / "project_home_sample.html").read_text(encoding="utf-8")
    assert 'data-id="v-tab-02"' in html and html.index('data-id="v-tab-02"') < html.index(' id="v-tab-02"')
    assert [d.dataset_id for d in parser.parse_dataset_list(html)] == [688, 687, 686, 685, 684, 682]
    section = parser._panel(html, "v-tab-02")
    assert section.startswith('id="v-tab-02"') and 'id="v-tab-03"' not in section


def test_parse_dataset_list_accepts_entity_and_plain_quotes():
    """원본 HTML 은 &#39;, DOM 추출본은 ' (2026-09-29 운영 결함 2)."""
    html = (FIXTURES_DIR / "project_home_sample.html").read_text(encoding="utf-8")
    assert "jobPage(&#39;annotator&#39;" in html and "jobPage('annotator'" not in html
    assert len(parser.parse_dataset_list(html)) == 6
    plain = html.replace("&#39;", "'")
    assert [d.dataset_id for d in parser.parse_dataset_list(plain)] == [688, 687, 686, 685, 684, 682]


def test_parse_dataset_list_missing_panel():
    with pytest.raises(PageStructureError):
        parser.parse_dataset_list("<html><body>no tabs</body></html>")
