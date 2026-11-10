"""Low-level OOXML builders for the MCQ template: shapes, tables, native equations (OMML) with a
picture fallback so equations never break in viewers that can't render PowerPoint math."""
import os, ctypes
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl")
# Pillow's complex-text layout (needed for Bangla) loads libfribidi at runtime; ship it with the app.
try:
    ctypes.CDLL(os.path.join(ASSETS, "lib", "libfribidi.so.0"), mode=ctypes.RTLD_GLOBAL)
except OSError:
    pass

import re
from xml.sax.saxutils import escape
from lxml import etree

EMU = 914400
NSDECL = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
          'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
          'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
          'xmlns:a14="http://schemas.microsoft.com/office/drawing/2010/main" '
          'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"')

# palette (from the original template + highlight families)
BLUE = "354894"; PINK = "CF278D"; WHITE = "FFFFFF"; YELLOW = "FFFF00"
AMBER = "FFC000"; CYAN = "00B0F0"; GREEN = "00B050"; RED = "E5484D"
OPT_FILL = "111111"; STIM_FILL = "2B2208"; STMT_FILL = "07283A"; EXPL_FILL = "0B2614"
BN = "Hind Siliguri"; MATHF = "Cambria Math"


def e(v):
    return int(round(v * EMU))


# ---------------------------------------------------------------- text model
def T(text, color=None, size=None, bold=True, font=None):
    return {"t": text, "color": color, "size": size, "bold": bold, "font": font}


def M(omml, fallback, tex):
    """inline equation: omml = callable returning inner xml of m:oMath; tex = mathtext for the
    picture fallback (shown by viewers that can't render PowerPoint equations)."""
    return {"m": omml, "fb": fallback, "tex": tex}


def P(*segs, algn="l", size=None, color=WHITE, spc_before=0, ln=None):
    segs = [T(s) if isinstance(s, str) else s for s in segs]
    return {"segs": segs, "algn": algn, "size": size, "color": color, "spcb": spc_before, "ln": ln}


def rpr(size, color, bold=True, font=BN, lang="bn-BD"):
    return (f'<a:rPr lang="{lang}" sz="{int(size*100)}" b="{1 if bold else 0}" dirty="0">'
            f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
            f'<a:latin typeface="{font}"/><a:ea typeface="{font}"/><a:cs typeface="{font}"/></a:rPr>')


# ------------------------------------------------------------ OMML helpers
_ITAL = {c: chr(0x1D44E + i) for i, c in enumerate("abcdefghijklmnopqrstuvwxyz")}
_ITAL["h"] = "ℎ"
_ITAL.update({c: chr(0x1D434 + i) for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")})
_MCTX = {"size": 60, "color": WHITE}


def mctx(size, color=WHITE):
    _MCTX.update(size=size, color=color)


def _mrpr():
    return rpr(_MCTX["size"], _MCTX["color"], bold=False, font=MATHF, lang="en-US")


def mr(text, italic=True):
    if italic:
        text = "".join(_ITAL.get(c, c) for c in text)
    return f'<m:r>{_mrpr()}<m:t>{escape(text)}</m:t></m:r>'


def mctrl():
    return f'<m:ctrlPr>{_mrpr()}</m:ctrlPr>'


def macc(base, ch):
    return f'<m:acc><m:accPr><m:chr m:val="{ch}"/>{mctrl()}</m:accPr><m:e>{base}</m:e></m:acc>'


def vec(letter):
    return macc(mr(letter), "⃗")


def hat(letter):
    return macc(mr(letter), "̂")


def frac(n, d):
    return f'<m:f><m:fPr>{mctrl()}</m:fPr><m:num>{n}</m:num><m:den>{d}</m:den></m:f>'


def bar(e):
    return f'<m:bar><m:barPr><m:pos m:val="top"/>{mctrl()}</m:barPr><m:e>{e}</m:e></m:bar>'


def op(s):
    return mr(s, italic=False)


# ------------------------------------------------------------- paragraphs
def para_xml(p, base_size, use_math):
    size = p["size"] or base_size
    ppr = f'<a:pPr algn="{p["algn"]}">'
    if p["ln"]:
        ppr += f'<a:lnSpc><a:spcPct val="{int(p["ln"]*1000)}"/></a:lnSpc>'
    if p["spcb"]:
        ppr += f'<a:spcBef><a:spcPts val="{int(p["spcb"]*100)}"/></a:spcBef>'
    ppr += '</a:pPr>'
    out = ppr
    for s in p["segs"]:
        if "m" in s:
            if use_math:
                mctx(size, p["color"])
                out += f'<a14:m><m:oMath>{s["m"]()}</m:oMath></a14:m>'
            else:
                out += f'<a:r>{rpr(size, p["color"], bold=False, font=MATHF, lang="en-US")}<a:t xml:space="preserve">{escape(s["fb"])}</a:t></a:r>'
        else:
            for piece in re.split(r'([σμ]+)', s["t"]):
                if not piece:
                    continue
                f = "Times New Roman" if re.fullmatch(r'[σμ]+', piece) else (s["font"] or BN)
                out += (f'<a:r>{rpr(s["size"] or size, s["color"] or p["color"], s["bold"], f)}'
                        f'<a:t xml:space="preserve">{escape(piece)}</a:t></a:r>')
    out += f'<a:endParaRPr lang="bn-BD" sz="{int(size*100)}" dirty="0"/>'
    return f'<a:p>{out}</a:p>'


# ------------------------------------------------- picture fallback for equations
import io, math as _m
import numpy as np
from PIL import Image, ImageDraw, ImageFont, features
HAS_RAQM = features.check("raqm")
LAYOUT = ImageFont.Layout.RAQM if HAS_RAQM else ImageFont.Layout.BASIC
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["mathtext.fontset"] = "stix"
from matplotlib.mathtext import MathTextParser
from matplotlib.font_manager import FontProperties
DPI = 150
_MP = MathTextParser("agg")
_FONTS = {}


def _font(bold, size, family=BN):
    path = os.path.join(ASSETS, "fonts", "HindSiliguri-Bold.ttf" if bold else "HindSiliguri-Regular.ttf")
    if family not in (BN,):
        path = os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf")
    k = (path, size)
    if k not in _FONTS:
        _FONTS[k] = ImageFont.truetype(path, max(1, int(round(size * DPI / 72))), layout_engine=LAYOUT)
    return _FONTS[k]


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _piece_text(t, size, color, bold, family):
    f = _font(bold, size, family)
    asc, desc = f.getmetrics()
    w = max(1, int(_m.ceil(f.getlength(t))))
    im = Image.new("RGBA", (w, asc + desc), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((0, asc), t, font=f, fill=_rgb(color) + (255,), anchor="ls")
    return im, asc


def _piece_math(tex, size, color):
    try:
        r = _MP.parse("$" + tex + "$", dpi=DPI, prop=FontProperties(size=size))
    except Exception:
        return _piece_text(tex, size, color, False, "serif")
    a = np.asarray(r.image)
    h, w = a.shape
    pad = int(size * DPI / 72 * 0.12)
    rgba = np.zeros((h, w + 2 * pad, 4), dtype=np.uint8)
    rgba[:, pad:pad + w, :3] = _rgb(color)
    rgba[:, pad:pad + w, 3] = a
    return Image.fromarray(rgba, "RGBA"), int(round(h - r.depth))


def render_paras(paras, base_size, avail_w_in):
    lines = []
    for p in paras:
        size = p["size"] or base_size
        pcs = []
        for sg in p["segs"]:
            if "m" in sg:
                pcs.append(_piece_math(sg["tex"], size, p["color"]))
            else:
                for piece in re.split(r'([σμ]+)', sg["t"]):
                    if piece:
                        fam = "serif" if re.fullmatch(r'[σμ]+', piece) or (sg["font"] and sg["font"] != BN) else BN
                        pcs.append(_piece_text(piece, sg["size"] or size, sg["color"] or p["color"], sg["bold"], fam))
        asc = max(a for _, a in pcs); desc = max(im.height - a for im, a in pcs)
        lh = max(asc + desc, int(size * DPI / 72 * 1.25))
        w = sum(im.width for im, _ in pcs)
        line = Image.new("RGBA", (max(w, 1), lh), (0, 0, 0, 0))
        x = 0; top = (lh - asc - desc) // 2
        for im, a in pcs:
            line.alpha_composite(im, (x, top + asc - a)); x += im.width
        lines.append((line, p["algn"], int(p["spcb"] * DPI / 72)))
    aw = int(avail_w_in * DPI)
    maxw = max(l.width for l, _, _ in lines)
    cw = aw if any(a == "ctr" for _, a, _ in lines) else maxw
    cw = max(cw, maxw)
    H = sum(l.height + sb for l, _, sb in lines)
    canvas = Image.new("RGBA", (cw, H), (0, 0, 0, 0))
    y = 0
    for l, a, sb in lines:
        y += sb
        x = (cw - l.width) // 2 if a == "ctr" else (cw - l.width if a == "r" else 0)
        canvas.alpha_composite(l, (x, y)); y += l.height
    return canvas


class Slide:
    def __init__(self, pslide):
        self.ps = pslide
        self.tree = pslide.shapes._spTree
        self.nid = 100

    def _id(self):
        self.nid += 1
        return self.nid

    def add(self, xml):
        el = etree.fromstring(f'<root {NSDECL}>{xml}</root>')[0]
        self.tree.append(el)

    def shape(self, name, x, y, w, h, geom="roundRect", fill=None, line=None, lw=4.5,
              paras=None, size=60, anchor="ctr", ins=(0.3, 0.15, 0.3, 0.15), txbox=False,
              adj=None, wrap=True, autofit=False, alpha=None):
        sid = self._id()

        def build(use_math):
            av = f'<a:gd name="adj" fmla="val {adj}"/>' if adj is not None else ''
            fillx = '<a:noFill/>' if fill is None else (
                f'<a:solidFill><a:srgbClr val="{fill}">' + (f'<a:alpha val="{alpha}"/>' if alpha else '') + '</a:srgbClr></a:solidFill>')
            linex = '<a:ln><a:noFill/></a:ln>' if line is None else (
                f'<a:ln w="{int(lw*12700)}"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>')
            body = ''
            if paras is not None:
                l, t, r, b = ins
                body = (f'<p:txBody><a:bodyPr wrap="{"square" if wrap else "none"}" lIns="{e(l)}" tIns="{e(t)}" rIns="{e(r)}" bIns="{e(b)}" '
                        f'rtlCol="0" anchor="{anchor}">' + ('<a:spAutoFit/>' if autofit else '<a:noAutofit/>') +
                        '</a:bodyPr><a:lstStyle/>' + ''.join(para_xml(p, size, use_math) for p in paras) + '</p:txBody>')
            return (f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{escape(name)}"/><p:cNvSpPr{" txBox=\"1\"" if txbox else ""}/><p:nvPr/></p:nvSpPr>'
                    f'<p:spPr><a:xfrm><a:off x="{e(x)}" y="{e(y)}"/><a:ext cx="{e(w)}" cy="{e(h)}"/></a:xfrm>'
                    f'<a:prstGeom prst="{geom}"><a:avLst>{av}</a:avLst></a:prstGeom>{fillx}{linex}</p:spPr>{body}</p:sp>')

        has_math = paras and any("m" in s for p in paras for s in p["segs"])
        if has_math and not HAS_RAQM:
            self.add('<mc:AlternateContent><mc:Choice Requires="a14">' + build(True) +
                     '</mc:Choice><mc:Fallback>' + build(False) + '</mc:Fallback></mc:AlternateContent>')
        elif has_math:
            # fallback = same box without text + a picture of the whole text (equations intact)
            l, t, r, b = ins
            aw, ah = w - l - r, h - t - b
            img = render_paras(paras, size, aw)
            pw, ph = img.width / DPI, img.height / DPI
            k = min(1.0, aw / pw, ah / ph) if ph > 0 else 1.0
            pw, ph = pw * k, ph * k
            px = x + l
            py = y + t + ((ah - ph) / 2 if anchor == "ctr" else (ah - ph if anchor == "b" else 0))
            buf = io.BytesIO(); img.save(buf, "PNG"); buf.seek(0)
            _, rid = self.ps.part.get_or_add_image_part(buf)
            pid = self._id()
            pic = (f'<p:pic><p:nvPicPr><p:cNvPr id="{pid}" name="{escape(name)} (equation picture)"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
                   f'<p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
                   f'<p:spPr><a:xfrm><a:off x="{e(px)}" y="{e(py)}"/><a:ext cx="{e(pw)}" cy="{e(ph)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')
            bare = build(False)
            bare = re.sub(r'<p:txBody>.*</p:txBody>', '', bare, flags=re.S)
            self.add('<mc:AlternateContent><mc:Choice Requires="a14">' + build(True) +
                     '</mc:Choice><mc:Fallback>' + bare + pic + '</mc:Fallback></mc:AlternateContent>')
        else:
            self.add(build(False))

    def picture(self, name, path, x, y, w=None, h=None):
        im = Image.open(path)
        if w is None:
            w = h * im.width / im.height
        if h is None:
            h = w * im.height / im.width
        _, rid = self.ps.part.get_or_add_image_part(path)
        pid = self._id()
        self.add(f'<p:pic><p:nvPicPr><p:cNvPr id="{pid}" name="{escape(name)}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
                 f'<p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
                 f'<p:spPr><a:xfrm><a:off x="{e(x)}" y="{e(y)}"/><a:ext cx="{e(w)}" cy="{e(h)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')
        return w, h

    def line(self, name, x1, y1, x2, y2, color=WHITE, lw=3, dot_end=False):
        sid = self._id()
        x, y = min(x1, x2), min(y1, y2)
        w, h = abs(x2 - x1), abs(y2 - y1)
        flip = (' flipH="1"' if x2 < x1 else '') + (' flipV="1"' if y2 < y1 else '')
        tail = '<a:tailEnd type="oval" w="sm" len="sm"/>' if dot_end else ''
        self.add(f'<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="{sid}" name="{escape(name)}"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>'
                 f'<p:spPr><a:xfrm{flip}><a:off x="{e(x)}" y="{e(y)}"/><a:ext cx="{e(w)}" cy="{e(h)}"/></a:xfrm>'
                 f'<a:prstGeom prst="line"><a:avLst/></a:prstGeom><a:ln w="{int(lw*12700)}"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>{tail}</a:ln></p:spPr></p:cxnSp>')

    def grid(self, name, x, y, colw, rowh, rows, size=40, head_rows=1, head_cols=0, line="BFBFBF",
             head_fill="2F3B66", body_fill="111111", head_color=WHITE, body_color=WHITE, mark=None):
        """Plain grid table (spreadsheet / truth table). rowh: list. mark: {(r,c): color} text colour override."""
        sid = self._id()
        grid = ''.join(f'<a:gridCol w="{e(c)}"/>' for c in colw)
        trs = ''
        for ri, row in enumerate(rows):
            tcs = ''
            for ci, txt in enumerate(row):
                head = ri < head_rows or ci < head_cols
                col = (mark or {}).get((ri, ci), head_color if head else body_color)
                bd = ''.join(f'<a:{s_} w="{int(2*12700)}"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:{s_}>'
                             for s_ in ("lnL", "lnR", "lnT", "lnB"))
                paras_ = ''.join(f'<a:p><a:pPr algn="ctr"/><a:r>{rpr(size, col, head)}<a:t>{escape(t_)}</a:t></a:r></a:p>'
                                 for t_ in str(txt).split("\n"))
                tcs += (f'<a:tc><a:txBody><a:bodyPr/><a:lstStyle/>{paras_}</a:txBody><a:tcPr marL="{e(.08)}" marR="{e(.08)}" marT="{e(.03)}" marB="{e(.03)}" anchor="ctr">{bd}'
                        f'<a:solidFill><a:srgbClr val="{head_fill if head else body_fill}"/></a:solidFill></a:tcPr></a:tc>')
            trs += f'<a:tr h="{e(rowh[ri])}">{tcs}</a:tr>'
        self.add(f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{sid}" name="{escape(name)}"/><p:cNvGraphicFramePr><a:graphicFrameLocks noGrp="1"/></p:cNvGraphicFramePr><p:nvPr/></p:nvGraphicFramePr>'
                 f'<p:xfrm><a:off x="{e(x)}" y="{e(y)}"/><a:ext cx="{e(sum(colw))}" cy="{e(sum(rowh))}"/></p:xfrm>'
                 f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table"><a:tbl><a:tblPr firstRow="1" bandRow="0"/>'
                 f'<a:tblGrid>{grid}</a:tblGrid>{trs}</a:tbl></a:graphicData></a:graphic></p:graphicFrame>')

    def table(self, name, x, y, colw, rowh, rows, size=40, head_fill=AMBER, body_fill="1A1A1A"):
        sid = self._id()
        W = sum(colw); H = rowh * len(rows)
        grid = ''.join(f'<a:gridCol w="{e(c)}"/>' for c in colw)
        trs = ''
        for ri, row in enumerate(rows):
            tcs = ''
            for ci, txt in enumerate(row):
                head = ri == 0 or ci == 0
                fill = head_fill if ri == 0 else ("332A0E" if ci == 0 else body_fill)
                col = "000000" if ri == 0 else WHITE
                bd = ''.join(f'<a:{s} w="{int(2*12700)}"><a:solidFill><a:srgbClr val="{AMBER}"/></a:solidFill></a:{s}>'
                             for s in ("lnL", "lnR", "lnT", "lnB"))
                tcs += (f'<a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p><a:pPr algn="ctr"/><a:r>{rpr(size, col, head)}'
                        f'<a:t>{escape(txt)}</a:t></a:r></a:p></a:txBody><a:tcPr marL="{e(.15)}" marR="{e(.15)}" anchor="ctr">{bd}'
                        f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill></a:tcPr></a:tc>')
            trs += f'<a:tr h="{e(rowh)}">{tcs}</a:tr>'
        self.add(f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{sid}" name="{escape(name)}"/><p:cNvGraphicFramePr><a:graphicFrameLocks noGrp="1"/></p:cNvGraphicFramePr><p:nvPr/></p:nvGraphicFramePr>'
                 f'<p:xfrm><a:off x="{e(x)}" y="{e(y)}"/><a:ext cx="{e(W)}" cy="{e(H)}"/></p:xfrm>'
                 f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table"><a:tbl><a:tblPr firstRow="1" bandRow="0"/>'
                 f'<a:tblGrid>{grid}</a:tblGrid>{trs}</a:tbl></a:graphicData></a:graphic></p:graphicFrame>')
