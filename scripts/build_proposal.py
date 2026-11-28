"""Build the designed Phase 1 proposal (HTML + PDF) from docs/PHASE1_PROPOSAL.md.

    python scripts/build_proposal.py            # HTML + PDF (uses Microsoft Edge headless)
    python scripts/build_proposal.py --no-pdf   # HTML only

Numbers are filled from real artefacts, never typed by hand:
  - the newest eval/results/eval_full_pramaan_all_*.json  ({{CIT}}, {{HIT5}}, ...)
  - data/build/corpus.sqlite                                ({{INDEXED}})
  - pytest --collect-only                                   ({{TESTS}})
Figures are injected at <!-- FIGURE:cards|arch|screenshot --> markers (invisible on GitHub).
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "PHASE1_PROPOSAL.md"
OUT_DIR = ROOT / "docs" / "submission"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


# --------------------------------------------------------------------------- numbers
def frac(m: dict) -> str:
    return f"{m['numerator']}/{m['denominator']}"


def load_numbers() -> dict[str, str]:
    runs = sorted((ROOT / "eval" / "results").glob("eval_full_pramaan_all_*.json"))
    if not runs:
        sys.exit("no full evaluation run found")
    run = runs[-1]
    m = json.loads(run.read_text(encoding="utf-8"))["metrics"]
    stamp = re.search(r"(\d{8})_\d{6}", run.name).group(1)
    w = m["generated_sentences_withheld_rate"]
    con = sqlite3.connect(ROOT / "data" / "build" / "corpus.sqlite")
    indexed = con.execute("select count(*) from passages where indexed=1 and revoked=0").fetchone()[0]
    tests = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT / "backend",
                           capture_output=True, text=True).stdout
    n_tests = re.search(r"(\d+) tests? collected", tests)
    cit = m["resolved_citation_rate_displayed"]
    return {
        "RUN_FILE": run.name,
        "EVAL_DATE": dt.datetime.strptime(stamp, "%Y%m%d").strftime("%d %b %Y").lstrip("0"),
        "WITHHELD": f"{w['numerator']} of {w['denominator']}",
        "WITHHELD_PCT": f"{round(100 * w['value'])}%",
        "CIT": f"{frac(cit)} ({round(100 * cit['value'])}%)",
        "CIT_PCT": f"{round(100 * cit['value'])}%",
        "FAB": frac(m["fabricated_citation_accepted"]),
        "FAB_N": str(m["fabricated_citation_accepted"]["numerator"]),
        "ESC": frac(m["escalation_recall"]),
        "FALSE": frac(m["false_escalation"]),
        "FALSE_N": str(m["false_escalation"]["numerator"]),
        "FALSE_D": str(m["false_escalation"]["denominator"]),
        "DOSE": frac(m["dose_shown_auto_proxy"]),
        "POS": frac(m["positive_use_shown_auto_proxy"]),
        "SAFE": frac(m["safety_rule_expectation_met"]),
        "ABST": frac(m["correct_abstention"]),
        "HIT5": f"{frac(m['hit_at_5'])} ({m['hit_at_5']['value']:.2f})",
        "HIT5_V": f"{m['hit_at_5']['value']:.2f}",
        "FIRST": f"{m['time_to_first_evidence_p50_ms']['value'] / 1000:.1f} s",
        "P50": f"{m['latency_p50_ms']['value'] / 1000:.1f} s",
        "INDEXED": f"{indexed:,}",
        "TESTS": n_tests.group(1) if n_tests else "?",
    }


# generic placeholders: {{source.metric|format}}, e.g. {{full.hit_at_5|frac}}, {{raw.latency_p50_ms|s}}, {{ret.@date}}
SOURCES = {"full": "eval_full_pramaan_all_*.json", "fulltest": "eval_full_pramaan_test_*.json",
           "ret": "eval_retrieval_ablation_all_*.json", "raw": "eval_raw_ayurparam_test_*.json",
           "rag": "eval_dense_rag_test_*.json"}


def fill_generic(text: str) -> tuple[str, list[str]]:
    cache: dict[str, tuple[dict, str]] = {}
    used: list[str] = []

    def src(name):
        if name not in cache:
            runs = sorted((ROOT / "eval" / "results").glob(SOURCES[name]))
            if not runs:
                sys.exit(f"no result file for {name}")
            stamp = re.search(r"(\d{8})_\d{6}", runs[-1].name).group(1)
            cache[name] = (json.loads(runs[-1].read_text(encoding="utf-8")),
                           dt.datetime.strptime(stamp, "%Y%m%d").strftime("%d %b %Y").lstrip("0"))
            used.append(runs[-1].name)
        return cache[name]

    def one(mt):
        name, key, fmt = mt.group(1), mt.group(2), mt.group(3) or "frac"
        if name not in SOURCES:
            return mt.group(0)
        d, date = src(name)
        if key == "@date":
            return date
        m = d["metrics"][key]
        v = m.get("value")
        return {"frac": lambda: f"{m['numerator']}/{m['denominator']}", "v2": lambda: f"{v:.2f}",
                "pct": lambda: f"{round(100 * v)}%", "s": lambda: f"{v / 1000:.1f} s",
                "n": lambda: str(m["numerator"]), "d": lambda: str(m["denominator"])}[fmt]()

    return re.sub(r"\{\{(\w+)\.([@\w]+)(?:\|(\w+))?\}\}", one, text), used


# --------------------------------------------------------------------------- markdown
def inline(t: str) -> str:
    codes: list[str] = []

    def keep(mt):
        codes.append(f"<code>{html.escape(mt.group(1), quote=False)}</code>")
        return f"\x00{len(codes) - 1}\x00"

    t = re.sub(r"`([^`]+)`", keep, t)
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<a href='\2'>\1</a>", t)
    return re.sub(r"\x00(\d+)\x00", lambda mt: codes[int(mt.group(1))], t)


def md_to_html(src: str, figures: dict[str, str]) -> str:
    lines, out, i = src.split("\n"), [], 0
    item = re.compile(r"(\d+\.|[-*]) ")
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        fig = re.match(r"<!-- FIGURE:(\w+) -->", ln.strip())
        if fig:
            out.append(figures[fig.group(1)])
            i += 1
            continue
        h = re.match(r"(#{1,4}) (.*)", ln)
        if h:
            n = len(h.group(1))
            out.append(f"<h{n}>{inline(h.group(2))}</h{n}>")
            i += 1
            continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            t = "<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in rows[0]) + "</tr></thead><tbody>"
            t += "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows[2:])
            out.append(t + "</tbody></table>")
            continue
        if item.match(ln):
            tag = "ol" if ln[0].isdigit() else "ul"
            items: list[str] = []
            while i < len(lines) and (item.match(lines[i]) or (lines[i].startswith("   ") and lines[i].strip())):
                if item.match(lines[i]):
                    items.append(item.sub("", lines[i], count=1))
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"(#{1,4} |\||<!--)", lines[i]) and not item.match(lines[i]):
            buf.append(lines[i])
            i += 1
        out.append("<p>" + " ".join(inline(b) for b in buf) + "</p>")
    return "\n".join(out)


# --------------------------------------------------------------------------- figures
def cards(n: dict[str, str]) -> str:
    data = [
        (n["CIT_PCT"], "of displayed claims cite a real, unchanged verse", n["CIT"].split(" ")[0]),
        (n["FAB_N"], "fabricated citations accepted", f"{n['FAB']} attempts"),
        (n["ESC"], "emergencies escalated, model never called", f"{n['FALSE_N']} false alarms in {n['FALSE_D']} non-emergency cases"),
        (n["INDEXED"], "verse-level passages from Caraka and Aṣṭāṅga Hṛdaya", "20 core topics · 24 curated concepts"),
        (n["HIT5_V"], "retrieval Hit@5 on answerable questions", n["HIT5"].split(" ")[0] + " questions"),
        (n["P50"], "median full answer on an 8 GB laptop GPU", f"first evidence in {n['FIRST']}"),
    ]
    cells = "".join(f"<div class='card'><div class='big'>{html.escape(b)}</div><div class='lbl'>{html.escape(l)}</div>"
                    f"<div class='sub'>{html.escape(s)}</div></div>" for b, l, s in data)
    return (f"<div class='cards'>{cells}</div><p class='note'>Measured on our 120-case evaluation suite with live AyurParam, "
            f"{n['EVAL_DATE']} (details in §9).</p>")


STAGES = [
    ("Ask", "#5b6b73", "#f1f4f5", ["English / Hindi", "+ optional", "synthetic case"]),
    ("Safety gate", "#b8720b", "#fdf3e1", ["13 YAML rules", "tri-state facts", "emergency stop"]),
    ("Retrieve", "#2f7d4f", "#e8f4ec", ["BM25 + dense", "RRF fusion", "definition first"]),
    ("Explain", "#2f5fa8", "#e8eff9", ["AyurParam 2.9B", "verse by verse", "English / Hindi"]),
    ("Verify", "#7a4fa3", "#f2ecf8", ["citation check", "support check", "withhold + why"]),
    ("Present", "#1f7a7a", "#e5f3f2", ["verse + [E] tags", "review packet", "source fallback"]),
]


def arch(n: dict[str, str]) -> str:
    x0, w, gap, y0, h = 10, 105, 14, 14, 106
    parts = ["<defs><marker id='ar' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='6' markerHeight='6' "
             "orient='auto-start-reverse'><path d='M0 0L10 5L0 10z' fill='#7d8a80'/></marker></defs>"]
    for k, (title, stroke, fill, lines) in enumerate(STAGES):
        x = x0 + k * (w + gap)
        cx = x + w / 2
        parts.append(f"<rect x='{x}' y='{y0}' width='{w}' height='{h}' rx='9' fill='{fill}' stroke='{stroke}' stroke-width='1.4'/>")
        parts.append(f"<circle cx='{cx}' cy='{y0}' r='11' fill='{stroke}'/>"
                     f"<text x='{cx}' y='{y0 + 4}' text-anchor='middle' font-size='11' font-weight='700' fill='#fff'>{k + 1}</text>")
        parts.append(f"<text x='{cx}' y='{y0 + 34}' text-anchor='middle' font-size='12.5' font-weight='700' fill='#1f2a1f'>{title}</text>")
        for j, line in enumerate(lines):
            parts.append(f"<text x='{cx}' y='{y0 + 56 + 16 * j}' text-anchor='middle' font-size='10.5' fill='#3d4a40'>{html.escape(line)}</text>")
        if k < len(STAGES) - 1:
            parts.append(f"<line x1='{x + w + 1}' y1='{y0 + h / 2}' x2='{x + w + gap - 2}' y2='{y0 + h / 2}' stroke='#7d8a80' "
                         f"stroke-width='1.4' marker-end='url(#ar)'/>")
    by, bh = y0 + h + 40, 64
    left_r = x0 + 2 * (w + gap) + w
    right_l = x0 + 3 * (w + gap)
    right_r = x0 + 5 * (w + gap) + w
    bands = [
        (x0, left_r, "#2f7d4f", "#f4faf6", "Knowledge base (expert-editable YAML)",
         ["Caraka + Aṣṭāṅga Hṛdaya · SARIT TEI, sha256-pinned",
          f"{n['INDEXED']} passages · 20 topics · EN/HI/SA terms · 13 rules"]),
        (right_l, right_r, "#2f5fa8", "#f3f6fc", "AyurParam 2.9B · the only LLM",
         ["bharatgenai/AyurParam @ 27c69ee · bf16",
          "local 8 GB laptop GPU · term expansion + explanation"]),
    ]
    for bx, br, stroke, fill, title, lines in bands:
        parts.append(f"<rect x='{bx}' y='{by}' width='{br - bx}' height='{bh}' rx='9' fill='{fill}' stroke='{stroke}' "
                     f"stroke-width='1.2' stroke-dasharray='5 3'/>")
        parts.append(f"<text x='{bx + 12}' y='{by + 20}' font-size='12' font-weight='700' fill='{stroke}'>{html.escape(title)}</text>")
        for j, line in enumerate(lines):
            parts.append(f"<text x='{bx + 12}' y='{by + 38 + 15 * j}' font-size='10.5' fill='#3d4a40'>{html.escape(line)}</text>")
    for k, label in ((1, "rules"), (2, "verses, terms"), (3, "model")):
        cx = x0 + k * (w + gap) + w / 2
        parts.append(f"<line x1='{cx}' y1='{by - 1}' x2='{cx}' y2='{y0 + h + 3}' stroke='#7d8a80' stroke-width='1.3' marker-end='url(#ar)'/>")
        parts.append(f"<text x='{cx + 6}' y='{y0 + h + 24}' font-size='9.5' fill='#6b776e'>{label}</text>")
    height = by + bh + 8
    svg = (f"<svg viewBox='0 0 720 {height}' xmlns='http://www.w3.org/2000/svg' role='img' "
           f"aria-label='PRAMAAN pipeline' style='width:100%;height:auto'>{''.join(parts)}</svg>")
    return (f"<figure>{svg}<figcaption>Figure 1 · Every displayed sentence passes the safety gate, cites a retrieved verse "
            f"and survives verification before the user sees it.</figcaption></figure>")


def screenshot() -> str:
    imgs = [p for p in (OUT_DIR / "app_screenshot.png", OUT_DIR / "app_screenshot.jpg") if p.exists()]
    if not imgs:
        return ""
    return (f"<figure class='shot'><img src='{imgs[0].name}' alt='PRAMAAN answer screen'/>"
            "<figcaption>Figure 2 · Live PRAMAAN answer to “What is tridosha?”: AyurParam's explanation (left) "
            "with an [E] tag on each sentence, and the original verses (right) with the defining verse, "
            "Aṣṭāṅga Hṛdaya Sūtrasthāna 1.6, first.</figcaption></figure>")


CSS = """
@page{size:A4;margin:13mm 14mm 14mm}
*{box-sizing:border-box}
body{font-family:'Segoe UI','Nirmala UI','Noto Sans',sans-serif;font-size:9.8pt;line-height:1.45;color:#1f2a1f;margin:0}
h1{font-size:19pt;line-height:1.2;color:#173d24;margin:0 0 4px}
h1+p{color:#5a4a1f;font-size:9.5pt;margin:0 0 8px;padding-bottom:6px;border-bottom:3px solid #e08a1e}
h2{font-size:12.5pt;color:#173d24;margin:16px 0 6px;padding:3px 0 3px 9px;border-left:4px solid #2f7d4f;
   background:linear-gradient(90deg,#eef6f0,rgba(255,255,255,0));break-after:avoid}
p{margin:5px 0}
ul,ol{margin:5px 0;padding-left:20px}li{margin:2px 0}
a{color:#1f5f9a;text-decoration:none}
code{font-family:Consolas,monospace;font-size:8.6pt;background:#f2f0ea;padding:0 3px;border-radius:3px}
table{border-collapse:collapse;width:100%;font-size:9pt;margin:6px 0;break-inside:avoid}
th{background:#173d24;color:#fff;text-align:left;padding:4px 7px;font-weight:600}
td{border-bottom:1px solid #e3ddd0;padding:4px 7px;vertical-align:top}
tbody tr:nth-child(even) td{background:#faf8f3}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:8px 0 2px;break-inside:avoid}
.card{border:1px solid #d9e6dc;border-top:4px solid #2f7d4f;border-radius:8px;padding:8px 10px;background:#fbfdfb}
.card:nth-child(2){border-top-color:#7a4fa3}.card:nth-child(3){border-top-color:#b8720b}
.card:nth-child(4){border-top-color:#1f7a7a}.card:nth-child(5){border-top-color:#2f5fa8}.card:nth-child(6){border-top-color:#5b6b73}
.big{font-size:20pt;font-weight:700;color:#173d24;line-height:1.1}
.lbl{font-size:8.8pt;color:#2e3a31;margin-top:2px}.sub{font-size:8pt;color:#6b776e;margin-top:2px}
.note{font-size:8pt;color:#6b776e;margin-top:2px}
figure{margin:8px 0;break-inside:avoid}
figcaption{font-size:8.4pt;color:#5f6b62;margin-top:4px;text-align:center}
.shot img{display:block;width:86%;margin:0 auto;border:1px solid #d6d0c2;border-radius:6px}
h1+p+table{margin-top:0}
h1+p+table td:nth-child(-n+3),h1+p+table th:nth-child(-n+3){white-space:nowrap}
p:has(+table){break-after:avoid}
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--src", default=str(SRC), help="markdown source (default: the Phase 1 proposal)")
    ap.add_argument("--name", default="PHASE1_PROPOSAL", help="output basename in docs/submission/")
    a = ap.parse_args()
    n = load_numbers()
    src = Path(a.src).read_text(encoding="utf-8")
    src, used = fill_generic(src)
    for k, v in n.items():
        src = src.replace("{{" + k + "}}", v)
    left = re.findall(r"\{\{\w+\}\}", src)
    if left:
        sys.exit(f"unfilled placeholders: {left}")
    body = md_to_html(src, {"cards": cards(n), "arch": arch(n), "screenshot": screenshot()})
    page = (f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(re.search(r'^# (.+)$', src, re.M).group(1))}</title>"
            f"<style>{CSS}</style></head><body>{body}</body></html>")
    out_html = OUT_DIR / f"{a.name}.html"
    out_html.write_text(page, encoding="utf-8")
    print("html:", out_html, "| numbers from", n["RUN_FILE"], *used)
    if a.no_pdf:
        return
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        pdf_tmp = Path(tmp) / "p.pdf"
        subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--user-data-dir={Path(tmp) / 'prof'}", f"--print-to-pdf={pdf_tmp}", out_html.as_uri()],
                       check=True, capture_output=True, timeout=120)
        # the Edge launcher can return before its renderer has finished writing the file
        last = -1
        for _ in range(120):
            size = pdf_tmp.stat().st_size if pdf_tmp.exists() else -1
            if size > 0 and size == last:
                break
            last = size
            time.sleep(0.5)
        else:
            sys.exit("Edge did not produce the PDF")
        (OUT_DIR / f"{a.name}.pdf").write_bytes(pdf_tmp.read_bytes())
    print("pdf:", OUT_DIR / f"{a.name}.pdf")


if __name__ == "__main__":
    main()
