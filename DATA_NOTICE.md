# Data notice

The PRAMAAN **application code** is licensed under Apache-2.0 (see `LICENSE`).
**Data is licensed separately.** Nothing in this repository relabels source text or derived
material as Apache-2.0 or MIT.

| Path | What it is | Licence / status |
|---|---|---|
| `data/sources/raw/carakasamhita.xml` | SARIT TEI edition of the Carakasaṃhitā (pinned commit `1eac9ee`, sha256 `9f8c1730…`) | CC BY-SA 3.0 Unported, as declared in the file's TEI header. The header also states `availability status="restricted"` and "Copyright 2014-2018 SARIT". Attribution: SARIT (Dominik Wujastyk, TEI); Kyoto e-text input by T. Yamashita, Y. Muroya, Y. Yamanaka, Madhu K. P.; based on the 1941 edition of Yādavaśarman Trivikramātmaja Ācārya. |
| `data/sources/raw/astangahrdayasamhita.xml` | SARIT TEI edition of the Aṣṭāṅgahṛdayasaṃhitā (pinned commit `1eac9ee`, sha256 `21e5bff8…`) | CC BY-SA 3.0 Unported, as declared in the TEI header. Attribution: base e-text R. P. Das and R. E. Emmerick; TEI conversion Richard Mahoney / Patrick McAllister; SARIT maintenance Dominik Wujastyk. |
| `data/build/corpus.sqlite` (generated) | Segmented passages, derived Devanagari transliteration, concept tags | **Derived from the SARIT files → treat as CC BY-SA 3.0 (ShareAlike).** Generated locally; not committed. |
| `data/curated/glosses_draft.yaml` | Short English draft gists for 15 verses, written by an AI build assistant | Draft, unreviewed, **not a published translation**. Because they adapt CC BY-SA text, distribute them under CC BY-SA 3.0 as well. |
| `data/sources/external/nccih_ashwagandha.json` | Short paraphrases (and quotes < 15 words) from NCCIH "Ashwagandha: Usefulness and Safety" (accessed 2026-11-07; page last updated March 2023) | The page states it is not copyrighted and is in the public domain. Attribution kept. Not a copy of the page. |
| `data/terminology/terminology.yaml`, `data/rules/safety_rules.yaml`, `data/curated/modules.yaml` | Team-authored curated tables (drafted by the build assistant) | Apache-2.0 with the code. **Clinical/domain review pending.** |
| `eval/cases.jsonl` | 120 synthetic candidate evaluation cases | Apache-2.0. Synthetic; labels are unreviewed candidates. |
| `models/AyurParam/` (not committed) | bharatgenai/AyurParam weights @ `27c69ee` | Hugging Face metadata says Apache-2.0; the model card body shows a CC-BY-4.0 badge. **Conflict recorded, not resolved** — check with BharatGen before redistribution. Weights are downloaded by users, not redistributed here. |

## Open rights questions (not legal advice)
1. SARIT headers combine `status="restricted"` with a CC BY-SA 3.0 grant. We follow the explicit
   CC BY-SA grant and keep attribution; the team should confirm with SARIT if commercial hosting is planned.
2. ShareAlike: any redistributed derived corpus (SQLite, exports containing passages, glosses) must be
   CC BY-SA 3.0 (or compatible). Review packets exported by the app contain passage text.
3. NIIMH/CCRAS e-Samhitā was **not** used; reuse permission has not been requested.
4. AyurParam licence conflict (see table).
5. Commercial use of the hosted service must respect (1)–(4).
