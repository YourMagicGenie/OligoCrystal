# OligoCrystal

Websites for OligoCrystal, a YMG Consulting Services proof of concept: crystal and glass jewelry with a crystalline insert formed from the customer's purified DNA. The repo root is the coming-soon site; [`gallery/`](gallery/README.md) is the Crystal Gallery.

Live at <https://oligocrystal.ymgconsultingservices.com/>.

## What this site is (and is not)

- A static, single-page announcement plus a privacy page. No JavaScript, no cookies, no analytics, no forms.
- The waitlist is an email link to `hello@ymgconsultingservices.com`. The site itself collects and stores nothing.
- It does not take orders or DNA samples. The product is a proof of concept.

## Layout

| Path | Purpose |
| --- | --- |
| `site/` | Everything that is served: HTML, CSS, SVG art, `_headers` (CSP and security headers), `robots.txt` |
| `wrangler.jsonc` | Cloudflare Workers static-assets config with the custom domain; no Worker script, no bindings |
| `test/` | Node built-in tests for links, headers and content rules |
| `gallery/` | The OligoCrystal Crystal Gallery, a separate site at <https://crystals.ymgconsultingservices.com/> with its own curator and Worker; see [`gallery/README.md`](gallery/README.md) |
| `.github/workflows/checks.yml` | Runs both sites' tests on every pull request and on `main` |

## Work on it

Requires Node 22 or later.

```sh
npm test                          # node --test, no install needed
npx wrangler@4.160.0 dev          # local preview on http://localhost:8787
npx wrangler@4.160.0 deploy       # publish (needs a logged-in Cloudflare account)
```

The Content-Security-Policy is `default-src 'none'` with only same-origin styles, images and fonts. Inline styles and scripts will be blocked; put CSS in `site/styles.css`.
