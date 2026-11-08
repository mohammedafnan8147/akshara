"""Local Tesseract OCR adapter.

The prototype can run without any cloud credentials. If Tesseract is
installed, uploads are genuinely OCR'd (word boxes + per-word confidence) and
the extraction layer maps labels to values. If it is absent, the caller falls
back to an explicit manual-indexing task.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

WINDOWS_CANDIDATES = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)
LANG_MAP = {"en": "eng", "hi": "hin", "mr": "mar", "ta": "tam",
            "bn": "ben", "ar": "ara"}


class OcrError(RuntimeError):
    pass


class OcrUnavailable(OcrError):
    pass


@dataclass
class OcrWord:
    text: str
    conf: float
    left: float
    top: float
    width: float
    height: float
    line: tuple[int, int, int, int]
    word_num: int

    @property
    def right(self) -> float:
        return self.left + self.width

    @property
    def bottom(self) -> float:
        return self.top + self.height


@dataclass
class OcrLine:
    key: tuple[int, int, int, int]
    words: list[OcrWord] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words).strip()

    @property
    def left(self) -> float:
        return min(w.left for w in self.words) if self.words else 0

    @property
    def top(self) -> float:
        return min(w.top for w in self.words) if self.words else 0

    @property
    def right(self) -> float:
        return max(w.right for w in self.words) if self.words else 0

    @property
    def bottom(self) -> float:
        return max(w.bottom for w in self.words) if self.words else 0

    @property
    def conf(self) -> float:
        return sum(w.conf for w in self.words) / len(self.words) if self.words else 0

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return (round(self.left, 1), round(self.top, 1),
                round(self.right - self.left, 1), round(self.bottom - self.top, 1))


@dataclass
class OcrResult:
    words: list[OcrWord]
    lines: list[OcrLine]
    text: str
    mean_conf: float
    engine: str
    version: str
    language: str
    requested_language: str
    psm: int
    image_size: tuple[int, int] | None = None

    @property
    def word_count(self) -> int:
        return len(self.words)

    @property
    def line_count(self) -> int:
        return len(self.lines)

    def meta(self) -> dict:
        return {
            "engine": self.engine,
            "version": self.version,
            "language": self.language,
            "requested_language": self.requested_language,
            "psm": self.psm,
            "words": self.word_count,
            "lines": self.line_count,
            "mean_confidence": round(self.mean_conf, 3),
        }


@lru_cache(maxsize=1)
def find_tesseract() -> str | None:
    env = os.environ.get("TESSERACT_CMD")
    if env and Path(env).is_file():
        return env
    found = shutil.which("tesseract")
    if found:
        return found
    for candidate in WINDOWS_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    return None


@lru_cache(maxsize=4)
def _version(exe: str) -> str:
    try:
        proc = subprocess.run([exe, "--version"], capture_output=True, text=True,
                              timeout=15, creationflags=_flags())
        first = (proc.stdout or proc.stderr or "").splitlines()
        return first[0].strip() if first else "Tesseract"
    except Exception:
        return "Tesseract"


@lru_cache(maxsize=4)
def available_languages(exe: str | None = None) -> list[str]:
    exe = exe or find_tesseract()
    if not exe:
        return []
    try:
        proc = subprocess.run([exe, "--list-langs"], capture_output=True, text=True,
                              timeout=15, creationflags=_flags())
        langs = []
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if line and " " not in line and line not in ("List",):
                langs.append(line)
        return langs
    except Exception:
        return []


def _flags() -> int:
    return 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW


def status() -> dict:
    exe = find_tesseract()
    if not exe:
        return {"available": False, "path": None, "version": None,
                "languages": [], "detail": "Tesseract binary not found"}
    langs = available_languages(exe)
    version = _version(exe)
    return {
        "available": True, "path": exe, "version": version,
        "languages": langs,
        "detail": f"{version.split(' ')[0]} {version.split(' ')[1] if len(version.split(' ')) > 1 else ''}".strip()
                  + " · " + (", ".join(langs) if langs else "no language data"),
    }


def parse_tsv(text: str, engine: str = "Tesseract", version: str = "",
              language: str = "eng", requested_language: str = "en",
              psm: int = 3) -> OcrResult:
    words: list[OcrWord] = []
    for raw in text.splitlines():
        cols = raw.split("\t")
        if len(cols) < 12 or cols[0] != "5":
            continue
        try:
            conf = float(cols[10])
            if conf < 0:
                continue
            word = cols[11].strip()
            if not word:
                continue
            key = (int(cols[1]), int(cols[2]), int(cols[3]), int(cols[4]))
            words.append(OcrWord(
                text=word, conf=conf / 100.0,
                left=float(cols[6]), top=float(cols[7]),
                width=float(cols[8]), height=float(cols[9]),
                line=key, word_num=int(cols[5]),
            ))
        except (ValueError, IndexError):
            continue

    grouped: dict[tuple[int, int, int, int], list[OcrWord]] = {}
    for w in words:
        grouped.setdefault(w.line, []).append(w)
    lines = [OcrLine(key=k, words=sorted(v, key=lambda x: x.word_num))
             for k, v in grouped.items()]
    lines.sort(key=lambda l: (round(l.top, 1), l.left))
    text_out = "\n".join(l.text for l in lines if l.text)
    mean = sum(w.conf for w in words) / len(words) if words else 0.0
    return OcrResult(words=words, lines=lines, text=text_out, mean_conf=mean,
                     engine=engine, version=version, language=language,
                     requested_language=requested_language, psm=psm)


class MergedOcr:
    """Aggregate pages of a multi-page OCR run for persistence and review."""

    def __init__(self, results: list[OcrResult]):
        if not results:
            raise OcrError("No OCR pages to merge.")
        self.results = results
        self.engine = results[0].engine
        self.version = results[0].version
        self.language = results[0].language
        self.requested_language = results[0].requested_language
        self.psm = results[0].psm
        self.word_count = sum(r.word_count for r in results)
        self.line_count = sum(r.line_count for r in results)
        total_words = max(1, self.word_count)
        self.mean_conf = sum(r.mean_conf * r.word_count for r in results) / total_words
        self.text = "\n".join(
            f"--- Page {i + 1} ---\n{result.text}" for i, result in enumerate(results)
        )

    def meta(self) -> dict:
        return {
            "engine": self.engine,
            "version": self.version,
            "language": self.language,
            "requested_language": self.requested_language,
            "psm": self.psm,
            "words": self.word_count,
            "lines": self.line_count,
            "mean_confidence": round(self.mean_conf, 3),
            "pages": len(self.results),
            "page_confidence": [round(r.mean_conf, 3) for r in self.results],
        }


def run_tesseract(image_path: str | Path, lang: str = "en", psm: int = 3,
                  timeout: int = 60) -> OcrResult:
    exe = find_tesseract()
    if not exe:
        raise OcrUnavailable("Tesseract is not installed.")
    path = str(Path(image_path))
    if not Path(path).is_file():
        raise OcrError("Image file not found.")
    requested = LANG_MAP.get(lang, lang or "eng")
    langs = available_languages(exe)
    chosen = requested
    if langs and requested not in langs:
        chosen = "eng" if "eng" in langs else (langs[0] if langs else "eng")
    version = _version(exe)
    cmd = [exe, path, "stdout", "-l", chosen, "--psm", str(psm), "tsv"]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout,
                              creationflags=_flags())
    except subprocess.TimeoutExpired as exc:
        raise OcrError("OCR timed out.") from exc
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", "replace").strip()
        raise OcrError(f"Tesseract failed: {err[:300] or 'unknown error'}")
    raw = (proc.stdout or b"").decode("utf-8-sig", "replace")
    result = parse_tsv(raw, engine="Tesseract", version=version,
                       language=chosen, requested_language=lang, psm=psm)
    if not result.words:
        raise OcrError("Tesseract found no readable words. The scan may be too poor or in an unsupported script.")
    return result
