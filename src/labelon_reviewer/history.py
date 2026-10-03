"""이력 저장소 C-12 (SQLite). 동기 API. 서비스 계층이 asyncio.to_thread 로 감싼다."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .domain import (
    Draft,
    FinalDraft,
    JudgeResult,
    ModelUsage,
    RevisedDraft,
    SourceItem,
    SubmissionRecord,
    utcnow,
)

DDL = """
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id INTEGER NOT NULL, dataset_id INTEGER NOT NULL, file_id INTEGER NOT NULL,
  job_vqa_id INTEGER, annotator_id INTEGER,
  org_file_name TEXT, file_name TEXT, image_url TEXT,
  category TEXT, weather TEXT, detected_object TEXT,
  related_qa_json TEXT NOT NULL, job_date TEXT NOT NULL, fetched_at TEXT NOT NULL,
  state TEXT NOT NULL, state_note TEXT, draft_json TEXT NOT NULL, dataset_name TEXT
);
CREATE INDEX IF NOT EXISTS idx_items_job ON items(job_id, fetched_at);
CREATE TABLE IF NOT EXISTS judge_results (
  item_id INTEGER PRIMARY KEY REFERENCES items(id), created_at TEXT NOT NULL, result_json TEXT NOT NULL,
  score INTEGER NOT NULL, impossible_candidate INTEGER NOT NULL, needs_revision INTEGER NOT NULL, instruction_ok INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS revisions (
  item_id INTEGER PRIMARY KEY REFERENCES items(id), created_at TEXT NOT NULL, skipped INTEGER NOT NULL,
  revised_json TEXT NOT NULL, change_notes_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS final_drafts (
  item_id INTEGER PRIMARY KEY REFERENCES items(id), updated_at TEXT NOT NULL, edited_by_user INTEGER NOT NULL, final_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL REFERENCES items(id), kind TEXT NOT NULL,
  payload_json TEXT NOT NULL, response_message TEXT, success INTEGER NOT NULL, error TEXT, submitted_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS model_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL REFERENCES items(id), stage TEXT NOT NULL, model TEXT NOT NULL,
  input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER, cache_creation_tokens INTEGER,
  cost_usd REAL, latency_ms INTEGER, created_at TEXT NOT NULL
);
"""

UNFINISHED_STATES = ("FETCHING", "JUDGING", "REVISING", "REVIEW", "SUBMITTING")


def _j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


class HistoryRepository:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        if str(path) != ":memory:":
            self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(DDL)
        self._migrate()

    def _migrate(self) -> None:
        cols = {r[1] for r in self._conn.execute("PRAGMA table_info(items)").fetchall()}
        if "dataset_name" not in cols:  # 사이클 2 (2026-09-28)
            self._conn.execute("ALTER TABLE items ADD COLUMN dataset_name TEXT")
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ---------------------------------------------------------- 저장
    def save_item(self, item: SourceItem, draft: Draft, state: str = "FETCHING") -> int:
        cur = self._conn.execute(
            """INSERT INTO items(job_id,dataset_id,file_id,job_vqa_id,annotator_id,org_file_name,file_name,image_url,
               category,weather,detected_object,related_qa_json,job_date,fetched_at,state,draft_json,dataset_name)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item.job_id, item.dataset_id, item.file_id, item.job_vqa_id, item.annotator_id,
                item.org_file_name, item.file_name, item.image_url, item.category, item.weather, item.detected_object,
                _j([q.model_dump() for q in item.related_qa]), item.job_date.isoformat(), utcnow().isoformat(),
                state, draft.model_dump_json(), item.dataset_name or None,
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def save_judge(self, item_id: int, judge: JudgeResult) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO judge_results VALUES(?,?,?,?,?,?,?)",
            (item_id, utcnow().isoformat(), judge.model_dump_json(), judge.consistency_score,
             int(judge.impossible_candidate), int(judge.needs_revision), int(judge.instruction_check.ok)),
        )
        if judge.model_usage:
            self._save_usage(item_id, judge.model_usage)
        self._conn.commit()

    def save_revision(self, item_id: int, revised: RevisedDraft) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO revisions VALUES(?,?,?,?,?)",
            (item_id, utcnow().isoformat(), int(revised.skipped), revised.draft.model_dump_json(), _j(revised.change_notes)),
        )
        if revised.model_usage:
            self._save_usage(item_id, revised.model_usage)
        self._conn.commit()

    def save_final(self, item_id: int, final: FinalDraft) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO final_drafts VALUES(?,?,?,?)",
            (item_id, final.updated_at.isoformat(), int(final.edited_by_user), final.model_dump_json()),
        )
        self._conn.commit()

    def save_submission(self, item_id: int, rec: SubmissionRecord) -> None:
        self._conn.execute(
            "INSERT INTO submissions(item_id,kind,payload_json,response_message,success,error,submitted_at) VALUES(?,?,?,?,?,?,?)",
            (item_id, rec.kind.value, _j(rec.payload_snapshot), rec.response_message, int(rec.success), rec.error,
             rec.submitted_at.isoformat()),
        )
        self._conn.commit()

    def mark_state(self, item_id: int, state: str, note: str | None = None) -> None:
        self._conn.execute("UPDATE items SET state=?, state_note=COALESCE(?, state_note) WHERE id=?", (state, note, item_id))
        self._conn.commit()

    def _save_usage(self, item_id: int, u: ModelUsage) -> None:
        self._conn.execute(
            "INSERT INTO model_usage(item_id,stage,model,input_tokens,output_tokens,cache_read_tokens,cache_creation_tokens,cost_usd,latency_ms,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (item_id, u.stage, u.model, u.input_tokens, u.output_tokens, u.cache_read_tokens, u.cache_creation_tokens,
             u.cost_usd, u.latency_ms, utcnow().isoformat()),
        )

    # ---------------------------------------------------------- 조회
    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """SELECT i.id, i.job_id, i.dataset_id, i.dataset_name, i.org_file_name, i.fetched_at, i.state, i.state_note, j.score,
                      (SELECT kind FROM submissions s WHERE s.item_id=i.id ORDER BY s.id DESC LIMIT 1) AS last_kind,
                      (SELECT success FROM submissions s WHERE s.item_id=i.id ORDER BY s.id DESC LIMIT 1) AS last_success
               FROM items i LEFT JOIN judge_results j ON j.item_id=i.id
               ORDER BY i.id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_detail(self, item_id: int) -> dict[str, Any] | None:
        it = self._conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        if not it:
            return None
        d = dict(it)
        d["draft"] = json.loads(d.pop("draft_json"))
        d["related_qa"] = json.loads(d.pop("related_qa_json"))
        j = self._conn.execute("SELECT result_json FROM judge_results WHERE item_id=?", (item_id,)).fetchone()
        d["judge"] = json.loads(j["result_json"]) if j else None
        r = self._conn.execute("SELECT skipped, revised_json, change_notes_json FROM revisions WHERE item_id=?", (item_id,)).fetchone()
        d["revised"] = {"skipped": bool(r["skipped"]), "draft": json.loads(r["revised_json"]), "change_notes": json.loads(r["change_notes_json"])} if r else None
        f = self._conn.execute("SELECT final_json FROM final_drafts WHERE item_id=?", (item_id,)).fetchone()
        d["final"] = json.loads(f["final_json"]) if f else None
        d["submissions"] = [dict(x) for x in self._conn.execute("SELECT * FROM submissions WHERE item_id=? ORDER BY id", (item_id,)).fetchall()]
        for s in d["submissions"]:
            s["payload"] = json.loads(s.pop("payload_json"))
        d["usage"] = [dict(x) for x in self._conn.execute("SELECT * FROM model_usage WHERE item_id=? ORDER BY id", (item_id,)).fetchall()]
        return d

    @staticmethod
    def _today_start_utc() -> str:
        """로컬(PC 시간대) 오늘 0시를 UTC ISO 로. 저장 시각은 모두 utcnow().isoformat() (+00:00) 이라 문자열 비교가 가능하다."""
        local_midnight = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
        return local_midnight.astimezone(UTC).isoformat()

    # 건마다 마지막 성공 제출 1건 (재시도·중복 방지)
    _LATEST_OK = ("SELECT s.item_id, s.kind, s.submitted_at FROM submissions s WHERE s.success=1 "
                  "AND s.id=(SELECT MAX(id) FROM submissions WHERE item_id=s.item_id AND success=1)")

    def summary(self) -> dict[str, Any]:
        """건수는 '제출 완료(승인·불가)' 기준. 건너뜀·만료·미완료·가져온 건수는 따로 낸다. '오늘'은 PC 로컬 날짜 (2026-09-29 개정)."""
        start = self._today_start_utc()
        fetched = self._conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        by_kind = {r[0]: r[1] for r in self._conn.execute(
            f"SELECT kind, COUNT(*) FROM ({self._LATEST_OK}) GROUP BY kind").fetchall()}
        by_kind_today = {r[0]: r[1] for r in self._conn.execute(
            f"SELECT kind, COUNT(*) FROM ({self._LATEST_OK}) WHERE submitted_at >= ? GROUP BY kind", (start,)).fetchall()}
        done_kinds = ("APPROVE",)  # 2026-10-02: 불가 처리건은 건수에서 제외 (사용자 요청)
        total = sum(by_kind.get(k, 0) for k in done_kinds)
        today_n = sum(by_kind_today.get(k, 0) for k in done_kinds)
        expired = self._conn.execute("SELECT COUNT(*) FROM items WHERE state='EXPIRED'").fetchone()[0]
        unfinished = self._conn.execute(
            f"SELECT COUNT(*) FROM items WHERE state IN ({','.join('?' * len(UNFINISHED_STATES))})", UNFINISHED_STATES).fetchone()[0]
        u = self._conn.execute(
            "SELECT COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0), COALESCE(SUM(cache_read_tokens),0), "
            "COALESCE(SUM(cache_creation_tokens),0), COALESCE(SUM(cost_usd),0), COUNT(*) FROM model_usage").fetchone()
        by_dataset: dict[int, dict[str, Any]] = {}
        for r in self._conn.execute("SELECT dataset_id, MAX(dataset_name) AS name, COUNT(*) AS n FROM items GROUP BY dataset_id").fetchall():
            by_dataset[int(r["dataset_id"])] = {"name": r["name"] or str(r["dataset_id"]), "total": 0, "fetched": r["n"], "APPROVE": 0, "IMPOSSIBLE": 0, "SKIP": 0}
        for r in self._conn.execute(
            f"SELECT i.dataset_id, s.kind, COUNT(*) AS n FROM ({self._LATEST_OK}) s JOIN items i ON i.id=s.item_id GROUP BY i.dataset_id, s.kind"
        ).fetchall():
            d = by_dataset.setdefault(int(r["dataset_id"]), {"name": str(r["dataset_id"]), "total": 0, "fetched": 0, "APPROVE": 0, "IMPOSSIBLE": 0, "SKIP": 0})
            d[r["kind"]] = r["n"]
        for d in by_dataset.values():
            d["total"] = d["APPROVE"]
        return {
            "total_items": total, "today_items": today_n, "by_kind": by_kind, "by_kind_today": by_kind_today,
            "expired": expired, "unfinished": unfinished, "fetched_items": fetched, "by_dataset": by_dataset,
            "tokens": {"input": u[0], "output": u[1], "cache_read": u[2], "cache_creation": u[3]},
            "cost_usd_estimate": round(u[4], 4), "model_calls": u[5],
        }

    def find_unfinished(self) -> list[dict[str, Any]]:
        q = f"SELECT id, job_id, org_file_name, fetched_at, state, state_note FROM items WHERE state IN ({','.join('?' * len(UNFINISHED_STATES))}) ORDER BY id DESC"
        return [dict(r) for r in self._conn.execute(q, UNFINISHED_STATES).fetchall()]

    def file_name_for(self, item_id: int) -> str | None:
        r = self._conn.execute("SELECT file_name FROM items WHERE id=?", (item_id,)).fetchone()
        return r["file_name"] if r else None

    def items_older_than(self, days: int) -> list[str]:
        cutoff = (utcnow() - timedelta(days=days)).isoformat()
        return [r[0] for r in self._conn.execute("SELECT file_name FROM items WHERE fetched_at < ? AND file_name IS NOT NULL", (cutoff,)).fetchall()]
