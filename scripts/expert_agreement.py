"""Score the two filled reviewer workbooks and compute inter-rater agreement.

    python scripts/expert_agreement.py <clinical_lead.xlsx> <external_expert.xlsx>

Reads tab '1 Answers' (columns F–I = Q1–Q4) from both files, matches rows by answer ID, and writes
eval/results/expert_agreement_<date>.json in the same {value, numerator, denominator} format as the other
result files, so the report build can cite it. Rows either rater left blank are excluded from that question.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = {"q1_relevant": ("F", "Yes"), "q2_faithful": ("G", "Yes"), "q3_clinically_correct": ("H", "Yes"),
             "q4_overall": ("I", "Good")}  # column, the 'best' category


def read(path: str) -> dict[str, dict[str, str]]:
    ws = load_workbook(path, data_only=True)["1 Answers"]
    out = {}
    for r in range(2, ws.max_row + 1):
        qid = ws[f"A{r}"].value
        if qid:
            out[str(qid).strip()] = {q: (str(ws[f"{col}{r}"].value).strip() if ws[f"{col}{r}"].value else "")
                                     for q, (col, _) in QUESTIONS.items()}
    return out


def kappa(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)


def main(path_a: str, path_b: str) -> Path:
    A, B = read(path_a), read(path_b)
    ids = sorted(set(A) & set(B))
    metrics, detail = {}, {}
    for q, (_, best) in QUESTIONS.items():
        pairs = [(A[i][q], B[i][q]) for i in ids if A[i][q] and B[i][q]]
        a, b = [x for x, _ in pairs], [y for _, y in pairs]
        n = len(pairs)
        metrics[f"{q}_agreement"] = {"value": round(sum(x == y for x, y in pairs) / n, 4) if n else None,
                                     "numerator": sum(x == y for x, y in pairs), "denominator": n}
        metrics[f"{q}_kappa"] = {"value": kappa(a, b), "note": "Cohen's kappa over the categories used"}
        for who, vals in (("lead", [A[i][q] for i in ids if A[i][q]]), ("external", [B[i][q] for i in ids if B[i][q]])):
            metrics[f"{q}_{who}_best"] = {"value": round(vals.count(best) / len(vals), 4) if vals else None,
                                          "numerator": vals.count(best), "denominator": len(vals),
                                          "note": f"share rated '{best}'"}
            detail[f"{q}_{who}"] = dict(Counter(vals))
    out = ROOT / "eval" / "results" / f"expert_agreement_{dt.datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps({"created_at": dt.datetime.now(dt.timezone.utc).isoformat(), "n_answers": len(ids),
                               "files": [Path(path_a).name, Path(path_b).name], "metrics": metrics,
                               "category_counts": detail}, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in metrics.items():
        print(f"{k:34} {v.get('value')}  {v.get('numerator', '')}/{v.get('denominator', '')}")
    print(out)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
