"""Label-anchored field extraction over Tesseract word boxes.

This is deliberately a transparent, deterministic baseline rather than a black
box. It locates a schema label in the OCR lines, then looks for the value in the
same line or in the whitespace immediately below/above it. That is enough for
the clean, label-driven forms in the specimen library and gives reviewers a
useful head start on real uploads. Every extracted value keeps its source box
and word-level confidence.
"""
from __future__ import annotations

import re
from typing import Any

from .ocr import OcrLine, OcrResult, OcrWord

SKIP_PREFIXES = ("item",)
LABEL_STOPWORDS = {"THE", "OF", "AND", "OR", "A", "AN"}


def normalize(text: str) -> str:
    text = (text or "").upper()
    text = text.replace("&", " AND ")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return " ".join(text.split())


def _tokens(text: str) -> list[str]:
    return [t for t in normalize(text).split() if t not in LABEL_STOPWORDS]


def _coverage(label: str, line: str) -> float:
    lt = set(_tokens(label))
    lnt = set(_tokens(line))
    if not lt:
        return 0.0
    return len(lt & lnt) / len(lt)


def _label_score(label: str, line_text: str) -> float:
    ln = normalize(label)
    lnt = normalize(line_text)
    if not ln or not lnt:
        return 0.0
    if lnt == ln:
        return 1.0
    if lnt.startswith(ln + " ") or lnt.startswith(ln):
        return 0.95
    if ln in lnt:
        return 0.86
    cov = _coverage(label, line_text)
    if cov >= 0.8 and len(_tokens(label)) >= 2:
        return 0.68 + 0.14 * cov
    return 0.0


def _label_prefix_words(line: OcrLine, label: str) -> tuple[list[OcrWord], list[OcrWord]]:
    """Split a line into the words that make up the label and the remainder.

    Returns (label_words, rest_words). If the label is only partly present on
    the line, fall back to the full line as label and no remainder.
    """
    target = normalize(label)
    words = line.words
    joined = ""
    for idx, word in enumerate(words):
        joined = (joined + " " + normalize(word.text)).strip()
        if joined == target or joined.startswith(target + " ") or joined.startswith(target):
            return words[: idx + 1], words[idx + 1:]
        if target.startswith(joined) and idx == len(words) - 1:
            break
    return words, []


def _union(words: list[OcrWord], pad: float = 2.0) -> list[float]:
    if not words:
        return [0.0, 0.0, 0.0, 0.0]
    left = min(w.left for w in words) - pad
    top = min(w.top for w in words) - pad
    right = max(w.right for w in words) + pad
    bottom = max(w.bottom for w in words) + pad
    return [round(max(0, left), 1), round(max(0, top), 1),
            round(max(1, right - left), 1), round(max(1, bottom - top), 1)]


def _clean_value(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    value = value.strip("|:;,- ")
    value = re.sub(r"^[|¦]+\s*", "", value)
    value = re.sub(r"\s*[|¦]+$", "", value)
    return value.strip()


def _is_probable_label(value: str, label_norms: set[str]) -> bool:
    return normalize(value) in label_norms


def _same_line_value(line: OcrLine, label: str) -> tuple[str, list[OcrWord]]:
    label_words, rest = _label_prefix_words(line, label)
    if rest:
        return _clean_value(" ".join(w.text for w in rest)), rest

    # Some OCR engines put the value in a separate block but the same visual
    # row. Look for a line whose vertical centre overlaps the label's.
    return "", []


def _row_value(ocr: OcrResult, line: OcrLine, label_norms: set[str]) -> tuple[str, list[OcrWord]]:
    """Look for the value line directly below the label.

    Labels are above values in the forms this extractor targets. We deliberately
    do not search above: a weak match there is more likely to steal the previous
    field's value. A low-confidence line below is still useful because review
    can correct it, and its low confidence is visible in the UI.
    """
    candidates: list[tuple[float, float, OcrLine]] = []
    for other in ocr.lines:
        if other is line:
            continue
        if other.conf < 0.01:
            continue
        if _is_probable_label(other.text, label_norms):
            continue
        # Prefer the column in which the label sits.
        if other.left < line.left - 28 or other.left > line.left + 72:
            continue
        below = other.top - line.bottom
        if -2 <= below <= 82:
            # Score: close to the label's left edge, close vertically, high conf.
            score = (abs(other.left - line.left) * 0.02 + max(0, below) * 0.012
                     - other.conf * 0.8)
            candidates.append((score, below, other))
    if not candidates:
        return "", []
    candidates.sort(key=lambda x: x[0])
    selected = candidates[0][2]
    return _clean_value(selected.text), selected.words


def _confidence(words: list[OcrWord]) -> float:
    if not words:
        return 0.0
    confs = [w.conf for w in words]
    avg = sum(confs) / len(confs)
    low = min(confs)
    score = 0.65 * avg + 0.35 * low
    if len(words) == 1 and len(words[0].text) <= 2:
        score *= 0.82
    return round(max(0.0, min(0.985, score)), 3)


def extract_fields(ocr: OcrResult, schema_fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels = [f.get("label", f.get("key", "")) for f in schema_fields]
    label_norms = {normalize(l) for l in labels if l}
    out: list[dict[str, Any]] = []

    for schema in schema_fields:
        key = schema["key"]
        label = schema.get("label") or key
        ftype = schema.get("field_type") or schema.get("type") or "text"
        required = bool(schema.get("required", True))
        options = schema.get("options") or []
        if isinstance(options, str):
            try:
                import json
                options = json.loads(options)
            except Exception:
                options = []
        if key.startswith(SKIP_PREFIXES):
            out.append({
                "key": key, "label": label, "value": "", "confidence": 0.0,
                "bbox": [0, 0, 0, 0], "type": ftype, "required": required,
                "options": options, "section": schema.get("section", ""),
                "dir": "ltr",
            })
            continue

        scored: list[tuple[float, OcrLine]] = []
        for line in ocr.lines:
            if line.conf < 0.15:
                continue
            score = _label_score(label, line.text)
            if score >= 0.68:
                scored.append((score, line))
        scored.sort(key=lambda x: (-x[0], -x[1].conf, x[1].top))
        value = ""
        words: list[OcrWord] = []
        if scored:
            score, line = scored[0]
            value, words = _same_line_value(line, label)
            if not value:
                value, words = _row_value(ocr, line, label_norms)
            if not value and score < 0.85:
                # A weak label match can produce a wrong value; leave it to a human.
                value, words = "", []
        value = _clean_value(value)
        if ftype == "amount" and value:
            match = re.search(r"([0-9][0-9,]*(?:\.[0-9]+)?)", value)
            if match:
                value = "₹ " + match.group(1)
        elif ftype in ("choice", "consent") and value:
            value = re.sub(r"^[^A-Za-z0-9\u0900-\u0fff]+", "", value)
            value = re.sub(r"^[A-Za-z]{1,2}\s+(?=[A-Z])", "", value)
            value = _clean_value(value)
        if _is_probable_label(value, label_norms) or len(value) > 280:
            value, words = "", []
        out.append({
            "key": key, "label": label, "value": value,
            "confidence": _confidence(words) if value else 0.0,
            "bbox": _union(words) if value else [0, 0, 0, 0],
            "type": ftype, "required": required, "options": options,
            "section": schema.get("section", ""),
            "dir": "rtl" if ftype == "text" and _has_rtl(value) else "ltr",
        })
    return out


def _has_rtl(value: str) -> bool:
    return any("\u0590" <= ch <= "\u08ff" for ch in value or "")


def summarize(ocr: OcrResult, fields: list[dict[str, Any]]) -> dict:
    extracted = [f for f in fields if f["value"]]
    confs = [f["confidence"] for f in extracted]
    avg = sum(confs) / len(confs) if confs else 0.0
    low = min(confs) if confs else 0.0
    coverage = len(extracted) / len(fields) if fields else 0.0
    document_conf = 0.65 * (0.6 * avg + 0.4 * low) + 0.35 * coverage if confs else 0.0
    if ocr.mean_conf >= 0.85:
        quality = "good"
    elif ocr.mean_conf >= 0.62:
        quality = "fair"
    else:
        quality = "poor"
    return {
        "extracted": len(extracted),
        "total": len(fields),
        "coverage": round(coverage, 3),
        "mean_confidence": round(avg, 3),
        "document_confidence": round(min(0.97, document_conf), 3),
        "quality": quality,
        "ocr_mean_confidence": round(ocr.mean_conf, 3),
        "words": ocr.word_count,
        "lines": ocr.line_count,
    }
