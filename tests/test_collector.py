from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from pricing_recorder.collector import collect_manufacturer_rows


@dataclass
class DummyClient:
    pages: Dict[str, str]
    base_url: str = "https://21stcenturydist.com/"

    def fetch_manufacturer_page(self, manufacturer: str) -> str:
        return self.pages.get(manufacturer, "")


HTML = """
<div class="col d-flex flex-column border rounded px-3 py-3">
  <div class="row">
    <div class="col-6 text-center">
      <a href="default.cfm?itemsearch=ITEM789&amp;page=products&amp;searchcode=N">
        <img src="/wce/thumbnails/example.png" />
      </a>
    </div>
  </div>
  <div class="row">
    <div class="col-12">
      <p class="productDescription font-weight-bold">Widget</p>
    </div>
  </div>
  <div class="row">
    <div class="col-6">
      <button class="btn btn-cart moreInfoButton" data-item="ITEM789">MORE INFO</button>
    </div>
  </div>
</div>
"""


def test_collect_manufacturer_rows_returns_flattened_results() -> None:
    client = DummyClient({"ExampleCo": HTML})

    result = collect_manufacturer_rows(client, ["ExampleCo"])

    assert len(result.rows) == 1
    assert result.empty_manufacturers == []
    row = result.rows[0]
    assert row["manufacturer"] == "ExampleCo"
    assert row["detail_url"].endswith("ITEM789&page=products&searchcode=N")


def test_collect_manufacturer_rows_marks_empty_manufacturers() -> None:
    client = DummyClient({})

    result = collect_manufacturer_rows(client, ["MissingCo"])

    assert result.rows == []
    assert result.empty_manufacturers == ["MissingCo"]
