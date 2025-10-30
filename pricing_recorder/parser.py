"""HTML parsing helpers."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .constants import DEFAULT_BASE_URL
from .models import Product

_LOGIN_TEXTS = {"log in", "sign in"}

_FIELD_PREFIXES = {
    "map:": "MAP",
    "msrp:": "MSRP",
    "dealer:": "Dealer",
    "your price:": "Your Price",
    "sale price:": "Sale Price",
    "special price:": "Special Price",
    "price:": "Price",
}

_PRICE_FIELD_KEYS = {"Dealer", "Your Price", "Price", "Sale Price", "Special Price"}


def parse_manufacturer_products(html: str, manufacturer: str, *, base_url: str | None = None) -> List[Product]:
    """Parse all product tiles from a manufacturer listing page."""

    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("div.col.d-flex.flex-column.border.rounded.px-3.py-3")

    products: Dict[str, Tuple[Product, bool]] = {}
    unmatched: List[Product] = []
    base_url = (base_url or DEFAULT_BASE_URL).rstrip("/") + "/"
    for card in cards:
        item_number = _extract_item_number(card)
        description = _extract_description(card)
        model = _extract_model(card)
        price_text = _extract_price(card)
        price_from_fields = False
        stock_status = _extract_stock(card)
        inventory = _extract_inventory(card)
        detail_url = _extract_detail_url(card, item_number, base_url)
        image_url = _extract_image_url(card, base_url)
        extra_fields = _extract_extra_fields(card)

        if not price_text:
            derived_price = _derive_price_from_fields(extra_fields)
            if derived_price:
                price_text = derived_price
                price_from_fields = True

        product = Product(
            manufacturer=manufacturer,
            item_number=item_number,
            model=model,
            description=description,
            price_text=price_text,
            stock_status=stock_status,
            inventory_by_location=inventory,
            detail_url=detail_url,
            image_url=image_url,
            extra_fields=extra_fields,
        )
        key = item_number or detail_url
        if key:
            existing_entry = products.get(key)
            if existing_entry:
                existing, existing_from_fields = existing_entry
                _merge_products(existing, product)

                incoming_price = product.price_text
                incoming_is_login = (
                    incoming_price.lower() in _LOGIN_TEXTS if incoming_price else False
                )
                updated_from_fields = existing_from_fields

                if incoming_price:
                    if not existing.price_text or existing.price_text.lower() in _LOGIN_TEXTS:
                        if not incoming_is_login:
                            existing.price_text = incoming_price
                            updated_from_fields = price_from_fields
                    elif existing_from_fields and not price_from_fields and not incoming_is_login:
                        existing.price_text = incoming_price
                        updated_from_fields = False

                products[key] = (existing, updated_from_fields)
            else:
                products[key] = (product, price_from_fields)
        else:
            unmatched.append(product)

    return [entry[0] for entry in products.values()] + unmatched


def _extract_item_number(card) -> Optional[str]:
    form = card.select_one("form input[name='item']")
    if form and form.has_attr("value"):
        return form["value"].strip()

    button = card.select_one(".moreInfoButton")
    if button and button.has_attr("data-item"):
        return str(button["data-item"]).strip()

    return None


def _extract_description(card) -> Optional[str]:
    description = card.select_one("p.productDescription.font-weight-bold")
    if description:
        return description.get_text(strip=True)
    return None


def _extract_model(card) -> Optional[str]:
    for para in card.select("p.productDescription"):
        text = para.get_text(strip=True)
        if text.lower().startswith("model:"):
            return text.split(":", 1)[1].strip()
    return None


def _extract_price(card) -> Optional[str]:
    price = card.select_one(".productPrice")
    if price:
        attr_value = _first_truthy(
            price.get(attr) for attr in ("data-price", "data-content", "title", "aria-label")
        )
        if attr_value and attr_value.strip().lower() not in _LOGIN_TEXTS:
            return attr_value.strip()

        text = price.get_text(" ", strip=True)
        if text and text.lower() not in _LOGIN_TEXTS:
            return text
    return None


def _extract_stock(card) -> Optional[str]:
    badge = card.select_one(".inStock, .outStock, .productStock")
    if badge:
        return badge.get_text(strip=True)
    return None


def _extract_inventory(card) -> Dict[str, str]:
    inventory: Dict[str, str] = {}
    table = card.select_one("table")
    if not table:
        return inventory

    for row in table.select("tr"):
        cells = [cell.get_text(strip=True) for cell in row.select("td")]
        if len(cells) != 2:
            continue
        location = cells[0].rstrip(": ")
        quantity = cells[1]
        if location:
            inventory[location] = quantity
    return inventory


def _extract_detail_url(card, item_number: Optional[str], base_url: str) -> Optional[str]:
    link = card.select_one(".moreInfoButton")
    if link and link.has_attr("data-item"):
        item_number = link["data-item"].strip()
    anchor = card.select_one("a[href*='itemsearch=']")
    if anchor and anchor.has_attr("href"):
        href = anchor["href"]
        return urljoin(base_url, href)
    if item_number:
        fallback = f"default.cfm?itemsearch={item_number}&page=products&searchcode=N"
        return urljoin(base_url, fallback)
    return None


def _extract_image_url(card, base_url: str) -> Optional[str]:
    image = card.select_one("img[src*='/wce/thumbnails/']")
    if image and image.has_attr("src"):
        return urljoin(base_url, image["src"])
    return None


def _extract_extra_fields(card) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    info_column = None
    for column in card.select("div.col-6"):
        if column.select_one(".productPrice"):
            info_column = column
            break
    if not info_column:
        for column in card.select("div.col-6"):
            if column.select_one("p.productDescription"):
                info_column = column
                break
    if not info_column:
        return fields

    for para in info_column.select("p.productDescription"):
        text = para.get_text(strip=True)
        if not text:
            continue
        lower = text.lower()
        if lower.startswith("model:"):
            continue
        if lower in {"log in to see pricing"}:
            continue
        for prefix, label in _FIELD_PREFIXES.items():
            if lower.startswith(prefix):
                value = text.split(":", 1)[1].strip()
                fields[label] = value
                break
        else:
            fields[text] = ""
    return fields


def _derive_price_from_fields(fields: Dict[str, str]) -> Optional[str]:
    for key in _PRICE_FIELD_KEYS:
        value = fields.get(key)
        if value:
            return value
    return None


def _merge_products(primary: Product, secondary: Product) -> None:
    """Merge ``secondary`` into ``primary`` preferring populated values."""

    if not primary.item_number and secondary.item_number:
        primary.item_number = secondary.item_number

    for attr in ("model", "description", "stock_status", "detail_url", "image_url"):
        current = getattr(primary, attr)
        incoming = getattr(secondary, attr)
        if (not current or current.strip() == "") and incoming:
            setattr(primary, attr, incoming)

    primary.inventory_by_location.update({k: v for k, v in secondary.inventory_by_location.items() if v})
    primary.extra_fields.update({k: v for k, v in secondary.extra_fields.items() if v or k not in primary.extra_fields})


def _first_truthy(values):
    for value in values:
        if value:
            return value
    return None
