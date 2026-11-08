"""Field and cross-field validation for the four document families.

The goal is not to encode every Indian banking rule. It is to demonstrate the
contract a production rules engine needs: deterministic messages, a severity,
and a clear blocking decision that the human review workflow can enforce.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

# --------------------------------------------------------------------------- parsing
DATE_FORMATS = ("%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]$")
PHONE_RE = re.compile(r"^[6-9]\d{9}$")
PIN_RE = re.compile(r"^\d{6}$")
ACCOUNT_RE = re.compile(r"^\d{9,18}$")


def parse_amount(value: str) -> float | None:
    if value is None:
        return None
    clean = str(value).replace("₹", "").replace(",", "").replace(" ", "").strip()
    if clean.startswith("-"):
        return None
    try:
        return float(clean)
    except ValueError:
        return None


def parse_date(value: str) -> datetime | None:
    value = (value or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _empty(value: Any) -> bool:
    return value is None or str(value).strip() == ""


# --------------------------------------------------------------------------- field rules
def validate_field(field: dict) -> tuple[str, str]:
    """Return (status, message) for one field.

    status is one of valid / warning / invalid / unchecked. Blocking is derived
    from invalid + required at the document level.
    """
    value = field.get("value", "")
    ftype = field.get("type", "text")
    required = bool(field.get("required", True))
    key = field.get("key", "")
    label = field.get("label", key)

    if _empty(value):
        if required:
            return "invalid", f"{label} is required."
        return "valid", ""

    value = str(value).strip()

    if ftype == "date":
        parsed = parse_date(value)
        if not parsed:
            return "invalid", f"{label} is not a valid date (use DD/MM/YYYY)."
        if key == "dob":
            if parsed > datetime.now():
                return "invalid", "Date of birth cannot be in the future."
            if parsed.year < 1900:
                return "invalid", "Date of birth is outside the supported range."
        if key in ("admission_date", "invoice_date", "preferred_date") and parsed.year > datetime.now().year + 1:
            return "invalid", f"{label} is unreasonably far in the future."
        return "valid", ""

    if ftype == "amount":
        amount = parse_amount(value)
        if amount is None:
            return "invalid", f"{label} is not a readable amount."
        if amount < 0:
            return "invalid", f"{label} cannot be negative."
        if amount == 0 and key not in ("existing_emi",):
            return "warning", f"{label} is zero; confirm before approval."
        return "valid", ""

    if ftype == "phone":
        digits = re.sub(r"\D", "", value)
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        if not PHONE_RE.match(digits):
            return "invalid", f"{label} must be a 10-digit Indian mobile number."
        return "valid", ""

    if ftype == "pincode":
        if not PIN_RE.match(value):
            return "invalid", f"{label} must contain exactly 6 digits."
        return "valid", ""

    if ftype == "email":
        if not EMAIL_RE.match(value):
            return "invalid", f"{label} is not a valid email address."
        return "valid", ""

    if ftype == "ifsc":
        if not IFSC_RE.match(value):
            return "invalid", f"{label} must be a valid 11-character IFSC."
        return "valid", ""

    if ftype == "pan":
        if not PAN_RE.match(value):
            return "invalid", f"{label} must match the PAN format (AAAAA9999A)."
        return "valid", ""

    if ftype == "gstin":
        if not GSTIN_RE.match(value):
            return "invalid", f"{label} must be a valid 15-character GSTIN."
        return "valid", ""

    if ftype == "account":
        if not ACCOUNT_RE.match(value):
            return "invalid", f"{label} must contain 9–18 digits."
        return "valid", ""

    if ftype == "number":
        digits = value.replace(" ", "").replace(",", "")
        if not digits.isdigit():
            return "invalid", f"{label} must be numeric."
        if key == "credit_score" and not 300 <= int(digits) <= 900:
            return "invalid", "Credit score must be between 300 and 900."
        if key == "aadhaar_last4" and len(digits) != 4:
            return "invalid", "Aadhaar last 4 must be exactly 4 digits."
        if key == "tenure_months" and not 6 <= int(digits) <= 360:
            return "invalid", "Tenure must be between 6 and 360 months."
        return "valid", ""

    if ftype == "id":
        if len(value) < 3:
            return "invalid", f"{label} looks too short to be valid."
        return "valid", ""

    if ftype in ("choice", "consent", "signature"):
        return "valid", ""

    return "valid", ""


# --------------------------------------------------------------------------- cross-field
def validate_document(doc_type: str, fields: list[dict]) -> list[dict]:
    """Validate and annotate fields in place. Returns a compact issue list."""
    by_key = {f["key"]: f for f in fields}
    issues: list[dict] = []

    for field in fields:
        status, message = validate_field(field)
        field["validation_status"] = status
        field["validation_message"] = message
        if status != "valid":
            issues.append({
                "field_id": field.get("id"),
                "key": field["key"],
                "label": field["label"],
                "status": status,
                "message": message,
                "blocking": status == "invalid" and bool(field.get("required", True)),
            })

    def invalid(key: str, message: str, blocking: bool = True):
        field = by_key.get(key)
        if not field:
            return
        field["validation_status"] = "invalid"
        field["validation_message"] = message
        issues.append({
            "field_id": field.get("id"), "key": key, "label": field["label"],
            "status": "invalid", "message": message, "blocking": blocking,
        })

    def warn(key: str, message: str):
        field = by_key.get(key)
        if not field:
            return
        if field.get("validation_status") != "invalid":
            field["validation_status"] = "warning"
            field["validation_message"] = message
        issues.append({
            "field_id": field.get("id"), "key": key, "label": field["label"],
            "status": "warning", "message": message, "blocking": False,
        })

    if doc_type == "claim":
        admission = parse_date(by_key.get("admission_date", {}).get("value", ""))
        discharge = parse_date(by_key.get("discharge_date", {}).get("value", ""))
        if admission and discharge and discharge < admission:
            invalid("discharge_date", "Discharge date cannot be before the admission date.")
        claim = parse_amount(by_key.get("claim_amount", {}).get("value", ""))
        insured = parse_amount(by_key.get("sum_insured", {}).get("value", ""))
        if claim is not None and insured is not None and claim > insured:
            invalid("claim_amount", "Claimed amount exceeds the sum insured.")

    elif doc_type == "invoice":
        subtotal = parse_amount(by_key.get("subtotal", {}).get("value", ""))
        cgst = parse_amount(by_key.get("cgst", {}).get("value", ""))
        sgst = parse_amount(by_key.get("sgst", {}).get("value", ""))
        total = parse_amount(by_key.get("total", {}).get("value", ""))
        if None not in (subtotal, cgst, sgst, total):
            difference = round((subtotal + cgst + sgst) - total, 2)
            if abs(difference) > 1:
                invalid("total", f"Total does not match subtotal + taxes (difference ₹{abs(difference):,.2f}).")
        if total is not None and total <= 0:
            invalid("total", "Invoice total must be greater than zero.")

    elif doc_type == "loan":
        income = parse_amount(by_key.get("monthly_income", {}).get("value", ""))
        emi = parse_amount(by_key.get("existing_emi", {}).get("value", ""))
        if income and emi and emi > income * 0.6:
            warn("existing_emi", "Existing EMI exceeds 60% of monthly income; affordability check required.")

    elif doc_type == "bank":
        income = parse_amount(by_key.get("annual_income", {}).get("value", ""))
        if income is not None and income < 120000:
            warn("annual_income", "Declared annual income is below the minimum for this account variant.")

    elif doc_type == "service":
        preferred = parse_date(by_key.get("preferred_date", {}).get("value", ""))
        if preferred and preferred < datetime.now():
            warn("preferred_date", "Preferred date is in the past; confirm a new appointment.")

    # De-duplicate by key/message and sort invalid first.
    seen = set()
    unique = []
    for issue in issues:
        marker = (issue["key"], issue["message"])
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(issue)
    unique.sort(key=lambda x: (x["status"] != "invalid", not x["blocking"]))
    return unique


def summarize(fields: list[dict]) -> dict:
    invalid = [f for f in fields if f.get("validation_status") == "invalid"]
    warnings = [f for f in fields if f.get("validation_status") == "warning"]
    low = [f for f in fields if float(f.get("confidence", 1)) < 0.8]
    return {
        "invalid": len(invalid),
        "warnings": len(warnings),
        "low_confidence": len(low),
        "blocking": len([f for f in invalid if f.get("required")]),
        "verified": len([f for f in fields if f.get("verified")]),
        "corrected": len([f for f in fields if f.get("corrected")]),
        "total": len(fields),
    }
