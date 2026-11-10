# Types

The thirteen codes are fixed in `doctype.taxonomy.TYPES`. Changing that dict changes what the classifier is for. How they are ordered is in [Rules](rules.md#precedence). The [README](../README.md) shows one command.

The table is what the rule keys on. Thresholds are the shipped profile (`stub_max_chars` 60, `code_sample_min_chars` 3000, `master_min_chars` 15000, `index_min_links` 15, and the master-guide structure minimums). They are profile fields.

The type names describe the corpus the taxonomy was collapsed from: roughly forty category-local types in a 1,806-article base, reduced to one primary type per document. Where the type name and the `if` disagree, the `if` is the behavior. That happens in T4, T8, and T9.

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

The longer signatures follow. The point was never to label documents. It was to route them: run only the quality checks that fit the type, and suppress the ones that will produce a false positive.

## T1 Overview / Concept

Prose by design. An "Overview", "Introduction", "About" or "What is" title, prose sections, few or no ordered lists, at most one table.

- **Run:** accuracy and staleness, terminology consistency, orphan detection, voice.
- **Skip:** wall-of-text detection, stub detection, field-table integrity, screenshot freshness. A short concept page is not a broken how-to, and treating it as one was the single largest source of false positives in the original scan.

## T2 Task / Procedure

Imperative or CRUD title, at least one ordered list, action-and-result steps, usually screenshots. May contain a field table for a dialog; that does not make it a reference.

- **Shape:** optional intro, ordered steps, optional dialog field table, screenshots.
- **Run:** wall-of-text, step and result completeness, screenshot freshness, self-service readability, voice.

## T3 Field / Screen Reference

Table-first. A Field | Description table, no ordered steps, a title naming a UI surface (tab, window, screen, fields).

- **Shape:** one orienting sentence, screenshot, one or more field tables.
- **Run:** table integrity, field-to-UI consistency, screenshot freshness.
- **Skip:** wall-of-text, step completeness.
- **Watch:** a role or permission matrix is not a field table. Applying field rules to one produces noise.

## T4 Config Instruction

The most structurally distinctive type. A metadata table at the top, explicit configuration steps, and settings named in ALL_CAPS.

- **Shape:** metadata table (epic, release, solution area, document type, related release note), then configuration steps, then per-setting sections: the setting name as a heading, a Field | Value table before the steps, a stated result, a screenshot.
- **Run:** config format compliance, value accuracy, release gating, secret scan.
- **Note:** the intent is that this type is never detected from its category alone, because ordered steps filed under a config category are usually just a procedure and gating on the category floods the type with every how-to in it.
- **Note:** the implemented rule does not hold that line. The config category alone does not match, which the tests lock. The config category plus one ordered list does match, and so does one config-step heading (`Configuration Steps`, `System Variable`, or `Configuration SQL`), or two headings whose whole text matches `^[A-Z][A-Z0-9_]{5,}$` (six characters or more), in any category. One such heading is not enough on its own. A plain how-to filed under the config category classifies as T4. The reason string still says `config instruction (metadata / system-variable / config-steps marker)` when the document has none of those markers. There is no config tag gate; the profile has no `config_tags` field.

## T5 Release Note (canonical)

The target schema. An attribute table, then the standard sections.

- **Shape:** attribute table, enabled-by-default statement, What's New, Why It Matters, Who Is Impacted, optional sections, configuration last with an anchor.
- **Run:** schema conformance, quality scoring, config-block formatting, release gating.

## T6 Release Note (legacy)

Pre-schema. An attribute table carrying the content in fields like Business Problem and Solution, with none of the canonical section headings.

- **Migration:** Business Problem maps to Why It Matters, Solution to What's New, Impacted to Who Is Impacted; add the enabled-by-default statement; move configuration to the end.
- **Note:** schema-nonconformant by definition. Do not report it as a schema failure, report it as migration backlog. Prioritize the oldest ones; they decay fastest.

## T7 Index / Landing / Rollup

Navigation, not content. A version-numbered or rollup title, no tables, a high link count, sections grouped by product area.

- **Run:** link integrity, knowledge-graph position, naming consistency.
- **Skip:** schema checks, quality scoring, anything that assumes prose.

## T8 API Spec

An endpoint contract.

- **Shape:** purpose, authentication, endpoints, request fields as a table, response fields as a table, samples inside `<pre>`, error codes.
- **Run:** code fencing, field-table flattening, table integrity, secret scan. Real hostnames and keys turn up in this type more than any other.
- **Note:** the intent is that this requires the contract vocabulary *and* supporting structure, so that the word "api" appearing in prose reads as an integration overview rather than a spec. The implemented rule is looser. The contract vocabulary has to appear in a heading. The other half is then a field table, a `pre` or `code` element, any table, or the substring `api` in the title. A page titled "Partner API Integration Overview" with an `Authentication` heading and no table, list, or code block classifies as T8.

## T9 Code Sample / Payload

The body is the payload. Every sample belongs in `<pre>` or `<code>`.

- **Smoking gun:** no `pre` or `code` element, over 3,000 characters, and either a title beginning "Sample" or a heading like `Sample Request`, `Data Models`, `Payload` or `Bundle`. That is a code sample and also a formatting defect.
- **Run:** code fencing, wall-of-text.
- **Note:** T9 fires only on an unfenced payload. `pre` must be 0. A sample wrapped in `<pre>` or `<code>` never classifies as T9; those headings usually satisfy the API rule and land on T8. The rule does not look for braces and does not parse the body as JSON. Prose past the size threshold under a `Payload` heading matches. So this type means "unfenced payload", not "payload".

## T10 FAQ

- **Shape:** topical section, question headings, short answers. The setup variant adds a pointer to the relevant configuration.
- **Run:** house style, self-service readability, cross-link validity.
- **Skip:** wall-of-text. Question-and-answer text legitimately has no ordered steps.

## T11 Long-form Master Guide

Over roughly 15,000 characters, multi-section, usually a config or reference guide that grew.

- **Run:** wall-of-text at highest priority, section structure, whether it should be decomposed, screenshot freshness at scale.
- **Rule of thumb:** over 15,000 characters with two or fewer sections is a wall of text, and that is the highest-priority defect in the corpus.

## T12 Internal / Non-content

Should not be client-facing, and often should not be published at all. Several distinct things that behave the same way for routing:

- **Engineering dump:** implementation plan, architecture summary, design decisions, test results, framework and tooling names as headings.
- **Raw import:** Word, spreadsheet or requirements-document paste. Table of contents, learning objectives, `Sheet:` headings. Usually huge, usually draft, frequently contains customer names, so this is the leak-critical case.
- **Support runbook:** trigger, background, fix, escalation. Internal by construction.
- **Template skeleton:** placeholder prose, empty. Not content, and must not be counted as content.
- **Product definition:** internal positioning and marketing prose.
- **Import artifact:** a UUID-shaped slug is a machine-generated duplicate.

- **Run:** secret scan at high priority, client-facing scope check, deduplication.
- **Skip:** voice, style, quality scoring. Triage promote-or-delete first; scoring a document that should be deleted is wasted effort.

## STUB

Under 60 characters of text. Empty or a placeholder.

The threshold is deliberately low. A *thin but real* page is a concept article, and conflating the two generated more false "broken document" reports than any other single mistake.
