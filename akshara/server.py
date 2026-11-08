"""Akshara HTTP application.

Run:
    python -m akshara.server --port 8765

The server is intentionally dependency-free: ThreadingHTTPServer, SQLite, and
a static SPA under web/. The extraction layer is represented by fixture
adapters so the review workflow can be explored without cloud credentials.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import shutil
import sys
import traceback
import uuid
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import __version__, auth, db, extract, ocr, pdf, validators
from .config import (DATA_DIR, DOC_TYPES, ROLE_LABELS, SAMPLES_DIR,
                     SETTINGS_SCHEMA, UPLOADS_DIR, WEB_DIR)

MIME_FALLBACK = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
}
MAX_JSON = 2 * 1024 * 1024
MAX_UPLOAD = 15 * 1024 * 1024


class ApiError(Exception):
    def __init__(self, status: int, message: str, code: str | None = None, details=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code
        self.details = details


def public_user(user: dict) -> dict:
    return {k: user[k] for k in ("id", "name", "email", "role", "title", "initials", "color")}


def providers() -> list[dict]:
    azure = bool(os.environ.get("AZURE_DOC_INTELLIGENCE_ENDPOINT")
                 and os.environ.get("AZURE_DOC_INTELLIGENCE_KEY"))
    tess = ocr.status()
    return [
        {"id": "layoutlm", "name": "Akshara LayoutLM", "kind": "Specimen adapter + calibration",
         "status": "active", "detail": "Deterministic fixture engine · 18 specimens",
         "icon": "sparkles"},
        {"id": "tesseract", "name": "Tesseract 5", "kind": "Local on-premise OCR",
         "status": "active" if tess["available"] else "not_installed",
         "detail": tess["detail"] if tess["available"] else "Install Tesseract to OCR uploads",
         "icon": "terminal", "languages": tess["languages"], "version": tess["version"]},
        {"id": "pdf", "name": "Windows PDF Renderer", "kind": "Local page rasterisation",
         "status": "active" if pdf.available() else "not_installed",
         "detail": "Windows.Data.Pdf · up to 6 pages per upload" if pdf.available()
                   else "PDF rendering is unavailable on this platform",
         "icon": "layers"},
        {"id": "azure", "name": "Azure Document Intelligence", "kind": "Cloud OCR + key/value",
         "status": "configured" if azure else "needs_config",
         "detail": "Credentials detected" if azure else "Set AZURE_DOC_INTELLIGENCE_ENDPOINT and _KEY",
         "icon": "cloud"},
        {"id": "manual", "name": "Manual indexing", "kind": "Human fallback",
         "status": "active", "detail": "Used when local OCR cannot read a scan",
         "icon": "keyboard"},
    ]


def meta() -> dict:
    ocr_status = {k: v for k, v in ocr.status().items() if k != "path"}
    languages = [
        {"code": "en", "name": "English", "script": "Latin"},
        {"code": "hi", "name": "Hindi", "script": "Devanagari"},
        {"code": "mr", "name": "Marathi", "script": "Devanagari"},
        {"code": "ta", "name": "Tamil", "script": "Tamil"},
        {"code": "bn", "name": "Bengali", "script": "Bengali"},
        {"code": "ar", "name": "Arabic", "script": "Arabic"},
    ]
    return {
        "version": __version__,
        "doc_types": [{"id": k, **v} for k, v in DOC_TYPES.items()],
        "languages": languages,
        "providers": providers(),
        "ocr": ocr_status,
        "pdf": pdf.status(),
        "roles": ROLE_LABELS,
        "validation_rules": [
            {"key": "required", "label": "Required fields", "blocking": True,
             "detail": "Every mandatory field must contain a value."},
            {"key": "date_order", "label": "Date sequence", "blocking": True,
             "detail": "Discharge cannot precede admission."},
            {"key": "invoice_totals", "label": "Invoice arithmetic", "blocking": True,
             "detail": "Subtotal + CGST + SGST must equal the total."},
            {"key": "identifier_format", "label": "Identifier formats", "blocking": True,
             "detail": "PAN, IFSC, GSTIN, mobile, PIN and account formats are checked."},
            {"key": "sum_insured", "label": "Sum insured ceiling", "blocking": True,
             "detail": "A claim cannot exceed the policy sum insured."},
            {"key": "affordability", "label": "Affordability", "blocking": False,
             "detail": "Existing EMI above 60% of income creates a warning."},
        ],
    }


def image_dimensions(data: bytes) -> tuple[int, int] | None:
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data[:3] == b"\xff\xd8\xff":
        i = 2
        n = len(data)
        while i + 9 < n:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            if i + 4 > n:
                return None
            size = int.from_bytes(data[i + 2:i + 4], "big")
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                if i + 9 <= n:
                    h = int.from_bytes(data[i + 5:i + 7], "big")
                    w = int.from_bytes(data[i + 7:i + 9], "big")
                    return w, h
            i += max(2, size + 2)
    return None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = f"Akshara/{__version__}"

    # ------------------------------------------------------------------ plumbing
    def log_message(self, fmt: str, *args):
        sys.stdout.write("%s  %s\n" % (self.log_date_time_string(), fmt % args))
        sys.stdout.flush()

    def _security_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; img-src 'self' data:; "
                         "style-src 'self' 'unsafe-inline'; script-src 'self'; "
                         "font-src 'self'; connect-src 'self'; frame-ancestors 'none'")

    def send_json(self, payload, status: int = 200, cookie: str | None = None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: int, message: str, code: str | None = None, details=None):
        payload = {"error": message, "code": code or "error"}
        if details is not None:
            payload["details"] = details
        self.send_json(payload, status)

    def read_body(self, limit: int = MAX_JSON) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ApiError(400, "Invalid Content-Length.")
        if length > limit:
            raise ApiError(413, "Request body is too large.")
        return self.rfile.read(length) if length else b""

    def read_json(self) -> dict:
        raw = self.read_body()
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(400, "Request body must be valid JSON.")
        if not isinstance(data, dict):
            raise ApiError(400, "Request body must be a JSON object.")
        return data

    def user(self) -> dict | None:
        cookies = auth.parse_cookies(self.headers.get("Cookie"))
        payload = auth.read_session(cookies.get(auth.COOKIE_NAME))
        if not payload:
            return None
        user = db.get_user(payload.get("uid", ""))
        if not user:
            return None
        user = public_user(user)
        user["csrf"] = payload.get("csrf")
        return user

    def require_user(self) -> dict:
        user = self.user()
        if not user:
            raise ApiError(401, "Sign in to continue.", "unauthorized")
        return user

    def require_csrf(self, user: dict):
        token = self.headers.get("X-CSRF-Token")
        if not token or token != user.get("csrf"):
            raise ApiError(403, "Security token missing or invalid. Refresh and try again.", "csrf")

    def require_role(self, user: dict, *roles: str):
        if user["role"] not in roles:
            raise ApiError(403, "Your role does not allow this action.", "forbidden")

    # ------------------------------------------------------------------ HTTP verbs
    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def do_PATCH(self):
        self.dispatch("PATCH")

    def do_PUT(self):
        self.dispatch("PUT")

    def dispatch(self, method: str):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path.startswith("/api/"):
                self.handle_api(method, path, parse_qs(parsed.query))
            elif method == "GET":
                self.serve_static(path)
            else:
                raise ApiError(404, "Not found.")
        except ApiError as exc:
            self.send_error_json(exc.status, exc.message, exc.code, exc.details)
        except PermissionError as exc:
            self.send_error_json(403, str(exc), "forbidden")
        except Exception as exc:  # noqa: BLE001 - top-level safety net
            traceback.print_exc()
            self.send_error_json(500, "Something went wrong on the server.", "server_error",
                                 {"type": type(exc).__name__})

    # ------------------------------------------------------------------ static
    def serve_static(self, path: str):
        if path in ("/", "/index.html"):
            target = WEB_DIR / "index.html"
            return self.send_file(target, cache="no-cache")
        if path in ("/favicon.ico", "/favicon.svg"):
            return self.send_file(WEB_DIR / "favicon.svg", cache="public, max-age=86400")
        if path.startswith("/assets/"):
            return self.send_file_under(WEB_DIR / "assets", path[len("/assets/"):], "public, max-age=3600")
        if path.startswith("/samples/"):
            return self.send_file_under(SAMPLES_DIR, path[len("/samples/"):], "public, max-age=86400")
        if path.startswith("/uploads/"):
            return self.send_file_under(UPLOADS_DIR, path[len("/uploads/"):], "private, max-age=60")
        raise ApiError(404, "Not found.")

    def send_file_under(self, root: Path, rel: str, cache: str):
        if not rel or ".." in rel or rel.startswith("/") or "\x00" in rel:
            raise ApiError(404, "Not found.")
        target = (root / rel).resolve()
        root_resolved = root.resolve()
        if root_resolved not in target.parents or not target.is_file():
            raise ApiError(404, "Not found.")
        self.send_file(target, cache=cache)

    def send_file(self, target: Path, cache: str = "no-cache"):
        if not target.is_file():
            raise ApiError(404, "Not found.")
        data = target.read_bytes()
        ext = target.suffix.lower()
        ctype = MIME_FALLBACK.get(ext) or mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self._security_headers()
        self.end_headers()
        self.wfile.write(data)

    # ------------------------------------------------------------------ api
    def handle_api(self, method: str, path: str, query: dict):
        # Auth endpoints -------------------------------------------------
        if method == "POST" and path == "/api/login":
            return self.api_login()
        if method == "POST" and path == "/api/demo-login":
            return self.api_demo_login()
        if method == "POST" and path == "/api/logout":
            return self.api_logout()
        if method == "GET" and path == "/api/health":
            return self.send_json({"ok": True, "version": __version__})

        user = self.require_user()

        if method == "GET" and path == "/api/session":
            counts = db.list_documents(view="all", limit=1)["counts"]
            return self.send_json({
                "user": user, "settings": db.get_settings(), "meta": meta(),
                "counts": counts, "csrf": user["csrf"],
            })

        if method == "GET" and path == "/api/dashboard":
            return self.send_json(db.dashboard())

        if method == "GET" and path == "/api/documents":
            view = (query.get("view") or ["queue"])[0]
            status = (query.get("status") or [None])[0]
            doc_type = (query.get("type") or [None])[0]
            script = (query.get("script") or [None])[0]
            assignee = (query.get("assignee") or [None])[0]
            q = (query.get("q") or [None])[0]
            result = db.list_documents(view=view, status=status, doc_type=doc_type,
                                       script=script, q=q, assignee=assignee,
                                       current_user=user["id"])
            return self.send_json(result)

        if method == "GET" and path == "/api/analytics":
            days = int((query.get("days") or ["14"])[0])
            days = max(7, min(days, 28))
            return self.send_json(db.analytics(days=days))

        if method == "GET" and path == "/api/audit":
            q = (query.get("q") or [None])[0]
            action = (query.get("action") or [None])[0]
            user_id = (query.get("user") or [None])[0]
            try:
                limit = min(200, max(1, int((query.get("limit") or ["80"])[0])))
                offset = max(0, int((query.get("offset") or ["0"])[0]))
            except ValueError:
                raise ApiError(400, "Invalid pagination.")
            return self.send_json(db.audit_events(q=q, action=action, user_id=user_id,
                                                  limit=limit, offset=offset))

        if method == "GET" and path == "/api/settings":
            return self.send_json({"settings": db.get_settings(), "meta": meta(),
                                   "providers": providers()})

        if method == "GET" and path == "/api/intake/samples":
            return self.send_json({"items": db.fixture_index()})

        if method == "GET" and path == "/api/users":
            return self.send_json({"items": db.list_users()})

        if method == "PUT" and path == "/api/settings":
            self.require_csrf(user)
            self.require_role(user, "supervisor", "admin")
            return self.api_update_settings(user)

        if method == "POST" and path == "/api/intake/demo":
            self.require_csrf(user)
            body = self.read_json()
            sample_id = str(body.get("sample_id", "")).strip()
            if not sample_id:
                raise ApiError(400, "Choose a specimen to process.")
            try:
                result = db.create_demo_intake(sample_id, user)
            except KeyError:
                raise ApiError(404, "Specimen not found.")
            return self.send_json(result, 201)

        if method == "POST" and path == "/api/intake/upload":
            self.require_csrf(user)
            return self.api_upload(user)

        if method == "POST" and path == "/api/admin/reset":
            self.require_csrf(user)
            self.require_role(user, "admin")
            self.read_body()  # consume even though the reset needs no payload
            db.reset_demo_data()
            return self.send_json({"ok": True})

        # Document detail -----------------------------------------------
        m = re.fullmatch(r"/api/documents/([^/]+)", path)
        if m and method == "GET":
            return self.api_document(m.group(1), user)

        # Field edit -----------------------------------------------------
        m = re.fullmatch(r"/api/fields/([^/]+)", path)
        if m and method == "PATCH":
            self.require_csrf(user)
            return self.api_update_field(m.group(1), user)

        # Document actions ----------------------------------------------
        m = re.fullmatch(r"/api/documents/([^/]+)/([a-z\-]+)", path)
        if m and method == "POST":
            self.require_csrf(user)
            return self.api_document_action(m.group(1), m.group(2), user)

        raise ApiError(404, "Not found.")

    # ------------------------------------------------------------------ auth handlers
    def api_login(self):
        body = self.read_json()
        email = str(body.get("email", "")).strip()
        password = str(body.get("password", ""))
        if not email or not password:
            raise ApiError(400, "Enter your email and password.")
        user = db.get_user_by_email(email)
        if not user or not auth.verify_password(password, user["password_hash"]):
            time.sleep(0.25)
            raise ApiError(401, "Email or password is incorrect.", "bad_credentials")
        cookie, _ = auth.create_session(user["id"])
        self.send_json({"ok": True, "user": public_user(user)},
                       cookie=auth.cookie_header(cookie))

    def api_demo_login(self):
        if not db.get_settings().get("demo_mode"):
            raise ApiError(403, "Demo access is disabled.", "demo_disabled")
        body = self.read_json()
        email = str(body.get("email", "")).strip()
        user = db.get_user_by_email(email)
        if not user:
            raise ApiError(404, "Demo account not found.")
        cookie, _ = auth.create_session(user["id"])
        self.send_json({"ok": True, "user": public_user(user)},
                       cookie=auth.cookie_header(cookie))

    def api_logout(self):
        self.read_body()  # keep-alive safe when the client sends an empty JSON object
        self.send_json({"ok": True}, cookie=auth.clear_cookie_header())

    # ------------------------------------------------------------------ documents
    def _actions(self, doc: dict, user: dict) -> dict:
        open_doc = doc["status"] in ("queued", "in_review", "escalated")
        assigned_to_me = bool(doc.get("assignee") and doc["assignee"]["id"] == user["id"])
        supervisor = user["role"] in ("supervisor", "admin")
        can_work = open_doc and (assigned_to_me or supervisor)
        return {
            "claim": open_doc and not doc.get("assignee") and doc["status"] in ("queued", "escalated"),
            "release": open_doc and assigned_to_me,
            "edit": can_work,
            "approve": can_work,
            "reject": can_work,
            "rescan": can_work,
            "escalate": can_work,
            "verify_high_confidence": can_work,
            "reopen": doc["status"] in ("approved", "rejected") and supervisor,
            "override": supervisor and bool(doc.get("blocking_issues")),
            "supervisor": supervisor,
        }

    def api_document(self, doc_id: str, user: dict):
        doc = db.get_document(doc_id)
        if not doc:
            raise ApiError(404, "Document not found.")
        doc["actions"] = self._actions(doc, user)
        return self.send_json(doc)

    def api_update_field(self, field_id: str, user: dict):
        body = self.read_json()
        value = body.get("value", "")
        if not isinstance(value, str):
            raise ApiError(400, "Field value must be text.")
        value = value.strip()
        if len(value) > 600:
            raise ApiError(400, "Field value is too long.")
        field = None
        with db.connect() as conn:
            field = conn.execute("SELECT * FROM fields WHERE id=?", (field_id,)).fetchone()
            if not field:
                raise ApiError(404, "Field not found.")
            doc = conn.execute("SELECT * FROM documents WHERE id=?", (field["document_id"],)).fetchone()
            if not doc:
                raise ApiError(404, "Document not found.")
            if doc["status"] in ("approved", "rejected", "auto_approved"):
                raise ApiError(409, "This document is locked. Reopen it before editing.", "locked")
            if doc["assignee_id"] and doc["assignee_id"] != user["id"] and user["role"] not in ("supervisor", "admin"):
                raise ApiError(403, "This document is assigned to another reviewer.", "assigned")
        doc = db.update_field(field_id, value, user["id"])
        if not doc:
            raise ApiError(404, "Field not found.")
        doc["actions"] = self._actions(doc, user)
        return self.send_json({"document": doc})

    def api_document_action(self, doc_id: str, action: str, user: dict):
        # Consume the request body up front. Several actions take no payload,
        # but leaving it in the socket corrupts HTTP keep-alive framing.
        body = self.read_json()
        doc = db.get_document(doc_id)
        if not doc:
            raise ApiError(404, "Document not found.")
        allowed = self._actions(doc, user)
        if action not in ("claim", "release", "approve", "reject", "rescan", "escalate",
                          "reopen", "verify-high-confidence", "comments"):
            raise ApiError(404, "Unknown action.")
        if action == "claim":
            if not allowed["claim"]:
                raise ApiError(409, "This document cannot be claimed right now.", "state")
            doc = db.claim_document(doc_id, user["id"])
        elif action == "release":
            if not allowed["release"] and user["role"] not in ("supervisor", "admin"):
                raise ApiError(403, "Only the assigned reviewer can release this document.", "assigned")
            doc = db.release_document(doc_id, user["id"])
        elif action == "verify-high-confidence":
            if not allowed["verify_high_confidence"]:
                raise ApiError(409, "Document is not open for verification.", "state")
            doc = db.verify_high_confidence(doc_id, user["id"])
        elif action == "approve":
            if not allowed["approve"]:
                raise ApiError(409, "This document cannot be approved in its current state.", "state")
            try:
                doc = db.approve_document(doc_id, user, body.get("override_reason"))
            except PermissionError as exc:
                raise ApiError(403, str(exc), "supervisor_required")
            except ValueError as exc:
                issues = getattr(exc, "blocking", None)
                raise ApiError(409, str(exc), "validation_blocked", issues)
        elif action == "reject":
            if not allowed["reject"]:
                raise ApiError(409, "This document cannot be rejected in its current state.", "state")
            reason = str(body.get("reason", "")).strip()
            if len(reason) < 4:
                raise ApiError(400, "Add a short reason for the rejection.")
            doc = db.reject_document(doc_id, user, reason)
        elif action == "rescan":
            reason = str(body.get("reason", "")).strip()
            if len(reason) < 4:
                raise ApiError(400, "Explain what needs to be rescanned.")
            doc = db.request_rescan(doc_id, user, reason)
        elif action == "escalate":
            reason = str(body.get("reason", "")).strip()
            if len(reason) < 4:
                raise ApiError(400, "Add a short escalation note.")
            doc = db.escalate_document(doc_id, user, reason)
        elif action == "reopen":
            if not allowed["reopen"]:
                raise ApiError(403, "Only a supervisor can reopen a closed document.", "forbidden")
            doc = db.reopen_document(doc_id, user)
        elif action == "comments":
            text = str(body.get("body", "")).strip()
            if not text:
                raise ApiError(400, "Comment cannot be empty.")
            with db.connect() as conn:
                conn.execute(
                    "INSERT INTO comments(document_id,user_id,body,created_at) VALUES (?,?,?,?)",
                    (doc_id, user["id"], text, db.iso()))
                db.add_event(conn, doc_id, user["id"], "comment.added", "Added a review comment.")
            doc = db.get_document(doc_id)
        if not doc:
            raise ApiError(404, "Document not found.")
        doc["actions"] = self._actions(doc, user)
        return self.send_json({"document": doc})

    # ------------------------------------------------------------------ upload
    def api_upload(self, user: dict):
        filename = unquote(self.headers.get("X-Filename", "upload.jpg"))
        filename = os.path.basename(filename)[:120] or "upload.jpg"
        doc_type = self.headers.get("X-Doc-Type", "bank")
        language = self.headers.get("X-Doc-Language", "en")
        data = self.read_body(limit=MAX_UPLOAD)
        if len(data) < 32:
            raise ApiError(400, "The uploaded file is empty or too small.")
        is_pdf = data[:5] == b"%PDF-"
        is_image = data[:8] == b"\x89PNG\r\n\x1a\n" or data[:3] == b"\xff\xd8\xff"
        if not is_pdf and not is_image:
            raise ApiError(415, "Upload a PNG, JPEG or PDF scan.")
        if doc_type not in DOC_TYPES:
            raise ApiError(400, "Unknown document type.")
        dims = image_dimensions(data) if is_image else None
        width, height = dims if dims else (1240, 1754)
        try:
            schema = db.template_fields(doc_type)
        except ValueError as exc:
            raise ApiError(400, str(exc))
        temp_path = None
        temp_dir = None
        try:
            if not ocr.status()["available"]:
                raise ocr.OcrUnavailable("Tesseract is not installed.")
            if is_pdf:
                if not pdf.available():
                    raise pdf.PdfError("The PDF rasteriser is not available.")
                temp_path = UPLOADS_DIR / f"_incoming_{uuid.uuid4().hex}.pdf"
                temp_path.write_bytes(data)
                temp_dir = UPLOADS_DIR / f"_pdf_{uuid.uuid4().hex}"
                rendered = pdf.render_pdf(temp_path, temp_dir, max_pages=6)
                results = []
                page_fields = []
                for page in rendered["pages"]:
                    try:
                        result = ocr.run_tesseract(page["path"], lang=language, psm=11)
                    except ocr.OcrError:
                        continue
                    fields = extract.extract_fields(result, schema)
                    for fld in fields:
                        fld["page"] = page["no"]
                    results.append(result)
                    page_fields.append(fields)
                if not results:
                    raise pdf.PdfError("No readable pages in the PDF.")
                merged = ocr.MergedOcr(results)
                chosen = {}
                for fields in page_fields:
                    for fld in fields:
                        current = chosen.get(fld["key"])
                        if current is None or (fld["value"] and
                                               (not current["value"] or fld["confidence"] > current["confidence"])):
                            chosen[fld["key"]] = fld
                fields = [chosen[s["key"]] for s in schema if s["key"] in chosen]
                summary = extract.summarize(merged, fields)
                summary["pdf_total_pages"] = rendered["total"]
                summary["pdf_rendered_pages"] = rendered["rendered"]
                payload = db.create_ocr_intake(filename, None, doc_type, user,
                                               width, height, merged, fields, summary,
                                               page_files=rendered["pages"])
            else:
                ext = ".jpg" if data[:3] == b"\xff\xd8\xff" else ".png"
                temp_path = UPLOADS_DIR / f"_incoming_{uuid.uuid4().hex}{ext}"
                temp_path.write_bytes(data)
                result = ocr.run_tesseract(temp_path, lang=language, psm=11)
                fields = extract.extract_fields(result, schema)
                summary = extract.summarize(result, fields)
                payload = db.create_ocr_intake(filename, data, doc_type, user,
                                               width, height, result, fields, summary)
            payload["fallback"] = False
            return self.send_json(payload, 201)
        except (ocr.OcrUnavailable, ocr.OcrError, pdf.PdfError) as exc:
            if is_pdf:
                raise ApiError(422, f"PDF could not be processed locally: {exc}", "pdf_failed")
            try:
                result = db.create_manual_intake(filename, data, doc_type, user, width, height)
                result["fallback"] = True
                result["ocr"] = None
                result["ocr_error"] = str(exc)
                return self.send_json(result, 201)
            except ValueError as exc2:
                raise ApiError(400, str(exc2))
        except ValueError as exc:
            raise ApiError(400, str(exc))
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            if temp_dir and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except OSError:
                    pass

    # ------------------------------------------------------------------ settings
    def api_update_settings(self, user: dict):
        body = self.read_json()
        updates = {}
        for key, value in body.items():
            if key not in SETTINGS_SCHEMA:
                continue
            typ, lo, hi = SETTINGS_SCHEMA[key]
            try:
                if typ is bool:
                    converted = value if isinstance(value, bool) else str(value).lower() == "true"
                elif typ is float:
                    converted = float(value)
                    if lo is not None and not (lo <= converted <= hi):
                        raise ValueError(f"{key} must be between {lo} and {hi}.")
                else:
                    converted = str(value).strip()
                    if lo is not None and len(converted) < int(lo):
                        raise ValueError(f"{key} is too short.")
            except (TypeError, ValueError) as exc:
                raise ApiError(400, str(exc))
            updates[key] = converted
        if not updates:
            raise ApiError(400, "No supported settings were supplied.")
        current = db.get_settings()
        merged = {**current, **updates}
        if merged["review_threshold"] >= merged["auto_approve_threshold"]:
            raise ApiError(400, "The review threshold must be lower than the auto-approval threshold.")
        saved = db.set_settings(updates)
        with db.connect() as conn:
            db.add_event(conn, None, user["id"], "settings.updated",
                         "Updated review policy and routing settings.",
                         meta={"keys": list(updates)})
        return self.send_json({"settings": saved, "meta": meta()})


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Akshara document review prototype")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--reset", action="store_true", help="Rebuild the demo database")
    args = parser.parse_args(argv)

    db.init_db(reset=args.reset)
    httpd = Server((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}"
    print("")
    print("  Akshara · multilingual document intake")
    print(f"  {url}")
    print("")
    print("  Demo accounts (one-click on the sign-in screen):")
    print("    maya@akshara.ai   / review123   reviewer")
    print("    arjun@akshara.ai  / super123    supervisor")
    print("    leela@akshara.ai  / admin123    administrator")
    print("")
    print("  Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopping.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

