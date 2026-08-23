"""Fingerprint extraction tests.

The counts here feed every rule, so a wrong count produces a confidently wrong
classification with nothing logged. These tests exist to make a miscount loud.
"""

from doctype import classify, fingerprint, fingerprint_many, text_only

PROCEDURE = """
<h2>Create a Case</h2>
<p>Use this to open a case.</p>
<ol><li>Click <strong>New</strong>.</li><li>Enter a name.</li><li>Save.</li></ol>
<table><tr><th>Field</th><th>Description</th></tr>
<tr><td><strong>Name</strong></td><td>The case name.</td></tr></table>
"""


def test_counts():
    fp = fingerprint(PROCEDURE, title="Create a Case", slug="create-a-case")
    assert fp["h2"] == 1
    assert fp["ol"] == 1
    assert fp["li"] == 3
    assert fp["tables"] == 1
    assert fp["heading_txt"] == ["Create a Case"]
    assert fp["chars"] > 0


def test_field_table_detection_wants_a_bold_first_cell():
    bold = "<table><tr><td><strong>Name</strong></td><td>x</td></tr></table>"
    plain = "<table><tr><td>Name</td><td>x</td></tr></table>"
    assert fingerprint(bold)["fieldish_tables"] == 1
    assert fingerprint(plain)["fieldish_tables"] == 0


def test_nested_tables_are_counted_individually():
    """The reason this module uses a parser and not a regex: a nested table skews
    the count, and a skewed count changes the classification silently."""
    html = "<table><tr><td><table><tr><td>inner</td></tr></table></td></tr></table>"
    assert fingerprint(html)["tables"] == 2


def test_angle_bracket_in_an_attribute_does_not_break_counting():
    html = '<table title="a > b"><tr><td>x</td></tr></table><table><tr><td>y</td></tr></table>'
    assert fingerprint(html)["tables"] == 2


def test_chars_measures_text_not_markup():
    """A document that is mostly markup is not a long document. Measuring markup
    length would push wrappers over the long-form threshold."""
    html = '<div class="' + "x" * 5000 + '"><p>Short.</p></div>'
    assert fingerprint(html)["chars"] < 20


def test_empty_and_none_are_safe():
    for value in ("", None):
        fp = fingerprint(value)
        assert fp["chars"] == 0
        assert classify(fp)[0] == "STUB"


def test_headings_are_capped_but_the_count_is_not():
    html = "".join(f"<h2>Section {i}</h2>" for i in range(50))
    fp = fingerprint(html)
    assert len(fp["heading_txt"]) == 20
    assert fp["h2"] == 50, "the cap must not truncate the count the rules read"


def test_tags_are_lowercased():
    assert fingerprint("<p>x</p>", tags=["Imported", "FAQ"])["tags"] == ["imported", "faq"]


def test_extra_travels_with_the_fingerprint():
    fp = fingerprint("<p>x</p>", extra={"id": "abc123"})
    assert fp["id"] == "abc123"


def test_text_only_flattens():
    assert text_only("<p>a</p><p>b</p>") == "a b"


def test_fingerprint_many_survives_a_bad_document():
    """One unparseable document must not abort a corpus sweep."""
    docs = [
        {"html": PROCEDURE, "slug": "good", "title": "Create a Case"},
        {"html": 12345, "slug": "bad", "title": "Bad"},  # not a string
        {"html": "<p>fine</p>", "slug": "also-good", "title": "Fine"},
    ]
    out = fingerprint_many(docs)
    assert len(out) == 3
    assert not out[0].get("error")
    assert out[1].get("error"), "a non-string body should be recorded, not raised"
    assert out[1]["slug"] == "bad", "an errored fingerprint must stay identifiable"
    assert not out[2].get("error")


def test_end_to_end_classification():
    fp = fingerprint(PROCEDURE, title="Create a Case", slug="create-a-case")
    assert classify(fp)[0] == "T2"
