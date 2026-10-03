"""project_home_sample.html 생성기. 2026-09-28 관찰한 LabelOn 프로젝트 홈 카드 구조를 재현한다.

실행: .venv\\Scripts\\python tests\\fixtures\\make_project_home_sample.py
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).parent

IN_PROGRESS = [
    ("AH25", 688, "[업사이클링] 거주환경 (어린이3)", 450),
    ("AH25", 687, "[업사이클링] 거주환경 (어린이보호자3)", 450),
    ("AH25", 686, "[업사이클링] 거주환경 (거동불편3)", 0),
    ("AH25", 685, "[업사이클링] 거주환경 (시각장애3)", 0),
    ("AH25", 684, "[업사이클링] 거주환경 (고령3)", 0),
    ("AH25", 682, "[업사이클링] 거주환경 (시각장애2-1)", 0),
    ("AH10", 999, "[테스트] 미지원 BBOX 데이터셋", 100),  # 미지원 타입: 목록에서 제외되어야 함
]
APPLICABLE = [("AH25", 700, "[업사이클링] 신청가능 샘플", 300)]


def card(job_type: str, ds_id: int, name: str, credit: int) -> str:
    return f"""<div class="project-box">
<a onclick="jobPage(&#39;annotator&#39;, &#39;{job_type}&#39;,&#39;{ds_id}&#39;)">
 <div class="project-tit-box"><div class="flx"><p class="project-tit">업사이클링</p> <span>UpcyclingLE</span></div>
  <p class="program-txt">{name}</p></div>
 <div class="program-desc-box"><ul>
  <li class="flx"><p class="title-m-13">크레딧</p><div class="flx"><span class="credit-icon"></span><span class="title-r-13"> {credit:,} </span></div></li>
  <li class="flx"><p class="title-m-13">등급</p><div><span class="title-r-13">고급자</span></div></li></ul>
  <div class="project-level flx"><span class="title-r-13">어노테이터</span></div></div>
</a></div>"""


def build() -> str:
    tab1 = "\n".join(card(*c) for c in APPLICABLE)
    tab2 = "\n".join(card(*c) for c in IN_PROGRESS)
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><title>LabelOn</title></head><body>
<header><nav><a href="/project/home">프로젝트</a><a href="#" onclick="logout()">로그아웃</a></nav></header>
<section class="sub-wrap"><div class="inner credit-cnt-wrap"><div class="col-12 guide-cnt-wrap guide-pg grid_flex">
<div class="project-v-tab">
 <button type="button" class="title-m-17 v-tab-list on" data-id="v-tab-01">신청가능 작업</button>
 <button type="button" class="title-m-17 v-tab-list" data-id="v-tab-02">진행중인 작업</button>
 <button type="button" class="title-m-17 v-tab-list" data-id="v-tab-03">신청중인 작업</button>
</div>
<div class="project-v-cnt">
 <div class="v-ctn-sec" id="v-tab-01"><div class="col-12 project-box-wrap">
{tab1}
 </div></div>
 <div class="v-ctn-sec" id="v-tab-02" style="display:none"><div class="col-12 project-box-wrap">
{tab2}
 </div></div>
 <div class="v-ctn-sec" id="v-tab-03" style="display:none"><div class="col-12 project-box-wrap"><p>신청중인 프로젝트가 없습니다.</p></div></div>
</div></div></div></section>
</body></html>
"""


if __name__ == "__main__":
    out = HERE / "project_home_sample.html"
    out.write_text(build(), encoding="utf-8")
    print(f"written {out} ({out.stat().st_size} bytes)")
