# The taxonomy

Thirteen types. Derived empirically from 1,806 published articles in one
enterprise knowledge base, not designed up front, which is why a few of the
signatures look oddly specific. Roughly forty category-local types collapsed into
these once the overlaps were resolved.

Each document gets exactly one primary type. The types overlap in reality, so
detection is precedence-ordered rather than exclusive; see the bottom.

The right-hand column is the reason the taxonomy exists. The point was never to
label documents, it was to route them: run only the quality checks that fit the
type, and suppress the ones that will produce a false positive.

---

## T1 Overview / Concept

Prose by design. An "Overview", "Introduction", "About" or "What is" title, prose
sections, few or no ordered lists, at most one table.

- **Run:** accuracy and staleness, terminology consistency, orphan detection, voice.
- **Skip:** wall-of-text detection, stub detection, field-table integrity,
  screenshot freshness. A short concept page is not a broken how-to, and treating
  it as one was the single largest source of false positives in the original scan.

## T2 Task / Procedure

Imperative or CRUD title, at least one ordered list, action-and-result steps,
usually screenshots. May contain a field table for a dialog; that does not make it
a reference.

- **Shape:** optional intro, ordered steps, optional dialog field table, screenshots.
- **Run:** wall-of-text, step and result completeness, screenshot freshness,
  self-service readability, voice.

## T3 Field / Screen Reference

Table-first. A Field | Description table, no ordered steps, a title naming a UI
surface (tab, window, screen, fields).

- **Shape:** one orienting sentence, screenshot, one or more field tables.
- **Run:** table integrity, field-to-UI consistency, screenshot freshness.
- **Skip:** wall-of-text, step completeness.
- **Watch:** a role or permission matrix is not a field table. Applying field rules
  to one produces noise.

## T4 Config Instruction

The most structurally distinctive type. A metadata table at the top, explicit
configuration steps, and settings named in ALL_CAPS.

- **Shape:** metadata table (epic, release, solution area, document type, related
  release note), then configuration steps, then per-setting sections: the setting
  name as a heading, a Field | Value table before the steps, a stated result, a
  screenshot.
- **Run:** config format compliance, value accuracy, release gating, secret scan.
- **Note:** the intent is that this type is never detected from its category alone,
  because ordered steps filed under a config category are usually just a procedure
  and gating on the category floods the type with every how-to in it.
- **Note:** the implemented rule does not hold that line. The config category plus
  one ordered list is enough, which is the flood the previous note warns about: a
  plain how-to filed under the config category classifies here, and the reason
  string still names a marker the document does not have. Independently of category,
  one `Configuration Steps` or `System Variable` heading, or two ALL_CAPS headings,
  also fires it. There is no config *tag* gate; the profile has no `config_tags`
  field.

## T5 Release Note (canonical)

The target schema. An attribute table, then the standard sections.

- **Shape:** attribute table, enabled-by-default statement, What's New, Why It
  Matters, Who Is Impacted, optional sections, configuration last with an anchor.
- **Run:** schema conformance, quality scoring, config-block formatting, release gating.

## T6 Release Note (legacy)

Pre-schema. An attribute table carrying the content in fields like Business
Problem and Solution, with none of the canonical section headings.

- **Migration:** Business Problem maps to Why It Matters, Solution to What's New,
  Impacted to Who Is Impacted; add the enabled-by-default statement; move
  configuration to the end.
- **Note:** schema-nonconformant by definition. Do not report it as a schema
  failure, report it as migration backlog. Prioritize the oldest ones; they decay
  fastest.

## T7 Index / Landing / Rollup

Navigation, not content. A version-numbered or rollup title, no tables, a high
link count, sections grouped by product area.

- **Run:** link integrity, knowledge-graph position, naming consistency.
- **Skip:** schema checks, quality scoring, anything that assumes prose.

## T8 API Spec

An endpoint contract.

- **Shape:** purpose, authentication, endpoints, request fields as a table,
  response fields as a table, samples inside `<pre>`, error codes.
- **Run:** code fencing, field-table flattening, table integrity, secret scan.
  Real hostnames and keys turn up in this type more than any other.
- **Note:** the intent is that this requires the contract vocabulary *and*
  supporting structure, so that the word "api" appearing in prose reads as an
  integration overview rather than a spec. The implemented rule is looser: the
  second half is satisfied by a field table, a `pre` or `code` element, *any*
  table, **or** the substring `api` in the title. A prose page titled
  "Partner API Integration Overview" with an `Authentication` heading and no
  structure at all still lands here.

## T9 Code Sample / Payload

The body is the payload. Every sample belongs in `<pre>` or `<code>`.

- **Smoking gun:** no `pre` or `code` element, over 3,000 characters, and either a
  title beginning "Sample" or a heading like `Sample Request`, `Data Models`,
  `Payload` or `Bundle`. That is a code sample and also a formatting defect.
- **Run:** code fencing, wall-of-text.
- **Note:** the rule fires *only* when nothing is fenced. A payload that is
  correctly wrapped in `<pre>` or `<code>` never classifies here; it usually lands
  on T8, because the same headings satisfy the API contract test. So this type
  means "unfenced payload", not "payload".
- **Note:** the rule does not look at the text itself. It does not count braces or
  try to parse the body as JSON, so ordinary prose over the size threshold under one
  of those headings will match it.

## T10 FAQ

- **Shape:** topical section, question headings, short answers. The setup variant
  adds a pointer to the relevant configuration.
- **Run:** house style, self-service readability, cross-link validity.
- **Skip:** wall-of-text. Question-and-answer text legitimately has no ordered steps.

## T11 Long-form Master Guide

Over roughly 15,000 characters, multi-section, usually a config or reference guide
that grew.

- **Run:** wall-of-text at highest priority, section structure, whether it should
  be decomposed, screenshot freshness at scale.
- **Rule of thumb:** over 15,000 characters with two or fewer sections is a wall of
  text, and that is the highest-priority defect in the corpus.

## T12 Internal / Non-content

Should not be client-facing, and often should not be published at all. Several
distinct things that behave the same way for routing:

- **Engineering dump:** implementation plan, architecture summary, design
  decisions, test results, framework and tooling names as headings.
- **Raw import:** Word, spreadsheet or requirements-document paste. Table of
  contents, learning objectives, `Sheet:` headings. Usually huge, usually draft,
  frequently contains customer names, so this is the leak-critical case.
- **Support runbook:** trigger, background, fix, escalation. Internal by construction.
- **Template skeleton:** placeholder prose, empty. Not content, and must not be
  counted as content.
- **Product definition:** internal positioning and marketing prose.
- **Import artifact:** a UUID-shaped slug is a machine-generated duplicate.

- **Run:** secret scan at high priority, client-facing scope check, deduplication.
- **Skip:** voice, style, quality scoring. Triage promote-or-delete first; scoring a
  document that should be deleted is wasted effort.

## STUB

Under 60 characters of text. Empty or a placeholder.

The threshold is deliberately low. A *thin but real* page is a concept article, and
conflating the two generated more false "broken document" reports than any other
single mistake.

---

## Detection precedence

Resolve top down. The first match wins. This ordering *is* the specification, and
it is implemented as the order of the `if` statements in `classify()`.

1. **Empty.** Under the stub threshold. Nothing else matters.
2. **Internal / non-content.** Imported tag, UUID slug, raw-import headings,
   engineering headings or slug markers, runbook, internal category, spec import,
   marketing prose, template skeleton. Before everything, because an engineering
   dump containing ordered steps is not a how-to.
3. **Release notes.** A closed universe: if the document carries the release-note
   tag or sits in the release-note category, it is exactly one of four things.
   Version or rollup title gives T7; canonical section headings give T5; an
   attribute table gives T6; prose with no table at all is really a concept page,
   T1. Nothing outside that gate can reach T5, T6 or T7 at all, which matters from
   the command line: `doctype` supplies no tags, so those three types need
   `--category-from-dir` and a directory named for your release-note category.
4. **FAQ.** Before API, because an integration FAQ matches the API vocabulary.
5. **API, then unfenced payload.**
6. **Config instruction.** Never on the category alone, but the category plus one
   ordered list is enough. See the two notes under T4.
7. **Long-form master.** Before procedure, because masters contain steps.
8. **Procedure.** Ordered steps, action-verb headings, or an imperative title.
9. **Field / screen reference.** A field table with no steps, or a table plus a
   screen-ish title.
10. **Overview / concept.**
11. **Fallthrough.** Prose defaults to concept, not to reference: an unstructured
    page is far more often a short explanation than a broken table. Anything
    structured that got this far defaults to reference.
