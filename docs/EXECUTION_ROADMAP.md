# Execution roadmap, 9–30 November 2026

Statuses: NOT STARTED · IN PROGRESS · BLOCKED · COMPLETED · NOT APPLICABLE. "Owner" marks work that
depends on people other than the engineers. Nothing is marked COMPLETED without the evidence listed.

| Date | Priority | Status (as of 9 Nov evening) | Evidence / blocker | Owner |
|---|---|---|---|---|
| 9 Nov | Repository and baseline freeze | COMPLETED | commits `31d3d07`…`04dbf44`; REPOSITORY_AUDIT.md; 43 tests pass; regression run `eval_full_pramaan_all_20261109_160413` | engineer |
| 10 Nov | Human audit training and protocol | IN PROGRESS | CLAIM_AUDIT_REVIEW_GUIDE.md + sheet `eval/audit/claim_audit_20261109_154354.*` ready; teammate briefing not done | **BAMS teammate** |
| 11 Nov | Claim audit batch 1 (records 1–27) | NOT STARTED | — | **BAMS teammate** |
| 12 Nov | Claim audit batch 2 (28–54) | NOT STARTED | — | **BAMS teammate** |
| 13 Nov | Claim audit batch 3 (55–81) | NOT STARTED | — | **BAMS teammate** |
| 14 Nov | Claim audit batch 4 (82–107) | NOT STARTED | — | **BAMS teammate** |
| 15 Nov | Complete claim audit; **registration closes** | NOT STARTED | Team Leader registers; enrolment proof uploaded | **Team Leader, BAMS teammate** |
| 16 Nov | Resolve labels; compute human support metrics | NOT STARTED | `import_claim_audit.py` + `claim_audit_summary.py` ready | engineer + teammate |
| 17 Nov | Create fresh retrieval benchmark (40–50 Qs, ≥20 locked) | NOT STARTED | template + `benchmark_lock.py` ready | **BAMS teammate** |
| 18 Nov | Retrieval failure analysis | COMPLETED (on inspected data) | RETRIEVAL_FAILURE_ANALYSIS.md; repeat on fresh dev rows | engineer |
| 19 Nov | Retrieval experiments | COMPLETED (round 1) | RETRIEVAL_EXPERIMENTS.md — no knob beats default; next: reviewed terminology/glosses, sama/sāma alias fix, fasting alias | engineer + teammate |
| 20 Nov | New held-out retrieval evaluation | NOT STARTED | blocked on 17 Nov benchmark | engineer |
| 21 Nov | Proposal final review | IN PROGRESS | PHASE1_PROPOSAL.md updated 9 Nov; team names/IDs missing | team |
| 22 Nov | **Phase 1 submission** | NOT STARTED | Team Leader submits via portal | **Team Leader** |
| 23 Nov | PyTorch 2.8 compatibility | COMPLETED (local) | ZEROGPU_COMPATIBILITY_REPORT.md: 8/8 identical outputs | engineer |
| 24 Nov | ZeroGPU Space | IN PROGRESS | code on `experiment/zerogpu-pt28`, verified locally; needs eligible HF account | **account owner** |
| 25 Nov | ZeroGPU inference integration | IN PROGRESS | `ZeroGPUAdapter` + local fallback verified against local Space; real run pending | engineer |
| 26 Nov | Cloudflare fallback | IN PROGRESS | auth/rate-limit/read-only implemented + tested; tunnel not run (cloudflared not installed) | engineer |
| 27 Nov | Docker validation | BLOCKED | Docker not installed on build machine; procedure in DOCKER_VALIDATION.md | engineer (machine with Docker) |
| 28 Nov | 5–8 student usability study | NOT STARTED | protocol + templates ready; check institutional ethics requirement | **teammate + participants** |
| 29 Nov | Bug fixes and regression | NOT STARTED | — | engineer |
| 30 Nov | Release freeze; final demo rehearsal | NOT STARTED | FINAL_DEMO_SCRIPT.md; record backup video | team |
Phase 2 submission (repo + hosted link + report): **1 Dec**. Finale: 15–18 Dec.
