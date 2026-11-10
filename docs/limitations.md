# Limitations

[doc-type-classifier](../README.md) returns a type and the name of the rule that fired. It does not return a margin.

- **HTML only.** The CLI reads `.html` and `.htm`. There is no Markdown, PDF, or docx reader.
- **The shipped vocabulary is English.** Lists and thresholds move with the profile. The words `bundle` and `template` do not; they are in the rules. See [Rules](rules.md#two-title-words-are-not-profile-fields).
- **No confidence score.** A rule matches or it does not. Overlapping types are resolved by order, not by a margin.
- **The reason names the rule.** For T4, T8, and the other compound conditions, it does not identify the clause.
- **Under 60 characters is STUB, whatever the structure.** A 40-character page with a perfect field table is a stub. The threshold is deliberately low. A thin but real page is a concept article, and calling those pages empty produced more false "broken document" reports than any other single check in the original scan.
- **Category and tag matching is exact** after lowercasing. Nested CMS categories need the top-level name passed as `top`.
- **Heading text stops at twenty.** A phrase that first appears on heading 21 cannot fire. The numeric heading counts still include it.
- **One bad document does not stop a corpus sweep.** The CLI replaces undecodable bytes. `fingerprint_many` records `error` and continues. Classify that record only after you have handled the error, or it will come back STUB.
