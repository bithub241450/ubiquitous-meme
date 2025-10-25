"""HTML parsing helpers."""
from __future__ import annotations

from typing import Dict, List, Optional
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .models import Product


def _extract_price(card):
    """
    Extracts the product price from markup like:
      <p class="productPrice my-0 py-0">
        <sup class="productPriceSup">$</sup>649<sup class="underlinedText productPriceSup">00</sup>
      </p>
    Returns '$649.00' or None.
    """
    price_tag = card.select_one("p.productPrice")
    if not price_tag:
        return None
    # Join all text fragments (handles split <sup> elements)
    price_text = "".join(price_tag.stripped_strings)
    # Normalize '$64900' -> '$649.00'
    price_text = re.sub(r"(\d+)(\s*)(\d{2})$", r"\1.\3", price_text)
    price_text = price_text.replace("$$", "$").strip()
    return price_text or None


def parse_manufacturer_products(html: str, manufacturer: str) -> List[Product]:
    """
    Parses a manufacturer listing page or AJAX fragment and returns
    a list of Product objects with description, model, price, stock, image, and detail URL.
    """
    soup = BeautifulSoup(html, "lxml")
    products: List[Product] = []
    # New layout: each product is wrapped in a col-6 or col-12 div
    cards = soup.select("div.col-6, div.col-12")
    for card in cards:
        desc_bold = card.select_one("p.productDescription.font-weight-bold")
        if not desc_bold:
            # skip image-only or layout divs
            continue
        # Extract model number
        model_value: Optional[str] = None
        model_tag = card.find("p", string=re.compile(r"Model", re.I))
        if model_tag:
            text = model_tag.get_text(strip=True)
            if ":" in text:
                model_value = text.split(":", 1)[1].strip()
        # Extract price
        price = _extract_price(card)
        # Stock status
        stock_tag = card.select_one("p.inStock, p.outStock, p.productStock")
        # Image and detail URL
        img_tag = card.find("img")
        a_tag = card.find("a", href=True)
        image_url = urljoin("https://21stcenturydist.com/", img_tag["src"]) if img_tag and img_tag.get("src") else None
        detail_url = urljoin("https://21stcenturydist.com/", a_tag["href"]) if a_tag else None
        # Build empty inventory and extra fields for now
        inventory: Dict[str, str] = {}
        extra_fields: Dict[str, str] = {}
        product = Product(
            manufacturer=manufacturer,
            item_number=None,
            model=model_value,
            description=desc_bold.get_text(strip=True),
            price_text=price,
            stock_status=stock_tag.get_text(strip=True) if stock_tag else None,
            inventory_by_location=inventory,
            detail_url=detail_url,
            image_url=image_url,
            extra_fields=extra_fields,
        )
        products.append(product)
    # Fallback to original layout if no products found in new layout
    if not products:
        # Use original parser: cards with specific classes
        cards_old = soup.select("div.col.d-flex.flex-column.border.rounded.px-3.py-3")
        for card in cards_old:
            item_number = _extract_item_number(card)
            description = _extract_description(card)
            model = _extract_model(card)
            price_text = _extract_price(card)
            stock_status = _extract_stock(card)
            inventory = _extract_inventory(card)
            detail_url_old = _extract_detail_url(card, item_number)
            image_url_old = _extract_image_url(card)
            extra_fields_old = _extract_extra_fields(card)
            # Skip entries that appear to be image placeholders (no item number and no description)
            if not item_number and not description:
                continue
            product = Product(
                manufacturer=manufacturer,
                item_number=item_number,
                model=model,
                description=description,
                price_text=price_text,
                stock_status=stock_status,
                inventory_by_location=inventory,
                detail_url=detail_url_old,
                image_url=image_url_old,
                extra_fields=extra_fields_old,
            )
            products.append(product)
    return products

# Original helper functions for legacy layout

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
        return (
            f"https://21stcenturydist.com/default.cfm?"
            f"itemsearch={item_number}&page=products&searchcode=N"
        )
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
