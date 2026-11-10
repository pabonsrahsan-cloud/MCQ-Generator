"""POST /api/generate   body: {"mcqs": [...], "stimuli": [...], "chapter": "...", "answer_slides": true}
Returns the .pptx file."""
import json, os, sys, traceback
from http.server import BaseHTTPRequestHandler
from urllib.parse import quote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _mcqgen.deck import build   # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            n = int(self.headers.get("content-length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
            data, warnings = build(body.get("mcqs", []), body.get("stimuli", []), body.get("chapter") or None,
                                   body.get("answer_slides", True))
            name = (body.get("filename") or "MCQ_slides") + ".pptx"
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.presentationml.presentation")
            self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + quote(name))
            self.send_header("X-Warnings", quote(json.dumps(warnings, ensure_ascii=False)))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            out = json.dumps({"error": str(e), "trace": traceback.format_exc()[-1500:]}, ensure_ascii=False).encode()
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
