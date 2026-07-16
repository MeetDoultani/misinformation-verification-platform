# Trusted Evidence Corpus (Placeholder)

**Status: empty placeholder.** This directory holds no data in Phase 1.
It exists now so the folder layout, naming, and documentation are settled
before the retrieval-dependent modules (Claim Verification, Knowledge
Graph) are built in a later phase.

## What this will hold

A curated corpus of trusted reference material that a future
**retrieval-augmented claim verification** component will search against
when scoring a claim's veracity — analogous to FEVER's Wikipedia evidence
set, but extended with fact-checking-organization content:

| Subfolder | Planned contents |
|---|---|
| `wikipedia/` | A snapshot (or filtered subset) of Wikipedia articles, used the same way FEVER's evidence set is used: as the primary factual-grounding corpus for open-domain claims. |
| `factcheck_org/` | Structured claim-review data from fact-checking organizations (e.g. PolitiFact, Snopes-style claim reviews) — verdicts plus their justification text, for claims that overlap with the platform's own claim set. |
| `trusted_news_sources/` | Articles from wire services and other high-reliability outlets, used as corroborating/contradicting evidence for claims not covered by Wikipedia or existing fact-checks. |

## Why it's separate from `data/raw/` and `data/processed/`

The five datasets under `data/raw/` and `data/processed/` are **labeled
training/evaluation data** (a claim + its truth label). The evidence
corpus is conceptually different: it is **unlabeled reference material**
that a retrieval step will search over at inference time, not something
a model is trained to classify directly. Keeping it in its own top-level
folder avoids conflating "data to learn from" with "data to look things
up in."

## How future phases will use it

1. **Claim Verification module**: given a claim, retrieve the top-k most
   relevant passages from this corpus (initially via lexical retrieval;
   embeddings/dense retrieval are explicitly out of scope for this data
   engineering phase) and pass them to the verification model as
   supporting/refuting evidence — the same claim+evidence+label shape
   FEVER already uses, so the FEVER-trained `claim_verification` dataset
   in `data/processed/` doubles as a template for this format.
2. **Knowledge Graph module**: entities and relations extracted from this
   corpus will seed the KG's node/edge set, giving the symbolic-reasoning
   side of the platform a real-world knowledge base to check claims
   against, rather than relying purely on the neural verification model.
3. **Fusion Model**: evidence-retrieval confidence/relevance scores from
   this corpus become an additional input feature alongside the
   text/image task outputs.

## What's intentionally NOT done in this phase

- No documents have been downloaded or indexed here yet.
- No retrieval index (BM25, FAISS, etc.) is built.
- No embeddings are generated.
- No schema is finalized for individual evidence documents beyond the
  three source-type subfolders above — that will be defined alongside
  the Claim Verification module once retrieval requirements are known.

This placeholder's job is solely to reserve the location and record the
intent, per Phase 1's data-engineering-only scope.
