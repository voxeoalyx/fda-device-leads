#!/usr/bin/env python3
"""Build the GitHub Pages site from weekly Markdown.

Invoked by .github/workflows/pages.yml before the site/ artifact is uploaded.
Reads weekly/YYYY-MM-DD.md and writes:

  site/weekly/index.html
  site/weekly/YYYY-MM-DD.html
  site/sitemap.xml
  site/robots.txt

A push of a new weekly Markdown file republishes that page on the next
Pages deploy. No generated HTML is committed.

Requires Python-Markdown (Markdown==3.10). Set PAGES_BASE_URL to the site
origin plus project path, without a trailing slash. In Actions this is
steps.pages.outputs.base_url from actions/configure-pages.
"""

from __future__ import annotations

import html
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    import markdown
except ImportError:
    sys.exit("Python-Markdown is required: pip install 'Markdown==3.10'")

ROOT = Path(__file__).resolve().parents[1]
WEEKLY_DIR = ROOT / "weekly"
SITE = ROOT / "site"

WEEK_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
RECALL_RANGE = re.compile(
    r"recalls posted (\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2})"
)
TOTAL_ROW = re.compile(r"\|\s*\*\*Total\*\*\s*\|\s*\*\*([0-9][0-9,]*)\*\*")
MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
DEFAULT_BASE_URL = "https://voxeoalyx.github.io/fda-device-leads"
SUMMARY = (
    "New FDA device establishments, 510(k) clearances and recalls — {label}"
)


@dataclass(frozen=True)
class Week:
    end: datetime
    label: str
    title: str
    total: str | None
    html_name: str
    article: str

    @property
    def path(self) -> str:
        return f"/weekly/{self.html_name}"

    @property
    def link_label(self) -> str:
        if self.label.startswith("week of "):
            return "Week of " + self.label.removeprefix("week of ")
        return self.label


def base_url() -> str:
    raw = os.environ.get("PAGES_BASE_URL", "").strip().rstrip("/")
    if raw:
        return raw
    if os.environ.get("GITHUB_ACTIONS") == "true":
        sys.exit("PAGES_BASE_URL is empty; configure-pages did not set base_url.")
    return DEFAULT_BASE_URL


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def absolute(origin: str, path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return origin + path


def format_span(start: datetime, end: datetime) -> str:
    start_month = MONTHS[start.month - 1]
    end_month = MONTHS[end.month - 1]
    if start.year == end.year and start.month == end.month:
        return f"{start_month} {start.day}–{end.day}, {end.year}"
    if start.year == end.year:
        return f"{start_month} {start.day}–{end_month} {end.day}, {end.year}"
    return (
        f"{start_month} {start.day}, {start.year}–{end_month} {end.day}, {end.year}"
    )


def week_label(text: str, end: datetime) -> str:
    match = RECALL_RANGE.search(text)
    if not match:
        month = MONTHS[end.month - 1]
        return f"week ending {month} {end.day}, {end.year}"
    start = datetime.strptime(match.group(1), "%Y-%m-%d")
    stop = datetime.strptime(match.group(2), "%Y-%m-%d")
    return "week of " + format_span(start, stop)


def load_weeks() -> list[Week]:
    weeks: list[Week] = []
    if not WEEKLY_DIR.is_dir():
        return weeks
    for path in WEEKLY_DIR.iterdir():
        match = WEEK_FILE.match(path.name)
        if not match:
            continue
        end = datetime.strptime(match.group(1), "%Y-%m-%d")
        text = path.read_text(encoding="utf-8")
        label = week_label(text, end)
        total_match = TOTAL_ROW.search(text)
        article = markdown.markdown(
            text, extensions=["tables"], output_format="html"
        )
        weeks.append(
            Week(
                end=end,
                label=label,
                title=SUMMARY.format(label=label),
                total=total_match.group(1) if total_match else None,
                html_name=f"{match.group(1)}.html",
                article=article,
            )
        )
    weeks.sort(key=lambda week: week.end, reverse=True)
    return weeks


def page(
    *,
    title: str,
    description: str,
    canonical: str,
    body: str,
    archive_href: str | None,
) -> str:
    archive = ""
    if archive_href:
        archive = f' · <a href="{esc(archive_href)}">Weekly archive</a>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
<link rel="stylesheet" href="../style.css">
</head>
<body>
<header><div class="wrap">
<h1>FDA Device Leads Weekly</h1>
<p class="lede">{esc(description)}</p>
<a class="btn ghost" href="../">Back to home</a>
</div></header>
<main>
{body}
</main>
<footer><div class="wrap">FDA Device Leads Weekly · Source: openFDA · <a href="../">Home</a>{archive} · <a href="https://ko-fi.com/fdadeviceleads">ko-fi.com/fdadeviceleads</a> · No trackers or cookies on this page.</div></footer>
</body>
</html>
"""


def week_page(origin: str, week: Week) -> str:
    canonical = absolute(origin, week.path)
    body = f'<section><div class="wrap prose">\n{week.article}\n</div></section>'
    return page(
        title=week.title,
        description=week.title,
        canonical=canonical,
        body=body,
        archive_href="./",
    )


def index_page(origin: str, weeks: list[Week]) -> str:
    title = (
        "Weekly FDA device summaries: new establishments, "
        "510(k) clearances and recalls"
    )
    description = (
        "Archive of weekly summaries of new FDA device establishments, "
        "510(k) clearances and recalls, compiled from public openFDA data."
    )
    items: list[str] = []
    for week in weeks:
        detail = f"{week.total} rows" if week.total is not None else "Weekly summary"
        items.append(
            f'<li><a href="{esc(week.html_name)}">{esc(week.link_label)}'
            f"<span>{esc(detail)}</span></a></li>"
        )
    listing = "\n".join(items) if items else "<li>No weekly summaries yet.</li>"
    body = f"""<section><div class="wrap">
<h2>Weekly summaries</h2>
<ul class="archive">
{listing}
</ul>
</div></section>"""
    return page(
        title=title,
        description=description,
        canonical=absolute(origin, "/weekly/"),
        body=body,
        archive_href=None,
    )


def sitemap(origin: str, weeks: list[Week]) -> str:
    urls: list[tuple[str, str | None]] = [
        (absolute(origin, "/"), weeks[0].end.date().isoformat() if weeks else None),
        (
            absolute(origin, "/weekly/"),
            weeks[0].end.date().isoformat() if weeks else None,
        ),
    ]
    for week in weeks:
        urls.append((absolute(origin, week.path), week.end.date().isoformat()))
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, lastmod in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{esc(loc)}</loc>")
        if lastmod:
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def robots(origin: str) -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {absolute(origin, '/sitemap.xml')}\n"
    )


def require(path: Path, text: str, needles: tuple[str, ...]) -> None:
    missing = [needle for needle in needles if needle not in text]
    if missing:
        joined = ", ".join(missing)
        sys.exit(f"{path} is missing required content: {joined}")


def main() -> None:
    origin = base_url()
    if not (SITE / "style.css").is_file():
        sys.exit(f"Missing stylesheet: {SITE / 'style.css'}")
    weeks = load_weeks()
    out_dir = SITE / "weekly"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    index = index_page(origin, weeks)
    index_path = out_dir / "index.html"
    index_path.write_text(index, encoding="utf-8")
    require(
        index_path,
        index,
        (
            "<title>",
            'name="description"',
            'rel="canonical"',
            'href="../"',
            "Back to home",
        ),
    )

    for week in weeks:
        text = week_page(origin, week)
        path = out_dir / week.html_name
        path.write_text(text, encoding="utf-8")
        require(
            path,
            text,
            (
                f"<title>{esc(week.title)}</title>",
                f'content="{esc(week.title)}"',
                f'href="{esc(absolute(origin, week.path))}"',
                'href="../"',
                'href="./"',
            ),
        )

    sitemap_path = SITE / "sitemap.xml"
    robots_path = SITE / "robots.txt"
    sitemap_text = sitemap(origin, weeks)
    robots_text = robots(origin)
    sitemap_path.write_text(sitemap_text, encoding="utf-8")
    robots_path.write_text(robots_text, encoding="utf-8")
    require(sitemap_path, sitemap_text, (absolute(origin, "/"), absolute(origin, "/weekly/")))
    for week in weeks:
        require(sitemap_path, sitemap_text, (absolute(origin, week.path),))
    require(robots_path, robots_text, (f"Sitemap: {absolute(origin, '/sitemap.xml')}",))
    print(f"base url: {origin}")
    print(f"wrote {len(weeks)} weekly page(s), sitemap.xml, and robots.txt")


if __name__ == "__main__":
    main()
