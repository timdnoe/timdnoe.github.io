#!/usr/bin/env python3
"""Snapshot the Terebinth (TB) New Testament from AncientLibrary into /tb/data/.

AncientLibrary (https://ancientlibrary.org) is the single source of truth for the
text. This script mirrors the 27 NT books — the SBLGNT Greek, the TB translation,
and per-word morphology — into static JSON so the reader at /tb/ loads instantly,
works offline, and never depends on the API being up when a reviewer opens it.

Run locally with `python sync_tb.py`, or let the `Sync TB` GitHub Action keep it
fresh on a schedule / manual dispatch. Commit the regenerated /tb/data/ tree.

Flags:
  --books nt-john,nt-mark   only sync these book ids (default: all NT books)
  --no-words                skip per-word morphology (much faster; smaller files)
  --workers N               concurrency for API calls (default 12)
  --api URL                 API base (default https://ancientlibrary.org)
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
DATA_DIR = ROOT / "tb" / "data"
DEFAULT_API = "https://ancientlibrary.org"
TRANSLATION = "TB"  # the translation being showcased

# The 27 books of the New Testament, in canonical order, by AncientLibrary id.
NT_BOOKS = [
    "nt-matt", "nt-mark", "nt-luke", "nt-john", "nt-acts",
    "nt-rom", "nt-1cor", "nt-2cor", "nt-gal", "nt-eph", "nt-phil", "nt-col",
    "nt-1thess", "nt-2thess", "nt-1tim", "nt-2tim", "nt-titus", "nt-phlm",
    "nt-heb", "nt-jas", "nt-1pet", "nt-2pet", "nt-1john", "nt-2john", "nt-3john",
    "nt-jude", "nt-rev",
]


def get_json(api: str, path: str, retries: int = 4) -> dict | list:
    """GET {api}{path} and parse JSON, with exponential backoff on failure."""
    url = api + path
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "tb-sync/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"GET {url} failed after {retries} tries: {last}")


def work_meta(api: str, book: str) -> dict:
    return get_json(api, f"/api/works/{book}")


def read_chapter(api: str, book: str, chapter: int) -> dict:
    q = urllib.parse.urlencode({"translation_pref": TRANSLATION})
    return get_json(api, f"/api/read/{book}/{chapter}?{q}")


def verse_words(api: str, verse_id: str) -> list:
    enc = urllib.parse.quote(verse_id, safe="")
    try:
        data = get_json(api, f"/api/words/{enc}")
    except RuntimeError:
        return []
    return data if isinstance(data, list) else data.get("words", [])


def slim_word(w: dict) -> dict:
    return {
        "form": w.get("form_with_punctuation") or w.get("form"),
        "lemma": w.get("lexical"),
        "type": w.get("type"),
        "code": w.get("type_code"),
    }


def build_chapter(api: str, book: str, book_name: str, chapter: int, words: bool) -> dict:
    raw = read_chapter(api, book, chapter)
    verses_out = []
    word_jobs = {}  # verse index -> verse_id
    for i, v in enumerate(raw.get("verses", [])):
        verses_out.append({
            "v": v.get("verse"),
            "ref": v.get("canonical_reference"),
            "grc": v.get("original_text"),
            "lemmas": v.get("lemmas") or [],
            "tr": v.get("translation"),
            "para": v.get("paragraph_index"),
            "para_continued": v.get("translation_continued", False),
        })
        if words and v.get("id"):
            word_jobs[i] = v["id"]

    if word_jobs:
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(verse_words, api, vid): i for i, vid in word_jobs.items()}
            for fut in cf.as_completed(futs):
                i = futs[fut]
                verses_out[i]["words"] = [slim_word(w) for w in fut.result()]

    return {
        "book": book,
        "book_name": book_name,
        "chapter": chapter,
        "chapter_label": raw.get("chapter_label"),
        "prev": raw.get("prev_chapter"),
        "next": raw.get("next_chapter"),
        "verses": verses_out,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Snapshot TB NT from AncientLibrary.")
    ap.add_argument("--books", default="", help="comma-separated book ids (default: all NT)")
    ap.add_argument("--no-words", action="store_true", help="skip morphology")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--api", default=DEFAULT_API)
    args = ap.parse_args()

    api = args.api.rstrip("/")
    books = [b.strip() for b in args.books.split(",") if b.strip()] or NT_BOOKS
    words = not args.no_words

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Syncing {len(books)} book(s) from {api} (words={'on' if words else 'off'})")

    # Pull translation metadata for the TB entry (translator name etc.).
    tb_meta = {"id": TRANSLATION, "name": "Terebinth", "translator": "Timothy Noe"}
    try:
        for t in get_json(api, "/api/translations"):
            if t.get("translation_id") == TRANSLATION:
                tb_meta = {
                    "id": t["translation_id"],
                    "name": t.get("translation_name") or "Terebinth",
                    "translator": t.get("translator") or "Timothy Noe",
                }
                break
    except RuntimeError as exc:
        print(f"  (warning: could not read /api/translations: {exc})")

    manifest_books = []
    chapter_jobs = []  # (book, book_name, chapter)

    for book in books:
        meta = work_meta(api, book)
        total = meta.get("total_chapters") or 1
        name = (meta.get("title_english") or book).replace("Gospel According to ", "")
        name = name.replace("The ", "").strip()
        manifest_books.append({
            "id": book,
            "name": name,
            "greek_title": meta.get("title"),
            "chapters": total,
            "verses": meta.get("total_verses"),
            "greek_source": meta.get("greek_text_source"),
            "subcategory": meta.get("subcategory"),
        })
        for ch in range(1, total + 1):
            chapter_jobs.append((book, name, ch))
        print(f"  {book}: {total} chapters")

    # Fan out chapter builds. Each chapter internally parallelizes its word calls.
    done = 0
    errors = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {
            ex.submit(build_chapter, api, b, n, ch, words): (b, ch)
            for (b, n, ch) in chapter_jobs
        }
        for fut in cf.as_completed(futs):
            b, ch = futs[fut]
            try:
                data = fut.result()
            except Exception as exc:  # noqa: BLE001 - record and continue
                errors.append(f"{b} ch{ch}: {exc}")
                continue
            out = DATA_DIR / b / f"{ch}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), "utf-8")
            done += 1
            if done % 25 == 0:
                print(f"    {done}/{len(chapter_jobs)} chapters written")

    manifest = {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "source": "https://ancientlibrary.org",
        "greek_source": "SBLGNT (Society of Biblical Literature Greek New Testament)",
        "translation": tb_meta,
        "has_morphology": words,
        "books": manifest_books,
    }
    (DATA_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8"
    )

    print(f"Done: {done}/{len(chapter_jobs)} chapters, manifest written to {DATA_DIR/'manifest.json'}")
    if errors:
        print(f"WARNING: {len(errors)} chapter(s) failed:", file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
