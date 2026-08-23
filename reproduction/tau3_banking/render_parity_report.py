#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "Markdown==3.10.3",
#   "WeasyPrint==69.0",
#   "pdfplumber==0.11.7",
#   "pypdf==6.1.3",
# ]
# ///
"""Create and verify the Tau3 banking parity PDF from Markdown.

Usage:
  uv run render_parity_report.py report.md report.pdf

The first H1 becomes the title. The first following paragraph becomes the
subtitle. A three-line Markdown table immediately after the subtitle becomes a
metric strip. The command also verifies link annotations and extractable text,
then renders every page to PNG for visual QA.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

BEST_MARKER = "<!-- best -->"


BASE_CSS = r"""
:root {
  --ink: #171512;
  --muted: #68645f;
  --rule: #292621;
  --light-rule: #d8d2c8;
  --code-bg: #f2f2f2;
  --code-border: #d5d5d5;
  --code-ink: #a61436;
  --best-bg: #eaf5ee;
  --best-rule: #247a4a;
  --best-ink: #1b6b42;
}

* { box-sizing: border-box; }

@page {
  size: A4;
  margin: 13mm 14mm 14mm;
}

html, body { background: #fff; }

body {
  margin: 0;
  color: var(--ink);
  font: 14.1px/1.48 "Helvetica Neue", Helvetica, Arial, sans-serif;
}

.top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  margin-bottom: 24px;
}

.doc-label {
  color: var(--muted);
  font-size: 11px;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.brand { font-size: 13px; font-weight: 700; white-space: nowrap; }
h1, h2 { color: var(--ink); font-family: "Times New Roman", Times, Georgia, serif; }

h1 {
  margin: 0 0 14px;
  font-size: 31px;
  line-height: 1.18;
  text-align: center;
}

h2 {
  margin: 25px 0 10px;
  padding-top: 20px;
  border-top: 1px solid var(--rule);
  font-size: 22px;
  line-height: 1.2;
  break-after: avoid-page;
}

.content > h2:first-child { margin-top: 28px; padding-top: 0; border-top: 0; }
h3 { margin: 20px 0 8px; font-size: 15px; line-height: 1.3; break-after: avoid-page; }
h3 + p { break-after: avoid-page; }
p { margin: 0 0 12px; }

.hero-sub {
  max-width: 45em;
  margin: 0 auto 24px;
  color: var(--muted);
  font-size: 14.5px;
  line-height: 1.5;
  text-align: center;
}

.metrics {
  display: grid;
  margin: 0 0 26px;
  border-top: 1px solid var(--rule);
  border-bottom: 1px solid var(--rule);
  break-inside: avoid;
}

.metric { padding: 15px 10px; text-align: center; }
.metric + .metric { border-left: 1px solid var(--light-rule); }
.metric-value { font: 700 24px/1.15 "Times New Roman", Times, Georgia, serif; }
.metric-label {
  margin-top: 4px;
  color: var(--muted);
  font-size: 10px;
  letter-spacing: .06em;
  text-transform: uppercase;
}

code, pre { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; }
:not(pre) > code {
  padding: .06em .30em;
  border: 1px solid var(--code-border);
  border-radius: 4px;
  background: var(--code-bg);
  color: var(--code-ink);
  font-size: .9em;
  white-space: nowrap;
  box-decoration-break: clone;
}

pre {
  margin: 0 0 16px;
  padding: 8px 14px;
  border: 1px solid var(--code-border);
  background: var(--code-bg);
  color: var(--code-ink);
  font-size: 10.2px;
  line-height: 1.34;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  break-inside: avoid;
}

pre code { padding: 0; border: 0; background: transparent; color: inherit; font-size: inherit; }

table { width: 100%; margin: 0 0 14px; border-collapse: collapse; font-size: 12.5px; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
th, td {
  padding: 8px 6px;
  border-bottom: 1px solid var(--light-rule);
  text-align: left;
  vertical-align: top;
}
th { border-bottom: 1.5px solid var(--rule); font-size: 12.5px; font-weight: 700; }
td.best {
  border-bottom: 2px solid var(--best-rule);
  background: var(--best-bg);
  color: var(--best-ink);
  font-weight: 700;
}

ul, ol { margin: 0 0 14px; padding-left: 20px; }
li { margin: 0 0 8px; }
blockquote {
  margin: 16px 0;
  padding-left: 14px;
  border-left: 4px solid var(--light-rule);
  color: var(--muted);
  font-style: italic;
  break-inside: avoid;
}
blockquote p:last-child { margin-bottom: 0; }
img { max-width: 100%; height: auto; }

footer {
  margin-top: 20px;
  padding-top: 8px;
  border-top: 1px solid var(--light-rule);
  color: #88847d;
  font-size: 12px;
}
"""


def parse_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def configure_native_paths() -> None:
    """Expose common Homebrew library paths before WeasyPrint imports CFFI."""
    if sys.platform != "darwin":
        return
    candidates = [
        "/opt/homebrew/lib",
        "/opt/homebrew/opt/pango/lib",
        "/opt/homebrew/opt/glib/lib",
        "/opt/homebrew/opt/harfbuzz/lib",
        "/opt/homebrew/opt/fontconfig/lib",
        "/usr/local/lib",
    ]
    existing = [path for path in candidates if Path(path).is_dir()]
    current = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    if current:
        existing.append(current)
    if existing:
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = os.pathsep.join(existing)


def is_separator_row(line: str) -> bool:
    cells = parse_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def split_document(source: str) -> tuple[str, str, list[tuple[str, str]], str]:
    lines = source.splitlines()
    index = next((i for i, line in enumerate(lines) if line.strip()), None)
    if index is None or not lines[index].startswith("# "):
        raise ValueError("Markdown must start with one H1 title")

    title = lines[index][2:].strip()
    index += 1
    while index < len(lines) and not lines[index].strip():
        index += 1

    subtitle_lines: list[str] = []
    while index < len(lines) and lines[index].strip():
        line = lines[index]
        if line.startswith(("#", "|", "```", ">", "- ", "* ")):
            break
        subtitle_lines.append(line.strip())
        index += 1
    subtitle = " ".join(subtitle_lines)

    while index < len(lines) and not lines[index].strip():
        index += 1

    metrics: list[tuple[str, str]] = []
    if (
        index + 2 < len(lines)
        and lines[index].lstrip().startswith("|")
        and is_separator_row(lines[index + 1])
        and lines[index + 2].lstrip().startswith("|")
    ):
        values = parse_table_row(lines[index])
        labels = parse_table_row(lines[index + 2])
        if len(values) == len(labels) and 2 <= len(values) <= 6:
            metrics = list(zip(values, labels))
            index += 3

    body = "\n".join(lines[index:]).lstrip()
    return title, subtitle, metrics, body


def add_class(attributes: str, class_name: str) -> str:
    match = re.search(r'\bclass="([^"]*)"', attributes)
    if match:
        classes = f"{match.group(1)} {class_name}".strip()
        return (
            attributes[: match.start()]
            + f'class="{classes}"'
            + attributes[match.end() :]
        )
    return attributes + f' class="{class_name}"'


def mark_best_cells(body: str) -> str:
    def replace(match: re.Match[str]) -> str:
        attributes, content = match.group(1), match.group(2)
        if BEST_MARKER not in content:
            return match.group(0)
        content = content.replace(BEST_MARKER, "")
        return f"<td{add_class(attributes, 'best')}>{content}</td>"

    return re.sub(r"<td([^>]*)>(.*?)</td>", replace, body, flags=re.DOTALL)


def inline_markdown(markdown_module, value: str) -> str:
    if not value:
        return ""
    rendered = markdown_module.markdown(value)
    return re.sub(r"^<p>|</p>$", "", rendered.strip())


def build_html(source: Path, brand: str, label: str, extra_css: str) -> str:
    try:
        import markdown
    except ImportError as exc:
        raise RuntimeError("missing Markdown; run this script with `uv run`") from exc

    title, subtitle, metrics, body_source = split_document(
        source.read_text(encoding="utf-8")
    )
    body = markdown.markdown(
        body_source,
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="html5",
    )
    body = mark_best_cells(body)

    metric_html = "\n".join(
        '<div class="metric">'
        f'<div class="metric-value">{inline_markdown(markdown, value)}</div>'
        f'<div class="metric-label">{inline_markdown(markdown, metric_label)}</div>'
        "</div>"
        for value, metric_label in metrics
    )
    metrics_block = ""
    if metrics:
        metrics_block = (
            f'<div class="metrics" style="grid-template-columns:repeat({len(metrics)},1fr)">'
            f"{metric_html}</div>"
        )

    brand_html = f'<div class="brand">★ {html.escape(brand)}</div>' if brand else ""
    footer = f"{brand} · {title}" if brand else title
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{BASE_CSS}\n{extra_css}</style>
</head>
<body>
<article class="sheet">
  <header class="top">
    <div class="doc-label">{html.escape(label)}</div>
    {brand_html}
  </header>
  <h1>{html.escape(title)}</h1>
  <div class="hero-sub">{inline_markdown(markdown, subtitle)}</div>
  {metrics_block}
  <main class="content">{body}</main>
  <footer>{html.escape(footer)}</footer>
</article>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Markdown source")
    parser.add_argument("output", type=Path, help="output PDF")
    parser.add_argument("--brand", default="", help="optional top-right brand")
    parser.add_argument(
        "--label", default="Benchmark Parity Report", help="top-left label"
    )
    parser.add_argument(
        "--css", type=Path, help="CSS appended after the built-in theme"
    )
    parser.add_argument("--html", type=Path, help="also write generated HTML")
    parser.add_argument("--pages-dir", type=Path, help="rendered page PNG directory")
    parser.add_argument("--dpi", type=int, default=150, help="page-render DPI")
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_external_links(source: str) -> set[str]:
    return {
        url
        for url in re.findall(r"\[[^]]+\]\((https?://[^)]+)\)", source)
        if not url.startswith(
            "https://github.com/signalrush/tau2-bench/blob/PLACEHOLDER"
        )
    }


def verify_and_render(
    source: Path, pdf: Path, pages_dir: Path, dpi: int
) -> dict[str, object]:
    try:
        import pdfplumber
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "missing PDF verification dependencies; run with `uv run`"
        ) from exc

    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise RuntimeError("missing `pdftoppm`; install Poppler")
    if dpi < 72:
        raise RuntimeError("--dpi must be at least 72")

    markdown_source = source.read_text(encoding="utf-8")
    if re.search(r"{{[A-Z0-9_]+}}", markdown_source):
        raise RuntimeError("report contains unresolved template placeholders")

    reader = PdfReader(pdf)
    actual_links: set[str] = set()
    for page in reader.pages:
        for annotation_ref in page.get("/Annots", []):
            annotation = annotation_ref.get_object()
            action = annotation.get("/A") or {}
            uri = action.get("/URI")
            if uri:
                actual_links.add(str(uri))
    expected_links = expected_external_links(markdown_source)
    missing_links = sorted(expected_links - actual_links)
    if missing_links:
        raise RuntimeError(f"missing PDF link annotations: {missing_links}")

    with pdfplumber.open(pdf) as document:
        extracted = "\n".join((page.extract_text() or "") for page in document.pages)
        page_count = len(document.pages)
    if not extracted.strip():
        raise RuntimeError("PDF has no extractable text")
    if "\ufffd" in extracted:
        raise RuntimeError("PDF text contains a replacement glyph")

    pages_dir.mkdir(parents=True, exist_ok=True)
    for stale in pages_dir.glob("page-*.png"):
        stale.unlink()
    prefix = pages_dir / "page"
    subprocess.run(
        [pdftoppm, "-png", "-r", str(dpi), str(pdf), str(prefix)],
        check=True,
        capture_output=True,
        text=True,
    )
    rendered = sorted(pages_dir.glob("page-*.png"))
    if len(rendered) != page_count or any(
        path.stat().st_size == 0 for path in rendered
    ):
        raise RuntimeError(
            f"rendered {len(rendered)} nonempty page images for {page_count} PDF pages"
        )
    return {
        "pdf": str(pdf),
        "pdf_sha256": file_sha256(pdf),
        "source": str(source),
        "source_sha256": file_sha256(source),
        "renderer_sha256": file_sha256(Path(__file__)),
        "page_count": page_count,
        "pages_dir": str(pages_dir),
        "expected_external_link_count": len(expected_links),
        "verified_external_link_count": len(expected_links & actual_links),
    }


def main() -> int:
    args = parse_args()
    if not args.source.is_file():
        print(f"source not found: {args.source}", file=sys.stderr)
        return 2
    if args.css and not args.css.is_file():
        print(f"CSS not found: {args.css}", file=sys.stderr)
        return 2

    extra_css = args.css.read_text(encoding="utf-8") if args.css else ""
    try:
        document = build_html(args.source, args.brand, args.label, extra_css)
        configure_native_paths()
        from weasyprint import HTML
    except (ImportError, OSError, RuntimeError) as exc:
        print(f"cannot load PDF dependencies: {exc}", file=sys.stderr)
        print(
            "Use `uv run create_pdf.py ...`; WeasyPrint also needs Pango.",
            file=sys.stderr,
        )
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(document, encoding="utf-8")
    HTML(string=document, base_url=str(args.source.resolve().parent)).write_pdf(
        args.output
    )
    pages_dir = args.pages_dir or args.output.parent / f"{args.output.stem}-pages"
    try:
        receipt = verify_and_render(args.source, args.output, pages_dir, args.dpi)
    except RuntimeError as exc:
        print(f"PDF verification failed: {exc}", file=sys.stderr)
        return 1
    receipt_path = args.output.with_suffix(".receipt.json")
    receipt["receipt"] = str(receipt_path)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
