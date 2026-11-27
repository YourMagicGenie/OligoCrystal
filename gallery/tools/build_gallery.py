"""Build the public Crystal Gallery from the curator's decisions.

Input  .local/curation.json   made by tools/curate.py (Gallery order, stars)
Output site/a/t/OC-####.webp  square thumbnail, 360 px
       site/a/f/OC-####.webp  square full view, 1600 px
       site/index.html, site/gallery.html  regenerated between markers

The wall follows the Gallery order exactly; starred crystals become the
homepage plates in that same order. Re-encoding to WebP drops all EXIF/GPS
metadata, so no location or device data is published. Catalogue numbers are
permanent: once a photo has one it keeps it.

Usage: python -I tools/build_gallery.py
"""
import html, os, re, sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gallery_lib as lib  # noqa: E402

SITE = lib.SITE
THUMB, FULL = 360, 1600
COLOURS = [  # (name, hue centre in degrees)
    ("red", 0), ("amber", 35), ("gold", 55), ("green", 120), ("teal", 175),
    ("blue", 220), ("violet", 270), ("magenta", 315),
]


def colour_of(im):
    a = np.asarray(im.convert("RGB").resize((64, 64)), dtype=np.float32) / 255
    mx, mn = a.max(2), a.min(2)
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    m = (s > 0.45) & (mx > 0.3)
    if m.mean() < 0.02:
        return "white"
    r, g, b = a[..., 0][m], a[..., 1][m], a[..., 2][m]
    hue = (np.degrees(np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)) + 360) % 360
    w = s[m] * mx[m]
    return max(COLOURS, key=lambda c: (w * np.cos(np.radians(hue - c[1]))).clip(0).sum())[0]


def square(im):
    # Eyepiece shots are portrait frames around a round field; a centred
    # square keeps the whole field and gives an even gallery wall.
    w, h = im.size
    s = min(w, h)
    return im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))


def save(im, edge, dest):
    c = square(im)
    c.thumbnail((edge, edge), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    c.save(dest, "WEBP", quality=80, method=6)  # no exif= argument: metadata dropped
    return list(c.size)


def inject(page, marker, content, inline=False):
    p = SITE / page
    s = p.read_text(encoding="utf-8")
    pat = re.compile(rf"(<!-- {marker}:start -->).*?(<!-- {marker}:end -->)", re.S)
    if not pat.search(s):
        sys.exit(f"marker {marker} missing in {page}")
    nl = "" if inline else "\n"
    p.write_text(pat.sub(lambda m: m.group(1) + nl + content + nl + m.group(2), s), encoding="utf-8")


def year_of(it, src):
    d = it.get("date")
    if d:
        return int(d[:4])
    return datetime.fromtimestamp(os.path.getmtime(src)).year


def main():
    cur = lib.load_curation()
    shown = [s for s in cur["order"] if cur["items"].get(s, {}).get("state") == "shown"]
    if not shown:
        sys.exit("The Gallery is empty: add crystals in the curator first.")

    # New catalogue numbers, oldest photo first, after the highest one ever issued.
    issued = [int(it["id"][3:]) for it in cur["items"].values() if it.get("id")]
    nxt = max(issued, default=0) + 1
    for s in sorted((s for s in shown if not cur["items"][s].get("id")), key=lambda s: cur["items"][s].get("date") or ""):
        cur["items"][s]["id"] = f"OC-{nxt:04d}"
        nxt += 1

    data, made = [], 0
    for s in shown:
        it = cur["items"][s]
        cid = it["id"]
        t, f = SITE / "a" / "t" / f"{cid}.webp", SITE / "a" / "f" / f"{cid}.webp"
        if not (t.exists() and f.exists() and it.get("pub")):
            if not os.path.exists(s):
                print(f"missing source, skipped: {cid}")
                continue
            im = lib.open_image(s)
            it["pub"] = {"t": save(im, THUMB, t), "f": save(im, FULL, f), "colour": colour_of(im), "year": year_of(it, s)}
            made += 1
        data.append({"id": cid, "star": bool(it.get("star")), **it["pub"]})
    lib.save_curation(cur)

    keep = {d["id"] for d in data}
    for d in ("t", "f"):
        for old in (SITE / "a" / d).glob("OC-*.webp"):
            if old.stem not in keep:
                old.unlink()

    years = sorted({d["year"] for d in data})
    span = f"{years[0]}–{years[-1]}" if len(years) > 1 else str(years[0])
    heroes = [d for d in data if d["star"]] or data[:12]

    def alt(d, prefix="Crystal"):
        tone = "colourless" if d["colour"] == "white" else d["colour"]
        return f'{prefix} {d["id"]}, {d["year"]}, {tone} tones'

    plates = "\n".join(
        f'<figure class="plate" id="{d["id"]}"><img src="/a/f/{d["id"]}.webp" width="{d["f"][0]}" height="{d["f"][1]}" '
        f'alt="{alt(d)}" loading="{"eager" if i == 0 else "lazy"}" decoding="async">'
        f'<figcaption><span class="cat">{d["id"]}</span> · {d["year"]}</figcaption></figure>'
        for i, d in enumerate(heroes))
    wall = "\n".join(
        f'<li data-colour="{d["colour"]}"><a href="/a/f/{d["id"]}.webp" data-id="{d["id"]}" data-year="{d["year"]}" '
        f'data-w="{d["f"][0]}" data-h="{d["f"][1]}"><img src="/a/t/{d["id"]}.webp" width="{d["t"][0]}" height="{d["t"][1]}" '
        f'alt="{alt(d)}" loading="lazy" decoding="async"></a></li>'
        for d in data)
    names = [c for c, _ in COLOURS] + ["white"]
    present = [c for c in names if any(d["colour"] == c for d in data)]
    filters = '<button type="button" data-colour="all" aria-pressed="true">All</button>\n' + "\n".join(
        f'<button type="button" data-colour="{c}" aria-pressed="false"><span class="sw sw-{c}"></span>'
        f'{"Colourless" if c == "white" else c.capitalize()}</button>' for c in present)

    for page in ("index.html", "gallery.html"):
        inject(page, "count", f'<span class="count">{len(data):,}</span>', inline=True)
        inject(page, "span", html.escape(span), inline=True)
    inject("index.html", "plates", plates)
    first = heroes[0]
    inject("index.html", "opening",
           f'<img class="glow" src="/a/f/{first["id"]}.webp" width="{first["f"][0]}" height="{first["f"][1]}" alt="" fetchpriority="high">')
    inject("gallery.html", "wall", wall)
    inject("gallery.html", "filters", filters)
    print(f"{len(data)} crystals in the Gallery ({made} newly encoded), {len(heroes)} on the homepage")


if __name__ == "__main__":
    main()
