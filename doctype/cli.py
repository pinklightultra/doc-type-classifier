"""Command line interface: classify documents, and score the rules against labels.

    doctype classify docs/                     # what type is each of these?
    doctype fingerprint docs/ -o fps.json      # cache the structural counts
    doctype score fps.json labels.json         # how good are the rules?

``score`` is the more interesting half. The rules in this package were tuned by
running it, reading the confusion matrix, editing one rule, and running it again;
without a scoring loop you are just guessing which rule to change next.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from .classify import classify
from .fingerprint import fingerprint
from .taxonomy import DEFAULT_PROFILE, TYPES, Profile

HTML_SUFFIXES = (".html", ".htm")


def _iter_html(paths: Sequence[str]) -> Iterable[str]:
    """Expand files and directories into a sorted list of HTML paths."""
    for path in paths:
        if os.path.isdir(path):
            for root, _dirs, files in os.walk(path):
                for name in sorted(files):
                    if name.lower().endswith(HTML_SUFFIXES):
                        yield os.path.join(root, name)
        else:
            yield path


def _read(path: str) -> str:
    # Authoring tools emit UTF-8 with and without a BOM, and mixed encodings inside
    # one export are normal. Never let one unreadable byte abort a corpus sweep.
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        return fh.read()


def _title_from(path: str) -> str:
    """Fall back to a humanized filename. Several rules key on the title, so an
    empty one measurably costs accuracy; a slug-shaped guess beats nothing."""
    stem = os.path.splitext(os.path.basename(path))[0]
    return stem.replace("-", " ").replace("_", " ").strip()


def _fingerprint_paths(paths: Sequence[str], root_as_category: bool) -> List[Dict[str, Any]]:
    out = []
    for path in _iter_html(paths):
        slug = os.path.splitext(os.path.basename(path))[0]
        top = os.path.basename(os.path.dirname(os.path.abspath(path))) if root_as_category else ""
        out.append(
            fingerprint(
                _read(path),
                title=_title_from(path),
                slug=slug,
                top=top,
                extra={"path": path},
            )
        )
    return out


def _load_profile(path: Optional[str]) -> Profile:
    return DEFAULT_PROFILE if not path else Profile.load(path).normalized()


def _load_labels(path: str) -> Dict[str, str]:
    """Accepts a bare list of ``{slug,label}``, or a ``{"labels": [...]}`` wrapper,
    or a flat ``{slug: label}`` mapping."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if isinstance(doc, Mapping) and "labels" in doc:
        doc = doc["labels"]
    if isinstance(doc, Mapping):
        return {str(k): str(v) for k, v in doc.items()}
    return {r["slug"]: r["label"] for r in doc}


# ----------------------------------------------------------------- subcommands
def cmd_classify(args: argparse.Namespace) -> int:
    profile = _load_profile(args.profile)
    fps = _fingerprint_paths(args.paths, args.category_from_dir)
    if not fps:
        print("no HTML files found", file=sys.stderr)
        return 1

    rows = []
    for fp in fps:
        code, why = classify(fp, profile)
        rows.append({"path": fp.get("path", ""), "slug": fp.get("slug", ""),
                     "type": code, "name": TYPES.get(code, "?"), "reason": why,
                     "chars": fp.get("chars", 0)})

    if args.json:
        json.dump(rows, sys.stdout, indent=1)
        sys.stdout.write("\n")
        return 0

    width = min(60, max((len(r["slug"]) for r in rows), default=10))
    for r in rows:
        print(f"  {r['slug'][:width]:{width}}  {r['type']:5} {r['name'][:24]:24}  {r['reason']}")
    print()
    for code, n in collections.Counter(r["type"] for r in rows).most_common():
        print(f"  {n:5}  {code:5} {TYPES.get(code, '?')}")
    print(f"  {len(rows):5}  total")
    return 0


def cmd_fingerprint(args: argparse.Namespace) -> int:
    fps = _fingerprint_paths(args.paths, args.category_from_dir)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(fps, fh, indent=1)
    print(f"wrote {args.out}: {len(fps)} fingerprints")
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    profile = _load_profile(args.profile)
    with open(args.fingerprints, encoding="utf-8") as fh:
        fps = {r["slug"]: r for r in json.load(fh) if not r.get("error")}
    labels = _load_labels(args.labels)

    rows = []
    for slug in sorted(labels):
        if slug in fps:
            pred, why = classify(fps[slug], profile)
            rows.append((slug, pred, labels[slug], why))
    if not rows:
        print("no labeled slug appears in the fingerprints; wrong pair of inputs?",
              file=sys.stderr)
        return 1

    correct = sum(1 for _, p, y, _ in rows if p == y)
    n = len(rows)
    missing = len(labels) - n
    print(f"labeled: {len(labels)}  scored: {n}  accuracy: {correct}/{n} = {correct/n:.1%}")
    if missing:
        print(f"  ({missing} labeled slugs absent from the fingerprints -- stale cache?)")

    conf = collections.Counter((p, y) for _, p, y, _ in rows if p != y)
    if conf:
        print("\n=== disagreements (predicted -> true : count) ===")
        for (p, y), c in conf.most_common():
            print(f"  {c:3}  {p:5} -> {y:5}")

    print("\n=== per type (support / recall / precision) ===")
    for t in sorted({y for _, _, y, _ in rows} | {p for _, p, _, _ in rows}):
        sup = sum(1 for _, _, y, _ in rows if y == t)
        tp = sum(1 for _, p, y, _ in rows if y == t and p == t)
        pp = sum(1 for _, p, _, _ in rows if p == t)
        print(f"  {t:5} sup={sup:3} recall={tp/sup if sup else 0:.0%} "
              f"precision={tp/pp if pp else 0:.0%}")

    if args.detail:
        print("\n=== misclassified ===")
        for slug, p, y, why in rows:
            if p != y:
                print(f"  {slug[:45]:45} pred {p:5} / true {y:5}  [{why[:44]}]")

    if args.expect is not None and correct != args.expect:
        print(f"\nREGRESSION: expected {args.expect}/{n}, got {correct}/{n}", file=sys.stderr)
        return 1
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    """Dump the active profile, so you have something to edit rather than invent."""
    profile = _load_profile(args.profile)
    data = {k: v for k, v in profile.to_dict().items()}
    json.dump(data, sys.stdout, indent=1)
    sys.stdout.write("\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="doctype", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", help="profile JSON (default: the shipped profile)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("classify", help="classify HTML files or directories")
    c.add_argument("paths", nargs="+")
    c.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    c.add_argument("--category-from-dir", action="store_true",
                   help="use each file's parent directory name as its category")
    c.set_defaults(func=cmd_classify)

    f = sub.add_parser("fingerprint", help="write structural fingerprints to JSON")
    f.add_argument("paths", nargs="+")
    f.add_argument("-o", "--out", default="fingerprints.json")
    f.add_argument("--category-from-dir", action="store_true")
    f.set_defaults(func=cmd_fingerprint)

    s = sub.add_parser("score", help="score the rules against ground-truth labels")
    s.add_argument("fingerprints", help="JSON from `doctype fingerprint`")
    s.add_argument("labels", help="JSON: [{slug,label}], {labels:[...]}, or {slug: label}")
    s.add_argument("--detail", action="store_true", help="list every misclassification")
    s.add_argument("--expect", type=int, metavar="N",
                   help="exit nonzero unless exactly N are correct (for CI / regression)")
    s.set_defaults(func=cmd_score)

    p = sub.add_parser("profile", help="dump the active profile as JSON, to edit")
    p.set_defaults(func=cmd_profile)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
