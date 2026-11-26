// Static checks for the OligoCrystal coming-soon site. Node built-ins only.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import { join, dirname, extname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "site");

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

const files = walk(root);
const html = files.filter((f) => extname(f) === ".html");
const svg = files.filter((f) => extname(f) === ".svg");
const read = (f) => readFileSync(f, "utf8");
const visibleText = (s) => s.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");

test("no inline styles, style blocks, scripts or event handlers (strict CSP)", () => {
  for (const f of [...html, ...svg]) {
    const s = read(f);
    assert.doesNotMatch(s, /\sstyle\s*=/i, `${f} has a style attribute`);
    assert.doesNotMatch(s, /<style[\s>]/i, `${f} has a <style> block`);
    assert.doesNotMatch(s, /<script[\s>]/i, `${f} has a <script>`);
    assert.doesNotMatch(s, /\son[a-z]+\s*=/i, `${f} has an inline event handler`);
  }
});

test("no forms: the site collects no personal data", () => {
  for (const f of html) assert.doesNotMatch(read(f), /<(form|input|textarea)[\s>]/i, f);
});

test("CSP and security headers are set for every path", () => {
  const h = read(join(root, "_headers"));
  assert.match(h, /^\/\*$/m);
  const csp = h.match(/Content-Security-Policy: (.+)/)?.[1] ?? "";
  assert.match(csp, /default-src 'none'/);
  assert.match(csp, /frame-ancestors 'none'/);
  assert.doesNotMatch(csp, /unsafe-inline|unsafe-eval/);
  for (const name of ["Strict-Transport-Security", "X-Content-Type-Options", "Referrer-Policy"]) {
    assert.match(h, new RegExp(`^\\s+${name}:`, "m"), name);
  }
});

test("every local link and image resolves", () => {
  for (const f of html) {
    for (const [, ref] of read(f).matchAll(/(?:href|src)="([^"]+)"/g)) {
      if (/^(https?:|mailto:|#)/.test(ref)) continue;
      const path = ref.split("#")[0];
      if (!path) continue;
      assert.ok(existsSync(join(root, path.replace(/^\//, ""))), `${f} -> ${ref}`);
    }
  }
});

test("external links go only to YMG", () => {
  for (const f of html) {
    for (const [, url] of read(f).matchAll(/href="(https?:[^"]+)"/g)) {
      assert.match(url, /^https:\/\/(oligocrystal\.)?ymgconsultingservices\.com\//, `${f} -> ${url}`);
    }
  }
});

test("every image has an alt attribute", () => {
  for (const f of html) {
    for (const [tag] of read(f).matchAll(/<img\b[^>]*>/g)) assert.match(tag, /\balt="/, `${f}: ${tag}`);
  }
});

test("home page has the required sections", () => {
  const s = read(join(root, "index.html"));
  for (const id of ["honest", "how", "pieces", "faq", "waitlist", "social"]) {
    assert.match(s, new RegExp(`id="${id}"`), id);
  }
  const t = visibleText(s);
  assert.match(t, /proof of concept/i);
  assert.match(t, /not accepting DNA samples/i);
  assert.match(t, /What happens to my DNA sample\?/);
  assert.match(t, /privacy/i);
});

// The research has not validated DNA retention, lattice identity or durability.
// Keep claims that would need that evidence off the site (Keeper DEC-20261126-01).
test("no unvalidated claims", () => {
  const banned = [
    /\bguarantee/i,
    /\bforever\b/i,
    /\bpermanent(ly)?\b/i,
    /\blifetime\b/i,
    /\bproven\b/i,
    /\bscientifically (shown|validated)/i,
    /\bDNA crystals?\b/i,
    /\bcrystalli[sz]ed DNA\b/i,
    /\bpreserv(e|es|ed|ing) your DNA\b/i,
    /\bunique (to you|genetic)/i,
    /\bone of a kind\b/i,
    /\bwaterproof\b/i,
    /\bHIPAA\b/i,
    /\bfully (secure|anonymous)\b/i,
  ];
  for (const f of html) {
    const t = visibleText(read(f)) + " " + (read(f).match(/<title>(.*?)<\/title>/)?.[1] ?? "");
    for (const re of banned) assert.doesNotMatch(t, re, `${f} matches ${re}`);
  }
});
