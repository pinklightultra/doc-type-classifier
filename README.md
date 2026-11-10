# doc-type-classifier

`doctype` reads one HTML documentation page and returns one of thirteen structural types, plus the name of the rule that fired.

![Classifying the sample docs, then explaining one file](docs/demo/demo.gif)

Re-record it from the repo root with `vhs docs/demo/demo.tape`.

It is for technical writers and docs engineers who have a directory of exported articles and need to route quality checks by document shape.

There is no model and no training step. There is no confidence score. A rule matches or it does not. Overlapping types are resolved by order, not by a margin. When the call is wrong, you can read the rule that misfired and edit that one rule.

## Quickstart

Python 3.9 or newer. The only runtime dependency is BeautifulSoup, and it is used to count tags.

```bash
git clone https://github.com/pinklightultra/doc-type-classifier
cd doc-type-classifier
pip install -e .
```

That puts `doctype` on your path. This repository is the distribution; `pyproject.toml` has no package-index metadata.

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

The five files in [`examples/docs/`](examples/docs) are synthetic fixtures written to land on five different types. They demonstrate the command. They are not an accuracy set. Filenames inside a directory are sorted. Directory order follows the filesystem walk, so another machine may print the same five rows in a different order. The type on each file stays the same. The summary lists types in the order they were first seen, because every count is 1.

`--category-from-dir` is load-bearing for the T7 row. The flag sets each file's category to the name of its parent directory, and `Release Notes` is a name in the shipped profile. Drop the flag and `2.4-release-notes` is T1, `prose fallthrough -> concept`. The other four rows stay. Why the flag changes that one row, and what else the command line cannot see, is in [Rules](docs/rules.md).

## Documentation

- [Types](docs/types.md) — the thirteen codes, and the checks each type should attract or suppress.
- [Rules](docs/rules.md) — the fingerprint, the order the rules run in, and the command line.
- [Limitations](docs/limitations.md) — what a result does not mean. There is no confidence score.
- [Design notes](docs/design.md) — why the rules exist, and what 84.2% measures.

## License

MIT. See [LICENSE](LICENSE).
