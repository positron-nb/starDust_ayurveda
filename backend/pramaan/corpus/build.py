"""Build the PRAMAAN corpus from pinned sources.

    python -m pramaan.corpus.build            # verify checksums, parse TEI, write corpus.sqlite
    python -m pramaan.corpus.build --fetch    # also download missing raw files (allowlisted URLs)

Only URLs listed in data/sources/manifest.json under an allowlisted host are fetched, and every
file must match its pinned sha256.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import yaml

from ..config import REPO_ROOT, settings
from ..schemas import Gloss, Passage, Variant
from ..terms import iast_to_deva, load_terminology
from .store import CorpusStore, sha256_file, sha256_text
from .tei import STHANA_NAMES, WORK_NAMES, parse_tei

ALLOWED_HOSTS = {"raw.githubusercontent.com"}


def load_manifest() -> dict:
    return json.loads((settings.data_dir / "sources" / "manifest.json").read_text(encoding="utf-8"))


def fetch(src: dict, dest: Path) -> None:
    url = src["download_url"]
    host = urlparse(url).hostname
    if host not in ALLOWED_HOSTS or urlparse(url).scheme != "https":
        raise SystemExit(f"Refusing to fetch non-allowlisted URL: {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:  # noqa: S310 (allowlisted)
        f.write(r.read())
    tmp.replace(dest)


def verify(src: dict, path: Path) -> str:
    actual = sha256_file(path)
    if actual != src["sha256"]:
        raise SystemExit(f"Checksum mismatch for {src['source_id']}: expected {src['sha256']}, got {actual}")
    return actual


def build(out: Path, do_fetch: bool = False) -> dict:
    manifest = load_manifest()
    terms = load_terminology()
    modules = yaml.safe_load((settings.data_dir / "curated" / "modules.yaml").read_text(encoding="utf-8"))
    gl = yaml.safe_load((settings.data_dir / "curated" / "glosses_draft.yaml").read_text(encoding="utf-8"))

    if out.exists():
        out.unlink()
    out.parent.mkdir(parents=True, exist_ok=True)
    store = CorpusStore(out)
    store.put_meta("manifest_version", manifest["manifest_version"])
    store.put_meta("terms_version", terms.version)
    store.put_meta("modules_version", modules["version"])

    chapter_prefixes: dict[str, list[tuple[str, str]]] = {}
    herb_filters: dict[str, list[tuple[str, str]]] = {}
    chapter_display: dict[str, str] = {}
    for m in modules["modules"]:
        for ch in m.get("chapters", []):
            chapter_prefixes.setdefault(ch["source_id"], []).append((ch["prefix"], m["module_id"]))
            chapter_display[ch["prefix"].rstrip(".")] = ch["name"]
        for tf in m.get("term_filter", []):
            herb_filters.setdefault(tf["source_id"], []).append((tf["concept"], m["module_id"]))

    stats = {}
    for src in manifest["sources"]:
        if src["kind"] != "classical_text":
            store.put_source(src, None)
            continue
        path = REPO_ROOT / src["local_path"]
        if not path.exists():
            if not do_fetch:
                raise SystemExit(f"Missing {path}. Run with --fetch.")
            fetch(src, path)
        file_hash = verify(src, path)
        store.put_source(src, file_hash)
        segs, chapter_names = parse_tei(path)
        n_idx = 0
        for pos, s in enumerate(segs):
            tags = terms.tag_passage(s.text)
            mods = [mid for (pref, mid) in chapter_prefixes.get(src["source_id"], []) if (s.passage_id + ".").startswith(pref) or s.passage_id.startswith(pref)]
            for concept, mid in herb_filters.get(src["source_id"], []):
                if concept in tags and mid not in mods:
                    mods.append(mid)
            ch_key = f"{s.work_code}.{s.sthana_no}.{s.chapter_no}"
            sthana = STHANA_NAMES[s.work_code].get(s.sthana_no, f"Sthāna {s.sthana_no}")
            p = Passage(
                passage_id=s.passage_id,
                source_id=src["source_id"],
                work=WORK_NAMES[s.work_code],
                sthana=sthana,
                sthana_no=s.sthana_no,
                chapter_no=s.chapter_no,
                chapter_name=chapter_display.get(ch_key) or chapter_names.get(ch_key) or f"{WORK_NAMES[s.work_code]}, {sthana} {s.chapter_no}",
                verse_label=f"{sthana} {s.chapter_no}.{s.verse}",
                xml_ids=s.xml_ids,
                segment_type=s.segment_type,
                text_iast=s.text,
                text_deva=iast_to_deva(s.text),
                text_hash=sha256_text(s.text),
                variants=[Variant(locator=a, text=b) for a, b in s.variants],
                modules=mods,
                concepts=sorted(tags.keys()),
                position=pos,
            )
            indexed = bool(mods)
            n_idx += indexed
            store.put_passage(p, indexed)
        stats[src["source_id"]] = {"segments": len(segs), "indexed": n_idx}

    for pid, text in (gl.get("glosses") or {}).items():
        store.put_gloss(pid, Gloss(lang="en", text=text, author=gl["author"], method=gl["method"],
                                   review_status=gl["review_status"]))
    store.commit()
    cv = store.compute_corpus_version()
    store.put_meta("corpus_version", cv)
    store.commit()
    stats["corpus_version"] = cv
    return stats


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--out", default=str(settings.corpus_db))
    a = ap.parse_args(argv)
    stats = build(Path(a.out), a.fetch)
    sys.stdout.write(json.dumps(stats, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
