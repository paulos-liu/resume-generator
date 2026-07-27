#!/usr/bin/env python3
"""Render a draft.md to PDF via headless Chrome.

Not a general Markdown converter. It handles exactly the subset
`templates/standard.md` produces -- `#` name, one contact paragraph, `##`
sections, `###` roles, `- ` bullets, and plain lines -- and raises on anything
else rather than guessing. A converter that silently drops what it does not
understand is worse than one that stops, because the loss shows up on a
document you already sent.

Chrome is used because it paginates for real: the page count it reports is the
page count a reader gets. That is what makes `--measure` trustworthy enough to
calibrate `max_lines` against, which is the whole reason this exists.
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)

# `**bold**` and `_italic_` are the only inline markup the template uses.
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
ITALIC_RE = re.compile(r"(?<!\w)_(.+?)_(?!\w)")


def find_chrome() -> str | None:
    for name in ("google-chrome", "chromium", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    for path in CHROME_CANDIDATES:
        if Path(path).is_file():
            return path
    return None


def _inline(text: str) -> str:
    """Escape, then restore the two inline markers the template allows."""
    out = html.escape(text)
    out = BOLD_RE.sub(r"<strong>\1</strong>", out)
    out = ITALIC_RE.sub(r"<em>\1</em>", out)
    return out


def markdown_to_html(md: str, css: str) -> str:
    body: list = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            body.append("</ul>")
            in_list = False

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("- "):
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{_inline(line[2:].strip())}</li>")
            continue
        close_list()
        if line.startswith("### "):
            body.append(f"<h3>{_inline(line[4:].strip())}</h3>")
        elif line.startswith("## "):
            body.append(f"<h2>{_inline(line[3:].strip())}</h2>")
        elif line.startswith("# "):
            body.append(f"<h1>{_inline(line[2:].strip())}</h1>")
        elif line.startswith("#"):
            raise ValueError(f"unsupported heading depth: {line!r}")
        else:
            body.append(f"<p>{_inline(line.strip())}</p>")
    close_list()

    return ("<!doctype html><html><head><meta charset='utf-8'>"
            f"<style>{css}</style></head><body>"
            + "\n".join(body) + "</body></html>")


def render(draft: Path, css: Path, out: Path, chrome: str,
           timeout: int = 90) -> None:
    """Print the draft to `out`, then stop waiting on Chrome.

    Chrome writes the PDF and then frequently does not exit -- so waiting for
    the process is waiting for the wrong thing. Poll for the file instead, let
    it settle so a partial write is never measured, and terminate. Anything
    else hangs for the full timeout on a render that already succeeded.
    """
    page = markdown_to_html(draft.read_text(encoding="utf-8"),
                            css.read_text(encoding="utf-8"))
    out = out.resolve()
    if out.exists():
        out.unlink()  # never mistake a stale PDF for this run's output

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "resume.html"
        src.write_text(page, encoding="utf-8")
        proc = subprocess.Popen(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
             "--no-first-run", "--disable-extensions",
             "--disable-background-networking", "--disable-sync",
             f"--user-data-dir={tmp}/profile", "--no-pdf-header-footer",
             f"--print-to-pdf={out}", src.as_uri()],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + timeout
            size = -1
            while time.monotonic() < deadline:
                if proc.poll() is not None and out.is_file():
                    break
                if out.is_file():
                    current = out.stat().st_size
                    if current > 0 and current == size:
                        break  # size stable across a poll: write finished
                    size = current
                time.sleep(0.25)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()

    if not out.is_file() or out.stat().st_size == 0:
        stderr = (proc.stderr.read() or b"").decode("utf-8", "replace")
        raise RuntimeError(f"chrome produced no PDF\n{stderr.strip()}")


def page_count(pdf: Path) -> int:
    """Count pages without a PDF library, by counting /Type /Page objects."""
    blob = pdf.read_bytes()
    pages = len(re.findall(rb"/Type\s*/Page[^s]", blob))
    return pages or 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path)
    parser.add_argument("--css", type=Path, default=Path("templates/print.css"))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--measure", action="store_true",
                        help="report page count and the draft's line count")
    args = parser.parse_args()

    chrome = find_chrome()
    if chrome is None:
        print("No Chrome/Chromium found. Install one, or render in Cowork "
              "(see plugin/skills/render-resume/SKILL.md).", file=sys.stderr)
        return 2

    out = args.out or args.draft.with_suffix(".pdf")
    render(args.draft, args.css, out, chrome)
    pages = page_count(out)
    lines = len([l for l in args.draft.read_text(encoding="utf-8").splitlines()
                 if l.strip()])
    print(f"wrote {out} — {pages} page(s)")
    if args.measure:
        print(f"draft markdown non-blank lines: {lines}")
        print(f"verdict: {'ONE PAGE' if pages == 1 else f'OVERFLOWS ({pages} pages)'}")
    return 0 if pages == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
