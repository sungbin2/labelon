from labelon_reviewer.domain import (
    FinalDraft,
    InstructionCheck,
    JudgeResult,
    ModelUsage,
    RevisedDraft,
    SubmissionKind,
    SubmissionRecord,
)
from labelon_reviewer.history import HistoryRepository


def _judge():
    return JudgeResult(
        instruction_check=InstructionCheck(archetype_known=True, task_matches_template=True, persona_matches_config=True),
        fact_verdicts=[], field_verdicts=[], consistency_score=79, impossible_candidate=False, needs_revision=True,
        model_usage=ModelUsage(stage="judge", model="m", input_tokens=10, output_tokens=5, cost_usd=0.01),
    )


def test_roundtrip(sample_item, sample_draft):
    repo = HistoryRepository(":memory:")
    iid = repo.save_item(sample_item, sample_draft)
    repo.save_judge(iid, _judge())
    repo.save_revision(iid, RevisedDraft(draft=sample_draft, change_notes=[{"field": "fact_2", "reason": "방향"}]))
    repo.save_final(iid, FinalDraft.from_draft(sample_draft, edited=True))
    repo.save_submission(iid, SubmissionRecord(kind=SubmissionKind.APPROVE, success=True, response_message="저장되었습니다."))
    repo.mark_state(iid, "DONE")

    rows = repo.list_recent()
    assert rows[0]["id"] == iid and rows[0]["score"] == 79 and rows[0]["last_kind"] == "APPROVE" and rows[0]["state"] == "DONE"
    d = repo.get_detail(iid)
    assert d["draft"]["scene"] == sample_draft.scene and d["judge"]["consistency_score"] == 79
    assert d["revised"]["change_notes"][0]["field"] == "fact_2" and d["final"]["edited_by_user"] is True
    assert d["submissions"][0]["kind"] == "APPROVE" and d["usage"][0]["stage"] == "judge"


def test_summary_and_unfinished(sample_item, sample_draft):
    repo = HistoryRepository(":memory:")
    a = repo.save_item(sample_item, sample_draft)
    b = repo.save_item(sample_item, sample_draft)
    repo.save_judge(a, _judge())
    repo.save_submission(a, SubmissionRecord(kind=SubmissionKind.IMPOSSIBLE, success=True))
    repo.mark_state(a, "DONE")
    repo.mark_state(b, "REVIEW", "server shutdown")
    s = repo.summary()
    assert s["total_items"] == 0 and s["fetched_items"] == 2 and s["unfinished"] == 1  # 불가는 건수 제외 (2026-10-02)
    assert s["by_kind"] == {"IMPOSSIBLE": 1} and s["tokens"]["input"] == 10 and s["model_calls"] == 1
    unf = repo.find_unfinished()
    assert [r["id"] for r in unf] == [b] and unf[0]["state_note"] == "server shutdown"
    assert repo.file_name_for(a) == sample_item.file_name


def test_summary_today_uses_local_date_and_counts_submitted_only(sample_item, sample_draft):
    """오늘 = PC 로컬 날짜 (KST 오전 9시 이전 제출도 포함). 누적 = 승인·불가 제출 완료 건 (건너뜀·재시도 제외) (2026-09-29 결함)."""
    from datetime import UTC, datetime, timedelta

    repo = HistoryRepository(":memory:")
    ids = [repo.save_item(sample_item, sample_draft) for _ in range(5)]
    now = datetime.now(UTC)
    local_midnight = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
    repo.save_submission(ids[0], SubmissionRecord(kind=SubmissionKind.APPROVE, success=True, submitted_at=now))
    repo.save_submission(ids[1], SubmissionRecord(kind=SubmissionKind.IMPOSSIBLE, success=True, submitted_at=local_midnight + timedelta(minutes=1)))  # 로컬 오늘 0시 직후 (UTC 로는 어제일 수 있음)
    repo.save_submission(ids[2], SubmissionRecord(kind=SubmissionKind.APPROVE, success=True, submitted_at=local_midnight - timedelta(minutes=1)))  # 어제
    repo.save_submission(ids[3], SubmissionRecord(kind=SubmissionKind.APPROVE, success=False, error="x", submitted_at=now))  # 실패 후
    repo.save_submission(ids[3], SubmissionRecord(kind=SubmissionKind.APPROVE, success=True, submitted_at=now))  # 재시도 성공 → 1건
    repo.save_submission(ids[4], SubmissionRecord(kind=SubmissionKind.SKIP, success=True, submitted_at=now))
    s = repo.summary()
    assert s["today_items"] == 2 and s["by_kind_today"] == {"APPROVE": 2, "IMPOSSIBLE": 1, "SKIP": 1}  # 승인만 집계
    assert s["total_items"] == 3 and s["by_kind"] == {"APPROVE": 3, "IMPOSSIBLE": 1, "SKIP": 1} and s["fetched_items"] == 5
    assert s["by_dataset"][688]["total"] == 3 and s["by_dataset"][688]["fetched"] == 5


def test_dataset_name_column_and_by_dataset(sample_item, sample_draft):
    repo = HistoryRepository(":memory:")
    a = repo.save_item(sample_item, sample_draft)
    other = sample_item.model_copy(update={"dataset_id": 685, "dataset_name": "[업사이클링] 거주환경 (시각장애3)"})
    b = repo.save_item(other, sample_draft)
    repo.save_submission(a, SubmissionRecord(kind=SubmissionKind.APPROVE, success=True))
    repo.save_submission(b, SubmissionRecord(kind=SubmissionKind.SKIP, success=True))
    rows = repo.list_recent()
    assert rows[0]["dataset_id"] == 685 and rows[0]["dataset_name"].endswith("(시각장애3)")
    bd = repo.summary()["by_dataset"]
    assert bd[688]["APPROVE"] == 1 and bd[685]["SKIP"] == 1 and bd[688]["name"].endswith("(어린이3)")


def test_migration_adds_dataset_name(tmp_path):
    import sqlite3

    db = tmp_path / "old.db"
    con = sqlite3.connect(db)
    con.executescript("""CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL, dataset_id INTEGER NOT NULL,
        file_id INTEGER NOT NULL, job_vqa_id INTEGER, annotator_id INTEGER, org_file_name TEXT, file_name TEXT, image_url TEXT,
        category TEXT, weather TEXT, detected_object TEXT, related_qa_json TEXT NOT NULL, job_date TEXT NOT NULL, fetched_at TEXT NOT NULL,
        state TEXT NOT NULL, state_note TEXT, draft_json TEXT NOT NULL);""")
    con.commit()
    con.close()
    repo = HistoryRepository(db)
    cols = {r[1] for r in repo._conn.execute("PRAGMA table_info(items)").fetchall()}
    assert "dataset_name" in cols
