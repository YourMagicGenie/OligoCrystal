# AGENTS.md

This repository holds both OligoCrystal websites:

| Folder | Site | Worker |
|---|---|---|
| repo root (`site/`, `test/`, `wrangler.jsonc`) | Jewelry coming-soon page, https://oligocrystal.ymgconsultingservices.com/ | `oligocrystal-website` |
| `gallery/` | **OligoCrystal Crystal Gallery**, https://crystals.ymgconsultingservices.com/ : an art-first gallery of the founder's microscope photographs of DNA crystals, used to impress investors and jewelry buyers. Includes the local curator (`gallery/Curate.cmd`). | `oligocrystal-gallery` |

Each site deploys on its own (`npm run deploy` from the root or from `gallery/`). CI runs both test suites.

Project memory lives in Project Keeper (`YourMagicGenie/Obsidian-Project-Keeper`), project `oligocrystal-proof-of-concept`. Read its central note and Status note before substantial work. When work here changes the project durably (launch, new canonical decision, scope change), update Keeper as part of the work. Routine commits don't need a Keeper entry.

## Rules for both sites

- **No third-party anything.** No analytics, cookies, fonts or CDNs. CSP allows first-party scripts only.
- **No data collection.** The waitlist is a mailto link. Any form, analytics, order flow or sample intake needs a new decision in Keeper and a privacy review first.
- The owner wants help with the websites and positioning here, not unrequested science advice.

## Rules for the Crystal Gallery (`gallery/`)

- **Call it the Crystal Gallery, not the Archive.** Owner's choice, 2026-11-27.
- **Photos are private until built.** Source photos come from the owner's personal libraries. Their paths, the library list, the selection and the catalogue-number map live only in git-ignored `gallery/.local/`. Never commit source photos, paths or personal folder names. This repo is public until 2026-12-17.
- **Publish only through `gallery/tools/build_gallery.py`.** It re-encodes to WebP, which strips EXIF/GPS, and drops near-duplicates. The tests fail if a published image carries EXIF.
- **Catalogue numbers (`OC-####`) are permanent.** Never renumber; `gallery/.local/curation.json` keeps them stable.
- **Keep the gallery/product distinction visible.** Gallery images are historical research DNA crystals; the jewelry uses a different salt-based composite. The footer note on each page says so; don't remove it or caption gallery images as products.
