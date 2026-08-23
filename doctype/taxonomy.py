"""The type system and the tunable vocabulary that the rules key on.

Two things live here, and the split is the whole point of this module:

* ``TYPES`` -- the type system. Stable. Changing it means changing what the
  classifier is *for*.
* ``Profile`` -- the vocabulary. Every literal string and threshold the rules
  match against, in one place, loadable from JSON. This is what you edit to
  point the classifier at *your* knowledge base instead of mine.

The rules in ``classify.py`` contain no bare strings for this reason. When they
were written they had a dozen literals baked in -- a category named "Release
Notes", a tag named ``imported``, a heading phrase "Configuration Steps". Those
are facts about one knowledge base, not facts about documentation, and leaving
them inline made the classifier unusable anywhere else.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Mapping, Sequence

TYPES: Dict[str, str] = {
    "T1": "Overview / Concept",
    "T2": "Task / Procedure",
    "T3": "Field / Screen Reference",
    "T4": "Config Instruction",
    "T5": "Release Note (canonical)",
    "T6": "Release Note (legacy)",
    "T7": "Index / Landing / Rollup",
    "T8": "API Spec",
    "T9": "Code Sample / Payload",
    "T10": "FAQ",
    "T11": "Long-form Master Guide",
    "T12": "Internal / Non-content",
    "STUB": "Stub / empty",
}


def _lower(seq: Sequence[str]) -> List[str]:
    return [s.lower() for s in seq]


@dataclass
class Profile:
    """Vocabulary and thresholds for one knowledge base.

    Every field is a plain list, string or number so the whole thing round-trips
    through JSON. Phrase lists are matched as case-insensitive substrings against
    the joined heading text, so "system variable" also matches a heading reading
    "System Variable Configuration".
    """

    name: str = "default"

    # --- category and tag names, as they appear in your CMS -------------------
    release_note_categories: List[str] = field(default_factory=lambda: ["Release Notes"])
    config_categories: List[str] = field(default_factory=lambda: ["Configuration Instructions"])
    internal_categories: List[str] = field(default_factory=lambda: ["Product Definitions"])
    release_note_tags: List[str] = field(default_factory=lambda: ["release-notes"])
    imported_tags: List[str] = field(default_factory=lambda: ["imported"])
    internal_tags: List[str] = field(default_factory=lambda: ["product-definitions"])
    faq_tags: List[str] = field(default_factory=lambda: ["faq"])
    overview_tags: List[str] = field(default_factory=lambda: ["overview", "getting-started", "onboarding"])

    # --- title vocabulary ----------------------------------------------------
    crud_verbs: List[str] = field(default_factory=lambda: [
        "create", "add", "edit", "delete", "update", "remove", "manage", "configure",
        "clone", "split", "upload", "assign", "convert", "generate", "go to", "access",
    ])
    overview_words: List[str] = field(default_factory=lambda: [
        "overview", "introduction", "about", "what is", "what are", "getting started",
    ])
    # "claims" is here because in the corpus this was tuned against, a claims grid
    # is a screen. It is the clearest example of a word you should replace with
    # your own domain's noun for "a table users look at".
    screen_words: List[str] = field(default_factory=lambda: [
        "tab", "window", "screen", "fields", "buttons", "claims",
    ])
    # screen_words plus anything else that implies a UI surface, used only by the
    # weaker late-stage screen-reference rule.
    screen_words_loose: List[str] = field(default_factory=lambda: [
        "tab", "window", "screen", "fields", "level",
    ])

    # --- heading phrase markers ----------------------------------------------
    canonical_rn_headings: List[str] = field(default_factory=lambda: [
        "what's new", "whats new", "why it matters", "who is impacted", "enabled by default",
    ])
    config_step_headings: List[str] = field(default_factory=lambda: [
        "configuration steps", "system variable", "configuration sql",
    ])
    # A metadata table at the top of a config document. These are the row labels
    # that get promoted to headings by most HTML importers.
    metadata_headings: List[str] = field(default_factory=lambda: [
        "jira epic", "document type", "solution area", "related release note",
    ])
    api_headings: List[str] = field(default_factory=lambda: [
        "authentication", "endpoint", "request", "response", "data schema",
        "error handling", "api endpoints", "api details", " api", "cds hooks",
    ])
    # A config document whose headings read "Managing X" / "Creating Y" *and*
    # mention configuration, with ordered steps. Both halves are required: either
    # one alone is just a procedure.
    config_context_word: str = "configuration"
    config_context_headings: List[str] = field(default_factory=lambda: [
        "managing", "creating", "navigation",
    ])
    faq_headings: List[str] = field(default_factory=lambda: ["faqs"])
    faq_title_words: List[str] = field(default_factory=lambda: ["faq", "setup and faq"])
    index_title_words: List[str] = field(default_factory=lambda: [
        "resolved issues", "patch notes", "service pack",
    ])
    screenref_headings: List[str] = field(default_factory=lambda: [
        "right click", "column options", "table options", "window",
    ])
    action_verbs: List[str] = field(default_factory=lambda: [
        "add", "create", "edit", "delete", "complete", "configure", "assign",
        "split", "link", "upload", "convert", "generate",
    ])

    # --- internal / non-content markers --------------------------------------
    raw_import_headings: List[str] = field(default_factory=lambda: [
        "learning objectives", "table of contents", "contact us",
    ])
    raw_import_heading_prefixes: List[str] = field(default_factory=lambda: ["sheet:"])
    engineering_headings: List[str] = field(default_factory=lambda: [
        "ticket summary", "architecture summary", "design decisions", "hibernate",
        "junit", "flyway", "terraform", "implementation plan",
    ])
    engineering_slug_markers: List[str] = field(default_factory=lambda: [
        "implementation-plan", "implementation-summary", "test-results",
    ])
    engineering_title_markers: List[str] = field(default_factory=lambda: ["test-results"])
    runbook_title_prefixes: List[str] = field(default_factory=lambda: ["runbook"])
    runbook_headings: List[str] = field(default_factory=lambda: ["trigger:", "escalation"])
    prd_headings_a: List[str] = field(default_factory=lambda: [
        "success metrics", "assumptions", "purpose",
    ])
    prd_headings_b: List[str] = field(default_factory=lambda: [
        "key features", "requirements", "deployment activities",
    ])
    bundle_headings: List[str] = field(default_factory=lambda: [
        "why bundle", "starter bundle", "included apis",
    ])
    template_headings: List[str] = field(default_factory=lambda: [
        "provide a brief", "placeholder",
    ])
    code_sample_headings: List[str] = field(default_factory=lambda: [
        "sample request", "data models", "payload", "bundle",
    ])
    code_sample_title_prefixes: List[str] = field(default_factory=lambda: ["sample"])

    # --- thresholds ----------------------------------------------------------
    # Deliberately low. A near-empty page is a stub; a *thin but real* page is a
    # concept article, and conflating the two was the single biggest source of
    # false "broken article" reports in the corpus this was built against.
    stub_max_chars: int = 60
    template_max_chars: int = 300
    thin_prose_max_chars: int = 250
    master_min_chars: int = 15000
    code_sample_min_chars: int = 3000
    index_min_links: int = 15
    master_min_tables: int = 4
    master_min_sections: int = 3
    master_min_field_tables: int = 4
    caps_heading_min_count: int = 2
    caps_heading_min_len: int = 5

    # --- patterns -------------------------------------------------------------
    # Regex, as strings so they survive a JSON round-trip. Replace these with your
    # own version-numbering and slug conventions.
    version_title_pattern: str = r"^\d+\.\d+(\.\d+)*\b.*release notes?$|service pack"
    bare_version_pattern: str = r"^\d+\.\d+\.\d+"
    uuid_slug_pattern: str = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}"

    # ------------------------------------------------------------------ loaders
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Profile":
        known = {f.name for f in fields(cls)}
        unknown = sorted(set(data) - known)
        if unknown:
            # Silently ignoring a typo'd key means a rule quietly stops firing and
            # the accuracy drop looks like a corpus change. Fail instead.
            raise ValueError(f"unknown profile key(s): {', '.join(unknown)}")
        return cls(**dict(data))

    @classmethod
    def load(cls, path) -> "Profile":
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def to_dict(self) -> Dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def normalized(self) -> "Profile":
        """Lowercase every vocabulary list once, so the hot path can skip it."""
        data = self.to_dict()
        for key, value in data.items():
            if isinstance(value, list) and value and isinstance(value[0], str):
                data[key] = _lower(value)
        return Profile(**data)


DEFAULT_PROFILE = Profile().normalized()
