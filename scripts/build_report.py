"""Convert reports/report.md into reports/report.docx and reports/report.pdf.

Self-contained — relies only on python-docx and fpdf2, both pure-Python.

Supports:
- Headings (#, ##, ###)
- Paragraphs with inline **bold**, *italic*, `code`, [link](url)
- Tables (| col | col |)
- Code blocks (``` ... ```)
- Bulleted (-) and numbered (1.) lists
- Blockquotes (> ...)
- Horizontal rules (---)
- Math blocks ($$ ... $$) and inline math ($ ... $) rendered as italic text
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.shared import Inches, Pt, RGBColor
from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
MD = ROOT / "reports" / "report.md"
DOCX = ROOT / "reports" / "report.docx"
PDF = ROOT / "reports" / "report.pdf"

ARIAL_REG = r"C:\Windows\Fonts\arial.ttf"
ARIAL_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
ARIAL_IT = r"C:\Windows\Fonts\ariali.ttf"
ARIAL_BI = r"C:\Windows\Fonts\arialbi.ttf"
CONSOLAS = r"C:\Windows\Fonts\consola.ttf"


# ---------- Markdown parsing ---------------------------------------------------

BLOCK_RE = {
    "h1": re.compile(r"^# (.+)"),
    "h2": re.compile(r"^## (.+)"),
    "h3": re.compile(r"^### (.+)"),
    "hr": re.compile(r"^---+$"),
    "code_fence": re.compile(r"^```(\w*)$"),
    "ul": re.compile(r"^(\s*)- (.+)"),
    "ol": re.compile(r"^(\s*)\d+\. (.+)"),
    "quote": re.compile(r"^> (.+)"),
    "table_row": re.compile(r"^\|.*\|\s*$"),
    "table_sep": re.compile(r"^\|[\s\-:|]+\|\s*$"),
    "math_block": re.compile(r"^\$\$"),
}


def parse(md_text: str):
    """Yield (kind, payload) blocks."""
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]

        if BLOCK_RE["h1"].match(line):
            yield ("h1", BLOCK_RE["h1"].match(line).group(1))
            i += 1
        elif BLOCK_RE["h2"].match(line):
            yield ("h2", BLOCK_RE["h2"].match(line).group(1))
            i += 1
        elif BLOCK_RE["h3"].match(line):
            yield ("h3", BLOCK_RE["h3"].match(line).group(1))
            i += 1
        elif BLOCK_RE["hr"].match(line):
            yield ("hr", None)
            i += 1
        elif BLOCK_RE["code_fence"].match(line):
            buf = []
            i += 1
            while i < len(lines) and not BLOCK_RE["code_fence"].match(lines[i]):
                buf.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            yield ("code", "\n".join(buf))
        elif BLOCK_RE["math_block"].match(line):
            stripped = line.strip()
            # Single-line case: $$ expr $$
            if stripped.endswith("$$") and len(stripped) > 4:
                yield ("math", stripped[2:-2].strip())
                i += 1
            else:
                buf = []
                i += 1
                while i < len(lines) and not BLOCK_RE["math_block"].match(lines[i]):
                    buf.append(lines[i])
                    i += 1
                i += 1
                yield ("math", "\n".join(buf))
        elif BLOCK_RE["table_row"].match(line):
            rows = []
            while i < len(lines) and BLOCK_RE["table_row"].match(lines[i]):
                if BLOCK_RE["table_sep"].match(lines[i]):
                    i += 1
                    continue
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            yield ("table", rows)
        elif BLOCK_RE["ul"].match(line):
            items = []
            while i < len(lines) and BLOCK_RE["ul"].match(lines[i]):
                items.append(BLOCK_RE["ul"].match(lines[i]).group(2))
                i += 1
            yield ("ul", items)
        elif BLOCK_RE["ol"].match(line):
            items = []
            while i < len(lines) and BLOCK_RE["ol"].match(lines[i]):
                items.append(BLOCK_RE["ol"].match(lines[i]).group(2))
                i += 1
            yield ("ol", items)
        elif BLOCK_RE["quote"].match(line):
            items = []
            while i < len(lines) and BLOCK_RE["quote"].match(lines[i]):
                items.append(BLOCK_RE["quote"].match(lines[i]).group(1))
                i += 1
            yield ("quote", " ".join(items))
        elif line.strip() == "":
            i += 1
        else:
            # Paragraph — gather consecutive non-empty, non-block lines
            buf = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not any(
                BLOCK_RE[k].match(lines[i])
                for k in ("h1", "h2", "h3", "hr", "code_fence", "ul", "ol", "quote", "table_row", "math_block")
            ):
                buf.append(lines[i])
                i += 1
            yield ("p", " ".join(buf))


# ---------- Inline parsing -----------------------------------------------------

# tokenizer: yields (style_set, text) where style_set is a frozenset of {"bold","italic","code","link"}
INLINE_RE = re.compile(
    r"(\*\*[^*]+\*\*)|"           # bold
    r"(`[^`]+`)|"                 # code
    r"(\*[^*\n]+\*)|"             # italic
    r"(\[[^\]]+\]\([^)]+\))|"     # link
    r"(\$[^$\n]+\$)"              # inline math (treated as italic)
)


def inline_tokens(text: str):
    """Yield (kind, content) tokens from inline-formatted text."""
    pos = 0
    for m in INLINE_RE.finditer(text):
        if m.start() > pos:
            yield ("plain", text[pos : m.start()])
        token = m.group(0)
        if token.startswith("**"):
            yield ("bold", token[2:-2])
        elif token.startswith("`"):
            yield ("code", token[1:-1])
        elif token.startswith("*"):
            yield ("italic", token[1:-1])
        elif token.startswith("["):
            inner = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token)
            yield ("link", (inner.group(1), inner.group(2)))
        elif token.startswith("$"):
            yield ("italic", token[1:-1])  # render math as italic
        pos = m.end()
    if pos < len(text):
        yield ("plain", text[pos:])


# ---------- DOCX rendering -----------------------------------------------------

def render_runs_docx(paragraph, text: str):
    for kind, content in inline_tokens(text):
        if kind == "link":
            label, _url = content
            r = paragraph.add_run(label)
            r.font.color.rgb = RGBColor(0x0B, 0x57, 0xD0)
            r.underline = True
        elif kind == "bold":
            paragraph.add_run(content).bold = True
        elif kind == "italic":
            paragraph.add_run(content).italic = True
        elif kind == "code":
            r = paragraph.add_run(content)
            r.font.name = "Consolas"
            r.font.size = Pt(10)
        else:
            paragraph.add_run(content)


def build_docx(blocks):
    doc = Document()
    # Tighten default font / margins
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(11)

    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)

    for kind, payload in blocks:
        if kind == "h1":
            p = doc.add_heading(level=0)
            render_runs_docx(p, payload)
        elif kind == "h2":
            p = doc.add_heading(level=1)
            render_runs_docx(p, payload)
        elif kind == "h3":
            p = doc.add_heading(level=2)
            render_runs_docx(p, payload)
        elif kind == "p":
            p = doc.add_paragraph()
            render_runs_docx(p, payload)
        elif kind == "ul":
            for item in payload:
                p = doc.add_paragraph(style="List Bullet")
                render_runs_docx(p, item)
        elif kind == "ol":
            for item in payload:
                p = doc.add_paragraph(style="List Number")
                render_runs_docx(p, item)
        elif kind == "quote":
            p = doc.add_paragraph(style="Intense Quote")
            render_runs_docx(p, payload)
        elif kind == "code":
            p = doc.add_paragraph()
            r = p.add_run(payload)
            r.font.name = "Consolas"
            r.font.size = Pt(9)
        elif kind == "math":
            p = doc.add_paragraph()
            r = p.add_run(payload)
            r.italic = True
            r.font.name = "Cambria Math"
        elif kind == "hr":
            p = doc.add_paragraph("_" * 70)
            p.alignment = 1  # center
        elif kind == "table":
            if not payload:
                continue
            n_cols = max(len(r) for r in payload)
            tbl = doc.add_table(rows=len(payload), cols=n_cols)
            tbl.style = "Light Grid Accent 1"
            for r_idx, row in enumerate(payload):
                for c_idx, cell_text in enumerate(row):
                    cell = tbl.cell(r_idx, c_idx)
                    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                    cell.text = ""
                    p = cell.paragraphs[0]
                    render_runs_docx(p, cell_text)
                    if r_idx == 0:
                        for run in p.runs:
                            run.bold = True
            doc.add_paragraph()  # spacer after table

    doc.save(DOCX)
    print(f"wrote {DOCX} ({DOCX.stat().st_size/1024:.1f} KB)")


# ---------- PDF rendering ------------------------------------------------------

class ReportPDF(FPDF):
    def __init__(self):
        super().__init__(format="A4")
        self.set_margins(20, 18, 20)
        self.set_auto_page_break(True, margin=18)
        # Embed Arial so we get full unicode
        self.add_font("Arial", "", ARIAL_REG, uni=True)
        self.add_font("Arial", "B", ARIAL_BOLD, uni=True)
        self.add_font("Arial", "I", ARIAL_IT, uni=True)
        self.add_font("Arial", "BI", ARIAL_BI, uni=True)
        self.add_font("Mono", "", CONSOLAS, uni=True)
        self.set_font("Arial", "", 11)

    def add_inline(self, text: str, base_style: str = ""):
        """Render text with inline **/*/` formatting on the current line.

        Wraps automatically when text exceeds the line width.
        """
        for kind, content in inline_tokens(text):
            if kind == "link":
                content = content[0]
                style = base_style
                self.set_text_color(11, 87, 208)
                self._write_wrapped(content, "Arial", style, 11)
                self.set_text_color(0, 0, 0)
            elif kind == "bold":
                self._write_wrapped(content, "Arial", "B", 11)
            elif kind == "italic":
                self._write_wrapped(content, "Arial", "I", 11)
            elif kind == "code":
                self._write_wrapped(content, "Mono", "", 10)
            else:
                self._write_wrapped(content, "Arial", base_style, 11)

    def _write_wrapped(self, text: str, family: str, style: str, size: int):
        self.set_font(family, style, size)
        # write() auto-wraps; line height 5.2mm
        self.write(5.2, text)


def render_pdf(blocks):
    pdf = ReportPDF()
    pdf.add_page()

    for kind, payload in blocks:
        if kind == "h1":
            pdf.set_font("Arial", "B", 22)
            pdf.set_text_color(20, 30, 60)
            pdf.multi_cell(0, 11, payload)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)
        elif kind == "h2":
            pdf.ln(3)
            pdf.set_font("Arial", "B", 15)
            pdf.set_text_color(20, 30, 60)
            pdf.multi_cell(0, 8, payload)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)
        elif kind == "h3":
            pdf.ln(2)
            pdf.set_font("Arial", "B", 12)
            pdf.set_text_color(40, 60, 100)
            pdf.multi_cell(0, 6, payload)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(0.5)
        elif kind == "p":
            pdf.add_inline(payload)
            pdf.ln(7)
        elif kind == "ul":
            for item in payload:
                pdf.set_font("Arial", "", 11)
                pdf.cell(5, 5.2, "")
                pdf.write(5.2, "•  ")
                pdf.add_inline(item)
                pdf.ln(5.5)
            pdf.ln(2)
        elif kind == "ol":
            for n, item in enumerate(payload, 1):
                pdf.set_font("Arial", "", 11)
                pdf.cell(5, 5.2, "")
                pdf.write(5.2, f"{n}.  ")
                pdf.add_inline(item)
                pdf.ln(5.5)
            pdf.ln(2)
        elif kind == "quote":
            pdf.set_font("Arial", "I", 11)
            pdf.set_text_color(80, 80, 80)
            pdf.set_left_margin(25)
            pdf.multi_cell(0, 5.5, payload)
            pdf.set_left_margin(20)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(3)
        elif kind == "code":
            pdf.set_fill_color(245, 245, 250)
            pdf.set_font("Mono", "", 9)
            for code_line in payload.split("\n"):
                pdf.cell(0, 4.5, code_line, ln=1, fill=True)
            pdf.ln(3)
        elif kind == "math":
            pdf.set_font("Arial", "I", 11)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 5.5, payload)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(3)
        elif kind == "hr":
            y = pdf.get_y() + 2
            pdf.set_draw_color(180, 180, 180)
            pdf.line(20, y, 190, y)
            pdf.ln(6)
        elif kind == "table":
            render_table_pdf(pdf, payload)

    pdf.output(str(PDF))
    print(f"wrote {PDF} ({PDF.stat().st_size/1024:.1f} KB)")


def _strip_inline(text: str) -> str:
    """Strip markdown for a plain-text snapshot used in table cells."""
    parts = []
    for kind, content in inline_tokens(text):
        parts.append(content[0] if kind == "link" else content)
    return "".join(parts)


def render_table_pdf(pdf, rows):
    if not rows:
        return
    n_cols = max(len(r) for r in rows)
    page_width = pdf.w - pdf.l_margin - pdf.r_margin
    col_width = page_width / n_cols
    pdf.ln(2)

    def measure(row, font_style):
        pdf.set_font("Arial", font_style, 10)
        max_lines = 1
        for cell in row:
            stripped = _strip_inline(cell)
            lines = pdf.multi_cell(col_width, 5, stripped, split_only=True)
            max_lines = max(max_lines, len(lines))
        return max_lines * 5 + 2

    for r_idx, row in enumerate(rows):
        is_header = r_idx == 0
        style = "B" if is_header else ""
        h = measure(row, style)
        # page break if needed
        if pdf.get_y() + h > pdf.h - pdf.b_margin:
            pdf.add_page()
        y_start = pdf.get_y()
        for c_idx in range(n_cols):
            cell = row[c_idx] if c_idx < len(row) else ""
            x_start = pdf.l_margin + c_idx * col_width
            pdf.set_xy(x_start, y_start)
            if is_header:
                pdf.set_fill_color(225, 230, 240)
                pdf.set_font("Arial", "B", 10)
            else:
                pdf.set_fill_color(252, 252, 254)
                pdf.set_font("Arial", "", 10)
            pdf.set_draw_color(200, 200, 210)
            pdf.multi_cell(col_width, 5, _strip_inline(cell), border=1, fill=True)
        pdf.set_xy(pdf.l_margin, y_start + h)
    pdf.ln(4)


# ---------- Main ---------------------------------------------------------------

EMOJI_FALLBACKS = {
    "✅": "[OK]",
    "❗": "[!]",
    "\U0001f150": "(A)",  # 🅰
    "\U0001f151": "(B)",  # 🅱
    "\U0001f7e2": "(A)",  # 🟢
    "\U0001f7e1": "(B)",  # 🟡
    "\U0001f534": "(C)",  # 🔴
    "\U0001f4c1": "[folder]",  # 📁
    "⚠️": "[!]",  # warning
    "⚠": "[!]",
}


def normalize_emoji(text: str) -> str:
    for k, v in EMOJI_FALLBACKS.items():
        text = text.replace(k, v)
    return text


def main():
    md_text = MD.read_text(encoding="utf-8")
    md_text = normalize_emoji(md_text)
    blocks = list(parse(md_text))
    print(f"Parsed {len(blocks)} blocks from {MD}")

    build_docx(blocks)
    render_pdf(blocks)


if __name__ == "__main__":
    main()
