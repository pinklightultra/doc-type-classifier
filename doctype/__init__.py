"""doc-type-classifier: tell documentation types apart by structure alone.

    from doctype import classify, fingerprint

    fp = fingerprint(html, title="Create a Case", top="How-To")
    code, why = classify(fp)      # ("T2", "procedural (ordered steps / ...)")

``classify`` needs no HTML and no network -- it reads a dict of counts. That split
is what makes the rules cheap to tune: fingerprint a corpus once, then iterate.
"""

from .classify import TYPES, classify
from .fingerprint import fingerprint, fingerprint_many, soup, text_only
from .taxonomy import DEFAULT_PROFILE, Profile

__version__ = "1.0.0"

__all__ = [
    "classify",
    "fingerprint",
    "fingerprint_many",
    "soup",
    "text_only",
    "Profile",
    "DEFAULT_PROFILE",
    "TYPES",
    "__version__",
]
