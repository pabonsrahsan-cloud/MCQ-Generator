"""Turn an uploaded file (.docx, .pptx, .pdf, .txt) into plain text lines.

Equations in Word / PowerPoint are converted to LaTeX and wrapped in $...$ so they can be rebuilt as
real equations. Slides are separated by a BREAK line so each slide can be treated as one block.
"""
import io, re
from lxml import etree
from .latex_omml import omml_to_latex

BREAK = "\f"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
MNS = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
A14 = "{http://schemas.microsoft.com/office/drawing/2010/main}"


def _math(el):
    tex = omml_to_latex(el).strip()
    return f" ${tex}$ " if tex else ""


# ---------------------------------------------------------------- docx
def _docx_par(p):
    out = []

    def walk(node):
        for ch in node:
            t = ch.tag
            if t == W + "t":
                out.append(ch.text or "")
            elif t == W + "tab":
                out.append(" ")
            elif t in (W + "br", W + "cr"):
                out.append("\n")
            elif t == MNS + "oMath":
                out.append(_math(ch))
            elif t == MNS + "oMathPara":
                for m in ch.iter(MNS + "oMath"):
                    out.append(_math(m))
            elif t in (W + "del", W + "pPr", W + "rPr", W + "instrText"):
                continue
            elif t == MC + "AlternateContent":
                fb = ch.find(MC + "Choice")
                if fb is not None:
                    walk(fb)
            else:
                walk(ch)
    walk(p)
    return "".join(out)


def docx_lines(data):
    import docx
    d = docx.Document(io.BytesIO(data))
    lines = []
    body = d.element.body
    for el in body.iterchildren():
        if el.tag == W + "p":
            lines += _docx_par(el).split("\n")
        elif el.tag == W + "tbl":
            for tr in el.iter(W + "tr"):
                for tc in tr.iter(W + "tc"):
                    for p in tc.iter(W + "p"):
                        lines += _docx_par(p).split("\n")
    return lines


# ---------------------------------------------------------------- pptx
def _ppt_par(p):
    out = []
    for ch in p:
        if ch.tag == A + "r":
            t = ch.find(A + "t")
            out.append(t.text if t is not None and t.text else "")
        elif ch.tag == A + "br":
            out.append("\n")
        elif ch.tag == A + "fld":
            t = ch.find(A + "t")
            out.append(t.text if t is not None and t.text else "")
        elif ch.tag == A14 + "m":
            for m in ch.iter(MNS + "oMath"):
                out.append(_math(m))
    return "".join(out)


def _shape_items(shapes, items):
    for sh in shapes:
        try:
            top, left = sh.top or 0, sh.left or 0
        except Exception:
            top, left = 0, 0
        if sh.shape_type == 6:  # group
            _shape_items(sh.shapes, items)
            continue
        el = sh._element
        # text bodies (prefer the a14 equation version inside AlternateContent)
        if getattr(sh, "has_table", False) and sh.has_table:
            rows = []
            for r in sh.table.rows:
                rows.append(" | ".join(c.text.strip() for c in r.cells))
            items.append((top, left, rows))
            continue
        txb = el.find(".//{http://schemas.openxmlformats.org/presentationml/2006/main}txBody")
        if txb is None:
            continue
        lines = []
        for p in txb.iter(A + "p"):
            lines += _ppt_par(p).split("\n")
        if any(l.strip() for l in lines):
            items.append((top, left, lines))


def pptx_lines(data):
    from pptx import Presentation
    prs = Presentation(io.BytesIO(data))
    lines = []
    for slide in prs.slides:
        items = []
        _shape_items(slide.shapes, items)
        # AlternateContent shapes (equations) are invisible to python-pptx: read them directly
        tree = slide.shapes._spTree
        for ac in tree.iter(MC + "AlternateContent"):
            ch = ac.find(MC + "Choice")
            if ch is None:
                continue
            for sp in ch:
                off = sp.find(".//" + A + "off")
                top = int(off.get("y")) if off is not None else 0
                left = int(off.get("x")) if off is not None else 0
                ls = []
                for p in sp.iter(A + "p"):
                    ls += _ppt_par(p).split("\n")
                if any(l.strip() for l in ls):
                    items.append((top, left, ls))
        # reading order: rows (top, with tolerance) then left
        lone = re.compile(r"^\s*\(?([কখগঘ]|iv|iii|ii|i)\)?\s*$")
        items.sort(key=lambda it: (round(it[0] / 300000), it[1] // 300000,
                                   0 if len(it[2]) == 1 and lone.match(it[2][0]) else 1))
        for _, _, ls in items:
            lines += ls
        lines.append(BREAK)
    return lines


# ---------------------------------------------------------------- pdf / txt
def pdf_lines(data):
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(data))
    lines = []
    for page in r.pages:
        lines += (page.extract_text() or "").split("\n")
    return lines


def txt_lines(data):
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return data.decode(enc).splitlines()
        except Exception:
            continue
    return data.decode("utf-8", "ignore").splitlines()


def file_lines(filename, data):
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "docx":
        return docx_lines(data)
    if ext == "pptx":
        return pptx_lines(data)
    if ext == "pdf":
        return pdf_lines(data)
    return txt_lines(data)
