"""LaTeX  <->  Office Math (OMML).

* latex_to_omml(tex)  -> inner XML of <m:oMath> (uses the run helpers in ooxml, so size/colour follow
  the paragraph).  Supports the subset used in school MCQs: fractions, roots, powers, subscripts,
  vectors / hats / bars, overline, Greek letters and common operators.
* omml_to_latex(el)   -> LaTeX text for an <m:oMath> element found in a .docx / .pptx, so equations in
  the uploaded file come through as $...$ and can be rebuilt as real equations.
"""
import re
from xml.sax.saxutils import escape
from . import ooxml as X

GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "varepsilon": "ε", "zeta": "ζ",
    "eta": "η", "theta": "θ", "vartheta": "ϑ", "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν",
    "xi": "ξ", "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ", "varphi": "φ",
    "chi": "χ", "psi": "ψ", "omega": "ω", "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ",
    "Pi": "Π", "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
}
SYMBOLS = {
    "times": "×", "div": "÷", "pm": "±", "mp": "∓", "cdot": "⋅", "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥",
    "ne": "≠", "neq": "≠", "approx": "≈", "equiv": "≡", "infty": "∞", "to": "→", "rightarrow": "→",
    "Rightarrow": "⇒", "leftarrow": "←", "Leftarrow": "⇐", "leftrightarrow": "↔", "Leftrightarrow": "⇔",
    "oplus": "⊕", "odot": "⊙", "otimes": "⊗", "sum": "∑", "prod": "∏", "int": "∫", "partial": "∂",
    "angle": "∠", "degree": "°", "circ": "∘", "therefore": "∴", "because": "∵", "in": "∈", "notin": "∉",
    "cup": "∪", "cap": "∩", "subset": "⊂", "subseteq": "⊆", "prime": "′", "ldots": "…", "cdots": "⋯",
    "dots": "…", "perp": "⊥", "parallel": "∥", "nabla": "∇", "forall": "∀", "exists": "∃", "emptyset": "∅",
    "%": "%", "{": "{", "}": "}", "_": "_", "&": "&", "#": "#", "$": "$", "|": "‖", "langle": "⟨", "rangle": "⟩",
    "sin": "sin", "cos": "cos", "tan": "tan", "cot": "cot", "sec": "sec", "csc": "cosec", "log": "log",
    "ln": "ln", "lim": "lim", "max": "max", "min": "min", "exp": "exp",
}
SPACES = {",": " ", ";": " ", ":": " ", " ": " ", "quad": "  ", "qquad": "   ", "!": ""}
ACCENTS = {"vec": "⃗", "hat": "̂", "widehat": "̂", "bar": "̅", "dot": "̇",
           "ddot": "̈", "tilde": "̃", "widetilde": "̃"}
FUNCS = {"sin", "cos", "tan", "cot", "sec", "csc", "log", "ln", "lim", "max", "min", "exp"}


def _tokens(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            m = re.match(r"\\([A-Za-z]+|.)", s[i:])
            out.append("\\" + m.group(1)); i += len(m.group(0))
        elif c.isdigit():
            m = re.match(r"[0-9]+(?:\.[0-9]+)?", s[i:])
            out.append(m.group(0)); i += len(m.group(0))
        elif c.isspace():
            i += 1
        else:
            out.append(c); i += 1
    return out


class _P:
    def __init__(self, tex):
        self.t = _tokens(tex)
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def next(self):
        tok = self.peek(); self.i += 1
        return tok

    def expr(self, stop=None):
        out = ""
        while self.peek() is not None and self.peek() != stop:
            if self.peek() == "}" and stop is None:
                self.next(); continue
            out += self.atom_with_scripts()
        if stop is not None and self.peek() == stop:
            self.next()
        return out

    def arg(self):
        if self.peek() == "{":
            self.next(); return self.expr("}")
        return self.atom()

    def raw_arg(self):
        if self.peek() != "{":
            return self.next() or ""
        self.next(); depth, out = 1, []
        while self.peek() is not None:
            tk = self.next()
            if tk == "{": depth += 1
            elif tk == "}":
                depth -= 1
                if depth == 0: break
            out.append(tk[1:] if tk.startswith("\\") and len(tk) == 2 else tk)
        return " ".join(out).replace("  ", " ")

    def atom_with_scripts(self):
        base = self.atom()
        sub = sup = None
        while self.peek() in ("^", "_"):
            k = self.next()
            if k == "^": sup = self.arg()
            else: sub = self.arg()
        ctrl = X.mctrl()
        if sub is not None and sup is not None:
            return (f"<m:sSubSup><m:sSubSupPr>{ctrl}</m:sSubSupPr><m:e>{base}</m:e>"
                    f"<m:sub>{sub}</m:sub><m:sup>{sup}</m:sup></m:sSubSup>")
        if sup is not None:
            return f"<m:sSup><m:sSupPr>{ctrl}</m:sSupPr><m:e>{base}</m:e><m:sup>{sup}</m:sup></m:sSup>"
        if sub is not None:
            return f"<m:sSub><m:sSubPr>{ctrl}</m:sSubPr><m:e>{base}</m:e><m:sub>{sub}</m:sub></m:sSub>"
        return base

    def atom(self):
        tk = self.next()
        if tk is None:
            return ""
        if tk == "{":
            return self.expr("}")
        if tk.startswith("\\"):
            name = tk[1:]
            if name in ("frac", "dfrac", "tfrac"):
                n = self.arg(); d = self.arg()
                return X.frac(n, d)
            if name == "sqrt":
                deg = ""
                if self.peek() == "[":
                    self.next()
                    while self.peek() not in (None, "]"):
                        deg += self.atom_with_scripts()
                    self.next()
                e = self.arg()
                hide = "" if deg else '<m:degHide m:val="1"/>'
                return f"<m:rad><m:radPr>{hide}{X.mctrl()}</m:radPr><m:deg>{deg}</m:deg><m:e>{e}</m:e></m:rad>"
            if name in ("overline", "overbar"):
                return X.bar(self.arg())
            if name in ACCENTS:
                return X.macc(self.arg(), ACCENTS[name])
            if name in ("text", "mathrm", "textrm", "mbox", "operatorname", "mathbf", "textbf"):
                return X.mr(self.raw_arg(), italic=False)
            if name in ("left", "right", "big", "Big", "bigg", "Bigg"):
                d = self.next() or ""
                d = d[1:] if d.startswith("\\") else d
                return X.op({"{": "{", "}": "}", ".": ""}.get(d, d)) if d != "." else ""
            if name in GREEK:
                return X.mr(GREEK[name], italic=name[0].islower())
            if name in FUNCS:
                return X.mr(SYMBOLS[name], italic=False) + X.op("⁡")
            if name in SYMBOLS:
                return X.op(SYMBOLS[name])
            if name in SPACES:
                return X.op(SPACES[name]) if SPACES[name] else ""
            return X.mr(name, italic=False)
        if tk[0].isdigit():
            return X.mr(tk, italic=False)
        if tk.isalpha() and tk.isascii():
            return X.mr(tk)
        return X.op({"-": "−", "*": "∗", "'": "′"}.get(tk, tk))


def latex_to_omml(tex):
    return _P(tex).expr()


# ------------------------------------------------------------------ OMML -> LaTeX
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
_UNITAL = {}
for _i, _c in enumerate("abcdefghijklmnopqrstuvwxyz"):
    for base in (0x1D44E, 0x1D482, 0x1D41A, 0x1D5BA):   # italic, bold-italic, bold, sans
        _UNITAL[chr(base + _i)] = _c
for _i, _c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    for base in (0x1D434, 0x1D468, 0x1D400, 0x1D5A0):
        _UNITAL[chr(base + _i)] = _c
for _i in range(10):
    _UNITAL[chr(0x1D7CE + _i)] = str(_i)
_UNITAL["ℎ"] = "h"
_REV_ACC = {"⃗": "vec", "→": "vec", "̂": "hat", "^": "hat", "̅": "bar", "¯": "bar",
            "̇": "dot", "̃": "tilde", "~": "tilde"}


def _txt(s):
    s = "".join(_UNITAL.get(c, c) for c in s)
    return s.replace("{", "\\{").replace("}", "\\}").replace("%", "\\%").replace("#", "\\#").replace("&", "\\&")


def _kids(el, tag):
    return el.find(M + tag)


def _val(el, path, default=None):
    n = el.find(path)
    return n.get(M + "val", default) if n is not None else default


def omml_to_latex(el):
    tag = el.tag.replace(M, "")
    c = lambda name: omml_to_latex(_kids(el, name)) if _kids(el, name) is not None else ""
    if tag == "r":
        return "".join(_txt(t.text or "") for t in el.iter(M + "t"))
    if tag == "f":
        return "\\frac{%s}{%s}" % (c("num"), c("den"))
    if tag == "acc":
        ch = _val(el, f"{M}accPr/{M}chr", "̂")
        return "\\%s{%s}" % (_REV_ACC.get(ch, "hat"), c("e"))
    if tag == "bar":
        return "\\overline{%s}" % c("e")
    if tag == "sSup":
        return "{%s}^{%s}" % (c("e"), c("sup"))
    if tag == "sSub":
        return "{%s}_{%s}" % (c("e"), c("sub"))
    if tag == "sSubSup":
        return "{%s}_{%s}^{%s}" % (c("e"), c("sub"), c("sup"))
    if tag == "sPre":
        return "{}_{%s}^{%s}{%s}" % (c("sub"), c("sup"), c("e"))
    if tag == "rad":
        deg = c("deg")
        return ("\\sqrt[%s]{%s}" % (deg, c("e"))) if deg.strip() else "\\sqrt{%s}" % c("e")
    if tag == "d":
        beg = _val(el, f"{M}dPr/{M}begChr", "(")
        end = _val(el, f"{M}dPr/{M}endChr", ")")
        sep = _val(el, f"{M}dPr/{M}sepChr", ",")
        inner = sep.join(omml_to_latex(e) for e in el.findall(M + "e"))
        esc = lambda ch: {"{": "\\{", "}": "\\}"}.get(ch, ch)
        return esc(beg) + inner + esc(end)
    if tag == "nary":
        ch = _val(el, f"{M}naryPr/{M}chr", "∫")
        name = {"∑": "\\sum", "∏": "\\prod", "∫": "\\int"}.get(ch, ch)
        return "%s_{%s}^{%s}{%s}" % (name, c("sub"), c("sup"), c("e"))
    if tag == "func":
        return "%s{%s}" % (c("fName"), c("e"))
    if tag == "limLow":
        return "{%s}_{%s}" % (c("e"), c("lim"))
    if tag == "limUpp":
        return "{%s}^{%s}" % (c("e"), c("lim"))
    if tag == "eqArr":
        return " , ".join(omml_to_latex(e) for e in el.findall(M + "e"))
    if tag.endswith("Pr") or tag == "ctrlPr":
        return ""
    return "".join(omml_to_latex(k) for k in el)
