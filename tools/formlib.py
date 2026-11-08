"""Layout primitives for the specimen-form generator.

The output is a list of drawing commands understood by FormRenderer.exe.
Everything is deterministic so that confidence fixtures and bounding boxes
stay in sync across regenerations.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

PAGE_W = 1240
PAGE_H = 1754
MARGIN = 72
CONTENT_W = PAGE_W - 2 * MARGIN

PAPER = "#FBF8F0"
INK = "#1B2622"
MUTED = "#6C736C"
LIGHT = "#9A9E96"
RULE = "#D8D4C8"
INK_BLUE = "#243B4A"

FONT = "Nirmala UI"
FONT_EN = "Segoe UI"
FONT_SERIF = "Georgia"
FONT_HAND = "Segoe Print"
FONT_SIGN = "Segoe Script"


@dataclass
class FieldSpec:
    key: str
    label: str
    value: str
    label_sub: str = ""
    type: str = "text"
    required: bool = True
    options: list[str] = field(default_factory=list)
    full: bool = False
    font_size: int = 26
    confidence: float = 0.97
    error: str | None = None
    section: str = ""
    dir: str = "ltr"
    hint: str = ""


@dataclass
class SectionSpec:
    title: str
    fields: list[FieldSpec]
    subtitle: str = ""
    columns: int = 2
    row_h: int = 82
    width: int = CONTENT_W


class Form:
    """Accumulates drawing ops and field metadata for one page."""

    def __init__(self, brand: str, brand_sub: str, form_code: str,
                 accent: str, dark: str, rtl: bool = False,
                 watermark: str = "SPECIMEN"):
        self.ops: list[dict[str, Any]] = []
        self.fields: list[dict[str, Any]] = []
        self.brand = brand
        self.brand_sub = brand_sub
        self.form_code = form_code
        self.accent = accent
        self.dark = dark
        self.rtl = rtl
        self.watermark_text = watermark
        self.y = 0
        self.section_title = ""
        self._field_by_key: dict[str, dict[str, Any]] = {}

    # ---------------------------------------------------------------- primitives
    def rect(self, x, y, w, h, fill=None, stroke=None, width=1, radius=0, **kw):
        op = {"type": "rect", "x": x, "y": y, "w": w, "h": h,
              "radius": radius, "width": width}
        if fill:
            op["fill"] = fill
        if stroke:
            op["stroke"] = stroke
        op.update(kw)
        self.ops.append(op)

    def line(self, x1, y1, x2, y2, color=RULE, width=1, dash=None):
        op = {"type": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
              "color": color, "width": width}
        if dash:
            op["dash"] = dash
        self.ops.append(op)

    def ellipse(self, x, y, w, h, fill=None, stroke=None, width=1, **kw):
        op = {"type": "ellipse", "x": x, "y": y, "w": w, "h": h, "width": width}
        if fill:
            op["fill"] = fill
        if stroke:
            op["stroke"] = stroke
        op.update(kw)
        self.ops.append(op)

    def path(self, points, color=INK_BLUE, width=2.2, **kw):
        op = {"type": "path", "points": points, "color": color, "width": width}
        op.update(kw)
        self.ops.append(op)

    def bars(self, x, y, h, widths, color="#2A2E2B", **kw):
        op = {"type": "bars", "x": x, "y": y, "h": h, "widths": widths,
              "color": color}
        op.update(kw)
        self.ops.append(op)

    def text(self, x, y, w, h, text, font=FONT_EN, size=16, color=INK,
             style="regular", align="left", valign="top", rtl=False,
             wrap=False, id=None, rotate=None, cx=None, cy=None):
        op = {"type": "text", "x": x, "y": y, "w": w, "h": h,
              "text": text, "font": font, "size": size, "color": color,
              "style": style, "align": align, "valign": valign,
              "rtl": rtl, "wrap": wrap}
        if id:
            op["id"] = id
        if rotate is not None:
            op["rotate"] = rotate
            op["cx"] = cx if cx is not None else x + w / 2
            op["cy"] = cy if cy is not None else y + h / 2
        self.ops.append(op)
        return op

    # ------------------------------------------------------------------- chrome
    def header(self, doc_no: str, date_text: str, brand_initials: str,
               meta_label: str = "FORM NO."):
        d = self.dark
        a = self.accent
        self.rect(0, 0, PAGE_W, 152, fill=d)
        self.rect(0, 152, PAGE_W, 6, fill=a)
        # subtle brand pattern
        for i in range(9):
            self.line(760 + i * 48, 0, 700 + i * 48, 152, color="#FFFFFF", width=1)
        self.rect(72, 36, 68, 68, fill=a, radius=15)
        self.text(72, 44, 68, 52, brand_initials, font=FONT_SERIF, size=30,
                  color=d, style="bold", align="center", valign="center")
        self.text(160, 30, 620, 46, self.brand, font=FONT_SERIF, size=31,
                  color="#F8F5EC", style="bold")
        self.text(161, 78, 620, 30, self.brand_sub, font=FONT, size=14,
                  color="#C9D2CA")
        self.text(900, 34, 268, 22, meta_label, font=FONT_EN, size=10,
                  color="#B7C2B8", align="right")
        self.text(720, 54, 448, 28, doc_no, font=FONT_EN, size=16,
                  color="#F8F5EC", style="bold", align="right")
        # barcode
        widths = [2, 1, 3, 1, 2, 4, 1, 2, 1, 3, 2, 1, 4, 1, 2]
        self.bars(1030, 92, 34, widths, color="#E8E3D6")

    def title(self, title: str, subtitle: str, doc_no: str, date_text: str,
              subtitle_font=FONT, title_size=33):
        rtl = self.rtl
        self.rect(0, 158, PAGE_W, 112, fill="#FFFDF7")
        align = "right" if rtl else "left"
        x = PAGE_W - MARGIN - 800 if rtl else MARGIN
        self.text(x, 174, 800, 44, title, font=FONT_SERIF, size=title_size,
                  color=INK, style="bold", align=align)
        self.text(x, 218, 800, 32, subtitle, font=subtitle_font, size=17,
                  color=self.accent, align=align)
        meta_x = MARGIN if rtl else PAGE_W - MARGIN - 250
        meta_align = "left" if rtl else "right"
        self.text(meta_x, 172, 250, 18, "DOCUMENT NO.", font=FONT_EN, size=9,
                  color=LIGHT, align=meta_align)
        self.text(meta_x, 188, 250, 24, doc_no, font=FONT_EN, size=14,
                  color=INK, style="bold", align=meta_align)
        self.text(meta_x, 216, 250, 18, "RECEIVED", font=FONT_EN, size=9,
                  color=LIGHT, align=meta_align)
        self.text(meta_x, 232, 250, 24, date_text, font=FONT_EN, size=13,
                  color=INK, align=meta_align)
        self.line(MARGIN, 270, PAGE_W - MARGIN, 270, color=RULE, width=1)

    def footer(self, doc_no: str, page_label: str = "Page 1 of 1"):
        y = PAGE_H - 92
        self.line(MARGIN, y, PAGE_W - MARGIN, y, color=RULE, width=1)
        self.text(MARGIN, y + 14, 760, 34,
                  "Specimen document generated for the Akshara product demonstration. "
                  "Fictitious data; not a valid financial or insurance record.",
                  font=FONT_EN, size=10, color=LIGHT)
        self.text(PAGE_W - MARGIN - 300, y + 14, 300, 20, doc_no,
                  font=FONT_EN, size=10, color=LIGHT, align="right")
        self.text(PAGE_W - MARGIN - 300, y + 32, 300, 20, page_label,
                  font=FONT_EN, size=10, color=LIGHT, align="right")

    def watermark(self):
        if not self.watermark_text:
            return
        self.text(120, PAGE_H / 2 - 100, PAGE_W - 240, 200, self.watermark_text,
                  font=FONT_SERIF, size=112, color="#14221D0D",
                  style="bold", align="center", valign="center", rotate=-24,
                  cx=PAGE_W / 2, cy=PAGE_H / 2)
        self.text(120, PAGE_H / 2 + 52, PAGE_W - 240, 40, "DEMO DATA",
                  font=FONT_EN, size=16, color="#14221D12", align="center",
                  rotate=-24, cx=PAGE_W / 2, cy=PAGE_H / 2)

    def paper_artifacts(self):
        # A gentle fold shadow and punch holes make the scans feel physical.
        self.line(632, 286, 632, PAGE_H - 110, color="#7D766814", width=2)
        self.line(636, 286, 636, PAGE_H - 110, color="#FFFFFF66", width=1)
        for cy in (70, PAGE_H / 2, PAGE_H - 70):
            self.ellipse(18, cy - 9, 18, 18, fill="#E7E2D5", stroke="#D2CCBE", width=1)

    # ------------------------------------------------------------------ sections
    def start_section(self, y: float, title: str, subtitle: str = "",
                      width: int = CONTENT_W) -> float:
        self.section_title = title
        rtl = self.rtl
        x0 = PAGE_W - MARGIN - width if rtl else MARGIN
        if rtl:
            self.rect(x0 + width - 6, y + 2, 6, 22, fill=self.accent, radius=2)
            self.text(x0, y - 4, width - 18, 32, subtitle or title,
                      font=FONT, size=16, color=INK, style="bold", align="right")
            if subtitle:
                self.text(x0, y + 22, width - 18, 22, title, font=FONT_EN,
                          size=10, color=LIGHT, align="right")
        else:
            self.rect(x0, y + 2, 6, 22, fill=self.accent, radius=2)
            self.text(x0 + 16, y - 4, width - 18, 32, title,
                      font=FONT_EN, size=13, color=INK, style="bold")
            if subtitle:
                self.text(x0 + 17, y + 20, width - 18, 22, subtitle,
                          font=FONT, size=14, color=MUTED)
        line_y = y + 40 if subtitle else y + 32
        self.line(x0, line_y, x0 + width, line_y, color=RULE, width=1)
        return line_y + 16

    def section(self, y: float, section: SectionSpec) -> float:
        """Two-column flow with optional full-width fields."""
        width = section.width
        x0 = PAGE_W - MARGIN - width if self.rtl else MARGIN
        y = self.start_section(y, section.title, section.subtitle, width)
        col_gap = 34
        cols = max(1, section.columns)
        col_w = (width - col_gap * (cols - 1)) / cols
        row_h = section.row_h

        # Build rows, giving full-width fields their own row.
        rows: list[list[FieldSpec]] = []
        pending: list[FieldSpec] = []
        for f in section.fields:
            if f.full:
                if pending:
                    rows.append(pending)
                    pending = []
                rows.append([f])
            else:
                pending.append(f)
                if len(pending) == cols:
                    rows.append(pending)
                    pending = []
        if pending:
            rows.append(pending)

        for row in rows:
            if len(row) == 1 and row[0].full:
                self.field(row[0], x0, y, width, row_h)
            else:
                for idx, f in enumerate(row):
                    if self.rtl:
                        col = cols - 1 - idx
                        fx = x0 + col * (col_w + col_gap)
                    else:
                        fx = x0 + idx * (col_w + col_gap)
                    self.field(f, fx, y, col_w, row_h)
            y += row_h
        return y + 18

    def field(self, f: FieldSpec, x: float, y: float, w: float, h: float):
        rtl = self.rtl or f.dir == "rtl"
        align = "right" if rtl else "left"
        label_x = x
        label_w = w
        self.fields.append({
            "key": f.key, "label": f.label, "label_sub": f.label_sub,
            "type": f.type, "required": f.required, "options": f.options,
            "section": self.section_title, "dir": f.dir,
            "confidence": f.confidence, "error": f.error, "truth": f.value,
            "rect": [x, y, w, h],
        })
        self._field_by_key[f.key] = self.fields[-1]

        if rtl:
            self.text(label_x, y - 2, label_w, 22, f.label_sub or f.label,
                      font=FONT, size=15, color=MUTED, style="bold", align="right")
            self.text(label_x, y + 19, label_w, 18, f.label, font=FONT_EN,
                      size=10, color=LIGHT, align="right")
            value_y = y + 38
        else:
            self.text(label_x, y - 2, label_w, 20, f.label.upper(),
                      font=FONT_EN, size=11, color=MUTED, style="bold")
            if f.label_sub:
                self.text(label_x, y + 18, label_w, 20, f.label_sub,
                          font=FONT, size=13, color=LIGHT)
                value_y = y + 40
            else:
                value_y = y + 24

        value_font = FONT if _has_non_latin(f.value) or rtl else FONT_HAND
        value_size = f.font_size
        text_x = x
        text_w = w
        if f.type == "signature":
            self._signature(x, y + 40, w, 30)
            self._field_by_key[f.key]["rect"] = [x, y + 36, w, 40]
            return

        if f.type == "choice":
            box_x = x + w - 22 if rtl else x
            self.rect(box_x, value_y + 2, 18, 18, fill="#FFFFFF",
                      stroke="#7A7A6E", width=1.2)
            self.line(box_x + 4, value_y + 11, box_x + 8, value_y + 15,
                      color=INK_BLUE, width=2)
            self.line(box_x + 8, value_y + 15, box_x + 15, value_y + 5,
                      color=INK_BLUE, width=2)
            if rtl:
                text_x = x
                text_w = w - 30
            else:
                text_x = x + 28
                text_w = w - 28
        elif f.type == "consent":
            self.rect(x, value_y + 2, 18, 18, fill="#FFFFFF",
                      stroke="#7A7A6E", width=1.2)
            self.line(x + 4, value_y + 11, x + 8, value_y + 15,
                      color=INK_BLUE, width=2)
            self.line(x + 8, value_y + 15, x + 15, value_y + 5,
                      color=INK_BLUE, width=2)
            text_x = x + 28
            text_w = w - 28

        # GDI+ shapes Arabic/Indic correctly even without the RTL paragraph
        # flag; using DirectionRightToLeft together with Far alignment
        # double-flips the origin and left-aligns the value. Align right is
        # enough for these single-line fields.
        self.text(text_x, value_y, text_w, 42, f.value, font=value_font,
                  size=value_size, color=INK_BLUE, align=align,
                  id=f.key)
        # dotted writing rule
        rule_y = y + h - 14
        self.line(x, rule_y, x + w, rule_y, color="#BDB7A8", width=0.8, dash="dot")

    def _signature(self, x, y, w, h):
        # A loose, deterministic signature stroke.
        pts = [
            (x + 8, y + h - 6), (x + 22, y - 8), (x + 34, y + 4),
            (x + 48, y + h - 2), (x + 60, y + 6), (x + 66, y + h - 4),
            (x + 84, y - 2), (x + 98, y + h - 8), (x + 112, y + 2),
            (x + 132, y + h - 4), (x + 146, y + 2), (x + 162, y + h - 10),
        ]
        self.path(pts, color="#244A6B", width=2.0)
        self.line(x, y + h + 2, x + min(w, 210), y + h + 2, color="#BDB7A8",
                  width=0.8)

    # ------------------------------------------------------------------ special
    def photo_box(self, x, y, w, h, caption="AFFIX PHOTO"):
        self.rect(x, y, w, h, fill="#F4F1E8", stroke="#B9B4A6", width=1.2,
                  radius=4)
        self.rect(x + 12, y + 12, w - 24, h - 24, fill="none",
                  stroke="#D3CDBE", width=1, radius=2)
        # simple portrait silhouette
        cx = x + w / 2
        self.ellipse(cx - 26, y + 38, 52, 52, fill="#DAD4C5")
        self.ellipse(cx - 42, y + 102, 84, 66, fill="#DAD4C5")
        self.text(x, y + h - 32, w, 20, caption, font=FONT_EN, size=9,
                  color=LIGHT, align="center")

    def id_card(self, x, y, w, h, title, number, name):
        self.rect(x, y, w, h, fill="#F1EEE3", stroke="#B9B4A6", width=1.1,
                  radius=5)
        self.rect(x, y, w, 28, fill="#E3DED0", radius=5)
        self.text(x + 12, y + 6, w - 24, 18, title, font=FONT_EN, size=10,
                  color=MUTED, style="bold")
        self.ellipse(x + 14, y + 42, 34, 34, fill="#D5CFC0")
        self.text(x + 58, y + 40, w - 70, 22, name, font=FONT, size=13,
                  color=INK, style="bold")
        self.text(x + 58, y + 64, w - 70, 20, number, font=FONT_EN, size=12,
                  color=INK_BLUE)
        self.text(x + 58, y + 86, w - 70, 28, "DEMO / SPECIMEN", font=FONT_EN,
                  size=8, color=LIGHT)
        self.bars(x + 14, y + h - 30, 18, [2, 1, 3, 1, 2, 2, 1, 4, 1, 2, 1],
                  color="#8C8778")

    def stamp(self, cx, cy, text1="VERIFIED", text2="BRANCH OPERATIONS",
              color="#B23A34"):
        # Decorative stamp. Alpha blends into the scan.
        self.ellipse(cx - 84, cy - 84, 168, 168, fill="none",
                     stroke=color + "AA", width=2.2)
        self.ellipse(cx - 72, cy - 72, 144, 144, fill="none",
                     stroke=color + "66", width=1)
        self.text(cx - 70, cy - 26, 140, 28, text1, font=FONT_EN, size=15,
                  color=color + "CC", style="bold", align="center",
                  rotate=-9, cx=cx, cy=cy)
        self.text(cx - 70, cy + 2, 140, 20, text2, font=FONT_EN, size=8,
                  color=color + "AA", style="bold", align="center",
                  rotate=-9, cx=cx, cy=cy)
        self.text(cx - 70, cy + 22, 140, 18, "12 NOV 2026", font=FONT_EN,
                  size=8, color=color + "99", align="center", rotate=-9,
                  cx=cx, cy=cy)
        self.line(cx - 54, cy - 2, cx + 54, cy - 2, color=color + "88",
                  width=1)

    def summary_box(self, x, y, w, h, label, value, sub="", fill="#F4F1E8",
                    value_id=None, value_size=22):
        self.rect(x, y, w, h, fill=fill, stroke=RULE, width=1, radius=5)
        self.text(x + 16, y + 12, w - 32, 18, label.upper(), font=FONT_EN,
                  size=9, color=MUTED, style="bold")
        self.text(x + 16, y + 32, w - 32, 34, value, font=FONT_EN,
                  size=value_size, color=INK, style="bold", id=value_id)
        if sub:
            self.text(x + 16, y + 66, w - 32, 18, sub, font=FONT_EN, size=9,
                      color=LIGHT)

    def table(self, x, y, width, columns, rows, header_fill="#E9E4D7",
              row_h=44, accent=None):
        """columns: [(title, width_fraction, align)]; rows: list of dicts with
        `cells` (list of str) and optional `keys` (list of field keys)."""
        accent = accent or self.accent
        self.rect(x, y, width, 34, fill=self.dark)
        cx = x
        for title, frac, align in columns:
            cw = width * frac
            self.text(cx + 10, y + 8, cw - 20, 20, title.upper(),
                      font=FONT_EN, size=9, color="#F5F1E6",
                      style="bold", align=align)
            cx += cw
        yy = y + 34
        for r_idx, row in enumerate(rows):
            if r_idx % 2 == 0:
                self.rect(x, yy, width, row_h, fill="#F7F4EB")
            self.line(x, yy + row_h, x + width, yy + row_h, color="#E1DCCE",
                      width=0.8)
            cx = x
            for c_idx, (title, frac, align) in enumerate(columns):
                cw = width * frac
                cell = row["cells"][c_idx]
                key = row.get("keys", [None] * len(columns))[c_idx]
                if cell:
                    self.text(cx + 10, yy + (row_h - 20) / 2, cw - 20, 24,
                              cell, font=FONT_EN if _is_ascii(cell) else FONT,
                              size=14, color=INK, align=align, id=key)
                if key:
                    self.fields.append({
                        "key": key, "label": title, "label_sub": "",
                        "type": "text", "required": True, "options": [],
                        "section": self.section_title,
                        "dir": "rtl" if self.rtl else "ltr",
                        "confidence": 0.96, "error": None, "truth": cell,
                        "rect": [cx, yy, cw, row_h],
                    })
                    self._field_by_key[key] = self.fields[-1]
                cx += cw
            yy += row_h
        self.rect(x, y, width, yy - y, fill="none", stroke="#CFC9BA", width=1)
        return yy

    # ------------------------------------------------------------------ final
    def finalize(self, measured: dict[str, dict[str, float]]):
        """Attach measured value boxes, falling back to the reserved field rect."""
        for f in self.fields:
            m = measured.get(f["key"])
            if m:
                f["bbox"] = [round(m["x"], 1), round(m["y"], 1),
                             round(m["w"], 1), round(m["h"], 1)]
            else:
                x, y, w, h = f["rect"]
                f["bbox"] = [round(x, 1), round(y, 1), round(w, 1),
                             round(min(34, h), 1)]
            f.pop("rect", None)
        return self.fields


def _is_ascii(s: str) -> bool:
    return all(ord(c) < 128 for c in s)


def _has_non_latin(s: str) -> bool:
    return any(ord(c) > 127 for c in s)


def regional_font(text: str) -> str:
    return FONT if _has_non_latin(text) else FONT_HAND


def dotted_rect(form: Form, x, y, w, h, color="#C9C3B4"):
    form.rect(x, y, w, h, fill="none", stroke=color, width=1, radius=4)
