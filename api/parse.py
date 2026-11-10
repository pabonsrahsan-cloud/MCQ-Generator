"""POST /api/parse   body: {"filename": "...", "data": "<base64>"}  or  {"text": "..."}
Returns {"mcqs": [...], "stimuli": [...], "warnings": [...]}"""
import base64, json, os, sys, traceback
from http.server import BaseHTTPRequestHandler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _mcqgen.extract import file_lines, txt_lines   # noqa: E402
from _mcqgen.parser import parse_lines              # noqa: E402


def run(body):
    if body.get("text"):
        lines = body["text"].splitlines()
    else:
        lines = file_lines(body.get("filename", "file.txt"), base64.b64decode(body["data"]))
    return parse_lines(lines)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            n = int(self.headers.get("content-length", 0))
            out = json.dumps(run(json.loads(self.rfile.read(n) or b"{}")), ensure_ascii=False).encode()
            code = 200
        except Exception as e:  # report parse errors to the page
            out = json.dumps({"error": str(e), "trace": traceback.format_exc()[-1500:]}, ensure_ascii=False).encode()
            code = 400
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)
