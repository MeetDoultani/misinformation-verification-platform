"""
canonical_schema.py
--------------------
Formal, typed canonical schema for every data modality the platform
ingests: articles, claims, and images. This is the contract that every
future module (Claim Verification, Knowledge Graph, Image Forensics,
Fusion Model) is written against, regardless of which of the 5 source
datasets a given row originally came from.

Design:
  - `BaseRecord` holds fields common to every modality: identity, source
    tracking, label, and lineage/version metadata (see docs/lineage.md).
  - `ArticleRecord`, `ClaimRecord`, `ImageRecord` extend it with the
    modality-specific fields that actually differ (a claim has evidence
    text; an image has a file path, not a body of text).
  - `to_row()` flattens any record to the single physical table shape
    (`CANONICAL_COLUMNS`) used for storage in `data/processed/*.parquet`,
    so all 3 modalities remain queryable side-by-side with one loader
    (needed by the future Fusion Model, which consumes all modalities at
    once). Fields that don't apply to a given modality are stored as
    empty string, not null, to keep dtypes stable across the parquet files.

CANONICAL_SCHEMA_VERSION is bumped whenever a field is added, removed, or
its meaning changes. It is stamped into every processed row (see
`label_mapping`/`clean_datasets.py`) so a future consumer can tell which
schema revision produced a given file.
"""

from dataclasses import dataclass, field
from typing import Optional

CANONICAL_SCHEMA_VERSION = "1.0"

MODALITIES = ("article", "claim", "image")

# Physical column order for every processed parquet file, regardless of
# modality. Lineage columns (dataset_version, pipeline_version, schema_version,
# ingested_at) are documented in docs/lineage.md.
CANONICAL_COLUMNS = [
    "id", "dataset", "task", "modality",
    "text", "text_secondary", "image_path",
    "label_raw", "label",
    "metadata",
    "schema_version", "dataset_version", "pipeline_version", "ingested_at",
]

# Columns present before label_mapping.py adds the integer `label` column.
PRE_LABEL_COLUMNS = [c for c in CANONICAL_COLUMNS if c != "label"]


@dataclass
class BaseRecord:
    id: str
    dataset: str            # source dataset key, e.g. "liar", "fever"
    task: str                # ML task identifier, e.g. "fact_checking"
    label_raw: str
    metadata: dict = field(default_factory=dict)   # source-specific extra fields

    modality: str = ""       # set by subclasses

    def to_row(self) -> dict:
        raise NotImplementedError


@dataclass
class ArticleRecord(BaseRecord):
    """A full-length text document: news article, or generic long-form text
    (used for both `fake_news` and `ai_text_detection` tasks)."""
    body: str = ""
    headline: str = ""
    modality: str = "article"

    def to_row(self) -> dict:
        return {
            "id": self.id, "dataset": self.dataset, "task": self.task,
            "modality": self.modality,
            "text": self.body, "text_secondary": self.headline, "image_path": "",
            "label_raw": self.label_raw, "metadata": self.metadata,
        }


@dataclass
class ClaimRecord(BaseRecord):
    """A short factual claim/statement, optionally paired with evidence or
    context (used for `claim_verification` and `fact_checking` tasks)."""
    claim_text: str = ""
    evidence_or_context: str = ""
    modality: str = "claim"

    def to_row(self) -> dict:
        return {
            "id": self.id, "dataset": self.dataset, "task": self.task,
            "modality": self.modality,
            "text": self.claim_text, "text_secondary": self.evidence_or_context, "image_path": "",
            "label_raw": self.label_raw, "metadata": self.metadata,
        }


@dataclass
class ImageRecord(BaseRecord):
    """An image asset (used for the `image_forensics` task). Pixel data is
    never loaded into this record -- only the path and file-level metadata."""
    image_path: str = ""
    modality: str = "image"

    def to_row(self) -> dict:
        return {
            "id": self.id, "dataset": self.dataset, "task": self.task,
            "modality": self.modality,
            "text": "", "text_secondary": "", "image_path": self.image_path,
            "label_raw": self.label_raw, "metadata": self.metadata,
        }


RECORD_TYPES = {
    "article": ArticleRecord,
    "claim": ClaimRecord,
    "image": ImageRecord,
}
