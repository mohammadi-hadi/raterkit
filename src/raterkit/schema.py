"""Input schema and loaders.

The schema deliberately accepts dirty data — duplicate ratings, missing
raters, skewed labels. Auditing those is the point; validation only rejects
rows the audit could not interpret at all.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator

Label = str | int | float


class Rating(BaseModel):
    """One rater's label on one item."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    rater_id: str
    label: Label
    t: float | None = None
    split: str | None = None
    text: str | None = None

    @field_validator("item_id", "rater_id")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("must be non-empty")
        return v


class Gold(BaseModel):
    """A reference label for one item."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    label: Label


class Config(BaseModel):
    """How the labels should be read and what the pipeline expects of them."""

    model_config = ConfigDict(extra="forbid")

    level: str = "nominal"
    labels: list[Label] | None = None
    target_reliability: float = 0.8

    @field_validator("level")
    @classmethod
    def _known_level(cls, v: str) -> str:
        if v not in ("nominal", "ordinal", "interval"):
            raise ValueError("level must be nominal, ordinal or interval")
        return v

    @field_validator("target_reliability")
    @classmethod
    def _valid_target(cls, v: float) -> float:
        if not 0.0 < v < 1.0:
            raise ValueError("target_reliability must be in (0, 1)")
        return v


def load_ratings(path: str | Path) -> list[Rating]:
    """Load ratings from a JSONL file, one rating object per line."""
    out = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(Rating.model_validate(json.loads(line)))
            except Exception as exc:
                raise ValueError(f"{path}:{line_no}: {exc}") from exc
    return out


def load_gold(path: str | Path) -> list[Gold]:
    """Load gold labels from a JSONL file."""
    out = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(Gold.model_validate(json.loads(line)))
            except Exception as exc:
                raise ValueError(f"{path}:{line_no}: {exc}") from exc
    return out


def load_config(path: str | Path) -> Config:
    """Load audit configuration from a JSON file."""
    with open(path, encoding="utf-8") as f:
        return Config.model_validate(json.load(f))
