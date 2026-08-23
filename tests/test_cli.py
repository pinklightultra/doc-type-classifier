"""CLI tests, including the scoring loop that the rules were tuned with."""

import json

import pytest

from doctype.cli import main

# Both fixtures are padded past the stub threshold on purpose: a document under
# it is a stub no matter what structure it has, which is correct but makes for a
# useless CLI fixture.
PROCEDURE = """<h2>Create a Case</h2>
<p>{}</p>
<ol><li>Click New.</li><li>Enter a name.</li><li>Save the case.</li></ol>""".format(
    "Open a case from the queue. " * 8)
OVERVIEW = """<h2>Overview</h2><p>{}</p>""".format("Widgets explained. " * 20)


@pytest.fixture
def corpus(tmp_path):
    (tmp_path / "create-a-case.html").write_text(PROCEDURE, encoding="utf-8")
    (tmp_path / "overview-of-widgets.html").write_text(OVERVIEW, encoding="utf-8")
    return tmp_path


def test_classify_table(corpus, capsys):
    assert main(["classify", str(corpus)]) == 0
    out = capsys.readouterr().out
    assert "T2" in out and "T1" in out
    assert "total" in out


def test_classify_json(corpus, capsys):
    assert main(["classify", str(corpus), "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    by_slug = {r["slug"]: r["type"] for r in rows}
    assert by_slug == {"create-a-case": "T2", "overview-of-widgets": "T1"}
    assert all(r["reason"] for r in rows)


def test_classify_reports_when_nothing_matched(tmp_path, capsys):
    assert main(["classify", str(tmp_path)]) == 1
    assert "no HTML files" in capsys.readouterr().err


def test_title_falls_back_to_the_filename(corpus, capsys):
    """Several rules key on the title. Deriving it from the slug is what makes
    `classify` on a bare directory of files useful at all -- without it the
    overview document has no signal and lands in a fallthrough."""
    main(["classify", str(corpus), "--json"])
    rows = json.loads(capsys.readouterr().out)
    assert {r["slug"]: r["type"] for r in rows}["overview-of-widgets"] == "T1"


def test_fingerprint_then_score(corpus, tmp_path, capsys):
    fps = tmp_path / "fps.json"
    assert main(["fingerprint", str(corpus), "-o", str(fps)]) == 0
    assert len(json.loads(fps.read_text(encoding="utf-8"))) == 2

    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps([
        {"slug": "create-a-case", "label": "T2"},
        {"slug": "overview-of-widgets", "label": "T1"},
    ]), encoding="utf-8")

    assert main(["score", str(fps), str(labels), "--detail"]) == 0
    out = capsys.readouterr().out
    assert "2/2 = 100.0%" in out


def test_score_expect_is_a_regression_gate(corpus, tmp_path, capsys):
    fps = tmp_path / "fps.json"
    main(["fingerprint", str(corpus), "-o", str(fps)])
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps({"create-a-case": "T2", "overview-of-widgets": "T1"}),
                      encoding="utf-8")

    assert main(["score", str(fps), str(labels), "--expect", "2"]) == 0
    assert main(["score", str(fps), str(labels), "--expect", "1"]) == 1
    assert "REGRESSION" in capsys.readouterr().err


def test_score_accepts_all_three_label_shapes(corpus, tmp_path):
    fps = tmp_path / "fps.json"
    main(["fingerprint", str(corpus), "-o", str(fps)])
    shapes = [
        [{"slug": "create-a-case", "label": "T2"}],
        {"labels": [{"slug": "create-a-case", "label": "T2"}]},
        {"create-a-case": "T2"},
    ]
    for i, shape in enumerate(shapes):
        path = tmp_path / f"labels{i}.json"
        path.write_text(json.dumps(shape), encoding="utf-8")
        assert main(["score", str(fps), str(path), "--expect", "1"]) == 0


def test_score_rejects_a_mismatched_pair(corpus, tmp_path, capsys):
    """Scoring fingerprints against labels for a different corpus silently yields
    0 rows. That has to be an error, not an accuracy of 0%."""
    fps = tmp_path / "fps.json"
    main(["fingerprint", str(corpus), "-o", str(fps)])
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps({"some-other-document": "T2"}), encoding="utf-8")
    assert main(["score", str(fps), str(labels)]) == 1
    assert "wrong pair of inputs" in capsys.readouterr().err


def test_profile_dump_round_trips(tmp_path, capsys):
    assert main(["profile"]) == 0
    dumped = capsys.readouterr().out
    path = tmp_path / "p.json"
    path.write_text(dumped, encoding="utf-8")
    assert main(["--profile", str(path), "profile"]) == 0


def test_category_from_dir(tmp_path, capsys):
    folder = tmp_path / "Release Notes"
    folder.mkdir()
    (folder / "widget-enhancement.html").write_text(
        "<h2>What's New</h2><p>" + "x " * 100 + "</p>", encoding="utf-8")
    main(["classify", str(folder), "--json", "--category-from-dir"])
    assert json.loads(capsys.readouterr().out)[0]["type"] == "T5"
