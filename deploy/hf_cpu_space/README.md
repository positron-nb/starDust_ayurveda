---
title: PRAMAAN Ayurveda Evidence Workbench
emoji: 📜
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
startup_duration_timeout: 1h
license: apache-2.0
short_description: Verse-grounded Ayurveda answers with AyurParam (CPU)
---

# PRAMAAN — live demo (free CPU hardware)

PRAMAAN shows original verses from the Caraka (Charaka) Saṃhitā and Aṣṭāṅga Hṛdaya and lets
**AyurParam** (`bharatgenai/AyurParam` @ `27c69ee`) explain them, with server-bound citations,
an evidence ledger and a model-independent safety layer.

- Code (Apache-2.0): https://github.com/positron-nb/starDust_ayurveda
- Corpus: third-party SARIT data under its original CC BY-SA 3.0 licence.

**This Space runs on free CPU hardware.** AyurParam runs on CPU in bf16, so one explanation takes
minutes rather than seconds; verses, citations and safety checks appear immediately. On a GPU the
same code explains up to three verses per answer (see the repository).

Not a diagnosis, prescription or safety-clearance tool. Educational use only.
