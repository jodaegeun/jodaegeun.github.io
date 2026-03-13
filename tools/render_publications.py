#!/usr/bin/env python3

from __future__ import annotations

import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PEER_REVIEWED_BIB = ROOT / "references" / "peer_reviewed.bib"
PREPRINTS_BIB = ROOT / "references" / "preprints.bib"
OUTPUT_QMD = ROOT / "publications" / "_publications-content.qmd"
SELECTED_OUTPUT_QMD = ROOT / "_selected-publications.qmd"


def load_entries(text: str) -> list[str]:
    cleaned = re.sub(r"^---\s*$", "", text, flags=re.MULTILINE)
    starts = list(re.finditer(r"@[A-Za-z]+\s*\{", cleaned))
    blocks: list[str] = []
    for idx, match in enumerate(starts):
        end = starts[idx + 1].start() if idx + 1 < len(starts) else len(cleaned)
        blocks.append(cleaned[match.start():end].strip())
    return blocks


def parse_braced_value(text: str, start: int) -> tuple[str, int]:
    depth = 0
    chars: list[str] = []
    idx = start + 1
    while idx < len(text):
        char = text[idx]
        if char == "{":
            depth += 1
            chars.append(char)
        elif char == "}":
            if depth == 0:
                return "".join(chars), idx + 1
            depth -= 1
            chars.append(char)
        else:
            chars.append(char)
        idx += 1
    return "".join(chars), idx


def parse_entry(block: str) -> dict[str, str]:
    body_start = block.find("{") + 1
    key_end = block.find(",", body_start)
    fields: dict[str, str] = {"id": block[body_start:key_end].strip()}
    idx = key_end + 1

    while idx < len(block):
        while idx < len(block) and block[idx] in " \t\r\n,}":
            idx += 1
        if idx >= len(block):
            break

        match = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=", block[idx:])
        if not match:
            idx += 1
            continue

        field = match.group(1).lower()
        idx += match.end()
        while idx < len(block) and block[idx].isspace():
            idx += 1

        if idx >= len(block):
            break

        if block[idx] == "{":
            value, idx = parse_braced_value(block, idx)
        elif block[idx] == '"':
            end = idx + 1
            while end < len(block) and block[end] != '"':
                end += 1
            value = block[idx + 1:end]
            idx = end + 1
        else:
            end = idx
            while end < len(block) and block[end] not in ",\n":
                end += 1
            value = block[idx:end]
            idx = end

        fields[field] = value.strip()

    return fields


def latex_to_unicode(text: str) -> str:
    replacements = {
        r"\"a": "ä",
        r"\"A": "Ä",
        r"\"o": "ö",
        r"\"O": "Ö",
        r"\"u": "ü",
        r"\"U": "Ü",
        r"\'a": "á",
        r"\'e": "é",
        r"\'i": "í",
        r"\'o": "ó",
        r"\'u": "ú",
        r"\&": "&",
        r"\-": "-",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"\\underline\{\\textbf\{([^{}]+)\}\}", r"\1", text)
    text = re.sub(r"\\textbf\{([^{}]+)\}", r"\1", text)
    text = re.sub(r"\\underline\{([^{}]+)\}", r"\1", text)
    text = text.replace("{", "").replace("}", "")
    return text


def normalize_text(text: str) -> str:
    normalized = latex_to_unicode(text)
    normalized = normalized.replace("$", "")
    normalized = normalized.replace("--", "-")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def format_author(author: str) -> str:
    dagger = "†" in author
    cleaned = author.replace("<sup>†</sup>", "")
    cleaned = cleaned.replace("<em>", "").replace("</em>", "")
    cleaned = normalize_text(cleaned)

    if "," in cleaned:
        last, first = [part.strip() for part in cleaned.split(",", 1)]
        cleaned = f"{first} {last}".strip()

    if cleaned in {"Daegeun Jo", "D. Jo"}:
        cleaned = f"<strong>{html.escape(cleaned)}</strong>"
    else:
        cleaned = html.escape(cleaned)

    if dagger:
        cleaned = f"{cleaned}<sup>†</sup>"

    return cleaned


def join_authors(authors: list[str]) -> str:
    if not authors:
        return ""
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return f"{authors[0]} and {authors[1]}"
    return ", ".join(authors[:-1]) + f", and {authors[-1]}"


def author_line(raw_authors: str) -> str:
    authors = [format_author(author.strip()) for author in raw_authors.split(" and ") if author.strip()]
    return join_authors(authors)


def extract_year(fields: dict[str, str]) -> str:
    year = fields.get("year", "").strip()
    if year:
        return normalize_text(year)
    date = fields.get("date", "")
    match = re.search(r"(\d{4})", date)
    return match.group(1) if match else ""


def make_preprint_url(fields: dict[str, str]) -> str:
    eprint = fields.get("eprint", "").strip()
    archive = normalize_text(fields.get("archiveprefix", "") or fields.get("eprinttype", "")).lower()
    if eprint and archive == "arxiv":
        return f"https://arxiv.org/abs/{eprint}"
    return ""


def make_link(fields: dict[str, str]) -> str:
    doi = fields.get("doi", "").strip()
    url = fields.get("url", "").strip()
    if doi:
        doi_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
        return html.escape(doi_url)
    if url:
        return html.escape(url)
    preprint_url = make_preprint_url(fields)
    if preprint_url:
        return html.escape(preprint_url)
    return ""


def normalize_doi(value: str) -> str:
    doi = value.strip()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    return doi.strip()


def metric_badges(fields: dict[str, str]) -> str:
    doi = normalize_doi(fields.get("doi", ""))
    if not doi:
        return ""

    safe_doi = html.escape(doi)
    return "\n".join(
        [
            '<span class="publication-metrics">',
            f'  <span class="__dimensions_badge_embed__" data-doi="{safe_doi}" data-hide-zero-citations="true" data-style="small_rectangle" data-legend="hover-right"></span>',
            f'  <span class="altmetric-embed" data-badge-type="2" data-badge-popover="right" data-hide-no-mentions="true" data-doi="{safe_doi}"></span>',
            "</span>",
        ]
    )


def preprint_venue(fields: dict[str, str]) -> str:
    eprint = html.escape(normalize_text(fields.get("eprint", "")))
    archive = normalize_text(fields.get("archiveprefix", "") or fields.get("eprinttype", "")).lower()
    year = html.escape(extract_year(fields))

    if archive == "arxiv" and eprint:
        venue = f"<em>arXiv</em>: {eprint}"
        if year:
            venue = f"{venue} ({year})"
        return venue

    return ""


def venue_line(fields: dict[str, str]) -> str:
    journal_source = fields.get("journal", "") or fields.get("note", "")
    journal = html.escape(normalize_text(journal_source))
    volume = html.escape(normalize_text(fields.get("volume", "")))
    pages = html.escape(normalize_text(fields.get("pages", "")))
    year = html.escape(extract_year(fields))

    venue = f"<em>{journal}</em>" if journal else preprint_venue(fields)

    if volume:
        venue = f"{venue} <strong>{volume}</strong>" if venue else f"<strong>{volume}</strong>"
    if pages:
        venue = f"{venue}, {pages}" if venue else pages
    if year and not venue.endswith(f"({year})"):
        venue = f"{venue} ({year})" if venue else f"({year})"

    link = make_link(fields)
    if link:
        venue = f'<a href="{link}">{venue}</a>'

    return venue


def format_entry(fields: dict[str, str]) -> str:
    title = html.escape(normalize_text(fields.get("title", "")))
    authors = author_line(fields.get("author", ""))
    venue = venue_line(fields)
    badges = metric_badges(fields)

    return "\n".join(
        [
            '<div class="publication-entry">',
            f'  <div class="publication-authors">{authors}</div>',
            f'  <div class="publication-title">{title}</div>',
            f'  <div class="publication-venue">{venue}{badges}</div>',
            "</div>",
        ]
    )


def selected_entries(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    return [entry for entry in entries if normalize_text(entry.get("selected", "")).lower() == "true"]


def build_page(entries: dict[str, list[dict[str, str]]]) -> str:
    publications = entries["publications"]
    preprints = entries["preprints"]

    publication_html = "\n\n".join(format_entry(entry) for entry in publications)
    preprint_html = "\n\n".join(format_entry(entry) for entry in preprints)

    return f"""<p class="publication-note">† indicates equal contribution.</p>

## Preprints

<details class="publication-fold">
<summary class="publication-fold-summary">Show preprints</summary>
<div class="publication-fold-body">
<div class="publication-list">
{preprint_html}
</div>
</div>
</details>

## Peer-Reviewed Articles

<div class="publication-list">
{publication_html}
</div>

<script async src="https://d1bxh8uas1mnw7.cloudfront.net/assets/embed.js"></script>
<script async src="https://badge.dimensions.ai/badge.js"></script>

<script>
document.addEventListener("DOMContentLoaded", () => {{
  const fold = document.querySelector(".publication-fold");
  if (!fold) return;

  const summary = fold.querySelector(".publication-fold-summary");
  const body = fold.querySelector(".publication-fold-body");
  if (!summary || !body) return;

  let isAnimating = false;

  const finishOpen = () => {{
    body.style.height = "auto";
    body.style.overflow = "visible";
    body.style.transition = "";
    body.style.opacity = "1";
    body.style.transform = "translateY(0)";
    isAnimating = false;
  }};

  const finishClose = () => {{
    fold.open = false;
    body.style.height = "";
    body.style.overflow = "";
    body.style.transition = "";
    body.style.opacity = "";
    body.style.transform = "";
    isAnimating = false;
  }};

  summary.addEventListener("click", (event) => {{
    event.preventDefault();
    if (isAnimating) return;

    const isOpen = fold.open;
    isAnimating = true;
    body.style.overflow = "hidden";

    if (!isOpen) {{
      fold.open = true;
      body.style.height = "0px";
      body.style.opacity = "0";
      body.style.transform = "translateY(-6px)";
      const endHeight = body.scrollHeight;

      requestAnimationFrame(() => {{
        body.style.transition = "height 360ms cubic-bezier(0.22, 1, 0.36, 1), opacity 280ms ease, transform 360ms cubic-bezier(0.22, 1, 0.36, 1)";
        body.style.height = `${{endHeight}}px`;
        body.style.opacity = "1";
        body.style.transform = "translateY(0)";
      }});

      body.addEventListener("transitionend", finishOpen, {{ once: true }});
      return;
    }}

    body.style.height = `${{body.offsetHeight}}px`;
    body.style.opacity = "1";
    body.style.transform = "translateY(0)";

    requestAnimationFrame(() => {{
      body.style.transition = "height 280ms cubic-bezier(0.4, 0, 0.2, 1), opacity 180ms ease, transform 280ms cubic-bezier(0.4, 0, 0.2, 1)";
      body.style.height = "0px";
      body.style.opacity = "0";
      body.style.transform = "translateY(-4px)";
    }});

    body.addEventListener("transitionend", finishClose, {{ once: true }});
  }});
}});
</script>
"""


def build_selected(entries: dict[str, list[dict[str, str]]]) -> str:
    selected_html = "\n\n".join(format_entry(entry) for entry in selected_entries(entries["publications"]))
    return f"""<div class="publication-list">
{selected_html}
</div>

<script async src="https://d1bxh8uas1mnw7.cloudfront.net/assets/embed.js"></script>
<script async src="https://badge.dimensions.ai/badge.js"></script>
"""


def main() -> None:
    peer_reviewed = [parse_entry(block) for block in load_entries(PEER_REVIEWED_BIB.read_text())]
    preprints = [parse_entry(block) for block in load_entries(PREPRINTS_BIB.read_text())]
    entries = {"publications": peer_reviewed, "preprints": preprints}
    OUTPUT_QMD.write_text(build_page(entries))
    SELECTED_OUTPUT_QMD.write_text(build_selected(entries))


if __name__ == "__main__":
    main()
