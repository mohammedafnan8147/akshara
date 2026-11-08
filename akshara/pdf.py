"""PDF rasterisation through the built-in Windows.Data.Pdf renderer.

No external PDF package is required. The actual rasterisation is performed by
`tools/pdf_render.ps1`, which loads the PDF from a .NET stream (avoiding the
WinRT StorageFile capability restriction) and writes one PNG per page.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from .imageutil import file_dimensions

ROOT = Path(__file__).resolve().parents[1]
RENDER_SCRIPT = ROOT / "tools" / "pdf_render.ps1"
POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"


class PdfError(RuntimeError):
    pass


def available() -> bool:
    return sys.platform == "win32" and RENDER_SCRIPT.is_file() and Path(POWERSHELL).is_file()


def status() -> dict:
    return {
        "available": available(),
        "engine": "Windows.Data.Pdf",
        "detail": "Built-in Windows PDF rasteriser" if available() else "PDF rasteriser unavailable",
    }


def render_pdf(pdf_path: str | Path, out_dir: str | Path, max_pages: int = 8) -> dict:
    if not available():
        raise PdfError("PDF rasterisation is not available on this platform.")
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not pdf_path.is_file():
        raise PdfError("PDF file not found.")
    cmd = [
        POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(RENDER_SCRIPT),
        "-Pdf", str(pdf_path),
        "-OutDir", str(out_dir),
        "-MaxPages", str(max(1, min(max_pages, 20))),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=150,
                              creationflags=0x08000000 if sys.platform == "win32" else 0)
    except subprocess.TimeoutExpired as exc:
        raise PdfError("PDF rendering timed out.") from exc
    out = (proc.stdout or b"").decode("utf-8", "replace").strip()
    if proc.returncode != 0 or not out:
        err = (proc.stderr or b"").decode("utf-8", "replace").strip()
        raise PdfError(f"PDF renderer failed: {err[-500:] or 'no output'}")
    try:
        payload = json.loads(out.splitlines()[-1])
    except (ValueError, json.JSONDecodeError) as exc:
        raise PdfError("PDF renderer returned an invalid response.") from exc
    pages = []
    for item in payload.get("pages", []):
        path = Path(item["file"])
        if not path.is_file():
            continue
        dims = file_dimensions(path)
        width, height = dims if dims else (item.get("width", 1240), item.get("height", 1754))
        pages.append({
            "no": int(item["no"]),
            "path": path,
            "width": width,
            "height": height,
        })
    if not pages:
        raise PdfError("PDF contained no renderable pages.")
    return {
        "total": int(payload.get("total", len(pages))),
        "rendered": len(pages),
        "pages": pages,
    }
