"""Profile loading tests. The profile is the whole configuration surface, so a
silently-ignored key here means a rule quietly stops firing."""

import json

import pytest

from doctype import DEFAULT_PROFILE, Profile


def test_round_trips_through_json(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps(DEFAULT_PROFILE.to_dict()), encoding="utf-8")
    assert Profile.load(path).to_dict() == DEFAULT_PROFILE.to_dict()


def test_unknown_key_is_an_error():
    """A typo'd key would otherwise look like a corpus change: the rule it was
    meant to configure keeps its default and the accuracy drop has no cause."""
    with pytest.raises(ValueError, match="unknown profile key"):
        Profile.from_dict({"relase_note_tags": ["release-notes"]})


def test_unknown_key_names_itself():
    with pytest.raises(ValueError) as exc:
        Profile.from_dict({"nope": [], "also_nope": []})
    assert "also_nope" in str(exc.value) and "nope" in str(exc.value)


def test_partial_profile_keeps_defaults():
    p = Profile.from_dict({"stub_max_chars": 10})
    assert p.stub_max_chars == 10
    assert p.release_note_categories == Profile().release_note_categories


def test_normalized_lowercases_vocabulary_but_not_patterns():
    p = Profile(release_note_categories=["Release Notes"],
                overview_words=["Overview", "ABOUT"]).normalized()
    assert p.release_note_categories == ["release notes"]
    assert p.overview_words == ["overview", "about"]
    # Patterns are regex and case-sensitivity is applied at compile time.
    assert p.uuid_slug_pattern == Profile().uuid_slug_pattern


def test_normalized_is_idempotent():
    once = DEFAULT_PROFILE.normalized().to_dict()
    twice = DEFAULT_PROFILE.normalized().normalized().to_dict()
    assert once == twice


def test_default_profile_is_already_normalized():
    assert DEFAULT_PROFILE.to_dict() == DEFAULT_PROFILE.normalized().to_dict()


def test_to_dict_excludes_the_internal_pattern_cache(tmp_path):
    """Regression guard: the compiled-regex cache lives on the instance, so a
    naive vars() dump would put compiled patterns into the JSON and break the
    round trip."""
    from doctype.classify import classify

    p = Profile().normalized()
    classify({"chars": 900, "title": "Overview"}, p)  # populates the cache
    data = p.to_dict()
    assert all(isinstance(v, (str, int, list)) for v in data.values())
    path = tmp_path / "p.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert Profile.load(path).to_dict() == data
