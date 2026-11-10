# Design notes

Why the rules look like this. What they do is in [Rules](rules.md). The codes are in [Types](types.md). The five-file transcript in the [README](../README.md) is not the measurement below.

## Problem

I was running a knowledge base of 1,806 published articles and wanted a quality scan over all of them. The first version applied every check to every article. Nearly every false positive came from that:

- A short concept page was flagged as a truncated how-to.
- A role matrix was flagged as a malformed field table.
- A link index was flagged as an article with no content.

The scan became usable once it classified the document first, ran only the checks that fit the type, and suppressed the rest. That turns a pile of findings into a list a writer can act on.

The type has to be explainable to the person whose article was flagged. "This fired because the heading `Configuration Steps` is present" is an argument. When the call is wrong, you can read the rule that misfired and edit that one rule.

## What 84.2% measures

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

The code in this repository was refactored out of that working copy: the vocabulary moved into a profile. The refactor was checked to classify all 1,806 documents the same way and to reproduce 123/146 with the same confusion matrix. The tests in this repository do not, and cannot, repeat that check. They assert rule behavior on hand-built fingerprints. For a figure on your own export, label a sample and run `doctype score`. There is no labels file in this repository. How score reads one is in [Rules](rules.md#score).

With the shipped profile and no tuning, a different knowledge base will score worse until the category names, tags, and headings match yours.

## Tests

```bash
pip install -e ".[test]"
pytest -q
```

That is 70 passed on this tree. The tests assert rule behavior on minimal fingerprints: exactly the signals one rule needs, so a failure names the rule. One parametrized case produces every code in `TYPES`. A second test fails if a code is added to the dict and left out of that list. Precedence has its own cases, including FAQ before API, config and the master guide before procedure, non-content before a how-to, and stub before an `imported` tag.

Three regressions are locked:

- Category names were compared in the CMS's original casing. The profile lowercases its lists on load, so the comparison missed, the release-note branch never opened, 41 documents fell through to other types, and nothing raised.
- Tags were matched as substrings. A tag `not-faq` classified the page as an FAQ.
- Compiled patterns were cached in a dict keyed by `id()`. After garbage collection, one profile could receive another profile's patterns.

[`.github/workflows/test.yml`](../.github/workflows/test.yml) runs `pytest` on every push and pull request to `main` or `master`, on Python 3.10, 3.11, and 3.12. The package allows 3.9 and up; the workflow does not install 3.9.

These tests are not the 84.2% measurement. A labeled corpus has to be yours. `doctype score --expect` is how you pin a number you computed yourself.

## Provenance

I built this while running documentation for a healthcare SaaS platform. It is the routing step in front of a type-aware scan of those 1,806 articles. The taxonomy was derived from that corpus, which is why a few signatures are specific to it: `claims` as a screen, Jira-epic rows as config metadata, `CDS Hooks` in the API heading list. Those strings are profile data so they can be replaced without forking the rules.
