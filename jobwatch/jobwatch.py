#!/usr/bin/env python3
"""
jobwatch.py - personal careers-page monitor (public pages only).

Setup:
  pip install requests beautifulsoup4
  export TG_TOKEN="<bot token from @BotFather>"
  export TG_CHAT="<your chat id>"
  export INCLUDE="java,spring boot,.net,c#,full stack,software engineer,associate,trainee"
  export EXCLUDE="senior,lead,manager,architect,principal,director"
  export LOCATIONS="pune,mumbai,bengaluru,hyderabad,remote,india"   # optional

companies.csv columns:  name,careers_url,type,slug
  type = greenhouse | lever | ashby | smartrecruiters | generic
  (leave type/slug empty and run `detect` to fill them automatically)

Usage:
  python jobwatch.py detect companies.csv            # writes companies_resolved.csv
  python jobwatch.py run companies_resolved.csv      # one pass
  python jobwatch.py run companies_resolved.csv --every 10   # loop every 10 min

First run only records existing jobs (no spam). After that, only NEW jobs alert.
"""
import csv, os, re, sqlite3, sys, time, argparse
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (compatible; PersonalJobWatcher/1.0)"}
DB = "seen.db"
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT = os.getenv("TG_CHAT")
def _env_list(*names):
    for n in names:
        v = os.getenv(n, "")
        if v.strip():
            return [k.strip().lower() for k in v.split(",") if k.strip()]
    return []

def _wb(words):
    # whole-word match so "java" does not match "javascript"
    return [re.compile(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", re.I) for w in words]

INCLUDE = _wb(_env_list("INCLUDE", "KEYWORDS"))   # title must match at least one (empty = allow all)
EXCLUDE = _wb(_env_list("EXCLUDE"))               # title must match none (e.g. senior,lead,manager)
LOCATIONS = _env_list("LOCATIONS")                # e.g. pune,mumbai,bengaluru,remote,india

def relevant(title):
    head, _, loc = title.partition(" | ")
    if INCLUDE and not any(rx.search(head) for rx in INCLUDE):
        return False
    if EXCLUDE and any(rx.search(head) for rx in EXCLUDE):
        return False
    loc = loc.strip().lower()
    if LOCATIONS and loc and not any(l in loc for l in LOCATIONS):
        return False   # location check only when the source gives a location
    return True
WORKERS = 8          # keep modest; be polite to servers
TIMEOUT = 20

JOBISH = re.compile(r"(job|career|opening|position|requisition|vacanc|apply|/jobs?/|/careers?/)", re.I)
SKIP = re.compile(r"(login|signin|sign-in|register|privacy|cookie|linkedin\.com|facebook|twitter|instagram|youtube|mailto:|tel:|javascript:|#$)", re.I)


# ---------- fetchers: each returns list of (job_id, title, url) ----------
def get(url):
    r = requests.get(url, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    return r

def f_greenhouse(c):
    d = get(f"https://boards-api.greenhouse.io/v1/boards/{c['slug']}/jobs").json()
    return [(str(j["id"]), j["title"] + " | " + (j.get("location") or {}).get("name", ""), j["absolute_url"])
            for j in d.get("jobs", [])]

def f_lever(c):
    d = get(f"https://api.lever.co/v0/postings/{c['slug']}?mode=json").json()
    return [(j["id"], j["text"] + " | " + (j.get("categories") or {}).get("location", ""), j["hostedUrl"]) for j in d]

def f_ashby(c):
    d = get(f"https://api.ashbyhq.com/posting-api/job-board/{c['slug']}").json()
    return [(j["id"], j["title"] + " | " + (j.get("location") or ""), j["jobUrl"]) for j in d.get("jobs", [])]

def f_smartrecruiters(c):
    d = get(f"https://api.smartrecruiters.com/v1/companies/{c['slug']}/postings?limit=100").json()
    return [(j["id"], j["name"] + " | " + (j.get("location") or {}).get("city", ""),
             f"https://jobs.smartrecruiters.com/{c['slug']}/{j['id']}") for j in d.get("content", [])]

def f_generic(c):
    """Fallback: diff job-looking links on the page. Works for static pages only;
    JS-rendered portals (Workday, custom SPAs) may return nothing."""
    base = c["careers_url"]
    soup = BeautifulSoup(get(base).text, "html.parser")
    out = {}
    for a in soup.find_all("a", href=True):
        href = urljoin(base, a["href"])
        text = " ".join(a.get_text().split())
        if SKIP.search(href) or href.rstrip("/") == base.rstrip("/"):
            continue
        if JOBISH.search(href) or JOBISH.search(text):
            if len(text) >= 4:
                out[href] = (href, text[:120], href)
    return list(out.values())

FETCHERS = {"greenhouse": f_greenhouse, "lever": f_lever, "ashby": f_ashby,
            "smartrecruiters": f_smartrecruiters, "generic": f_generic}


# ---------- detection ----------
DETECT = [
    ("greenhouse", re.compile(r"(?:boards|job-boards)\.greenhouse\.io/(?:embed/job_board\?for=)?([\w-]+)", re.I)),
    ("lever", re.compile(r"jobs\.lever\.co/([\w-]+)", re.I)),
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/([\w.-]+)", re.I)),
    ("smartrecruiters", re.compile(r"(?:jobs|careers)\.smartrecruiters\.com/([\w-]+)", re.I)),
]

def detect_one(row):
    if row.get("type"):
        return row
    row["type"], row["slug"] = "generic", ""
    try:
        html = get(row["careers_url"]).text
        for t, rx in DETECT:
            m = rx.search(html)
            if m and m.group(1).lower() not in ("embed", "jobs"):
                row["type"], row["slug"] = t, m.group(1)
                break
    except Exception as e:
        print(f"[detect fail] {row['name']}: {e}")
    return row

def cmd_detect(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    for r in rows:
        r.setdefault("type", ""); r.setdefault("slug", "")
    with ThreadPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(detect_one, rows))
    out = path.replace(".csv", "_resolved.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "careers_url", "type", "slug"])
        w.writeheader(); w.writerows({k: r.get(k, "") for k in w.fieldnames} for r in rows)
    from collections import Counter
    print(Counter(r["type"] for r in rows), "->", out)
    print("'generic' rows are page-diff only; check them manually for a better source.")


# ---------- notify ----------
def notify(company, title, url):
    msg = f"🆕 {company}\n{title}\n{url}"
    if TG_TOKEN and TG_CHAT:
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                          data={"chat_id": TG_CHAT, "text": msg, "disable_web_page_preview": True}, timeout=15)
            time.sleep(0.4)  # telegram rate limit
        except Exception as e:
            print("telegram error:", e)
    print(msg, "\n")


# ---------- main loop ----------
def check(c):
    try:
        return c, FETCHERS[c.get("type") or "generic"](c), None
    except Exception as e:
        return c, [], str(e)

def run_once(path, db):
    companies = list(csv.DictReader(open(path, encoding="utf-8")))
    with ThreadPoolExecutor(WORKERS) as ex:
        results = list(ex.map(check, companies))
    new_total = 0
    for c, jobs, err in results:
        if err:
            print(f"[err] {c['name']}: {err[:100]}")
            continue
        name = c["name"]
        known = {r[0] for r in db.execute("SELECT job_id FROM seen WHERE company=?", (name,))}
        first_time = not known
        for jid, title, url in jobs:
            if jid in known:
                continue
            db.execute("INSERT OR IGNORE INTO seen VALUES (?,?,?)", (name, jid, title))
            if first_time:
                continue  # seed silently
            if not relevant(title):
                continue
            notify(name, title, url)
            new_total += 1
        db.commit()
    print(f"[{time.strftime('%H:%M:%S')}] checked {len(companies)} companies, {new_total} new alerts")

def cmd_run(path, every):
    db = sqlite3.connect(DB)
    db.execute("CREATE TABLE IF NOT EXISTS seen (company TEXT, job_id TEXT, title TEXT, PRIMARY KEY(company, job_id))")
    while True:
        run_once(path, db)
        if not every:
            break
        time.sleep(every * 60)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["detect", "run"])
    p.add_argument("csv")
    p.add_argument("--every", type=int, default=0, help="loop interval in minutes")
    a = p.parse_args()
    cmd_detect(a.csv) if a.cmd == "detect" else cmd_run(a.csv, a.every)
