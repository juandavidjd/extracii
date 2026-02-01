# ======================================================================
#     SRM Runtime Dashboard Server v2 — PRO UI
# ======================================================================

import http.server
import socketserver
import json
import os

PORT = 8080
BASE = r"C:\SRM_ADSI\05_pipeline"
DASHBOARD = os.path.join(BASE, "dashboard_pro")
HEALTH = os.path.join(BASE, "health")
MEMORY = os.path.join(HEALTH, "memory")

def read_json(path):
    if not os.path.exists(path):
        return {"error": "Archivo no existe"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"error": "Error leyendo JSON"}

class SRMHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):

        routes = {
            "/health_status": os.path.join(HEALTH, "health_status.json"),
            "/supervisor": os.path.join(HEALTH, "supervisor_report.json"),
            "/autopilot": os.path.join(HEALTH, "autopilot_log.json"),
            "/predictor": os.path.join(HEALTH, "ai_predictor_report.json"),
            "/logs": os.path.join(BASE, "runtime_log.json"),
        }

        if self.path in routes:
            self.respond_json(read_json(routes[self.path]))
            return

        if self.path == "/memory":
            mem = {
                "short": read_json(os.path.join(MEMORY, "memory_short.json")),
                "context": read_json(os.path.join(MEMORY, "memory_context.json")),
                "long": read_json(os.path.join(MEMORY, "memory_long.json")),
            }
            self.respond_json(mem)
            return

        self.path = self.path.lstrip("/")
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def respond_json(self, data):
        body = json.dumps(data, indent=4, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

os.chdir(DASHBOARD)
print(f"SRM Dashboard PRO listo: http://localhost:{PORT}/srm_runtime_dashboard_pro.html")

with socketserver.TCPServer(("", PORT), SRMHandler) as httpd:
    httpd.serve_forever()
