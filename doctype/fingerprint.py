"""Reduce an HTML document to the structural counts the classifier reads.

The fingerprint is deliberately small and cheap: 15 integers plus the heading text,
the title, the slug, the category and the tags. It is the only place in this package that parses HTML, and it is
kept separate from the rules so you can fingerprint once, cache the result, and
re-run the rules a hundred times while tuning them. That loop is the reason the
rules converged at all.

Everything here goes through BeautifulSoup. Do not be tempted to regex HTML for
these counts -- a nested table or an attribute containing a ``>`` will silently
skew a count, and a skewed count produces a confidently wrong classification with
no error to notice.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from bs4 import BeautifulSoup

#: How many headings to keep. The rules only ever substring-match the joined text,
#: and documents with hundreds of headings are index pages whose first twenty are
#: already conclusive.
MAX_HEADINGS = 20

_HEADING_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6"]


def soup(html: str) -> BeautifulSoup:
    """Parse with the stdlib parser, so the package needs no lxml build."""
    return BeautifulSoup(html or "", "html.parser")


def text_only(html: str) -> str:
    return soup(html).get_text(" ", strip=True)


def _is_field_table(table) -> bool:
    """A field/value table: first cell of the first row is bold.

    This is a convention, not a standard, and it is the single most
    corpus-specific thing in this module. It is what distinguishes a
    Field | Description reference table from a layout table or a role matrix. If
    your authoring tool marks these differently, this is the function to replace.
    """
    first_row = table.find("tr")
    if not first_row:
        return False
    first_cell = first_row.find(["td", "th"])
    return bool(first_cell and first_cell.find(["strong", "b"]))


def fingerprint(
    html: str,
    *,
    title: str = "",
    slug: str = "",
    top: str = "",
    tags: Optional[Sequence[str]] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Fingerprint one document.

    Args:
        html: the document body.
        title: human title. Several rules key on it, so a missing title measurably
            costs accuracy -- it is optional only so that a body-only call works.
        slug: URL slug or filename. Used to spot import artifacts.
        top: top-level category or folder name.
        tags: CMS tags. Matched as exact, lowercased values.
        extra: merged into the result. Use it to carry ids or anything else you
            want to travel with the fingerprint.

    Returns:
        A plain dict, JSON-serializable, ready for ``classify``.
    """
    s = soup(html)
    headings = s.find_all(_HEADING_TAGS)
    tables = s.find_all("table")

    fp: Dict[str, Any] = {
        "title": title,
        "slug": slug,
        "top": top,
        "tags": [str(t).lower() for t in (tags or [])],
        "chars": len(s.get_text(" ", strip=True)),
        "h": len(headings),
        "h2": len(s.find_all("h2")),
        "h3": len(s.find_all("h3")),
        "h4": len(s.find_all("h4")),
        "tables": len(tables),
        "fieldish_tables": sum(1 for t in tables if _is_field_table(t)),
        "ol": len(s.find_all("ol")),
        "ul": len(s.find_all("ul")),
        "li": len(s.find_all("li")),
        "img": len(s.find_all("img")),
        "pre": len(s.find_all(["pre", "code"])),
        "strong": len(s.find_all("strong")),
        "links": len(s.find_all("a", href=True)),
        "p": len(s.find_all("p")),
        "heading_txt": [h.get_text(" ", strip=True) for h in headings[:MAX_HEADINGS]],
    }
    if extra:
        fp.update(extra)
    return fp


def fingerprint_many(docs: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Fingerprint a sequence of ``{html, title, slug, top, tags, ...}`` mappings.

    A document that fails to parse yields ``{"error": ...}`` plus its identifying
    fields rather than raising, so one bad document cannot abort a corpus sweep.
    Check for ``error`` before classifying -- an errored fingerprint has no counts,
    and every count would read as zero, which classifies as a stub.
    """
    known = {"html", "title", "slug", "top", "tags"}
    out: List[Dict[str, Any]] = []
    for doc in docs:
        ident = {k: doc.get(k, "") for k in ("title", "slug", "top")}
        try:
            fp = fingerprint(
                doc.get("html") or "",
                title=doc.get("title", ""),
                slug=doc.get("slug", ""),
                top=doc.get("top", ""),
                tags=doc.get("tags") or [],
                extra={k: v for k, v in doc.items() if k not in known},
            )
        except Exception as exc:  # noqa: BLE001 - one bad doc must not stop the sweep
            fp = {"error": f"{type(exc).__name__}: {exc}", **ident}
        out.append(fp)
    return out
