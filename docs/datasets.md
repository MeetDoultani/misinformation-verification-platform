# Dataset Documentation

This document describes every dataset used in Phase 1, why it was chosen,
its expected size and schema, licensing considerations, and how it feeds
future project phases.

---

## 1. Fake vs Real News — ISOT Fake and Real News Dataset

| | |
|---|---|
| **Source** | Kaggle: `clmentbisaillon/fake-and-real-news-dataset` (originally from the ISOT Research Lab, University of Victoria) |
| **Access** | Gated (Kaggle account + API token) |
| **Expected size** | ~44,900 articles (~23,500 fake / ~21,400 real) |
| **Raw schema** | `title, text, subject, date` + derived `label` (`Fake`/`True`) |
| **License** | Free for research/educational use per ISOT's terms; redistribution restrictions apply — see the Kaggle page before any commercial use |

**Why chosen:** It is one of the most widely benchmarked fake-news corpora in
academic literature, giving comparability with published baselines. Real
articles are sourced from Reuters (wire-service quality control), fake
articles from PolitiFact-flagged and known unreliable sites, giving a
reasonably clean binary label with minimal manual re-annotation needed.

**Known caveat, handled in cleaning:** Real articles are prefixed with a
`CITY (Reuters) -` dateline that fake articles lack. Left unaddressed, a
classifier could learn to detect the dateline string instead of genuine
stylistic/factual signal. `text_cleaning.strip_source_boilerplate()`
strips this prefix.

**Downstream use:** Primary training/benchmark corpus for the future
**Claim Verification** and **Fusion Model** phases; a standard
binary-classification baseline against which more advanced neuro-symbolic
approaches will be measured.

---

## 2. Claim Verification — FEVER (Fact Extraction and VERification)

| | |
|---|---|
| **Source** | https://fever.ai (Thorne et al., 2018) |
| **Access** | Public, no authentication required |
| **Expected size** | ~185,000 claims (train), ~20,000 (paper_dev), ~20,000 (paper_test), paired with a 5.4M-document Wikipedia evidence corpus |
| **Raw schema** | `id, claim, label (SUPPORTS/REFUTES/NOT ENOUGH INFO), evidence (list of Wikipedia sentence references)` |
| **License** | CC BY-SA 3.0 (Wikipedia-derived) + FEVER's own terms — free for research use, attribution required |

**Why chosen:** FEVER is the standard large-scale benchmark for
claim-verification-against-evidence, exactly the task shape needed for a
neuro-symbolic verification pipeline: a claim, retrieved evidence, and a
three-way veracity label. Its scale (~185K claims) supports both
supervised training and evaluation.

**Downstream use:** Directly powers the **Claim Verification** module
(claim, label) and supplies the evidence-linking structure that the
**Knowledge Graph** module will later build on — this phase only prepares
the claim/label tabular data, not the KG itself.

---

## 3. Fact Checking — LIAR Dataset

| | |
|---|---|
| **Source** | https://www.cs.ucsb.edu/~william/data/liar_dataset.zip (Wang, 2017, "Liar, Liar Pants on Fire") |
| **Access** | Public, no authentication required |
| **Expected size** | 12,791 short statements (10,269 train / 1,284 val / 1,283 test) |
| **Raw schema** | `id, label, statement, subject, speaker, speaker_job, state_info, party, [5 historical truthfulness counts], context` |
| **License** | Released for research use by the author; no commercial redistribution license stated — treat as research-only |

**Why chosen:** LIAR complements FEVER and ISOT with short, single-sentence
political statements rated on a **6-way fine-grained truthfulness scale**
(pants-fire → true) sourced from PolitiFact, rather than a binary label.
This finer granularity is valuable for a neuro-symbolic system that needs
to reason about degrees of truth, not just true/false. It also carries
rich speaker/context metadata useful for later symbolic reasoning (e.g.
speaker credibility history).

**Downstream use:** Secondary fact-checking signal and fine-grained
truthfulness benchmark for the **Claim Verification** and **Fusion Model**
phases; speaker/context metadata is preserved in the `metadata` field of
the canonical schema for future symbolic-reasoning features.

---

## 4. Image Forensics — CIFAKE: Real and AI-Generated Synthetic Images

| | |
|---|---|
| **Source** | Kaggle: `birdy654/cifake-real-and-ai-generated-synthetic-images` (Bird & Lotfi, 2023) |
| **Access** | Gated (Kaggle account + API token) |
| **Expected size** | 120,000 images (60,000 real from CIFAR-10, 60,000 AI-generated via a latent diffusion model), 32×32 px, pre-split train/test |
| **Raw schema** | Folder structure: `train/REAL/*.jpg`, `train/FAKE/*.jpg`, `test/REAL/*.jpg`, `test/FAKE/*.jpg` |
| **License** | CC0 / open for research and commercial use per the Kaggle listing (verify current terms on the dataset page before redistribution) |

**Why chosen:** Provides a clean, balanced, already-labeled REAL-vs-AI-GENERATED
image benchmark, directly matching the "AI-generated" half of the platform's
multimodal misinformation problem (manipulated/synthetic visuals accompanying
false claims). Its manageable size (120K small images) keeps Phase 1 storage
and validation tractable while still being large enough for future model
training.

**Downstream use:** Feeds the future **Image Forensics** module. This phase
only validates file integrity and produces a `(image_path, label)` metadata
table — no pixel-level features, embeddings, or models are built here.

---

## 5. AI-Generated Text Detection — GPT-2 Output Dataset (OpenAI)

| | |
|---|---|
| **Source** | https://github.com/openai/gpt-2-output-dataset |
| **Access** | Public, no authentication required (direct HTTPS download) |
| **Expected size** | 250,000 human ("webtext") + 250,000 machine-generated ("small-117M") documents across train/valid/test splits (this project uses train splits by default; valid/test are also downloaded for future use) |
| **Raw schema** | JSONL: `{"text": "...", ...}` per line, human and machine files kept separate (label derived from filename) |
| **License** | Released by OpenAI under an MIT-style permissive license for research use |

**Why chosen:** It is the original, widely-cited benchmark for human-vs-GPT-2
text detection, and — despite predating modern LLMs — remains the most
accessible, license-clean, no-signup corpus with a clean 1:1 matched
human/machine design (the human "webtext" split was GPT-2's own training
data source, so topics/style are naturally comparable across classes).

**Limitation acknowledged:** GPT-2-generated text is stylistically easier
to detect than output from current-generation LLMs. This dataset is
suitable for Phase 1 data-engineering purposes and as a first benchmark,
but the **AI-generated Text Detection** module in a later phase should
budget for supplementing it with more modern LLM-generated text if
higher realism is required — that decision is out of scope for this phase.

**Downstream use:** Trains/evaluates the future **AI-generated Text
Detection** module and contributes an additional text-authenticity signal
to the **Fusion Model**.

---

## Dataset Summary Table

| Dataset | Task | Access | Approx. Size | Automated Download |
|---|---|---|---|---|
| ISOT Fake/Real News | fake_news | Kaggle (gated) | ~44.9K | No — manual, see below |
| FEVER | claim_verification | Public URL | ~225K claims | Yes |
| LIAR | fact_checking | Public URL | ~12.8K | Yes |
| CIFAKE | image_forensics | Kaggle (gated) | 120K images | No — manual, see below |
| GPT-2 Output Dataset | ai_text_detection | Public URL | ~500K docs | Yes |

## Manual Download Checklist (Gated Datasets)

Two datasets require you to act before the pipeline can process them:

**ISOT Fake and Real News** (Kaggle)
1. Create a Kaggle account: https://www.kaggle.com
2. Get an API token: Account settings → "Create New Token" → downloads `kaggle.json`
3. Place it at `~/.kaggle/kaggle.json` and `chmod 600` it
4. `pip install kaggle`
5. Run `python src/download/download_fake_real_news.py` (it will use the CLI automatically), OR manually download from https://www.kaggle.com/datasets/clmentbisaillon/fake-and-real-news-dataset and place `Fake.csv` + `True.csv` in `data/raw/fake_real_news/`

**CIFAKE** (Kaggle)
Same prerequisites as above, then:
`python src/download/download_image_forensics.py`, OR manually download from
https://www.kaggle.com/datasets/birdy654/cifake-real-and-ai-generated-synthetic-images
and place the `train/` and `test/` folders in `data/raw/image_forensics/`

The three other datasets (FEVER, LIAR, GPT-2 Output) download automatically
with no account needed — run `python src/download/run_all_downloads.py`.
