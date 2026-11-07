"""Secure TEI XML parsing for SARIT editions.

* External entities, DTD loading and network access are disabled.
* Base text excludes <label> (locator echoes) and <note> (variant readings / editorial notes);
  notes are kept separately as variants.
* Locators come from the encoded xml:id attributes. No verse or page number is invented.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
T = "{%s}" % TEI_NS

STHANA_NAMES = {
    "Ca": {1: "Sūtrasthāna", 2: "Nidānasthāna", 3: "Vimānasthāna", 4: "Śārīrasthāna",
           5: "Indriyasthāna", 6: "Cikitsāsthāna", 7: "Kalpasthāna", 8: "Siddhisthāna"},
    "Ah": {1: "Sūtrasthāna", 2: "Śārīrasthāna", 3: "Nidānasthāna", 4: "Cikitsitasthāna",
           5: "Kalpasiddhisthāna", 6: "Uttarasthāna"},
}
WORK_NAMES = {"Ca": "Caraka Saṃhitā", "Ah": "Aṣṭāṅga Hṛdaya"}

ID_RE = re.compile(r"^(Ca|Ah)\.(\d+)\.(\d+)\.(.+)$")


def secure_parser() -> etree.XMLParser:
    return etree.XMLParser(
        resolve_entities=False, no_network=True, load_dtd=False, dtd_validation=False,
        huge_tree=True, remove_comments=True,
    )


def verse_key(rest: str) -> str:
    """'001a' -> '1'; '3ab' -> '3'; '027and1a' -> '27+1'; '016.1and1a' -> '16-1+1'; '9' -> '9'."""
    r = re.sub(r"(?<=\d)[a-f]{1,2}$", "", rest)
    parts = r.split(".")
    out = []
    for p in parts:
        p = p.replace("and", "+")
        p = re.sub(r"\b0+(\d)", r"\1", p)
        out.append(p)
    return "-".join(out)


def parse_xml_id(xml_id: str):
    m = ID_RE.match(xml_id)
    if not m:
        return None
    work, sth, ch, rest = m.groups()
    return work, int(sth), int(ch), verse_key(rest)


def _text_without(el, skip_tags: set[str]) -> str:
    """Concatenate text of el, skipping subtrees in skip_tags but keeping their tails."""
    parts: list[str] = []

    def walk(e):
        if e.text:
            parts.append(e.text)
        for child in e:
            if isinstance(child.tag, str) and etree.QName(child).localname in skip_tags:
                pass
            else:
                walk(child)
            if child.tail:
                parts.append(child.tail)

    walk(el)
    return "".join(parts)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class RawSegment:
    passage_id: str
    work_code: str
    sthana_no: int
    chapter_no: int
    verse: str
    xml_ids: list[str]
    segment_type: str
    text: str
    variants: list[tuple[str, str]] = field(default_factory=list)


def _segment_from(el, kind: str) -> RawSegment | None:
    if kind == "verse":
        lines = [l for l in el.iter(T + "l")] if etree.QName(el).localname == "lg" else [el]
    else:
        lines = [el]
    ids, texts, variants = [], [], []
    for l in lines:
        xid = l.get(XML_ID)
        if xid:
            ids.append(xid)
        texts.append(_clean(_text_without(l, {"label", "note"})))
        for n in l.iter(T + "note"):
            vt = _clean("".join(n.itertext()))
            if vt:
                variants.append((xid or "", vt))
    if not ids:
        return None
    parsed = parse_xml_id(ids[0])
    if not parsed:
        return None
    work, sth, ch, verse = parsed
    return RawSegment(
        passage_id=f"{work}.{sth}.{ch}.{verse}", work_code=work, sthana_no=sth, chapter_no=ch,
        verse=verse, xml_ids=ids, segment_type=kind, text=" ".join(t for t in texts if t),
        variants=variants,
    )


def parse_tei(path: Path) -> tuple[list[RawSegment], dict[str, str]]:
    """Return ordered segments (consecutive pieces with the same verse id merged) and
    chapter-name map {"Ca.3.2": "trividhakukṣīya..."} derived from colophon trailers."""
    tree = etree.parse(str(path), secure_parser())
    body = tree.getroot().find(f".//{T}body")
    segs: list[RawSegment] = []
    for el in body.iter(T + "lg", T + "p", T + "l"):
        name = etree.QName(el).localname
        if name == "l" and etree.QName(el.getparent()).localname == "lg":
            continue
        if name == "p" and el.get(XML_ID) is None:
            continue
        seg = _segment_from(el, "prose" if name == "p" else "verse")
        if seg is None:
            continue
        if segs and segs[-1].passage_id == seg.passage_id:
            prev = segs[-1]
            prev.xml_ids += seg.xml_ids
            prev.text = f"{prev.text} {seg.text}".strip()
            prev.variants += seg.variants
        else:
            segs.append(seg)

    chapter_names: dict[str, str] = {}
    for div in body.iter(T + "div"):
        first = next((e.get(XML_ID) for e in div.iter() if e.get(XML_ID)), None)
        if not first:
            continue
        p = parse_xml_id(first)
        if not p:
            continue
        key = f"{p[0]}.{p[1]}.{p[2]}"
        tr = div.find(T + "trailer")
        if tr is not None and key not in chapter_names:
            txt = _clean("".join(tr.itertext()))
            m = re.search(r"(\S+)\s+nām(?:a|ā)", txt)
            if m:
                chapter_names[key] = m.group(1)
    return segs, chapter_names
