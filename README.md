# doc-type-classifier

Tell documentation types apart by structure alone. Feed it HTML, get back one of
thirteen types plus the reason it decided that.

```
$ doctype classify examples/docs/ --category-from-dir
  create-a-case          T2    Task / Procedure          procedural (ordered steps / action headings / imperative title)
  data-exchange-faq      T10   FAQ                       faq / setup+faq
  record-detail-tab      T3    Field / Screen Reference  field / screen reference (table, no steps)
  2.4-release-notes      T7    Index / Landing / Rollup  version / rollup landing page
  runbook-queue-backlog  T12   Internal / Non-content    support runbook (internal)

      1  T2    Task / Procedure
      1  T10   FAQ
      1  T3    Field / Screen Reference
      1  T7    Index / Landing / Rollup
      1  T12   Internal / Non-content
      5  total
```

That is a real transcript, and it is runnable: the five HTML files it reads ship in
[`examples/docs/`](examples/docs), so after `pip install -e .` that command prints
those exact lines for you. They are synthetic fixtures written to land on five
different types, which demonstrates the CLI rather than the accuracy. What is not
shipped here is a corpus -- there is none, and no corpus this was tuned against can
be published. `--category-from-dir` is load-bearing: the T7 row needs the file's
parent directory (`examples/docs/Release Notes/`) to name your release-note
category, and a plain `doctype classify examples/docs/` reports that same file as
T1 instead. See [Reachability from the CLI](#reachability-from-the-cli).

No model, no training, no network. `classify` reads a dict of 15 integers plus the
heading text, and returns in microseconds; the only dependency is BeautifulSoup,
and that is just for counting tags.

## Why this exists

I was running a knowledge base of 1,806 published articles and wanted an
automated quality scan over all of them. The first version applied every check to
every article, and nearly every false positive came from that: a short concept
page flagged as a truncated how-to, a role matrix flagged as a malformed field
table, a link index flagged as an article with no content.

The fix was routing. Classify the document first, then run only the checks that
fit its type and suppress the ones that do not. That turns "289 problems" into
something a person can act on.

Rules rather than a model, for two reasons. The scan has to justify itself to the
writer whose article got flagged, and "this fired because the heading `Configuration
Steps` is present" is an argument while a 0.83 confidence score is not. And when
the classifier is wrong you can read the rule that misfired and edit that one
rule, which is a five-minute loop instead of a relabel-and-retrain loop.

## Install

```bash
git clone https://github.com/pinklightultra/doc-type-classifier
cd doc-type-classifier
pip install -e .          # or: pip install -e ".[test]"
```

Python 3.9+. One runtime dependency. Not on PyPI, so the editable install from a
clone is the only install there is.

## Use

As a library:

```python
from doctype import classify, fingerprint

fp = fingerprint(html, title="Create a Case", top="How-To", tags=["procedure"])
code, why = classify(fp)
# ("T2", "procedural (ordered steps / action headings / imperative title)")
```

The two halves are separate on purpose. Fingerprinting parses HTML and is the slow
part; classifying is pure arithmetic over the result. Fingerprint your corpus once
to a JSON file, then re-run the rules against it as many times as you like. That
loop is the only reason the rules ever converged.

From the command line:

```bash
doctype classify docs/                      # table plus a type distribution
doctype classify docs/ --json               # machine-readable
doctype fingerprint docs/ -o fps.json       # cache the structural counts
doctype score fps.json labels.json          # accuracy, confusion matrix, per-type
doctype score fps.json labels.json --expect 123   # nonzero exit if it moved
doctype profile > my-profile.json           # dump the vocabulary, to edit
doctype --profile my-profile.json classify docs/
```

`--category-from-dir` uses each file's parent directory as its category, which is
usually what you want when your export mirrors the CMS hierarchy.

### Reachability from the CLI

The CLI reads files off a disk, and files on a disk have no CMS metadata. That
makes the command line strictly weaker than the library, in two ways worth knowing
before you conclude a rule is broken.

- **The CLI never supplies tags.** `doctype classify` and `doctype fingerprint`
  pass a title, a slug and optionally a category, and nothing else. Any rule whose
  only gate is a tag therefore cannot fire from the command line -- in the shipped
  profile that is the `imported` tag rule for T12. Rules where a tag is one of
  several alternatives (FAQ, overview, internal, release note) still fire on their
  title, heading or category half.
- **Without `--category-from-dir` there is no category, and three types become
  unreachable.** T5, T6 and T7 all live behind the release-note gate, and that gate
  opens on a release-note tag or a release-note category. With neither, the whole
  branch is skipped, so no file can classify as a release note or a rollup no
  matter what is in it. The same flag is what makes T4's config-category branch and
  T12's internal-category branch reachable.

With `--category-from-dir`, the parent directory name has to match a name in your
profile's category lists. Matching is exact after lowercasing and is not
hierarchical, so a directory named `Release Notes` matches the default profile and
a directory named `4.2 Release Notes` does not.

None of this applies to the library. `fingerprint(html, title=..., top=..., tags=...)`
takes all of it, so every rule is reachable from Python.

## The thirteen types

| Code | Type | What it looks like |
|---|---|---|
| T1 | Overview / Concept | prose, "Overview"/"About"/"What is" title, no ordered steps |
| T2 | Task / Procedure | imperative title, `ol` present, step-and-result, screenshots |
| T3 | Field / Screen Reference | Field \| Description table, no steps, screen-ish title |
| T4 | Config Instruction | metadata table, `Configuration Steps`, ALL_CAPS variable names |
| T5 | Release Note (canonical) | attribute table plus What's New / Why / Who headings |
| T6 | Release Note (legacy) | attribute table only, pre-schema wording |
| T7 | Index / Landing / Rollup | version title, no tables, high link count |
| T8 | API Spec | auth / endpoint / request / response headings, field tables |
| T9 | Code Sample / Payload | body is a payload *and* nothing is fenced -- see the note below |
| T10 | FAQ | `faq` tag, question headings, "Setup and FAQs" |
| T11 | Long-form Master Guide | over 15k characters with heavy sectioning |
| T12 | Internal / Non-content | engineering dump, raw import, runbook, template skeleton |
| STUB | Stub / empty | under 60 characters of text |

Longer signatures, and the checks each type should and should not attract, are in
[TAXONOMY.md](TAXONOMY.md).

T9 is narrower than its name. The rule requires `pre == 0`, so it is a detector for
an *unfenced* payload rather than for payloads in general: a code sample that is
correctly wrapped in `<pre>` or `<code>` never classifies as T9, and generally
lands on T8 instead because the same headings satisfy the API contract test. Read
T9 as "this is a payload and it is also a formatting defect". The rule keys on size
and on the payload vocabulary (`sample` in the title, or a heading like `Sample
Request` or `Payload`); it does not inspect the text for braces or attempt to parse
it as JSON, so prose over the size threshold under one of those headings will
match.

## How it decides

The types genuinely overlap. A release note is also a procedure. A long config
guide is also a master guide. There is no clean feature boundary, so resolution is
ordered: the most specific claim wins, and precedence is encoded as nothing more
than the order of the `if` statements in `classify()`. Read that function top to
bottom and you have read the entire specification. It is 185 lines including its
docstring, of which the `if` cascade itself is about 115.

Three orderings are load-bearing and each one cost accuracy to find:

- **Non-content before everything.** An engineering dump with ordered steps in it
  is not a how-to, it is something that should not have been published.
- **FAQ before API.** An integration page titled "Setup and FAQs" matches the API
  contract vocabulary and gets classified as a spec otherwise.
- **Config and master guide before procedure.** Both routinely contain ordered
  steps, and "has ordered steps" is a much weaker signal than "has a
  system-variable table" or "is 20,000 characters with nine sections".

Two rules are gated tighter than the bare category, and in both cases the gate is
looser than the intent behind it. Read them as written rather than as described.

**Config instruction.** The config category alone does not fire it -- but the config
category *plus a single ordered list* does, and so does one heading matching
`Configuration Steps` or `System Variable`, or two ALL_CAPS headings, anywhere in
the document regardless of category. The rationale for the gate was that ordered
steps filed under a config category are usually just a procedure, and the rule does
not actually enforce that: a plain how-to in the config category classifies as T4,
with a reason string naming a marker it does not have. There is no config *tag*
gate at all; the shipped profile has no `config_tags` field.

**API spec.** It requires the contract vocabulary and then any one of a field
table, a `pre` or `code` element, any table at all, or the substring `api` in the
title. That last alternative is the leak: the structural half was added because the
word "api" in prose swallowed every integration overview, and a page titled
"Partner API Integration Overview" with an `Authentication` heading and no table,
no list and no code block still classifies as T8 on the title alone.

## Accuracy: 84.2% training, with no held-out split

123 of 146. Before the provenance, the caveat that governs all of it: **that set
was not held out.** The rules were tuned over four rounds against those same 146
items, scoring the same set each round, so 84.2% is training accuracy and an
optimistic estimate of what the rules would do on documents they have never seen.
There is no held-out split, no cross-validation, and no second set. Nothing below
is a generalization figure.

**The label set.** 146 articles sampled from a 1,806-article enterprise knowledge
base, labeled by four independent LLM agents. Each agent read the real article
content, applied the written taxonomy, and never saw the classifier rules. Labels
were emitted per article with a confidence and a one-line justification. It served
as the tuning set and as the scoreboard at the same time, which is exactly the
thing you are told not to do.

**The tuning loop.** Four rounds. Each round: score, read the confusion matrix,
change one or two rules, re-score.

| Round | Accuracy | What changed |
|---|---|---|
| v0 | 67.1% | rules transcribed straight from the written taxonomy |
| v1 | 75.3% | config gated on more than the category alone; API gated on the contract vocabulary plus a second signal; FAQ moved above API; prose defaults to concept instead of reference |
| v2 | 82.2% | config and master guide moved above procedure; master guide keyed on size; action-verb headings win over field tables |
| v3 | **84.2%** | spec imports and marketing prose routed to non-content; two ALL_CAPS headings imply config |

**Where it is weak,** from the same run, and therefore also on the tuning set
rather than on held-out data: API spec precision is 50% (support 7),
master guide recall is 62% (support 8), stub recall is 71% (support 7). FAQ and
code sample are 100% on both, but code sample has a support of 1.

**Why I stopped at v3.** The remaining 23 misses are almost all one-count boundary
singletons, plus cases the labeling agents themselves marked low confidence
because two types plausibly fit. Editing rules to capture those would be fitting
the 146-item set, not improving the classifier.

### What that number is not

- **It is not a held-out or generalization figure.** Stated again here because it
  is the caveat most likely to be skipped: the 146 items were the tuning set. The
  honest reading of 84.2% is "the rules fit the set they were written against this
  well", and the true out-of-sample number is unknown and lower.
- **You cannot reproduce it from this repository.** The label set is real content
  from a private knowledge base, and neither the articles nor their slugs can be
  published. The test suite here asserts *rule behavior* on hand-built
  fingerprints, which is a different and weaker claim. If you want an accuracy
  figure for your corpus, label a sample of your own and run `doctype score`.
- **The ground truth is model output, not adjudicated by a human.** Four
  independent agents reading real content is a reasonable proxy and much better
  than one, but it is a proxy. Some of the 23 disagreements are probably the
  labels being wrong rather than the rules.
- **Per-type figures for the small types are anecdote.** Five of the thirteen
  types have a support under 10, and one has a support of 1.
- **It is one corpus.** 84.2% is this ruleset against that knowledge base. On a
  different knowledge base, with the shipped profile and no tuning, expect
  materially worse until you edit the profile.

The code in this repository was refactored out of the original working version
(the vocabulary was pulled out into a profile). That refactor was verified
behavior-identical: it produces the same classification for all 1,806 documents
and reproduces 123/146 with the same confusion matrix.

## Retargeting it to your knowledge base

Every literal string and threshold the rules match against lives in
`taxonomy.Profile`, not in the rules. That is deliberate. The first version had a
dozen strings baked in, and they were facts about one knowledge base rather than
facts about documentation.

```bash
doctype profile > my-profile.json
```

Edit, then pass `--profile my-profile.json`. Or in Python:

```python
from doctype import classify, Profile

german = Profile(
    release_note_categories=["Versionshinweise"],
    canonical_rn_headings=["was ist neu", "warum"],
).normalized()

classify(fp, german)
```

An unknown key raises rather than being ignored, because a typo'd key otherwise
leaves the rule it was meant to configure on its default and the accuracy drop has
no visible cause.

Start with these, in this order:

1. `release_note_categories`, `config_categories`, `internal_categories` and the
   `*_tags` lists. Your CMS's actual names. Nothing works until these are right.
2. `canonical_rn_headings`. Your release-note schema's section headings.
3. `screen_words`. The default includes `claims`, which is a healthcare noun and
   the clearest example of something to replace with your own domain's word for
   "a table users look at".
4. `fingerprint._is_field_table`. It looks for a bold first cell, which is an
   authoring convention rather than a standard. If your tool marks field tables
   differently, this is the one function to replace.

## Limitations

- **HTML only.** No Markdown, PDF or docx.
- **English vocabulary** in the shipped profile. The rules themselves are
  language-agnostic; the profile is not.
- **No confidence score.** A rule fires or it does not. Since the types genuinely
  overlap, a real number here would be useful and there isn't one.
- **The reason string is a rule name, not an explanation.** It tells you which
  rule fired, not which signal within a compound rule tipped it.
- **A short document is a stub regardless of structure**, because the stub test
  runs first. A 40-character page with a perfect field table classifies as STUB.
  That is intentional, and it will surprise you once.
- **Category and tag matching is exact** (case-insensitively) rather than
  hierarchical. If your CMS nests categories, pass the top-level name in `top`.
- **`fingerprint_many` swallows per-document errors** by design, so one bad
  document cannot abort a corpus sweep. Check for the `error` key before
  classifying: an errored fingerprint has no counts, every count reads as zero,
  and it will classify as STUB.

## Development

```bash
pip install -e ".[test]"
pytest -q          # 70 tests
```

The tests assert what each rule does, using minimal hand-built fingerprints so a
failure names the rule rather than a document. Two of them are regressions for
bugs made while writing this package: category names being compared against the
wrong casing, which silently killed the entire release-note branch for 41
documents and raised nothing; and tags being substring-matched, which made a tag
reading `not-faq` classify the document as an FAQ.

If you add a rule, add a minimal case for it and a precedence case showing what it
beats. Precedence is the design, so an untested ordering is an untested design.

## Background

Built while running documentation for a healthcare SaaS platform, where it drives
a type-aware corpus health scan over the 1,806 published articles described above.
The taxonomy was derived empirically from that corpus rather than designed up
front, which is why some of it looks oddly specific.

## License

MIT. See [LICENSE](LICENSE).
