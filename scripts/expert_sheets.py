"""Build the reviewer workbooks from the newest eval/expert_validation/answers_*.json (see expert_validation.py)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
OUT = ROOT / "eval" / "expert_validation"
DELIVER = ROOT / "docs" / "review"

F = "Arial"
HEAD = PatternFill("solid", fgColor="1E4D2B")
FILL = PatternFill("solid", fgColor="FFF2A8")  # cells the reviewer fills in
EXAMPLE = PatternFill("solid", fgColor="EDEDED")
THIN = Border(*(Side(style="thin", color="D0CCC0"),) * 4)
WRAP = Alignment(wrap_text=True, vertical="top")


def _head(ws, cols):
    for i, (name, width) in enumerate(cols, start=1):
        c = ws.cell(row=1, column=i, value=name)
        c.font = Font(name=F, bold=True, color="FFFFFF")
        c.fill = HEAD
        c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[c.column_letter].width = width
    ws.row_dimensions[1].height = 42
    ws.freeze_panes = "B2"


def _row(ws, r, values, fill_from=None, example=False):
    for i, v in enumerate(values, start=1):
        c = ws.cell(row=r, column=i, value=v)
        c.font = Font(name=F, italic=example, color="666666" if example else "000000")
        c.alignment = WRAP
        c.border = THIN
        if example:
            c.fill = EXAMPLE
        elif fill_from and i >= fill_from:
            c.fill = FILL


def _dropdown(ws, col_letter, n_rows, options, first=2):
    dv = DataValidation(type="list", formula1='"' + ",".join(options) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"{col_letter}{first}:{col_letter}{first + n_rows - 1}")


def _readme(wb, title, lines):
    ws = wb.active
    ws.title = "Read me"
    ws.column_dimensions["A"].width = 110
    ws["A1"] = title
    ws["A1"].font = Font(name=F, bold=True, size=14, color="1E4D2B")
    for i, line in enumerate(lines, start=3):
        c = ws.cell(row=i, column=1, value=line)
        c.font = Font(name=F, bold=line.startswith("•") is False and line.endswith(":"))
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.cell(row=len(lines) + 4, column=1, value="Legend: yellow cells = please fill in · grey italic row = example only").fill = FILL


def answers_sheet(wb, data, name="1 Answers"):
    ws = wb.create_sheet(name)
    cols = [("ID", 7), ("Lang", 6), ("Question", 28), ("AyurParam explanation shown to the user (each sentence with the verse it cites)", 55),
            ("Verses shown, in order (first 3)", 60),
            ("Q1. Are the verses shown relevant to the question?", 16),
            ("Q2. Does each explanation sentence say what its cited verse says?", 18),
            ("Q3. Is the explanation clinically correct?", 16),
            ("Q4. Overall answer quality", 14), ("Comments (optional)", 30)]
    _head(ws, cols)
    for r, a in enumerate(data["answers"], start=2):
        if a["shown"]:
            expl = "\n".join(f"• {s['text']}  [{', '.join(s['passages']) or ', '.join(s['cites'])}]" for s in a["shown"])
        else:
            expl = "(No explanation sentence passed the checks, so only the verses were shown. For Q2–Q3 choose \"No explanation\".)"
        verses = "\n\n".join(f"{e['label']} · {e['locator']}\n{e['iast'][:260]}" for e in a["evidence"][:3])
        _row(ws, r, [a["qid"], a["lang"].upper(), a["query"], expl, verses, None, None, None, None, None], fill_from=6)
        ws.row_dimensions[r].height = 150
    n = len(data["answers"])
    _dropdown(ws, "F", n, ["Yes", "Partly", "No"])
    _dropdown(ws, "G", n, ["Yes", "Partly", "No", "No explanation"])
    _dropdown(ws, "H", n, ["Yes", "Partly", "No", "No explanation"])
    _dropdown(ws, "I", n, ["Good", "Acceptable", "Poor"])
    return ws


def definitions_sheet(wb):
    from pramaan.corpus.store import CorpusStore
    from pramaan.config import settings
    from pramaan.terms import load_terminology
    store = CorpusStore(settings.corpus_db)
    ws = wb.create_sheet("2 Definition verses")
    _head(ws, [("Concept", 22), ("Verse shown first (and next)", 22), ("Verse text (IAST)", 60), ("Devanagari", 50),
               ("Right verse to show first?", 14), ("If not: better verse (e.g. Ca. Sū. 12.8)", 22), ("Comments", 30)])
    r = 2
    for c in load_terminology().concepts:
        if not c.definition_verses:
            continue
        ps = [store.get(pid) for pid in c.definition_verses]
        _row(ws, r, [c.label.get("en", c.id), "\n".join(c.definition_verses),
                     "\n".join(p.text_iast for p in ps if p), "\n".join(p.text_deva for p in ps if p), None, None, None], fill_from=5)
        ws.row_dimensions[r].height = 110
        r += 1
    _dropdown(ws, "E", r - 2, ["Yes", "No", "Not sure"])


def rules_sheet(wb):
    rules = yaml.safe_load((ROOT / "data" / "rules" / "safety_rules.yaml").read_text(encoding="utf-8"))["rules"]
    ws = wb.create_sheet("3 Safety rules")
    _head(ws, [("Rule", 18), ("When it fires", 34), ("What PRAMAAN does / says", 70), ("Basis", 16),
               ("Clinically appropriate?", 15), ("Suggested change", 40)])
    for r, x in enumerate(rules, start=2):
        o = x["outcome"]
        said = o.get("message_en", "") + (f"\nAsks: {o['question_en']}" if o.get("question_en") else "")
        _row(ws, r, [x["id"], f"{x['title']}\n{json.dumps(x['condition'])}", f"[{o['action']}] {said}",
                     (x.get("basis") or {}).get("type", ""), None, None], fill_from=5)
        ws.row_dimensions[r].height = 90
    _dropdown(ws, "E", len(rules), ["Yes", "Needs change", "No"])


def input_sheet(wb, name, cols, example, rows=25):
    ws = wb.create_sheet(name)
    _head(ws, cols)
    _row(ws, 2, example, example=True)
    for r in range(3, 3 + rows):
        _row(ws, r, [None] * len(cols), fill_from=1)


def build() -> None:
    files = sorted(OUT.glob("answers_*.json"))
    if not files:
        raise SystemExit("no answers file; run: python scripts/expert_validation.py generate")
    data = json.loads(files[-1].read_text(encoding="utf-8"))
    DELIVER.mkdir(parents=True, exist_ok=True)
    common = [
        "PRAMAAN shows original verses from the Caraka (Charaka) Saṃhitā and Aṣṭāṅga Hṛdaya and lets AyurParam explain them.",
        "Each answer below is exactly what the app showed for that question (live AyurParam, "
        f"{data['meta']['created_at'][:10]}, corpus {data['meta']['corpus_version']}). The verse id after each sentence is the verse it cites.",
        "",
        "How to rate each answer (tab '1 Answers'):",
        "• Q1 Relevance: are the verses shown the right ones for this question? (Yes / Partly / No)",
        "• Q2 Faithfulness: does each explanation sentence say what its cited verse says? (Yes / Partly / No / No explanation)",
        "• Q3 Clinical correctness: is the explanation correct from an Ayurveda standpoint? (Yes / Partly / No / No explanation)",
        "• Q4 Overall: would you accept this answer for a BAMS student? (Good / Acceptable / Poor)",
        "• Please rate on your own, without discussing with the other reviewer. Comments are optional but very helpful.",
        "",
    ]
    wb = Workbook()
    _readme(wb, "PRAMAAN review — clinical lead", common + [
        "Other tabs:",
        "• 2 Definition verses: is the verse we show first for each 'what is X' question the right one?",
        "• 3 Safety rules: are the 13 rules clinically appropriate? Suggest wording changes.",
        "• 4 Anupana & Ritu: which Anupāna and seasonal (Ṛtu) restrictions should we add, with verse references?",
        "• 5 Benchmark questions: real questions a BAMS student would ask, each with the verse you'd expect.",
        "• 6 Add-on ideas: anything else that would make PRAMAAN more useful or more convincing.",
        "",
        "Priority if time is short: tabs 1, 2 and 3. Please return by 30 Nov 2026.",
    ])
    answers_sheet(wb, data)
    definitions_sheet(wb)
    rules_sheet(wb)
    input_sheet(wb, "4 Anupana & Ritu", [("Situation / season", 24), ("Herb, food or activity", 24), ("Restriction or advice", 40),
                                        ("Classical reference (verse)", 24), ("Notes", 30)],
                ["Example: Grīṣma (summer)", "Divāsvapna (day sleep)", "Day sleep is suitable in summer; avoid it in other seasons",
                 "Ca. Sū. 21.43–44", "Example row from our corpus; replace with your own"])
    input_sheet(wb, "5 Benchmark questions", [("Question (as a student would ask)", 40), ("Language", 10),
                                             ("Expected verse(s)", 28), ("Notes", 30)],
                ["Example: What is srotas?", "EN", "Ca. Sū. 30.12; Ca. Vi. 5.3", "Example row; replace with your own"], rows=50)
    input_sheet(wb, "6 Add-on ideas", [("Idea", 60), ("Why it helps (students / Vaidyas / jury)", 50)],
                ["Example: show the commentary (Cakrapāṇi) next to the verse", "Students read verses with commentary"], rows=15)
    f1 = DELIVER / "PRAMAAN_Review_Clinical_Lead.xlsx"
    wb.save(f1)

    wb2 = Workbook()
    _readme(wb2, "PRAMAAN answer review — external Ayurveda expert", common + [
        "Only one tab to fill: '1 Answers' (50 answers). It takes about 2–3 hours.",
        "Thank you for helping us validate PRAMAAN for the AyushTech Innovate challenge (Techfest, IIT Bombay).",
    ])
    answers_sheet(wb2, data)
    f2 = DELIVER / "PRAMAAN_Review_External_Expert.xlsx"
    wb2.save(f2)
    print(f1)
    print(f2)


if __name__ == "__main__":
    build()
