"""Run the whole app on your own computer:   python local_server.py   then open http://localhost:8000"""
import http.server, os, sys, importlib.util

ROOT = os.path.dirname(os.path.abspath(__file__))


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "api", name + ".py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.handler


HANDLERS = {"/api/parse": load("parse"), "/api/generate": load("generate")}


class Router(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=os.path.join(ROOT, "public"), **kw)

    def do_POST(self):
        h = HANDLERS.get(self.path.split("?")[0])
        if not h:
            self.send_error(404); return
        h.do_POST(self)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"http://localhost:{port}")
    http.server.ThreadingHTTPServer(("", port), Router).serve_forever()
