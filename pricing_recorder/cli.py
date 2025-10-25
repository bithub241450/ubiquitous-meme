"""Command line entry point for the pricing recorder."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable, List

from .client import AuthenticationError, Century21Client, RequestFailed
from .parser import parse_manufacturer_products
from .utils import union_fieldnames


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Record pricing data from 21stcenturydist.com")
    parser.add_argument("manufacturer", nargs="+", help="Manufacturer name(s) to capture")
    parser.add_argument("--email", help="Account email. Defaults to CENTURY21_EMAIL env var")
    parser.add_argument("--password", help="Account password. Defaults to CENTURY21_PASSWORD env var")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--format", choices={"csv", "json"}, default="csv", help="Output file format")
    parser.add_argument("--base-url", default="https://21stcenturydist.com/", help="Override the site base URL")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--skip-login",
        action="store_true",
        help="Skip the login request. Useful for public pages that do not require authentication.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    email = args.email or os.getenv("CENTURY21_EMAIL") or ""
    password = args.password or os.getenv("CENTURY21_PASSWORD") or ""
    if not args.skip_login and (not email or not password):
        parser.error(
            "Credentials must be provided via --email/--password or CENTURY21_EMAIL/CENTURY21_PASSWORD env vars"
        )

    client = Century21Client(email=email, password=password, base_url=args.base_url, timeout=args.timeout)

    if not args.skip_login:
        try:
            client.login()
        except AuthenticationError as exc:
            print(f"[error] Login failed: {exc}", file=sys.stderr)
            return 1
        except RequestFailed as exc:
            print(f"[error] Request failed during login: {exc}", file=sys.stderr)
            return 1

    all_rows: List[dict[str, str]] = []

    for manufacturer in args.manufacturer:
        if args.verbose:
            print(f"[info] Fetching products for {manufacturer}", file=sys.stderr)
        try:
            html = client.fetch_manufacturer_page(manufacturer)
        except RequestFailed as exc:
            print(f"[error] Failed to fetch manufacturer page for {manufacturer}: {exc}", file=sys.stderr)
            return 1
        products = parse_manufacturer_products(html, manufacturer=manufacturer)
        if not products:
            print(
                f"[warn] No products parsed for {manufacturer}. Check credentials or manufacturer spelling.",
                file=sys.stderr,
            )
        for product in products:
            all_rows.append(product.as_flat_dict())

    if not all_rows:
        print("[warn] No data collected. Nothing will be written.", file=sys.stderr)
        return 0

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "csv":
        _write_csv(output_path, all_rows)
    else:
        _write_json(output_path, all_rows)

    if args.verbose:
        print(f"[info] Wrote {len(all_rows)} rows to {output_path}", file=sys.stderr)

    return 0


def _write_csv(path: Path, rows: List[dict[str, str]]) -> None:
    import csv

    fieldnames = union_fieldnames(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, rows: List[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
