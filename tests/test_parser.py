from __future__ import annotations

from pathlib import Path

from pricing_recorder.parser import parse_manufacturer_products


FIXTURE = Path(__file__).parent / "data" / "manufacturer_snippet.html"


def test_parse_manufacturer_products(tmp_path: Path) -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    products = parse_manufacturer_products(html, manufacturer="ExampleCo")
    assert len(products) == 1

    product = products[0]
    assert product.manufacturer == "ExampleCo"
    assert product.item_number == "ITEM123"
    assert product.model == "PRO-123"
    assert product.description == "Example Product Title"
    assert product.price_text == "$149.99"
    assert product.stock_status == "IN STOCK"
    assert product.inventory_by_location == {"Raleigh": "12", "Charlotte": "5"}
    assert product.extra_fields == {"MAP": "$199.99", "MSRP": "$249.99"}
    assert product.detail_url.endswith("itemsearch=ITEM123&page=products&searchcode=N")
    assert product.image_url.endswith("/wce/thumbnails/example.png")

    flattened = product.as_flat_dict()
    assert flattened["manufacturer"] == "ExampleCo"
    assert flattened["inventory_raleigh"] == "12"
    assert flattened["info_map"] == "$199.99"
