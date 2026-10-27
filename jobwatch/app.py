"""JobWatch web app: uvicorn app:app --host 0.0.0.0 --port 8080
Env: JOBWATCH_PASSWORD (user: admin; random one is printed if unset), JOBWATCH_DIR (data dir)."""
import csv, os, re, json, time, socket, secrets, sqlite3, ipaddress, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse, urljoin
import requests
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import jobwatch as jw

D = Path(os.getenv("JOBWATCH_DIR", ".")); CSV, FLAG = D / "companies.csv", D / "flagged.csv"
PREFS, RES = D / "prefs.json", D / "results.json"
FIELDS = ["name", "careers_url", "type", "slug"]
LOCK, RUN_LOCK, WAKE = threading.Lock(), threading.Lock(), threading.Event()
ALLOW_PRIVATE = os.getenv("JOBWATCH_ALLOW_PRIVATE") == "1"   # tests only
PW = os.getenv("JOBWATCH_PASSWORD") or secrets.token_urlsafe(10)
if not os.getenv("JOBWATCH_PASSWORD"): print("JobWatch login -> user: admin  password:", PW)

# ---- safe fetching (SSRF guard, redirect re-check, size cap) ----
def check_url(u):
    p = urlparse(u)
    if p.scheme not in ("http", "https") or not p.hostname: raise ValueError("invalid url")
    if ALLOW_PRIVATE: return
    for ai in socket.getaddrinfo(p.hostname, None):
        if not ipaddress.ip_address(ai[4][0].split("%")[0]).is_global: raise ValueError("private/internal address blocked")

def safe_get(url, **kw):
    for _ in range(5):
        check_url(url)
        r = requests.get(url, headers=jw.UA, timeout=jw.TIMEOUT, allow_redirects=False, stream=True)
        if r.is_redirect and r.headers.get("location"):
            url = urljoin(url, r.headers["location"]); continue
        r.raise_for_status()
        r._content, r._content_consumed = r.raw.read(2_000_000, decode_content=True), True
        return r
    raise ValueError("too many redirects")
jw.get = safe_get

# ---- storage ----
def load(p): return list(csv.DictReader(open(p, encoding="utf-8"))) if p.exists() else []
def save(p, rows):
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS + (["reason"] if p == FLAG else []), extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    os.replace(tmp, p)
def prefs():
    d = {"include": "", "exclude": "", "locations": "", "interval": 10, "tg_token": "", "tg_chat": ""}
    if PREFS.exists(): d.update(json.loads(PREFS.read_text()))
    split = lambda s: [x.strip().lower() for x in s.split(",") if x.strip()]
    jw.INCLUDE, jw.EXCLUDE, jw.LOCATIONS = jw._wb(split(d["include"])), jw._wb(split(d["exclude"])), split(d["locations"])
    jw.TG_TOKEN, jw.TG_CHAT = d["tg_token"] or os.getenv("TG_TOKEN"), d["tg_chat"] or os.getenv("TG_CHAT")
    return d

# ---- polling ----
def classify(c, jobs, err):
    if err: return "blocked" if re.search(r"\b(403|429|503)\b|captcha", err, re.I) else "error"
    if jobs: return "ok"
    return "needs_js_or_empty" if (c.get("type") or "generic") == "generic" else "empty"

def run_once():
    with RUN_LOCK:
        prefs(); rows = load(CSV); db = sqlite3.connect(D / "seen.db")
        db.execute("CREATE TABLE IF NOT EXISTS seen (company TEXT, job_id TEXT, title TEXT, PRIMARY KEY(company, job_id))")
        with ThreadPoolExecutor(8) as ex: out = list(ex.map(jw.check, rows))
        res = {}
        for c, jobs, err in out:
            known = {r[0] for r in db.execute("SELECT job_id FROM seen WHERE company=?", (c["name"],))}
            new = []
            for jid, title, url in jobs:
                if jid in known: continue
                db.execute("INSERT OR IGNORE INTO seen VALUES (?,?,?)", (c["name"], jid, title))
                if known and jw.relevant(title): jw.notify(c["name"], title, url); new.append(title)
            res[c["name"]] = {"status": classify(c, jobs, err), "count": len(jobs), "error": (err or "")[:150], "new": new,
                              "sample": [{"title": t, "url": u} for _, t, u in jobs[:5]], "checked": time.strftime("%d %b %H:%M")}
        db.commit(); db.close(); RES.write_text(json.dumps(res))

def loop():
    while True:
        try: run_once()
        except Exception as e: print("run failed:", e)
        WAKE.wait(max(1, int(prefs()["interval"])) * 60); WAKE.clear()

# ---- API ----
app = FastAPI(); sec = HTTPBasic()
def auth(c: HTTPBasicCredentials = Depends(sec)):
    if not (secrets.compare_digest(c.username, "admin") and secrets.compare_digest(c.password, PW)):
        raise HTTPException(401, headers={"WWW-Authenticate": "Basic"})
@app.on_event("startup")
def _s(): threading.Thread(target=loop, daemon=True).start()

@app.get("/")
def index(_=Depends(auth)): return FileResponse(Path(__file__).parent / "index.html")

@app.get("/api/state")
def state(_=Depends(auth)):
    p = prefs(); res = json.loads(RES.read_text()) if RES.exists() else {}
    p["tg_token"] = "set" if p["tg_token"] else ""
    return {"prefs": p, "flagged": load(FLAG), "companies": [{**r, **res.get(r["name"], {"status": "pending"})} for r in load(CSV)]}

class Prefs(BaseModel): include: str = ""; exclude: str = ""; locations: str = ""; interval: int = 10; tg_token: str = ""; tg_chat: str = ""
@app.post("/api/prefs")
def set_prefs(p: Prefs, _=Depends(auth)):
    old = json.loads(PREFS.read_text()) if PREFS.exists() else {}
    d = p.dict(); d["tg_token"] = d["tg_token"] if d["tg_token"] not in ("", "set") else old.get("tg_token", "")
    PREFS.write_text(json.dumps(d)); prefs(); return {"ok": True}

class Bulk(BaseModel): urls: list[str]
def name_from(u, taken):
    parts = [x for x in urlparse(u).hostname.split(".") if x not in ("www", "careers", "career", "jobs", "com", "in", "co", "org", "net", "io")]
    n = (parts[0] if parts else urlparse(u).hostname).capitalize()
    return n if n not in taken else urlparse(u).hostname
@app.post("/api/companies/bulk")
def bulk(b: Bulk, _=Depends(auth)):
    with LOCK:
        rows, taken = load(CSV), {r["name"] for r in load(CSV)}
        urls = {r["careers_url"].rstrip("/") for r in rows}; new, rejected = [], []
        for u in [x.strip() for x in b.urls if x.strip()][:50]:
            if re.match(r"(javascript|data|mailto|file|vbscript):", u, re.I) or ("://" in u and not re.match(r"https?://", u, re.I)):
                rejected.append({"url": u, "why": "only http(s) links allowed"}); continue
            u = u if re.match(r"https?://", u, re.I) else "https://" + u
            try: check_url(u)
            except Exception as e: rejected.append({"url": u, "why": str(e)}); continue
            if u.rstrip("/") in urls: rejected.append({"url": u, "why": "already added"}); continue
            urls.add(u.rstrip("/")); n = name_from(u, taken); taken.add(n)
            new.append({"name": n, "careers_url": u, "type": "", "slug": ""})
        with ThreadPoolExecutor(8) as ex: new = list(ex.map(jw.detect_one, new))
        save(CSV, rows + new)
    WAKE.set(); return {"added": new, "rejected": rejected}

class Flag(BaseModel): name: str; reason: str = ""
@app.post("/api/flag")
def flag(f: Flag, _=Depends(auth)):
    with LOCK:
        rows = load(CSV); hit = [r for r in rows if r["name"] == f.name]
        if not hit: raise HTTPException(404, "company not found")
        save(CSV, [r for r in rows if r["name"] != f.name]); hit[0]["reason"] = f.reason
        save(FLAG, load(FLAG) + hit)
    return {"ok": True}

@app.post("/api/run")
def run_now(_=Depends(auth)): WAKE.set(); return {"ok": True}
