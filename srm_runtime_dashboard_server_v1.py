# ======================================================================
#   srm_runtime_dashboard_server_v1.py — Mini servidor HTTP
# ======================================================================
#  Sirve archivos estáticos del dashboard y expone endpoints JSON:
#
#    /health_status
#    /supervisor
#    /autopilot
#    /predictor
#    /memory
#    /logs
#
#  Ejecutar:
#      python srm_runtime_dashboard_server_v1.py
#
#  Abrir en navegador:
#      http://localhost:8080/srm_runtime_dashboard.html
#
# ======================================================================

import http.server
import socketserver
import json
import os

PORT = 8080
BASE = r"C:\SRM_ADSI\05_pipeline"
DASHBOARD = os.path.join(BASE, "dashboard")
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
        if self.path == "/health_status":
            self.respond_json(read_json(os.path.join(HEALTH, "health_status.json")))
        elif self.path == "/supervisor":
            self.respond_json(read_json(os.path.join(HEALTH, "supervisor_report.json")))
        elif self.path == "/autopilot":
            self.respond_json(read_json(os.path.join(HEALTH, "autopilot_log.json")))
        elif self.path == "/predictor":
            self.respond_json(read_json(os.path.join(HEALTH, "ai_predictor_report.json")))
        elif self.path == "/memory":
            data = {
                "short": read_json(os.path.join(MEMORY, "memory_short.json")),
                "context": read_json(os.path.join(MEMORY, "memory_context.json")),
                "long": read_json(os.path.join(MEMORY, "memory_long.json")),
            }
            self.respond_json(data)
        elif self.path == "/logs":
            self.respond_json(read_json(os.path.join(BASE, "runtime_log.json")))
        else:
            self.path = self.path.lstrip("/")
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def respond_json(self, data):
        res = json.dumps(data, indent=4, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(res))
        self.end_headers()
        self.wfile.write(res)

os.chdir(DASHBOARD)
print(f"🌐 SRM Dashboard Server corriendo en: http://localhost:{PORT}/srm_runtime_dashboard.html")

with socketserver.TCPServer(("", PORT), SRMHandler) as httpd:
    httpd.serve_forever()
