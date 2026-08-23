"""Rule behavior tests.

These are hand-built fingerprints, not documents from a corpus. They assert what
each *rule* does, which is the thing you break when you edit one. They are not a
substitute for an accuracy measurement -- an accuracy number needs a labeled
corpus, and that has to be your own (see the README).

Every case here is minimal on purpose: exactly the signals needed to reach one
rule, so a failure names the rule rather than the document.
"""

import pytest

from doctype import DEFAULT_PROFILE, TYPES, classify
from doctype.taxonomy import Profile


def fp(**kw):
    """A neutral fingerprint that classifies as prose, plus whatever you override."""
    base = dict(title="Widget Handling", slug="widget-handling", top="", tags=[],
                chars=800, h=0, h2=0, h3=0, h4=0, tables=0, fieldish_tables=0,
                ol=0, ul=0, li=0, img=0, pre=0, strong=0, links=0, p=4,
                heading_txt=[])
    base.update(kw)
    return base


def code(**kw):
    return classify(fp(**kw))[0]


# --------------------------------------------------------------------- one per type
CASES = [
    ("STUB", dict(chars=12)),
    ("T1", dict(title="Overview of Widgets")),
    ("T2", dict(ol=1)),
    ("T3", dict(tables=1, fieldish_tables=1)),
    ("T4", dict(heading_txt=["Configuration Steps"], h2=1)),
    ("T5", dict(top="Release Notes", heading_txt=["What's New"], h2=1)),
    ("T6", dict(top="Release Notes", tables=1, heading_txt=["Attribute"])),
    ("T7", dict(top="Release Notes", title="4.2 Release Notes")),
    ("T8", dict(title="Member Lookup API", tables=1,
                heading_txt=["Authentication", "Endpoint"], h2=2)),
    ("T9", dict(title="Sample Payload", chars=4000, pre=0)),
    ("T10", dict(tags=["faq"])),
    ("T11", dict(chars=20000, h2=5)),
    ("T12", dict(tags=["imported"])),
]


@pytest.mark.parametrize("expected,overrides", CASES, ids=[c[0] for c in CASES])
def test_one_case_per_type(expected, overrides):
    got, why = classify(fp(**overrides))
    assert got == expected, f"got {got} ({why})"


def test_every_type_is_reachable():
    """A type in TYPES that no case produces is either dead or untested."""
    covered = {expected for expected, _ in CASES}
    assert covered == set(TYPES), f"untested types: {sorted(set(TYPES) - covered)}"


# ------------------------------------------------------------------- non-content
def test_uuid_slug_is_an_import_artifact():
    assert code(slug="epic-config-3f2b91ac-4d1e-11ee") == "T12"


def test_table_of_contents_heading_means_raw_import():
    assert code(heading_txt=["Table of Contents", "Learning Objectives"], h2=2) == "T12"


def test_engineering_dump_by_slug():
    assert code(slug="ticket-4308-implementation-plan") == "T12"


def test_runbook_title():
    assert code(title="Runbook: Queue Backlog") == "T12"


def test_internal_category():
    assert code(top="Product Definitions") == "T12"


def test_prd_needs_both_heading_groups():
    """Either group alone is ordinary documentation; together they are a spec import."""
    assert code(heading_txt=["Purpose"], h2=1) != "T12"
    assert code(heading_txt=["Key Features"], h2=1) != "T12"
    assert code(heading_txt=["Purpose", "Key Features"], h2=2) == "T12"


def test_template_in_title_is_not_enough():
    """"Template" is usually a real feature, not a skeleton. Only an empty or
    placeholder-filled one is non-content."""
    assert code(title="Link an Ad Hoc Template", ol=1, chars=2000) == "T2"
    assert code(title="Release Note Template", chars=150) == "T12"


# -------------------------------------------------------------------- precedence
def test_faq_beats_api():
    """An integration FAQ matches the API vocabulary; FAQ must win."""
    assert code(tags=["faq"], title="Interoperability FAQ", tables=1,
                heading_txt=["Authentication", "Endpoint"], h2=2) == "T10"


def test_config_beats_procedural():
    """Config documents contain ordered steps. The system-variable marker is the
    stronger signal, so it has to be tested first."""
    assert code(ol=3, heading_txt=["Configuration Steps"], h2=1) == "T4"


def test_master_beats_procedural():
    assert code(chars=20000, h2=4, ol=2) == "T11"


def test_non_content_beats_everything():
    """An engineering dump with steps in it is still not a how-to."""
    assert code(tags=["imported"], ol=5, heading_txt=["Configuration Steps"]) == "T12"


def test_stub_beats_everything():
    assert code(chars=5, ol=3, tags=["imported"]) == "STUB"


# ------------------------------------------------------------------- key signals
def test_api_needs_structure_not_just_the_word():
    """Gating on the word "api" alone swallowed every integration overview. The
    contract vocabulary must be backed by a table, a code block or a field table."""
    prose = dict(title="How Integration Works", chars=2000,
                 heading_txt=["Authentication"], h2=1)
    assert code(**prose) == "T1"
    assert code(**dict(prose, tables=1)) == "T8"


def test_config_needs_a_marker_not_just_the_category():
    """Gating T4 on the category flooded it with every how-to filed there."""
    assert code(top="Configuration Instructions", chars=2000) == "T1"
    assert code(top="Configuration Instructions", ol=1) == "T4"


def test_two_all_caps_headings_are_system_variables():
    assert code(heading_txt=["CM_ENABLE_FLAG"], h2=1) != "T4"
    assert code(heading_txt=["CM_ENABLE_FLAG", "CM_OTHER_FLAG"], h2=2) == "T4"


def test_action_verb_headings_make_it_procedural():
    """"Add a Rule" / "Delete a Rule" over a field table is a how-to."""
    assert code(tables=1, fieldish_tables=1, heading_txt=["Field Reference"]) == "T3"
    assert code(tables=1, fieldish_tables=1, heading_txt=["Add a Rule"]) == "T2"


def test_thin_but_real_prose_is_a_concept_not_a_stub():
    """Conflating these two produced the most false "broken document" reports."""
    assert code(chars=200) == "T1"
    assert code(chars=40) == "STUB"


def test_unfenced_payload_is_a_code_sample():
    assert code(title="Sample Request Bundle", chars=5000, pre=0) == "T9"
    # Once it is fenced it is a spec, not a raw payload.
    assert code(title="Sample Request Bundle", chars=5000, pre=3,
                tables=1, heading_txt=["Request", "Response"], h2=2) == "T8"


def test_release_note_universe_is_closed():
    """Anything in the release-note category resolves inside that branch."""
    inside = {classify(fp(top="Release Notes", **extra))[0] for extra in (
        dict(title="4.2 Release Notes"),
        dict(heading_txt=["What's New"], h2=1),
        dict(tables=1),
        dict(chars=900),
    )}
    assert inside <= {"T1", "T5", "T6", "T7"}


# ------------------------------------------------------------------- regressions
def test_category_matching_is_case_insensitive():
    """Regression: the profile lowercases its vocabulary on load, but categories
    were compared against the CMS's own casing. That silently killed the entire
    release-note branch -- 41 documents in the reference corpus fell through to
    procedure and reference types, and nothing raised."""
    for spelling in ("Release Notes", "release notes", "RELEASE NOTES"):
        got = classify(fp(top=spelling, heading_txt=["What's New"], h2=1))[0]
        assert got == "T5", f"category {spelling!r} missed the release-note branch"


def test_tags_match_exactly_not_as_substrings():
    """Regression: a tag is a controlled value. Substring-matching it meant a tag
    reading "not-faq" classified the document as an FAQ."""
    assert code(tags=["not-faq"]) != "T10"
    assert code(tags=["faq"]) == "T10"
    assert code(tags=["imported-legacy"]) != "T12"


def test_missing_keys_do_not_raise():
    """A partial fingerprint should classify with fewer signals, not blow up."""
    got, _ = classify({"chars": 900})
    assert got in TYPES
    assert classify({})[0] == "STUB"


def test_reason_is_always_populated():
    """The reason string is the auditability of the whole approach; an empty one
    makes a call unreviewable."""
    for _, overrides in CASES:
        _, why = classify(fp(**overrides))
        assert why and why.strip()


# ---------------------------------------------------------------------- profiles
def test_a_custom_profile_changes_the_answer():
    """The point of the profile: retarget the rules without editing them."""
    doc = fp(top="Versionshinweise", heading_txt=["Was ist neu"], h2=1)
    assert classify(doc)[0] != "T5"

    german = Profile(
        release_note_categories=["Versionshinweise"],
        canonical_rn_headings=["was ist neu"],
    ).normalized()
    assert classify(doc, german)[0] == "T5"


def test_profiles_do_not_share_a_compiled_pattern_cache():
    """Regression: caching compiled patterns in a dict keyed by id() can hand one
    profile's patterns to another after the first is garbage collected."""
    loose = Profile(action_verbs=["frobnicate"]).normalized()
    assert classify(fp(heading_txt=["Frobnicate the Widget"]), loose)[0] == "T2"
    assert classify(fp(heading_txt=["Frobnicate the Widget"]), DEFAULT_PROFILE)[0] != "T2"
    # ...and back again, to catch a cache that was clobbered rather than keyed.
    assert classify(fp(heading_txt=["Frobnicate the Widget"]), loose)[0] == "T2"


def test_thresholds_are_tunable():
    small = Profile(master_min_chars=1000, master_min_sections=2).normalized()
    doc = fp(chars=2000, h2=3)
    assert classify(doc)[0] != "T11"
    assert classify(doc, small)[0] == "T11"
