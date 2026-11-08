"""OCR, label extraction and OCR-ingest tests.

The pure parser/extractor tests always run. The live Tesseract test is skipped
when no binary is installed.
"""
from __future__ import annotations

import io
import json
import shutil
import unittest
from pathlib import Path

from akshara import db, extract, ocr, pdf

ROOT = Path(__file__).resolve().parents[1]
TSV = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"


def row(block, line, word, text, left, top, width=40, height=20, conf=95.0):
    return f"5\t1\t{block}\t1\t{line}\t{word}\t{left}\t{top}\t{width}\t{height}\t{conf}\t{text}\n"


class ParserExtractorTests(unittest.TestCase):
    def result(self):
        body = TSV
        body += row(1, 1, 1, "FULL", 72, 100, 44)
        body += row(1, 1, 2, "NAME", 120, 100, 52)
        body += row(1, 2, 1, "Ramesh", 72, 150, 70)
        body += row(1, 2, 2, "Iyer", 146, 150, 38)
        body += row(2, 1, 1, "MOBILE", 72, 260, 60)
        body += row(2, 1, 2, "NUMBER", 136, 260, 62)
        body += row(2, 2, 1, "9820112233", 72, 310, 150)
        return ocr.parse_tsv(body)

    @property
    def schema(self):
        return [
            {"key": "full_name", "label": "Full name", "field_type": "text", "required": True, "options": []},
            {"key": "mobile", "label": "Mobile number", "field_type": "phone", "required": True, "options": []},
        ]

    def test_parse_tsv_groups_lines(self):
        r = self.result()
        self.assertEqual(r.word_count, 7)
        self.assertEqual(r.line_count, 4)
        self.assertGreater(r.mean_conf, 0.9)
        self.assertIn("Ramesh Iyer", r.text)

    def test_label_anchor_extracts_value_and_box(self):
        r = self.result()
        fields = extract.extract_fields(r, self.schema)
        self.assertEqual(fields[0]["value"], "Ramesh Iyer")
        self.assertGreater(fields[0]["confidence"], 0.9)
        self.assertGreater(fields[0]["bbox"][2], 100)
        self.assertEqual(fields[1]["value"], "9820112233")

    def test_summary_marks_low_coverage(self):
        r = self.result()
        fields = extract.extract_fields(r, self.schema + [
            {"key": "address", "label": "Address", "field_type": "text", "required": True, "options": []},
        ])
        s = extract.summarize(r, fields)
        self.assertEqual(s["extracted"], 2)
        self.assertEqual(s["total"], 3)
        self.assertLess(s["coverage"], 1)


@unittest.skipUnless(ocr.status()["available"], "Tesseract is not installed")
class LiveTesseractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = ROOT / "tmp" / "akshara-ocr-test"
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

    def test_reads_english_invoice(self):
        result = ocr.run_tesseract(ROOT / "data" / "samples" / "invoice_01.jpg", psm=11)
        self.assertGreater(result.word_count, 50)
        self.assertGreater(result.mean_conf, 0.5)
        fixture = json.loads((ROOT / "data" / "samples" / "invoice_01.json").read_text(encoding="utf-8"))
        fields = extract.extract_fields(result, fixture["fields"])
        summary = extract.summarize(result, fields)
        self.assertGreaterEqual(summary["extracted"], 6)
        vendor = next(f for f in fields if f["key"] == "vendor_name")
        self.assertIn("Sundaram", vendor["value"])
        self.assertGreater(vendor["bbox"][2], 100)

    def test_ocr_ingest_persists_text_and_boxes(self):
        image = (ROOT / "data" / "samples" / "invoice_01.jpg").read_bytes()
        result = ocr.run_tesseract(ROOT / "data" / "samples" / "invoice_01.jpg", psm=11)
        schema = db.template_fields("invoice")
        fields = extract.extract_fields(result, schema)
        summary = extract.summarize(result, fields)
        user = db.get_user("u_maya")
        created = db.create_ocr_intake("invoice.jpg", image, "invoice", user,
                                       1240, 1754, result, fields, summary)
        doc = db.get_document(created["id"])
        self.assertEqual(doc["status"], "queued")
        self.assertTrue(doc["ocr_text"])
        self.assertEqual(doc["ocr_meta"]["engine"], "Tesseract")
        self.assertGreater(doc["field_count"], 10)
        self.assertTrue(any(f["bbox"][2] > 0 for f in doc["fields"]))
        self.assertTrue((db.UPLOADS_DIR / Path(doc["image_file"]).name).exists())


class _FakeOcr:
    engine = "Tesseract"
    version = "test"
    language = "eng"
    requested_language = "en"
    psm = 11
    word_count = 20
    line_count = 6
    mean_conf = 0.8
    text = "test ocr text"

    def meta(self):
        return {"engine": self.engine, "version": self.version, "language": self.language,
                "requested_language": self.requested_language, "psm": self.psm,
                "words": self.word_count, "lines": self.line_count,
                "mean_confidence": self.mean_conf}


@unittest.skipUnless(pdf.available(), "Windows PDF rasteriser is not available")
class PdfAndPagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = ROOT / "tmp" / "akshara-pdf-test"
        shutil.rmtree(cls.tmp, ignore_errors=True)
        cls.tmp.mkdir(parents=True, exist_ok=True)
        cls.old = (db.DB_PATH, db.DATA_DIR, db.UPLOADS_DIR)
        db.DB_PATH = cls.tmp / "test.db"
        db.DATA_DIR = cls.tmp
        db.UPLOADS_DIR = cls.tmp / "uploads"
        db.init_db(reset=True)

    @classmethod
    def tearDownClass(cls):
        db.DB_PATH, db.DATA_DIR, db.UPLOADS_DIR = cls.old
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_pdf_pages_and_ocr_document(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not available")
        pdf_path = self.tmp / "two.pdf"
        a = Image.open(ROOT / "data" / "samples" / "invoice_01.jpg").convert("RGB")
        b = Image.open(ROOT / "data" / "samples" / "claim_01.jpg").convert("RGB")
        a.save(pdf_path, "PDF", save_all=True, append_images=[b], resolution=150)
        rendered = pdf.render_pdf(pdf_path, self.tmp / "pages", max_pages=4)
        self.assertEqual(rendered["total"], 2)
        self.assertEqual(rendered["rendered"], 2)
        self.assertTrue(all(p["width"] > 0 and p["height"] > 0 for p in rendered["pages"]))

        schema = db.template_fields("invoice")
        fields = []
        for f in schema:
            fields.append({
                "key": f["key"], "label": f["label"], "value": "",
                "confidence": 0.0, "bbox": [0, 0, 0, 0], "type": f["field_type"],
                "required": f["required"], "options": f["options"],
                "section": f["section"], "page": 1,
            })
        summary = {"document_confidence": 0.4, "quality": "poor", "extracted": 0,
                   "total": len(fields), "mean_confidence": 0.0, "words": 20}
        user = db.get_user("u_maya")
        created = db.create_ocr_intake("two.pdf", None, "invoice", user, 100, 100,
                                       _FakeOcr(), fields, summary,
                                       page_files=rendered["pages"])
        doc = db.get_document(created["id"])
        self.assertEqual(doc["pages"], 2)
        self.assertEqual(len(doc["page_images"]), 2)
        self.assertTrue(doc["page_images"][0]["url"].startswith("/uploads/"))
        self.assertTrue((db.UPLOADS_DIR / Path(doc["page_images"][1]["file"]).name).exists())


if __name__ == "__main__":
    unittest.main()
