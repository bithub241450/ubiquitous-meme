"""High-level helpers for collecting pricing data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

from .client import Century21Client
from .models import Product
from .parser import parse_manufacturer_products


@dataclass(slots=True)
class ManufacturerCollectionResult:
    """Aggregated result of collecting manufacturers."""

    rows: List[dict[str, str]] = field(default_factory=list)
    empty_manufacturers: List[str] = field(default_factory=list)


def collect_manufacturer_products(client: Century21Client, manufacturer: str) -> List[Product]:
    """Return parsed products for a single manufacturer."""

    html = client.fetch_manufacturer_page(manufacturer)
    return parse_manufacturer_products(html, manufacturer=manufacturer, base_url=client.base_url)


def collect_manufacturer_rows(client: Century21Client, manufacturers: Iterable[str]) -> ManufacturerCollectionResult:
    """Fetch, parse, and flatten manufacturer listings into row dictionaries."""

    result = ManufacturerCollectionResult()
    for manufacturer in manufacturers:
        products = collect_manufacturer_products(client, manufacturer)
        if not products:
            result.empty_manufacturers.append(manufacturer)
            continue
        result.rows.extend(product.as_flat_dict() for product in products)
    return result
