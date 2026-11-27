"""Shared helpers for the scanner, the curator and the site build."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / ".local"
SITE = ROOT / "site"
CONFIG = LOCAL / "config.json"
CURATION = LOCAL / "curation.json"
SCORES = LOCAL / "scores.csv"
THUMBS = LOCAL / "thumbs"

EXT = (".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff", ".bmp")

DEFAULT_CONFIG = {
    # Photo libraries the scanner searches for microscope shots. Set them in
    # .local/config.json: library paths are private and stay out of git.
    "libraries": [],
    # Everything in these folders goes straight to the Inbox, whatever its score.
    "incoming": [str(LOCAL / "incoming")],
    # Folders (substring match) the scanner never looks in. Add personal ones in
    # .local/config.json; Google Drive folders download when read, so skip any
    # that can't hold crystal shots.
    "skip": ["\\videos\\"],
    # Minimum scanner score for a library photo to reach the Inbox.
    "inbox_threshold": 0.15,
}


def config():
    LOCAL.mkdir(exist_ok=True)
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG.exists():
        cfg.update(json.loads(CONFIG.read_text(encoding="utf-8")))
    else:
        CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    for d in cfg["incoming"]:
        Path(d).mkdir(parents=True, exist_ok=True)
    return cfg


def open_image(path, small=False):
    """Open any supported photo, upright. small=True uses the fast HEIC preview."""
    if small and str(path).lower().endswith(".heic"):
        try:
            f = pillow_heif.open_heif(path, convert_hdr_to_8bit=True)
            th = f[0].get_thumbnail(0)
            return Image.frombytes(th.mode, th.size, th.data, "raw", th.mode, th.stride).convert("RGB")
        except Exception:
            pass
    im = Image.open(path)
    if small:
        try:
            im.draft("RGB", (400, 400))
        except Exception:
            pass
    return ImageOps.exif_transpose(im).convert("RGB")


def dhash(im):
    g = np.asarray(im.convert("L").resize((9, 8)), dtype=np.int16)
    return int("".join("1" if x else "0" for x in (g[:, 1:] > g[:, :-1]).flatten()), 2)


def similar(a, b, limit=10):
    return a is not None and b is not None and bin(a ^ b).count("1") <= limit


def load_curation():
    if CURATION.exists():
        return json.loads(CURATION.read_text(encoding="utf-8"))
    return {"items": {}, "order": []}


def save_curation(cur):
    tmp = CURATION.with_suffix(".tmp")
    tmp.write_text(json.dumps(cur, indent=1), encoding="utf-8")
    tmp.replace(CURATION)
