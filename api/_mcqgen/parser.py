"""Rule-based MCQ parser for Bangla (and English) question banks.

Recognises
  * question numbers      ১.  12.  (৩)  প্রশ্ন ৪:      or a slide title "MCQ - 7"
  * options               (ক) ক. ক) A. (a) a)  — several on one line is fine
  * statements            i.  (ii)  iii)          + the line "নিচের কোনটি সঠিক?"
  * board references      [ঢা. বো. ২৩]  [Dhaka Board 2019]  [দিনাজপুর বোর্ড, ২০২৫]
  * answers               উত্তর: খ   সঠিক উত্তর: (গ)   Ans: B
  * explanations          ব্যাখ্যা: ...
  * stimulus blocks       "নিচের উদ্দীপকটি পড়ে ৩০ ও ৩১ নম্বর প্রশ্নের উত্তর দাও"  or  "উদ্দীপক: ..."
  * quotes / poems        a question whose first lines are inside quotation marks
"""
import re
from .extract import BREAK

BN_DIGITS = "০১২৩৪৫৬৭৮৯"
TO_EN = str.maketrans(BN_DIGITS, "0123456789")
TO_BN = str.maketrans("0123456789", BN_DIGITS)
LETTER_IDX = {"ক": 0, "খ": 1, "গ": 2, "ঘ": 3, "a": 0, "b": 1, "c": 2, "d": 3}

NUM = r"[0-9০-৯]{1,3}"
RE_QNUM = re.compile(rf"^\s*(?:প্রশ্ন\s*(?:নং|নম্বর)?\s*[-:]?\s*)?\(?({NUM})\)?\s*[\.।:)]\s*(.*)$")
RE_MCQ_TITLE = re.compile(r"^\s*MCQ\s*[-–—:]?\s*([0-9০-৯]+)\s*$", re.I)
RE_NOISE = re.compile(r"^\s*(?:Type\s*\d+|.*MCQ\s*$|SCHOOL PROGRAM|ACADEMIC PROGRAM|CLASS\s*\d+|shikho|Component Kit.*|উদ্দীপক|উদ্ধৃতি|কোড)\s*$", re.I)
# option markers: (ক) | ক. ক) ক। | A. A) (A) | a. a) (a)
RE_OPT = re.compile(r"(?:\(\s*([কখগঘ]|[a-dA-D])\s*\)|(?:(?<=\s)|^)([কখগঘ])\s*[\.\)।]|(?:(?<=\s)|^)([a-dA-D])\s*[\.\)])\s*")
RE_LONE_OPT = re.compile(r"^\s*\(?\s*([কখগঘ]|[a-dA-D])\s*[\.\)।]?\s*$")
RE_ROMAN = re.compile(r"(?:(?<=\s)|^)\(?\s*(iii|ii|iv|i)\s*[\.\)]\s+")
RE_ASK = re.compile(r"নিচের\s*কোনটি\s*সঠিক\s*[?？]?")
RE_ANS = re.compile(r"^\s*(?:সঠিক\s*)?(?:উত্তর|উঃ|উ:|Ans(?:wer)?|Correct)\s*[:：\-–]?\s*\(?\s*([কখগঘ]|[a-dA-D])\b", re.I)
RE_ANS_LOOSE = re.compile(r"^\s*(?:সঠিক\s*)?(?:উত্তর|উঃ|Ans(?:wer)?)\s*[:：\-–]\s*\(?\s*([কখগঘ]|[a-dA-D])", re.I)
RE_EXPL = re.compile(r"^\s*(?:ব্যাখ্যা|সমাধান|Explanation|Solution)\s*[:：\-–]\s*(.*)$", re.I)
RE_STIM_HEAD = re.compile(r"(উদ্দীপক|অনুচ্ছেদ|কবিতাংশ|চিত্র|ছক|সারণি|তথ্য|উদ্ধৃতি|নিচের).{0,40}(পড়|দেখ|লক্ষ).{0,60}(প্রশ্ন|উত্তর)")
RE_STIM_LABEL = re.compile(r"^\s*(উদ্দীপক|উদ্ধৃতি|অনুচ্ছেদ)\s*[:：\-–]\s*(.*)$")
RE_BOARD_LINE = re.compile(r"^\s*\[?((?:[^\s\[\]]{1,10}\.?\s*বো\.?\s*['’]?[0-9০-৯]{2}[^\]]*)|(?:সকল\s*বোর্ড.*))\]?\s*$")
RE_LONE_ROMAN = re.compile(r"^\s*\(?(iv|iii|ii|i)\)?\s*$")
RE_TICK = re.compile(r"^\s*[✓✔☑]\s*$")
RE_BOARD = re.compile(r"\[([^\]]{2,80})\]")
QUOTES_OPEN = "\"“‘'«"
QUOTES_CLOSE = "\"”’'»"

BOARDS = [("ঢাকা", "ঢা."), ("রাজশাহী", "রা."), ("কুমিল্লা", "কু."), ("যশোর", "য."), ("চট্টগ্রাম", "চ."),
          ("সিলেট", "সি."), ("বরিশাল", "ব."), ("দিনাজপুর", "দি."), ("ময়মনসিংহ", "ম."), ("মাদ্রাসা", "মা."),
          ("Dhaka", "ঢা."), ("Rajshahi", "রা."), ("Cumilla", "কু."), ("Comilla", "কু."), ("Jashore", "য."),
          ("Jessore", "য."), ("Chattogram", "চ."), ("Chittagong", "চ."), ("Sylhet", "সি."), ("Barishal", "ব."),
          ("Barisal", "ব."), ("Dinajpur", "দি."), ("Mymensingh", "ম.")]


def _looks_like_board(s):
    return bool(re.search(r"বো|বোর্ড|Board|DU|ঢাবি|বুয়েট|মেডিকেল|ভর্তি|[০-৯0-9]{2}", s))


def norm_board(s):
    """'দিনাজপুর বোর্ড, ২০২৫' -> 'দি. বো. ২৫';  'Dhaka Board 19-20' -> 'ঢা. বো. ১৯-২০'."""
    s = s.strip().strip("[]").strip()
    if re.match(r"^(সকল|সব)\s*বো", s):
        return re.sub(r"^(সকল|সব)\s*বো(র্ড|\.)?\s*['’]?(?:২০|20)?", "সকল বোর্ড ", s).strip().translate(TO_BN)
    for long, short in BOARDS:
        s = re.sub(long + r"\s*(?:বোর্ড|Board|বো\.?)?", short + " বো.", s, flags=re.I)
    s = re.sub(r"\bBoard\b|বোর্ড", "বো.", s, flags=re.I)
    s = re.sub(r"(বো\.)\s*,?\s*['’]?\s*(?:২০|20)?([0-9০-৯]{2})\b", r"\1 \2", s)
    s = re.sub(r"\s+", " ", s).replace(" ,", ",").strip(" ,")
    return s.translate(TO_BN)


def split_boards(s):
    parts = re.split(r";|\s*,\s*(?=[^\d০-৯\s])", s)
    return [norm_board(p) for p in parts if p.strip()]


def take_boards(text):
    boards = []

    def rep(m):
        if _looks_like_board(m.group(1)):
            boards.extend(split_boards(m.group(1)))
            return ""
        return m.group(0)
    text = RE_BOARD.sub(rep, text)
    return re.sub(r"[ \t]+", " ", text).strip(), boards


def to_int(s):
    try:
        return int(s.translate(TO_EN))
    except Exception:
        return None


def roman_option(t):
    """'i, ii, iii' -> 'i, ii ও iii'  ;  'i, ii' -> 'i ও ii'."""
    if not re.fullmatch(r"[\siv,ওএবং&]+", t.strip()):
        return t
    items = re.findall(r"iv|iii|ii|i", t)
    if len(items) < 2:
        return t.strip()
    return ", ".join(items[:-1]) + " ও " + items[-1]


def _new(num=None, stem=""):
    return {"num": num, "stem": stem, "statements": [], "options": ["", "", "", ""], "answer": None,
            "boards": [], "explanation": "", "stimulus": None}


def _split_options(line):
    """Return list of (index, text) if the line starts with an option marker, else None."""
    ms = list(RE_OPT.finditer(line))
    if not ms or ms[0].start() > 0 and line[:ms[0].start()].strip():
        return None
    out = []
    for i, m in enumerate(ms):
        letter = (m.group(1) or m.group(2) or m.group(3)).lower()
        end = ms[i + 1].start() if i + 1 < len(ms) else len(line)
        out.append((LETTER_IDX[letter], line[m.end():end].strip()))
    # ignore false positives such as a single 'a.' inside a sentence: indices must be distinct
    if len({i for i, _ in out}) != len(out):
        return None
    return out


def parse_lines(lines):
    mcqs, warnings = [], []
    cur, mode, pending_letter, pending_roman = None, None, None, False
    stim, next_num = None, None   # stim = {"text","boards","nums","header","label","used"}

    def finalize():
        nonlocal cur, mode
        if cur and sum(1 for o in cur["options"] if o.strip()) >= 2:
            _post(cur)
            if mcqs and mcqs[-1]["stem"] == cur["stem"] and mcqs[-1]["options"] == cur["options"]:
                if cur["answer"] is not None and mcqs[-1]["answer"] is None:
                    mcqs[-1]["answer"] = cur["answer"]
            else:
                mcqs.append(cur)
        cur, mode = None, None

    def attach_stim(q):
        nonlocal stim
        if not stim:
            return
        n = q["num"]
        if stim["nums"]:
            if n is not None and stim["nums"][0] <= n <= stim["nums"][-1]:
                q["stimulus"] = stim["id"]
            elif n is not None and n > stim["nums"][-1]:
                stim = None
        elif stim["used"] < 2:
            q["stimulus"] = stim["id"]
            stim["used"] += 1

    stimuli = {}

    for raw in lines:
        if raw == BREAK:
            if cur and any(o.strip() for o in cur["options"]):
                finalize()
            pending_letter = None
            continue
        line = raw.replace(" ", " ").strip()
        if not line:
            continue

        m = RE_ANS.match(line) or RE_ANS_LOOSE.match(line)
        if m and cur:
            cur["answer"] = LETTER_IDX[m.group(1).lower()]
            mode = "ans"; continue
        m = RE_EXPL.match(line)
        if m and cur:
            cur["explanation"] = m.group(1).strip()
            mode = "expl"; continue
        m = RE_STIM_LABEL.match(line)
        if m or (RE_STIM_HEAD.search(line) and not RE_QNUM.match(line)):
            finalize()
            sid = f"s{len(stimuli) + 1}"
            nums = sorted({to_int(x) for x in re.findall(NUM, line) if to_int(x) is not None})
            if len(nums) == 2 and nums[1] - nums[0] > 6:
                nums = []
            if len(nums) == 2:
                nums = list(range(nums[0], nums[1] + 1))
            stim = {"id": sid, "text": (m.group(2) if m else ""), "nums": nums,
                    "header": "" if m else line, "label": (m.group(1) if m and m.group(1) == "উদ্ধৃতি" else "উদ্দীপক"),
                    "used": 0}
            stimuli[sid] = stim
            mode = "stim"; continue
        m = RE_MCQ_TITLE.match(line)
        if m:
            finalize(); next_num = to_int(m.group(1)); continue
        m = RE_QNUM.match(line)
        if m and not _split_options(line):
            finalize()
            cur = _new(to_int(m.group(1)), m.group(2).strip())
            attach_stim(cur)
            mode = "stem"; continue
        if RE_NOISE.match(line) and mode != "stem":
            continue
        if mode == "stim" and stim:
            stim["text"] = (stim["text"] + "\n" + line).strip()
            continue

        if RE_TICK.match(line):
            if cur:
                last = max((i for i, o in enumerate(cur["options"]) if o), default=None)
                if last is not None:
                    cur["answer"] = last
            continue
        line = re.sub(r"\s*[✓✔]\s*", " ", line).strip()
        if not line:
            continue
        bm = RE_BOARD_LINE.match(line)
        if bm and cur is not None and mode in ("stem", "stmt", "stmt_done", None):
            cur["boards"] += split_boards(bm.group(1))
            continue
        if RE_LONE_ROMAN.match(line) and cur is not None and mode in ("stem", "stmt"):
            pending_roman = True; mode = "stmt"; continue
        if pending_roman and cur is not None and not RE_ASK.search(line):
            cur["statements"].append(line); pending_roman = False; continue
        pending_roman = False

        opts = _split_options(line)
        if opts:
            if cur is None:
                cur = _new(next_num, ""); next_num = None
                attach_stim(cur)
            for i, t in opts:
                cur["options"][i] = t
            mode = "opts"; pending_letter = None; continue
        lm = RE_LONE_OPT.match(line)
        if lm and len(line) <= 4:
            if cur is None:
                cur = _new(next_num, ""); next_num = None
            pending_letter = LETTER_IDX[lm.group(1).lower()]
            mode = "opts"; continue
        if pending_letter is not None and cur:
            cur["options"][pending_letter] = line
            pending_letter = None; continue

        if RE_ROMAN.match(line) and cur is not None:
            parts = list(RE_ROMAN.finditer(line))
            for i, pm in enumerate(parts):
                end = parts[i + 1].start() if i + 1 < len(parts) else len(line)
                txt = RE_ASK.sub("", line[pm.end():end]).strip()
                if txt:
                    cur["statements"].append(txt)
            mode = "stmt"
            if RE_ASK.search(line):
                mode = "stmt_done"
            continue
        if RE_ASK.search(line) and cur is not None:
            rest = RE_ASK.sub("", line).strip()
            rest, b = take_boards(rest)
            cur["boards"] += b
            mode = "stmt_done"; continue

        if mode == "expl" and cur:
            cur["explanation"] += " " + line; continue
        if mode == "opts" and cur:
            last = max((i for i, o in enumerate(cur["options"]) if o), default=None)
            if last is not None and not RE_QNUM.match(line):
                cur["options"][last] += " " + line
            continue
        if mode in ("stem",) and cur:
            cur["stem"] = (cur["stem"] + "\n" + line).strip(); continue
        if mode == "stmt" and cur and cur["statements"]:
            cur["statements"][-1] += " " + line; continue
        if cur is None:
            # implicit question (e.g. a slide without numbering)
            cur = _new(next_num, line); next_num = None
            attach_stim(cur)
            mode = "stem"; continue
    finalize()

    # numbering + stimulus objects
    used = {}
    n = 0
    for q in mcqs:
        n = q["num"] if q["num"] else n + 1
        q["num"] = n
        if q["stimulus"]:
            s = stimuli[q["stimulus"]]
            text, boards = take_boards(s["text"])
            used[q["stimulus"]] = {"id": s["id"], "label": s["label"], "text": text, "boards": boards,
                                   "header": s["header"]}
    for q in mcqs:
        q["type"] = _type(q)
    if not mcqs:
        warnings.append("কোনো MCQ পাওয়া যায়নি — প্রশ্নের নম্বর ও ক/খ/গ/ঘ option ঠিকমতো আছে কিনা দেখো।")
    for q in mcqs:
        if q["answer"] is None:
            warnings.append(f"MCQ {q['num']}: উত্তর পাওয়া যায়নি — review-এ উত্তর বেছে দাও।")
        if sum(1 for o in q["options"] if o.strip()) < 4:
            warnings.append(f"MCQ {q['num']}: ৪টি option পাওয়া যায়নি।")
    return {"mcqs": mcqs, "stimuli": list(used.values()), "warnings": warnings}


def tidy(t):
    t = re.sub(r"\$ +(?=[-–—।,?:;)!])", "$", t)
    t = re.sub(r"(?<=[(])\s+\$", "$", t)
    return re.sub(r"[ \t]{2,}", " ", t).strip()


def _post(q):
    q["stem"] = tidy(q["stem"].replace("\n", "\u2028")).replace("\u2028", "\n")
    q["statements"] = [tidy(x) for x in q["statements"]]
    q["options"] = [tidy(x) for x in q["options"]]
    q["explanation"] = tidy(q["explanation"])
    stem, b = take_boards(q["stem"])
    q["boards"] += b
    # quote / poem at the start of the stem -> its own box
    lines = [l for l in stem.split("\n") if l.strip()]
    if len(lines) >= 2 and lines[0].lstrip()[:1] in QUOTES_OPEN:
        for k in range(len(lines) - 1):
            if lines[k].rstrip()[-1:] in QUOTES_CLOSE or lines[k].rstrip()[-2:-1] in QUOTES_CLOSE:
                quote = "\n".join(lines[:k + 1]).strip().strip(QUOTES_OPEN + QUOTES_CLOSE + " ")
                quote = re.sub(r"[\"”’']\s*$", "", quote)
                q["quote"] = quote
                stem = " ".join(lines[k + 1:])
                break
    q["stem"] = re.sub(r"\s*\n\s*", " ", stem).strip()
    q["statements"] = [re.sub(r"\s+", " ", s).strip() for s in q["statements"]]
    q["options"] = [re.sub(r"\s+", " ", o).strip().rstrip("।") if o else "" for o in q["options"]]
    if q["statements"]:
        q["options"] = [roman_option(o) for o in q["options"]]
    q["explanation"] = q["explanation"].strip()
    q["boards"] = [b for b in q["boards"] if b]


def _type(q):
    if q["statements"]:
        return "roman"
    if q.get("quote"):
        return "quote"
    if q.get("stimulus"):
        return "stimulus"
    return "single"
