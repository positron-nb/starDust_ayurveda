"""Terminology, normalisation and transliteration helpers.

Transliteration (indic_transliteration) converts scripts; it is NOT translation and NOT clinical
normalisation. Raw input is always retained alongside derived forms.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from indic_transliteration import sanscript

from .config import settings

DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")
IAST_LETTERS = "a-zāīūṛṝḷḹṅñṭḍṇśṣṃḥ"


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def fold_ascii(s: str) -> str:
    """Remove diacritics, hyphens and avagraha apostrophes for loose matching."""
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[-'’]", "", s)


def has_devanagari(s: str) -> bool:
    return bool(DEVANAGARI_RE.search(s))


def deva_to_iast(s: str) -> str:
    return sanscript.transliterate(s, sanscript.DEVANAGARI, sanscript.IAST)


def iast_to_deva(s: str) -> str:
    # The AH e-text uses editorial hyphens inside compounds; drop them for Devanagari display.
    cleaned = re.sub(r"(?<=[^\d\s|/])-(?=[^\d\s])", "", s)
    return sanscript.transliterate(cleaned, sanscript.IAST, sanscript.DEVANAGARI)


@dataclass
class Concept:
    id: str
    label: dict
    aliases: dict
    patterns: list[re.Pattern]
    note: str = ""
    meta: bool = False


@dataclass
class Terminology:
    version: str
    concepts: list[Concept]

    @property
    def meta_ids(self) -> set[str]:
        return {c.id for c in self.concepts if c.meta}

    def by_id(self, cid: str) -> Concept | None:
        return next((c for c in self.concepts if c.id == cid), None)

    def tag_passage(self, text_iast: str) -> dict[str, list[tuple[int, int, str]]]:
        """Return concept_id -> list of (start, end, matched_text) in the original text."""
        low = nfc(text_iast).lower()
        out: dict[str, list[tuple[int, int, str]]] = {}
        for c in self.concepts:
            spans = []
            for p in c.patterns:
                for m in p.finditer(low):
                    spans.append((m.start(), m.end(), text_iast[m.start():m.end()]))
            if spans:
                # de-duplicate overlapping spans
                spans.sort()
                merged = []
                for s in spans:
                    if merged and s[0] < merged[-1][1]:
                        continue
                    merged.append(s)
                out[c.id] = merged
        return out

    def concepts_in_query(self, text: str, use_patterns: bool = True) -> dict[str, list[str]]:
        """Map free text (English / Hindi / IAST / ASCII) to concept ids with matched aliases."""
        raw = nfc(text).lower()
        folded = fold_ascii(raw)
        iast = deva_to_iast(raw) if has_devanagari(raw) else raw
        iast_folded = fold_ascii(iast)
        # passage patterns are only applied to genuinely Sanskrit-looking material: IAST words with
        # diacritics, or Devanagari input transliterated to IAST (avoids 'balanced' -> bala).
        iast_words = [w for w in re.findall(r"[\w'’-]+", raw) if re.search("[āīūṛṝḷṅñṭḍṇśṣṃḥ]", w)]
        pattern_text = " ".join(iast_words) + (" " + iast if has_devanagari(raw) else "")
        hits: dict[str, list[str]] = {}
        for c in self.concepts:
            matched = []
            for lang, aliases in c.aliases.items():
                for a in aliases:
                    a_low = nfc(a).lower()
                    if has_devanagari(a_low):
                        # word-boundary on the left always; short aliases (<=3 code points, e.g. 'अपच',
                        # 'बल') must also end at a word boundary so 'अपचित' / 'दुर्बल' do not match.
                        right = r"(?![ऀ-ॿ])" if len(a_low) <= 3 else ""
                        if re.search(r"(?<![ऀ-ॿ])" + re.escape(a_low) + right, raw):
                            matched.append(a)
                        continue
                    a_f = fold_ascii(a_low)
                    if len(a_f) < 3:
                        continue
                    pat = r"(?<![a-z])" + re.escape(a_f) + (r"(?:s|es)?(?![a-z])" if len(a_f) <= 5 else "")
                    if re.search(pat, folded) or re.search(pat, iast_folded):
                        matched.append(a)
            # also allow the passage patterns to fire on IAST/Devanagari-derived input
            if not matched and pattern_text and use_patterns:
                for p in c.patterns:
                    if p.search(pattern_text):
                        matched.append(c.label.get("iast", c.id))
                        break
            if matched:
                hits[c.id] = sorted(set(matched))
        # 'mandagni' etc. imply 'agni'
        for sub in ("mandagni", "vishamagni", "tikshnagni", "samagni"):
            if sub in hits and "agni" not in hits:
                hits["agni"] = [f"(via {sub})"]
        if "ajirna_types" in hits and "ajirna" not in hits:
            hits["ajirna"] = ["(via ajirna_types)"]
        return hits

    def expansion_terms(self, concept_ids: list[str]) -> list[str]:
        terms: list[str] = []
        for cid in concept_ids:
            c = self.by_id(cid)
            if not c:
                continue
            terms.extend(c.aliases.get("sa", []))
            terms.append(c.label.get("iast", ""))
        return [t for t in dict.fromkeys(terms) if t]


@lru_cache(maxsize=1)
def load_terminology(path: str | None = None) -> Terminology:
    p = Path(path) if path else settings.data_dir / "terminology" / "terminology.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    concepts = []
    for c in data["concepts"]:
        concepts.append(
            Concept(
                id=c["id"],
                label=c["label"],
                aliases=c.get("query_aliases", {}),
                patterns=[re.compile(nfc(x)) for x in c.get("passage_patterns", [])],
                note=c.get("note", ""),
                meta=bool(c.get("meta", False)),
            )
        )
    return Terminology(version=data["version"], concepts=concepts)


def tokenize_for_bm25(text: str) -> list[str]:
    """Tokens for BM25: ASCII-folded words with hyphens/avagraha removed, plus 5-char prefixes
    to soften Sanskrit inflection. Applied identically to queries and passages."""
    t = fold_ascii(nfc(text))
    words = re.findall(r"[a-z]+", t)
    toks: list[str] = []
    for w in words:
        if len(w) < 2:
            continue
        toks.append(w)
        if len(w) > 6:
            toks.append("p:" + w[:5])
    return toks
