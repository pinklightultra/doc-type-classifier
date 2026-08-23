"""Rule-based document-type classifier.

Takes a structural fingerprint of an HTML document -- 15 counts plus the heading
text, the title, the slug, the tags and the category -- and returns one of thirteen
types with the reason it fired. No model, no training, no dependencies beyond
``re``. It runs over thousands of documents in under a second.

## Why rules

The job this was built for is routing: classify a document, then run only the
quality checks that fit its type. Every false positive in the original corpus scan
came from applying one rule to every document -- a short concept page flagged as a
truncated how-to, a role matrix flagged as a malformed field table. Type-aware
checking fixes that, and for routing, a wrong-but-legible answer beats an opaque
one. When the classifier is wrong here you can read the rule that misfired and
edit it. That property is worth more than a few points of accuracy.

## Precedence is the design

The types overlap in reality. A release note *is* also a procedure; a long config
guide *is* also a master guide. There is no clean feature boundary between them,
so the resolution is ordered: the most specific claim wins, and precedence is
encoded as nothing more than the order of the ``if`` statements below. Read the
function top to bottom and you have read the whole spec.

Three orderings are load-bearing and each one cost accuracy to find. The README
lists the same three:

* Internal / non-content is tested **before everything**, because an engineering
  dump that happens to contain ordered steps is not a how-to, it is something that
  should not have been published.
* FAQ is tested **before** API, because a page titled "Setup and FAQs" for an
  integration matches the API vocabulary and gets stolen.
* Config and master-guide are tested **before** procedure, because both routinely
  contain ordered steps, and "has ordered steps" is a much weaker signal than
  "has a system-variable table".

## Accuracy

84.2% (123/146) on a 146-item hand-labelled set. That set was **not** held out:
the rules below were tuned over four rounds against it, scoring the same 146
items each time, so this is training accuracy and an optimistic estimate of what
it would do on documents it has never seen. There is no held-out split. See the
README, "What that number is not", for how it was produced.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Tuple

from .taxonomy import DEFAULT_PROFILE, TYPES, Profile

__all__ = ["classify", "TYPES", "Profile"]


def _joined(headings) -> str:
    return " || ".join(h or "" for h in headings).lower()


def _any_in(haystack: str, needles) -> bool:
    return any(n in haystack for n in needles)


_RX_ATTR = "_rx_cache"


def _compiled(profile: Profile) -> Dict[str, Any]:
    """Per-profile regex cache. Compiling on every call would dominate the runtime
    when sweeping a whole corpus.

    The cache is stored on the profile instance rather than in a module-level dict
    keyed by ``id()``: ids are reused after garbage collection, so a keyed-by-id
    cache can hand one profile's compiled patterns to a different profile.
    """
    cache = profile.__dict__.get(_RX_ATTR)
    if cache is None:
        verbs = "|".join(re.escape(v) for v in profile.action_verbs)
        cache = {
            "version_title": re.compile(profile.version_title_pattern, re.I),
            "bare_version": re.compile(profile.bare_version_pattern),
            "uuid_slug": re.compile(profile.uuid_slug_pattern, re.I),
            "action_heading": re.compile(rf"^({verbs})\b"),
            "caps_heading": re.compile(rf"^[A-Z][A-Z0-9_]{{{profile.caps_heading_min_len},}}$"),
        }
        profile.__dict__[_RX_ATTR] = cache
    return cache


def classify(fp: Mapping[str, Any], profile: Profile = DEFAULT_PROFILE) -> Tuple[str, str]:
    """Classify one fingerprint.

    Args:
        fp: a fingerprint dict, as produced by ``doctype.fingerprint.fingerprint``.
            Missing keys are treated as zero/empty, so a partial fingerprint still
            classifies -- it just has fewer signals to go on.
        profile: the vocabulary to match against. Defaults to the shipped profile,
            which is tuned to one particular knowledge base; see ``taxonomy.Profile``.

    Returns:
        ``(type_code, reason)``. The reason is a short human-readable string naming
        the rule that fired, meant to be shown to whoever has to audit the call.
    """
    rx = _compiled(profile)

    title = (fp.get("title") or "").strip()
    tl = title.lower()
    slug = (fp.get("slug") or "").lower()
    tags = [str(t).lower() for t in (fp.get("tags") or [])]
    # Lowercased to match the profile, whose vocabulary is normalized on load.
    # Category and tag names come from a CMS and their casing is not dependable.
    top = (fp.get("top") or "").lower()
    chars = fp.get("chars") or 0
    headings = fp.get("heading_txt") or []
    H = _joined(headings)

    ol = fp.get("ol") or 0
    fieldish = fp.get("fieldish_tables") or 0
    tables = fp.get("tables") or 0
    pre = fp.get("pre") or 0
    links = fp.get("links") or 0
    h2 = fp.get("h2") or 0
    h3 = fp.get("h3") or 0

    # ---------------------------------------------------------------- sub-signals
    prose_only = fieldish == 0 and ol == 0 and tables <= 1

    caps_headings = sum(1 for h in headings if rx["caps_heading"].match((h or "").strip()))

    # A system-variable marker: a config-steps heading, or an ALL_CAPS_NAME heading,
    # which is how a system variable or feature flag is titled.
    sv_marker = _any_in(H, profile.config_step_headings) or caps_headings >= 1

    metadata_marker = _any_in(H, profile.metadata_headings)

    # A real endpoint contract, not the word "api" appearing in prose. Requires both
    # the contract vocabulary and some structure to hold the contract in. Without the
    # structural half this rule swallowed every integration overview.
    api_contract = _any_in(H, profile.api_headings) and (
        fieldish >= 1 or pre >= 1 or tables >= 1 or "api" in tl
    )

    # Action-verb section headings mean procedural, even sitting on top of field
    # tables -- "Add a Rule", "Delete a Rule" is a how-to with a field reference in it.
    action_headings = any(rx["action_heading"].match((h or "").strip().lower()) for h in headings)

    # A screen reference can lack a bold-first-column table and still obviously be
    # one, if it has any table plus a screen-ish title or a UI-affordance heading.
    screenref_signal = tables >= 1 and (
        _any_in(H, profile.screenref_headings) or _any_in(tl, profile.screen_words)
    )

    # Tags match exactly; title and headings match as substrings. A tag is a
    # controlled value, so substring-matching it would let "not-faq" fire.
    faqish = (
        bool(set(tags) & set(profile.faq_tags))
        or _any_in(tl, profile.faq_title_words)
        or _any_in(H, profile.faq_headings)
    )

    # 1. Hard empty only. A thin-but-real page is handled at the bottom as a concept
    #    article; calling it a stub is the mistake that generated the most noise.
    if chars < profile.stub_max_chars:
        return "STUB", f"empty ({chars} chars)"

    # 2. Internal / non-content. First because an engineering dump that happens to
    #    contain ordered steps is not a how-to, it is something that should not be
    #    published at all.
    if set(tags) & set(profile.imported_tags):
        return "T12", "imported tag"
    if rx["uuid_slug"].search(slug):
        return "T12", "uuid slug artifact"
    if _any_in(H, profile.raw_import_headings) or _any_in(H, profile.raw_import_heading_prefixes):
        return "T12", "raw word/spreadsheet import structure"
    if (
        _any_in(H, profile.engineering_headings)
        or _any_in(slug, profile.engineering_slug_markers)
        or _any_in(tl, profile.engineering_title_markers)
    ):
        return "T12", "implementation plan / engineering / QA dump"
    if any(tl.startswith(p) for p in profile.runbook_title_prefixes) or _any_in(H, profile.runbook_headings):
        return "T12", "support runbook (internal)"
    if top in profile.internal_categories or set(tags) & set(profile.internal_tags):
        return "T12", "internal product definition"
    if _any_in(H, profile.prd_headings_a) and _any_in(H, profile.prd_headings_b):
        return "T12", "PRD / spec import (internal)"
    if re.search(r"\bbundle\b", tl) and _any_in(H, profile.bundle_headings):
        return "T12", "marketing / licensing prose"
    # A "template" in the title is usually a real feature ("Link an Ad Hoc Template"),
    # not a skeleton. Only an empty or placeholder-filled one is non-content.
    if re.search(r"\btemplate\b", tl) and (
        chars < profile.template_max_chars or _any_in(H, profile.template_headings)
    ):
        return "T12", "template skeleton"

    # 3. Release notes. A closed universe: if the document lives in the release-note
    #    category it is one of exactly four things, so resolve it here and return.
    if set(tags) & set(profile.release_note_tags) or top in profile.release_note_categories:
        if (
            rx["version_title"].search(tl)
            or rx["bare_version"].match(tl)
            or (tables == 0 and links > profile.index_min_links)
            or _any_in(tl, profile.index_title_words)
        ):
            return "T7", "version / rollup landing page"
        if _any_in(H, profile.canonical_rn_headings):
            return "T5", "canonical release-note sections present"
        if prose_only and not (tables >= 1 or fieldish >= 1):
            return "T1", "release-note category but prose overview, no attribute table"
        if tables >= 1 or fieldish >= 1:
            return "T6", "legacy attribute-table release note"
        return "T6", "release-note fallback"

    # 4. FAQ. Must precede the API test: an integration FAQ matches the API
    #    vocabulary and would otherwise be classified as a spec.
    if faqish:
        return "T10", "faq / setup+faq"

    # 5. API and code.
    if api_contract:
        return "T8", "api endpoint contract"
    if pre == 0 and chars > profile.code_sample_min_chars and (
        any(tl.startswith(p) for p in profile.code_sample_title_prefixes)
        or _any_in(H, profile.code_sample_headings)
    ):
        # Body is a payload but nothing is fenced -- a code sample *and* a defect.
        return "T9", "code sample / payload (unfenced)"

    # 6. Config instruction. Gated on a config *marker*, never on the category or
    #    tag alone: ordered steps without a metadata or system-variable table are a
    #    procedure, and gating on the category flooded T4 with every how-to in it.
    if (
        metadata_marker
        or _any_in(H, profile.config_step_headings)
        or caps_headings >= profile.caps_heading_min_count
        or (top in profile.config_categories and (sv_marker or ol >= 1))
        or (profile.config_context_word in H and _any_in(H, profile.config_context_headings) and ol >= 1)
        or (fieldish >= 1 and sv_marker)
    ):
        return "T4", "config instruction (metadata / system-variable / config-steps marker)"

    # 7. Long-form master. Above procedural, because masters usually contain steps.
    #    Size is the signal; structure only distinguishes a master from a wall of text.
    if chars > profile.master_min_chars and (
        tables >= profile.master_min_tables
        or h2 >= profile.master_min_sections
        or h3 >= profile.master_min_sections
        or fieldish >= profile.master_min_field_tables
    ):
        return "T11", f"long-form master ({chars} chars, heavy structure)"

    # 8. Procedural how-to.
    if ol >= 1 or action_headings or any(tl.startswith(w) for w in profile.crud_verbs):
        return "T2", "procedural (ordered steps / action headings / imperative title)"

    # 9. Field and screen reference. Needs a field table or the weaker screen signal.
    if (fieldish >= 1 and ol == 0) or screenref_signal:
        return "T3", "field / screen reference (table, no steps)"
    if prose_only and _any_in(tl, profile.overview_words):
        return "T1", "overview / concept title"
    if _any_in(tl, profile.screen_words_loose) and fieldish >= 1:
        return "T3", "screen-reference title + field table"

    # 10. Overview / concept.
    if _any_in(tl, profile.overview_words) or (tags and set(tags) & set(profile.overview_tags)):
        return "T1", "overview / concept"

    # 11. Fallthroughs. Prose defaults to concept, not to reference: an unstructured
    #     page is far more often a short explanation than a broken table.
    if chars < profile.thin_prose_max_chars and prose_only:
        return "T1", "thin concept (no structure but real prose)"
    if prose_only:
        return "T1", "prose fallthrough -> concept"
    return "T3", "structured fallthrough default"
