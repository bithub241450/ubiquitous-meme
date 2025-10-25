"""HTML parsing helpers."""

from __future__ import annotations

from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from .models import Product

_LOGIN_TEXTS = {"log in", "sign in"}


def parse_manufacturer_products(html: str, manufacturer: str) -> List[Product]:
    """Parse all product tiles from a manufacturer listing page."""

    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("div.col.d-flex.flex-column.border.rounded.px-3.py-3")

    products: List[Product] = []
    for card in cards:
        item_number = _extract_item_number(card)
        description = _extract_description(card)
        model = _extract_model(card)
        price_text = _extract_price(card)
        stock_status = _extract_stock(card)
        inventory = _extract_inventory(card)
        detail_url = _extract_detail_url(card, item_number)
        image_url = _extract_image_url(card)
        extra_fields = _extract_extra_fields(card)

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
        products.append(product)

    return products


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
    price = card.select_one("a.productPrice")
    if not price:
        return None
    text = price.get_text(strip=True)
    if text.lower() in _LOGIN_TEXTS:
        return None
    return text


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


def _extract_detail_url(card, item_number: Optional[str]) -> Optional[str]:
    link = card.select_one(".moreInfoButton")
    if link and link.has_attr("data-item"):
        item_number = link["data-item"].strip()
    anchor = card.select_one("a[href*='itemsearch=']")
    if anchor and anchor.has_attr("href"):
        return anchor["href"]
    if item_number:
        return f"https://21stcenturydist.com/default.cfm?itemsearch={item_number}&page=products&searchcode=N"
    return None


def _extract_image_url(card) -> Optional[str]:
    image = card.select_one("img[src*='/wce/thumbnails/']")
    if image and image.has_attr("src"):
        return image["src"]
    return None


def _extract_extra_fields(card) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    info_column = None
    for column in card.select("div.col-6"):
        if column.select_one("a.productPrice"):
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
        if lower.startswith("map:"):
            fields["MAP"] = text.split(":", 1)[1].strip()
            continue
        if lower.startswith("msrp:"):
            fields["MSRP"] = text.split(":", 1)[1].strip()
            continue
        if lower.startswith("dealer:"):
            fields["Dealer"] = text.split(":", 1)[1].strip()
            continue
        if lower in {"log in to see pricing"}:
            continue
        fields[text] = ""
    return fields
