# -*- coding: utf-8 -*-
"""Behaviour tests for the Build Maker page.

Drives the real assets/build-maker.js against the real build-maker.json inside
a minimal DOM, so the only way in is the same events a visitor produces. Two
bugs these caught that nothing else did: applyState being fed a base64url
string instead of an object, and a stylesheet revert that dropped every rule
the library markup depends on.

Run: python -m scripts.test_build_maker
"""
import base64
import io
import json
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_JS = os.path.join(ROOT, "assets", "build-maker.js")
BUILD_HTML = os.path.join(ROOT, "division-2", "build-maker", "index.html")
STYLES = os.path.join(ROOT, "assets", "styles.css")
SITE_JS = os.path.join(ROOT, "assets", "site.js")
DATA_FILE = os.path.join(ROOT, "assets", "data", "build-maker.json")
TMP = os.path.join(os.environ.get("TEMP", "."), "build_maker_test")

KEY = "raigulus-build-maker"
LIB = "raigulus-build-library"
CAP = 1000000

def read(path):
    with io.open(path, encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


JS = read(BUILD_JS)
HTML = read(BUILD_HTML)
CSS = read(STYLES)
DATA = json.loads(read(DATA_FILE))

MASK = DATA["gear"]["mask"][0]["name"]
CHEST = DATA["gear"]["chest"][0]["name"]
GLOVES = DATA["gear"]["gloves"][0]["name"]
W1 = DATA["weapons"]["assault-rifle"][0]["name"]
S1 = DATA["skills"][0]["name"]

IDS = ["bm-gear-slots", "bm-weapon-slots", "bm-skill-slots", "bm-summary",
       "bm-modal-title", "bm-modal-search", "bm-modal", "bm-modal-filters",
       "bm-modal-list", "bm-modal-close", "bm-data-meta", "bm-copy-link",
       "bm-copy-text", "bm-screenshot", "bm-reset", "bm-watch1000", "bm-export",
       "bm-import", "bm-import-file", "bm-changelog", "bm-changelog-meta",
       "bm-library", "bm-library-panel", "bm-library-name", "bm-library-add",
       "bm-library-empty", "bm-library-list", "bm-compare", "bm-compare-label",
       "bm-compare-body"]

HARNESS = r"""
var __store = __STORE__;
var __downloads = [];
var __errors = [];
var __resolveFetch = __FETCH_OK__;
var __ids = {};
__IDLIST__.forEach(function (id) {
  __ids[id] = { id: id, textContent: "", value: "", hidden: true, innerHTML: "",
    checked: false, style: {}, _attrs: {}, files: [],
    setAttribute: function (k, v) { this._attrs[k] = v; },
    getAttribute: function (k) { return k in this._attrs ? this._attrs[k] : null; },
    appendChild: function (c) { return c; }, removeChild: function () {},
    replaceChildren: function () {}, remove: function () {},
    addEventListener: function (ev, fn) { this._on = this._on || {}; this._on[ev] = fn; },
    click: function () {}, focus: function () {}, select: function () {} };
});
var document = {
  getElementById: function (id) { return __ids[id] || null; },
  createElement: function (t) { return { tagName: t, style: {}, href: "", download: "",
    value: "", select: function () {}, setAttribute: function () {},
    appendChild: function (c) { return c; }, removeChild: function () {},
    click: function () { __downloads.push({ download: this.download }); } }; },
  execCommand: function () { return true; },
  body: { appendChild: function () {}, removeChild: function () {} },
  addEventListener: function (ev, fn) { document._on = document._on || {}; document._on[ev] = fn; },
  readyState: "complete"
};
var Blob = function (parts, opts) { this._text = parts.join(""); this.type = opts && opts.type; };
var URL = { createObjectURL: function (b) { __downloads.push({ text: b._text }); return "blob:x"; },
            revokeObjectURL: function () {} };
var FileReader = function () {};
FileReader.prototype.readAsText = function (f) { this.result = f._text; if (this.onload) this.onload(); };
var localStorage = {
  getItem: function (k) { return k in __store ? __store[k] : null; },
  setItem: function (k, v) { __store[k] = String(v); },
  removeItem: function (k) { delete __store[k]; }
};
var location = { href: "https://raigulus.github.io/division-2/build-maker/#" + __HASH__,
                 pathname: "/division-2/build-maker/", hash: "#" + __HASH__ };
var history = { replaceState: function (a, b, url) { location.hash = url; } };
var navigator = { clipboard: null };
var DATA = null;
var IMG = {};
globalThis.window = globalThis;
globalThis.addEventListener = function (ev, fn) { globalThis.__win = globalThis.__win || {};
  globalThis.__win[ev] = fn; };
globalThis.__clarityTags = [];
globalThis.__ga4 = [];
globalThis.gtag = function () { globalThis.__ga4.push(Array.prototype.slice.call(arguments)); };
globalThis.clarity = __WITH_CLARITY__
  ? function () { globalThis.__clarityTags.push(Array.prototype.slice.call(arguments)); }
  : undefined;

function pending(res, ms) { return new Promise(function (r) { setTimeout(function () { r(res); }, ms); }); }
// A promise that never settles keeps DATA null without leaving a long timer
// behind, which would stop node from exiting.
function never() { return new Promise(function () {}); }
function fetch(url) {
  if (!__resolveFetch) return never();
  if (url.indexOf("build-maker.json") >= 0 && url.indexOf("changelog") < 0)
    return pending({ json: function () { return Promise.resolve(__DATA__); } }, 1);
  if (url.indexOf("item-images") >= 0)
    return pending({ json: function () { return Promise.resolve({}); } }, 1);
  return pending({ json: function () { return Promise.resolve({ meta: {}, sections: [] }); } }, 1);
}
__JS__

function clickBtn(id, checked) {
  var t = { id: id, closest: function () { return null; } };
  if (checked !== undefined) t.checked = checked;
  document._on.click({ target: t });
}
function clickAttr(attr, id) {
  var btn = { id: "", getAttribute: function (a) { return a === attr ? id : null; },
              closest: function (s) { return s && s.indexOf(attr) !== -1 ? this : null; } };
  document._on.click({ target: btn });
}
function clickSlot(sel, slotKey, dataAttr) {
  var btn = { id: "", getAttribute: function (a) { return a === dataAttr ? slotKey : null; },
              closest: function (s) { return s === sel ? this : null; } };
  try { document._on.click({ target: btn }); return "ok"; }
  catch (e) { __errors.push(String(e && e.message || e)); return "threw"; }
}
function importFile(text, size) {
  __ids["bm-import-file"]._on.change({ target: { files: [{ _text: text, size: size === undefined ? text.length : size }], value: "x" } });
}
setTimeout(function () {
  try { (function () { __BODY__ })(); } catch (e) {
    __errors.push(String(e && e.message || e));
  }
}, __STEPAT__);
setTimeout(function () {
  console.log(JSON.stringify({
    store: __store, downloads: __downloads, errors: __errors,
    summary: __ids["bm-summary"].innerHTML,
    gear: __ids["bm-gear-slots"].innerHTML,
    weapons: __ids["bm-weapon-slots"].innerHTML,
    skills: __ids["bm-skill-slots"].innerHTML,
    modalHidden: __ids["bm-modal"].hidden,
    modalList: __ids["bm-modal-list"].innerHTML,
    exportLabel: __ids["bm-export"].textContent,
    importLabel: __ids["bm-import"].textContent,
    libraryHidden: __ids["bm-library-panel"].hidden,
    libraryList: __ids["bm-library-list"].innerHTML,
    emptyHidden: __ids["bm-library-empty"].hidden,
    compareHidden: __ids["bm-compare"].hidden,
    compareLabel: __ids["bm-compare-label"].textContent,
    compareBody: __ids["bm-compare-body"].innerHTML,
    clarityTags: globalThis.__clarityTags,
    dataArrived: __ids["bm-data-meta"].textContent.indexOf("Data:") === 0,
    globalPollution: ({}).polluted !== undefined ? "YES" : "no"
  }));
}, __SNAPAT__);
"""


def b64(obj):
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")


def unb64(text):
    pad = "=" * (-len(text) % 4)
    return json.loads(base64.urlsafe_b64decode(
        text.replace("-", "+").replace("_", "/") + pad))


def drive(body="", store=None, hash_="", clarity=True, fetch_ok=True,
          step_at=90, snap_at=170):
    """Run the page once and return what the DOM ended up holding."""
    src = (HARNESS.replace("__STORE__", json.dumps(store if store is not None else {}))
                 .replace("__HASH__", json.dumps(hash_))
                 .replace("__IDLIST__", json.dumps(IDS))
                 .replace("__DATA__", json.dumps(DATA))
                 .replace("__JS__", JS)
                 .replace("__WITH_CLARITY__", "true" if clarity else "false")
                 .replace("__FETCH_OK__", "true" if fetch_ok else "false")
                 .replace("__STEPAT__", str(step_at))
                 .replace("__SNAPAT__", str(snap_at))
                 .replace("__BODY__", body))
    if not os.path.isdir(TMP):
        os.makedirs(TMP)
    path = os.path.join(TMP, "page.js")
    write(path, src)
    proc = subprocess.run(["node", path], capture_output=True, text=True, timeout=120)
    if "SyntaxError" in proc.stderr or "ReferenceError" in proc.stderr:
        raise AssertionError("harness is broken: " + proc.stderr.strip()[:300])
    for line in reversed(proc.stdout.strip().split("\n")):
        if line.startswith("{"):
            return json.loads(line)
    raise AssertionError("no result from node: " + proc.stderr.strip()[-300:])


class Base(unittest.TestCase):
    def assertAlive(self, res):
        self.assertEqual(res["errors"], [], "page raised: %s" % res["errors"])
        self.assertEqual(res["globalPollution"], "no", "prototype was polluted")

    def assertBuilt(self, res, item):
        blob = "".join(res.get(k, "") for k in ("summary", "gear", "weapons", "skills"))
        self.assertIn(item, blob)

    def assertNotBuilt(self, res, item):
        blob = "".join(res.get(k, "") for k in ("summary", "gear", "weapons", "skills"))
        self.assertNotIn(item, blob)


class TestWiring(unittest.TestCase):
    """The page has three files that reference each other by name.

    A stylesheet revert once removed every rule the library markup needs while
    the markup and the script stayed put, and no behaviour test noticed because
    the DOM stub never evaluates CSS. These check the references resolve.
    """

    def test_every_id_the_script_uses_exists_in_the_markup(self):
        import re
        used = sorted(set(re.findall(r'\$\("([^"]+)"\)', JS)))
        missing = [i for i in used if ('id="%s"' % i) not in HTML]
        self.assertEqual(missing, [], "script reaches for ids the markup lacks")

    def test_every_class_the_script_emits_has_a_rule(self):
        import re
        emitted = set()
        for group in re.findall(r'class="(bm-[a-z\- ]+)"', JS):
            emitted.update(group.split())
        missing = sorted(c for c in emitted if ("." + c) not in CSS)
        self.assertEqual(missing, [], "markup classes with no stylesheet rule")

    def test_no_css_variable_is_used_without_being_defined(self):
        import re
        defined = set(re.findall(r"(--[\w-]+)\s*:", CSS))
        used = set(re.findall(r"var\((--[\w-]+)\)", CSS))
        self.assertEqual(sorted(used - defined), [])

    def test_no_token_defines_itself(self):
        import re
        root = re.search(r":root\s*\{[^}]*\}", CSS, re.S)
        self.assertIsNotNone(root, "no :root block found")
        self.assertEqual(re.findall(r"(--[\w-]+)\s*:\s*var\(\1\)", root.group(0)), [],
                         "a custom property refers to itself")


class TestBeforeDataLoads(Base):
    def test_slot_click_before_data_does_not_throw(self):
        res = drive(body="clickSlot('.bm-slot-change', 'mask', 'data-slot');",
                    fetch_ok=False, step_at=40, snap_at=90)
        self.assertAlive(res)
        self.assertFalse(res["modalHidden"], "the click got no visible answer")
        self.assertIn("Loading", res["modalList"])

    def test_picker_shows_real_items_once_data_arrives(self):
        res = drive(body="clickSlot('.bm-slot-change', 'mask', 'data-slot');", snap_at=320)
        self.assertAlive(res)
        self.assertTrue(res["dataArrived"])
        self.assertIn(MASK, res["modalList"])
        self.assertNotIn("Loading", res["modalList"])


class TestPersistence(Base):
    def test_empty_visit_writes_nothing(self):
        res = drive()
        self.assertEqual(res["store"], {})

    def test_watch_toggle_is_stored(self):
        res = drive(body="clickBtn('bm-watch1000', true);")
        self.assertIn(KEY, res["store"])

    def test_saved_build_comes_back(self):
        res = drive(store={KEY: b64({"m": MASK, "w1": W1, "s1": S1})})
        self.assertBuilt(res, MASK)
        self.assertBuilt(res, S1)

    def test_hash_beats_the_stored_build(self):
        res = drive(store={KEY: b64({"m": MASK})}, hash_=b64({"c": CHEST}))
        self.assertBuilt(res, CHEST)
        self.assertNotBuilt(res, MASK)

    def test_reset_clears_the_stored_build(self):
        res = drive(store={KEY: b64({"m": MASK})}, body="clickBtn('bm-reset');")
        self.assertAlive(res)
        self.assertNotIn(KEY, res["store"])
        self.assertNotBuilt(res, MASK)

    def test_a_malformed_hash_does_not_break_the_page(self):
        for bad in ("!!!nope!!!", base64.urlsafe_b64encode(b"{oops").decode().rstrip("="), ""):
            self.assertAlive(drive(hash_=bad))


class TestLibrary(Base):
    SEED = json.dumps({"version": 1, "builds": [
        {"id": "x1", "name": "Alpha", "saved": "2026-10-01",
         "state": {"m": MASK, "c": CHEST}},
        {"id": "y2", "name": "Beta", "saved": "2026-10-02",
         "state": {"m": MASK, "w1": W1}}]})

    def test_panel_toggles(self):
        opened = drive(body="clickBtn('bm-library');")
        self.assertFalse(opened["libraryHidden"])
        closed = drive(body="clickBtn('bm-library');clickBtn('bm-library');")
        self.assertTrue(closed["libraryHidden"])

    def test_saving_without_a_name_is_refused(self):
        res = drive(hash_=b64({"m": MASK}),
                    body="clickBtn('bm-library');clickBtn('bm-library-add');")
        self.assertAlive(res)
        self.assertNotIn(LIB, res["store"])

    def test_a_named_build_is_stored_and_shown(self):
        res = drive(hash_=b64({"m": MASK, "c": CHEST}),
                    body="__ids['bm-library-name'].value='Solo Striker';"
                         "clickBtn('bm-library');clickBtn('bm-library-add');")
        self.assertAlive(res)
        self.assertIn(LIB, res["store"])
        entry = json.loads(res["store"][LIB])["builds"][0]
        self.assertEqual(entry["name"], "Solo Striker")
        # encodeState returns base64url text, so the snapshot has to be decoded
        # before it is stored, or loading it finds no slots at all.
        self.assertIsInstance(entry["state"], dict)
        self.assertEqual(entry["state"].get("m"), MASK)
        self.assertIn("Solo Striker", res["libraryList"])
        self.assertTrue(res["emptyHidden"])

    def test_builds_survive_a_reload(self):
        res = drive(store={LIB: self.SEED}, body="clickBtn('bm-library');")
        self.assertIn("Alpha", res["libraryList"])
        self.assertIn("Beta", res["libraryList"])

    def test_loading_replaces_the_working_build(self):
        res = drive(store={LIB: self.SEED}, hash_=b64({"w2": W1}),
                    body="clickBtn('bm-library');clickAttr('data-lib-load','x1');")
        self.assertAlive(res)
        self.assertBuilt(res, CHEST)
        self.assertNotBuilt(res, W1)

    def test_deleting_removes_one_entry_only(self):
        res = drive(store={LIB: self.SEED},
                    body="clickBtn('bm-library');clickAttr('data-lib-del','x1');")
        names = [b["name"] for b in json.loads(res["store"][LIB])["builds"]]
        self.assertNotIn("Alpha", names)
        self.assertIn("Beta", names)
        self.assertNotIn("Alpha", res["libraryList"])

    def test_comparison_needs_both_slots(self):
        res = drive(store={LIB: self.SEED},
                    body="clickBtn('bm-library');clickAttr('data-lib-a','x1');")
        self.assertNotEqual(res["compareHidden"], False)

    def test_comparison_renders_a_table(self):
        res = drive(store={LIB: self.SEED},
                    body="clickBtn('bm-library');clickAttr('data-lib-a','x1');"
                         "clickAttr('data-lib-b','y2');")
        self.assertAlive(res)
        self.assertFalse(res["compareHidden"])
        self.assertIn("Alpha", res["compareLabel"])
        self.assertIn("Beta", res["compareLabel"])
        self.assertIn("bm-compare-table", res["compareBody"])
        self.assertIn("bm-cmp-", res["compareBody"])

    def test_comparison_leaves_the_working_build_alone(self):
        res = drive(store={LIB: self.SEED}, hash_=b64({"g": GLOVES}),
                    body="clickBtn('bm-library');clickAttr('data-lib-a','x1');"
                         "clickAttr('data-lib-b','y2');")
        self.assertAlive(res)
        self.assertBuilt(res, GLOVES)
        self.assertNotBuilt(res, MASK)

    def test_a_damaged_library_degrades_instead_of_throwing(self):
        for raw in ("{broken", "[1,2]", "null", '{"builds":"x"}'):
            self.assertAlive(drive(store={LIB: raw}, body="clickBtn('bm-library');"))

    def test_malformed_entries_are_dropped(self):
        junk = json.dumps({"version": 1, "builds": [
            {"name": "no state"}, {"id": "ok"}, "string", None]})
        res = drive(store={LIB: junk}, body="clickBtn('bm-library');")
        self.assertAlive(res)
        self.assertNotIn(">ok<", res["libraryList"])


class TestImportExport(Base):
    STATE = {"m": MASK, "w1": W1, "s1": S1, "w": 1, "cf": {"mask:core_1": "Weapon Damage"}}
    WRAPPED = json.dumps({"app": "raigulus-build-maker", "format": 1,
                          "exported": "2026-10-13T00:00:00Z", "state": STATE})

    def test_export_produces_a_file(self):
        res = drive(store={KEY: b64({"m": MASK})}, body="clickBtn('bm-export');")
        self.assertTrue(res["downloads"])

    def test_import_accepts_wrapped_and_bare_state(self):
        for text in (self.WRAPPED, json.dumps(self.STATE)):
            res = drive(body="importFile(%s);" % json.dumps(text))
            self.assertAlive(res)
            self.assertBuilt(res, MASK)

    def test_round_trip_keeps_every_field(self):
        res = drive(body="importFile(%s);" % json.dumps(self.WRAPPED))
        back = unb64(res["store"][KEY])
        for field in ("m", "w1", "s1", "w"):
            self.assertEqual(back.get(field), self.STATE[field])
        self.assertEqual(back.get("cf"), {"mask:core_1": "Weapon Damage"})

    def test_malformed_files_are_refused(self):
        for text in ("{not json", "[1,2,3]", '{"hello":"world"}', '"x"', "null", "", "42"):
            res = drive(body="importFile(%s);" % json.dumps(text))
            self.assertAlive(res)
            self.assertNotBuilt(res, MASK)

    def test_inherited_key_names_cannot_reach_state_cfg(self):
        for key in ("__proto__", "constructor", "toString", "valueOf", "hasOwnProperty"):
            res = drive(body="importFile(%s);" % json.dumps(
                json.dumps({"m": MASK, "cf": {key: {"polluted": "yes"}}})))
            self.assertEqual(res["globalPollution"], "no", key)
            if KEY in res["store"]:
                self.assertNotIn(key, (unb64(res["store"][KEY]).get("cf") or {}))

    def test_an_oversized_file_is_refused(self):
        big = json.dumps({"m": MASK, "cf": {"mask:core_%d" % i: "v" * 200 for i in range(6000)}})
        self.assertGreater(len(big), CAP)
        res = drive(body="importFile(%s);" % json.dumps(big))
        self.assertIn("too large", res["importLabel"].lower())


class TestClarityTag(Base):
    def tag(self, res):
        for call in res["clarityTags"]:
            if len(call) == 3 and call[0] == "set" and call[1] == "build_action":
                return call[2]
        return None

    def test_each_action_is_tagged(self):
        cases = {"bm-export": "export_json", "bm-copy-link": "copy_link",
                 "bm-copy-text": "copy_text", "bm-screenshot": "screenshot"}
        for button, expected in cases.items():
            res = drive(body="clickBtn('%s');" % button)
            self.assertEqual(self.tag(res), expected, button)

    def test_nothing_is_tagged_without_consent(self):
        res = drive(body="clickBtn('bm-export');", clarity=False)
        self.assertAlive(res)
        self.assertIsNone(self.tag(res))

    def test_a_session_that_does_nothing_is_left_untagged(self):
        self.assertEqual(drive()["clarityTags"], [])


class TestThemeControl(unittest.TestCase):
    """site.js also carries the search dialog, which needs far more DOM, so the
    theme block is lifted out verbatim and run on its own."""

    SITE = read(SITE_JS)
    START = SITE.find("// Accent theme.")
    END = SITE.find("})();", START) + len("})();")
    BLOCK = SITE[START:END] if START >= 0 else ""

    HARNESS = """
var __store = __STORE__;
var __attrs = {};
var __root = { setAttribute: function (k, v) { __attrs[k] = v; },
               removeAttribute: function (k) { delete __attrs[k]; } };
var __footer = { children: [], appendChild: function (n) { this.children.push(n); return n; } };
function mkButton() {
  return { type: "", className: "", textContent: "", _attrs: {},
           setAttribute: function (k, v) { this._attrs[k] = v; },
           addEventListener: function (ev, fn) { if (ev === "click") this._on = fn; },
           click: function () { if (this._on) this._on(); } };
}
var document = { documentElement: __root, readyState: "complete",
  querySelector: function (s) { return s === ".footer-right" ? __footer : null; },
  createElement: function () { return mkButton(); },
  querySelectorAll: function () { return []; }, addEventListener: function () {} };
var window = { location: { href: "https://raigulus.github.io/", origin: "https://raigulus.github.io" } };
window.localStorage = { getItem: function (k) { return k in __store ? __store[k] : null; },
                        setItem: function (k, v) { __store[k] = String(v); } };
__JS__
console.log(JSON.stringify({ attr: __attrs["data-theme"] || "",
                             button: __footer.children[0] ? __footer.children[0].textContent : "" }));
"""

    def run_theme(self, store):
        self.assertNotEqual(self.BLOCK, "", "theme block not found in site.js")
        src = self.HARNESS.replace("__STORE__", json.dumps(store)).replace("__JS__", self.BLOCK)
        if not os.path.isdir(TMP):
            os.makedirs(TMP)
        path = os.path.join(TMP, "theme.js")
        write(path, src)
        proc = subprocess.run(["node", path], capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr.strip()[-300:])
        for line in reversed(proc.stdout.strip().split("\n")):
            if line.startswith("{"):
                return json.loads(line)
        self.fail("no result")

    def test_default_visit_gets_no_theme_attribute(self):
        res = self.run_theme({})
        self.assertEqual(res["attr"], "")
        self.assertIn("Division", res["button"])

    def test_a_stored_theme_is_applied_on_load(self):
        for theme in ("ice", "toxic", "void"):
            self.assertEqual(self.run_theme({"raigulus-theme": theme})["attr"], theme)

    def test_the_button_names_the_active_theme(self):
        for theme, label in (("", "Division"), ("ice", "Ice"),
                             ("toxic", "Toxin"), ("void", "Void")):
            self.assertIn(label, self.run_theme({"raigulus-theme": theme})["button"])

    def test_an_unknown_stored_value_does_not_throw(self):
        for bad in ("nope", "../../etc/passwd", "'; DROP TABLE--", " ICE "):
            self.run_theme({"raigulus-theme": bad})

    CLICK_HARNESS = """
var __store = __STORE__;
var __attrs = {};
var __root = { setAttribute: function (k, v) { __attrs[k] = v; },
               removeAttribute: function (k) { delete __attrs[k]; } };
var __footer = { children: [], appendChild: function (n) { this.children.push(n); return n; } };
function mkButton() {
  return { type: "", className: "", textContent: "", _attrs: {},
           setAttribute: function (k, v) { this._attrs[k] = v; },
           addEventListener: function (ev, fn) { if (ev === "click") this._on = fn; },
           click: function () { if (this._on) this._on(); } };
}
var document = { documentElement: __root, readyState: "complete",
  querySelector: function (s) { return s === ".footer-right" ? __footer : null; },
  createElement: function () { return mkButton(); },
  querySelectorAll: function () { return []; }, addEventListener: function () {} };
var window = { location: { href: "https://raigulus.github.io/", origin: "https://raigulus.github.io" } };
window.localStorage = { getItem: function (k) { return k in __store ? __store[k] : null; },
                        setItem: function (k, v) { __store[k] = String(v); } };
__JS__
function snap() {
  return { attr: __attrs["data-theme"] || "",
           button: __footer.children[0] ? __footer.children[0].textContent : "",
           stored: __store["raigulus-theme"] === undefined ? "" : __store["raigulus-theme"] };
}
var __steps = [snap()];
for (var __i = 0; __i < __CLICKS__; __i++) {
  if (__footer.children[0]) __footer.children[0].click();
  __steps.push(snap());
}
console.log(JSON.stringify({ steps: __steps }));
"""

    NAMES = {"": "Division", "ice": "Ice", "toxic": "Toxin", "void": "Void", "light": "Light"}

    def run_clicks(self, store, clicks):
        self.assertNotEqual(self.BLOCK, "", "theme block not found in site.js")
        src = (self.CLICK_HARNESS.replace("__STORE__", json.dumps(store))
               .replace("__CLICKS__", str(clicks))
               .replace("__JS__", self.BLOCK))
        if not os.path.isdir(TMP):
            os.makedirs(TMP)
        path = os.path.join(TMP, "theme_clicks.js")
        write(path, src)
        proc = subprocess.run(["node", path], capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr.strip()[-300:])
        for line in reversed(proc.stdout.strip().split("\n")):
            if line.startswith("{"):
                return json.loads(line)["steps"]
        self.fail("no result")

    def test_repeated_presses_walk_every_theme(self):
        attrs = [s["attr"] for s in self.run_clicks({}, 6)]
        self.assertEqual(attrs, ["", "ice", "toxic", "void", "light", "", "ice"])

    def test_label_names_the_theme_that_is_active(self):
        for step in self.run_clicks({}, 5):
            self.assertEqual(step["button"], "Theme: " + self.NAMES[step["attr"]])

    def test_each_press_persists_what_it_applies(self):
        for step in self.run_clicks({}, 5)[1:]:
            self.assertEqual(step["stored"], step["attr"])

    def test_pressing_recovers_from_an_unknown_stored_theme(self):
        attrs = [s["attr"] for s in self.run_clicks({"raigulus-theme": "nope"}, 3)[1:]]
        self.assertEqual(attrs, ["ice", "toxic", "void"])

    def test_every_theme_in_the_script_has_a_stylesheet_block(self):
        for theme in ("ice", "toxic", "void"):
            self.assertIn(":root[data-theme=%s]" % theme, CSS)


class TestPvpValues(Base):
    """Brand and gear set bonuses must switch to their PvP overrides."""

    def two_pieces(self, key, value):
        picked = {}
        for slot, items in DATA["gear"].items():
            if slot in picked:
                continue
            for item in items:
                if (item.get(key) or "") == value:
                    picked[slot] = item["name"]
                    break
        return picked

    def summary(self, state, pvp):
        body = "clickBtn('bm-pvp', true);" if pvp else ""
        res = drive(hash_=b64(state), body=body)
        self.assertAlive(res)
        return res["summary"]

    def test_gear_set_bonus_uses_the_pvp_value(self):
        build = self.two_pieces("gear_set", "Aegis")
        self.assertEqual(len(build), 6, "Aegis should fill every slot")
        pve = self.summary({"m": build["mask"], "c": build["chest"]}, False)
        pvp = self.summary({"m": build["mask"], "c": build["chest"]}, True)
        self.assertIn("Health 70%", pve, "PvE 2pc Aegis should read 70%")
        self.assertIn("Health 100%", pvp, "PvP 2pc Aegis should read 100%")
        self.assertNotIn("Health 70%", pvp, "PvE value leaked into PvP mode")

    def test_brand_bonus_uses_the_pvp_value(self):
        build = self.two_pieces("brand_set", "Ceska Vyroba s.r.o.")
        self.assertEqual(len(build), 6, "Ceska should fill every slot")
        pve = self.summary({"m": build["mask"], "c": build["chest"]}, False)
        pvp = self.summary({"m": build["mask"], "c": build["chest"]}, True)
        self.assertIn("Shotgun Damage 24%", pve)
        self.assertIn("Shotgun Damage 12%", pvp)
        self.assertNotIn("Shotgun Damage 24%", pvp)

    def test_every_pvp_override_keeps_the_pve_attribute(self):
        """A PvP override may change a number, never the attribute it applies to."""
        def stats(bonus):
            return set(part.split(":")[1] for part in (bonus or "").split("|")
                       if part.startswith("stat:"))
        checked = 0
        for node in DATA["brands"] + DATA["gearSets"]:
            for pc in ("1", "2", "3"):
                over = node.get("pvp_%spc_bonus" % pc)
                if not over:
                    continue
                checked += 1
                self.assertEqual(stats(node.get(pc + "pc_bonus")), stats(over),
                                 "%s %spc swaps the attribute in PvP" % (node["name"], pc))
        self.assertGreater(checked, 25, "PvP overrides went missing from the data")


if __name__ == "__main__":
    unittest.main(verbosity=2)