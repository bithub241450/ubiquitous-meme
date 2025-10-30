"""Utility helpers for the pricing recorder."""

from __future__ import annotations

import re
from typing import Iterable, Sequence

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def slugify_key(value: str) -> str:
    """Return a filesystem and CSV friendly slug for a column name."""

    value = value.strip().lower()
    value = _SLUG_PATTERN.sub("_", value)
    value = value.strip("_")
    return value or "value"


def union_fieldnames(rows: Sequence[dict[str, str]]) -> list[str]:
    """Return a deterministic list of field names across all rows."""

    preferred_order: list[str] = [
        "collected_at",
        "manufacturer",
        "item_number",
        "model",
        "description",
        "price_text",
        "stock_status",
        "detail_url",
        "image_url",
    ]
    extra = set()
    for row in rows:
        extra.update(row.keys())
    ordered = [field for field in preferred_order if field in extra]
    for field in sorted(extra):
        if field not in preferred_order:
            ordered.append(field)
    return ordered
