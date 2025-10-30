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


def test_parse_manufacturer_products_with_base_url() -> None:
    html = """
    <div class="col d-flex flex-column border rounded px-3 py-3">
      <div class="row">
        <div class="col-6 text-center">
          <a href="default.cfm?itemsearch=ITEM456&amp;page=products&amp;searchcode=N">
            <img src="/wce/thumbnails/example.png" />
          </a>
        </div>
      </div>
      <div class="row">
        <div class="col-6">
          <p class="productDescription font-weight-bold">Another Product</p>
        </div>
      </div>
      <div class="row">
        <div class="col-6">
          <button class="btn btn-cart moreInfoButton" data-item="ITEM456">MORE INFO</button>
        </div>
      </div>
    </div>
    """

    products = parse_manufacturer_products(
        html,
        manufacturer="ExampleCo",
        base_url="https://mirror.example/catalog",
    )

    assert len(products) == 1
    product = products[0]
    assert (
        product.detail_url
        == "https://mirror.example/catalog/default.cfm?itemsearch=ITEM456&page=products&searchcode=N"
    )
    assert product.image_url == "https://mirror.example/wce/thumbnails/example.png"


def test_parse_manufacturer_products_deduplicates_and_merges() -> None:
    html = """
    <div class="col d-flex flex-column border rounded px-3 py-3">
      <div class="row pb-2">
        <div class="col-6 text-center">
          <form>
            <input type="hidden" name="item" value="ITEM1" />
          </form>
        </div>
      </div>
      <div class="row">
        <div class="col-6">
          <p class="productDescription font-weight-bold">First Listing</p>
          <p class="productDescription">Model: MOD-1</p>
          <p class="productDescription my-0 py-0">Dealer: $9.99</p>
        </div>
        <div class="col-6">
          <table>
            <tr><td>Raleigh:</td><td>5</td></tr>
          </table>
        </div>
      </div>
    </div>
    <div class="col d-flex flex-column border rounded px-3 py-3">
      <div class="row pb-2">
        <div class="col-6 text-center">
          <form>
            <input type="hidden" name="item" value="ITEM1" />
          </form>
        </div>
      </div>
      <div class="row">
        <div class="col-6">
          <a class="productPrice" href="#">$8.49</a>
        </div>
        <div class="col-6">
          <table>
            <tr><td>Charlotte:</td><td>2</td></tr>
          </table>
        </div>
      </div>
    </div>
    <div class="col d-flex flex-column border rounded px-3 py-3">
      <div class="row pb-2">
        <div class="col-6 text-center">
          <form>
            <input type="hidden" name="item" value="ITEM2" />
          </form>
        </div>
      </div>
      <div class="row">
        <div class="col-6">
          <p class="productDescription">Model: MOD-2</p>
          <p class="productDescription">Price: $4.99</p>
        </div>
      </div>
    </div>
    """

    products = parse_manufacturer_products(html, manufacturer="ExampleCo")

    assert len(products) == 2
    merged = next(prod for prod in products if prod.item_number == "ITEM1")
    fallback = next(prod for prod in products if prod.item_number == "ITEM2")

    assert merged.price_text == "$8.49"
    assert merged.inventory_by_location == {"Raleigh": "5", "Charlotte": "2"}
    assert merged.extra_fields["Dealer"] == "$9.99"

    assert fallback.price_text == "$4.99"
    assert fallback.extra_fields["Price"] == "$4.99"
