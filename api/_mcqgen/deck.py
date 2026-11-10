"""Build the MCQ slide deck in the Shikho MCQ template format, with automatic layout.

Rules (agreed with the team):
  * left side stays free for live solving; options are one right-aligned column (15.5 in standard,
    grows leftwards only as much as long options need)
  * minimum font 54 pt for everything on the board; question / উদ্দীপক paragraphs justified
  * nothing below 20.0 in from the top
  * board reference = pink pill on the bottom-right of the question / উদ্দীপক box
  * answer slide = same slide with the correct option blue + green ✓ (no marks beside i/ii/iii)
  * explanations, sources and answers go to the speaker notes
"""
import io, os, re, math
from pptx import Presentation
from PIL import ImageFont
from . import ooxml as X
from .ooxml import P, T, M, BLUE, PINK, WHITE, YELLOW, AMBER, CYAN, GREEN, OPT_FILL, STIM_FILL, STMT_FILL, BN
from .latex_omml import latex_to_omml

BASE = os.path.join(X.ASSETS, "base.pptx")
FB = ImageFont.truetype(os.path.join(X.ASSETS, "fonts", "HindSiliguri-Bold.ttf"), 200, layout_engine=X.LAYOUT)
FR = ImageFont.truetype(os.path.join(X.ASSETS, "fonts", "HindSiliguri-Regular.ttf"), 200, layout_engine=X.LAYOUT)
L, R = 1.5, 38.5
W = R - L
TOP, BOTTOM = 4.35, 20.0
MINW = 15.5
LETTERS = ["ক", "খ", "গ", "ঘ"]
TO_BN = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
TO_EN = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def LH(size):
    return size * 1.5 / 72


# ------------------------------------------------------------------ text helpers
def segs(text, color=None, bold=True):
    """'...$\\frac{1}{2}$...' -> list of text / equation segments."""
    out = []
    for i, part in enumerate(re.split(r"\$([^$]+)\$", text or "")):
        if not part:
            continue
        if i % 2:
            out.append(M(lambda tex=part: latex_to_omml(tex), part, part))
        else:
            out.append(T(part, color=color, bold=bold))
    return out or [T(" ")]


def paras(text, color=WHITE, bold=True, algn="l"):
    return [P(*segs(line, bold=bold), algn=algn, color=color) for line in (text or " ").split("\n")]


_MW = {}


def seg_w(s, size):
    if "m" in s:
        k = (s["tex"], size)
        if k not in _MW:
            try:
                r = X._MP.parse("$" + s["tex"] + "$", dpi=X.DPI, prop=X.FontProperties(size=size))
                _MW[k] = r.width / X.DPI + 0.25 * size / 72
            except Exception:
                _MW[k] = len(s["tex"]) * 0.5 * size / 72
        return _MW[k]
    f = FB if s.get("bold", True) else FR
    return f.getlength(s["t"]) * (s["size"] or size) / 200 / 72


def text_w(text, size, bold=True):
    return sum(seg_w(s, size) for s in segs(text, bold=bold))


def nlines(text, size, avail, bold=True):
    n = 0
    for line in (text or " ").split("\n"):
        n += max(1, math.ceil(text_w(line, size, bold) * 1.05 / max(avail, 0.5)))
    return n


def just(ps):
    for p in ps:
        if p["algn"] == "l":
            p["algn"] = "just"
    return ps


# ------------------------------------------------------------------ components
class Deck:
    def __init__(self, chapter=None):
        self.prs = Presentation(BASE)
        self.layout = self.prs.slide_layouts[0]
        if chapter:
            self._set_chapter(chapter)
        self.warnings = []

    def _set_chapter(self, chapter):
        for part in [self.prs.slide_master] + list(self.prs.slide_layouts):
            for sh in part.shapes:
                if sh.has_text_frame:
                    for p in sh.text_frame.paragraphs:
                        for r in p.runs:
                            if r.text.strip() == "বাক্যতত্ত্ব":
                                r.text = chapter

    def slide(self, notes):
        ps = self.prs.slides.add_slide(self.layout)
        for ph in list(ps.placeholders):
            ph._element.getparent().remove(ph._element)
        ps.notes_slide.notes_text_frame.text = notes
        return X.Slide(ps)

    def save(self):
        buf = io.BytesIO()
        self.prs.save(buf)
        return buf.getvalue()


def title(s, text):
    s.shape("Title", 10.49, 1.21, 19.03, 2.76, geom="rect", txbox=True, size=115,
            paras=[P(T(text, color=YELLOW, font="Gibson"), algn="ctr")], ins=(0.1, 0.05, 0.1, 0.05))


def qbox(s, y, h, text, size, board_space):
    s.shape("Question box", L, y, W, h, fill=BLUE, line=WHITE, lw=6, adj=18000 if h < 4 else 12000,
            paras=just(paras(text)), size=size, ins=(0.8, 0.2, 0.8, 0.7 if board_space else 0.35))


def board(s, boards, right, ybottom, size=54):
    text = "; ".join(b for b in boards if b.strip())
    if not text:
        return
    w = FB.getlength(text) * size / 200 / 72 * 1.08 + 1.0
    w = min(w, W - 1.0)
    s.shape("Board tag", right - w, ybottom - 0.675, w, 1.35, fill=PINK, line=WHITE, lw=4, adj=50000,
            paras=[P(T(text), algn="ctr")], size=size, ins=(0.25, 0.02, 0.25, 0.05), wrap=False)


def tick(s, x, y, d):
    s.shape("Correct mark", x, y, d, d, geom="ellipse", fill=GREEN, line=WHITE, lw=3,
            paras=[P(T("✓", font="Segoe UI Symbol"), algn="ctr")], size=d * 34, ins=(0, 0, 0, 0))


def option(s, i, x, y, w, h, text, size, correct, algn):
    bw = min(2.5, h * 1.05)
    s.shape(f"Option {LETTERS[i]} box", x, y, w, h, fill=BLUE if correct else OPT_FILL, line=WHITE, lw=4.5,
            adj=22000, paras=[P(*segs(text), algn=algn)], size=size, ins=(bw + 0.45, 0.05, 1.7, 0.12))
    s.shape(f"Option {LETTERS[i]} letter", x, y, bw, h, fill=PINK, line=WHITE, lw=4.5, adj=22000,
            paras=[P(T(LETTERS[i]), algn="ctr")], size=max(54, min(size + 6, 72)), ins=(0, 0, 0, 0.1))
    if correct:
        d = min(1.3, h - 0.2)
        tick(s, x + w - 1.55, y + (h - d) / 2, d)


def opt_measure(opts, size, h_guess=2.0):
    bw = min(2.5, h_guess * 1.05)
    pad = bw + 0.45 + 1.7 + 0.3
    need = max(text_w(o, size) for o in opts) * 1.06 + pad
    if need <= MINW:
        return MINW, "ctr", 1
    if need <= W:
        return need, "l", 1
    return W, "l", max(nlines(o, size, W - pad) for o in opts)


def labeled_box(s, label, x, y, w, h, fill, line, label_fill, label_color, ps, size, anchor="t",
                ins=(0.8, 0.8, 0.8, 0.25), name="Box"):
    s.shape(name, x, y, w, h, fill=fill, line=line, lw=4.5, adj=7000, paras=ps, size=size, anchor=anchor, ins=ins)
    lw_ = FB.getlength(label) * 54 / 200 / 72 * 1.08 + 1.0
    s.shape(name + " label", x + 0.8, y - 0.65, lw_, 1.3, fill=label_fill, line=WHITE, lw=3, adj=50000,
            paras=[P(T(label, color=label_color), algn="ctr")], size=54, ins=(0.1, 0, 0.1, 0.05))


def statements(s, y, rows_h, stmts, size, head=None):
    total = 0.3 + (LH(size) + 0.1 if head else 0) + sum(rows_h) + LH(size) + 0.25
    s.shape("Statements panel", L, y, W, total, fill=STMT_FILL, line=CYAN, lw=4.5, adj=6000)
    yy = y + 0.3
    if head:
        s.shape("Statements stem", L + 0.6, yy, W - 1.2, LH(size), geom="rect", txbox=True,
                paras=just(paras(head)), size=size, ins=(0, 0, 0, 0))
        yy += LH(size) + 0.1
    d = min(1.25, LH(size) - 0.05)
    for i, (st, rh) in enumerate(zip(stmts, rows_h)):
        rom = ["i", "ii", "iii", "iv", "v"][i] if i < 5 else str(i + 1)
        s.shape(f"Roman {rom}", L + 0.6, yy + (LH(size) - d) / 2, d, d, geom="ellipse", fill=CYAN, line=WHITE, lw=3,
                paras=[P(T(rom, color="000000", font="Times New Roman"), algn="ctr")], size=54 if d >= 1.2 else d * 44,
                ins=(0, 0, 0, 0))
        s.shape(f"Statement {i + 1}", L + d + 1.0, yy, W - d - 2.0, rh, geom="rect", txbox=True,
                paras=just(paras(st)), size=size, ins=(0, 0, 0, 0), anchor="t")
        yy += rh
    s.shape("Ask line", L + 0.6, yy, W - 1.2, LH(size), geom="rect", txbox=True,
            paras=[P(T("নিচের কোনটি সঠিক?", color=YELLOW))], size=size, ins=(0, 0, 0, 0))
    return total


CODEF = "Consolas"
_KW = r"\b(for|in|if|elif|else|while|break|continue|print|range|def|return|and|or|not|True|False|int|float|input|printf|scanf|include|main|void|char)\b"
_MONO = None


def code_w(line, size):
    global _MONO
    if _MONO is None:
        import matplotlib
        _MONO = ImageFont.truetype(os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSansMono.ttf"), 200)
    return _MONO.getlength(line) * size / 200 / 72


def code_paras(lines):
    pat = re.compile(r'("[^"]*"|\'[^\']*\')|' + _KW + r'|(\b\d+\b)|(</?\w+|/?>)')
    out = []
    for line in lines:
        sg, pos = [], 0
        for m in pat.finditer(line):
            if m.start() > pos:
                sg.append(T(line[pos:m.start()], color=WHITE, bold=False, font=CODEF))
            col = "FDE68A" if m.group(1) else ("7DD3FC" if m.group(2) else ("FDBA74" if m.group(3) else "F9A8D4"))
            sg.append(T(m.group(0), color=col, bold=False, font=CODEF)); pos = m.end()
        if pos < len(line):
            sg.append(T(line[pos:], color=WHITE, bold=False, font=CODEF))
        out.append(P(*(sg or [T(" ", font=CODEF)])))
    return out


# ------------------------------------------------------------------ layout
SIZES = [(62, 58, 60), (60, 56, 58), (58, 56, 56), (56, 54, 56), (54, 54, 54)]


def _measure(q, stim, compact_stim, qs, ss, os_):
    lay = {"qs": qs, "ss": ss, "os": os_, "overflow": False}
    y = TOP
    if stim and compact_stim:
        n = nlines(stim["text"], 54, W - 1.6, bold=False)
        h = 0.75 + n * LH(54) + 0.25
        lay["stim"] = (y + 0.45, h)
        y = y + 0.45 + h + (0.85 if stim.get("boards") else 0.45)
    if q.get("quote"):
        n = nlines(q["quote"], 56, W - 1.8)
        h = 0.7 + n * LH(56) + 0.25
        lay["quote"] = (y + 0.45, h)
        y = y + 0.45 + h + 0.45
    has_board = bool([b for b in q.get("boards", []) if b.strip()])
    n = nlines(q["stem"], qs, W - 1.6)
    h = 0.2 + n * LH(qs) + (0.7 if has_board else 0.35)
    lay["q"] = (y, h, has_board)
    y += h + (0.85 if has_board else 0.45)
    if q.get("statements"):
        rows = [max(1, nlines(st, ss, W - 3.4)) * LH(ss) + 0.08 for st in q["statements"]]
        ph = 0.3 + sum(rows) + LH(ss) + 0.25
        lay["stmts"] = (y, rows)
        y += ph + 0.4
    if q.get("code", "").strip():
        cl = q["code"].rstrip("\n").split("\n")
        cwid = min(21.0, max(code_w(l, 54) for l in cl) * 1.1 + 1.3)
        ch = 0.85 + len(cl) * LH(54) * 0.85 + 0.3
        lay["code"] = (y + 0.45, cwid, ch)
        if y + 0.45 + ch > BOTTOM:
            lay["overflow"] = True
    opts = [o or " " for o in q["options"]]
    cw, algn, ol = opt_measure(opts, os_)
    if "code" in lay:
        room = R - (L + lay["code"][1] + 0.6)
        if cw > room:
            cw, algn = max(MINW, room), "l"
            ol = max(nlines(o, os_, cw - 4.6) for o in opts)
    hmin = max(1.35, ol * LH(os_) + 0.2)
    return lay, y, cw, algn, ol, hmin, BOTTOM - y


def plan(q, stim, compact_stim):
    """Pick the largest sizes where the options fit as a right column; else a 2x2 grid for short
    options; else the tightest layout, flagged as overflow."""
    for qs, ss, os_ in SIZES:
        lay, y, cw, algn, ol, hmin, avail = _measure(q, stim, compact_stim, qs, ss, os_)
        if avail >= 4 * hmin + 3 * 0.2:
            h = min(2.4, max(hmin, (avail - 3 * 0.45) / 4))
            gap = max(0.2, min(0.55, (avail - 4 * h) / 3))
            lay["opts"] = ("col", y, h, gap, cw, algn)
            return lay
    for qs, ss, os_ in SIZES:
        lay, y, cw, algn, ol, hmin, avail = _measure(q, stim, compact_stim, qs, ss, os_)
        if cw == MINW and ol == 1 and avail >= 2 * hmin + 0.2:
            h = min(2.0, (avail - 0.25) / 2)
            lay["opts"] = ("grid", y, h, 0.25, MINW, "ctr")
            return lay
    h = max(1.0, (avail - 0.6) / 4)
    lay["opts"] = ("col", y, h, 0.2, cw, algn)
    lay["overflow"] = True
    return lay


def draw_question(d, q, stim, ans, compact_stim, notes):
    lay = plan(q, stim, compact_stim)
    s = d.slide(notes + ("\n⚠ লেখা বেশি লম্বা — slide-টা হাতে একবার দেখে নাও।" if lay["overflow"] else ""))
    title(s, f"MCQ - {str(q['num']).translate(TO_EN)}")
    if "stim" in lay:
        y, h = lay["stim"]
        labeled_box(s, stim.get("label") or "উদ্দীপক", L, y, W, h, STIM_FILL, AMBER, AMBER, "000000",
                    just(paras(stim["text"], bold=False)), 54, ins=(0.8, 0.75, 0.8, 0.2), name="Stimulus")
        board(s, stim.get("boards", []), R - 1.0, y + h)
    if "quote" in lay:
        y, h = lay["quote"]
        labeled_box(s, "উদ্ধৃতি", L, y, W, h, STIM_FILL, AMBER, AMBER, "000000",
                    paras(q["quote"], algn="ctr"), 56, anchor="ctr", ins=(0.9, 0.7, 0.9, 0.25), name="Quote")
    y, h, hb = lay["q"]
    qbox(s, y, h, q["stem"], lay["qs"], hb)
    if hb:
        board(s, q["boards"], R - 1.0, y + h)
    if "stmts" in lay:
        y, rows = lay["stmts"]
        statements(s, y, rows, q["statements"], lay["ss"])
    if "code" in lay:
        y, cwid, ch = lay["code"]
        labeled_box(s, "কোড", L, y, cwid, ch, "0D1117", "8B5CF6", "8B5CF6", WHITE,
                    [dict(p, ln=85) for p in code_paras(q["code"].rstrip("\n").split("\n"))], 54,
                    ins=(0.7, 0.8, 0.4, 0.25), name="Code")
    mode, y, h, gap, cw, algn = lay["opts"]
    opts = [o or " " for o in q["options"]]
    if mode == "col":
        for i, o in enumerate(opts):
            option(s, i, R - cw, y + i * (h + gap), cw, h, o, lay["os"], ans == i, algn)
    else:
        c = (MINW - 0.5) / 2
        for i, o in enumerate(opts):
            option(s, i, R - MINW + (i % 2) * (c + 0.5), y + (i // 2) * (h + gap), c, h, o, lay["os"], ans == i, "ctr")
    if lay["overflow"]:
        d.warnings.append(f"MCQ {q['num']}: লেখা বেশি লম্বা, slide-টা হাতে দেখে নিও।")


def draw_stimulus_slide(d, stim, nums):
    bn = [str(n).translate(TO_BN) for n in nums]
    en = [str(n).translate(TO_EN) for n in nums]
    joined_bn = " ও ".join(bn) if len(bn) <= 2 else f"{bn[0]}–{bn[-1]}"
    joined_en = " & ".join(en) if len(en) <= 2 else f"{en[0]}-{en[-1]}"
    head = stim.get("header") or f"নিচের উদ্দীপকটি পড়ে {joined_bn} নম্বর প্রশ্নের উত্তর দাও:"
    s = d.slide("উদ্দীপক slide — আগে পুরোটা পড়ানো হবে।" + (" উৎস: " + "; ".join(stim["boards"]) if stim.get("boards") else ""))
    title(s, f"MCQ - {joined_en}")
    s.shape("Instruction", L, 4.5, W, 1.5, geom="rect", txbox=True, size=58,
            paras=[P(*segs(head, color=YELLOW))], ins=(0, 0, 0, 0))
    box_h = 11.0
    size = 54
    for sz in (80, 72, 66, 60, 54):
        if 1.5 + nlines(stim["text"], sz, W - 2.4, bold=False) * LH(sz) * 1.1 <= box_h:
            size = sz; break
    labeled_box(s, stim.get("label") or "উদ্দীপক", L, 7.6, W, box_h, STIM_FILL, AMBER, AMBER, "000000",
                [dict(p, ln=110) for p in just(paras(stim["text"], bold=False))], size, anchor="ctr",
                ins=(1.2, 0.9, 1.2, 0.6), name="Stimulus")
    board(s, stim.get("boards", []), R - 1.0, 7.6 + box_h)


TYPE_NAME = {"single": "সাধারণ", "roman": "বহুপদী সমাপ্তিসূচক", "quote": "উদ্ধৃতি / কবিতাংশ", "stimulus": "উদ্দীপক-ভিত্তিক"}


def build(mcqs, stimuli=None, chapter=None, answer_slides=True):
    """mcqs: list of dicts (see parser). stimuli: list of {id,label,text,boards,header}. Returns (bytes, warnings)."""
    d = Deck(chapter)
    smap = {s["id"]: s for s in (stimuli or [])}
    shown = set()
    for qi, q in enumerate(mcqs):
        stim = smap.get(q.get("stimulus")) if q.get("stimulus") else None
        if stim and stim["id"] not in shown:
            group = [x["num"] for x in mcqs if x.get("stimulus") == stim["id"]]
            if len(group) > 1 or len(stim["text"]) > 160:
                draw_stimulus_slide(d, stim, group)
            shown.add(stim["id"])
        ans = q.get("answer")
        letter = LETTERS[ans] if isinstance(ans, int) and 0 <= ans < 4 else "?"
        notes = (f"{TYPE_NAME.get(q.get('type'), '')} | উত্তর: ({letter}) {q['options'][ans] if letter != '?' else ''}"
                 + (f"\nউৎস: {'; '.join(q['boards'])}" if q.get("boards") else "")
                 + (f"\nব্যাখ্যা: {q['explanation']}" if q.get("explanation") else "")
                 + "\nবাঁ দিক ফাঁকা — সমাধান লেখার জায়গা।")
        draw_question(d, q, stim, None, True, "প্রশ্ন slide | " + notes)
        if answer_slides and letter != "?":
            draw_question(d, q, stim, ans, True, "উত্তর slide | " + notes)
    return d.save(), d.warnings
