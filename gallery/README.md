# OligoCrystal Crystal Gallery

Art-first gallery of the founder's microscope photographs of DNA crystals: https://crystals.ymgconsultingservices.com/

- `site/` static pages served by a Cloudflare Worker (`oligocrystal-gallery`), no server code.
- `tools/` the local curator, the photo scanner and the site build. They run only on the curating laptop.

## Curating

Double-click **`Curate.cmd`** (the first run sets up Python packages). The curator opens at http://127.0.0.1:8761/ .

| Tab | What it is |
|---|---|
| **Gallery** | What the site shows, in this order. Drag to rearrange, or select and press `T` (top), `B` (bottom), `S` (★ homepage), `H` (hide). Red `×N` badges mark similar shots next to each other; **Hide repeats in a row** clears them. |
| **Inbox** | New candidates, best first, with similar shots grouped (coloured underline). `A` adds to the Gallery (at the top), `H` hides. **Keep best of each similar group** hides the rest of each burst. |
| **Hidden** | Never shown on the site. Bring anything back. |

Selecting: click, `Shift`-click for a range, `Ctrl`-click to add one, `Ctrl+A` for all. `Space` or double-click opens a large view; `←`/`→` browse, `A`/`H`/`S` decide.

**Scan for new photos** looks through the photo libraries for new microscope shots; photos already scanned are skipped, so it's quick after the first time. Anything you put in `.local/incoming/` goes straight to the Inbox. Libraries, folders to skip, incoming folders and the Inbox threshold are in `.local/config.json`.

**Publish to site** rebuilds the pages from the Gallery order and runs the site checks. **Preview site** shows the result at http://127.0.0.1:8762/ . Nothing is online until you deploy.

## Deploying

From this folder: `npm install` once, then `npm run deploy` (runs the tests, then `wrangler deploy`). Built images (`site/a/`) are git-ignored and deploy from this laptop.

## Privacy

Source photo paths, library locations, decisions and thumbnails stay in git-ignored `.local/`. Published images are re-encoded to WebP, which removes EXIF/GPS data; a test checks this.
