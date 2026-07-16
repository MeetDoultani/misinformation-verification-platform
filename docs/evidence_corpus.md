# Trusted Evidence Corpus

Full documentation for the evidence corpus placeholder lives next to the
data itself: **[`data/evidence_corpus/README.md`](../data/evidence_corpus/README.md)**.

It's kept there rather than only in `docs/` so anyone browsing
`data/evidence_corpus/` and finding it empty immediately sees why, and
what it's reserved for, without having to know to look in `docs/`.

Short summary: this is a placeholder for future retrieval-augmented claim
verification (Wikipedia + fact-checking-org content + trusted news
sources). It is **not populated in Phase 1** — no downloads, no index, no
embeddings. See the linked README for the full design rationale and how
future modules (Claim Verification, Knowledge Graph, Fusion Model) will
consume it.
