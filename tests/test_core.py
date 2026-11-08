"""Core workflow tests. Run with:
    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from akshara import db, validators


class ValidatorTests(unittest.TestCase):
    def test_phone_and_pan(self):
        self.assertEqual(validators.validate_field({
            "key": "mobile", "label": "Mobile", "value": "9820112233",
            "type": "phone", "required": True,
        })[0], "valid")
        self.assertEqual(validators.validate_field({
            "key": "mobile", "label": "Mobile", "value": "982O112233",
            "type": "phone", "required": True,
        })[0], "invalid")
        self.assertEqual(validators.validate_field({
            "key": "pan", "label": "PAN", "value": "AKJPI4821R",
            "type": "pan", "required": True,
        })[0], "valid")

    def test_required_and_optional(self):
        status, _ = validators.validate_field({
            "key": "x", "label": "X", "value": "", "type": "text", "required": True,
        })
        self.assertEqual(status, "invalid")
        status, _ = validators.validate_field({
            "key": "x", "label": "X", "value": "", "type": "text", "required": False,
        })
        self.assertEqual(status, "valid")

    def test_claim_date_order(self):
        fields = [
            {"id": "a", "key": "admission_date", "label": "Admission", "value": "06/11/2026", "type": "date", "required": True},
            {"id": "b", "key": "discharge_date", "label": "Discharge", "value": "03/11/2026", "type": "date", "required": True},
        ]
        issues = validators.validate_document("claim", fields)
        self.assertTrue(any(i["key"] == "discharge_date" and i["blocking"] for i in issues))
        self.assertEqual(fields[1]["validation_status"], "invalid")

    def test_invoice_total(self):
        fields = [
            {"id": "s", "key": "subtotal", "label": "Subtotal", "value": "₹ 1,00,000", "type": "amount", "required": True},
            {"id": "c", "key": "cgst", "label": "CGST", "value": "₹ 9,000", "type": "amount", "required": True},
            {"id": "g", "key": "sgst", "label": "SGST", "value": "₹ 9,000", "type": "amount", "required": True},
            {"id": "t", "key": "total", "label": "Total", "value": "₹ 1,28,000", "type": "amount", "required": True},
        ]
        issues = validators.validate_document("invoice", fields)
        self.assertTrue(any(i["key"] == "total" and i["blocking"] for i in issues))


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(__file__).resolve().parents[1] / "tmp" / "akshara-test-db"
        shutil.rmtree(cls.tmp, ignore_errors=True)
        cls.tmp.mkdir(parents=True, exist_ok=True)
        cls.old_db = db.DB_PATH
        cls.old_data = db.DATA_DIR
        cls.old_uploads = db.UPLOADS_DIR
        db.DB_PATH = cls.tmp / "test.db"
        db.DATA_DIR = cls.tmp
        db.UPLOADS_DIR = cls.tmp / "uploads"
        db.init_db(reset=True)

    @classmethod
    def tearDownClass(cls):
        db.DB_PATH = cls.old_db
        db.DATA_DIR = cls.old_data
        db.UPLOADS_DIR = cls.old_uploads
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        db.init_db(reset=True)

    def users(self):
        return {
            "maya": db.get_user("u_maya"),
            "arjun": db.get_user("u_arjun"),
            "leela": db.get_user("u_leela"),
        }

    def test_seed_shape(self):
        docs = db.list_documents(view="all", limit=100)
        self.assertEqual(len(docs["items"]), 18)
        self.assertGreaterEqual(docs["counts"]["queue"], 8)
        self.assertTrue(any(d["is_high_value"] for d in docs["items"]))

    def test_blocked_approval_and_override(self):
        users = self.users()
        doc = db.get_document("doc_bank_01")
        self.assertEqual(doc["status"], "queued")
        db.claim_document("doc_bank_01", users["maya"]["id"])
        with self.assertRaises(ValueError) as ctx:
            db.approve_document("doc_bank_01", users["maya"])
        self.assertTrue(getattr(ctx.exception, "blocking", None))
        result = db.approve_document(
            "doc_bank_01", users["arjun"],
            override_reason="Verified against the original branch record.",
        )
        self.assertEqual(result["status"], "approved")
        actions = [e["action"] for e in result["events"]]
        self.assertIn("document.override", actions)

    def test_correction_changes_validation(self):
        users = self.users()
        doc = db.get_document("doc_bank_01")
        mobile = next(f for f in doc["fields"] if f["key"] == "mobile")
        updated = db.update_field(mobile["id"], "9820112233", users["maya"]["id"])
        self.assertEqual(updated["fields"][[f["key"] for f in updated["fields"]].index("mobile")]["value"], "9820112233")
        self.assertNotIn("mobile", [i["key"] for i in updated["blocking_issues"]])

    def test_auto_intake_and_manual_upload(self):
        users = self.users()
        result = db.create_demo_intake("service_01", users["maya"])
        self.assertIn(result["status"], ("auto_approved", "queued"))
        self.assertTrue(result["ref"].startswith("AK-26-"))
        image = (db.SAMPLES_DIR / "bank_01.jpg").read_bytes()
        uploaded = db.create_manual_intake("phone.jpg", image, "bank", users["maya"], 1240, 1754)
        doc = db.get_document(uploaded["id"])
        self.assertEqual(doc["status"], "queued")
        self.assertEqual(doc["field_count"], 21)
        self.assertEqual(doc["fields"][0]["value"], "")
        self.assertTrue(doc["image_url"].startswith("/uploads/"))

    def test_reopen_resets_verification(self):
        users = self.users()
        result = db.reopen_document("doc_bank_02", users["arjun"])
        self.assertEqual(result["status"], "queued")
        self.assertEqual(result["progress"]["verified"], 0)

    def test_analytics_and_audit(self):
        analytics = db.analytics()
        self.assertEqual(analytics["totals"]["documents"], 18)
        self.assertEqual(len(analytics["confidence_bands"]), 5)
        audit = db.audit_events(limit=10)
        self.assertGreater(audit["total"], 20)

    def test_dashboard_shape(self):
        data = db.dashboard()
        for key in ("open_queue", "overdue", "auto_rate", "avg_confidence"):
            self.assertIn(key, data["kpis"])
        self.assertEqual(len(data["trend"]), 14)
        self.assertIn("totals", data)


if __name__ == "__main__":
    unittest.main()
