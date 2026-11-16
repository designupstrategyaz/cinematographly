#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""pixabay_search.py — search Pixabay images and video under the licence rules: cache what the API
terms require you to cache, download what you are not allowed to hotlink, and write a provenance
record for every asset that lands.

The rules are in ../references/stock-sourcing.md, which carries the sources and the reasoning; this
script is only the mechanical half. It is NOT a rights clearance. A clean run means the query
worked — not that the asset can ship. That verdict is the per-asset check in stock-sourcing.md
section 5, and it is a human looking at the frame.

Usage
-----
  export PIXABAY_API_KEY=...                    # or --key-file PATH, or drop the key in
                                                # <plugin root>/.pixabay.key (gitignored, never
                                                # bundled) — see "The API key" below
  python3 pixabay_search.py -q "linen bedding morning light"
  python3 pixabay_search.py -q "bedroom" --type video --vertical
  python3 pixabay_search.py -q "bedroom" --type video --vertical --download _reference/environment/
  python3 pixabay_search.py -q "calm home" --orientation vertical --min-width 1080 --json
  python3 pixabay_search.py --selftest          # offline: no network, no key needed

Exit codes: 0 results · 1 nothing found / rate-limited / refused · 2 usage or IO error.

What it cannot do
-----------------
- **It cannot see inside the frame.** A recognisable face, a logo, a brand, a distinctive building —
  every blocker that actually stops a shot shipping (stock-sourcing.md section 5) is invisible to
  this script. It prints the checklist on every download precisely because it cannot run it.
- **It cannot detect AI-generated assets.** No API field exposes the uploader's AI label, so
  generated material cannot be filtered, flagged or counted. Human eye, every asset.
- **It cannot filter video orientation server-side** — the video endpoint has no `orientation`
  parameter. `--vertical` over-fetches and filters renditions locally, so a vertical video search
  costs more requests and returns fewer hits than the equivalent image search.
- **It cannot fetch music.** There is no documented audio endpoint (an undocumented /api/audio/ path
  resolves, is UNVERIFIED, and must not be built on). Music is a manual website pull into
  `06-music/` with a hand-written provenance record.
- **It cannot get the ORIGINAL image** without approved "full API access" — that gate covers only
  `fullHDURL` (<=1920px), `imageURL` and `vectorURL`. A default key still gets `largeImageURL` at up
  to 1280px, which this tool prefers automatically and which is adequate for reference and for most
  1080x1920 start frames. It does not rewrite `webformatURL` sizes (`_180`/`_340`/`_960`) for you.
- **It does not clear rights, and the sidecar it writes is not a licence.** The sidecar records what
  was downloaded, when, and under which terms version. That is evidence, not permission.

The API key
-----------
Tried in order: `--key-file PATH` · `$PIXABAY_API_KEY` · `<plugin root>/.pixabay.key` ·
`~/.config/pixabay.key` · `~/.pixabay.key`. There is deliberately no --key argument: a key passed on
the command line lands in shell history and in every process listing. The key is never printed,
never logged, never part of a cache filename and never written to a sidecar — every URL this script
emits is redacted (verified against a live key 2026-09-06: zero occurrences in any downloaded file,
sidecar, cache entry or recorded URL).

⛔ **Why `<plugin root>/.pixabay.key` and not somewhere inside `skills/`.** The bundler packages
`.claude-plugin/`, `hooks/` and `skills/` — nothing else — and the plugin bundle is UPLOADED to the
plugin marketplace and synced into cloud containers. A key under `skills/` would travel with it even
from a private repo. At the plugin root it is gitignored, unbundled, and stays on the machine that
holds it. The key is free, read-only and rotates in one click, but "private repo" is not the same
property as "does not leave this machine", and the bundle is the part that leaves.

Caching is not optional
-----------------------
The API terms say "requests must be cached for 24 hours". The wording is genuinely ambiguous between
a floor (do not re-request the same query inside 24h) and a ceiling (do not hold a response longer
than 24h), so this script satisfies both readings: a cached response under 24 hours old is served
instead of a request, and anything older is deleted. That is why `--no-cache` is refused; `--refresh`
is the honest escape hatch — it re-requests and re-caches. Note that the 24-hour rule governs API
*responses*; downloaded *media* may be kept forever under the perpetual licence. Different objects,
different rules.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys, tempfile, time
import urllib.error, urllib.parse, urllib.request

TERMS_VERSION = "2024-11-18"   # Pixabay Content Licence version this tool records against
ENDPOINTS = {"image": "https://pixabay.com/api/", "video": "https://pixabay.com/api/videos/"}
CACHE_TTL = 24 * 3600          # the API terms' 24-hour rule, honoured as both floor and ceiling
RESULT_CAP = 500               # default API access caps results per query
MAX_PAGES_CEILING = 5          # "Systematic mass downloads are not allowed."
RENDITIONS = ("large", "medium", "small", "tiny")
USER_AGENT = "cinematographly/pixabay_search.py"

BLOCKERS = [
    "recognisable face      -> HARD BLOCK for final footage (no release, none warranted, you indemnify)",
    "trademark/logo/brand   -> flat licence prohibition for commercial use, no cure available",
    "building / property    -> reserved rights; reference only, structure not reproduced",
    "transformation         -> a near-raw clip with a bumper is close to standalone redistribution",
    "AI output inherits every one of these: the generator launders pixels, not rights",
]


# --------------------------------------------------------------------------- pure helpers (tested)
def redact(url: str) -> str:
    """Never let a key reach a terminal, a log or a sidecar."""
    return re.sub(r"(key=)[^&]*", r"\1<REDACTED>", url)


def build_url(kind: str, params: dict) -> str:
    items = sorted((k, str(v)) for k, v in params.items() if v not in (None, ""))
    return ENDPOINTS[kind] + "?" + urllib.parse.urlencode(items, quote_via=urllib.parse.quote)


def cache_key(kind: str, params: dict) -> str:
    """Identity of a QUERY, not of a caller: the API key is excluded deliberately — it is a
    credential, it must never appear in a filename, and two keys asking the same question get the
    same answer."""
    stable = sorted((k, str(v)) for k, v in params.items() if k != "key" and v not in (None, ""))
    blob = kind + "|" + urllib.parse.urlencode(stable)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def video_renditions(hit: dict) -> list:
    out = []
    for name in RENDITIONS:
        r = (hit.get("videos") or {}).get(name)
        if isinstance(r, dict) and r.get("url"):
            out.append((name, r))
    return out


def vertical_renditions(hit: dict, min_ratio: float) -> list:
    """The video endpoint has NO orientation parameter, so portrait is decided here, per rendition,
    on the numbers the API does return."""
    keep = []
    for name, r in video_renditions(hit):
        try:
            w, h = int(r.get("width") or 0), int(r.get("height") or 0)
        except (TypeError, ValueError):
            continue
        if w > 0 and h > 0 and h > w and (h / w) >= min_ratio:
            keep.append((name, r))
    return keep


def combo_error(kind: str, vertical: bool, orientation) -> str | None:
    if kind == "image" and vertical:
        return ("--vertical is a client-side video filter. Images CAN be filtered server-side: "
                "use --orientation vertical.")
    if kind == "video" and orientation:
        return ("the video endpoint has NO orientation parameter — vertical cannot be filtered "
                "server-side. Use --vertical (client-side, per rendition), see stock-sourcing.md §6.")
    return None


def within_result_cap(page: int, per_page: int) -> bool:
    return page * per_page <= RESULT_CAP


def cache_is_fresh(mtime: float, now: float) -> bool:
    return (now - mtime) < CACHE_TTL


# ------------------------------------------------------------------------------------ cache / net
def default_cache_dir() -> str:
    home = os.path.expanduser("~")
    if home and os.path.isdir(home):
        return os.path.join(home, ".cache", "pixabay")
    return os.path.join(tempfile.gettempdir(), "pixabay-cache")


def cache_prune(cache_dir: str, now: float) -> int:
    """The ceiling reading of the 24-hour rule: nothing older than a day survives on disk."""
    dropped = 0
    if not os.path.isdir(cache_dir):
        return 0
    for name in os.listdir(cache_dir):
        if not name.endswith(".json") or name.startswith("_"):
            continue
        path = os.path.join(cache_dir, name)
        try:
            if not cache_is_fresh(os.path.getmtime(path), now):
                os.remove(path)
                dropped += 1
        except OSError:
            pass
    return dropped


def cache_load(path: str, now: float):
    try:
        if cache_is_fresh(os.path.getmtime(path), now):
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
    except (OSError, ValueError):
        return None
    return None


def cache_store(path: str, payload: dict) -> None:
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
    except OSError as e:
        print(f"warning: could not write cache ({e}) — the 24h caching obligation is not being met",
              file=sys.stderr)


def rl_path(cache_dir: str) -> str:
    return os.path.join(cache_dir, "_ratelimit.json")


def rl_load(cache_dir: str) -> dict:
    try:
        with open(rl_path(cache_dir), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def rl_store(cache_dir: str, state: dict) -> None:
    try:
        with open(rl_path(cache_dir), "w", encoding="utf-8") as fh:
            json.dump(state, fh)
    except OSError:
        pass


def http_json(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8")
        headers = {k.lower(): v for k, v in r.headers.items()}
    return json.loads(body), headers


def http_download(url: str, dest: str, timeout: int = 120) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    with open(dest, "wb") as fh:
        fh.write(data)
    return len(data)


# --------------------------------------------------------------------------------- normalisation
def normalise(kind: str, hit: dict, want: str, vertical: bool, min_ratio: float):
    """One record shape for both endpoints. pageURL and user are always present — that is the API
    terms' link-back obligation, so it is structural rather than a display option."""
    base = {"kind": kind, "id": hit.get("id"), "pageURL": hit.get("pageURL", ""),
            "user": hit.get("user", ""), "tags": hit.get("tags", "")}
    if kind == "video":
        rends = vertical_renditions(hit, min_ratio) if vertical else video_renditions(hit)
        if not rends:
            return None
        chosen = next((r for r in rends if r[0] == want), rends[0])
        name, r = chosen
        base.update({"rendition": name, "url": r.get("url", ""),
                     "width": int(r.get("width") or 0), "height": int(r.get("height") or 0),
                     "bytes": r.get("size"), "duration_s": hit.get("duration"),
                     "renditions_available": [n for n, _ in rends]})
    else:
        # Size ladder, best first. largeImageURL (<=1280px) IS available on a default key; only
        # fullHDURL (<=1920), imageURL (original) and vectorURL need approved full API access.
        # webformatURL is <=640px AND expires after 24h — last resort, and another reason to download.
        for field, name in (("fullHDURL", "fullHD"), ("largeImageURL", "large"),
                            ("webformatURL", "webformat")):
            if hit.get(field):
                url, rendition = hit[field], name
                break
        else:
            url, rendition = "", "none"
        base.update({"rendition": rendition, "url": url,
                     "width": hit.get("imageWidth"), "height": hit.get("imageHeight"),
                     "bytes": hit.get("imageSize"), "duration_s": None,
                     "full_api_access": bool(hit.get("fullHDURL"))})
    return base


def sidecar_record(rec: dict, filename: str) -> dict:
    return {
        "source": "pixabay",
        "id": rec["id"],
        "pageURL": rec["pageURL"],
        "user": rec["user"],
        "tags": rec["tags"],
        "width": rec.get("width"), "height": rec.get("height"),
        "duration_s": rec.get("duration_s"),
        "rendition": rec.get("rendition"),
        "rendition_url": rec.get("url"),
        "file": filename,
        "downloaded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "licence": {"name": "Pixabay Content License", "terms_version": TERMS_VERSION,
                    "attribution_required_in_ad": False,
                    "api_terms_link_back": "render pageURL + user wherever results are displayed",
                    "hotlinking": "prohibited — this file was downloaded, not linked"},
        "clearance": "NOT CLEARED — per-asset checks below are outstanding",
        "checks_outstanding": BLOCKERS,
        "reference": "references/stock-sourcing.md §5",
    }


def print_reminder(stream=sys.stdout) -> None:
    print("\n" + "-" * 88, file=stream)
    print("BEFORE ANY OF THIS SHIPS — check EACH asset, and each frame generated from it:", file=stream)
    for b in BLOCKERS:
        print(f"  ⛔ {b}", file=stream)
    print("The licence is permissive; the whole exposure is what is inside the frame. Attribution is",
          file=stream)
    print("not required in the ad — pageURL + user ARE, wherever you display results.", file=stream)
    print("Full reasoning: references/stock-sourcing.md §5.", file=stream)
    print("-" * 88, file=stream)


# --------------------------------------------------------------------------------------- the key
# Searched in order when neither --key-file nor $PIXABAY_API_KEY is set. All three are OUTSIDE the
# bundled tree (`.claude-plugin/`, `hooks/`, `skills/`), so a key placed in any of them is never
# packaged into the .plugin and never uploaded with it. The plugin-root file is .gitignored as well,
# which is what makes "keep it with the plugin" safe: local to this machine, and git never sees it.
def default_key_paths() -> list:
    # scripts/ -> skills/cinematographly -> skills -> <plugin root>
    plugin_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    return [os.path.join(plugin_root, ".pixabay.key"),
            os.path.expanduser("~/.config/pixabay.key"),
            os.path.expanduser("~/.pixabay.key")]


def resolve_key(key_file) -> str:
    if key_file:
        try:
            with open(os.path.expanduser(key_file), encoding="utf-8") as fh:
                key = fh.read().strip()
        except OSError as e:
            raise SystemExit(f"error: could not read --key-file: {e}")
        if not key:
            raise SystemExit(f"error: --key-file {key_file} is empty")
        return key
    key = (os.environ.get("PIXABAY_API_KEY") or "").strip()
    if key:
        return key
    for cand in default_key_paths():
        try:
            with open(cand, encoding="utf-8") as fh:
                key = fh.read().strip()
        except OSError:
            continue
        if key:
            return key
    raise SystemExit(
        "error: no API key. Any ONE of these, in the order they are tried:\n"
        "       $PIXABAY_API_KEY · --key-file PATH · " + " · ".join(default_key_paths()) + "\n"
        "       There is no --key argument on purpose: a key on the command line lands in shell\n"
        "       history and in every process listing. The key is personal and issued on login at\n"
        "       pixabay.com/api/docs; 100 requests per 60 seconds, bound to the key not your IP.\n"
        "\n"
        "       \u26d4 STOP HERE AND ASK. There are exactly two ways forward and improvising a\n"
        "       third is the failure this message exists to prevent:\n"
        "         1. the operator supplies a key (or points $PIXABAY_API_KEY at one), or\n"
        "         2. the operator supplies their own photographs, recorded with\n"
        "            `provenance.py record --source client-supplied --holder <who>`.\n"
        "       \u26d4 Do NOT substitute another stock library. Pixabay FORBIDS hotlinking and\n"
        "       Unsplash REQUIRES it, so one fetcher across two libraries breaks one library's\n"
        "       terms silently (stock-sourcing.md \u00a710). Do not hand-roll a downloader against\n"
        "       Wikimedia, Openverse, Pexels or a search engine's image results either: none of\n"
        "       them writes the \u00a79 provenance record, and an asset with no record cannot be\n"
        "       cleared. A missing key is a question for the operator, not a routing problem.")


# ---------------------------------------------------------------------------------- the query run
def query_params(a, page: int) -> dict:
    p = {"q": a.query, "page": page, "per_page": a.per_page, "order": a.order,
         "min_width": a.min_width, "min_height": a.min_height,
         "category": a.category, "lang": a.lang,
         "safesearch": "true" if a.safesearch else None,
         "editors_choice": "true" if a.editors_choice else None}
    if a.type == "image":
        p["image_type"] = a.image_type
        p["orientation"] = a.orientation
    else:
        p["video_type"] = a.video_type
    return {k: v for k, v in p.items() if v not in (None, "")}


def run_search(a, key: str, cache_dir: str) -> tuple:
    """Returns (records, total_hits, notes). Raises SystemExit(1) on rate-limit refusal."""
    now = time.time()
    state = rl_load(cache_dir)
    records, total, notes = [], None, []

    for offset in range(a.max_pages):
        page = a.page + offset
        if not within_result_cap(page, a.per_page):
            notes.append(f"stopped at page {page}: default API access caps results at "
                         f"{RESULT_CAP} per query")
            break

        params = query_params(a, page)
        ckey = cache_key(a.type, params)
        cpath = os.path.join(cache_dir, ckey + ".json")
        payload = None if a.refresh else cache_load(cpath, now)

        if payload is not None:
            notes.append(f"page {page}: served from cache (24h rule)")
        else:
            remaining = state.get("remaining")
            reset_at = state.get("reset_at", 0)
            if remaining is not None and remaining <= 0 and now < reset_at:
                print(f"error: rate limit exhausted (0 of {state.get('limit', '?')} remaining). "
                      f"Resets in {int(reset_at - now)}s.\n"
                      "       Waiting is the whole remedy — 'systematic mass downloads are not "
                      "allowed'.", file=sys.stderr)
                raise SystemExit(1)

            url = build_url(a.type, dict(params, key=key))
            try:
                payload, headers = http_json(url)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    print("error: HTTP 429 — rate limited by Pixabay. Back off and retry later.",
                          file=sys.stderr)
                    raise SystemExit(1)
                print(f"error: HTTP {e.code} for {redact(url)}", file=sys.stderr)
                raise SystemExit(2)
            except (urllib.error.URLError, ValueError, OSError) as e:
                print(f"error: request failed ({e}) for {redact(url)}", file=sys.stderr)
                raise SystemExit(2)

            try:
                state = {"limit": int(headers.get("x-ratelimit-limit", 0)) or state.get("limit"),
                         "remaining": int(headers.get("x-ratelimit-remaining", 0)),
                         "reset_at": now + int(headers.get("x-ratelimit-reset", 0) or 0)}
                rl_store(cache_dir, state)
                notes.append(f"page {page}: fetched; {state['remaining']} requests left this window")
            except (TypeError, ValueError):
                notes.append(f"page {page}: fetched (rate-limit headers unreadable)")
            cache_store(cpath, payload)

        total = payload.get("totalHits", total)
        hits = payload.get("hits") or []
        for hit in hits:
            rec = normalise(a.type, hit, a.rendition, a.vertical and a.type == "video", a.min_ratio)
            if rec:
                records.append(rec)
        if len(hits) < a.per_page:
            break
    return records, total, notes


def do_downloads(records: list, out_dir: str) -> int:
    """Hotlinking is prohibited, so a shot that will be used is a shot that is downloaded — with its
    provenance sidecar written at the same moment."""
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as e:
        print(f"error: cannot create {out_dir}: {e}", file=sys.stderr)
        return 2
    for rec in records:
        url = rec.get("url") or ""
        if not url:
            print(f"  [skip] id {rec['id']}: no rendition URL", file=sys.stderr)
            continue
        ext = os.path.splitext(urllib.parse.urlparse(url).path)[1] or (
            ".mp4" if rec["kind"] == "video" else ".jpg")
        stem = f"pixabay-{rec['id']}-{rec.get('rendition', 'src')}"
        media = os.path.join(out_dir, stem + ext)
        try:
            size = http_download(url, media)
        except (urllib.error.URLError, OSError) as e:
            print(f"  [fail] id {rec['id']}: {e}", file=sys.stderr)
            continue
        # `<media filename>.json`, appended — the one sidecar convention (provenance.sidecar_path).
        with open(media + ".json", "w", encoding="utf-8") as fh:
            json.dump(sidecar_record(rec, os.path.basename(media)), fh, indent=2, ensure_ascii=False)
        print(f"  [ ok ] {os.path.basename(media)}  {size/1e6:.1f} MB  + provenance sidecar")
    return 0


# ---------------------------------------------------------------------------------------- output
def emit(records: list, total, notes: list, as_json: bool) -> None:
    if as_json:
        json.dump({"count": len(records), "total_hits_reported": total,
                   "terms_version": TERMS_VERSION, "notes": notes,
                   "clearance": "NOT CLEARED — see references/stock-sourcing.md §5",
                   "results": records}, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return
    for i, r in enumerate(records, 1):
        dims = f"{r.get('width') or '?'}x{r.get('height') or '?'}"
        dur = f"  {r['duration_s']}s" if r.get("duration_s") else ""
        print(f"[{i:>3}] id {r['id']}  {dims}{dur}  rendition {r.get('rendition')}")
        print(f"      {r['tags']}")
        print(f"      {r['pageURL']}  · by {r['user']}")
    print(f"\n{len(records)} shown · totalHits reported: {total}")
    for n in notes:
        print(f"  · {n}")


# --------------------------------------------------------------------------------------- selftest
def selftest() -> int:
    fails = []

    def check(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    hit = {"videos": {"large":  {"url": "u", "width": 1920, "height": 1080},
                      "medium": {"url": "u", "width": 1080, "height": 1920},
                      "small":  {"url": "u", "width": 1000, "height": 1100},
                      "tiny":   {"url": "u", "width": 0,    "height": 0}}}
    keep = [n for n, _ in vertical_renditions(hit, 1.2)]
    check("vertical filter keeps only the portrait rendition at ratio 1.2", keep == ["medium"])
    keep105 = [n for n, _ in vertical_renditions(hit, 1.05)]
    check("--min-ratio 1.05 also keeps the 1000x1100 rendition", keep105 == ["medium", "small"])
    check("landscape and zero-dimension renditions are always dropped",
          "large" not in keep105 and "tiny" not in keep105)
    check("a hit with no portrait rendition normalises away under --vertical",
          normalise("video", {"id": 1, "videos": {"large": {"url": "u", "width": 1920,
                                                            "height": 1080}}},
                    "large", True, 1.2) is None)

    p1 = {"key": "AAA", "q": "linen bedding", "per_page": 20}
    p2 = {"key": "BBB", "q": "linen bedding", "per_page": 20}
    p3 = {"key": "AAA", "q": "linen sheets", "per_page": 20}
    k1 = cache_key("image", p1)
    check("cache key ignores the API key (query identity, not caller)", k1 == cache_key("image", p2))
    check("cache key changes with the query", k1 != cache_key("image", p3))
    check("cache key changes with the endpoint", k1 != cache_key("video", p1))
    check("cache key is opaque hex — no key material can leak into a filename",
          bool(re.fullmatch(r"[0-9a-f]{32}", k1)) and "AAA" not in k1)
    check("cache freshness is a 24h window", cache_is_fresh(100.0, 100.0 + CACHE_TTL - 1)
          and not cache_is_fresh(100.0, 100.0 + CACHE_TTL + 1))

    u = build_url("video", {"key": "SECRET", "q": "bedroom morning", "per_page": 50})
    check("video endpoint used for --type video", u.startswith(ENDPOINTS["video"]))
    check("image endpoint used for --type image",
          build_url("image", {"key": "S", "q": "x"}).startswith(ENDPOINTS["image"]))
    check("query is URL-encoded", "q=bedroom%20morning" in u)
    check("empty params are dropped", "lang=" not in build_url("image", {"key": "S", "q": "x",
                                                                        "lang": None}))
    check("redaction removes the key from any URL this tool prints",
          "SECRET" not in redact(u) and "key=<REDACTED>" in redact(u))

    check("images refuse --vertical and are pointed at --orientation",
          "orientation vertical" in (combo_error("image", True, None) or ""))
    check("video refuses --orientation and is pointed at --vertical",
          "NO orientation parameter" in (combo_error("video", False, "vertical") or ""))
    check("valid combinations pass", combo_error("video", True, None) is None
          and combo_error("image", False, "vertical") is None)
    check("the 500-result cap is enforced by page arithmetic",
          within_result_cap(25, 20) and not within_result_cap(26, 20))

    sc = sidecar_record({"id": 7, "pageURL": "p", "user": "u", "tags": "t", "kind": "image",
                         "width": 1, "height": 2, "rendition": "webformat", "url": "http://x/y.jpg"},
                        "y.jpg")
    check("sidecar carries the terms version and refuses to read as a clearance",
          sc["licence"]["terms_version"] == TERMS_VERSION and sc["clearance"].startswith("NOT CLEARED")
          and len(sc["checks_outstanding"]) == len(BLOCKERS))

    # the sidecar NAME is a contract with provenance.py and every reader — a stem-form sidecar here
    # and an appended one from `provenance.py record` is how a cleared asset reads back as uncleared
    # (found live 2026-09-06).
    import provenance as _pv
    check("the sidecar this script writes is the name every reader resolves",
          _pv.sidecar_path("/x/pixabay-1-large.jpg") == "/x/pixabay-1-large.jpg.json")

    print("-" * 60)
    print(f"RESULT: {'OK' if not fails else 'FAIL — ' + '; '.join(fails)}")
    return 1 if fails else 0


# ------------------------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-q", "--query", help="search terms (max 100 characters; encoded for you)")
    ap.add_argument("--type", choices=("image", "video"), default="image")
    ap.add_argument("--orientation", choices=("all", "horizontal", "vertical"),
                    help="IMAGES ONLY — the API supports this server-side for images and NOT for video")
    ap.add_argument("--image-type", choices=("all", "photo", "illustration", "vector"))
    ap.add_argument("--video-type", choices=("all", "film", "animation"))
    ap.add_argument("--vertical", action="store_true",
                    help="VIDEO ONLY, client-side: keep hits that have a portrait rendition "
                         "(height/width >= --min-ratio). It is client-side because the video "
                         "endpoint has NO orientation parameter — vertical cannot be filtered "
                         "server-side, so this over-fetches and filters each rendition locally.")
    ap.add_argument("--min-ratio", type=float, default=1.2,
                    help="portrait threshold for --vertical (default 1.2; true 9:16 is 1.78)")
    ap.add_argument("--min-width", type=int, help="absolute pixels, NOT aspect ratio")
    ap.add_argument("--min-height", type=int, help="absolute pixels, NOT aspect ratio")
    ap.add_argument("--category")
    ap.add_argument("--lang")
    ap.add_argument("--editors-choice", action="store_true")
    ap.add_argument("--safesearch", action="store_true")
    ap.add_argument("--order", choices=("popular", "latest"), default="popular")
    ap.add_argument("--per-page", type=int, default=20, help="3-200 (API limit)")
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--max-pages", type=int, default=1,
                    help=f"pages to walk from --page (max {MAX_PAGES_CEILING}); the guard that keeps "
                         "a search from becoming a systematic mass download")
    ap.add_argument("--rendition", choices=RENDITIONS, default="medium",
                    help="video rendition to prefer for --download (default medium)")
    ap.add_argument("--download", metavar="DIR",
                    help="fetch the chosen renditions here (hotlinking is prohibited) and write a "
                         "provenance sidecar per asset")
    ap.add_argument("--json", action="store_true", help="emit the result set for another tool")
    ap.add_argument("--cache-dir", help=f"default: {default_cache_dir()}")
    ap.add_argument("--no-cache", action="store_true", help="refused — see --refresh")
    ap.add_argument("--refresh", action="store_true",
                    help="re-request and re-cache instead of serving a fresh cache entry")
    ap.add_argument("--key-file", help="file containing the API key (alternative to $PIXABAY_API_KEY)")
    ap.add_argument("--selftest", action="store_true", help="offline checks; no network, no key")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    if a.no_cache:
        print("error: --no-cache is refused. The Pixabay API terms state that \"requests must be "
              "cached\n       for 24 hours\" — caching here is a term of use, not a performance "
              "choice.\n       Use --refresh to re-request and re-cache a single query, or "
              "--cache-dir to move\n       the cache. See references/stock-sourcing.md §7.",
              file=sys.stderr)
        return 2
    if not a.query:
        print("error: -q/--query is required (or --selftest)", file=sys.stderr)
        return 2
    if len(a.query) > 100:
        print(f"error: q is capped at 100 characters by the API (yours: {len(a.query)})",
              file=sys.stderr)
        return 2
    err = combo_error(a.type, a.vertical, a.orientation)
    if err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    if not 3 <= a.per_page <= 200:
        print("error: --per-page must be 3-200 (API limit)", file=sys.stderr)
        return 2
    if a.page < 1:
        print("error: --page starts at 1", file=sys.stderr)
        return 2
    if not 1 <= a.max_pages <= MAX_PAGES_CEILING:
        print(f"error: --max-pages must be 1-{MAX_PAGES_CEILING}. The API terms say \"systematic "
              f"mass\n       downloads are not allowed\", and default access caps a query at "
              f"{RESULT_CAP} results anyway.", file=sys.stderr)
        return 2

    try:
        key = resolve_key(a.key_file)
    except SystemExit as e:
        print(e.code if isinstance(e.code, str) else "error: no API key", file=sys.stderr)
        return 2

    cache_dir = os.path.expanduser(a.cache_dir or default_cache_dir())
    try:
        os.makedirs(cache_dir, exist_ok=True)
    except OSError as e:
        print(f"error: cannot create cache dir {cache_dir}: {e}", file=sys.stderr)
        return 2
    dropped = cache_prune(cache_dir, time.time())

    try:
        records, total, notes = run_search(a, key, cache_dir)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 2
    if dropped:
        notes.append(f"pruned {dropped} cache entries older than 24h")

    if not records:
        msg = "no results" + (" with a portrait rendition (try --min-ratio 1.0)" if a.vertical else "")
        print(f"{msg}. totalHits reported: {total}", file=sys.stderr)
        return 1

    emit(records, total, notes, a.json)

    if a.type == "image" and not any(r.get("full_api_access") for r in records):
        best = "largeImageURL (<=1280px)" if any(r.get("rendition") == "large" for r in records) \
            else "webformatURL (<=640px, expires in 24h)"
        print(f"note: default key — best available here is {best}. Only fullHDURL (<=1920px), "
              "imageURL (original) and vectorURL need approved \"full API access\"; 1280px is "
              "usually enough for reference and for a 1080x1920 start frame.",
              file=sys.stderr if a.json else sys.stdout)

    if a.download:
        print(f"\ndownloading {len(records)} asset(s) to {a.download} "
              "(hotlinking is prohibited — these are local copies):",
              file=sys.stderr if a.json else sys.stdout)
        rc = do_downloads(records, a.download)
        print_reminder(sys.stderr if a.json else sys.stdout)
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
