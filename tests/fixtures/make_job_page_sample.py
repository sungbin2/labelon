"""job_page_sample.html 생성기. 2026-09-23 관찰한 LabelOn UC-LE 작업 화면 구조를 재현한다.

실행: .venv\\Scripts\\python tests\\fixtures\\make_job_page_sample.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent / "src"))

from conftest import SAMPLE_FACTS, SAMPLE_FINAL_ANSWER, SAMPLE_INSTRUCTION

HEAD = {
    "hostingId": 1, "id": 158448, "jobStatus": "AK01", "inspectionStatus": "AL01",
    "regDate": "2026-09-22T10:36:01.000+00:00", "jobDate": "2026-09-23T09:52:33.000+00:00", "inspectionDate": None,
    "annotatorId": 2833767, "datasetId": 688, "datasetName": "[업사이클링] 거주환경 (어린이3)", "fileId": 2190682,
    "reviewerId": 0, "jobVqaId": 7113916, "question": "간장통에 간장이 가득 차있어", "answer": "아니요",
    "deIdentificationStatus": "AY01", "fileName": "150a214ef70b4f6ea16ba176044afde9.jpg",
    "orgFileName": "20210211_084503.jpg", "filePath": "2021/02/11", "detectedObject": "병,식탁",
    "category": "음식", "weather": "그외",
    "qaList": [
        {"question": "간장통에 간장이 가득 차있어", "answer": "아니요", "id": 7113916},
        {"question": "냄비엔 집게가 있어", "answer": "아니요", "id": 7113917},
        {"question": "위험한 물건 또는 상황은 무엇이 있습니까", "answer": "뜨거운 냄비", "id": 7113922},
    ],
}
RESULT = {
    "id": 99488, "jobSourceId": 158448, "datasetId": 0, "fileId": 0,
    "instruction": json.dumps(SAMPLE_INSTRUCTION, ensure_ascii=False),
    "scene": "조리대 오른쪽 레인지에는 음식이 든 냄비가 있고 왼쪽에는 빈 그릇과 조리 도구가 놓여 있다.",
    "facts": json.dumps(SAMPLE_FACTS, ensure_ascii=False),
    "finalAnswer": json.dumps(SAMPLE_FINAL_ANSWER, ensure_ascii=False),
    "summary": None,
    "cot1": "조리대만 가까이 보이며, 음식이 든 냄비와 손잡이는 오른쪽에 있고 빈 그릇은 왼쪽에 있다.",
    "cot2": "레인지 위 냄비와 그 안의 음식은 뜨거울 수 있고, 가까운 손잡이를 당기면 냄비가 움직일 수 있으며 유리 뚜껑은 건드리면 깨질 수 있다.",
    "cot3": "아이를 빈 그릇 쪽으로 비켜서게 한 뒤 손잡이와 유리 뚜껑을 피하게 하고, 뜨거운 냄비에서 음식을 담는 일은 어른에게 맡기도록 안내한다.",
    "cot4": None,
}


def textareas(cls: str, n: int) -> str:
    return "\n".join(f'<textarea class="{cls}"></textarea>' for _ in range(n))


def build() -> str:
    src_js = json.dumps([HEAD], ensure_ascii=True).replace("/", r"\/")
    res_js = json.dumps([RESULT], ensure_ascii=True).replace("/", r"\/")
    qa = "".join(
        '<div class="ucle_final_qa"><textarea class="ucle_final_qa_input ucle_final_question_input"></textarea>'
        '<textarea class="ucle_final_qa_input ucle_final_answer_input"></textarea></div>' for _ in range(6)
    )
    img_js = r'"https:\/\/images.labelon.kr\/2021\/02\/11\/150a214ef70b4f6ea16ba176044afde9.jpg"'
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><title>LabelOn</title></head>
<body>
<header><nav><a href="/project/home">프로젝트</a><a href="#" onclick="logout()">로그아웃</a></nav></header>
<input type="hidden" id="csrf" name="_csrf" value="4bbc2cfe-12c5-4fc5-8efc-d0ce0206ac24"/>
<main><div id="labelon-annotation">
<section class="dqa_content_box"><div class="ucle_editor_layout">
<div class="ucle_source_image_box"><img class="ucle_source_image" src="https://images.labelon.kr/2021/02/11/150a214ef70b4f6ea16ba176044afde9.jpg"/></div>
<div class="ucle_meta_box">image: 20210211_084503.jpgcategory: 음식weather: 그외</div>
{textareas("ucle_field_textarea ucle_instruction_textarea", 3)}
<textarea class="ucle_field_textarea" placeholder="입력하세요"></textarea>
{textareas("ucle_field_textarea ucle_facts_textarea", 5)}
{textareas("ucle_field_textarea", 3)}
<div>이미지 작업 가능 여부 <input class="eu_input" type="radio" name="able"/> 가능 <input class="eu_input" type="radio" name="able"/> 불가</div>
<button class="eu_button button_color bg_w w_full" type="submit">제출</button>
</div>
<section class="dqa_modal ucle_final_panel">{qa}</section></section></div></main>
<script>
        if (false) {{ $('#jobMainColorDiv').addClass('return'); }}
        let getDate;
        const ucleObj = {{ 'dataset_id': '', 'image': '' }};
        const vqaCotList = {src_js};

            if (vqaCotList?.length > 0) {{
                const head = vqaCotList[0];
                ucleObj.image = {img_js};
            }}
            const vqaCotResultList = {res_js};
</script>
</body></html>
"""


if __name__ == "__main__":
    out = HERE / "job_page_sample.html"
    out.write_text(build(), encoding="utf-8")
    print(f"written {out} ({out.stat().st_size} bytes)")
