import os, sys, json, threading, http.server, tempfile
d = tempfile.mkdtemp(); os.environ.update(JOBWATCH_DIR=d, JOBWATCH_PASSWORD="pw", JOBWATCH_ALLOW_PRIVATE="1")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
EXTRA=[]
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(s):
        s.send_response(200); s.send_header("Content-Type", "text/html"); s.end_headers()
        s.wfile.write(b'<a href="/jobs/1">Java Developer</a>'+b''.join(EXTRA)+b'<a href="/jobs/2">Sales Manager</a><a href="/jobs/3">Senior Java Lead</a><a href="/about">About</a>')
    def log_message(*a): pass
srv = http.server.HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_port}/careers"
import app; from fastapi.testclient import TestClient
c = TestClient(app.app); a = ("admin", "pw")
assert c.get("/api/state").status_code == 401 and c.get("/api/state", auth=("admin","x")).status_code == 401
r = c.post("/api/companies/bulk", json={"urls": [url, url, "ftp://x.com", "javascript:alert(1)"]}, auth=a).json(); print("bulk", r)
app.ALLOW_PRIVATE = False
r2 = c.post("/api/companies/bulk", json={"urls": ["http://169.254.169.254/latest/meta-data", "http://localhost:8080/x", "http://127.0.0.1/"]}, auth=a).json(); print("ssrf", r2["rejected"])
app.ALLOW_PRIVATE = True
c.post("/api/prefs", json={"include": "java", "exclude": "senior", "interval": 5}, auth=a)
app.run_once(); s = c.get("/api/state", auth=a).json(); co = s["companies"][0]; print("run1", co["status"], co["count"], co["new"])
name = co["name"]
EXTRA.append(b'<a href="/jobs/9">Spring Boot Java Trainee</a><a href="/jobs/10">Senior Java Architect</a>')
app.run_once(); co = c.get("/api/state", auth=a).json()["companies"][0]; print("run2 new:", co["new"]); assert co["new"] == ["Spring Boot Java Trainee"]
assert co["status"] == "ok" and co["count"] == 5
f = c.post("/api/flag", json={"name": name, "reason": "wrong titles"}, auth=a); s = c.get("/api/state", auth=a).json()
print("flag", f.status_code, s["companies"], s["flagged"][0]["name"], s["flagged"][0]["reason"])
assert open(d + "/companies.csv").read().strip().count("\n") == 0
import jobwatch as jw
for t in ["Java Developer | Pune", "JavaScript Dev", "Senior Java | Pune"]: print(t, jw.relevant(t))
