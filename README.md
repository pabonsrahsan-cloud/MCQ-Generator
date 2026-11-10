# MCQ Slide Generator (Shikho MCQ template)

যেকোনো **.docx / .pptx / .pdf / .txt** ফাইল (বা paste করা লেখা) থেকে MCQ বের করে, ওয়েব পেজে দেখে ঠিক করে,
Shikho-র MCQ template-এর format-এ **.pptx** বানায়।

- প্রশ্ন ও উত্তর slide (সঠিক option নীল + ✓), বোর্ডের pink tag, i/ii/iii panel, উদ্দীপক/উদ্ধৃতি box, কোড box
- বাঁ দিক ফাঁকা থাকে (লাইভ সমাধানের জায়গা), option ডানে এক কলামে; সব লেখা কমপক্ষে 54pt; কিছুই 20 inch লাইনের নিচে যায় না
- Word/PowerPoint-এর equation আপনা-আপনি PowerPoint equation হয়ে আসে (সাথে ছবি-fallback, তাই কোথাও ভাঙে না)
- কোনো AI/API লাগে না — নিয়ম দিয়ে পড়ে, পুরোপুরি ফ্রি

---

## ১. GitHub-এ তোলা

**সবচেয়ে সহজ (ব্রাউজার দিয়ে):**
1. https://github.com → উপরে ডানে **+** → **New repository** → নাম দাও (যেমন `mcq-generator`) → **Private** বা Public → **Create repository**।
2. নতুন repo-র পেজে **uploading an existing file** লিংকে ক্লিক করো।
3. এই zip খুলে ভেতরের **সব ফাইল ও ফোল্ডার** (`api`, `public`, `samples`, `requirements.txt`, `vercel.json`, `README.md`, `.gitignore`, `local_server.py`) টেনে এনে ছেড়ে দাও।
   ⚠ zip ফাইলটা নিজে না, ভেতরের জিনিসগুলো দিতে হবে। `api/_mcqgen/assets` ফোল্ডারটা যেন বাদ না পড়ে।
4. নিচে **Commit changes**।

**অথবা git দিয়ে (Terminal):**
```bash
cd mcq-generator
git init
git add .
git commit -m "MCQ slide generator"
git branch -M main
git remote add origin https://github.com/<তোমার-username>/mcq-generator.git
git push -u origin main
```

## ২. Vercel-এ deploy

1. https://vercel.com → **Sign Up / Log in** → **Continue with GitHub**।
2. Dashboard-এ **Add New… → Project** → তালিকা থেকে `mcq-generator` repo-র পাশে **Import**।
   (repo না দেখালে **Adjust GitHub App Permissions** থেকে repo-টার access দাও।)
3. **Framework Preset: Other** রাখো। Build Command / Output Directory **খালি** থাকবে — কিছু বদলাতে হবে না।
4. **Deploy** চাপো। ২–৪ মিনিট লাগবে (প্রথমবার Python package install হয়)।
5. শেষ হলে `https://mcq-generator-xxxx.vercel.app` ধরনের লিংক পাবে — এটাই তোমার app।
   চাইলে **Settings → Domains** থেকে নিজের নাম দিতে পারো।

এরপর GitHub-এ যেকোনো পরিবর্তন push/commit করলেই Vercel নিজে থেকে নতুন version deploy করবে।

## ৩. ব্যবহার

1. ফাইল টেনে আনো (বা লেখা paste করো) → MCQ-গুলো কার্ড আকারে আসবে।
2. প্রতিটা কার্ডে ঠিক করো: ধরন, প্রশ্ন, option, **সবুজ বৃত্তে সঠিক উত্তর**, বোর্ড, উদ্দীপক, ব্যাখ্যা। হলুদ বক্সে যেগুলোর উত্তর / option পাওয়া যায়নি সেগুলো দেখাবে।
3. উপরে অধ্যায়ের নাম দাও (slide-এর উপরে বাঁয়ে বসবে)।
4. **PPT বানাও** → .pptx download।
5. কাজ মাঝপথে রাখতে **JSON সেভ**, পরে **JSON খোলো**।

### ফাইল কেমন হলে সবচেয়ে ভালো পড়ে
```
১. প্রশ্ন ... [ঢা. বো. ২৩; রা. বো. ২২]
(ক) ... (খ) ...
(গ) ... (ঘ) ...
উত্তর: খ
ব্যাখ্যা: ...

২. ... ক্ষেত্রে—
i. ...
ii. ...
iii. ...
নিচের কোনটি সঠিক?
(ক) i ও ii (খ) i ও iii (গ) ii ও iii (ঘ) i, ii ও iii
উত্তর: ক

নিচের উদ্দীপকটি পড়ে ৩০ ও ৩১ নম্বর প্রশ্নের উত্তর দাও:
উদ্দীপকের লেখা ... [য. বো. ১৯]
৩০. ...
```
- option: `(ক)` `ক.` `ক)` `A.` `(a)` — এক লাইনে একাধিক থাকলেও চলবে; A–D আপনা-আপনি ক–ঘ হয়
- বোর্ড: `[দিনাজপুর বোর্ড, ২০২৫]` লিখলেও `দি. বো. ২৫` হয়ে যায়; সব বোর্ডে একই সালে হলে `[সকল বোর্ড ২৩]`
- কবিতা/উদ্ধৃতি: প্রশ্নের শুরুতে উদ্ধৃতি চিহ্নের ভেতরে আলাদা লাইনে
- সমীকরণ নিজে লিখতে: `$\frac{1}{2}$`, `$\vec{P}=2\hat{i}+n\hat{j}$`, `$x^{2}$`, `$\sqrt{2}$`, `$\overline{A+B}$`, `$A\oplus B$`
- নমুনা: `samples/sample_mcq.txt`

## ৪. নিজের কম্পিউটারে চালানো (ঐচ্ছিক)
```bash
pip install -r requirements.txt
python local_server.py        # তারপর ব্রাউজারে http://localhost:8000
```

## ৫. সীমাবদ্ধতা
- আপলোড ফাইল সর্বোচ্চ **৩ MB** (Vercel-এর ৪.৫ MB request সীমার কারণে)। বড় ফাইল ভাগ করে দাও।
- একবারে খুব বেশি MCQ (≈৬০+) দিলে PPT ৪.৫ MB ছাড়াতে পারে — দুই ভাগে বানাও।
- PDF থেকে বাংলা লেখা অনেক সময় ভাঙা আসে (PDF-এর font encoding-এর কারণে) — সম্ভব হলে .docx দাও।
- চিত্র / circuit / সারণি আপনা-আপনি আসে না; কোডের জন্য কার্ডে **কোড** ঘর আছে। চিত্র লাগলে PPT-তে বাঁ দিকে ছবি বসিয়ে নাও।
- প্রথম request-এ কয়েক সেকেন্ড বেশি লাগে (Vercel cold start)।

## ৬. Template বদলাতে চাইলে
`api/_mcqgen/assets/base.pptx` হলো slide master (header, logo, background)। অন্য class/বিষয়ের master দিয়ে এটা বদলে দিলেই হবে
(slide ছাড়া শুধু master/layout রাখা .pptx)। master-এ `বাক্যতত্ত্ব` লেখাটা অধ্যায়ের নাম দিয়ে আপনা-আপনি বদলে যায়।

## ফোল্ডার
```
api/parse.py            POST /api/parse     ফাইল → MCQ (JSON)
api/generate.py         POST /api/generate  MCQ (JSON) → .pptx
api/_mcqgen/extract.py  docx/pptx/pdf/txt → লাইন (equation → LaTeX)
api/_mcqgen/parser.py   লাইন → MCQ (নিয়মগুলো এখানে)
api/_mcqgen/deck.py     auto-layout ও slide বানানো
api/_mcqgen/ooxml.py    shape, table, equation (+ ছবি-fallback)
api/_mcqgen/latex_omml.py  LaTeX ↔ PowerPoint equation
api/_mcqgen/assets/     base.pptx, Hind Siliguri font (SIL OFL), libfribidi (LGPL-2.1; বাংলা লেখার shaping-এর জন্য)
public/index.html       ওয়েব পেজ
vercel.json             function-এর সময়/মেমরি ও assets যুক্ত করা
```
