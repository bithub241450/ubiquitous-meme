"""Data models used by the pricing recorder."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Mapping, MutableMapping, Optional


@dataclass(slots=True)
class Product:
    """Represents a single product listing returned from the website.

    Attributes
    ----------
    manufacturer:
        Human readable manufacturer name used when collecting the data.
    item_number:
        Internal item number used by the distributor.  This is the value that is
        embedded in the add-to-cart forms and AJAX endpoints.
    model:
        Model identifier that is displayed on the product card.
    description:
        Marketing description of the product.
    price_text:
        Raw price string extracted from the listing.  When the session is not
        authenticated this value is typically ``"Log In"``.
    stock_status:
        The text displayed in the stock status badge such as ``"IN STOCK"`` or
        ``"OUT OF STOCK"``.
    inventory_by_location:
        Mapping of branch name to the inventory string displayed for that
        branch.
    detail_url:
        Absolute link to the product detail page.
    image_url:
        Absolute link to the product thumbnail shown on the listing.
    extra_fields:
        Any additional labelled values that are rendered within the listing
        (e.g. MAP, MSRP, special notes).
    collected_at:
        Timestamp indicating when the data was collected.
    """

    manufacturer: str
    item_number: Optional[str] = None
    model: Optional[str] = None
    description: Optional[str] = None
    price_text: Optional[str] = None
    stock_status: Optional[str] = None
    inventory_by_location: Dict[str, str] = field(default_factory=dict)
    detail_url: Optional[str] = None
    image_url: Optional[str] = None
    extra_fields: Dict[str, str] = field(default_factory=dict)
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_flat_dict(self) -> Dict[str, str]:
        """Return a flattened dictionary representation suitable for CSV export."""

        from .utils import slugify_key

        base: Dict[str, str] = {
            "collected_at": self.collected_at.isoformat(),
            "manufacturer": self.manufacturer or "",
            "item_number": self.item_number or "",
            "model": self.model or "",
            "description": self.description or "",
            "price_text": self.price_text or "",
            "stock_status": self.stock_status or "",
            "detail_url": self.detail_url or "",
            "image_url": self.image_url or "",
        }

        for location, quantity in sorted(self.inventory_by_location.items()):
            base[f"inventory_{slugify_key(location)}"] = quantity

        for key, value in sorted(self.extra_fields.items()):
            base[f"info_{slugify_key(key)}"] = value

        return base

    @classmethod
    def merge_flattened(cls, products: Mapping[str, str] | MutableMapping[str, str], *others: Mapping[str, str]) -> Dict[str, str]:
        """Merge multiple flattened dictionaries giving precedence to later ones."""

        merged: Dict[str, str] = dict(products)
        for other in others:
            merged.update(other)
        return merged
