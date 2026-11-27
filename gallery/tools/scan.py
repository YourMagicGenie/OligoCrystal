"""Find microscope crystal shots in the photo libraries.

Scores every photo once (results kept in .local/scores.csv), so later runs
only look at new photos. Two cues on a ~128 px preview:
  circle: bright round field on a black surround (phone through eyepiece)
  polar:  vivid saturated colours on a largely dark background (zoomed in)
Nothing is copied or uploaded.

usage: python -I tools/scan.py
"""
import csv, os, sys, time
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FuturesTimeout
from concurrent.futures.process import BrokenProcessPool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gallery_lib import EXT, SCORES, config, open_image  # noqa: E402

FIELDS = ["path", "circle", "polar", "w", "h", "error"]


def score(path):
    try:
        im = open_image(path, small=True)
        w, h = im.size
        im.thumbnail((128, 128))
        a = np.asarray(im, dtype=np.float32) / 255.0
    except Exception as e:
        return (path, "", "", "", "", "err:" + type(e).__name__)
    mx, mn = a.max(axis=2), a.min(axis=2)
    v = mx
    s = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0)
    H, W = v.shape
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot(yy - (H - 1) / 2, xx - (W - 1) / 2) / (min(H, W) / 2)
    centre = v[r < 0.55].mean()
    out = r > 1.05 if (r > 1.05).any() else r > 0.95
    circle = max(0.0, centre - v[out].mean()) * (v[out] < 0.10).mean()

    dark = (v < 0.15).mean()
    vivid = (s > 0.55) & (v > 0.35)
    hue_bins = 0
    if vivid.sum() >= 10:
        r_, g_, b_ = a[..., 0][vivid], a[..., 1][vivid], a[..., 2][vivid]
        hue = np.arctan2(np.sqrt(3) * (g_ - b_), 2 * r_ - g_ - b_)
        hist, _ = np.histogram(hue, bins=12, range=(-np.pi, np.pi))
        hue_bins = int((hist > 0.03 * vivid.sum()).sum())
    polar = (vivid.mean() * min(1.0, hue_bins / 4.0)) if 0.15 < dark < 0.9 else 0.0
    return (path, round(float(circle), 4), round(float(polar), 4), w, h, "")


def iter_files(cfg):
    skip = [k.lower() for k in cfg["skip"]]
    for root in cfg["libraries"] + cfg["incoming"]:
        if not os.path.isdir(root):
            print(f"not found, skipped: {root}", flush=True)
            continue
        for d, _, fs in os.walk(root):
            if any(k in d.lower() + "\\" for k in skip):
                continue
            for f in fs:
                if f.lower().endswith(EXT):
                    yield os.path.join(d, f)


def scored_paths():
    if not SCORES.exists():
        return set()
    with open(SCORES, encoding="utf-8") as fh:
        return {r["path"] for r in csv.DictReader(fh)}


def run(progress=print):
    cfg = config()
    done = scored_paths()
    files = [f for f in iter_files(cfg) if f not in done]
    progress(f"{len(files)} new photos to scan ({len(done)} already scanned)")
    if not files:
        return 0
    t0 = time.time()
    new = not SCORES.exists()
    workers = max(2, (os.cpu_count() or 4) - 1)
    done_n = 0
    with open(SCORES, "a", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        if new:
            wr.writerow(FIELDS)
        # Batches, so a photo that crashes the image library costs one batch,
        # not the whole scan: the batch is retried one photo at a time and the
        # culprit is recorded as an error instead of hanging everything.
        for b in range(0, len(files), 400):
            batch = files[b:b + 400]
            try:
                with ProcessPoolExecutor(workers) as ex:
                    rows = list(ex.map(score, batch, chunksize=8, timeout=900))
            except (BrokenProcessPool, FuturesTimeout):
                rows = [one_safely(p) for p in batch]
            wr.writerows(rows)
            fh.flush()
            done_n += len(batch)
            progress(f"{done_n}/{len(files)} scanned, {time.time() - t0:.0f}s")
    return len(files)


def one_safely(path):
    try:
        with ProcessPoolExecutor(1) as ex:
            return ex.submit(score, path).result(timeout=120)
    except Exception as e:
        return (path, "", "", "", "", "err:" + type(e).__name__)


if __name__ == "__main__":
    run(lambda m: print(m, flush=True))
