"""SQLite persistence, demo seed data, and read models for the API.

The app deliberately uses only the Python standard library at runtime. The
single-file database keeps the prototype easy to run and reset.
"""
from __future__ import annotations

import json
import random
import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from . import validators
from .auth import hash_password
from .config import (CLOSED_STATUSES, DATA_DIR, DB_PATH, DEFAULT_SETTINGS,
                     DEMO_USERS, DOC_TYPES, OPEN_STATUSES, SAMPLES_DIR,
                     STATUS_LABELS, UPLOADS_DIR)

IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc

SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL,
    title TEXT,
    password_hash TEXT NOT NULL,
    initials TEXT,
    color TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    ref TEXT UNIQUE NOT NULL,
    doc_type TEXT NOT NULL,
    title TEXT NOT NULL,
    customer_name TEXT,
    language TEXT,
    language_name TEXT,
    script TEXT,
    status TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'normal',
    confidence REAL NOT NULL DEFAULT 0,
    quality TEXT,
    pages INTEGER NOT NULL DEFAULT 1,
    image_file TEXT NOT NULL,
    page_files TEXT,
    width INTEGER NOT NULL DEFAULT 1240,
    height INTEGER NOT NULL DEFAULT 1754,
    submitted_at TEXT NOT NULL,
    due_at TEXT NOT NULL,
    claimed_at TEXT,
    assignee_id TEXT,
    reviewer_id TEXT,
    reviewed_at TEXT,
    amount REAL,
    is_high_value INTEGER NOT NULL DEFAULT 0,
    engine TEXT,
    engine_version TEXT,
    source TEXT,
    notes TEXT,
    ocr_text TEXT,
    ocr_meta TEXT,
    review_seconds INTEGER,
    field_count INTEGER NOT NULL DEFAULT 0,
    low_count INTEGER NOT NULL DEFAULT 0,
    invalid_count INTEGER NOT NULL DEFAULT 0,
    verified_count INTEGER NOT NULL DEFAULT 0,
    corrected_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (assignee_id) REFERENCES users(id),
    FOREIGN KEY (reviewer_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS fields (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    key TEXT NOT NULL,
    label TEXT NOT NULL,
    label_sub TEXT,
    section TEXT,
    value TEXT,
    original_value TEXT,
    confidence REAL NOT NULL DEFAULT 0,
    page INTEGER NOT NULL DEFAULT 1,
    x REAL NOT NULL DEFAULT 0,
    y REAL NOT NULL DEFAULT 0,
    w REAL NOT NULL DEFAULT 0,
    h REAL NOT NULL DEFAULT 0,
    field_type TEXT NOT NULL DEFAULT 'text',
    required INTEGER NOT NULL DEFAULT 1,
    options TEXT,
    dir TEXT NOT NULL DEFAULT 'ltr',
    validation_status TEXT NOT NULL DEFAULT 'unchecked',
    validation_message TEXT,
    corrected INTEGER NOT NULL DEFAULT 0,
    corrected_by TEXT,
    corrected_at TEXT,
    verified INTEGER NOT NULL DEFAULT 0,
    display_order INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT,
    user_id TEXT,
    action TEXT NOT NULL,
    detail TEXT,
    meta TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    user_id TEXT,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS metrics_daily (
    day TEXT PRIMARY KEY,
    volume INTEGER NOT NULL,
    auto_approved INTEGER NOT NULL,
    reviewed INTEGER NOT NULL,
    corrections INTEGER NOT NULL,
    avg_confidence REAL NOT NULL,
    avg_tat_minutes REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_docs_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_docs_due ON documents(due_at);
CREATE INDEX IF NOT EXISTS idx_docs_assignee ON documents(assignee_id);
CREATE INDEX IF NOT EXISTS idx_fields_doc ON fields(document_id);
CREATE INDEX IF NOT EXISTS idx_events_doc ON events(document_id, created_at);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
"""


# --------------------------------------------------------------------------- time
def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(dt: datetime | None = None) -> str:
    dt = dt or utcnow()
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def local_midnight_utc() -> datetime:
    now = datetime.now(IST)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


# --------------------------------------------------------------------------- connection
@contextmanager
def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(reset: bool = False) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if reset and DB_PATH.exists():
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(DB_PATH) + suffix)
            if p.exists():
                p.unlink()
    with connect() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
        seed_if_needed(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    """Small additive migrations for databases created by earlier builds."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(documents)")}
    if "ocr_text" not in cols:
        conn.execute("ALTER TABLE documents ADD COLUMN ocr_text TEXT")
    if "ocr_meta" not in cols:
        conn.execute("ALTER TABLE documents ADD COLUMN ocr_meta TEXT")
    if "page_files" not in cols:
        conn.execute("ALTER TABLE documents ADD COLUMN page_files TEXT")


# --------------------------------------------------------------------------- seed
def seed_if_needed(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        seed_users(conn)
    if conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)",
                         (key, json.dumps(value)))
    if conn.execute("SELECT COUNT(*) FROM metrics_daily").fetchone()[0] == 0:
        seed_metrics(conn)
    if conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0:
        seed_documents(conn)
        update_today_metrics(conn)


def seed_users(conn: sqlite3.Connection) -> None:
    now = iso()
    for user in DEMO_USERS:
        conn.execute(
            """INSERT OR IGNORE INTO users(id,name,email,role,title,password_hash,initials,color,created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (user["id"], user["name"], user["email"], user["role"], user["title"],
             hash_password(user["password"]), user["initials"], user["color"], now),
        )


def seed_metrics(conn: sqlite3.Connection) -> None:
    today = datetime.now(IST).date()
    rnd = random.Random(7919)
    for offset in range(27, -1, -1):
        day = today - timedelta(days=offset)
        volume = rnd.randint(14, 31)
        auto_ratio = rnd.uniform(0.52, 0.72)
        auto = int(round(volume * auto_ratio))
        reviewed = max(0, volume - auto)
        corrections = rnd.randint(1, 7)
        confidence = round(rnd.uniform(0.858, 0.938), 3)
        tat = round(rnd.uniform(3.6, 8.4), 1)
        conn.execute(
            """INSERT OR REPLACE INTO metrics_daily
               (day,volume,auto_approved,reviewed,corrections,avg_confidence,avg_tat_minutes)
               VALUES (?,?,?,?,?,?,?)""",
            (day.isoformat(), volume, auto, reviewed, corrections, confidence, tat),
        )


def update_today_metrics(conn: sqlite3.Connection) -> None:
    today = datetime.now(IST).date().isoformat()
    start = iso(local_midnight_utc())
    row = conn.execute(
        """SELECT COUNT(*) AS n,
                  SUM(CASE WHEN status='auto_approved' THEN 1 ELSE 0 END) AS auto,
                  SUM(CASE WHEN status IN ('approved','rejected') THEN 1 ELSE 0 END) AS reviewed,
                  SUM(corrected_count) AS corrections,
                  AVG(confidence) AS conf
           FROM documents WHERE submitted_at >= ?""", (start,)
    ).fetchone()
    if not row or not row["n"]:
        return
    conn.execute(
        """UPDATE metrics_daily SET volume=?, auto_approved=?, reviewed=?, corrections=?,
           avg_confidence=? WHERE day=?""",
        (row["n"], row["auto"] or 0, row["reviewed"] or 0, row["corrections"] or 0,
         round(row["conf"] or 0.9, 3), today),
    )


def get_settings() -> dict[str, Any]:
    out = dict(DEFAULT_SETTINGS)
    with connect() as conn:
        for row in conn.execute("SELECT key, value FROM settings"):
            try:
                out[row["key"]] = json.loads(row["value"])
            except json.JSONDecodeError:
                out[row["key"]] = row["value"]
    return out


def set_settings(updates: dict[str, Any]) -> dict[str, Any]:
    with connect() as conn:
        for key, value in updates.items():
            conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)",
                         (key, json.dumps(value)))
    return get_settings()


# --------------------------------------------------------------------------- fixtures
def fixture_index() -> list[dict]:
    path = SAMPLES_DIR / "index.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    items = []
    for fp in sorted(SAMPLES_DIR.glob("*.json")):
        if fp.name == "index.json":
            continue
        data = json.loads(fp.read_text(encoding="utf-8"))
        items.append(data)
    return items


def load_fixture(sample_id: str) -> dict | None:
    path = SAMPLES_DIR / f"{sample_id}.json"
    if not path.exists():
        # Allow lookup by fixture id inside a single index.
        for item in fixture_index():
            if item.get("id") == sample_id:
                alt = SAMPLES_DIR / f"{item['id']}.json"
                if alt.exists():
                    return json.loads(alt.read_text(encoding="utf-8"))
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _priority_rank(priority: str) -> int:
    return {"urgent": 0, "high": 1, "normal": 2}.get(priority, 3)


def _doc_reasons(row: sqlite3.Row | dict) -> list[str]:
    reasons = []
    try:
        low = int(row["low_count"])
        invalid = int(row["invalid_count"])
    except (KeyError, TypeError):
        low = invalid = 0
    if low:
        reasons.append(f"{low} low-confidence field{'s' if low != 1 else ''}")
    if invalid:
        reasons.append(f"{invalid} validation issue{'s' if invalid != 1 else ''}")
    if row["is_high_value"]:
        reasons.append("High-value document")
    if row["quality"] == "poor":
        reasons.append("Poor scan quality")
    if row["status"] == "escalated":
        reasons.append("Escalated to supervisor")
    due = parse_iso(row["due_at"])
    if due and row["status"] in OPEN_STATUSES and due < utcnow():
        reasons.append("SLA breached")
    return reasons


def seed_documents(conn: sqlite3.Connection) -> None:
    samples = fixture_index()
    users = {u["email"].split("@")[0]: u for u in DEMO_USERS}
    user_ids = {"maya": "u_maya", "arjun": "u_arjun", "leela": "u_leela"}
    now = utcnow()
    corrections_map = {
        "bank_02": ["pincode", "occupation"],
        "invoice_03": ["total"],
        "loan_01": ["pan"],
        "claim_03": ["diagnosis"],
    }
    for sample in samples:
        path = SAMPLES_DIR / f"{sample['id']}.json"
        if not path.exists():
            continue
        fixture = json.loads(path.read_text(encoding="utf-8"))
        doc_id = f"doc_{fixture['id']}"
        if conn.execute("SELECT 1 FROM documents WHERE id=?", (doc_id,)).fetchone():
            continue
        submitted = now - timedelta(minutes=int(fixture.get("submitted_minutes", 30)))
        hours = 4 if fixture.get("priority") == "urgent" else 8
        due = submitted + timedelta(hours=hours)
        status = fixture["status"]
        assignee = user_ids.get(fixture.get("assignee") or "")
        reviewer = user_ids.get(fixture.get("reviewer") or "")
        reviewed_after = fixture.get("reviewed_after")
        reviewed_at = submitted + timedelta(minutes=int(reviewed_after)) if reviewed_after else None
        claimed_at = submitted + timedelta(minutes=3) if assignee else None
        if reviewed_at and reviewed_at > now:
            reviewed_at = now - timedelta(minutes=1)
        amount = fixture.get("amount")
        is_high = bool(amount and amount >= 100000)

        fields = []
        for idx, f in enumerate(fixture["fields"]):
            bbox = f.get("bbox") or [0, 0, 0, 0]
            fields.append({
                "id": f"{doc_id}:{f['key']}", "document_id": doc_id,
                "key": f["key"], "label": f["label"], "label_sub": f.get("label_sub", ""),
                "section": f.get("section", ""), "value": f.get("value", ""),
                "original_value": f.get("value", ""), "confidence": float(f.get("confidence", 0)),
                "page": 1, "x": bbox[0], "y": bbox[1], "w": bbox[2], "h": bbox[3],
                "field_type": f.get("type", "text"), "type": f.get("type", "text"),
                "required": 1 if f.get("required", True) else 0,
                "options": json.dumps(f.get("options", []), ensure_ascii=False),
                "dir": f.get("dir", "ltr"), "display_order": idx,
                "verified": 0, "corrected": 0,
                "corrected_by": None, "corrected_at": None,
            })
        issues = validators.validate_document(fixture["kind"], fields)
        summary = validators.summarize(fields)

        if status in ("auto_approved", "approved", "rejected"):
            for f in fields:
                f["verified"] = 1
        elif status == "in_review":
            for f in fields:
                f["verified"] = 1 if f["confidence"] >= 0.9 else 0
        for key in corrections_map.get(fixture["id"], []):
            fld = next((f for f in fields if f["key"] == key), None)
            if fld:
                fld["corrected"] = 1
                fld["corrected_by"] = reviewer
                fld["corrected_at"] = iso(reviewed_at) if reviewed_at else None
                # The fixture truth is what the reviewer typed.
                truth = next((x.get("truth") for x in fixture["fields"]
                              if x["key"] == key), fld["value"])
                fld["value"] = truth
                fld["verified"] = 1

        conn.execute(
            """INSERT INTO documents
               (id,ref,doc_type,title,customer_name,language,language_name,script,status,priority,
                confidence,quality,pages,image_file,width,height,submitted_at,due_at,claimed_at,
                assignee_id,reviewer_id,reviewed_at,amount,is_high_value,engine,engine_version,
                source,notes,review_seconds,field_count,low_count,invalid_count,verified_count,
                corrected_count,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (doc_id, fixture["ref"], fixture["kind"], fixture["doc_type_label"],
             fixture["customer_name"], fixture["language"], fixture["language_name"],
             fixture["script"], status, fixture.get("priority", "normal"),
             fixture["confidence"], fixture.get("quality"), 1, fixture["preview"],
             1240, 1754, iso(submitted), iso(due), iso(claimed_at) if claimed_at else None,
             assignee, reviewer, iso(reviewed_at) if reviewed_at else None,
             amount, 1 if is_high else 0, "Akshara LayoutLM", "0.9.4-sim",
             "branch_scan" if fixture.get("source") != "upload" else "upload",
             fixture.get("note", ""),
             int(reviewed_after * 60 * 0.62) if reviewed_after else None,
             len(fields), summary["low_confidence"], summary["invalid"],
             summary["verified"], summary["corrected"], iso(submitted)),
        )
        for f in fields:
            conn.execute(
                """INSERT INTO fields
                   (id,document_id,key,label,label_sub,section,value,original_value,confidence,
                    page,x,y,w,h,field_type,required,options,dir,validation_status,
                    validation_message,corrected,corrected_by,corrected_at,verified,display_order)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f["id"], f["document_id"], f["key"], f["label"], f["label_sub"],
                 f["section"], f["value"], f["original_value"], f["confidence"], f["page"],
                 f["x"], f["y"], f["w"], f["h"], f["field_type"], f["required"],
                 f["options"], f["dir"], f["validation_status"],
                 f["validation_message"], f["corrected"], f["corrected_by"],
                 f["corrected_at"], f["verified"], f["display_order"]),
            )
        _seed_events(conn, doc_id, fixture, fields, submitted, reviewed_at, assigned=assignee,
                     reviewer=reviewer, issues=issues)
        if fixture.get("note"):
            commenter = reviewer or assignee
            conn.execute(
                "INSERT INTO comments(document_id,user_id,body,created_at) VALUES (?,?,?,?)",
                (doc_id, commenter, fixture["note"], iso(submitted + timedelta(minutes=5))),
            )
        refresh_counts(conn, doc_id)
    # Refresh today's aggregate once the current work is in place.
    update_today_metrics(conn)


def _seed_events(conn, doc_id, fixture, fields, submitted, reviewed_at,
                 assigned=None, reviewer=None, issues=None):
    confidence = fixture["confidence"]
    low = sum(1 for f in fields if f["confidence"] < 0.8)
    invalid = [i for i in (issues or []) if i["status"] == "invalid"]
    add_event(conn, doc_id, None, "document.received",
              f"Scan received from {'branch' if fixture.get('source') != 'upload' else 'upload'} intake.",
              submitted, meta={"source": "branch"})
    add_event(conn, doc_id, None, "document.extracted",
              f"Layout-aware extraction complete · {len(fields)} fields · mean confidence {confidence * 100:.0f}%.",
              submitted + timedelta(minutes=1),
              meta={"engine": "Akshara LayoutLM", "confidence": confidence,
                    "low_confidence": low, "invalid": len(invalid)})
    status = fixture["status"]
    if status == "auto_approved":
        add_event(conn, doc_id, None, "document.auto_approved",
                  f"All checks passed above the 92% threshold; no human review required.",
                  submitted + timedelta(minutes=2),
                  meta={"threshold": 0.92})
        return
    reasons = []
    if low:
        reasons.append(f"{low} low-confidence fields")
    if invalid:
        reasons.append(f"{len(invalid)} validation issues")
    if fixture.get("quality") == "poor":
        reasons.append("poor scan quality")
    if not reasons:
        reasons.append("random quality sample")
    add_event(conn, doc_id, None, "document.routed",
              "Routed to human review: " + ", ".join(reasons) + ".",
              submitted + timedelta(minutes=2), meta={"reasons": reasons})

    if status == "queued":
        return
    claim_time = submitted + timedelta(minutes=4)
    add_event(conn, doc_id, assigned, "document.claimed",
              "Claimed from the shared review queue.", claim_time)
    if status == "in_review":
        return
    if status == "needs_rescan":
        add_event(conn, doc_id, assigned, "document.rescan",
                  fixture.get("rescan_reason", "Requested a clearer copy."),
                  submitted + timedelta(minutes=14))
        return
    if status == "escalated":
        add_event(conn, doc_id, "u_arjun", "document.escalated",
                  fixture.get("escalation_reason", "Escalated for supervisor review."),
                  submitted + timedelta(minutes=18))
        return
    if status in ("approved", "rejected") and reviewed_at:
        if fixture.get("reject_reason"):
            add_event(conn, doc_id, reviewer, "document.rejected",
                      fixture["reject_reason"], reviewed_at)
        else:
            add_event(conn, doc_id, reviewer, "document.approved",
                      "Reviewed, validated, and approved.", reviewed_at)
        for f in fields:
            if f.get("corrected"):
                add_event(conn, doc_id, reviewer, "field.corrected",
                          f"Corrected “{f['label']}”.",
                          reviewed_at - timedelta(minutes=2),
                          meta={"field": f["key"], "old": f["original_value"],
                                "new": f["value"]})


# --------------------------------------------------------------------------- read models
def _user(row: sqlite3.Row | dict | None) -> dict | None:
    if not row:
        return None
    d = dict(row)
    return {
        "id": d.get("id"), "name": d.get("name"), "email": d.get("email"),
        "role": d.get("role"), "title": d.get("title"), "initials": d.get("initials"),
        "color": d.get("color"),
    }


def _field(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "key": row["key"], "label": row["label"],
        "label_sub": row["label_sub"], "section": row["section"],
        "value": row["value"], "original_value": row["original_value"],
        "confidence": row["confidence"], "page": row["page"],
        "bbox": [row["x"], row["y"], row["w"], row["h"]],
        "type": row["field_type"], "required": bool(row["required"]),
        "options": json.loads(row["options"] or "[]"), "dir": row["dir"],
        "validation_status": row["validation_status"],
        "validation_message": row["validation_message"],
        "corrected": bool(row["corrected"]),
        "corrected_by": row["corrected_by"], "corrected_at": row["corrected_at"],
        "verified": bool(row["verified"]), "order": row["display_order"],
    }


def _doc(row: sqlite3.Row, assignee=None, reviewer=None) -> dict:
    due = parse_iso(row["due_at"])
    submitted = parse_iso(row["submitted_at"])
    now = utcnow()
    due_in = (due - now).total_seconds() / 60 if due else 0
    age = (now - submitted).total_seconds() / 60 if submitted else 0
    if row["status"] in CLOSED_STATUSES:
        sla_state = "closed"
    elif due_in < 0:
        sla_state = "overdue"
    elif due_in < 120:
        sla_state = "due_soon"
    else:
        sla_state = "on_track"
    reasons = _doc_reasons(row)
    risk = 0
    risk += 55 if sla_state == "overdue" else 0
    risk += int(row["low_count"]) * 7 + int(row["invalid_count"]) * 9
    risk += 18 if row["priority"] == "urgent" else 8 if row["priority"] == "high" else 0
    risk += 12 if row["is_high_value"] else 0
    risk += min(20, age / 60)

    page_files = []
    try:
        page_files = json.loads(row["page_files"]) if row["page_files"] else []
    except (json.JSONDecodeError, TypeError):
        page_files = []
    if not page_files:
        page_files = [{"file": row["image_file"], "width": row["width"], "height": row["height"]}]
    page_images = []
    for idx, page in enumerate(page_files):
        fname = page.get("file", row["image_file"])
        url = "/samples/" + fname if not fname.startswith("uploads/") else "/" + fname
        page_images.append({
            "no": idx + 1, "url": url, "file": fname,
            "width": int(page.get("width") or row["width"]),
            "height": int(page.get("height") or row["height"]),
        })
    return {
        "id": row["id"], "ref": row["ref"], "doc_type": row["doc_type"],
        "doc_type_label": row["title"], "title": row["title"],
        "customer_name": row["customer_name"], "language": row["language"],
        "language_name": row["language_name"], "script": row["script"],
        "status": row["status"], "status_label": STATUS_LABELS.get(row["status"], row["status"]),
        "priority": row["priority"], "confidence": row["confidence"],
        "quality": row["quality"], "pages": row["pages"],
        "image_file": row["image_file"],
        "image_url": "/samples/" + row["image_file"] if not row["image_file"].startswith("uploads/")
                     else "/" + row["image_file"],
        "page_images": page_images,
        "width": row["width"], "height": row["height"],
        "submitted_at": row["submitted_at"], "due_at": row["due_at"],
        "claimed_at": row["claimed_at"], "reviewed_at": row["reviewed_at"],
        "assignee": _user(assignee), "reviewer": _user(reviewer),
        "amount": row["amount"], "is_high_value": bool(row["is_high_value"]),
        "engine": row["engine"], "engine_version": row["engine_version"],
        "source": row["source"], "notes": row["notes"],
        "ocr_text": row["ocr_text"],
        "ocr_meta": json.loads(row["ocr_meta"]) if row["ocr_meta"] else None,
        "field_count": row["field_count"], "low_count": row["low_count"],
        "invalid_count": row["invalid_count"], "verified_count": row["verified_count"],
        "corrected_count": row["corrected_count"],
        "age_minutes": round(age), "due_in_minutes": round(due_in),
        "sla_state": sla_state, "reasons": reasons, "risk": round(risk),
        "progress": {
            "verified": row["verified_count"], "total": row["field_count"],
            "percent": round(100 * row["verified_count"] / row["field_count"]) if row["field_count"] else 0,
        },
    }


def get_document(doc_id: str) -> dict | None:
    with connect() as conn:
        return _get_document(conn, doc_id)


def _get_document(conn: sqlite3.Connection, doc_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not row:
        return None
    assignee = conn.execute("SELECT * FROM users WHERE id=?", (row["assignee_id"],)).fetchone() if row["assignee_id"] else None
    reviewer = conn.execute("SELECT * FROM users WHERE id=?", (row["reviewer_id"],)).fetchone() if row["reviewer_id"] else None
    doc = _doc(row, assignee, reviewer)
    fields = [_field(r) for r in conn.execute(
        "SELECT * FROM fields WHERE document_id=? ORDER BY display_order", (doc_id,))]
    doc["fields"] = fields
    doc["validation"] = validators.summarize(fields)
    doc["blocking_issues"] = [
        {"field_id": f["id"], "key": f["key"], "label": f["label"],
         "message": f["validation_message"]}
        for f in fields
        if f["validation_status"] == "invalid" and f["required"]
    ]
    events = []
    for e in conn.execute(
        """SELECT e.*, u.name AS user_name, u.initials AS user_initials, u.color AS user_color
           FROM events e LEFT JOIN users u ON u.id=e.user_id
           WHERE e.document_id=? ORDER BY e.created_at DESC, e.id DESC""", (doc_id,)):
        events.append({
            "id": e["id"], "action": e["action"], "detail": e["detail"],
            "created_at": e["created_at"],
            "meta": json.loads(e["meta"]) if e["meta"] else {},
            "user": ({"name": e["user_name"], "initials": e["user_initials"],
                      "color": e["user_color"]} if e["user_name"] else None),
        })
    doc["events"] = events
    doc["comments"] = [
        {"id": c["id"], "body": c["body"], "created_at": c["created_at"],
         "user": ({"name": c["user_name"], "initials": c["user_initials"],
                   "color": c["user_color"]} if c["user_name"] else None)}
        for c in conn.execute(
            """SELECT c.*, u.name AS user_name, u.initials AS user_initials, u.color AS user_color
               FROM comments c LEFT JOIN users u ON u.id=c.user_id
               WHERE c.document_id=? ORDER BY c.created_at""", (doc_id,))
    ]
    return doc


def get_user_by_email(email: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email)=lower(?)", (email,)).fetchone()
        return dict(row) if row else None


def get_user(user_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else None


def list_users() -> list[dict]:
    with connect() as conn:
        return [_user(r) for r in conn.execute("SELECT * FROM users ORDER BY role,name")]


def list_documents(view: str = "queue", status: str | None = None,
                   doc_type: str | None = None, script: str | None = None,
                   q: str | None = None, assignee: str | None = None,
                   current_user: str | None = None, limit: int = 200) -> dict:
    where = ["1=1"]
    params: list[Any] = []
    if view == "queue":
        where.append("d.status IN ('queued','in_review','escalated')")
    elif view == "rescan":
        where.append("d.status='needs_rescan'")
    elif view == "auto":
        where.append("d.status='auto_approved'")
    elif view == "closed":
        where.append("d.status IN ('approved','rejected')")
    elif view == "attention":
        where.append("d.status IN ('queued','in_review','escalated')")
        where.append("(d.low_count > 0 OR d.invalid_count > 0 OR d.due_at < ?)")
        params.append(iso())
    if status:
        where.append("d.status=?")
        params.append(status)
    if doc_type:
        where.append("d.doc_type=?")
        params.append(doc_type)
    if script:
        where.append("d.script=?")
        params.append(script)
    if assignee == "me" and current_user:
        where.append("d.assignee_id=?")
        params.append(current_user)
    elif assignee == "unassigned":
        where.append("d.assignee_id IS NULL")
    if q:
        where.append("(d.ref LIKE ? OR d.customer_name LIKE ? OR d.title LIKE ? OR d.language_name LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like, like])

    order = "CASE d.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 ELSE 2 END, d.due_at ASC"
    sql = f"""SELECT d.*, ua.name AS assignee_name, ua.initials AS assignee_initials,
                     ua.color AS assignee_color, ur.name AS reviewer_name,
                     ur.initials AS reviewer_initials, ur.color AS reviewer_color
              FROM documents d
              LEFT JOIN users ua ON ua.id=d.assignee_id
              LEFT JOIN users ur ON ur.id=d.reviewer_id
              WHERE {' AND '.join(where)}
              ORDER BY {order} LIMIT ?"""
    with connect() as conn:
        rows = conn.execute(sql, (*params, limit)).fetchall()
        items = []
        for r in rows:
            assignee_obj = ({"id": r["assignee_id"], "name": r["assignee_name"],
                             "initials": r["assignee_initials"], "color": r["assignee_color"]}
                            if r["assignee_name"] else None)
            reviewer_obj = ({"id": r["reviewer_id"], "name": r["reviewer_name"],
                             "initials": r["reviewer_initials"], "color": r["reviewer_color"]}
                            if r["reviewer_name"] else None)
            items.append(_doc(r, assignee_obj, reviewer_obj))
        counts = _counts(conn)
        total = conn.execute(f"SELECT COUNT(*) FROM documents d WHERE {' AND '.join(where)}",
                             params).fetchone()[0]
    return {"items": items, "total": total, "counts": counts}


def _counts(conn: sqlite3.Connection) -> dict:
    now = iso()
    row = conn.execute(
        """SELECT
             COUNT(*) AS all_count,
             SUM(CASE WHEN status='queued' THEN 1 ELSE 0 END) AS queued,
             SUM(CASE WHEN status='in_review' THEN 1 ELSE 0 END) AS in_review,
             SUM(CASE WHEN status='escalated' THEN 1 ELSE 0 END) AS escalated,
             SUM(CASE WHEN status='needs_rescan' THEN 1 ELSE 0 END) AS needs_rescan,
             SUM(CASE WHEN status='auto_approved' THEN 1 ELSE 0 END) AS auto_approved,
             SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approved,
             SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) AS rejected,
             SUM(CASE WHEN status IN ('queued','in_review','escalated') THEN 1 ELSE 0 END) AS queue,
             SUM(CASE WHEN status='queued' AND assignee_id IS NULL THEN 1 ELSE 0 END) AS unassigned,
             SUM(CASE WHEN status IN ('queued','in_review','escalated') AND due_at <= ? THEN 1 ELSE 0 END) AS overdue,
             SUM(CASE WHEN status IN ('queued','in_review','escalated') AND low_count > 0 THEN 1 ELSE 0 END) AS low_confidence
           FROM documents""", (now,)
    ).fetchone()
    out = {k: row[k] or 0 for k in row.keys()}
    out["all"] = out.pop("all_count")
    return out


def next_ref(conn: sqlite3.Connection) -> str:
    max_ref = conn.execute("SELECT MAX(CAST(substr(ref, 7) AS INTEGER)) FROM documents").fetchone()[0]
    n = max(2000, (max_ref or 2000) + 1)
    return f"AK-26-{n}"


# --------------------------------------------------------------------------- mutations
def add_event(conn: sqlite3.Connection, doc_id: str | None, user_id: str | None,
              action: str, detail: str, created_at: datetime | None = None,
              meta: dict | None = None) -> None:
    conn.execute(
        "INSERT INTO events(document_id,user_id,action,detail,meta,created_at) VALUES (?,?,?,?,?,?)",
        (doc_id, user_id, action, detail,
         json.dumps(meta, ensure_ascii=False) if meta else None,
         iso(created_at) if created_at else iso()),
    )


def refresh_counts(conn: sqlite3.Connection, doc_id: str) -> dict:
    row = conn.execute(
        """SELECT COUNT(*) AS total,
                  SUM(CASE WHEN confidence < 0.8 THEN 1 ELSE 0 END) AS low,
                  SUM(CASE WHEN validation_status='invalid' THEN 1 ELSE 0 END) AS invalid,
                  SUM(verified) AS verified, SUM(corrected) AS corrected
           FROM fields WHERE document_id=?""", (doc_id,)
    ).fetchone()
    vals = {
        "field_count": row["total"] or 0, "low_count": row["low"] or 0,
        "invalid_count": row["invalid"] or 0, "verified_count": row["verified"] or 0,
        "corrected_count": row["corrected"] or 0,
    }
    conn.execute(
        """UPDATE documents SET field_count=?, low_count=?, invalid_count=?,
           verified_count=?, corrected_count=? WHERE id=?""",
        (vals["field_count"], vals["low_count"], vals["invalid_count"],
         vals["verified_count"], vals["corrected_count"], doc_id),
    )
    return vals


def recompute_validation(conn: sqlite3.Connection, doc_id: str) -> list[dict]:
    doc = conn.execute("SELECT doc_type FROM documents WHERE id=?", (doc_id,)).fetchone()
    rows = conn.execute("SELECT * FROM fields WHERE document_id=? ORDER BY display_order",
                        (doc_id,)).fetchall()
    fields = []
    for r in rows:
        fields.append({
            "id": r["id"], "key": r["key"], "label": r["label"],
            "value": r["value"], "type": r["field_type"],
            "required": bool(r["required"]), "confidence": r["confidence"],
        })
    issues = validators.validate_document(doc["doc_type"] if doc else "", fields)
    for f in fields:
        conn.execute(
            "UPDATE fields SET validation_status=?, validation_message=? WHERE id=?",
            (f["validation_status"], f["validation_message"], f["id"]),
        )
    refresh_counts(conn, doc_id)
    return issues


def update_field(field_id: str, value: str, user_id: str) -> dict | None:
    with connect() as conn:
        field = conn.execute("SELECT * FROM fields WHERE id=?", (field_id,)).fetchone()
        if not field:
            return None
        doc = conn.execute("SELECT * FROM documents WHERE id=?", (field["document_id"],)).fetchone()
        if not doc or doc["status"] in CLOSED_STATUSES:
            raise ValueError("This document is locked. Reopen it before editing fields.")
        old = field["value"]
        corrected = 1 if value != field["original_value"] else field["corrected"]
        conn.execute(
            """UPDATE fields SET value=?, corrected=?, corrected_by=?, corrected_at=?, verified=1
               WHERE id=?""",
            (value, corrected, user_id, iso(), field_id),
        )
        issues = recompute_validation(conn, field["document_id"])
        add_event(conn, field["document_id"], user_id, "field.corrected",
                  f"Corrected “{field['label']}”.",
                  meta={"field": field["key"], "old": old, "new": value})
        out = _get_document(conn, field["document_id"])
        return out


def verify_high_confidence(doc_id: str, user_id: str, threshold: float = 0.9) -> dict | None:
    with connect() as conn:
        doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not doc or doc["status"] in CLOSED_STATUSES:
            raise ValueError("Document is not open for verification.")
        cur = conn.execute(
            """UPDATE fields SET verified=1 WHERE document_id=? AND confidence >= ?
               AND validation_status != 'invalid' AND verified=0""",
            (doc_id, threshold),
        )
        refresh_counts(conn, doc_id)
        add_event(conn, doc_id, user_id, "field.bulk_verified",
                  f"Accepted {cur.rowcount} high-confidence fields at ≥{threshold * 100:.0f}%.")
        return _get_document(conn, doc_id)


def claim_document(doc_id: str, user_id: str) -> dict | None:
    with connect() as conn:
        doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not doc:
            return None
        if doc["status"] not in ("queued", "escalated"):
            raise ValueError("This document cannot be claimed in its current state.")
        conn.execute(
            """UPDATE documents SET status='in_review', assignee_id=?, claimed_at=?
               WHERE id=?""", (user_id, iso(), doc_id))
        add_event(conn, doc_id, user_id, "document.claimed", "Claimed for review.")
        return _get_document(conn, doc_id)


def release_document(doc_id: str, user_id: str) -> dict | None:
    with connect() as conn:
        doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not doc:
            return None
        conn.execute(
            """UPDATE documents SET status='queued', assignee_id=NULL, claimed_at=NULL
               WHERE id=?""", (doc_id,))
        add_event(conn, doc_id, user_id, "document.released", "Returned to the shared queue.")
        return _get_document(conn, doc_id)


def approve_document(doc_id: str, user: dict, override_reason: str | None = None) -> dict:
    with connect() as conn:
        doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not doc:
            raise KeyError("Document not found.")
        if doc["status"] in CLOSED_STATUSES:
            raise ValueError("Document is already closed.")
        issues = recompute_validation(conn, doc_id)
        blocking = [i for i in issues if i["status"] == "invalid" and i["blocking"]]
        settings = get_settings()
        if doc["is_high_value"] and settings.get("require_supervisor_high_value") and user["role"] == "reviewer":
            raise PermissionError("High-value documents require a supervisor approval.")
        if blocking:
            if user["role"] not in ("supervisor", "admin") or not (override_reason or "").strip():
                e = ValueError("Resolve blocking validation issues or provide a supervisor override.")
                e.blocking = blocking  # type: ignore[attr-defined]
                raise e
        now = utcnow()
        claimed = parse_iso(doc["claimed_at"])
        review_seconds = int((now - (claimed or parse_iso(doc["submitted_at"]))).total_seconds())
        conn.execute(
            """UPDATE documents SET status='approved', reviewer_id=?, reviewed_at=?,
               review_seconds=?, assignee_id=COALESCE(assignee_id, ?), claimed_at=COALESCE(claimed_at, ?)
               WHERE id=?""",
            (user["id"], iso(now), max(1, review_seconds), user["id"], iso(now), doc_id))
        conn.execute("UPDATE fields SET verified=1 WHERE document_id=?", (doc_id,))
        refresh_counts(conn, doc_id)
        override = bool(blocking)
        detail = ("Approved with supervisor override: " + override_reason.strip()
                  if override else "Reviewed and approved.")
        add_event(conn, doc_id, user["id"], "document.approved", detail,
                  meta={"override": override, "override_reason": override_reason,
                        "blocking": [i["message"] for i in blocking]})
        if override:
            add_event(conn, doc_id, user["id"], "document.override",
                      "Supervisor override recorded with reason.", meta={"reason": override_reason})
        return _get_document(conn, doc_id)


def reject_document(doc_id: str, user: dict, reason: str) -> dict:
    with connect() as conn:
        doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not doc:
            raise KeyError("Document not found.")
        if doc["status"] in CLOSED_STATUSES:
            raise ValueError("Document is already closed.")
        now = utcnow()
        conn.execute(
            """UPDATE documents SET status='rejected', reviewer_id=?, reviewed_at=?,
               review_seconds=? WHERE id=?""",
            (user["id"], iso(now), max(1, int((now - (parse_iso(doc["claimed_at"]) or parse_iso(doc["submitted_at"]))).total_seconds())), doc_id))
        add_event(conn, doc_id, user["id"], "document.rejected", reason,
                  meta={"reason": reason})
        return _get_document(conn, doc_id)


def request_rescan(doc_id: str, user: dict, reason: str) -> dict:
    with connect() as conn:
        doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not doc:
            raise KeyError("Document not found.")
        conn.execute("UPDATE documents SET status='needs_rescan' WHERE id=?", (doc_id,))
        add_event(conn, doc_id, user["id"], "document.rescan", reason,
                  meta={"reason": reason})
        return _get_document(conn, doc_id)


def escalate_document(doc_id: str, user: dict, reason: str) -> dict:
    with connect() as conn:
        doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not doc:
            raise KeyError("Document not found.")
        conn.execute(
            "UPDATE documents SET status='escalated', priority='urgent' WHERE id=?",
            (doc_id,))
        add_event(conn, doc_id, user["id"], "document.escalated", reason,
                  meta={"reason": reason})
        return _get_document(conn, doc_id)


def reopen_document(doc_id: str, user: dict) -> dict:
    with connect() as conn:
        doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not doc:
            raise KeyError("Document not found.")
        conn.execute(
            """UPDATE documents SET status='queued', reviewer_id=NULL, reviewed_at=NULL,
               assignee_id=NULL, claimed_at=NULL WHERE id=?""", (doc_id,))
        conn.execute("UPDATE fields SET verified=0 WHERE document_id=?", (doc_id,))
        refresh_counts(conn, doc_id)
        add_event(conn, doc_id, user["id"], "document.reopened",
                  "Reopened for a fresh review pass.")
        return _get_document(conn, doc_id)


# --------------------------------------------------------------------------- dashboard / analytics
def dashboard() -> dict:
    docs_result = list_documents(view="all", limit=1000)
    docs = docs_result["items"]
    counts = docs_result["counts"]
    now = utcnow()
    today_start = iso(local_midnight_utc())
    today_docs = [d for d in docs if parse_iso(d["submitted_at"]) >= parse_iso(today_start)]
    open_docs = [d for d in docs if d["status"] in OPEN_STATUSES]
    overdue = [d for d in open_docs if d["sla_state"] == "overdue"]
    attention = sorted(open_docs, key=lambda d: -d["risk"])[:5]
    reviewed = [d for d in docs if d["reviewed_at"] and d["status"] in ("approved", "rejected")]
    avg_tat = (sum((parse_iso(d["reviewed_at"]) - parse_iso(d["submitted_at"])).total_seconds() / 60
                   for d in reviewed) / len(reviewed)) if reviewed else 0
    auto = [d for d in docs if d["status"] == "auto_approved"]
    script_mix: dict[str, int] = {}
    type_mix: dict[str, int] = {}
    workload: dict[str, dict] = {}
    for d in docs:
        script_mix[d["script"]] = script_mix.get(d["script"], 0) + 1
        type_mix[d["doc_type_label"]] = type_mix.get(d["doc_type_label"], 0) + 1
        if d["status"] in OPEN_STATUSES:
            key = d["assignee"]["name"] if d["assignee"] else "Unassigned"
            workload.setdefault(key, {"name": key, "initials": d["assignee"]["initials"] if d["assignee"] else "—",
                                      "color": d["assignee"]["color"] if d["assignee"] else "#B9B2A1",
                                      "count": 0, "overdue": 0})
            workload[key]["count"] += 1
            if d["sla_state"] == "overdue":
                workload[key]["overdue"] += 1
    with connect() as conn:
        trend = [dict(r) for r in conn.execute(
            "SELECT * FROM metrics_daily ORDER BY day DESC LIMIT 14")]
        trend.reverse()
        activity_rows = conn.execute(
            """SELECT e.*, u.name AS user_name, u.initials AS user_initials, u.color AS user_color,
                      d.ref AS doc_ref, d.id AS doc_id, d.title AS doc_title
               FROM events e LEFT JOIN users u ON u.id=e.user_id
               LEFT JOIN documents d ON d.id=e.document_id
               ORDER BY e.created_at DESC, e.id DESC LIMIT 9""").fetchall()
        activity = [{
            "id": r["id"], "action": r["action"], "detail": r["detail"],
            "created_at": r["created_at"], "doc_id": r["doc_id"], "doc_ref": r["doc_ref"],
            "doc_title": r["doc_title"],
            "user": ({"name": r["user_name"], "initials": r["user_initials"],
                      "color": r["user_color"]} if r["user_name"] else None),
        } for r in activity_rows]
    by_script = [{"script": k, "count": v} for k, v in sorted(script_mix.items(), key=lambda kv: -kv[1])]
    by_type = [{"type": k, "count": v} for k, v in sorted(type_mix.items(), key=lambda kv: -kv[1])]
    return {
        "kpis": {
            "open_queue": len(open_docs),
            "unassigned": counts["unassigned"],
            "overdue": len(overdue),
            "today_volume": len(today_docs),
            "auto_rate": round(100 * len(auto) / len(docs)) if docs else 0,
            "avg_confidence": round(100 * sum(d["confidence"] for d in docs) / len(docs)) if docs else 0,
            "avg_tat_minutes": round(avg_tat, 1),
            "reviewed_today": len([d for d in today_docs if d["status"] in ("approved", "rejected")]),
        },
        "counts": counts,
        "trend": trend,
        "queue_health": {
            "auto_approved": counts["auto_approved"],
            "approved": counts["approved"],
            "in_review": counts["in_review"],
            "queued": counts["queued"],
            "escalated": counts["escalated"],
            "needs_rescan": counts["needs_rescan"],
            "rejected": counts["rejected"],
        },
        "attention": attention,
        "activity": activity,
        "by_script": by_script,
        "by_type": by_type,
        "workload": list(workload.values()),
        "total_docs": len(docs),
        "totals": {
            "fields": sum(d["field_count"] for d in docs),
            "corrections": sum(d["corrected_count"] for d in docs),
        },
    }


def analytics(days: int = 14) -> dict:
    docs_result = list_documents(view="all", limit=1000)
    docs = docs_result["items"]
    with connect() as conn:
        trend = [dict(r) for r in conn.execute(
            "SELECT * FROM metrics_daily ORDER BY day DESC LIMIT ?", (days,))]
        trend.reverse()
        field_rows = conn.execute(
            """SELECT f.*, d.doc_type, d.language_name, d.script FROM fields f
               JOIN documents d ON d.id=f.document_id""").fetchall()
    fields = [dict(r) for r in field_rows]

    def aggregate(items: Iterable[dict], key: str) -> list[dict]:
        buckets: dict[str, list[dict]] = {}
        for d in items:
            buckets.setdefault(d[key] or "Unknown", []).append(d)
        out = []
        for name, group in buckets.items():
            reviewed = [d for d in group if d["reviewed_at"] and d["status"] in ("approved", "rejected")]
            auto = [d for d in group if d["status"] == "auto_approved"]
            tat = [(parse_iso(d["reviewed_at"]) - parse_iso(d["submitted_at"])).total_seconds() / 60
                   for d in reviewed]
            out.append({
                "name": name, "count": len(group),
                "auto_rate": round(100 * len(auto) / len(group)) if group else 0,
                "avg_confidence": round(100 * sum(d["confidence"] for d in group) / len(group)),
                "corrections": sum(d["corrected_count"] for d in group),
                "avg_tat": round(sum(tat) / len(tat), 1) if tat else 0,
                "invalid": sum(d["invalid_count"] for d in group),
            })
        return sorted(out, key=lambda x: -x["count"])

    bands = [
        {"label": "< 60%", "min": 0, "max": 0.6},
        {"label": "60–70%", "min": 0.6, "max": 0.7},
        {"label": "70–80%", "min": 0.7, "max": 0.8},
        {"label": "80–90%", "min": 0.8, "max": 0.9},
        {"label": "90–100%", "min": 0.9, "max": 1.01},
    ]
    for b in bands:
        group = [f for f in fields if b["min"] <= f["confidence"] < b["max"]]
        b["fields"] = len(group)
        b["corrected"] = sum(1 for f in group if f["corrected"])
        b["invalid"] = sum(1 for f in group if f["validation_status"] == "invalid")
        b["correction_rate"] = round(100 * b["corrected"] / len(group)) if group else 0

    error_map: dict[str, dict] = {}
    for f in fields:
        if f["validation_status"] == "invalid" or f["confidence"] < 0.7:
            key = f["label"]
            entry = error_map.setdefault(key, {"label": key, "count": 0, "low": 0, "invalid": 0})
            entry["count"] += 1
            if f["confidence"] < 0.7:
                entry["low"] += 1
            if f["validation_status"] == "invalid":
                entry["invalid"] += 1
    error_fields = sorted(error_map.values(), key=lambda x: -x["count"])[:8]

    reviewers_map: dict[str, dict] = {}
    for d in docs:
        if not d["reviewer"]:
            continue
        key = d["reviewer"]["name"]
        entry = reviewers_map.setdefault(key, {
            "name": key, "initials": d["reviewer"]["initials"],
            "color": d["reviewer"]["color"], "reviewed": 0, "corrections": 0,
            "tat": [], "auto": 0,
        })
        if d["status"] in ("approved", "rejected"):
            entry["reviewed"] += 1
            if d["reviewed_at"]:
                entry["tat"].append((parse_iso(d["reviewed_at"]) - parse_iso(d["submitted_at"])).total_seconds() / 60)
        entry["corrections"] += d["corrected_count"]
    reviewers = []
    for entry in reviewers_map.values():
        tat = entry.pop("tat")
        entry["avg_tat"] = round(sum(tat) / len(tat), 1) if tat else 0
        entry["correction_rate"] = round(100 * entry["corrections"] / entry["reviewed"]) if entry["reviewed"] else 0
        reviewers.append(entry)

    open_docs = [d for d in docs if d["status"] in OPEN_STATUSES]
    overdue = [d for d in open_docs if d["sla_state"] == "overdue"]
    on_time = [d for d in docs if d["status"] in ("approved", "rejected", "auto_approved")
               and (not d["reviewed_at"] or d["sla_state"] != "overdue")]
    return {
        "trend": trend,
        "by_type": aggregate(docs, "doc_type_label"),
        "by_language": aggregate(docs, "language_name"),
        "by_quality": aggregate(docs, "quality"),
        "confidence_bands": bands,
        "error_fields": error_fields,
        "reviewers": sorted(reviewers, key=lambda x: -x["reviewed"]),
        "totals": {
            "documents": len(docs),
            "fields": len(fields),
            "corrections": sum(1 for f in fields if f["corrected"]),
            "invalid": sum(1 for f in fields if f["validation_status"] == "invalid"),
            "open": len(open_docs),
            "overdue": len(overdue),
            "sla_compliance": round(100 * (len(on_time) / len(docs))) if docs else 0,
        },
    }


def audit_events(q: str | None = None, action: str | None = None,
                 user_id: str | None = None, limit: int = 80, offset: int = 0) -> dict:
    where = ["1=1"]
    params: list[Any] = []
    if action:
        where.append("e.action=?")
        params.append(action)
    if user_id:
        where.append("e.user_id=?")
        params.append(user_id)
    if q:
        where.append("(e.detail LIKE ? OR d.ref LIKE ? OR u.name LIKE ? OR d.customer_name LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like, like])
    base = f"""FROM events e LEFT JOIN users u ON u.id=e.user_id
               LEFT JOIN documents d ON d.id=e.document_id WHERE {' AND '.join(where)}"""
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) " + base, params).fetchone()[0]
        rows = conn.execute(
            f"""SELECT e.*, u.name AS user_name, u.initials AS user_initials,
                       u.color AS user_color, d.ref AS doc_ref, d.title AS doc_title,
                       d.customer_name AS customer_name
                {base} ORDER BY e.created_at DESC, e.id DESC LIMIT ? OFFSET ?""",
            (*params, limit, offset)).fetchall()
    items = [{
        "id": r["id"], "action": r["action"], "detail": r["detail"],
        "created_at": r["created_at"], "doc_id": r["document_id"],
        "doc_ref": r["doc_ref"], "doc_title": r["doc_title"],
        "customer_name": r["customer_name"],
        "meta": json.loads(r["meta"]) if r["meta"] else {},
        "user": ({"name": r["user_name"], "initials": r["user_initials"],
                  "color": r["user_color"]} if r["user_name"] else None),
    } for r in rows]
    return {"items": items, "total": total}  # type: ignore[return-value]


# --------------------------------------------------------------------------- intake
def _new_doc_id() -> str:
    return "doc_" + uuid.uuid4().hex[:10]


def _insert_fields(conn, doc_id: str, fields: list[dict]) -> tuple[list[dict], dict]:
    issues = validators.validate_document(
        conn.execute("SELECT doc_type FROM documents WHERE id=?", (doc_id,)).fetchone()["doc_type"],
        fields,
    )
    for idx, f in enumerate(fields):
        bbox = f.get("bbox") or [0, 0, 0, 0]
        conn.execute(
            """INSERT INTO fields
               (id,document_id,key,label,label_sub,section,value,original_value,confidence,
                page,x,y,w,h,field_type,required,options,dir,validation_status,
                validation_message,corrected,corrected_by,corrected_at,verified,display_order)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (f"{doc_id}:{f['key']}", doc_id, f["key"], f["label"], f.get("label_sub", ""),
             f.get("section", ""), f.get("value", ""), f.get("value", ""),
             float(f.get("confidence", 0)), int(f.get("page", 1) or 1),
             bbox[0], bbox[1], bbox[2], bbox[3],
             f.get("type", "text"), 1 if f.get("required", True) else 0,
             json.dumps(f.get("options", []), ensure_ascii=False), f.get("dir", "ltr"),
             f["validation_status"], f["validation_message"], 0, None, None, 0, idx),
        )
    return fields, validators.summarize(fields)


def create_demo_intake(sample_id: str, user: dict) -> dict:
    fixture = load_fixture(sample_id)
    if not fixture:
        raise KeyError("Sample not found.")
    settings = get_settings()
    with connect() as conn:
        doc_id = _new_doc_id()
        ref = next_ref(conn)
        now = utcnow()
        fields = [dict(f) for f in fixture["fields"]]
        for f in fields:
            f["value"] = f.get("value", "")
            f["original_value"] = f["value"]
            f["verified"] = 0
            f["corrected"] = 0
        issues = validators.validate_document(fixture["kind"], fields)
        summary = validators.summarize(fields)
        amount = fixture.get("amount")
        is_high = bool(amount and amount >= settings["high_value_threshold"])
        conf = fixture["confidence"]
        blocking = summary["invalid"]
        auto = (conf >= settings["auto_approve_threshold"] and blocking == 0
                and not (is_high and settings.get("require_supervisor_high_value")))
        status = "auto_approved" if auto else "queued"
        priority = "urgent" if is_high else ("high" if conf < settings["review_threshold"] else "normal")
        due = now + timedelta(hours=settings["urgent_sla_hours"] if priority == "urgent" else settings["sla_hours"])
        conn.execute(
            """INSERT INTO documents
               (id,ref,doc_type,title,customer_name,language,language_name,script,status,priority,
                confidence,quality,pages,image_file,width,height,submitted_at,due_at,claimed_at,
                assignee_id,reviewer_id,reviewed_at,amount,is_high_value,engine,engine_version,
                source,notes,review_seconds,field_count,low_count,invalid_count,verified_count,
                corrected_count,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (doc_id, ref, fixture["kind"], fixture["doc_type_label"],
             fixture["customer_name"], fixture["language"], fixture["language_name"],
             fixture["script"], status, priority, conf, fixture.get("quality"), 1,
             fixture["preview"], 1240, 1754, iso(now), iso(due), None, None, None, None,
             amount, 1 if is_high else 0, "Akshara LayoutLM", "0.9.4-sim",
             "demo_intake", "Simulated intake from the specimen library.", None,
             len(fields), summary["low_confidence"], summary["invalid"], 0, 0, iso(now)),
        )
        _insert_fields(conn, doc_id, fields)
        add_event(conn, doc_id, user["id"], "document.received",
                  f"Simulated intake started by {user['name']}.", now)
        add_event(conn, doc_id, None, "document.extracted",
                  f"Extraction complete · {len(fields)} fields · mean confidence {conf * 100:.0f}%.",
                  now + timedelta(seconds=1),
                  meta={"engine": "Akshara LayoutLM", "confidence": conf})
        if auto:
            add_event(conn, doc_id, None, "document.auto_approved",
                      "All checks passed; routed straight through.",
                      now + timedelta(seconds=2), meta={"threshold": settings["auto_approve_threshold"]})
        else:
            add_event(conn, doc_id, None, "document.routed",
                      "Routed to review after extraction.",
                      now + timedelta(seconds=2), meta={"reasons": ["simulated intake"]})
        refresh_counts(conn, doc_id)
        update_today_metrics(conn)
    return {"id": doc_id, "status": status, "ref": ref, "auto": auto}


def create_manual_intake(filename: str, data: bytes, doc_type: str, user: dict,
                         width: int = 1240, height: int = 1754) -> dict:
    if doc_type not in DOC_TYPES:
        raise ValueError("Unknown document type.")
    with connect() as conn:
        template = conn.execute(
            "SELECT * FROM documents WHERE doc_type=? ORDER BY submitted_at DESC LIMIT 1",
            (doc_type,)).fetchone()
        if not template:
            raise ValueError("No template available for this document type.")
        template_fields = conn.execute(
            "SELECT * FROM fields WHERE document_id=? ORDER BY display_order",
            (template["id"],)).fetchall()
        doc_id = _new_doc_id()
        ref = next_ref(conn)
        now = utcnow()
        ext = ".jpg" if data[:3] == b"\xff\xd8\xff" else ".png"
        rel = f"uploads/{doc_id}{ext}"
        path = UPLOADS_DIR / f"{doc_id}{ext}"
        path.write_bytes(data)
        settings = get_settings()
        due = now + timedelta(hours=settings["sla_hours"])
        conn.execute(
            """INSERT INTO documents
               (id,ref,doc_type,title,customer_name,language,language_name,script,status,priority,
                confidence,quality,pages,image_file,width,height,submitted_at,due_at,claimed_at,
                assignee_id,reviewer_id,reviewed_at,amount,is_high_value,engine,engine_version,
                source,notes,review_seconds,field_count,low_count,invalid_count,verified_count,
                corrected_count,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (doc_id, ref, doc_type, DOC_TYPES[doc_type]["label"], None, "en", "English",
             "Unknown", "queued", "normal", 0.0, "unknown", 1, rel, width, height,
             iso(now), iso(due), None, None, None, None, None, 0,
             "Manual indexing", "—", "upload", f"Uploaded file: {filename}", None,
             len(template_fields), len(template_fields), 0, 0, 0, iso(now)),
        )
        blank_fields = []
        for f in template_fields:
            blank_fields.append({
                "key": f["key"], "label": f["label"], "label_sub": f["label_sub"],
                "section": f["section"], "value": "", "confidence": 0.0,
                "bbox": [0, 0, 0, 0], "type": f["field_type"],
                "required": bool(f["required"]), "options": json.loads(f["options"] or "[]"),
                "dir": "ltr",
            })
        _insert_fields(conn, doc_id, blank_fields)
        add_event(conn, doc_id, user["id"], "document.received",
                  f"Uploaded “{filename}” for manual indexing.", now)
        add_event(conn, doc_id, user["id"], "document.routed",
                  "No OCR provider is configured for this upload; created a manual indexing task.",
                  now + timedelta(seconds=1))
        refresh_counts(conn, doc_id)
    return {"id": doc_id, "ref": ref, "status": "queued"}


OCR_LANG_NAMES = {"eng": "English", "hin": "Hindi", "mar": "Marathi",
                  "tam": "Tamil", "ben": "Bengali", "ara": "Arabic"}
OCR_SCRIPTS = {"eng": "Latin", "hin": "Devanagari", "mar": "Devanagari",
               "tam": "Tamil", "ben": "Bengali", "ara": "Arabic"}


def template_fields(doc_type: str) -> list[dict]:
    """Field schema from the most recent specimen of this document type."""
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM documents WHERE doc_type=? ORDER BY submitted_at DESC LIMIT 1",
            (doc_type,)).fetchone()
        if not row:
            raise ValueError("No schema is available for this document type.")
        out = []
        for f in conn.execute(
                "SELECT * FROM fields WHERE document_id=? ORDER BY display_order",
                (row["id"],)):
            out.append({
                "key": f["key"], "label": f["label"], "label_sub": f["label_sub"],
                "section": f["section"], "field_type": f["field_type"],
                "type": f["field_type"], "required": bool(f["required"]),
                "options": json.loads(f["options"] or "[]"),
            })
        return out


def _infer_amount(fields: list[dict]) -> float | None:
    for key in ("total", "claim_amount", "loan_amount", "subtotal"):
        fld = next((f for f in fields if f["key"] == key), None)
        if fld and fld.get("value"):
            amount = validators.parse_amount(fld["value"])
            if amount and amount > 0:
                return amount
    return None


def _guess_customer(fields: list[dict]) -> str:
    for key in ("full_name", "insured_name", "applicant_name", "customer_name"):
        fld = next((f for f in fields if f["key"] == key), None)
        if fld and fld.get("value"):
            return str(fld["value"])[:120]
    return "Unknown customer"


def create_ocr_intake(filename: str, data: bytes | None, doc_type: str, user: dict,
                      width: int, height: int, ocr_result, fields: list[dict],
                      summary: dict, page_files: list[dict] | None = None) -> dict:
    """Persist a genuinely OCR'd upload and its extracted schema.

    `page_files` is used for a multi-page PDF that has already been rasterised;
    each item is {path, width, height}. For a single image, pass its bytes and
    the function writes one page under uploads/.
    """
    if doc_type not in DOC_TYPES:
        raise ValueError("Unknown document type.")
    settings = get_settings()
    with connect() as conn:
        doc_id = _new_doc_id()
        ref = next_ref(conn)
        now = utcnow()
        if page_files:
            stored_pages = []
            for idx, page in enumerate(page_files):
                src = Path(page["path"])
                ext = src.suffix.lower() or ".png"
                rel = f"uploads/{doc_id}_p{idx + 1}{ext}"
                dest = UPLOADS_DIR / Path(rel).name
                if src.resolve() != dest.resolve():
                    shutil.move(str(src), str(dest))
                stored_pages.append({
                    "file": rel,
                    "width": int(page.get("width") or width),
                    "height": int(page.get("height") or height),
                })
            page_json = json.dumps(stored_pages, ensure_ascii=False)
            page_count = len(stored_pages)
            rel = stored_pages[0]["file"]
            width = stored_pages[0]["width"]
            height = stored_pages[0]["height"]
        else:
            if data is None:
                raise ValueError("No image data supplied.")
            ext = ".jpg" if data[:3] == b"\xff\xd8\xff" else ".png"
            rel = f"uploads/{doc_id}{ext}"
            (UPLOADS_DIR / f"{doc_id}{ext}").write_bytes(data)
            stored_pages = [{"file": rel, "width": width, "height": height}]
            page_json = json.dumps(stored_pages, ensure_ascii=False)
            page_count = 1

        amount = _infer_amount(fields)
        is_high = bool(amount and amount >= settings["high_value_threshold"])
        confidence = float(summary.get("document_confidence", 0))
        quality = summary.get("quality", "fair")
        priority = "urgent" if is_high else ("high" if confidence < settings["review_threshold"] else "normal")
        hours = settings["urgent_sla_hours"] if priority == "urgent" else settings["sla_hours"]
        due = now + timedelta(hours=hours)
        lang = ocr_result.language
        meta = {**ocr_result.meta(), **summary,
                "provider": "tesseract", "extracted_fields": summary.get("extracted", 0),
                "pages": page_count}
        note = (f"Local OCR · {ocr_result.word_count} words · "
                f"{ocr_result.mean_conf * 100:.0f}% mean OCR confidence · "
                f"{summary.get('extracted', 0)}/{len(fields)} fields extracted"
                + (f" across {page_count} pages." if page_count > 1 else "."))
        total_pdf_pages = int(summary.get("pdf_total_pages") or 0)
        if total_pdf_pages > page_count:
            note += f" First {page_count} of {total_pdf_pages} PDF pages rendered."
        conn.execute(
            """INSERT INTO documents
               (id,ref,doc_type,title,customer_name,language,language_name,script,status,priority,
                confidence,quality,pages,image_file,page_files,width,height,submitted_at,due_at,
                claimed_at,assignee_id,reviewer_id,reviewed_at,amount,is_high_value,engine,
                engine_version,source,notes,ocr_text,ocr_meta,review_seconds,field_count,
                low_count,invalid_count,verified_count,corrected_count,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (doc_id, ref, doc_type, DOC_TYPES[doc_type]["label"],
             _guess_customer(fields), lang, OCR_LANG_NAMES.get(lang, "Unknown"),
             OCR_SCRIPTS.get(lang, "Unknown"), "queued", priority, confidence, quality,
             page_count, rel, page_json, width, height, iso(now), iso(due), None, None, None,
             None, amount, 1 if is_high else 0, ocr_result.engine, ocr_result.version,
             "upload_ocr", note, ocr_result.text,
             json.dumps(meta, ensure_ascii=False), None, len(fields),
             sum(1 for f in fields if f.get("value") and f.get("confidence", 0) < 0.8),
             sum(1 for f in fields if f.get("value") and f.get("confidence", 0) < 0.5), 0, 0,
             iso(now)),
        )
        _insert_fields(conn, doc_id, fields)
        add_event(conn, doc_id, user["id"], "document.received",
                  f"Uploaded “{filename}” for local OCR.", now)
        add_event(conn, doc_id, None, "document.extracted",
                  note, now + timedelta(seconds=1),
                  meta={"engine": ocr_result.engine, "version": ocr_result.version,
                        "confidence": ocr_result.mean_conf, "words": ocr_result.word_count,
                        "extracted": summary.get("extracted", 0), "pages": page_count})
        add_event(conn, doc_id, None, "document.routed",
                  "Local OCR result routed to human review. OCR values are not auto-approved.",
                  now + timedelta(seconds=2),
                  meta={"reasons": ["local OCR", "human verification required"]})
        refresh_counts(conn, doc_id)
        update_today_metrics(conn)
    return {"id": doc_id, "ref": ref, "status": "queued", "ocr": meta,
            "pages": page_count}


def reset_demo_data() -> None:
    init_db(reset=True)
