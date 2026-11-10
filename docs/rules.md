# Rules

How a page becomes a type code. The codes, and the checks each one should attract or suppress, are in [Types](types.md). What the tool will not do is in [Limitations](limitations.md).

The package is split in two, and the split is the whole design.

## Fingerprint

`fingerprint()` parses with the stdlib HTML parser (no lxml build) and reduces the page to a JSON-serializable dict. The fifteen counts are `chars`, `h`, `h2`, `h3`, `h4`, `tables`, `fieldish_tables`, `ol`, `ul`, `li`, `img`, `pre`, `strong`, `links`, and `p`. Heading text is kept for the first twenty headings (`heading_txt`); the heading counts include every heading. A parser is required for the counts. A regular expression mis-counts a nested table, or a `>` inside an attribute, and a wrong count becomes a confident wrong type with nothing logged.

The current rules consult `chars`, `ol`, `tables`, `fieldish_tables`, `pre`, `links`, `h2`, and `h3`, plus title, slug, tags, category, and heading text. `ul`, `li`, `img`, `strong`, `p`, `h`, and `h4` are recorded and then ignored. Procedure looks for an ordered list (`ol`). A bullet list and a screenshot do not move the type.

A field table means the first cell of the first row is bold (`strong` or `b`). That is an authoring convention, implemented in `fingerprint._is_field_table`. `pre` counts `<pre>` and `<code>` elements together, including a `<code>` nested in a `<pre>`.

## Classify

`classify()` reads that dict and returns `(type_code, reason)`. Missing keys count as zero, so a partial fingerprint still classifies. The reason names the rule that fired. On a compound rule it does not say which clause matched. There is no confidence score. A rule matches or it does not.

Category names, heading phrases, and size thresholds live in `taxonomy.Profile`. The shipped profile was tuned on one knowledge base. Retargeting means editing the profile. Two English title words, `bundle` and `template`, stay in `classify()`; they are called out under [retargeting](#two-title-words-are-not-profile-fields). An unknown profile key raises `ValueError` and names itself. A typo that was ignored would leave a rule on its default and look like a change in the corpus.

## Precedence

The types overlap. A release note contains steps. A long config guide is also a master guide. The first matching rule wins. That order is the specification: read `classify()` from the stub test down to the fallthrough.

Three orderings carry the design. Each one showed up as a block of errors in the confusion matrix, and the fix was to test the more specific claim first.

1. **Non-content before every content type.** An engineering dump that contains ordered steps is a document that should not have been published. The stub test is the exception that runs even earlier: under 60 characters, an `imported` tag is never consulted.
2. **FAQ before API.** An integration page with an `faq` tag, a table, and `Authentication` / `Endpoint` headings satisfies the API rule. FAQ is tested first, so it stays T10. `test_faq_beats_api` locks that.
3. **Config and the master guide before procedure.** Both routinely contain ordered lists. "Has an `ol`" is a weaker signal than a system-variable marker, or than 20,000 characters across several sections.

Release notes are a closed branch. A release-note tag or a release-note category resolves to exactly one of T7, T5, T1, or T6, and the function returns inside that branch. Nothing outside the gate can become T5, T6, or T7.

After those branches, procedure wins over a field table when a heading starts with an action verb: "Add a Rule" above a field table is a how-to. Prose that matches nothing falls through to T1. Structured residue falls through to T3. The prose default was a measured change: an unstructured page was more often a short explanation than a broken table.

The same order, as the `if` statements run:

1. **Empty.** Under the stub threshold. Nothing else matters.
2. **Internal / non-content.** Imported tag, UUID slug, raw-import headings, engineering headings or slug markers, runbook, internal category, spec import, marketing prose, template skeleton. Before everything, because an engineering dump containing ordered steps is not a how-to.
3. **Release notes.** If the document carries the release-note tag or sits in the release-note category, it is exactly one of four things. A version or rollup title gives T7; canonical section headings give T5; an attribute table gives T6; prose with no table at all is a concept page, T1. Nothing outside that gate can reach T5, T6, or T7. The command line supplies no tags, so those three types need [`--category-from-dir`](#what-the-command-line-cannot-reach) and a directory named for your release-note category.
4. **FAQ.** Before API, because an integration FAQ matches the API vocabulary.
5. **API, then unfenced payload.**
6. **Config instruction.** Never on the category alone, but the category plus one ordered list is enough. See [T4](types.md#t4-config-instruction).
7. **Long-form master.** Before procedure, because masters contain steps.
8. **Procedure.** Ordered steps, action-verb headings, or an imperative title.
9. **Field / screen reference.** A field table with no steps, or a table plus a screen-ish title.
10. **Overview / concept.**
11. **Fallthrough.** Prose defaults to concept, not to reference: an unstructured page is far more often a short explanation than a broken table. Anything structured that got this far defaults to reference.

## Command line

The pages in this `docs/` directory are Markdown. They are not a corpus. A directory with no `.html` or `.htm` file prints `no HTML files found` on stderr and exits 1. The fixtures that the commands below read are in `examples/docs/`.

```bash
doctype classify examples/docs/
doctype classify examples/docs/ --json
doctype classify examples/docs/ --category-from-dir
```

`classify` prints the slug (cut at 60 characters), the type code, the type name (cut at 24 characters), and the reason. A trailing block counts files per type. `--json` emits `path`, `slug`, `type`, `name`, `reason`, and `chars`. Directory walks keep `.html` and `.htm`; a path you pass as a file is read whatever the suffix is.

The title is the filename stem, with hyphens and underscores turned into spaces. Several rules key on the title, and an empty title loses matches. The CLI does not read a `<title>` element. An `<h1>` is stored with the other headings; it is not copied into the title field. `create-a-case.html` is titled "create a case", which is enough for the procedural rule on its own. `data-exchange-faq.html` matches because the title contains `faq`.

CRUD verbs are prefixes of the title, with no word boundary, so a stem `created-widgets` is also T2. Action-verb headings use a word boundary. Title and heading phrases match as substrings; tags match as whole values.

The transcript in the README is `doctype classify examples/docs/ --category-from-dir`. Without the flag the release-note row changes and the other four do not:

```bash
doctype classify examples/docs/
```

```
  2.4-release-notes      T1    Overview / Concept        prose fallthrough -> concept
```

Category match is exact after lowercasing. It is not hierarchical. `Release Notes` matches. `4.2 Release Notes` does not. The same flag is what makes T4's config-category branch and T12's internal-category branch reachable from the CLI.

`fingerprint` exists so a corpus is parsed once. Rule edits then re-score against the JSON. Files are read as UTF-8 with or without a BOM; an undecodable byte is replaced, so one bad file does not abort the sweep. The default output name is `fingerprints.json`, which this repository gitignores. Heading text is in that file. Do not commit it for a corpus that is not yours.

```bash
doctype fingerprint examples/docs/ --category-from-dir -o fingerprints.json
```

### Score

`doctype score` joins a fingerprint file to a labels file on `slug` and skips any fingerprint with an `error` key. It prints how many labels were scored, the accuracy, the disagreements, and per-type support, recall, and precision. `--detail` lists every miss. `--expect N` exits 1 unless exactly N are correct. That is the regression gate for a labeled cache you keep outside this repository.

Labels may be a list of `{"slug", "label"}` objects, a `{"labels": [...]}` wrapper, or a flat `{"slug": "T2"}` mapping. This repository does not include a labels file. The 146 articles behind the 84.2% figure are private, and a `labels*.json` dropped here is gitignored. The five files in `examples/docs/` are not an accuracy set, so they are not scored here.

## From Python

```python
from doctype import classify, fingerprint

html = open("examples/docs/How-To/create-a-case.html", encoding="utf-8").read()
fp = fingerprint(html, title="Create a Case", top="How-To", tags=["procedure"])
code, why = classify(fp)
# ("T2", "procedural (ordered steps / action headings / imperative title)")
```

`top` is the category name. `tags` are exact values, lowercased. `fingerprint_many()` takes a sequence of `{html, title, slug, top, tags, ...}` mappings. A document that raises is returned as `{"error": "..."}` plus its title, slug, and category, and the sweep continues. Check `error` before you classify. An errored fingerprint has no counts, every missing count reads as zero, and the result is STUB.

## What the command line cannot reach

`doctype classify` and `doctype fingerprint` pass a title, a slug, and — only with `--category-from-dir` — a category. They never pass tags.

A rule whose only gate is a tag cannot fire from the CLI. In the shipped profile that is the `imported` tag, one of the T12 rules. Where a tag is one of several alternatives, the other half still fires: FAQ from the title or an `faqs` heading, overview from the title, internal from the category, release note from the category.

Without a category, T5, T6, and T7 are unreachable. All three sit behind the release-note gate, and the CLI has no other way to open it. The library call `fingerprint(html, title=..., top=..., tags=...)` takes the metadata the files do not carry, so every rule is reachable from Python.

## Point the vocabulary at your categories

```bash
doctype profile > my-profile.json
doctype --profile my-profile.json classify examples/docs/ --category-from-dir
```

`my-profile.json` is gitignored. Edit it, then pass `--profile`. Or build a `Profile` and normalize it, which lowercases every vocabulary list once:

```python
from doctype import classify, fingerprint, Profile

html = open("examples/docs/How-To/create-a-case.html", encoding="utf-8").read()
fp = fingerprint(html, title="Create a Case", top="How-To", tags=["procedure"])

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

### Two title words are not profile fields

Two title tests are written in `classify()` and are not profile fields: the word `bundle` (with the bundle headings, this is marketing prose) and the word `template` (a skeleton only when the page is under 300 characters or contains a placeholder heading). A title like "Link an Ad Hoc Template" on a real article stays content. Version-number and UUID patterns are profile fields (`version_title_pattern`, `bare_version_pattern`, `uuid_slug_pattern`), stored as strings so they survive JSON.

`profiles/default.json` is a dump of the defaults for you to copy. The package does not load that file. The defaults live on `Profile`. Regenerate the dump with `doctype profile > profiles/default.json`. Passing the committed dump explicitly classifies the fixtures the same way as the shipped profile:

```bash
doctype --profile profiles/default.json classify examples/docs/ --category-from-dir
```
