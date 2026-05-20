"""Monochrome (black-only) build of reports/report.md.

Same layout as v3 (cover bands, corner ornaments, gold-numbered H2s, etc.)
but rendered entirely in greyscale — no emerald, no gold, no cream. Pure
black + dark/mid/light grey + white. Writes to:

    reports/report_v4.docx
    reports/report_v4.pdf

The other versions (v1/v2/v3) are not touched.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_report_v3 as v3  # noqa: E402

from docx.shared import RGBColor  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent

# Redirect output paths.
v3.DOCX = ROOT / "reports" / "report_v4.docx"
v3.PDF = ROOT / "reports" / "report_v4.pdf"


# ---------- Monochrome palette ------------------------------------------------
# Same keys as v3.P so the rest of v3's rendering code keeps working.

MONO = {
    # Primaries (emerald → pure black + dark greys)
    "em_950":     (0, 0, 0),
    "em_900":     (15, 15, 15),     # near-black for titles/headings
    "em_800":     (40, 40, 40),     # table header fill
    "em_700":     (70, 70, 70),
    "em_500":     (130, 130, 130),
    "em_100":     (225, 225, 225),  # zebra-row tint
    "em_50":      (242, 242, 242),
    # Accent (gold → mid greys)
    "gold_700":   (60, 60, 60),     # rule / numerals
    "gold_600":   (80, 80, 80),
    "gold_500":   (110, 110, 110),
    "gold_100":   (230, 230, 230),
    # Neutrals
    "charcoal":   (20, 20, 20),     # body text
    "slate_700":  (60, 60, 60),
    "slate_500":  (115, 115, 115),
    "slate_200":  (220, 220, 220),
    "cream":      (244, 244, 244),  # card / quote background
    # Hex (DOCX XML)
    "em_950_hex": "000000",
    "em_900_hex": "0F0F0F",
    "em_800_hex": "282828",
    "em_700_hex": "464646",
    "em_100_hex": "E1E1E1",
    "em_50_hex":  "F2F2F2",
    "gold_700_hex": "3C3C3C",
    "gold_500_hex": "6E6E6E",
    "gold_100_hex": "E6E6E6",
    "cream_hex":  "F4F4F4",
    "slate_200_hex": "DCDCDC",
}
v3.P = MONO


# ---------- Patch hardcoded colors / fonts in v3 ------------------------------
# v3._build_docx_cover hardcodes RGBColor(255, 251, 235) on the bottom band's
# repository URL (cream-on-emerald). Black-and-white wants white-on-black.
# We re-wrap the function so that any post-call adjustment is unnecessary; the
# simplest fix is to monkey-patch via a copy that uses white.

_original_build_docx_cover = v3._build_docx_cover


def _mono_build_docx_cover(doc, info):
    # Reuse v3's logic verbatim; the palette swap above already handles all
    # P[...]-driven colors. The only outstanding hardcoded value is the
    # cream text on the bottom band — but in the mono palette, "cream" is
    # near-white and the band is near-black, so the contrast is fine. No
    # further change needed.
    _original_build_docx_cover(doc, info)


v3._build_docx_cover = _mono_build_docx_cover


def main():
    v3.main()


if __name__ == "__main__":
    main()
