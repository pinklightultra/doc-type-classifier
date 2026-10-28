# doc-type-classifier

`doctype` reads one HTML documentation page and returns one of thirteen structural types, plus the name of the rule that fired. It is for technical writers and docs engineers who have a directory of exported articles and need to route quality checks by document shape.

Parsing uses BeautifulSoup. The decision itself is an ordered list of rules over a small structural fingerprint: fifteen integer counts, the heading text, and whatever title, slug, category, and tags you pass in. There is no model and no training step.

## Problem

I was running a knowledge base of 1,806 published articles and wanted a quality scan over all of them. The first version applied every check to every article. Nearly every false positive came from that:

- A short concept page was flagged as a truncated how-to.
- A role matrix was flagged as a malformed field table.
- A link index was flagged as an article with no content.

The scan became usable once it classified the document first, ran only the checks that fit the type, and suppressed the rest. That turns a pile of findings into a list a writer can act on.

The type has to be explainable to the person whose article was flagged. "This fired because the heading `Configuration Steps` is present" is an argument. When the call is wrong, you can read the rule that misfired and edit that one rule.

## Method

The package is split in two, and the split is the whole design.

**Fingerprint.** `fingerprint()` parses with the stdlib HTML parser (no lxml build) and reduces the page to a JSON-serializable dict. The fifteen counts are `chars`, `h`, `h2`, `h3`, `h4`, `tables`, `fieldish_tables`, `ol`, `ul`, `li`, `img`, `pre`, `strong`, `links`, and `p`. Heading text is kept for the first twenty headings (`heading_txt`); the heading counts include every heading. A parser is required for the counts. A regular expression mis-counts a nested table, or a `>` inside an attribute, and a wrong count becomes a confident wrong type with nothing logged.

**Classify.** `classify()` reads that dict and returns `(type_code, reason)`. Missing keys count as zero, so a partial fingerprint still classifies. The reason names the rule that fired. On a compound rule it does not say which clause matched.

The current rules consult `chars`, `ol`, `tables`, `fieldish_tables`, `pre`, `links`, `h2`, and `h3`, plus title, slug, tags, category, and heading text. `ul`, `li`, `img`, `strong`, `p`, `h`, and `h4` are recorded and then ignored. Procedure looks for an ordered list (`ol`). A bullet list and a screenshot do not move the type.

A field table means the first cell of the first row is bold (`strong` or `b`). That is an authoring convention, implemented in `fingerprint._is_field_table`. `pre` counts `<pre>` and `<code>` elements together, including a `<code>` nested in a `<pre>`.

Category names, heading phrases, and size thresholds live in `taxonomy.Profile`. The shipped profile was tuned on one knowledge base. Retargeting means editing the profile. Two English title words, `bundle` and `template`, stay in `classify()`; they are called out under retargeting. An unknown profile key raises `ValueError` and names itself. A typo that was ignored would leave a rule on its default and look like a change in the corpus.

The thirteen codes are fixed in `doctype.taxonomy.TYPES`. Changing that dict changes what the classifier is for.

### The thirteen types

| Code | Type | What the rule keys on |
|---|---|---|
| T1 | Overview / Concept | An overview-shaped title or an overview tag; thin prose; unstructured prose. Also a release-note page with no table and no ordered list. |
| T2 | Task / Procedure | An ordered list, a heading that starts with an action verb (`Add a Rule`), or a title that starts with a CRUD verb (`Create`, `Edit`, `Delete`, …). |
| T3 | Field / Screen Reference | A field table and no ordered list, or any table plus a screen-ish title or a UI heading (`column options`, `window`). Structured pages that matched nothing earlier land here. |
| T4 | Config Instruction | A metadata heading, a `Configuration Steps` / `System Variable` / `Configuration SQL` heading, two headings that are entirely `^[A-Z][A-Z0-9_]{5,}$` (six characters or more), the config category plus an ordered list, or a field table plus a system-variable marker. |
| T5 | Release Note (canonical) | Release-note category or tag, and a canonical section heading (`What's New`, `Why It Matters`, `Who Is Impacted`, `Enabled by Default`). |
| T6 | Release Note (legacy) | The same gate, with a table and none of those headings. Also the fallback for anything else inside the gate. |
| T7 | Index / Landing / Rollup | The same gate, and a version or rollup title, an index title (`resolved issues`, `patch notes`, `service pack`), or no tables and more than 15 links. |
| T8 | API Spec | A contract heading (`Authentication`, `Endpoint`, `Request`, `Response`, …) plus a field table, a `pre` or `code` element, any table, or the substring `api` in the title. |
| T9 | Code Sample / Payload | No `pre` or `code`, more than 3,000 characters, and a title starting with `Sample` or a heading such as `Sample Request`, `Data Models`, `Payload`, or `Bundle`. |
| T10 | FAQ | An `faq` tag, `faq` in the title, or an `faqs` heading. |
| T11 | Long-form Master Guide | More than 15,000 characters, and at least four tables, or three `h2`s, or three `h3`s, or four field tables. |
| T12 | Internal / Non-content | An `imported` tag, a UUID-shaped slug, raw-import or engineering markers, a runbook title or a `Trigger:` / `Escalation` heading, an internal category or tag, a heading from both PRD groups, a `bundle` title plus a bundle heading, or a template skeleton. |
| STUB | Stub / empty | Fewer than 60 characters of text. This test runs first. |

Thresholds above are the shipped profile (`stub_max_chars` 60, `code_sample_min_chars` 3000, `master_min_chars` 15000, `index_min_links` 15, and the master-guide structure minimums). They are profile fields.

The type names describe the corpus the taxonomy was collapsed from: roughly forty category-local types in that 1,806-article base, reduced to one primary type per document. Longer signatures, and the quality checks each type should attract or suppress, are in [TAXONOMY.md](TAXONOMY.md). Where the type name and the `if` disagree, the `if` is the behavior.

**T9 fires only on an unfenced payload.** `pre` must be 0. A sample wrapped in `<pre>` or `<code>` never classifies as T9; those headings usually satisfy the API rule and land on T8. The rule does not look for braces and does not parse the body as JSON. Prose past the size threshold under a `Payload` heading matches.

**T4's category gate is wider than the comment above it.** The config category alone does not match, which the tests lock. The config category plus one ordered list does match, and so does one config-step heading, or two headings whose whole text matches `^[A-Z][A-Z0-9_]{5,}$`, in any category. One such heading is not enough on its own. A plain how-to filed under the config category classifies as T4. The reason string still says `config instruction (metadata / system-variable / config-steps marker)` when the document has none of those markers. The shipped profile has no `config_tags` field.

**T8's second signal includes the title.** The contract vocabulary has to appear in a heading. The other half is then a field table, a `pre` or `code` element, any table, or the substring `api` in the title. A page titled "Partner API Integration Overview" with an `Authentication` heading and no table, list, or code block classifies as T8.

### Precedence

The types overlap. A release note contains steps. A long config guide is also a master guide. The first matching rule wins. That order is the specification: read `classify()` from the stub test down to the fallthrough.

Three orderings carry the design. Each one showed up as a block of errors in the confusion matrix, and the fix was to test the more specific claim first.

1. **Non-content before every content type.** An engineering dump that contains ordered steps is a document that should not have been published. The stub test is the exception that runs even earlier: under 60 characters, an `imported` tag is never consulted.
2. **FAQ before API.** An integration page with an `faq` tag, a table, and `Authentication` / `Endpoint` headings satisfies the API rule. FAQ is tested first, so it stays T10. `test_faq_beats_api` locks that.
3. **Config and the master guide before procedure.** Both routinely contain ordered lists. "Has an `ol`" is a weaker signal than a system-variable marker, or than 20,000 characters across several sections.

Release notes are a closed branch. A release-note tag or a release-note category resolves to exactly one of T7, T5, T1, or T6, and the function returns inside that branch. Nothing outside the gate can become T5, T6, or T7.

After those branches, procedure wins over a field table when a heading starts with an action verb: "Add a Rule" above a field table is a how-to. Prose that matches nothing falls through to T1. Structured residue falls through to T3. The prose default was a measured change: an unstructured page was more often a short explanation than a broken table.

## Result

The five files in [`examples/docs/`](examples/docs) are synthetic fixtures written to land on five different types. They demonstrate the command. They are not an accuracy set.

```bash
doctype classify examples/docs/ --category-from-dir
```

```
  data-exchange-faq      T10   FAQ                       faq / setup+faq
  create-a-case          T2    Task / Procedure          procedural (ordered steps / action headings / imperative title)
  2.4-release-notes      T7    Index / Landing / Rollup  version / rollup landing page
  runbook-queue-backlog  T12   Internal / Non-content    support runbook (internal)
  record-detail-tab      T3    Field / Screen Reference  field / screen reference (table, no steps)

      1  T10   FAQ
      1  T2    Task / Procedure
      1  T7    Index / Landing / Rollup
      1  T12   Internal / Non-content
      1  T3    Field / Screen Reference
      5  total
```

That is the transcript from this tree. Filenames inside a directory are sorted. Directory order follows the filesystem walk, so another machine may print the same five rows in a different order. The type on each file stays the same. The summary lists types in the order they were first seen, because every count is 1.

`--category-from-dir` is load-bearing for the T7 row. The command line has no CMS metadata. The flag sets each file's category to the basename of its parent directory, here `Release Notes`, which is a name in the shipped profile. Without the flag the release-note branch never opens, and that file is T1:

```
  2.4-release-notes      T1    Overview / Concept        prose fallthrough -> concept
```

Category match is exact after lowercasing. It is not hierarchical. `Release Notes` matches. `4.2 Release Notes` does not. The same flag is what makes T4's config-category branch and T12's internal-category branch reachable from the CLI. See [What the command line cannot reach](#what-the-command-line-cannot-reach).

### What 84.2% measures

On a 146-article sample from the 1,806, the rules agree with the labels on 123 (84.2%). Those 146 articles are the set the rules were tuned on, over four rounds, scoring the same items each round. The figure is training accuracy. This repository contains no held-out split, no cross-validation, and no second labeled set. You cannot recompute it from the files here: the articles and their slugs are private.

| Round | Accuracy | What changed |
|---|---|---|
| v0 | 67.1% | Rules transcribed from the written taxonomy |
| v1 | 75.3% | Config required more than the category; API required the contract vocabulary plus a second signal; FAQ moved above API; prose defaults to concept |
| v2 | 82.2% | Config and the master guide moved above procedure; the master guide keyed on size; action-verb headings win over a field table |
| v3 | 84.2% | Spec imports and marketing prose routed to non-content; two ALL_CAPS headings imply config |

The labels came from four independent LLM agents. Each agent read the article, applied the written taxonomy, and did not see these rules. Each label carried a confidence and a one-line justification. That is a proxy for a human adjudication. Some of the 23 disagreements are probably the label.

On that same set, API-spec precision was 50% (support 7), master-guide recall was 62% (support 8), and stub recall was 71% (support 7). FAQ and code sample were both 100%; code sample had a support of 1. Five of the thirteen types had support under 10. Per-type figures at that size are anecdotes.

I stopped at v3 because the remaining misses were almost all one-count boundary cases, plus articles the labeling agents had already marked low-confidence where two types fit. Another rule edit would have fit those 146 items more tightly.

The code in this repository was refactored out of that working copy: the vocabulary moved into a profile. The refactor was checked to classify all 1,806 documents the same way and to reproduce 123/146 with the same confusion matrix. The tests in this repository do not, and cannot, repeat that check. They assert rule behavior on hand-built fingerprints. For a figure on your own export, label a sample and run `doctype score`.

With the shipped profile and no tuning, a different knowledge base will score worse until the category names, tags, and headings match yours.

## Install

Python 3.9 or newer. The only runtime dependency is BeautifulSoup, and it is used to count tags.

```bash
git clone https://github.com/pinklightultra/doc-type-classifier
cd doc-type-classifier
pip install -e .
```

That puts `doctype` on your path. This repository is the distribution; `pyproject.toml` has no package-index metadata.

To run the tests as well:

```bash
pip install -e ".[test]"
pytest -q
```

## Use

Classify a directory of HTML. You can do that before reading a rule.

```bash
doctype classify docs/                         # a row per file, then a count per type
doctype classify docs/ --json                  # one JSON object per file
doctype classify docs/ --category-from-dir     # parent directory name becomes the category
doctype fingerprint docs/ -o fps.json          # write the structural counts
doctype score fps.json labels.json             # accuracy, disagreements, per-type recall and precision
doctype score fps.json labels.json --detail    # and list every miss
doctype score fps.json labels.json --expect 123  # exit 1 unless exactly 123 are correct
doctype profile > my-profile.json              # dump the vocabulary so you can edit it
doctype --profile my-profile.json classify docs/
```

`classify` prints the slug (cut at 60 characters), the type code, the type name (cut at 24 characters), and the reason. A trailing block counts files per type. `--json` emits `path`, `slug`, `type`, `name`, `reason`, and `chars`. A directory that contains no `.html` or `.htm` file prints `no HTML files found` on stderr and exits 1. Directory walks keep those two suffixes; a path you pass as a file is read whatever the suffix is.

The title is the filename stem, with hyphens and underscores turned into spaces. Several rules key on the title, and an empty title loses matches. The CLI does not read a `<title>` element. An `<h1>` is stored with the other headings; it is not copied into the title field. `create-a-case.html` is titled "create a case", which is enough for the procedural rule on its own. `data-exchange-faq.html` matches because the title contains `faq`.

CRUD verbs are prefixes of the title, with no word boundary, so a stem `created-widgets` is also T2. Action-verb headings use a word boundary. Title and heading phrases match as substrings; tags match as whole values.

`fingerprint` exists so a corpus is parsed once. Rule edits then re-score against the JSON. That loop is how the four rounds above were run. Files are read as UTF-8 with or without a BOM; an undecodable byte is replaced, so one bad file does not abort the sweep.

`score` joins fingerprints to labels on `slug` and skips any fingerprint with an `error` key. Labels may be a list of `{"slug", "label"}` objects, a `{"labels": [...]}` wrapper, or a flat `{"slug": "T2"}` mapping. `--expect` is the regression gate for a labeled cache you keep outside this repository.

### From Python

```python
from doctype import classify, fingerprint

html = open("create-a-case.html", encoding="utf-8").read()
fp = fingerprint(html, title="Create a Case", top="How-To", tags=["procedure"])
code, why = classify(fp)
# ("T2", "procedural (ordered steps / action headings / imperative title)")
```

`top` is the category name. `tags` are exact values, lowercased. `fingerprint_many()` takes a sequence of `{html, title, slug, top, tags, ...}` mappings. A document that raises is returned as `{"error": "..."}` plus its title, slug, and category, and the sweep continues. Check `error` before you classify. An errored fingerprint has no counts, every missing count reads as zero, and the result is STUB.

### What the command line cannot reach

`doctype classify` and `doctype fingerprint` pass a title, a slug, and — only with `--category-from-dir` — a category. They never pass tags.

A rule whose only gate is a tag cannot fire from the CLI. In the shipped profile that is the `imported` tag, one of the T12 rules. Where a tag is one of several alternatives, the other half still fires: FAQ from the title or an `faqs` heading, overview from the title, internal from the category, release note from the category.

Without a category, T5, T6, and T7 are unreachable. All three sit behind the release-note gate, and the CLI has no other way to open it. The library call `fingerprint(html, title=..., top=..., tags=...)` takes the metadata the files do not carry, so every rule is reachable from Python.

### Point the vocabulary at your categories

```bash
doctype profile > my-profile.json
```

Edit, then pass `--profile`. Or build a `Profile` and normalize it, which lowercases every vocabulary list once:

```python
from doctype import classify, Profile

german = Profile(
    release_note_categories=["Versionshinweise"],
    canonical_rn_headings=["was ist neu", "warum"],
).normalized()

classify(fp, german)
```

Phrase lists match as case-insensitive substrings of the joined heading text, so `system variable` matches a heading `System Variable Configuration`. Tags match as whole values. The tag `not-faq` does not match `faq`.

Change these first:

1. `release_note_categories`, `config_categories`, `internal_categories`, and the `*_tags` lists. These are your CMS's names. Until a name matches, that category or tag rule does not fire.
2. `canonical_rn_headings`. The section headings in your release-note schema.
3. `screen_words`. The shipped list includes `claims`, because in the original corpus a claims grid is a screen. Replace it with your own noun for a table people look at.
4. `fingerprint._is_field_table`, if a field table in your HTML is not bold in the first cell.

Two title tests are written in `classify()` and are not profile fields: the word `bundle` (with the bundle headings, this is marketing prose) and the word `template` (a skeleton only when the page is under 300 characters or contains a placeholder heading). A title like "Link an Ad Hoc Template" on a real article stays content. Version-number and UUID patterns are profile fields (`version_title_pattern`, `bare_version_pattern`, `uuid_slug_pattern`), stored as strings so they survive JSON.

`profiles/default.json` is a dump of the defaults for you to copy. The package does not load that file. The defaults live on `Profile`. Regenerate the dump with `doctype profile > profiles/default.json`.

## Limits

- **HTML only.** The CLI reads `.html` and `.htm`. There is no Markdown, PDF, or docx reader.
- **The shipped vocabulary is English.** Lists and thresholds move with the profile. The words `bundle` and `template` do not; they are in the rules.
- **No confidence score.** A rule matches or it does not. Overlapping types are resolved by order, not by a margin.
- **The reason names the rule.** For T4, T8, and the other compound conditions, it does not identify the clause.
- **Under 60 characters is STUB, whatever the structure.** A 40-character page with a perfect field table is a stub. The threshold is deliberately low. A thin but real page is a concept article, and calling those pages empty produced more false "broken document" reports than any other single check in the original scan.
- **Category and tag matching is exact** after lowercasing. Nested CMS categories need the top-level name passed as `top`.
- **Heading text stops at twenty.** A phrase that first appears on heading 21 cannot fire. The numeric heading counts still include it.
- **One bad document does not stop a corpus sweep.** The CLI replaces undecodable bytes. `fingerprint_many` records `error` and continues. Classify that record only after you have handled the error, or it will come back STUB.

## Tests

```bash
pip install -e ".[test]"
pytest -q          # 70 passed
```

The tests assert rule behavior on minimal fingerprints: exactly the signals one rule needs, so a failure names the rule. One parametrized case produces every code in `TYPES`. A second test fails if a code is added to the dict and left out of that list. Precedence has its own cases, including FAQ before API, config and the master guide before procedure, non-content before a how-to, and stub before an `imported` tag.

Three regressions are locked:

- Category names were compared in the CMS's original casing. The profile lowercases its lists on load, so the comparison missed, the release-note branch never opened, 41 documents fell through to other types, and nothing raised.
- Tags were matched as substrings. A tag `not-faq` classified the page as an FAQ.
- Compiled patterns were cached in a dict keyed by `id()`. After garbage collection, one profile could receive another profile's patterns.

[`.github/workflows/test.yml`](.github/workflows/test.yml) runs `pytest` on every push and pull request to `main` or `master`, on Python 3.10, 3.11, and 3.12. The package allows 3.9 and up; the workflow does not install 3.9.

These tests are not the 84.2% measurement. A labeled corpus has to be yours. `doctype score --expect` is how you pin a number you computed yourself.

## Provenance

I built this while running documentation for a healthcare SaaS platform. It is the routing step in front of a type-aware scan of those 1,806 articles. The taxonomy was derived from that corpus, which is why a few signatures are specific to it: `claims` as a screen, Jira-epic rows as config metadata, `CDS Hooks` in the API heading list. Those strings are profile data so they can be replaced without forking the rules.

## License

MIT. See [LICENSE](LICENSE).
