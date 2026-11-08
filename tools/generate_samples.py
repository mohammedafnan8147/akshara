"""Generate specimen scans, OCR fixtures, and thumbnails.

Usage (from the workspace root):
    python tools/generate_samples.py [--only bank_01] [--no-effects]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import samples_data as sd  # noqa: E402

BUILD = ROOT / "build" / "forms"
OUT = ROOT / "data" / "samples"
RENDER_PS1 = ROOT / "tools" / "render.ps1"
POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"


def scan_effects(img: Image.Image, quality: str, seed: str) -> Image.Image:
    rnd = np.random.default_rng(abs(hash(seed)) % (2**32))
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    h, w, _ = arr.shape

    settings = {
        "good": (1.4, 0.15, 94, 0.06),
        "fair": (2.8, 0.30, 90, 0.10),
        "poor": (5.5, 0.55, 80, 0.16),
    }[quality]
    noise_sigma, blur, jpeg_q, stain_alpha = settings

    # Sensor grain.
    arr += rnd.normal(0, noise_sigma, (h, w, 1)).astype(np.float32)
    # Very low-frequency paper tone variation.
    small = rnd.normal(0, 5.0, (h // 40 + 2, w // 40 + 2, 1)).astype(np.float32)
    field = np.asarray(Image.fromarray(np.clip(small[:, :, 0] + 128, 0, 255).astype(np.uint8))
                       .resize((w, h), Image.Resampling.BICUBIC)).astype(np.float32) - 128
    arr += field[:, :, None] * 0.4

    # Vignette / phone-camera falloff.
    yy, xx = np.mgrid[0:h, 0:w]
    nx = (xx - w / 2) / (w / 2)
    ny = (yy - h / 2) / (h / 2)
    radius = np.sqrt(nx * nx + ny * ny)
    vignette = np.clip(1.0 - settings[3] * radius ** 2, 0.72, 1.0)
    arr *= vignette[:, :, None]

    # Fine scanner lines.
    line = np.ones((h, 1, 1), dtype=np.float32)
    line[::5, 0, 0] = 0.988
    arr *= line

    arr = np.clip(arr, 0, 255).astype(np.uint8)
    out = Image.fromarray(arr, "RGB")
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out = ImageEnhance.Contrast(out).enhance(1.03)

    # Paper stains and edge shadow, kept away from dense text.
    if quality == "poor":
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        cx, cy = int(w * 0.82), int(h * 0.78)
        for r in range(170, 10, -8):
            a = int(stain_alpha * 255 * (1 - r / 180) * 0.16)
            d.ellipse((cx - r, cy - int(r * 0.55), cx + r, cy + int(r * 0.55)),
                      fill=(132, 96, 48, a))
        overlay = overlay.filter(ImageFilter.GaussianBlur(9))
        out = Image.alpha_composite(out.convert("RGBA"), overlay).convert("RGB")
    if quality in ("fair", "poor"):
        shade = Image.new("L", (w, h), 0)
        ds = ImageDraw.Draw(shade)
        ds.rectangle((0, 0, w - 1, h - 1), outline=255, width=10)
        shade = shade.filter(ImageFilter.GaussianBlur(9))
        dark = ImageEnhance.Brightness(out).enhance(0.82)
        out = Image.composite(dark, out, shade)

    # JPEG generation loss, then save as a clean PNG for rendering.
    import io
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=jpeg_q, subsampling=2)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--no-effects", action="store_true")
    args = ap.parse_args()

    if not RENDER_PS1.exists():
        print(f"Renderer script missing: {RENDER_PS1}", file=sys.stderr)
        return 2
    BUILD.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    chosen = [s for s in sd.SAMPLES if not args.only or s.id in args.only]
    index = []
    for s in chosen:
        print(f"  · {s.id} ({s.kind}, {s.lang}, {s.quality})", flush=True)
        form, meta = sd.build_sample(s)
        cmd_path = BUILD / f"{s.id}.json"
        meta_path = BUILD / f"{s.id}.meta.json"
        png_path = BUILD / f"{s.id}.raw.png"
        cmd_path.write_text(json.dumps({
            "width": sd.PAGE_W if hasattr(sd, "PAGE_W") else 1240,
            "height": sd.PAGE_H if hasattr(sd, "PAGE_H") else 1754,
            "background": "#FBF8F0",
            "ops": form.ops,
        }, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run([
            POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(RENDER_PS1),
            "-Commands", str(cmd_path), "-Out", str(png_path), "-Meta", str(meta_path),
        ], capture_output=True, text=True)
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
            return 3
        measured = json.loads(meta_path.read_text(encoding="utf-8"))
        fields = form.finalize(measured)
        ocr_by_key = {f["key"]: f for f in meta.pop("field_ocr")}
        for fld in fields:
            ocr = ocr_by_key.get(fld["key"], {})
            fld["value"] = ocr.get("value", fld.get("truth", ""))
            fld["confidence"] = ocr.get("confidence", fld.get("confidence", 0.95))
            fld["dir"] = ocr.get("dir", "ltr")
            fld["corrected"] = False
        meta["fields"] = fields

        img = Image.open(png_path).convert("RGB")
        if not args.no_effects:
            img = scan_effects(img, s.quality, s.id)
        final_img = OUT / f"{s.id}.jpg"
        img.save(final_img, "JPEG", quality=90 if s.quality != "poor" else 84,
                 optimize=True, subsampling=1)
        thumb = img.copy()
        thumb.thumbnail((420, 594), Image.Resampling.LANCZOS)
        thumb.save(OUT / f"{s.id}_thumb.jpg", "JPEG", quality=82, optimize=True)

        confs = [f["confidence"] for f in meta["fields"]]
        doc_conf = round(0.55 * min(confs) + 0.45 * (sum(confs) / len(confs)), 3)
        meta["confidence"] = doc_conf
        meta["low_count"] = sum(1 for c in confs if c < 0.8)
        meta["field_count"] = len(meta["fields"])
        meta["thumb"] = f"{s.id}_thumb.jpg"
        meta["preview"] = f"{s.id}.jpg"
        meta["doc_type"] = s.kind
        meta["doc_type_label"] = {
            "bank": "Account opening", "claim": "Health claim",
            "service": "Service request", "loan": "Loan application",
            "invoice": "Tax invoice", "kyc": "KYC update",
        }[s.kind]
        (OUT / f"{s.id}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
        index.append({k: meta[k] for k in (
            "id", "kind", "doc_type", "doc_type_label", "ref", "title", "customer_name",
            "language", "language_name", "script", "quality", "status", "priority",
            "confidence", "low_count", "field_count", "amount", "thumb", "preview")})
        print(f"    confidence {doc_conf:.3f} · {len(meta['fields'])} fields · {final_img.stat().st_size // 1024} KB")

    if not args.only:
        (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
        print(f"\nWrote {len(index)} fixtures to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
