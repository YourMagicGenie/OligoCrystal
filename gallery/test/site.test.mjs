// Checks that need only Node built-ins (no npm install in CI).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync } from "node:fs";

const site = new URL("../site/", import.meta.url);
const read = (p) => readFileSync(new URL(p, site), "utf8");
const pages = ["index.html", "gallery.html", "404.html"];

test("every page has a title, viewport and the shared stylesheet", () => {
  for (const p of pages) {
    const h = read(p);
    assert.match(h, /<title>[^<]+<\/title>/, p);
    assert.match(h, /name="viewport"/, p);
    assert.match(h, /href="\/styles.css"/, p);
  }
});

test("no third-party scripts, styles, fonts or images", () => {
  for (const p of pages) {
    const h = read(p);
    for (const m of h.matchAll(/<(?:script|link|img)[^>]+(?:src|href)="([^"]+)"/g)) {
      const url = m[1];
      if (/^https?:/.test(url)) assert.match(url, /\.ymgconsultingservices\.com\//, `${p}: ${url}`);
    }
  }
});

test("security headers keep scripts first-party", () => {
  const h = read("_headers");
  assert.match(h, /default-src 'none'/);
  assert.match(h, /script-src 'self'/);
  assert.doesNotMatch(h, /unsafe-inline|unsafe-eval/);
  assert.match(h, /Strict-Transport-Security/);
});

// Built images live only on the curating laptop (site/a is git-ignored), so
// this check runs there before deploy and is skipped in CI.
test("every image the pages reference exists", { skip: !existsSync(new URL("a/", site)) && "images not built here" }, () => {
  for (const p of ["index.html", "gallery.html"]) {
    for (const m of read(p).matchAll(/(?:src|href)="(\/a\/[^"]+)"/g)) {
      assert.ok(existsSync(new URL("." + m[1], site)), `${p}: ${m[1]}`);
    }
  }
});

test("published images carry no EXIF/GPS metadata", () => {
  for (const d of ["a/t/", "a/f/"]) {
    const dir = new URL(d, site);
    if (!existsSync(dir)) continue;
    for (const f of readdirSync(dir)) {
      const head = readFileSync(new URL(f, dir)).subarray(0, 64 * 1024).toString("latin1");
      assert.ok(!head.includes("EXIF") && !head.includes("Exif\0\0"), `${d}${f} has EXIF`);
    }
  }
});

test("gallery counts match the wall", () => {
  const h = read("gallery.html");
  const tiles = (h.match(/<li data-colour=/g) || []).length;
  const shown = Number((h.match(/<span class="count">([\d,]+)<\/span>/) || [, "0"])[1].replace(/,/g, ""));
  assert.equal(shown, tiles);
});
