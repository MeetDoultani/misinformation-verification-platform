# Assumptions and Limitations

## Assumptions

1. **Kaggle access will be configured separately.** Two of five datasets
   (ISOT Fake/Real News, CIFAKE) require the user to hold a Kaggle account
   and API token; this phase cannot and does not attempt to bypass that.
2. **English-language focus.** No language filtering is enabled by default
   (`cleaning.language_filter: null` in config), but all five source
   datasets are predominantly/exclusively English. Multilingual support
   is out of scope for this phase.
3. **Row = one example.** The canonical schema assumes one row = one
   claim/article/statement/image, matching how all five datasets are
   natively structured. Multi-sentence "evidence" documents (FEVER) are
   flattened into `text_secondary` / `metadata`, not exploded into
   multiple rows.
4. **Task boundaries stay separate.** Each dataset keeps its own `task`
   label (fake_news, claim_verification, fact_checking, ai_text_detection,
   image_forensics) rather than being merged into one universal
   binary "real/fake" target — the tasks are related but not
   equivalent, and conflating them would lose information later modules
   need (e.g. FEVER's 3-way vs. LIAR's 6-way granularity).
5. **80/10/10 split is a reasonable default**, not a hard requirement.
   It balances training-set size against getting statistically stable
   validation/test estimates even for the smaller LIAR dataset (~12.8K
   rows). Documented and configurable in `config/config.yaml`.

## Limitations

1. **GPT-2 Output Dataset is dated.** It benchmarks against GPT-2-era
   text, which is stylistically easier to detect than modern LLM output.
   It's the best license-clean, no-signup option available for this
   phase, but the AI-generated Text Detection module will likely need
   supplementary modern-LLM text in a future phase.
2. **CIFAKE images are 32×32px.** Small resolution keeps this phase's
   storage/validation tractable, but may limit forensic fidelity for the
   future Image Forensics module; higher-resolution manipulated-image
   datasets may need to be added later.
3. **No cross-dataset entity/claim linking yet.** Even though FEVER, LIAR,
   and ISOT all touch overlapping real-world topics, this phase does not
   attempt to link claims across datasets (that's Knowledge Graph work,
   explicitly out of scope here).
4. **Near-duplicate detection is heuristic.** It uses a normalized-text
   exact match, which catches formatting-level duplicates but not
   paraphrased or substantially rewritten re-publications. A future
   phase could upgrade this to embedding-based similarity — deliberately
   not done here since embeddings are out of scope for Phase 1.
5. **Label noise is inherited, not corrected.** All labels are taken
   as-is from the original datasets (e.g. PolitiFact ratings, ISOT's
   source-based labeling). This phase does not re-annotate or
   adjudicate disputed labels.
6. **LIAR's license is research-only** per the author's release terms;
   any future productization work must revisit licensing before
   commercial use.
7. **Manual-download datasets can't be verified until you run them.**
   Since ISOT and CIFAKE require your own Kaggle credentials, this
   phase's automated pipeline has been smoke-tested against
   structurally-equivalent synthetic data, not the real Kaggle files.
   Run `pytest tests/` and `python src/cleaning/clean_datasets.py` after
   placing your real downloads to confirm end-to-end behavior on the
   actual data.
