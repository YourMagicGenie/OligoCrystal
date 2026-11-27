"""OligoCrystal Crystal Gallery curator: a local-only app for choosing,
ordering and publishing gallery crystals.

    python -I tools/curate.py        (or double-click Curate.cmd)

Opens http://127.0.0.1:8761/ . Everything stays on this computer: decisions are
saved in .local/curation.json, thumbnails in .local/thumbs/.
"""
import csv, hashlib, io, json, os, subprocess, sys, threading, time, traceback, webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gallery_lib as lib  # noqa: E402
import scan  # noqa: E402

PORT = 8761
HERE = Path(__file__).resolve().parent
LOCK = threading.RLock()
JOB = {"name": None, "log": [], "running": False}


def key_of(src):
    return hashlib.sha1(src.encode("utf-8")).hexdigest()[:16]


# ---------- curation data ----------

def taken(src):
    try:
        e = lib.Image.open(src).getexif()
        v = e.get_ifd(0x8769).get(36867) or e.get(306)
        if v:
            return str(v)[:19].replace(":", "-", 2)
    except Exception:
        pass
    return datetime.fromtimestamp(os.path.getmtime(src)).strftime("%Y-%m-%d %H:%M:%S")


def ensure_thumb(src, item=None):
    """Make the 300 px thumbnail; fill in date and similarity hash if missing."""
    t = lib.THUMBS / f"{key_of(src)}.jpg"
    if t.exists() and item is not None and item.get("h") is not None and item.get("date"):
        return t
    im = lib.open_image(src, small=True)
    if item is not None:
        item["h"] = format(lib.dhash(im), "016x")
        item.setdefault("date", taken(src))
    if not t.exists():
        lib.THUMBS.mkdir(parents=True, exist_ok=True)
        c = im.copy()
        c.thumbnail((300, 300))
        c.save(t, "JPEG", quality=80)
    return t


def plausible(r):
    p = r["path"].lower()
    if p.endswith(".png") or "screenshot" in p:
        return False
    w, h = int(r["w"] or 0), int(r["h"] or 0)
    return not (w and h and max(w, h) / min(w, h) > 1.9)


def migrate(cur):
    """One-time: bring in the first hand-made selection and its catalogue numbers."""
    sel, ids_file = lib.LOCAL / "selection.tsv", lib.LOCAL / "ids.json"
    if cur["items"] or not sel.exists():
        return
    ids = json.loads(ids_file.read_text(encoding="utf-8")) if ids_file.exists() else {}
    for line in sel.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        src = parts[0].strip()
        cur["items"][src] = {"state": "shown", "star": len(parts) > 1 and parts[1].strip() == "hero",
                             "id": ids.get(src), "score": None}
        cur["order"].append(src)


def import_candidates(log):
    cfg = lib.config()
    incoming = [os.path.normcase(os.path.abspath(d)) for d in cfg["incoming"]]
    with LOCK:
        cur = lib.load_curation()
        migrate(cur)
    added = []
    if lib.SCORES.exists():
        with open(lib.SCORES, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["error"] or r["path"] in cur["items"] or not os.path.exists(r["path"]):
                    continue
                s = max(float(r["circle"]) * 2, float(r["polar"]))
                inc = any(os.path.normcase(r["path"]).startswith(d) for d in incoming)
                if inc or (s >= cfg["inbox_threshold"] and plausible(r)):
                    added.append((r["path"], s))
    log(f"{len(added)} new candidates for the Inbox; making thumbnails…")
    new_items = {}

    def work(arg):
        src, s = arg
        item = {"state": "inbox", "star": False, "id": None, "score": round(s, 3)}
        try:
            ensure_thumb(src, item)
        except Exception:
            return None
        return src, item

    with ThreadPoolExecutor(max_workers=max(2, (os.cpu_count() or 4) - 2)) as ex:
        for i, res in enumerate(ex.map(work, added), 1):
            if res:
                new_items[res[0]] = res[1]
            if i % 200 == 0:
                log(f"  {i}/{len(added)} thumbnails")
    # Thumbnails for anything already in the list that lacks one.
    with LOCK:
        cur = lib.load_curation()
        migrate(cur)
        for src, it in cur["items"].items():
            if it.get("h") is None and os.path.exists(src):
                try:
                    ensure_thumb(src, it)
                except Exception:
                    pass
        for src, it in new_items.items():
            cur["items"].setdefault(src, it)
        regroup(cur)
        lib.save_curation(cur)
    log(f"Inbox now has {sum(1 for i in cur['items'].values() if i['state'] == 'inbox')} photos.")


def regroup(cur):
    """Burst shots are taken seconds apart and look alike: walk all photos in
    time order and give runs of similar neighbours the same group number."""
    items = sorted(cur["items"].items(), key=lambda kv: kv[1].get("date") or "")
    g, prev = 0, None
    for src, it in items:
        h = int(it["h"], 16) if it.get("h") else None
        if not (prev is not None and h is not None and lib.similar(prev, h, 12)):
            g += 1
        it["group"] = g
        prev = h


# ---------- background jobs ----------

def run_job(name, fn):
    with LOCK:
        if JOB["running"]:
            return False
        JOB.update(name=name, log=[], running=True)

    def log(msg):
        JOB["log"].append(f"{time.strftime('%H:%M:%S')}  {msg}")
        JOB["log"] = JOB["log"][-200:]

    def target():
        try:
            fn(log)
            log("Done.")
        except Exception as e:
            log(f"Failed: {e}")
            log(traceback.format_exc(limit=3))
        finally:
            JOB["running"] = False

    threading.Thread(target=target, daemon=True).start()
    return True


def job_scan(log):
    scan.run(log)
    import_candidates(log)


def job_publish(log):
    log("Building the site from the Gallery order…")
    p = subprocess.run([sys.executable, "-I", str(HERE / "build_gallery.py")],
                       cwd=lib.ROOT, capture_output=True, text=True, encoding="utf-8")
    for line in (p.stdout + p.stderr).strip().splitlines()[-15:]:
        log(line)
    if p.returncode:
        raise RuntimeError("build failed")
    t = subprocess.run(["node", "--test", "test/site.test.mjs"], cwd=lib.ROOT, capture_output=True, text=True)
    log("Site checks passed." if t.returncode == 0 else "Site checks FAILED: " + t.stdout[-400:])
    log("Preview it with Preview site; nothing is online until you deploy.")


# ---------- HTTP ----------

def state_payload():
    with LOCK:
        cur = lib.load_curation()
        migrate(cur)
    pos = {src: i for i, src in enumerate(cur["order"])}
    out = []
    for src, it in cur["items"].items():
        p = Path(src)
        out.append({"k": key_of(src), "name": p.name, "folder": str(p.parent), "state": it["state"],
                    "star": bool(it.get("star")), "id": it.get("id"), "score": it.get("score"),
                    "date": it.get("date"), "group": it.get("group"), "pos": pos.get(src)})
    return {"items": out, "job": {"name": JOB["name"], "running": JOB["running"], "log": JOB["log"][-30:]}}


def apply_changes(body):
    with LOCK:
        cur = lib.load_curation()
        migrate(cur)
        by_key = {key_of(s): s for s in cur["items"]}
        srcs = [by_key[k] for k in body.get("keys", []) if k in by_key]
        act = body.get("action")
        for s in srcs:
            it = cur["items"][s]
            if act == "show":
                it["state"] = "shown"
            elif act == "hide":
                it["state"], it["star"] = "hidden", False
            elif act == "inbox":
                it["state"], it["star"] = "inbox", False
            elif act == "star":
                it["star"], it["state"] = True, "shown"
            elif act == "unstar":
                it["star"] = False
        order = [s for s in cur["order"] if cur["items"][s]["state"] == "shown"]
        if act in ("show", "star", "top"):
            # Newly added or "move to top": put them first, in the order given.
            order = [s for s in srcs if cur["items"][s]["state"] == "shown"] + [s for s in order if s not in srcs]
        elif act == "bottom":
            order = [s for s in order if s not in srcs] + [s for s in srcs if cur["items"][s]["state"] == "shown"]
        elif act == "order":
            given = [s for s in srcs if cur["items"][s]["state"] == "shown"]
            order = given + [s for s in order if s not in given]
        for s, it in cur["items"].items():  # anything shown but unordered goes last
            if it["state"] == "shown" and s not in order:
                order.append(s)
        cur["order"] = order
        lib.save_curation(cur)


class Server(ThreadingHTTPServer):
    # Windows lets a second server silently share a port when address reuse is
    # on; refuse instead, so a clash is reported rather than hidden.
    allow_reuse_address = False
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body=b"", ctype="application/json", cache=False):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "max-age=86400" if cache else "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def local_host(self):
        return self.headers.get("Host", "") in (f"127.0.0.1:{PORT}", f"localhost:{PORT}")

    def do_GET(self):
        if not self.local_host():
            return self.send(403)
        path = urlparse(self.path).path
        if path == "/":
            return self.send(200, (HERE / "curator.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/state":
            return self.send(200, json.dumps(state_payload()).encode())
        if path.startswith("/t/") or path.startswith("/v/"):
            k = path[3:].split(".")[0]
            with LOCK:
                cur = lib.load_curation()
            src = next((s for s in cur["items"] if key_of(s) == k), None)  # only listed photos
            if not src or not os.path.exists(src):
                return self.send(404)
            try:
                if path.startswith("/t/"):
                    return self.send(200, ensure_thumb(src).read_bytes(), "image/jpeg", cache=True)
                im = lib.open_image(src)
                im.thumbnail((1400, 1400))
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=85)
                return self.send(200, buf.getvalue(), "image/jpeg", cache=True)
            except Exception:
                return self.send(500)
        return self.send(404)

    def do_POST(self):
        # Only the curator page can make changes: it sends this header, which a
        # page on another site cannot add without a CORS preflight we never allow.
        if not self.local_host() or self.headers.get("X-Curator") != "1":
            return self.send(403)
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        path = urlparse(self.path).path
        if path == "/api/change":
            apply_changes(body)
            return self.send(200, json.dumps(state_payload()).encode())
        if path in ("/api/scan", "/api/import", "/api/publish"):
            fn = {"/api/scan": job_scan, "/api/import": import_candidates, "/api/publish": job_publish}[path]
            ok = run_job(path[5:], fn)
            return self.send(200 if ok else 409, json.dumps({"started": ok}).encode())
        return self.send(404)


def preview_server():
    """Serve site/ on :8762 the way Cloudflare does (/gallery -> gallery.html)."""
    from functools import partial
    from http.server import SimpleHTTPRequestHandler

    class Site(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def send_head(self):
            p = urlparse(self.path).path
            if p != "/" and "." not in p.rsplit("/", 1)[-1] and (lib.SITE / (p.lstrip("/") + ".html")).exists():
                self.path = p + ".html"
            return super().send_head()

    srv = Server(("127.0.0.1", PORT + 1), partial(Site, directory=str(lib.SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()


if __name__ == "__main__":
    lib.config()
    preview_server()
    srv = Server(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Curator running at {url}  (close this window to stop)", flush=True)
    if "--no-browser" not in sys.argv:
        webbrowser.open(url)
    srv.serve_forever()
