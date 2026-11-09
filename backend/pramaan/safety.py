"""Tri-state fact extraction and structured safety-rule evaluation (outside the model).

Extraction is deterministic and deliberately simple; the user confirms or edits every fact in the
UI. 'unknown' is never coerced to 'absent'.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from .config import settings
from .schemas import CaseFact, SafetyAlert
from .terms import Terminology, fold_ascii, nfc

FACT_KEYS = ["pregnancy", "lactation", "pediatric", "medications", "serious_comorbidity",
             "emergency_signs", "dose_request", "stop_medication_request", "proposed_herbs"]

CURATED_HERBS = {"ashwagandha"}  # herbs with a curated modern safety source

# Herbs we can recognise but have NO curated safety source for (-> 'not assessed').
OTHER_HERBS = {
    "turmeric": ["turmeric", "haridra", "हल्दी", "हरिद्रा"],
    "triphala": ["triphala", "त्रिफला"],
    "guduchi": ["guduchi", "giloy", "गिलोय", "गुडूची"],
    "brahmi": ["brahmi", "ब्राह्मी"],
    "shatavari": ["shatavari", "शतावरी"],
    "ginger": ["ginger", "shunthi", "sunthi", "अदरक", "सोंठ", "शुण्ठी"],
    "guggulu": ["guggulu", "guggul", "गुग्गुल"],
    "trikatu": ["trikatu", "त्रिकटु"],
    "hingu": ["hingu", "asafoetida", "हींग"],
}

NEG_EN = r"(?:not|no|never|isn't|is not|non)"
PREG_POS = [r"\bpregnan\w*", r"\bexpecting a baby\b", r"\btrimester\b", r"गर्भवती", r"गर्भावस्था", r"गर्भ से"]
PREG_NEG = [r"\bnot pregnant\b", r"\bnon[- ]?pregnant\b", r"\bno pregnancy\b", r"\bisn'?t pregnant\b",
            r"\bpregnancy[: ]+(?:no|negative|absent)\b", r"गर्भवती नहीं", r"\bmale\b", r"\bman\b", r"पुरुष"]
# In the QUESTION, pregnancy/lactation become 'present' only on an explicit assertion about a
# person ("I am pregnant", "my wife is pregnant", "मैं गर्भवती हूँ"). Topic mentions such as
# "Is X safe in pregnancy?" keep the state 'unknown'. Text in the CASE box describes the case,
# so plain mentions there count as present.
PREG_ASSERT = [r"\b(?:i am|i'm|im|she is|she's|patient is|wife is|daughter is|mother is|i was recently|currently)\s+(?:\w+\s+)?pregnant\b",
               r"\bmy pregnancy\b", r"\b\d+\s*(?:weeks?|months?)\s+pregnant\b", r"\bpregnant\s+(?:woman|patient|lady|mother),?\s+\d",
               r"(?:मैं|वह|पत्नी|मरीज)\s+(?:\S+\s+)?गर्भवती", r"गर्भवती\s+(?:हूँ|हूं|है|हैं)", r"मेरी गर्भावस्था"]
LACT_ASSERT = [r"\b(?:i am|i'm|she is|she's|patient is|wife is)\s+(?:currently\s+)?(?:breast-?feeding|nursing|lactating)\b",
               r"\bi breast-?feed\b", r"(?:मैं|वह|पत्नी)\s+(?:\S+\s+)?स्तनपान\s+(?:करा|कर)"]
LACT_POS = [r"\bbreast-?feed\w*", r"\blactat\w*", r"\bnursing\b", r"स्तनपान"]
LACT_NEG = [r"\bnot breast-?feeding\b", r"\bnot lactating\b", r"\bnot nursing\b", r"स्तनपान नहीं", r"\bmale\b", r"\bman\b", r"पुरुष"]
AGE_RE = re.compile(r"(\d{1,3})\s*(?:-|\s)?\s*(?:years?|yrs?|y/o|yo|year-old|वर्ष|साल)", re.I)
CHILD_WORDS = [r"\bchild\b", r"\binfant\b", r"\bbaby\b", r"\btoddler\b", r"\bboy\b", r"\bgirl\b", r"बच्च", r"शिशु"]
ADULT_WORDS = [r"\badult\b", r"\bwoman\b", r"\bman\b", r"वयस्क", r"\bstudent\b"]
MED_NEG = [r"\bno (?:current )?medications?\b", r"\bno medicines?\b", r"\bnot (?:taking|on) any\b", r"\bno drugs\b",
           r"कोई दवा नहीं", r"दवा नहीं लेत"]
MED_POS = [r"\btaking (\w+) (?:tablets?|medication|medicine|pills?)", r"\bon (\w+) (?:tablets?|medication)", r"\bcurrent medications?\b",
           r"\bprescribed\b", r"\btablets?\b", r"\bpills?\b",
           r"\bmetformin\b", r"\binsulin\b", r"\blevothyroxine\b", r"\bthyroxine\b", r"\bamlodipine\b", r"\bsedative",
           r"\bantiepileptic", r"\bimmunosuppress", r"दवा", r"गोली"]
COMORB = {
    "thyroid": [r"\bthyroid\b", r"\bhypothyroid\w*", r"\bhyperthyroid\w*", r"थायरॉइड", r"थायराइड"],
    "autoimmune": [r"\bautoimmune\b", r"\blupus\b", r"\brheumatoid\b", r"ऑटोइम्यून"],
    "surgery": [r"\bsurgery\b", r"\boperation\b", r"सर्जरी", r"ऑपरेशन"],
    "prostate cancer": [r"\bprostate cancer\b"],
    "liver": [r"\bliver disease\b", r"\bhepatitis\b", r"\bcirrhosis\b", r"\bjaundice\b", r"लिवर", r"पीलिया"],
    "diabetes": [r"\bdiabet\w*", r"मधुमेह", r"शुगर"],
    "hypertension": [r"\bhypertension\b", r"\bhigh blood pressure\b", r"\bbp\b", r"उच्च रक्तचाप", r"बीपी"],
    "kidney": [r"\bkidney disease\b", r"\brenal\b", r"किडनी"],
    "cancer": [r"\bcancer\b", r"कैंसर"],
    "heart disease": [r"\bheart disease\b", r"\bcardiac\b", r"हृदय रोग"],
    "epilepsy": [r"\bepilep\w*", r"मिर्गी"],
}
COMORB_NEG = [r"\bno (?:known )?(?:comorbidit\w*|medical history|chronic (?:illness|disease)s?)\b", r"\botherwise healthy\b",
              r"कोई बीमारी नहीं"]


def _find(patterns: list[str], text: str) -> list[str]:
    out = []
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            out.append(m.group(0))
    return out


@dataclass
class Policy:
    version: str
    templates: dict
    lexicons: dict
    rules: list[dict]


@lru_cache(maxsize=4)
def load_policy(path: str | None = None) -> Policy:
    p = Path(path) if path else settings.data_dir / "rules" / "safety_rules.yaml"
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    return Policy(version=d["version"], templates=d["templates"], lexicons=d["lexicons"], rules=d["rules"])


@lru_cache(maxsize=2)
def load_safety_statements() -> dict[str, dict]:
    d = json.loads((settings.data_dir / "sources" / "external" / "nccih_ashwagandha.json").read_text(encoding="utf-8"))
    return {s["id"]: {**s, "url": d["url"], "accessed": d["accessed"], "page_last_updated": d["page_last_updated"]}
            for s in d["statements"]}


def extract_facts(text: str, terms: Terminology, policy: Policy, case_text: str = "") -> list[CaseFact]:
    """`text` is the user's question; `case_text` the (synthetic) case description."""
    q = nfc(text)
    case = nfc(case_text or "")
    t = (q + "\n" + case).strip()
    facts: dict[str, CaseFact] = {k: CaseFact(key=k, state="unknown") for k in FACT_KEYS}

    def setf(key, state, values=None, ev=None):
        facts[key] = CaseFact(key=key, state=state, values=values or [], origin="extracted", evidence_text=ev)

    def tri(key, neg_p, assert_p, pos_p):
        neg = _find(neg_p, t)
        pos = _find(assert_p, q) + _find(pos_p, case) + _find(assert_p, case)
        topic = _find(pos_p, q)
        if neg:
            setf(key, "absent", ev=neg[0])
        elif pos:
            setf(key, "present", ev=pos[0])
        elif topic:
            facts[key] = CaseFact(key=key, state="unknown", values=["mentioned as a topic, not stated about this person"],
                                  origin="extracted", evidence_text=topic[0])

    tri("pregnancy", PREG_NEG, PREG_ASSERT, PREG_POS)
    tri("lactation", LACT_NEG, LACT_ASSERT, LACT_POS)

    ages = [int(m.group(1)) for m in AGE_RE.finditer(t)]
    if ages:
        a = ages[0]
        setf("pediatric", "present" if a < 18 else "absent", values=[f"age {a}"], ev=f"{a} years")
    elif _find(CHILD_WORDS, t):
        setf("pediatric", "present", ev=_find(CHILD_WORDS, t)[0])
    elif _find(ADULT_WORDS, t):
        setf("pediatric", "absent", ev=_find(ADULT_WORDS, t)[0])

    neg = _find(MED_NEG, t)
    if neg:
        setf("medications", "absent", ev=neg[0])
    else:
        pos = _find(MED_POS, t)
        if pos:
            setf("medications", "present", values=sorted(set(pos)), ev=pos[0])

    found = {name: _find(pats, t) for name, pats in COMORB.items()}
    found = {k: v for k, v in found.items() if v}
    if found:
        setf("serious_comorbidity", "present", values=sorted(found), ev=next(iter(found.values()))[0])
    elif _find(COMORB_NEG, t):
        setf("serious_comorbidity", "absent", ev=_find(COMORB_NEG, t)[0])

    def lex(key):
        words = policy.lexicons.get(key, {})
        low = t.lower()
        hits = [w for lang in words for w in words[lang] if w.lower() in low]
        return hits

    em = lex("emergency_signs")
    if em:
        setf("emergency_signs", "present", values=em, ev=em[0])
    # emergency_signs stays 'unknown' otherwise: absence of red-flag words is not a negative screen.
    dr = lex("dose_request")
    setf("dose_request", "present" if dr else "absent", values=dr, ev=dr[0] if dr else None)
    sm = lex("stop_medication_request")
    # pattern form catches word-order variants the lexicon misses ("stop my metformin", "replace my BP tablets")
    m = re.search(r"\b(?:stop|quit|discontinue|leave|replace|skip|come off)\b[^.?!]{0,30}?\b(?:medicines?|medications?|tablets?|pills?|drugs?|"
                  r"metformin|insulin|thyroxine|levothyroxine|amlodipine|warfarin|statins?|steroids?|antidepressants?)\b", t, re.I)
    m_hi = re.search(r"(?:दवा|दवाई|गोली|इंसुलिन)\S*\s+(?:\S+\s+){0,3}?(?:बंद|छोड़|छोड)", t)
    sm = sm + [x.group(0) for x in (m, m_hi) if x]
    setf("stop_medication_request", "present" if sm else "absent", values=sm, ev=sm[0] if sm else None)

    herbs = []
    q = terms.concepts_in_query(t)
    if "ashwagandha" in q:
        herbs.append("ashwagandha")
    folded = fold_ascii(t)
    for h, al in OTHER_HERBS.items():
        for a in al:
            if (a in t) or (fold_ascii(a) in folded and re.search(r"(?<![a-z])" + re.escape(fold_ascii(a)), folded)):
                herbs.append(h)
                break
    if herbs:
        setf("proposed_herbs", "present", values=sorted(set(herbs)), ev=", ".join(sorted(set(herbs))))
    else:
        setf("proposed_herbs", "absent")
    return list(facts.values())


def merge_facts(extracted: list[CaseFact], user: list[CaseFact] | None) -> list[CaseFact]:
    if not user:
        return extracted
    by = {f.key: f for f in extracted}
    for f in user:
        origin = f.origin if f.origin in ("user_confirmed", "user_edited") else "user_edited"
        by[f.key] = CaseFact(key=f.key, state=f.state, values=f.values, origin=origin, evidence_text=f.evidence_text)
    return [by[k] for k in FACT_KEYS if k in by]


def _fact(facts: list[CaseFact], key: str) -> CaseFact:
    return next((f for f in facts if f.key == key), CaseFact(key=key, state="unknown"))


def evaluate_rules(facts: list[CaseFact], policy: Policy, lang: str = "en") -> list[SafetyAlert]:
    herbs = set(_fact(facts, "proposed_herbs").values)
    statements = load_safety_statements()
    alerts: list[SafetyAlert] = []
    for r in policy.rules:
        c = r["condition"]
        if "herb" in c:
            h = c["herb"]
            if h == "any" and not herbs:
                continue
            if h == "uncurated" and not (herbs - CURATED_HERBS):
                continue
            if h not in ("any", "uncurated") and h not in herbs:
                continue
        if "fact" in c:
            f = _fact(facts, c["fact"])
            if f.state != c["state"]:
                continue
            if "any_of" in c and not (set(c["any_of"]) & set(f.values)):
                continue
        o = r["outcome"]
        b = r["basis"]
        if o["action"] == "escalate":
            continue  # handled by escalation(), never mixed with ordinary alerts
        msg = o.get(f"message_{lang}") or o.get("message_en", "")
        if c.get("herb") == "uncurated":
            names = ", ".join(sorted(herbs - CURATED_HERBS))
            msg = f"[{names}] " + msg
        st = statements.get(b.get("statement_id") or b.get("related_statement_id") or "")
        alerts.append(SafetyAlert(
            rule_id=r["id"], title=r["title"], action=o["action"], severity=o["severity"], message=msg,
            question=o.get(f"question_{lang}") or o.get("question_en"),
            basis_type=b["type"], basis_text=b.get("text"), source_id=b.get("source_id") or (st and "nccih-ashwagandha"),
            statement_id=st["id"] if st else None,
            statement_paraphrase=st["paraphrase"] if st else None,
            statement_scope=st["scope"] if st else None,
            source_url=st["url"] if st else None,
            review_status=r.get("review_status", "pending"),
        ))
    return alerts


def escalation(facts: list[CaseFact], policy: Policy, lang: str = "en") -> tuple[str, str] | None:
    em = _fact(facts, "emergency_signs")
    if em.state != "present":
        return None
    rule = next(r for r in policy.rules if r["outcome"]["action"] == "escalate")
    tpl = policy.templates[rule["outcome"]["template"]]
    text = tpl.get(lang) or tpl["en"]
    return rule["id"], text.format(matched=", ".join(em.values[:3]))


def withholds_positive_use(alerts: list[SafetyAlert]) -> bool:
    return any(a.action in ("withhold_positive_use", "request_information", "not_assessed") for a in alerts)
