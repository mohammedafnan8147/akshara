"""Paths, labels, and policy defaults."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SAMPLES_DIR = DATA_DIR / "samples"
UPLOADS_DIR = DATA_DIR / "uploads"
BUILD_DIR = ROOT / "build"
WEB_DIR = ROOT / "web"
DB_PATH = DATA_DIR / "akshara.db"
SECRET_PATH = DATA_DIR / ".session_secret"

STATUS_LABELS = {
    "queued": "Needs review",
    "in_review": "In review",
    "escalated": "Escalated",
    "needs_rescan": "Rescan requested",
    "auto_approved": "Auto-approved",
    "approved": "Approved",
    "rejected": "Rejected",
}

STATUS_TONE = {
    "queued": "amber",
    "in_review": "blue",
    "escalated": "red",
    "needs_rescan": "slate",
    "auto_approved": "green",
    "approved": "green",
    "rejected": "red",
}

OPEN_STATUSES = ("queued", "in_review", "escalated")
REVIEWABLE_STATUSES = ("queued", "in_review", "escalated")
CLOSED_STATUSES = ("approved", "rejected", "auto_approved")

DOC_TYPES = {
    "bank": {"label": "Account opening", "family": "Banking", "icon": "bank"},
    "claim": {"label": "Health claim", "family": "Insurance", "icon": "heart"},
    "service": {"label": "Service request", "family": "Service centre", "icon": "headset"},
    "loan": {"label": "Loan application", "family": "Lending", "icon": "landmark"},
    "invoice": {"label": "Tax invoice", "family": "Business", "icon": "receipt"},
    "kyc": {"label": "KYC update", "family": "Banking", "icon": "shield"},
}

DEFAULT_SETTINGS = {
    "workspace_name": "Meridian Bank · Operations",
    "auto_approve_threshold": 0.92,
    "review_threshold": 0.70,
    "high_value_threshold": 100000,
    "sla_hours": 8,
    "urgent_sla_hours": 4,
    "require_supervisor_high_value": True,
    "auto_assign": False,
    "demo_mode": True,
}

SETTINGS_SCHEMA = {
    "auto_approve_threshold": (float, 0.5, 0.999),
    "review_threshold": (float, 0.3, 0.99),
    "high_value_threshold": (float, 1000, 100000000),
    "sla_hours": (float, 1, 72),
    "urgent_sla_hours": (float, 1, 48),
    "require_supervisor_high_value": (bool, None, None),
    "auto_assign": (bool, None, None),
    "workspace_name": (str, 2, 80),
}

DEMO_USERS = [
    {
        "id": "u_maya", "name": "Maya Rao", "email": "maya@akshara.ai",
        "password": "review123", "role": "reviewer", "title": "Review specialist",
        "initials": "MR", "color": "#C77655",
    },
    {
        "id": "u_arjun", "name": "Arjun Mehta", "email": "arjun@akshara.ai",
        "password": "super123", "role": "supervisor", "title": "Operations supervisor",
        "initials": "AM", "color": "#2B6E62",
    },
    {
        "id": "u_leela", "name": "Leela Nair", "email": "leela@akshara.ai",
        "password": "admin123", "role": "admin", "title": "Workspace administrator",
        "initials": "LN", "color": "#8A6F3D",
    },
]

ROLE_LABELS = {"reviewer": "Reviewer", "supervisor": "Supervisor", "admin": "Administrator"}
