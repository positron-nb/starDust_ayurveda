# Usability study protocol (pilot, 5–8 Ayurveda students)

**Not clinical validation. Not yet conducted.** No participant data exists until real sessions happen.

## Purpose
Find out whether students can (a) find the relevant classical passage, (b) read the evidence ledger
correctly, and (c) avoid reading PRAMAAN as a diagnostic or prescribing tool.

## Participants and consent
- 5–8 voluntary BAMS / MD students; no compensation that could pressure participation.
- Verbal + written consent at the start (template below). Participants may stop at any time.
- Anonymous IDs (P01…P08). Record no names, phone numbers, roll numbers or health information.
- Only synthetic educational inputs; participants must not type their own or anyone's health details.
- Check whether your institution requires ethics-committee / IEC approval for a student usability pilot;
  if unsure, ask before running it.

Consent text: "This is a 20-minute test of a study software prototype, not of you. It does not give
medical advice. Your answers are anonymous and used only to improve the prototype and in the
competition report. You can stop at any time. Do you agree to take part?"

## Setup
Laptop with live AyurParam (banner LIVE) or labelled fixture replay; screen recording only with consent;
one moderator (reads tasks, does not help unless asked) and one note-taker.

## Tasks (read aloud; start timer when the moderator finishes reading)
| # | Task | Success criterion |
|---|---|---|
| T1 | "Find what Aṣṭāṅgahṛdaya says about the definition of āma." | Opens a passage with AH Sū 13.25 visible |
| T2 | "Show me the exact original location of that verse." | Points to locator + xml:id in Source Explorer |
| T3 | "Run example A. For one shown sentence, tell me which verse supports it and whether a human has checked it." | Names the [E#] verse and says review is pending |
| T4 | "Open the withheld sentences. Pick one and explain why it was not shown." | Gives the stated reason in own words |
| T5 | "Ask: 'What does Ayurveda say about smartphone addiction?' What did the system tell you?" | Says the corpus has insufficient evidence (not 'no effect') |
| T6 | "Run example B. Is ashwagandha safe for this person? What information is missing?" | Says it is not assessed / withheld; names pregnancy status as missing |

Record per task: completion (y/n/partial), time, wrong paths, help requested, whether the evidence status
was understood, and any statement treating the tool as diagnosis/prescription
(`eval/usability/task_results_template.csv`).

## Questionnaire (after tasks)
UMUX-Lite (two items, 7-point agreement): "This system's capabilities meet my requirements" and
"This system is easy to use", plus "I trust the way evidence is displayed" (1–7), "Would you use it for
study?" and two open questions (`eval/usability/questionnaire_template.csv`).

## Analysis (report exactly, no inflation)
Per task: completion n/N, median time, common errors. UMUX-Lite: report item means and n; do not
convert to SUS-equivalent scores with n < 10 without saying so. Count every misinterpretation as
diagnostic/prescribing. Quote open feedback verbatim (anonymised). Compare with ordinary search only if
the same tasks were also timed on a plain text/PDF search; otherwise make no comparative claim.
